"""
research/benchmarks/ground_truth/extract_beat_salience.py - Ground Truth Beat Importance Extractor.

Extracts objective Rhythmic Salience & Beat Importance ground-truth data for benchmark tracks:
1. Computes continuous Beat Importance curve S(t) in [0.0, 1.0].
2. Interpolates importance weights w_i for every reference beat in <track>.beats.txt.
3. Saves <track>.salience.npz alongside beats in research/benchmarks/ground_truth/neural/.
4. Updates <track>.meta.json with salience statistics (mean_salience, high_salience_ratio).

Usage:
    python -m research.benchmarks.ground_truth.extract_beat_salience --core-only
    python -m research.benchmarks.ground_truth.extract_beat_salience --track "Sweet Child O' Mine"
    python -m research.benchmarks.ground_truth.extract_beat_salience --all
"""

from __future__ import annotations
import os
import sys

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import argparse
import time
import numpy as np
from typing import List, Dict, Any, Optional

from research.benchmarks.plot_beat_salience import compute_beat_importance
from research.benchmarks.engine.evaluator import load_beats_file


def extract_salience_for_track(
    track_name: str,
    audio_path: str,
    beats_path: str,
    output_dir: str,
    skip_existing: bool = False
) -> Dict[str, Any]:
    """
    Computes and saves salience ground truth (.salience.npz) and updates .meta.json for a single track.
    """
    safe_name = track_name
    npz_out = os.path.join(output_dir, f"{safe_name}.salience.npz")
    meta_out = os.path.join(output_dir, f"{safe_name}.meta.json")

    if skip_existing and os.path.exists(npz_out):
        print(f"  [Salience Ground Truth] Skipping '{track_name}' (already exists)")
        if os.path.exists(meta_out):
            with open(meta_out, "r", encoding="utf-8") as f:
                return json.load(f)

    print(f"  [Salience Ground Truth] Processing '{track_name}'...")
    t0 = time.time()

    # 1. Compute continuous Beat Importance curve S(t)
    data = compute_beat_importance(audio_path)
    timeline = data["times"]
    salience_curve = data["salience"]
    duration = data["duration"]

    # 2. Load ground truth reference beats
    true_beats = load_beats_file(beats_path) if os.path.exists(beats_path) else np.array([])

    # 3. Sample importance weights at each beat timestamp
    if len(true_beats) > 0:
        beat_weights = np.interp(true_beats, timeline, salience_curve)
    else:
        beat_weights = np.array([])

    # 4. Save to companion .salience.npz
    np.savez_compressed(
        npz_out,
        times=timeline.astype(np.float32),
        salience_curve=salience_curve.astype(np.float32),
        beat_times=true_beats.astype(np.float64),
        beat_weights=beat_weights.astype(np.float32)
    )

    # 5. Compute statistics
    mean_salience = float(np.mean(salience_curve)) if len(salience_curve) > 0 else 0.0
    high_salience_ratio = float(np.mean(salience_curve >= 0.60)) if len(salience_curve) > 0 else 0.0
    low_salience_ratio = float(np.mean(salience_curve < 0.25)) if len(salience_curve) > 0 else 0.0

    # 6. Update .meta.json
    meta = {}
    if os.path.exists(meta_out):
        try:
            with open(meta_out, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    meta["salience_data"] = {
        "mean_salience": round(mean_salience, 3),
        "high_salience_ratio": round(high_salience_ratio, 3),
        "low_salience_ratio": round(low_salience_ratio, 3),
        "has_salience_curve": True,
        "salience_npz": os.path.basename(npz_out)
    }

    with open(meta_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t0
    print(f"    ✓ Saved {os.path.basename(npz_out)} in {elapsed:.1f}s | Mean S: {mean_salience:.2f} (Groove: {high_salience_ratio*100:.0f}%, Solo: {low_salience_ratio*100:.0f}%)")

    return meta


def main():
    parser = argparse.ArgumentParser(description="Extract Rhythmic Salience / Beat Importance ground truth.")
    parser.add_argument("--track", type=str, default=None, help="Process single track by name substring")
    parser.add_argument("--core-only", action="store_true", help="Process only the curated 10-track neural-core suite")
    parser.add_argument("--all", action="store_true", help="Process all tracks in neural ground truth directory")
    parser.add_argument("--skip-existing", action="store_true", help="Skip already processed tracks")
    args = parser.parse_args()

    neural_dir = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "neural")
    mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
    core_json = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "neural_core.json")

    allowed_tracks: Optional[set[str]] = None
    if args.core_only and os.path.exists(core_json):
        with open(core_json, "r", encoding="utf-8") as f:
            allowed_tracks = set(json.load(f))
        print(f"🎯 Targeting {len(allowed_tracks)} curated neural-core tracks...")

    # Discover target tracks
    targets: List[str] = []
    if os.path.exists(neural_dir):
        for f in sorted(os.listdir(neural_dir)):
            if f.endswith(".beats.txt"):
                tname = f.replace(".beats.txt", "")
                if args.track and args.track.lower() not in tname.lower():
                    continue
                if allowed_tracks is not None and tname not in allowed_tracks:
                    continue
                targets.append(tname)

    print(f"🚀 Found {len(targets)} tracks to process.")
    for idx, tname in enumerate(targets, 1):
        print(f"\n[{idx}/{len(targets)}] {tname}")
        beats_path = os.path.join(neural_dir, f"{tname}.beats.txt")
        audio_path = None
        for ext in (".mp3", ".wav"):
            cand = os.path.join(mp3_dir, f"{tname}{ext}")
            if os.path.exists(cand):
                audio_path = cand
                break

        if not audio_path:
            print(f"  ⚠️ Warning: Audio file for '{tname}' not found in {mp3_dir}, skipping.")
            continue

        extract_salience_for_track(
            track_name=tname,
            audio_path=audio_path,
            beats_path=beats_path,
            output_dir=neural_dir,
            skip_existing=args.skip_existing
        )

    print(f"\n✨ Ground truth beat importance extraction completed successfully!")


if __name__ == "__main__":
    main()
