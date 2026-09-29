"""
research/benchmarks/run_benchmark.py - CLI Runner for the Vialactée Beat Tracking Benchmark Suite.

Usage:
    python -m research.benchmarks.run_benchmark --suite synthetic --save-run
    python -m research.benchmarks.run_benchmark --suite neural-core --save-run
    python -m research.benchmarks.run_benchmark --model AudioAnalyzer --suite neural-core
    python -m research.benchmarks.run_benchmark --suite neural-core --genre funk
    python -m research.benchmarks.run_benchmark --param high_snap_ratio=0.40 --param human_prior_center=120.0
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
import traceback
import importlib.util
from datetime import datetime
from typing import Dict, Any, List, Tuple, Type, Optional
import numpy as np

from core.AudioAnalyzer import AudioAnalyzer
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.RhythmConfig import RhythmConfig
from research.benchmarks.engine.evaluator import run_benchmark_on_track
from research.benchmarks.engine.episode_slicer import extract_failure_episodes
from research.benchmarks.ground_truth.synthetic.generator import generate_all_synthetic_tracks


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


def load_music_catalog(repo_root: str) -> Dict[str, Any]:
    """Loads musical taxonomy metadata from music_catalog.json if present."""
    catalog_path = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "music_catalog.json")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_model_class(model_name: str, repo_root: str) -> Type[BaseAudioAnalyzer]:
    """
    Dynamically discovers and loads any model subclassing BaseAudioAnalyzer.
    Looks in core.AudioAnalyzer and research/experiments/models/*.py.
    """
    if model_name == "AudioAnalyzer":
        return AudioAnalyzer
    if model_name in ("MultiBandOnsetAudioAnalyzer", "production"):
        from core.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer
        return MultiBandOnsetAudioAnalyzer

    models_dir = os.path.join(repo_root, "research", "experiments", "models")
    discovered_classes: Dict[str, Type[BaseAudioAnalyzer]] = {}

    if os.path.exists(models_dir):
        for fname in sorted(os.listdir(models_dir)):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(models_dir, fname)
                mod_name = f"research.experiments.models.{fname[:-3]}"
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, fpath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[mod_name] = module
                        spec.loader.exec_module(module)
                        for attr_name in dir(module):
                            obj = getattr(module, attr_name)
                            if (
                                isinstance(obj, type)
                                and issubclass(obj, BaseAudioAnalyzer)
                                and obj is not BaseAudioAnalyzer
                            ):
                                discovered_classes[attr_name.lower()] = obj
                                discovered_classes[attr_name] = obj
                except Exception as e:
                    print(f"⚠️  Warning: Failed to import model module {fname}: {e}")

    if model_name in discovered_classes:
        return discovered_classes[model_name]
    elif model_name.lower() in discovered_classes:
        return discovered_classes[model_name.lower()]

    available = sorted(set([k for k in discovered_classes.keys() if not k.islower()]))
    raise ValueError(
        f"Model class '{model_name}' not found. Available models in research/experiments/models: {available}"
    )


def build_rhythm_config(
    config_path: Optional[str] = None,
    param_overrides: Optional[List[str]] = None
) -> RhythmConfig:
    """Builds a RhythmConfig with optional JSON config and CLI key=value overrides."""
    cfg = RhythmConfig()

    if config_path:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
            else:
                print(f"⚠️  Warning: Unknown config field '{k}' in {config_path}")

    if param_overrides:
        for item in param_overrides:
            if "=" in item:
                k, v = item.split("=", 1)
            elif ":" in item:
                k, v = item.split(":", 1)
            else:
                continue
            k = k.strip()
            v = v.strip()
            if hasattr(cfg, k):
                orig_val = getattr(cfg, k)
                target_type = type(orig_val)
                if target_type == bool:
                    cast_v = v.lower() in ("true", "1", "yes", "on")
                elif target_type in (int, float):
                    cast_v = target_type(v)
                else:
                    cast_v = v
                setattr(cfg, k, cast_v)
                print(f"🔧 Overrode param {k} = {cast_v} ({target_type.__name__})")
            else:
                print(f"⚠️  Warning: Unknown param '{k}' ignored.")

    return cfg


def discover_tracks(
    suite: str,
    repo_root: str,
    genre: str = "",
    meter: str = "",
    character: str = ""
) -> List[Tuple[str, str, str]]:
    """
    Finds audio and ground truth files for the chosen suite with optional musical filters.
    Returns: List of (track_name, audio_path, beats_path)
    """
    tracks: List[Tuple[str, str, str]] = []
    catalog = load_music_catalog(repo_root)

    # 1. Synthetic Suite
    if suite in ("synthetic", "all"):
        synth_cache = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "synthetic_cache")
        os.makedirs(synth_cache, exist_ok=True)
        generate_all_synthetic_tracks(synth_cache)

        for f in sorted(os.listdir(synth_cache)):
            if f.endswith(".wav"):
                track_name = f.replace(".wav", "")
                beats_file = os.path.join(synth_cache, f"{track_name}.beats.txt")
                wav_file = os.path.join(synth_cache, f)
                if os.path.exists(beats_file):
                    tracks.append((track_name, wav_file, beats_file))

    # 2. Neural Ground Truth Suites (neural and neural-core)
    if suite in ("neural", "neural-core", "neural_core", "all"):
        neural_dir = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "neural")
        mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")

        # Check for curated neural-core list
        allowed_names: Optional[set[str]] = None
        if suite in ("neural-core", "neural_core"):
            core_path = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "neural_core.json")
            if os.path.exists(core_path):
                with open(core_path, "r", encoding="utf-8") as f:
                    allowed_names = set(json.load(f))

        if os.path.exists(neural_dir):
            for f in sorted(os.listdir(neural_dir)):
                if f.endswith(".beats.txt"):
                    track_name = f.replace(".beats.txt", "")
                    if allowed_names is not None and track_name not in allowed_names:
                        continue

                    beats_file = os.path.join(neural_dir, f)
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
        from research.benchmarks.ground_truth.academic.loader import load_academic_tracks
        academic_tracks = load_academic_tracks("ballroom", require_audio=True)
        academic_beats_dir = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "academic", "ballroom")
        for track_id, audio_path, beats_array in academic_tracks:
            txt_path = os.path.join(academic_beats_dir, f"{track_id}.beats.txt")
            if not os.path.exists(txt_path):
                os.makedirs(academic_beats_dir, exist_ok=True)
                with open(txt_path, "w", encoding="utf-8") as f:
                    for b in beats_array:
                        f.write(f"{b:.4f}\n")
            tracks.append((track_id, audio_path, txt_path))

    # Apply musical taxonomy filters
    if genre:
        tracks = [
            t for t in tracks
            if genre.lower() in catalog.get(t[0], {}).get("genre", "").lower()
        ]
    if meter:
        tracks = [
            t for t in tracks
            if meter.lower() in catalog.get(t[0], {}).get("meter", "").lower()
        ]
    if character:
        tracks = [
            t for t in tracks
            if character.lower() in catalog.get(t[0], {}).get("tempo_character", "").lower()
        ]

    return tracks


def format_scorecard_table(track_results: Dict[str, Any]) -> str:
    """Formats a clean terminal scorecard table including Rhythmic Salience metrics."""
    lines = []
    lines.append("=" * 115)
    lines.append(f"{'Track Name':<28} {'F1@50ms':<8} {'F1_Salient':<11} {'CMLt':<7} {'AMLt':<7} {'UpbeatGap':<10} {'Jitter':<9} {'TrustCal':<9} {'CPU(ms)':<8}")
    lines.append("-" * 115)

    f1_50_list = []
    f1_sal_list = []
    cmlt_list = []
    amlt_list = []
    upbeat_gap_list = []
    jitter_list = []
    cal_list = []
    cpu_list = []

    for name, data in track_results.items():
        sc = data["scorecard"]
        if sc.get("crashed", False):
            lines.append(f"{name[:27]:<28} {'💥 CRASHED':<8} {'--':<11} {'--':<7} {'--':<7} {'--':<10} {'--':<9} {'--':<9} {'--':<8}")
            continue

        f1_50_list.append(sc["f1_50ms"])
        f1_sal = sc.get("f1_salient_50ms", sc["f1_50ms"])
        f1_sal_list.append(f1_sal)
        cmlt_list.append(sc["cmlt"])
        amlt_list.append(sc["amlt"])
        upbeat_gap_list.append(sc["upbeat_gap"])
        jitter_list.append(sc["phase_jitter_ms"])
        cal_list.append(sc.get("bpm_trust_calibration", 0.0))
        cpu_list.append(sc["avg_frame_time_ms"])

        cal_str = f"{sc.get('bpm_trust_calibration', 0.0):>+6.2f}" if sc.get("bpm_trust_calibration") is not None else "  --  "

        lines.append(
            f"{name[:27]:<28} "
            f"{sc['f1_50ms']*100:>5.1f}%  "
            f"{f1_sal*100:>7.1f}%    "
            f"{sc['cmlt']*100:>5.1f}%  "
            f"{sc['amlt']*100:>5.1f}%  "
            f"{sc['upbeat_gap']:>8.2f}  "
            f"{sc['phase_jitter_ms']:>6.1f}ms  "
            f"{cal_str:>7}  "
            f"{sc['avg_frame_time_ms']:>6.2f}"
        )

    lines.append("-" * 115)
    if f1_50_list:
        lines.append(
            f"{'MACRO AVERAGE':<28} "
            f"{np.mean(f1_50_list)*100:>5.1f}%  "
            f"{np.mean(f1_sal_list)*100:>7.1f}%    "
            f"{np.mean(cmlt_list)*100:>5.1f}%  "
            f"{np.mean(amlt_list)*100:>5.1f}%  "
            f"{np.mean(upbeat_gap_list):>8.2f}  "
            f"{np.mean(jitter_list):>6.1f}ms  "
            f"{np.mean(cal_list):>+7.2f}  "
            f"{np.mean(cpu_list):>6.2f}"
        )
    lines.append("=" * 115)
    return "\n".join(lines)


def format_genre_breakdown_table(track_results: Dict[str, Any], catalog: Dict[str, Any]) -> str:
    """Formats performance breakdown by musical genre."""
    if not catalog:
        return ""

    genre_data: Dict[str, List[Dict[str, Any]]] = {}
    for name, data in track_results.items():
        if data["scorecard"].get("crashed", False):
            continue
        genre = catalog.get(name, {}).get("genre", "Other / Uncategorized")
        genre_data.setdefault(genre, []).append(data["scorecard"])

    if not genre_data:
        return ""

    lines = []
    lines.append("\n" + "=" * 90)
    lines.append("🎼 GENRE & MUSICAL STYLE PERFORMANCE BREAKDOWN")
    lines.append("=" * 90)
    lines.append(f"{'Musical Genre':<32} {'Tracks':<8} {'F1@50ms':<10} {'CMLt':<9} {'AMLt':<9} {'UpbeatGap':<11} {'Jitter':<9}")
    lines.append("-" * 90)

    for genre, cards in sorted(genre_data.items()):
        f1_m = np.mean([c["f1_50ms"] for c in cards]) * 100.0
        cmlt_m = np.mean([c["cmlt"] for c in cards]) * 100.0
        amlt_m = np.mean([c["amlt"] for c in cards]) * 100.0
        gap_m = np.mean([c["upbeat_gap"] for c in cards])
        jit_m = np.mean([c["phase_jitter_ms"] for c in cards])

        lines.append(
            f"{genre[:31]:<32} "
            f"{len(cards):<8} "
            f"{f1_m:>6.1f}%   "
            f"{cmlt_m:>5.1f}%   "
            f"{amlt_m:>5.1f}%   "
            f"{gap_m:>9.2f}   "
            f"{jit_m:>6.1f}ms"
        )

    lines.append("=" * 90)
    return "\n".join(lines)


def update_leaderboard(
    leaderboard_path: str,
    run_id: str,
    suite: str,
    model_name: str,
    git_commit: str,
    macro_scores: Dict[str, float]
) -> None:
    """Appends benchmark results to experiments/LEADERBOARD.md with Suite column."""
    os.makedirs(os.path.dirname(leaderboard_path), exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    header = (
        "# 🏆 Vialactée Music Analyzer Leaderboard\n\n"
        "| Date | Run ID | Suite | Model Name | Commit | F1@50ms | CMLt | AMLt | Upbeat Gap | Avg Jitter | CPU/frame |\n"
        "| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    )

    if not os.path.exists(leaderboard_path) or os.path.getsize(leaderboard_path) == 0:
        with open(leaderboard_path, "w", encoding="utf-8") as f:
            f.write(header)

    row = (
        f"| {today} "
        f"| `{run_id}` "
        f"| `{suite}` "
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
        choices=["synthetic", "neural", "neural-core", "neural_core", "academic", "all"],
        default="synthetic",
        help="Benchmark track suite (synthetic, neural-core, neural, academic, or all)"
    )
    parser.add_argument("--track", type=str, default="", help="Filter specific track by substring name")
    parser.add_argument("--genre", type=str, default="", help="Filter by musical genre (e.g. funk, electronic, rock, chanson)")
    parser.add_argument("--meter", type=str, default="", help="Filter by meter (e.g. 4/4, 3/4)")
    parser.add_argument("--character", type=str, default="", help="Filter by tempo character (e.g. quantized, drift)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tracks evaluated")
    parser.add_argument("--model", type=str, default="AudioAnalyzer", help="Model class to evaluate (AudioAnalyzer or candidate class)")
    parser.add_argument("--config", type=str, default="", help="Path to JSON config overrides for RhythmConfig")
    parser.add_argument("--param", action="append", help="Inline parameter override: key=value (e.g. --param high_snap_ratio=0.4)")
    parser.add_argument("--save-run", action="store_true", help="Record experiment to experiments/runs and LEADERBOARD.md")
    parser.add_argument("--name", type=str, default="", help="Custom experiment tag")
    args = parser.parse_args()

    research_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    repo_root = os.path.abspath(os.path.join(research_root, ".."))

    # Select model class via dynamic auto-discovery
    model_class = load_model_class(args.model, repo_root)

    # Build RhythmConfig with hyperparameter overrides
    config = build_rhythm_config(config_path=args.config if args.config else None, param_overrides=args.param)

    # Load musical catalog & discover tracks
    catalog = load_music_catalog(repo_root)
    tracks = discover_tracks(
        suite=args.suite,
        repo_root=repo_root,
        genre=args.genre,
        meter=args.meter,
        character=args.character
    )

    if args.track:
        tracks = [t for t in tracks if args.track.lower() in t[0].lower()]
    if args.limit > 0:
        tracks = tracks[: args.limit]

    if not tracks:
        print(f"No tracks found matching suite='{args.suite}' and filters [track='{args.track}', genre='{args.genre}']!")
        return

    print(f"\n🚀 Running Benchmark on {len(tracks)} tracks [Model: {args.model}, Suite: {args.suite}]...\n")

    track_results: Dict[str, Any] = {}
    all_episodes: List[Dict[str, Any]] = []

    for name, audio_path, beats_path in tracks:
        print(f"  --> Simulating {name}...")
        try:
            res = run_benchmark_on_track(model_class, audio_path, beats_path, config=config)
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
        except Exception as e:
            tb = traceback.format_exc()
            print(f"       💥 CRASH during simulation of {name}: {e}")
            track_results[name] = {
                "scorecard": {
                    "f1_50ms": 0.0,
                    "f1_70ms": 0.0,
                    "cmlt": 0.0,
                    "amlt": 0.0,
                    "upbeat_gap": 1.0,
                    "mean_phase_bias_ms": 0.0,
                    "phase_jitter_ms": 999.0,
                    "avg_frame_time_ms": 0.0,
                    "error": str(e),
                    "crashed": True
                },
                "true_beats": np.array([]),
                "est_beats": np.array([]),
                "telemetry": {}
            }
            all_episodes.append({
                "song": name,
                "failure_type": "MODEL_CRASH",
                "start_time": 0.0,
                "end_time": 0.0,
                "duration": 0.0,
                "diagnostic": f"Exception: {e}\n{tb}"
            })

    # Print scorecard
    table_str = format_scorecard_table(track_results)
    print("\n" + table_str)

    # Print Genre Breakdown Table
    genre_table_str = format_genre_breakdown_table(track_results, catalog)
    if genre_table_str:
        print(genre_table_str)

    # Compute macro averages (excluding crashed tracks)
    valid_results = [d for d in track_results.values() if not d["scorecard"].get("crashed", False)]
    f1_list = [d["scorecard"]["f1_50ms"] for d in valid_results]
    f1_sal_list = [d["scorecard"].get("f1_salient_50ms", d["scorecard"]["f1_50ms"]) for d in valid_results]
    cmlt_list = [d["scorecard"]["cmlt"] for d in valid_results]
    amlt_list = [d["scorecard"]["amlt"] for d in valid_results]
    gap_list = [d["scorecard"]["upbeat_gap"] for d in valid_results]
    jitter_list = [d["scorecard"]["phase_jitter_ms"] for d in valid_results]
    cal_list = [d["scorecard"].get("bpm_trust_calibration", 0.0) for d in valid_results]
    cpu_list = [d["scorecard"]["avg_frame_time_ms"] for d in valid_results]

    macro_scores = {
        "f1_50ms": float(np.mean(f1_list)) if f1_list else 0.0,
        "f1_salient_50ms": float(np.mean(f1_sal_list)) if f1_sal_list else 0.0,
        "cmlt": float(np.mean(cmlt_list)) if cmlt_list else 0.0,
        "amlt": float(np.mean(amlt_list)) if amlt_list else 0.0,
        "upbeat_gap": float(np.mean(gap_list)) if gap_list else 0.0,
        "jitter_ms": float(np.mean(jitter_list)) if jitter_list else 0.0,
        "bpm_trust_calibration": float(np.mean(cal_list)) if cal_list else 0.0,
        "cpu_ms": float(np.mean(cpu_list)) if cpu_list else 0.0,
    }

    if all_episodes:
        print(f"\n⚠️  Extracted {len(all_episodes)} Failure Episodes for AI Pattern Mining:")
        for ep in all_episodes[:5]:
            print(f"   [{ep['failure_type']}] {ep['song']}: {ep['diagnostic'][:80]}...")
        if len(all_episodes) > 5:
            print(f"   ... and {len(all_episodes) - 5} more.")

    # Save run to experiments ledger
    if args.save_run:
        tag = f"_{args.name}" if args.name else ""
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.model}{tag}"
        run_dir = os.path.join(research_root, "experiments", "runs", run_id)
        os.makedirs(run_dir, exist_ok=True)

        # 1. Manifest
        manifest = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "git_commit": get_git_commit(),
            "model": args.model,
            "suite": args.suite,
            "config": {k: getattr(config, k) for k in config.__dataclass_fields__},
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
        valid_telemetry = {k: v["telemetry"] for k, v in track_results.items() if v["telemetry"]}
        if valid_telemetry:
            np.savez_compressed(os.path.join(run_dir, "telemetry.npz"), **valid_telemetry)

        # 5. Update Leaderboard
        leaderboard_file = os.path.join(research_root, "experiments", "LEADERBOARD.md")
        update_leaderboard(
            leaderboard_path=leaderboard_file,
            run_id=run_id,
            suite=args.suite,
            model_name=args.model,
            git_commit=manifest["git_commit"],
            macro_scores=macro_scores
        )
        print(f"\n✅ Experiment saved to {run_dir}")
        print(f"✅ Leaderboard updated in {leaderboard_file}")


if __name__ == "__main__":
    main()
