"""
benchmarks/ground_truth/academic/loader.py - Tier 3 Academic Dataset Loader via mirdata.

Provides standardized access to academic MIR benchmarks (e.g., Ballroom, Beatles)
for international reproducibility against published literature.
"""

from __future__ import annotations
import os
import sys
import argparse
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

# Configure UTF-8 output encoding for Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_academic_dataset(dataset_name: str = "ballroom", data_home: Optional[str] = None):
    """Initializes and returns a mirdata dataset handle with explicit data_home."""
    try:
        import mirdata
    except ImportError:
        raise ImportError("mirdata is required for Tier 3 academic datasets. Install with `pip install mirdata`.")

    if data_home is None:
        # Default to local cache within repo or user cache
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        data_home = os.path.join(repo_root, "benchmarks", "ground_truth", "academic", "data", dataset_name)
    
    os.makedirs(data_home, exist_ok=True)
    return mirdata.initialize(dataset_name, data_home=data_home)


def load_academic_tracks(
    dataset_name: str = "ballroom",
    limit: Optional[int] = None,
    require_audio: bool = True
) -> List[Tuple[str, Optional[str], np.ndarray]]:
    """
    Discovers and validates academic tracks.
    
    Returns:
        List of (track_id, audio_path, ground_truth_beats_array)
    """
    dataset = get_academic_dataset(dataset_name)
    tracks: List[Tuple[str, Optional[str], np.ndarray]] = []

    try:
        all_tracks = dataset.load_tracks()
    except Exception as e:
        print(f"Warning: Could not load tracks for {dataset_name} ({e}). Ensure index/annotations are downloaded.")
        return []

    count = 0
    for track_id, track in all_tracks.items():
        if limit is not None and count >= limit:
            break

        audio_path = getattr(track, "audio_path", None)
        if require_audio and (not audio_path or not os.path.exists(audio_path)):
            continue

        beats_path = getattr(track, "beats_path", None)
        if not beats_path or not os.path.exists(beats_path):
            continue

        beats_data = getattr(track, "beats", None)
        if beats_data is None or not hasattr(beats_data, "times"):
            continue

        beat_times = np.array(beats_data.times, dtype=np.float64)
        if len(beat_times) < 2:
            continue

        tracks.append((track_id, audio_path, beat_times))
        count += 1

    return tracks


def export_academic_beats_to_txt(
    dataset_name: str = "ballroom",
    output_dir: Optional[str] = None,
    limit: Optional[int] = None
) -> int:
    """
    Exports academic beat annotations into standard .beats.txt format for offline benchmarking.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    out_dir = output_dir or os.path.join(repo_root, "benchmarks", "ground_truth", "academic", dataset_name)
    os.makedirs(out_dir, exist_ok=True)

    tracks = load_academic_tracks(dataset_name, limit=limit, require_audio=False)
    for track_id, audio_path, beat_times in tracks:
        txt_path = os.path.join(out_dir, f"{track_id}.beats.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"# Academic Ground Truth from {dataset_name}\n")
            f.write(f"# Track ID: {track_id}\n")
            f.write(f"# Total Beats: {len(beat_times)}\n")
            for b in beat_times:
                f.write(f"{b:.4f}\n")

    return len(tracks)


def main():
    parser = argparse.ArgumentParser(description="Tier 3 Academic Dataset Manager")
    parser.add_argument("--dataset", type=str, default="ballroom", help="Dataset name in mirdata")
    parser.add_argument("--download-all", action="store_true", help="Download audio and annotations (~1.35GB for ballroom)")
    parser.add_argument("--download-annotations", action="store_true", help="Download beat annotations only (<1MB)")
    parser.add_argument("--download-audio", action="store_true", help="Download audio wav files only")
    parser.add_argument("--export", action="store_true", help="Export all beat annotations to .beats.txt format")
    parser.add_argument("--status", action="store_true", help="Check local readiness of dataset")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tracks")
    args = parser.parse_args()

    ds = get_academic_dataset(args.dataset)

    if args.download_all:
        print(f"Downloading complete {args.dataset} dataset (audio + annotations) via mirdata...")
        ds.download()
    elif args.download_annotations:
        print(f"Downloading {args.dataset} beat annotations and index...")
        ds.download(partial_download=["beats", "tempo"], force_overwrite=True)
        print("Annotations downloaded successfully!")
    elif args.download_audio:
        print(f"Downloading {args.dataset} audio wav files (~1.35GB)...")
        ds.download(partial_download=["audio"])
        print("Audio files downloaded successfully!")

    if args.export:
        exported = export_academic_beats_to_txt(args.dataset, limit=args.limit)
        print(f"Exported {exported} tracks into benchmarks/ground_truth/academic/{args.dataset}/")

    if args.status or (not args.download_all and not args.download_annotations and not args.download_audio and not args.export):
        ready_with_audio = load_academic_tracks(args.dataset, require_audio=True)
        all_annotated = load_academic_tracks(args.dataset, require_audio=False)
        print(f"\nAcademic Dataset '{args.dataset}' Status:")
        print(f"  - Annotated Tracks: {len(all_annotated)}")
        print(f"  - Tracks with Local Audio Ready: {len(ready_with_audio)}")
        if len(ready_with_audio) == 0 and len(all_annotated) > 0:
            print(f"  - Tip: To download audio files, run: python -m benchmarks.ground_truth.academic.loader --dataset {args.dataset} --download-audio")
        elif len(all_annotated) == 0:
            print(f"  - Tip: To download annotations, run: python -m benchmarks.ground_truth.academic.loader --dataset {args.dataset} --download-annotations")


if __name__ == "__main__":
    main()
