"""
benchmarks/run_benchmark.py - CLI Runner for the Vialactée Beat Tracking Benchmark Suite.

Usage:
    python -m benchmarks.run_benchmark --suite synthetic --save-run
    python -m benchmarks.run_benchmark --suite all --save-run
    python -m benchmarks.run_benchmark --model AudioAnalyzer --suite synthetic
"""

from __future__ import annotations
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import argparse
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np

from core.AudioAnalyzer import AudioAnalyzer
from benchmarks.engine.evaluator import run_benchmark_on_track
from benchmarks.engine.episode_slicer import extract_failure_episodes
from benchmarks.ground_truth.synthetic.generator import generate_all_synthetic_tracks


def get_git_commit() -> str:
    """Retrieves current git commit hash if available."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def discover_tracks(suite: str, repo_root: str) -> List[Tuple[str, str, str]]:
    """
    Finds audio and ground truth files for the chosen suite.
    Returns: List of (track_name, audio_path, beats_path)
    """
    tracks: List[Tuple[str, str, str]] = []

    # 1. Synthetic Suite
    if suite in ("synthetic", "all"):
        synth_cache = os.path.join(repo_root, "benchmarks", "ground_truth", "synthetic_cache")
        os.makedirs(synth_cache, exist_ok=True)
        # Ensure synthetic audio exists
        generate_all_synthetic_tracks(synth_cache)

        for f in sorted(os.listdir(synth_cache)):
            if f.endswith(".wav"):
                track_name = f.replace(".wav", "")
                beats_file = os.path.join(synth_cache, f"{track_name}.beats.txt")
                wav_file = os.path.join(synth_cache, f)
                if os.path.exists(beats_file):
                    tracks.append((track_name, wav_file, beats_file))

    # 2. Neural Ground Truth Suite (Deep Learning verified)
    if suite in ("neural", "all"):
        neural_dir = os.path.join(repo_root, "benchmarks", "ground_truth", "neural")
        mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")

        if os.path.exists(neural_dir):
            for f in sorted(os.listdir(neural_dir)):
                if f.endswith(".beats.txt"):
                    track_name = f.replace(".beats.txt", "")
                    beats_file = os.path.join(neural_dir, f)

                    # Look for corresponding audio file in assets/musics/mp3_files
                    audio_cand1 = os.path.join(mp3_dir, f"{track_name}.mp3")
                    audio_cand2 = os.path.join(mp3_dir, f"{track_name}.m4a")

                    audio_file = None
                    if os.path.exists(audio_cand1):
                        audio_file = audio_cand1
                    elif os.path.exists(audio_cand2):
                        audio_file = audio_cand2
                    else:
                        for mp3_f in os.listdir(mp3_dir):
                            if mp3_f.startswith(track_name) and mp3_f.endswith((".mp3", ".m4a")):
                                audio_file = os.path.join(mp3_dir, mp3_f)
                                break

                    if audio_file and os.path.exists(audio_file):
                        tracks.append((track_name, audio_file, beats_file))

    # 3. Academic Suite (Ballroom, etc.)
    if suite in ("academic", "ballroom"):
        from benchmarks.ground_truth.academic.loader import load_academic_tracks
        academic_tracks = load_academic_tracks("ballroom", require_audio=True)
        academic_beats_dir = os.path.join(repo_root, "benchmarks", "ground_truth", "academic", "ballroom")
        for track_id, audio_path, beats_array in academic_tracks:
            txt_path = os.path.join(academic_beats_dir, f"{track_id}.beats.txt")
            if not os.path.exists(txt_path):
                os.makedirs(academic_beats_dir, exist_ok=True)
                with open(txt_path, "w", encoding="utf-8") as f:
                    for b in beats_array:
                        f.write(f"{b:.4f}\n")
            tracks.append((track_id, audio_path, txt_path))

    # 4. Natural Suite (Legacy Studio-Quantized Grid)
    if suite == "natural":
        natural_dir = os.path.join(repo_root, "benchmarks", "ground_truth", "natural")
        mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")

        if os.path.exists(natural_dir):
            for f in sorted(os.listdir(natural_dir)):
                if f.endswith(".beats.txt"):
                    track_name = f.replace(".beats.txt", "")
                    beats_file = os.path.join(natural_dir, f)

                    # Look for corresponding audio file in assets/musics/mp3_files
                    audio_cand1 = os.path.join(mp3_dir, f"{track_name}.mp3")
                    audio_cand2 = os.path.join(mp3_dir, f"{track_name}.m4a")

                    audio_file = None
                    if os.path.exists(audio_cand1):
                        audio_file = audio_cand1
                    elif os.path.exists(audio_cand2):
                        audio_file = audio_cand2
                    else:
                        for mp3_f in os.listdir(mp3_dir):
                            if mp3_f.startswith(track_name) and mp3_f.endswith((".mp3", ".m4a")):
                                audio_file = os.path.join(mp3_dir, mp3_f)
                                break

                    if audio_file and os.path.exists(audio_file):
                        tracks.append((track_name, audio_file, beats_file))

    return tracks


def format_scorecard_table(track_results: Dict[str, Any]) -> str:
    """Formats a clean terminal scorecard table."""
    lines = []
    lines.append("=" * 105)
    lines.append(f"{'Track Name':<32} {'F1@50ms':<9} {'CMLt':<8} {'AMLt':<8} {'UpbeatGap':<11} {'Bias(ms)':<10} {'Jitter(ms)':<11} {'CPU(ms)':<8}")
    lines.append("-" * 105)

    f1_50_list = []
    cmlt_list = []
    amlt_list = []
    upbeat_gap_list = []
    jitter_list = []
    cpu_list = []

    for name, data in track_results.items():
        sc = data["scorecard"]
        f1_50_list.append(sc["f1_50ms"])
        cmlt_list.append(sc["cmlt"])
        amlt_list.append(sc["amlt"])
        upbeat_gap_list.append(sc["upbeat_gap"])
        jitter_list.append(sc["phase_jitter_ms"])
        cpu_list.append(sc["avg_frame_time_ms"])

        lines.append(
            f"{name[:31]:<32} "
            f"{sc['f1_50ms']*100:>6.1f}%  "
            f"{sc['cmlt']*100:>5.1f}%  "
            f"{sc['amlt']*100:>5.1f}%  "
            f"{sc['upbeat_gap']:>9.2f}  "
            f"{sc['mean_phase_bias_ms']:>+8.1f}  "
            f"{sc['phase_jitter_ms']:>9.1f}  "
            f"{sc['avg_frame_time_ms']:>6.2f}"
        )

    lines.append("-" * 105)
    if f1_50_list:
        lines.append(
            f"{'MACRO AVERAGE':<32} "
            f"{np.mean(f1_50_list)*100:>6.1f}%  "
            f"{np.mean(cmlt_list)*100:>5.1f}%  "
            f"{np.mean(amlt_list)*100:>5.1f}%  "
            f"{np.mean(upbeat_gap_list):>9.2f}  "
            f"{'--':>8}  "
            f"{np.mean(jitter_list):>9.1f}  "
            f"{np.mean(cpu_list):>6.2f}"
        )
    lines.append("=" * 105)
    return "\n".join(lines)


def update_leaderboard(
    leaderboard_path: str,
    run_id: str,
    model_name: str,
    git_commit: str,
    macro_scores: Dict[str, float]
) -> None:
    """Appends benchmark results to experiments/LEADERBOARD.md."""
    os.makedirs(os.path.dirname(leaderboard_path), exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    header = (
        "# 🏆 Vialactée Music Analyzer Leaderboard\n\n"
        "| Date | Run ID | Model Name | Commit | F1@50ms | CMLt | AMLt | Upbeat Gap | Avg Jitter | CPU/frame |\n"
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    )

    if not os.path.exists(leaderboard_path) or os.path.getsize(leaderboard_path) == 0:
        with open(leaderboard_path, "w", encoding="utf-8") as f:
            f.write(header)

    row = (
        f"| {today} "
        f"| `{run_id}` "
        f"| **{model_name}** "
        f"| `{git_commit}` "
        f"| **{macro_scores.get('f1_50ms', 0)*100:.1f}%** "
        f"| {macro_scores.get('cmlt', 0)*100:.1f}% "
        f"| {macro_scores.get('amlt', 0)*100:.1f}% "
        f"| {macro_scores.get('upbeat_gap', 0):.2f} "
        f"| {macro_scores.get('jitter_ms', 0):.1f}ms "
        f"| {macro_scores.get('cpu_ms', 0):.2f}ms |\n"
    )

    with open(leaderboard_path, "a", encoding="utf-8") as f:
        f.write(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vialactée Beat Tracker Benchmark Harness")
    parser.add_argument(
        "--suite",
        choices=["synthetic", "neural", "academic", "natural", "all"],
        default="synthetic",
        help="Benchmark track suite (synthetic, neural, academic, or all)"
    )
    parser.add_argument("--track", type=str, default="", help="Filter specific track by substring name")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tracks evaluated")
    parser.add_argument("--model", type=str, default="AudioAnalyzer", help="Model class to evaluate")
    parser.add_argument("--save-run", action="store_true", help="Record experiment to experiments/runs and LEADERBOARD.md")
    parser.add_argument("--name", type=str, default="", help="Custom experiment tag")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Select model class
    if args.model == "AudioAnalyzer":
        model_class = AudioAnalyzer
    else:
        raise NotImplementedError(f"Custom model loader for {args.model} not implemented yet.")

    tracks = discover_tracks(args.suite, repo_root)
    if args.track:
        tracks = [t for t in tracks if args.track.lower() in t[0].lower()]
    if args.limit > 0:
        tracks = tracks[: args.limit]

    if not tracks:
        print(f"No tracks found matching suite='{args.suite}' and track='{args.track}'!")
        return

    print(f"\n🚀 Running Benchmark on {len(tracks)} tracks [Model: {args.model}, Suite: {args.suite}]...\n")

    track_results: Dict[str, Any] = {}
    all_episodes: List[Dict[str, Any]] = []

    for name, audio_path, beats_path in tracks:
        print(f"  --> Simulating {name}...")
        res = run_benchmark_on_track(model_class, audio_path, beats_path)
        track_results[name] = res

        # Slicing failure episodes
        episodes = extract_failure_episodes(
            song_name=name,
            true_beats=res["true_beats"],
            est_beats=res["est_beats"],
            telemetry=res["telemetry"],
            scorecard=res["scorecard"]
        )
        all_episodes.extend(episodes)

    # Print scorecard
    table_str = format_scorecard_table(track_results)
    print("\n" + table_str)

    # Compute macro averages
    f1_list = [d["scorecard"]["f1_50ms"] for d in track_results.values()]
    cmlt_list = [d["scorecard"]["cmlt"] for d in track_results.values()]
    amlt_list = [d["scorecard"]["amlt"] for d in track_results.values()]
    gap_list = [d["scorecard"]["upbeat_gap"] for d in track_results.values()]
    jitter_list = [d["scorecard"]["phase_jitter_ms"] for d in track_results.values()]
    cpu_list = [d["scorecard"]["avg_frame_time_ms"] for d in track_results.values()]

    macro_scores = {
        "f1_50ms": float(np.mean(f1_list)) if f1_list else 0.0,
        "cmlt": float(np.mean(cmlt_list)) if cmlt_list else 0.0,
        "amlt": float(np.mean(amlt_list)) if amlt_list else 0.0,
        "upbeat_gap": float(np.mean(gap_list)) if gap_list else 0.0,
        "jitter_ms": float(np.mean(jitter_list)) if jitter_list else 0.0,
        "cpu_ms": float(np.mean(cpu_list)) if cpu_list else 0.0,
    }

    if all_episodes:
        print(f"\n⚠️  Extracted {len(all_episodes)} Failure Episodes for AI Pattern Mining:")
        for ep in all_episodes[:5]:
            print(f"   [{ep['failure_type']}] {ep['song']}: {ep['diagnostic']}")
        if len(all_episodes) > 5:
            print(f"   ... and {len(all_episodes) - 5} more.")

    # Save run to experiments ledger
    if args.save_run:
        tag = f"_{args.name}" if args.name else ""
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.model}{tag}"
        run_dir = os.path.join(repo_root, "experiments", "runs", run_id)
        os.makedirs(run_dir, exist_ok=True)

        # 1. Manifest
        manifest = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "git_commit": get_git_commit(),
            "model": args.model,
            "suite": args.suite,
            "macro_scores": macro_scores,
        }
        with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 2. Scorecard
        scorecards = {k: v["scorecard"] for k, v in track_results.items()}
        with open(os.path.join(run_dir, "scorecard.json"), "w", encoding="utf-8") as f:
            json.dump(scorecards, f, indent=2)

        # 3. Failure Episodes for AI
        with open(os.path.join(run_dir, "failure_episodes.json"), "w", encoding="utf-8") as f:
            json.dump(all_episodes, f, indent=2)

        # 4. Telemetry Archive (Compressed npz)
        telemetry_pack = {k: v["telemetry"] for k, v in track_results.items()}
        np.savez_compressed(os.path.join(run_dir, "telemetry.npz"), **telemetry_pack)

        # 5. Update Leaderboard
        leaderboard_file = os.path.join(repo_root, "experiments", "LEADERBOARD.md")
        update_leaderboard(
            leaderboard_path=leaderboard_file,
            run_id=run_id,
            model_name=args.model,
            git_commit=manifest["git_commit"],
            macro_scores=macro_scores
        )
        print(f"\n✅ Experiment saved to {run_dir}")
        print(f"✅ Leaderboard updated in {leaderboard_file}")


if __name__ == "__main__":
    main()
