"""
research/benchmarks/ground_truth/cache_audio_arrays.py

Pre-computes and caches float32 mono audio arrays (.npz) at 44.1 kHz for all
tracks in assets/musics/mp3_files/ into assets/musics/mp3_files/librosa/.
Eliminates the 10-20s MP3 decoding overhead on Windows during benchmark runs.
"""

from __future__ import annotations
import os
import sys
import time
import argparse
from typing import Optional, Tuple
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_raw_audio(audio_path: str, target_sr: int = 44100) -> Tuple[np.ndarray, int]:
    """Loads audio using torchaudio (fastest) or librosa fallback."""
    # Attempt torchaudio first
    try:
        import torchaudio
        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
            waveform = resampler(waveform)
        return waveform.numpy().flatten().astype(np.float32), target_sr
    except Exception:
        pass

    # Fallback to librosa
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
        return y.astype(np.float32), target_sr
    except Exception as e:
        raise RuntimeError(f"Failed to decode {audio_path}: {e}")


def cache_all_tracks(mp3_dir: str, force: bool = False, limit: int = 0) -> None:
    librosa_dir = os.path.join(mp3_dir, "librosa")
    os.makedirs(librosa_dir, exist_ok=True)

    candidates = [
        f for f in sorted(os.listdir(mp3_dir))
        if f.endswith((".mp3", ".m4a")) and not os.path.isdir(os.path.join(mp3_dir, f))
    ]

    if limit > 0:
        candidates = candidates[:limit]

    print(f"🔍 Discovered {len(candidates)} audio tracks in {mp3_dir}")
    print(f"📁 Target cache directory: {librosa_dir}\n")

    cached_count = 0
    skipped_count = 0
    failed_count = 0

    for i, fname in enumerate(candidates, start=1):
        target_npz = os.path.join(librosa_dir, f"{fname}.npz")
        audio_path = os.path.join(mp3_dir, fname)

        if not force and os.path.exists(target_npz):
            try:
                data = np.load(target_npz, allow_pickle=True)
                if "y" in data:
                    skipped_count += 1
                    print(f"[{i}/{len(candidates)}] ⏩ Already cached: {fname}")
                    continue
            except Exception:
                pass

        print(f"[{i}/{len(candidates)}] ⏳ Decoding & caching: {fname}...")
        t0 = time.time()
        try:
            y, sr = load_raw_audio(audio_path, target_sr=44100)
            np.savez_compressed(target_npz, y=y, sr=sr)
            elapsed = time.time() - t0
            size_mb = os.path.getsize(target_npz) / (1024 * 1024)
            print(f"       ✅ Cached in {elapsed:.2f}s ({size_mb:.1f} MB)")
            cached_count += 1
        except Exception as e:
            print(f"       ❌ Failed to cache {fname}: {e}")
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"🎉 Caching Summary: {cached_count} newly cached, {skipped_count} skipped, {failed_count} failed.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Audio Array Pre-Caching Utility")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .npz files")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tracks to cache")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
    cache_all_tracks(mp3_dir, force=args.force, limit=args.limit)


if __name__ == "__main__":
    main()
