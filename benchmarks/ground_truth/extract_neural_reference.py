"""
benchmarks/ground_truth/extract_neural_reference.py - Neural Ground Truth Extractor.

Replaces the naive periodic grid with deep learning joint beat and downbeat tracking
using BeatNet (Heydari et al., ISMIR 2021) with Numba-accelerated DBN inference.
Captures true human micro-timing, expressive swing, downbeats, and tempo dynamics.
"""

from __future__ import annotations
import os
import sys
import json
import time
import argparse
import tempfile
import numpy as np
import soundfile as sf
from typing import List, Dict, Any, Tuple, Optional

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from benchmarks.engine.evaluator import load_audio_file


def extract_track_neural_reference(
    audio_path: str,
    output_dir: str,
    estimator: Optional[Any] = None,
    save_downbeats: bool = True,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Extracts neural ground-truth beats and downbeats for a single audio track.
    
    Returns metadata dictionary with track statistics.
    """
    track_name = os.path.splitext(os.path.basename(audio_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    
    beats_out_path = os.path.join(output_dir, f"{track_name}.beats.txt")
    downbeats_out_path = os.path.join(output_dir, f"{track_name}.downbeats.txt")
    meta_out_path = os.path.join(output_dir, f"{track_name}.meta.json")

    if skip_existing and os.path.exists(beats_out_path) and os.path.exists(meta_out_path):
        print(f"  [Neural Extraction] Skipping '{track_name}' (already exists in {output_dir})")
        with open(meta_out_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Initialize BeatNet if not provided
    if estimator is None:
        from BeatNet.BeatNet import BeatNet
        estimator = BeatNet(1, mode="offline", inference_model="DBN", plot=[], thread=False)

    print(f"  [Neural Extraction] Processing '{track_name}'...")
    t_start = time.time()

    # Load audio using evaluator's cache-aware loader (fast .npz or native decode)
    y, sr = load_audio_file(audio_path, target_sr=22050)
    duration_sec = len(y) / sr

    # Write temporary 22.05kHz mono wav for BeatNet ingestion
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav_path = tmp.name
    
    try:
        sf.write(tmp_wav_path, y, sr, subtype="PCM_16")
        # BeatNet returns (N, 2) array: [time_seconds, beat_number_in_bar]
        output = estimator.process(tmp_wav_path)
    finally:
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)

    elapsed = time.time() - t_start

    if len(output) == 0:
        print(f"    --> WARNING: No beats detected for {track_name}")
        return {"track": track_name, "error": "No beats detected"}

    beat_times = output[:, 0]
    beat_positions = output[:, 1].astype(int)
    downbeat_times = output[beat_positions == 1, 0]

    # Calculate rhythm statistics
    intervals = np.diff(beat_times)
    median_interval = float(np.median(intervals)) if len(intervals) > 0 else 0.5
    estimated_bpm = 60.0 / median_interval if median_interval > 0 else 0.0
    jitter_ms = float(np.std(intervals) * 1000.0) if len(intervals) > 0 else 0.0

    # 1. Write .beats.txt
    with open(beats_out_path, "w", encoding="utf-8") as f:
        f.write(f"# Neural Ground Truth Beats (BeatNet CRNN + DBN)\n")
        f.write(f"# Track: {track_name}\n")
        f.write(f"# Duration: {duration_sec:.2f}s, Estimated BPM: {estimated_bpm:.1f}\n")
        f.write(f"# Total Beats: {len(beat_times)}, Downbeats: {len(downbeat_times)}\n")
        for b in beat_times:
            f.write(f"{b:.4f}\n")

    # 2. Write .downbeats.txt
    if save_downbeats:
        with open(downbeats_out_path, "w", encoding="utf-8") as f:
            f.write(f"# Neural Ground Truth Downbeats (BeatNet CRNN + DBN)\n")
            f.write(f"# Track: {track_name}\n")
            for db in downbeat_times:
                f.write(f"{db:.4f}\n")

    # 3. Write metadata JSON
    meta = {
        "track": track_name,
        "audio_path": audio_path,
        "duration_sec": round(duration_sec, 2),
        "total_beats": int(len(beat_times)),
        "total_downbeats": int(len(downbeat_times)),
        "estimated_bpm": round(estimated_bpm, 2),
        "interval_jitter_ms": round(jitter_ms, 2),
        "compute_time_sec": round(elapsed, 2),
        "generator": "BeatNet 1.1.1 (CRNN + DBN, Numba-accelerated)"
    }
    with open(meta_out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"    --> Found {len(beat_times)} beats ({len(downbeat_times)} downbeats, ~{estimated_bpm:.1f} BPM) in {elapsed:.2f}s")
    return meta


def extract_all_neural_references(
    repo_root: Optional[str] = None,
    track_filter: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False
) -> List[Dict[str, Any]]:
    """
    Extracts neural ground truth for all music files in assets/musics/mp3_files/.
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    mp3_dir = os.path.join(root, "assets", "musics", "mp3_files")
    output_dir = os.path.join(root, "benchmarks", "ground_truth", "neural")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(mp3_dir):
        print(f"Error: Music directory not found at {mp3_dir}")
        return []

    # Initialize model once for entire batch
    from BeatNet.BeatNet import BeatNet
    print("Initializing BeatNet model weights...")
    estimator = BeatNet(1, mode="offline", inference_model="DBN", plot=[], thread=False)

    # Discover eligible audio tracks
    candidates = []
    for fname in sorted(os.listdir(mp3_dir)):
        if fname.endswith((".mp3", ".wav")):
            if track_filter and track_filter.lower() not in fname.lower():
                continue
            candidates.append(os.path.join(mp3_dir, fname))

    if limit and limit > 0:
        candidates = candidates[:limit]

    print(f"Found {len(candidates)} tracks to process into Neural Ground Truth.\n")

    results = []
    for path in candidates:
        try:
            meta = extract_track_neural_reference(
                path,
                output_dir,
                estimator=estimator,
                skip_existing=not force
            )
            results.append(meta)
        except Exception as e:
            print(f"    --> ERROR on {os.path.basename(path)}: {e}")

    # Write batch manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "tracks": results}, f, indent=2)

    print(f"\nCompleted Neural Ground Truth derivation for {len(results)} tracks. Manifest: {manifest_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Neural Ground Truth references using BeatNet")
    parser.add_argument("--track", type=str, default=None, help="Filter by specific track name substring")
    parser.add_argument("--out-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tracks to process")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if files exist")
    args = parser.parse_args()

    extract_all_neural_references(
        track_filter=args.track,
        limit=args.limit if args.limit > 0 else None,
        force=args.force
    )
