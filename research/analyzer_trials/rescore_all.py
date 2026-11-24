"""Score every analyzer model on a benchmark suite and save the per-track scorecards to one JSON file.

Used to measure how much the leaderboard depends on the reference files: run once before correcting the
references and once after, then compare with --compare.

Run from the repository root with the project's own environment:
    python research/analyzer_trials/rescore_all.py --suite neural-core --out research/analyzer_trials/output/rescore/before.json
    python research/analyzer_trials/rescore_all.py --compare before.json after.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

PRODUCTION = ["AudioAnalyzer", "MultiBandOnsetAudioAnalyzer", "DyadicMetricalAudioAnalyzer"]
KEYS = ["f1_50ms", "f1_70ms", "f1_salient_50ms", "cmlt", "amlt", "upbeat_gap"]


def model_names() -> list[str]:
    models_dir = os.path.join(REPO, "research", "experiments", "models")
    extra = sorted(f[:-3] for f in os.listdir(models_dir) if f.endswith(".py") and not f.startswith("__"))
    return PRODUCTION + [m for m in extra if m not in PRODUCTION]


def score(job: tuple[str, str, str, str]) -> tuple[str, str, dict]:
    model, name, audio, beats = job
    from research.benchmarks.run_benchmark import build_rhythm_config, load_model_class
    from research.benchmarks.engine.evaluator import run_benchmark_on_track

    try:
        res = run_benchmark_on_track(load_model_class(model, REPO), audio, beats, config=build_rhythm_config())
        card = {k: float(v) for k, v in res["scorecard"].items() if isinstance(v, (int, float))}
    except Exception as e:  # a crashed model scores zero, as in run_benchmark.py
        card = {"f1_50ms": 0.0, "crashed": 1.0, "error": str(e)[:200]}
    return model, name, card


def run(suite: str, out: str, workers: int, only: list[str], beats_dir: str = "") -> None:
    from research.benchmarks.run_benchmark import discover_tracks

    tracks = discover_tracks(suite=suite, repo_root=REPO, genre="", meter="", character="")
    if beats_dir:  # score against another copy of the references (e.g. the old ones exported from git)
        tracks = [(n, a, os.path.join(beats_dir, os.path.basename(b))) for n, a, b in tracks]
    models = [m for m in model_names() if not only or m in only]
    jobs = [(m, n, a, b) for m in models for n, a, b in tracks]
    print(f"{len(models)} models x {len(tracks)} tracks = {len(jobs)} simulations, {workers} workers", flush=True)
    results: dict[str, dict] = {m: {} for m in models}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, (model, name, card) in enumerate(pool.map(score, jobs), 1):
            results[model][name] = card
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} done, {time.time() - t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"suite": suite, "results": results}, f, indent=1)
    crashed = sorted({n for tr in results.values() for n, c in tr.items() if c.get("crashed")})
    print(f"tracks that crashed for at least one model: {len(crashed)} {crashed[:6]}")
    table(results)


def macro(tracks: dict, key: str) -> float:
    vals = [c.get(key, c.get("f1_50ms", 0.0)) for c in tracks.values() if not c.get("crashed")]
    return 100 * sum(vals) / len(vals) if vals else 0.0


def table(results: dict) -> None:
    print(f"\n{'model':32s} " + " ".join(f"{k:>16s}" for k in KEYS[:5]))
    for m, tr in sorted(results.items(), key=lambda kv: -macro(kv[1], "f1_50ms")):
        print(f"{m:32s} " + " ".join(f"{macro(tr, k):16.1f}" for k in KEYS[:5]))


def compare(a_path: str, b_path: str) -> None:
    a = json.load(open(a_path, encoding="utf-8"))["results"]
    b = json.load(open(b_path, encoding="utf-8"))["results"]
    rank = lambda r: {m: i + 1 for i, m in enumerate(sorted(r, key=lambda m: -macro(r[m], "f1_50ms")))}
    ra, rb = rank(a), rank(b)
    print(f"{'model':32s} {'F1@50 before':>12s} {'after':>7s} {'change':>7s}   {'salient before':>14s} {'after':>7s}   rank")
    for m in sorted(b, key=lambda m: rb[m]):
        fa, fb = macro(a[m], "f1_50ms"), macro(b[m], "f1_50ms")
        print(f"{m:32s} {fa:12.1f} {fb:7.1f} {fb - fa:+7.1f}   {macro(a[m], 'f1_salient_50ms'):14.1f} {macro(b[m], 'f1_salient_50ms'):7.1f}   {ra[m]} -> {rb[m]}")
    best = max(b, key=lambda m: macro(b[m], "f1_50ms"))
    print(f"\nper track, {best}:")
    for t in sorted(b[best]):
        fa, fb = 100 * a[best][t].get("f1_50ms", 0), 100 * b[best][t].get("f1_50ms", 0)
        flag = "  <-- changed" if abs(fb - fa) >= 1 else ""
        print(f"  {t[:44]:44s} {fa:6.1f} -> {fb:6.1f}{flag}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--suite", default="neural-core")
    p.add_argument("--out", default="")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--model", action="append", default=[])
    p.add_argument("--compare", nargs=2)
    p.add_argument("--beats-dir", default="", help="score against the reference files in this folder instead")
    args = p.parse_args()
    if args.compare:
        compare(*args.compare)
    else:
        run(args.suite, args.out, args.workers, args.model, args.beats_dir)
