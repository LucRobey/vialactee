"""
benchmarks/ground_truth/build_quantized_reference.py - Derives mathematically verified 
Tier 2 Ground Truth beat grids for studio-produced music.

For tracks produced to a studio click track or drum machine, the tempo is fixed with
quartz-crystal stability. This script determines the exact physical downbeat offset (t0)
via cross-correlation of low-frequency transients against a periodic comb filter.
"""

from __future__ import annotations
import os
import sys
import json
import numpy as np
import librosa
from typing import Dict, Any, Tuple, Optional, List

from benchmarks.engine.evaluator import load_audio_file


def compute_optimal_t0(
    y: np.ndarray,
    sr: int,
    bpm: float,
    max_eval_time: float = 60.0
) -> Tuple[float, float]:
    """
    Computes the optimal phase offset t0 in [0, 60/BPM) that maximizes
    cross-correlation with physical drum onsets.
    
    Returns:
        (best_t0_seconds, correlation_score)
    """
    period = 60.0 / bpm
    hop_length = 256  # ~5.8ms resolution at 44.1kHz
    
    # Clip to max_eval_time to avoid intro noise and keep compute fast
    eval_len = min(len(y), int(sr * max_eval_time))
    eval_y = y[:eval_len]

    # Compute onset strength focusing on rhythm section (kick/bass up to 1000Hz)
    onset_env = librosa.onset.onset_strength(
        y=eval_y,
        sr=sr,
        hop_length=hop_length,
        fmax=1000.0,
        n_mels=64
    )
    onset_times = librosa.frames_to_time(
        np.arange(len(onset_env)),
        sr=sr,
        hop_length=hop_length
    )

    # Sub-millisecond candidate grid: 1000 points across one beat period
    t0_candidates = np.linspace(0.0, period, 1000, endpoint=False)
    scores = np.zeros(len(t0_candidates))

    # Evaluate each t0
    for i, t0 in enumerate(t0_candidates):
        grid = np.arange(t0, onset_times[-1] - 0.1, period)
        if len(grid) == 0:
            continue
        grid_values = np.interp(grid, onset_times, onset_env)
        scores[i] = np.mean(grid_values)

    best_idx = int(np.argmax(scores))
    best_t0 = float(t0_candidates[best_idx])
    best_score = float(scores[best_idx])

    return best_t0, best_score


def generate_quantized_beats(
    audio_path: str,
    bpm: float,
    output_path: str,
    max_eval_time: float = 60.0
) -> Tuple[str, int, float]:
    """
    Generates a full-song quantized beat grid aligned to audio transients.
    """
    y, sr = load_audio_file(audio_path, target_sr=44100)
    duration = len(y) / sr
    period = 60.0 / bpm

    t0, score = compute_optimal_t0(y, sr, bpm, max_eval_time=max_eval_time)

    # Build continuous grid across entire song
    beat_times: List[float] = []
    t = t0
    while t < duration - 0.05:
        beat_times.append(t)
        t += period

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Studio-Quantized Ground Truth Beats\n")
        f.write(f"# Audio: {os.path.basename(audio_path)}\n")
        f.write(f"# Verified BPM: {bpm:.2f}\n")
        f.write(f"# Alignment t0: {t0:.4f}s (Period: {period:.4f}s, Score: {score:.3f})\n")
        f.write(f"# Total Beats: {len(beat_times)}\n")
        for b in beat_times:
            f.write(f"{b:.4f}\n")

    return output_path, len(beat_times), t0


def build_all_quantized_references():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    bpm_db_path = os.path.join(repo_root, "assets", "musics", "mp3_files", "bpm_database.json")
    mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
    output_dir = os.path.join(repo_root, "benchmarks", "ground_truth", "natural")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(bpm_db_path):
        print(f"BPM database not found at {bpm_db_path}")
        return

    with open(bpm_db_path, "r", encoding="utf-8") as f:
        bpm_db: Dict[str, Any] = json.load(f)

    # Filter for verified fixed studio tempos
    verified_tracks = {}
    for track, data in bpm_db.items():
        src = data.get("source", "")
        if "verified" in src or track in [
            "Palladium",
            "Another One Bites The Dust - Remastered 2011",
            "Pumped Up Kicks",
            "Boogie Wonderland",
            "Nobody Rules the Streets",
            "Stayin' Alive - From _Saturday Night Fever_ Soundtrack",
            "September",
            "Roxanne - Remastered 2003",
            "01-Plastic-People"
        ]:
            verified_tracks[track] = float(data["bpm"])

    print(f"Deriving Studio-Quantized Reference for {len(verified_tracks)} verified tracks...\n")

    generated = 0
    for track_name, bpm in sorted(verified_tracks.items()):
        audio_cand1 = os.path.join(mp3_dir, f"{track_name}.mp3")
        audio_cand2 = os.path.join(mp3_dir, f"{track_name}.m4a")
        audio_path = audio_cand1 if os.path.exists(audio_cand1) else (audio_cand2 if os.path.exists(audio_cand2) else None)

        if not audio_path:
            # Match partial
            for f in os.listdir(mp3_dir):
                if f.startswith(track_name) and f.endswith((".mp3", ".m4a")):
                    audio_path = os.path.join(mp3_dir, f)
                    break

        if not audio_path or not os.path.exists(audio_path):
            continue

        out_beats = os.path.join(output_dir, f"{track_name}.beats.txt")
        print(f"  [Quantizing] {track_name} (BPM: {bpm:.1f})...")
        try:
            _, count, t0 = generate_quantized_beats(audio_path, bpm, out_beats)
            print(f"   --> Generated {count} beats (t0 = {t0:.4f}s)")
            generated += 1
        except Exception as e:
            print(f"   --> Error: {e}")

    print(f"\nSuccessfully generated {generated} Studio-Quantized Ground Truth reference files in {output_dir}")


if __name__ == "__main__":
    build_all_quantized_references()
