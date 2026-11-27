"""Tuning of the no-beat rule of NoBeatSlotAudioAnalyzer, on the OPEN tracks only (split.json).

Step 1 (capture): play each open track through the production Listener and keep, per tick, what the analyzer
knows when the audio ARRIVES (tick k is the music at k / 60 s): how sure the tempo judge is, the streams it
builds, the level. The kicks are read from the production slot (speaker time) and shifted back to arrival time.
Step 2 (sweep): replay the rule offline over that capture for a grid of settings and grade each against
regions.no_beat with the scoreboard's own grading (grade.state_score), averaged over the open tracks.

The check tracks are never read here.

Run from the repository root:
    research/analyzer_trials/.venv/Scripts/python.exe research/scoreboard/runs/2026-11-27_no_beat/tune_no_beat.py capture
    research/analyzer_trials/.venv/Scripts/python.exe research/scoreboard/runs/2026-11-27_no_beat/tune_no_beat.py look
    research/analyzer_trials/.venv/Scripts/python.exe research/scoreboard/runs/2026-11-27_no_beat/tune_no_beat.py sweep
"""
from __future__ import annotations

import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
CAPTURE = REPO / "research" / "scoreboard" / "output" / "tune_no_beat"
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
SPLIT = json.loads((REPO / "research" / "scoreboard" / "split.json").read_text(encoding="utf-8"))
OPEN = [t for t in TRACKS["tracks"] if t["id"] in SPLIT["open"]]
FPS = 60.0
LEAD = 300                           # 5 s of look-ahead, in ticks


def _capture_one(t: dict) -> str:
    from music.api import Listener
    from tools.choreography_probe import HOP, OfflineClock, load_audio_mono, step_listener
    from tools.listener_config import build_listener_infos

    mono = load_audio_mono(str(REPO / TRACKS["audio_dir"] / t["file"]))
    n = len(mono) // HOP
    cols = ("conf", "locked", "odf", "kick_stream", "snare_stream", "hat_stream", "baseline", "bpm", "power", "kick", "sub")
    out = {c: np.zeros(n, dtype=np.float32) for c in cols}
    with OfflineClock() as clock:
        listener = Listener(build_listener_infos())
        listener.dynamic_audio_latency = 0.0
        a = listener.analyzer
        for k in range(n + LEAD):
            step_listener(listener, mono, k * HOP, clock)
            if k < n:
                out["conf"][k] = a.confidence_score
                out["locked"][k] = float(a.flywheel_status == "locked")
                out["odf"][k] = a.odf_buffer[-1]
                out["kick_stream"][k] = a.kick_odf_buffer[-1]
                out["snare_stream"][k] = a.snare_odf_buffer[-1]
                out["hat_stream"][k] = a.hat_odf_buffer[-1]
                out["baseline"][k] = a.rolling_flux_baseline
                out["bpm"][k] = a.bpm
                out["power"][k] = float(np.sum(a.ingestion.multiband_fft_values))
                out["sub"][k] = float(a.subpulse_active)
            i = k - LEAD                                  # the production kick slot speaks at speaker time
            if 0 <= i < n and listener.signals.kick:
                out["kick"][i] = float(listener.signals.kick)
    CAPTURE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CAPTURE / f"{t['id']}.npz", **out)
    return f"[{t['id']}] {n} ticks"


def capture() -> None:
    with ProcessPoolExecutor(max_workers=5) as pool:
        for line in pool.map(_capture_one, OPEN):
            print(line, flush=True)


def load() -> list:
    from research.scoreboard import grade

    data = []
    for t in OPEN:
        truth = json.loads((REPO / "research" / "truth" / "tracks" / f"{t['id']}.json").read_text(encoding="utf-8"))
        with np.load(CAPTURE / f"{t['id']}.npz") as z:
            cap = {k: z[k].astype(float) for k in z.files}
        n = len(cap["conf"])
        regions = truth["regions"].get("no_beat", [])
        mask = grade.regions_to_mask([(r["start"], r["end"]) for r in regions], n, FPS)
        silence = grade.regions_to_mask([(r["start"], r["end"]) for r in truth["regions"].get("silence", [])], n, FPS)
        data.append({"id": t["id"], "name": t["file"][:24], "cap": cap, "mask": mask, "silence": silence, "regions": regions})
    return data


HALF = 150                           # the rule decides for the instant half a look-ahead (2.5 s) before the newest audio


def kick_gap(kick: np.ndarray) -> np.ndarray:
    """Per tick: seconds from the kick before to the kick after. The kick after is only known 2.5 s ahead."""
    n = len(kick)
    at = np.flatnonzero(kick > 0)
    idx = np.arange(n)
    since = np.full(n, 1e9)
    until = np.full(n, 1e9)
    if len(at):
        pos = np.searchsorted(at, idx, side="right")
        since[pos > 0] = (idx[pos > 0] - at[pos[pos > 0] - 1]) / FPS
        nxt = pos < len(at)
        until[nxt] = (at[pos[nxt]] - idx[nxt]) / FPS
    return since + np.minimum(until, HALF / FPS)


def rule(cap: dict, gap_s: float, conf_max: float, window_s: float, share: float = 0.5) -> np.ndarray:
    """The rule of the candidate, replayed offline. Returns no_beat per tick of the song (speaker time).

    Raw answer for an instant: no kick around it (more than gap_s between the kick before and the kick after)
    AND the tempo judge is unsure of the 5 s centred on it (confidence under conf_max). The answer given is the
    majority of the raw answers from window_s before to window_s after.
    """
    n = len(cap["conf"])
    conf_mid = cap["conf"][np.clip(np.arange(n) + HALF, 0, n - 1)]
    raw = (kick_gap(cap["kick"]) > gap_s) & (conf_mid < conf_max)
    w = int(round(window_s * FPS))
    if w == 0:
        return raw
    padded = np.concatenate((np.ones(w), raw.astype(float), np.full(w, float(raw[-1]))))   # before the song: no beat
    csum = np.concatenate(([0.0], np.cumsum(padded)))
    return (csum[2 * w + 1:] - csum[:-2 * w - 1]) / (2 * w + 1) > share


def _grade(data: list, est_of) -> tuple:
    """Mean score over the open tracks that have a no-beat stretch; share of 'no beat' on those that have none."""
    from research.scoreboard import grade

    scores, false_on, per = [], [], []
    for d in data:
        est = est_of(d)
        if d["mask"].any():
            res = grade.state_score(est, d["mask"], FPS)
            scores.append(res["balanced"])
            per.append(f"{d['id']}:{100 * res['balanced']:.0f}")
        else:
            music = ~d["silence"]
            false_on.append(float(np.mean(est[music])))
            per.append(f"{d['id']}:on {100 * false_on[-1]:.0f}%")
    return float(np.mean(scores)), float(np.max(false_on)), " ".join(per)


def sweep() -> None:
    data = load()
    print("stand-in of the scoreboard, replayed from the capture (the confidence of the 5 s BEFORE the instant):")
    for c in (0.30, 0.35):
        m, f, per = _grade(data, lambda d: d["cap"]["conf"] < c)
        print(f"  beat trust under {c}: {100 * m:5.1f}   worst false share {100 * f:3.0f}%   {per}")
    results = []
    for gap_s, conf_max, window_s in itertools.product((1.5, 2.0, 2.5), (0.30, 0.35, 0.40, 0.45, 0.50, 9.0), (0.0, 1.0, 1.5, 2.0, 2.5)):
        m, f, per = _grade(data, lambda d: rule(d["cap"], gap_s, conf_max, window_s))
        results.append((m, f, gap_s, conf_max, window_s, per))
    results.sort(reverse=True)
    print("score = mean over the open tracks with a no-beat stretch; false = worst share of 'no beat' on a track with none")
    print("score false | gap_s conf_max window_s | track by track")
    for m, f, gap_s, conf_max, window_s, per in results:
        print(f"{100 * m:5.1f} {100 * f:4.0f}% | {gap_s:4.1f} {conf_max:6.2f} {window_s:6.1f} | {per}")


if __name__ == "__main__":
    {"capture": capture, "sweep": sweep}[sys.argv[1]]()
