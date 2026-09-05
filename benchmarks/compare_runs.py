"""
benchmarks/compare_runs.py - Diffs two benchmark experiment runs.

Usage:
    python -m benchmarks.compare_runs experiments/runs/RUN_A experiments/runs/RUN_B
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
from typing import Dict, Any


def load_scorecard(path: str) -> Dict[str, Any]:
    """Loads scorecard from a directory containing scorecard.json or a direct JSON file."""
    if os.path.isdir(path):
        sc_file = os.path.join(path, "scorecard.json")
        if not os.path.exists(sc_file):
            raise FileNotFoundError(f"No scorecard.json found in {path}")
        path = sc_file

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_scorecards(base: Dict[str, Any], cand: Dict[str, Any], name_a: str, name_b: str) -> None:
    common_tracks = sorted(set(base.keys()).intersection(set(cand.keys())))
    if not common_tracks:
        print("No common tracks between the two runs to compare!")
        return

    print("=" * 115)
    print(f"📊 BENCHMARK COMPARISON: Baseline [{name_a}] vs Candidate [{name_b}]")
    print("=" * 115)
    print(f"{'Track Name':<30} {'Δ F1@50ms':<13} {'Δ CMLt':<12} {'Δ AMLt':<12} {'Δ UpbeatGap':<14} {'Δ Jitter':<12} {'Verdict':<15}")
    print("-" * 115)

    delta_f1 = []
    delta_cmlt = []
    delta_amlt = []
    delta_gap = []
    delta_jitter = []

    for t in common_tracks:
        b_sc = base[t]
        c_sc = cand[t]

        d_f1 = (c_sc["f1_50ms"] - b_sc["f1_50ms"]) * 100.0
        d_c = (c_sc["cmlt"] - b_sc["cmlt"]) * 100.0
        d_a = (c_sc["amlt"] - b_sc["amlt"]) * 100.0
        d_g = c_sc["upbeat_gap"] - b_sc["upbeat_gap"]
        d_j = c_sc["phase_jitter_ms"] - b_sc["phase_jitter_ms"]

        delta_f1.append(d_f1)
        delta_cmlt.append(d_c)
        delta_amlt.append(d_a)
        delta_gap.append(d_g)
        delta_jitter.append(d_j)

        verdict = "IMPROVED" if d_f1 > 1.0 or d_c > 2.0 else ("REGRESSED" if d_f1 < -1.0 else "NEUTRAL")

        print(
            f"{t[:29]:<30} "
            f"{d_f1:>+7.1f}%     "
            f"{d_c:>+7.1f}%   "
            f"{d_a:>+7.1f}%   "
            f"{d_g:>+9.2f}    "
            f"{d_j:>+7.1f}ms   "
            f"{verdict:<15}"
        )

    print("-" * 115)
    mean_d_f1 = sum(delta_f1) / len(delta_f1)
    mean_d_cmlt = sum(delta_cmlt) / len(delta_cmlt)
    mean_d_amlt = sum(delta_amlt) / len(delta_amlt)
    mean_d_gap = sum(delta_gap) / len(delta_gap)
    mean_d_jitter = sum(delta_jitter) / len(delta_jitter)

    print(
        f"{'MACRO DELTA AVERAGE':<30} "
        f"{mean_d_f1:>+7.1f}%     "
        f"{mean_d_cmlt:>+7.1f}%   "
        f"{mean_d_amlt:>+7.1f}%   "
        f"{mean_d_gap:>+9.2f}    "
        f"{mean_d_jitter:>+7.1f}ms"
    )
    print("=" * 115)

    if mean_d_f1 > 0.5 or mean_d_cmlt > 1.0:
        print("🎯 OVERALL VERDICT: CANDIDATE OUTPERFORMS BASELINE (Recommended to merge)")
    elif mean_d_f1 < -0.5:
        print("❌ OVERALL VERDICT: CANDIDATE REGRESSED (Check failure episodes before merging)")
    else:
        print("⚖️ OVERALL VERDICT: STATISTICALLY EQUIVALENT")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two benchmark runs")
    parser.add_argument("baseline", help="Path to baseline run directory or scorecard.json")
    parser.add_argument("candidate", help="Path to candidate run directory or scorecard.json")
    args = parser.parse_args()

    base_sc = load_scorecard(args.baseline)
    cand_sc = load_scorecard(args.candidate)

    name_a = os.path.basename(os.path.normpath(args.baseline))
    name_b = os.path.basename(os.path.normpath(args.candidate))

    compare_scorecards(base_sc, cand_sc, name_a, name_b)


if __name__ == "__main__":
    main()
