"""
research/benchmarks/run_ablation.py - Automated Multi-Model & Multi-Parameter Ablation Runner.

Usage:
    # Compare multiple models on a track (e.g. isolating regression cause):
    python -m research.benchmarks.run_ablation --track "Another One Bites The Dust" --models AudioAnalyzer,PhaseInertiaAudioAnalyzer

    # Compare parameter sweeps on a track:
    python -m research.benchmarks.run_ablation --track "Stayin' Alive" --model AudioAnalyzer --params high_snap_ratio=0.50,high_snap_ratio=0.35,high_snap_ratio=0.20

    # Run multi-model ablation on synthetic suite:
    python -m research.benchmarks.run_ablation --suite synthetic --models AudioAnalyzer,PhaseInertiaAudioAnalyzer
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
from typing import Dict, Any, List, Optional, Tuple, Type
import numpy as np

from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioAnalyzer import AudioAnalyzer
from core.RhythmConfig import RhythmConfig
from research.benchmarks.run_benchmark import (
    discover_tracks,
    load_model_class,
    build_rhythm_config,
    load_music_catalog
)
from research.benchmarks.engine.evaluator import run_benchmark_on_track


def evaluate_config(
    model_cls: Type[BaseAudioAnalyzer],
    tracks: List[Tuple[str, str, str]],
    config: RhythmConfig
) -> Dict[str, Any]:
    """Runs model over target tracks and returns aggregated metrics."""
    f1_50_list = []
    f1_70_list = []
    cmlt_list = []
    amlt_list = []
    gap_list = []
    jitter_list = []
    cpu_list = []

    per_track_scores = {}

    for name, audio_path, beats_path in tracks:
        res = run_benchmark_on_track(model_cls, audio_path, beats_path, config=config)
        sc = res["scorecard"]
        per_track_scores[name] = sc

        f1_50_list.append(sc.get("f1_50ms", 0.0))
        f1_70_list.append(sc.get("f1_70ms", 0.0))
        cmlt_list.append(sc.get("cmlt", 0.0))
        amlt_list.append(sc.get("amlt", 0.0))
        gap_list.append(sc.get("upbeat_gap", 0.0))
        jitter_list.append(sc.get("phase_jitter_ms", 0.0))
        cpu_list.append(sc.get("avg_frame_time_ms", 0.0))

    return {
        "f1_50ms": float(np.mean(f1_50_list)) if f1_50_list else 0.0,
        "f1_70ms": float(np.mean(f1_70_list)) if f1_70_list else 0.0,
        "cmlt": float(np.mean(cmlt_list)) if cmlt_list else 0.0,
        "amlt": float(np.mean(amlt_list)) if amlt_list else 0.0,
        "upbeat_gap": float(np.mean(gap_list)) if gap_list else 0.0,
        "phase_jitter_ms": float(np.mean(jitter_list)) if jitter_list else 0.0,
        "avg_frame_time_ms": float(np.mean(cpu_list)) if cpu_list else 0.0,
        "per_track": per_track_scores
    }


def format_ablation_table(
    experiment_results: List[Tuple[str, Dict[str, Any]]],
    track_title: str
) -> str:
    """Formats an ASCII and Markdown comparison table with baseline deltas."""
    lines = []
    lines.append("=" * 110)
    lines.append(f"🧪 ABLATION MATRIX: {track_title}")
    lines.append("=" * 110)
    lines.append(
        f"{'Configuration':<35} {'F1@50ms':<12} {'Δ F1':<10} {'CMLt':<10} {'Δ CMLt':<10} {'AMLt':<10} {'Gap':<8} {'Jitter':<10} {'CPU'}"
    )
    lines.append("-" * 110)

    base_f1 = experiment_results[0][1]["f1_50ms"]
    base_cmlt = experiment_results[0][1]["cmlt"]

    for i, (label, sc) in enumerate(experiment_results):
        f1_pct = sc["f1_50ms"] * 100.0
        cmlt_pct = sc["cmlt"] * 100.0
        amlt_pct = sc["amlt"] * 100.0
        gap = sc["upbeat_gap"]
        jitter = sc["phase_jitter_ms"]
        cpu = sc["avg_frame_time_ms"]

        if i == 0:
            d_f1_str = "Baseline"
            d_cmlt_str = "--"
        else:
            d_f1 = (sc["f1_50ms"] - base_f1) * 100.0
            d_cmlt = (sc["cmlt"] - base_cmlt) * 100.0
            d_f1_str = f"{d_f1:>+6.1f}%"
            d_cmlt_str = f"{d_cmlt:>+6.1f}%"

        lines.append(
            f"{label[:34]:<35} {f1_pct:>5.1f}%      {d_f1_str:<10} {cmlt_pct:>5.1f}%    {d_cmlt_str:<10} {amlt_pct:>5.1f}%    {gap:>5.2f}   {jitter:>5.1f}ms   {cpu:>4.2f}ms"
        )

    lines.append("=" * 110)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vialactée Automated Ablation Study Runner")
    parser.add_argument("--track", type=str, default="", help="Evaluate ablation on a single track name")
    parser.add_argument("--suite", type=str, default="neural-core", help="Evaluate ablation on suite (default: neural-core)")
    parser.add_argument("--models", type=str, default="", help="Comma-separated model classes (e.g. 'AudioAnalyzer,PhaseInertiaAudioAnalyzer')")
    parser.add_argument("--model", type=str, default="AudioAnalyzer", help="Base model when sweeping params (default: AudioAnalyzer)")
    parser.add_argument("--params", type=str, default="", help="Comma-separated param overrides (e.g. 'high_snap_ratio=0.5,high_snap_ratio=0.35')")
    parser.add_argument("--output", type=str, default="", help="Optional path to write markdown table")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Discover target tracks
    if args.track:
        all_tracks = discover_tracks(suite="all", repo_root=repo_root)
        matching = [t for t in all_tracks if args.track.lower() in t[0].lower()]
        if not matching:
            raise ValueError(f"No track found matching '{args.track}'")
        matching.sort(key=lambda x: len(x[0]))
        tracks = [matching[0]]
        track_title = f"Track: {tracks[0][0]}"
    else:
        tracks = discover_tracks(suite=args.suite, repo_root=repo_root)
        if not tracks:
            raise ValueError(f"No tracks found for suite '{args.suite}'")
        track_title = f"Suite: {args.suite} ({len(tracks)} tracks)"

    experiment_plan: List[Tuple[str, Type[BaseAudioAnalyzer], RhythmConfig]] = []

    if args.models:
        model_names = [m.strip() for m in args.models.split(",") if m.strip()]
        base_cfg = RhythmConfig()
        for mname in model_names:
            cls = load_model_class(mname, repo_root)
            experiment_plan.append((mname, cls, base_cfg))
    elif args.params:
        cls = load_model_class(args.model, repo_root)
        param_sets = [p.strip() for p in args.params.split(",") if p.strip()]
        # Baseline with defaults
        experiment_plan.append((f"{args.model} (default)", cls, RhythmConfig()))
        for p in param_sets:
            cfg = build_rhythm_config(param_overrides=[p])
            experiment_plan.append((f"{args.model} [{p}]", cls, cfg))
    else:
        raise ValueError("Must specify either --models or --params for ablation!")

    print(f"\n🚀 Running Ablation Experiment: {track_title}")
    print(f"   Testing {len(experiment_plan)} configurations across {len(tracks)} tracks...\n")

    results: List[Tuple[str, Dict[str, Any]]] = []
    for label, cls, cfg in experiment_plan:
        print(f"  --> Evaluating: {label}...")
        sc = evaluate_config(cls, tracks, cfg)
        results.append((label, sc))

    table_text = format_ablation_table(results, track_title)
    print("\n" + table_text + "\n")

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(table_text)
        print(f"📄 Saved ablation report to {args.output}")


if __name__ == "__main__":
    main()
