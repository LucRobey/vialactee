"""Score analyzer models through the production Listener path, with and without the 5 s look-ahead.

The standard benchmark (research/benchmarks/engine/evaluator.py) runs the bare analyzer on a mock ingestion with
`fakeDelay: 0.0`. The installation runs `music.Listener` with real `AudioIngestion` and `fakeDelay: 5.0`: the
analyzer hears the music 5 s before the speakers and emits `is_beat` at speaker time. This script measures that.

For each model, track and look-ahead value it steps a Listener offline at 60 Hz (same stepping as
tools/choreography_probe.py), records every beat at its speaker time (frame time minus look-ahead), and scores
it with the benchmark's own `compute_scorecard`.

Run from the repository root:
    python research/analyzer_trials/rescore_lookahead.py --suite neural-core --out research/analyzer_trials/output/rescore/lookahead_core.json
    python research/analyzer_trials/rescore_lookahead.py --calibrate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from rescore_all import model_names  # noqa: E402

LOOKAHEADS = (0.0, 5.0)


def listener_beats(model: str, mono: np.ndarray, lookahead: float) -> tuple[np.ndarray, list[float]]:
    """Beat times (seconds into the song, at speaker time) emitted by `model` inside a production Listener."""
    from music.api import Listener
    from research.benchmarks.run_benchmark import load_model_class
    from tools.choreography_probe import HOP, OfflineClock, step_listener
    from tools.listener_config import build_listener_infos

    infos = build_listener_infos()
    infos["fakeDelay"] = lookahead
    beats: list[float] = []
    durations: list[float] = []
    with OfflineClock() as clock:
        listener = Listener(infos, analyzer_class=load_model_class(model, REPO))
        listener.dynamic_audio_latency = 0.0
        last = listener.beat_count
        frames = len(mono) // HOP + int((lookahead + 1.0) * 60)  # keep stepping until the speakers reach the end
        for k in range(frames):
            t0 = time.perf_counter()
            step_listener(listener, mono, k * HOP, clock)
            durations.append(time.perf_counter() - t0)
            if listener.is_beat or listener.beat_count > last:
                beats.append(k / 60.0 - lookahead)
                last = listener.beat_count
    return np.array([b for b in beats if b >= 0.0], dtype=np.float64), durations


def score(job: tuple[str, str, str, str, float]) -> tuple[str, str, float, dict]:
    model, name, audio, beats_path, lookahead = job
    from research.benchmarks.engine.evaluator import compute_scorecard, load_beats_file
    from tools.choreography_probe import load_audio_mono

    try:
        est, durations = listener_beats(model, load_audio_mono(audio), lookahead)
        ref = load_beats_file(beats_path)
        weights = curve = None
        sp = beats_path.replace(".beats.txt", ".salience.npz")
        if os.path.exists(sp):
            s = np.load(sp)
            weights = s["beat_weights"].astype(np.float64)
            curve = {"times": s["times"].astype(np.float64), "curve": s["salience_curve"].astype(np.float64)}
        card = compute_scorecard(ref, est, durations, salience_weights=weights, salience_curve_data=curve)
        card = {k: float(v) for k, v in card.items() if isinstance(v, (int, float))}
        card["n_est"] = float(len(est))
    except Exception as e:
        card = {"f1_50ms": 0.0, "crashed": 1.0, "error": f"{type(e).__name__}: {e}"[:200]}
    return model, name, lookahead, card


def macro(tracks: dict, key: str) -> float:
    vals = [c.get(key, 0.0) for c in tracks.values() if not c.get("crashed")]
    return float(np.mean(vals)) if vals else float("nan")


def run(suite: str, out: str, workers: int, only: list[str]) -> None:
    from research.benchmarks.run_benchmark import discover_tracks

    tracks = discover_tracks(suite=suite, repo_root=REPO, genre="", meter="", character="")
    models = [m for m in model_names() if not only or m in only]
    jobs = [(m, n, a, b, la) for la in LOOKAHEADS for m in models for n, a, b in tracks]
    print(f"{len(models)} models x {len(tracks)} tracks x {len(LOOKAHEADS)} look-ahead settings = {len(jobs)} runs", flush=True)
    res: dict = {str(la): {m: {} for m in models} for la in LOOKAHEADS}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, (model, name, la, card) in enumerate(pool.map(score, jobs), 1):
            res[str(la)][model][name] = card
            if i % 20 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} done, {time.time() - t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump({"suite": suite, "results": res}, open(out, "w", encoding="utf-8"), indent=1)
    report(res)


def report(res: dict) -> None:
    a, b = res[str(LOOKAHEADS[0])], res[str(LOOKAHEADS[1])]
    crashed = sorted({(m, la) for la, r in res.items() for m, tr in r.items() if any(c.get("crashed") for c in tr.values())})
    if crashed:
        print("crashed (model, look-ahead):", crashed)
    print(f"\n{'model':30s} {'F1@50 no look-ahead':>20s} {'with 5 s':>9s} {'change':>7s}   {'F1@70':>6s} {'5 s':>6s}   {'bias ms':>8s} {'5 s':>6s}")
    for m in sorted(b, key=lambda m: -(macro(b[m], "f1_50ms") if not np.isnan(macro(b[m], "f1_50ms")) else -1)):
        fa, fb = 100 * macro(a[m], "f1_50ms"), 100 * macro(b[m], "f1_50ms")
        print(f"{m:30s} {fa:20.1f} {fb:9.1f} {fb - fa:+7.1f}   {100 * macro(a[m], 'f1_70ms'):6.1f} {100 * macro(b[m], 'f1_70ms'):6.1f}"
              f"   {macro(a[m], 'mean_phase_bias_ms'):8.1f} {macro(b[m], 'mean_phase_bias_ms'):6.1f}")


def per_track(path: str, models: list[str]) -> None:
    res = json.load(open(path, encoding="utf-8"))["results"]
    a, b = res[str(LOOKAHEADS[0])], res[str(LOOKAHEADS[1])]
    for m in models:
        print(f"\n{m}: F1@50 per track, no look-ahead -> with 5 s")
        for t in sorted(b[m]):
            print(f"  {t[:44]:44s} {100 * a[m][t].get('f1_50ms', 0):6.1f} -> {100 * b[m][t].get('f1_50ms', 0):6.1f}")


def calibrate() -> None:
    """Timing check on a synthetic click track whose beat times are known exactly."""
    from research.benchmarks.engine.evaluator import load_beats_file
    from tools.choreography_probe import load_audio_mono

    d = os.path.join(REPO, "research", "benchmarks", "ground_truth", "synthetic_cache")
    for clip in ("synthetic_click_120bpm", "synthetic_click_85bpm"):
        mono, ref = load_audio_mono(os.path.join(d, clip + ".wav")), load_beats_file(os.path.join(d, clip + ".beats.txt"))
        for model in ("DyadicMetricalAudioAnalyzer", "MultiBandOnsetAudioAnalyzer"):
            for la in LOOKAHEADS:
                est, _ = listener_beats(model, mono, la)
                est = est[est > 8.0]  # after lock-in
                idx = np.clip(np.searchsorted(ref, est), 1, len(ref) - 1)
                err = np.where(np.abs(est - ref[idx - 1]) < np.abs(est - ref[idx]), est - ref[idx - 1], est - ref[idx])
                print(f"{clip:26s} {model:28s} look-ahead {la:3.1f}s: {len(est):3d} beats, "
                      f"median offset {1000 * np.median(err):+6.1f} ms, spread {1000 * np.std(err):5.1f} ms")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--suite", default="neural-core")
    p.add_argument("--out", default="")
    p.add_argument("--workers", type=int, default=5)
    p.add_argument("--model", action="append", default=[])
    p.add_argument("--calibrate", action="store_true")
    p.add_argument("--per-track", default="")
    args = p.parse_args()
    if args.calibrate:
        calibrate()
    elif args.per_track:
        per_track(args.per_track, args.model or ["DyadicMetricalAudioAnalyzer", "MultiBandOnsetAudioAnalyzer"])
    else:
        run(args.suite, args.out, args.workers, args.model)
