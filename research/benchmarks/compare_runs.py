"""
research/benchmarks/compare_runs.py - Diffs two benchmark experiment runs.

Usage:
    python -m research.benchmarks.compare_runs research/experiments/runs/RUN_A research/experiments/runs/RUN_B
    python -m research.benchmarks.compare_runs research/experiments/runs/RUN_A research/experiments/runs/RUN_B --json
"""

from __future__ import annotations
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import argparse
from typing import Dict, Any, List
import numpy as np


def load_scorecard(path: str) -> Dict[str, Any]:
    """Loads scorecard from a directory containing scorecard.json or a direct JSON file."""
    if os.path.isdir(path):
        sc_file = os.path.join(path, "scorecard.json")
        if not os.path.exists(sc_file):
            raise FileNotFoundError(f"No scorecard.json found in {path}")
        path = sc_file

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_music_catalog() -> Dict[str, Any]:
    """Loads musical taxonomy metadata if available."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cat_file = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "music_catalog.json")
    if os.path.exists(cat_file):
        try:
            with open(cat_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def compare_scorecards(
    base: Dict[str, Any],
    cand: Dict[str, Any],
    name_a: str,
    name_b: str,
    output_json: bool = False,
    allow_regression: bool = False
) -> int:
    common_tracks = sorted(set(base.keys()).intersection(set(cand.keys())))
    if not common_tracks:
        if output_json:
            print(json.dumps({"error": "No common tracks to compare", "verdict": "ERROR"}))
        else:
            print("No common tracks between the two runs to compare!")
        return 2

    catalog = load_music_catalog()
    per_track = {}
    genre_deltas: Dict[str, List[float]] = {}

    delta_f1 = []
    delta_cmlt = []
    delta_amlt = []
    delta_gap = []
    delta_jitter = []

    for t in common_tracks:
        b_sc = base[t]
        c_sc = cand[t]

        # Handle crashed tracks
        if b_sc.get("crashed") or c_sc.get("crashed"):
            per_track[t] = {
                "d_f1_50ms": -100.0 if c_sc.get("crashed") else 100.0,
                "d_cmlt": 0.0,
                "d_amlt": 0.0,
                "d_upbeat_gap": 0.0,
                "d_jitter_ms": 0.0,
                "verdict": "CRASHED"
            }
            continue

        d_f1 = (c_sc["f1_50ms"] - b_sc["f1_50ms"]) * 100.0
        d_c = (c_sc["cmlt"] - b_sc["cmlt"]) * 100.0
        d_a = (c_sc["amlt"] - b_sc["amlt"]) * 100.0
        d_g = c_sc["upbeat_gap"] - b_sc["upbeat_gap"]
        d_j = c_sc["phase_jitter_ms"] - b_sc["phase_jitter_ms"]

        d_f1_sal = (c_sc.get("f1_salient_50ms", c_sc["f1_50ms"]) - b_sc.get("f1_salient_50ms", b_sc["f1_50ms"])) * 100.0
        d_cal = c_sc.get("bpm_trust_calibration", 0.0) - b_sc.get("bpm_trust_calibration", 0.0)

        delta_f1.append(d_f1)
        delta_cmlt.append(d_c)
        delta_amlt.append(d_a)
        delta_gap.append(d_g)
        delta_jitter.append(d_j)

        genre = catalog.get(t, {}).get("genre", "Other")
        genre_deltas.setdefault(genre, []).append(d_f1)

        verdict = "IMPROVED" if d_f1 > 1.0 or d_c > 2.0 or d_f1_sal > 1.5 else ("REGRESSED" if d_f1 < -1.0 else "NEUTRAL")
        per_track[t] = {
            "d_f1_50ms": float(d_f1),
            "d_f1_salient_50ms": float(d_f1_sal),
            "d_cmlt": float(d_c),
            "d_amlt": float(d_a),
            "d_upbeat_gap": float(d_g),
            "d_jitter_ms": float(d_j),
            "d_trust_calibration": float(d_cal),
            "verdict": verdict
        }

    mean_d_f1 = float(np.mean(delta_f1)) if delta_f1 else 0.0
    mean_d_cmlt = float(np.mean(delta_cmlt)) if delta_cmlt else 0.0
    mean_d_amlt = float(np.mean(delta_amlt)) if delta_amlt else 0.0
    mean_d_gap = float(np.mean(delta_gap)) if delta_gap else 0.0
    mean_d_jitter = float(np.mean(delta_jitter)) if delta_jitter else 0.0

    if mean_d_f1 > 0.5 or mean_d_cmlt > 1.0:
        overall_verdict = "IMPROVED"
        exit_code = 0
    elif mean_d_f1 < -0.5:
        overall_verdict = "REGRESSED"
        exit_code = 0 if allow_regression else 1
    else:
        overall_verdict = "NEUTRAL"
        exit_code = 0

    genre_summary = {
        g: {"tracks": len(diffs), "mean_d_f1_50ms": float(np.mean(diffs))}
        for g, diffs in sorted(genre_deltas.items())
    }

    if output_json:
        result = {
            "baseline": name_a,
            "candidate": name_b,
            "common_tracks_count": len(common_tracks),
            "macro_deltas": {
                "d_f1_50ms": mean_d_f1,
                "d_cmlt": mean_d_cmlt,
                "d_amlt": mean_d_amlt,
                "d_upbeat_gap": mean_d_gap,
                "d_jitter_ms": mean_d_jitter,
            },
            "genre_deltas": genre_summary,
            "overall_verdict": overall_verdict,
            "exit_code": exit_code,
            "per_track": per_track,
        }
        print(json.dumps(result, indent=2))
        return exit_code

    # Terminal ASCII report
    print("=" * 115)
    print(f"📊 BENCHMARK COMPARISON: Baseline [{name_a}] vs Candidate [{name_b}]")
    print("=" * 115)
    print(f"{'Track Name':<32} {'Δ F1@50ms':<13} {'Δ CMLt':<12} {'Δ AMLt':<12} {'Δ UpbeatGap':<14} {'Δ Jitter':<12} {'Verdict':<15}")
    print("-" * 115)

    for t, p in per_track.items():
        if p["verdict"] == "CRASHED":
            print(f"{t[:31]:<32} {'💥 CRASHED':<13} {'--':<12} {'--':<12} {'--':<14} {'--':<12} {'CRASHED':<15}")
            continue

        print(
            f"{t[:31]:<32} "
            f"{p['d_f1_50ms']:>+7.1f}%     "
            f"{p['d_cmlt']:>+7.1f}%   "
            f"{p['d_amlt']:>+7.1f}%   "
            f"{p['d_upbeat_gap']:>+9.2f}    "
            f"{p['d_jitter_ms']:>+7.1f}ms   "
            f"{p['verdict']:<15}"
        )

    print("-" * 115)
    print(
        f"{'MACRO DELTA AVERAGE':<32} "
        f"{mean_d_f1:>+7.1f}%     "
        f"{mean_d_cmlt:>+7.1f}%   "
        f"{mean_d_amlt:>+7.1f}%   "
        f"{mean_d_gap:>+9.2f}    "
        f"{mean_d_jitter:>+7.1f}ms"
    )
    print("=" * 115)

    if genre_summary:
        print("\n" + "=" * 65)
        print("🎼 GENRE DELTA BREAKDOWN (Δ F1@50ms)")
        print("=" * 65)
        print(f"{'Genre':<32} {'Tracks':<10} {'Mean Δ F1@50ms':<15}")
        print("-" * 65)
        for g, gd in genre_summary.items():
            print(f"{g[:31]:<32} {gd['tracks']:<10} {gd['mean_d_f1_50ms']:>+8.1f}%")
        print("=" * 65)

    print()
    if overall_verdict == "IMPROVED":
        print("🎯 OVERALL VERDICT: CANDIDATE OUTPERFORMS BASELINE (Recommended to merge)")
    elif overall_verdict == "REGRESSED":
        print("❌ OVERALL VERDICT: CANDIDATE REGRESSED (Check failure episodes before merging)")
    else:
        print("⚖️ OVERALL VERDICT: STATISTICALLY EQUIVALENT")

    print(f"\n[Exit code: {exit_code} | {'Allowed Regression' if allow_regression and exit_code == 0 else ('Regression Detected' if exit_code == 1 else 'Success/Neutral')}]")
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two benchmark runs")
    parser.add_argument("baseline", help="Path to baseline run directory or scorecard.json")
    parser.add_argument("candidate", help="Path to candidate run directory or scorecard.json")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary")
    parser.add_argument(
        "--allow-regression",
        action="store_true",
        help="Exit with code 0 even if candidate regressed (prevents tool runner errors)"
    )
    args = parser.parse_args()

    base_sc = load_scorecard(args.baseline)
    cand_sc = load_scorecard(args.candidate)

    name_a = os.path.basename(os.path.normpath(args.baseline))
    name_b = os.path.basename(os.path.normpath(args.candidate))

    code = compare_scorecards(
        base_sc,
        cand_sc,
        name_a,
        name_b,
        output_json=args.json,
        allow_regression=args.allow_regression
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
