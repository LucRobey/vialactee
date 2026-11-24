"""Shared helpers for the analyzer trials (track list, audio decoding, output paths)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "output"


def load_tracks(only: list[str] | None = None) -> list[dict]:
    spec = json.loads((HERE / "tracks.json").read_text(encoding="utf-8"))
    audio_dir = REPO / spec["audio_dir"]
    tracks = []
    for t in spec["tracks"]:
        if only and t["id"] not in only:
            continue
        t = dict(t)
        t["path"] = str(audio_dir / t["file"])
        tracks.append(t)
    return tracks


def load_audio(path: str, sr: int | None = None, mono: bool = False) -> tuple[np.ndarray, int]:
    """Decode to float32 array shaped (channels, samples). Uses libsndfile (no ffmpeg needed)."""
    data, file_sr = sf.read(path, dtype="float32", always_2d=True)  # (samples, ch)
    y = data.T
    if mono:
        y = y.mean(axis=0, keepdims=True)
    if sr and sr != file_sr:
        import librosa

        y = np.stack([librosa.resample(ch, orig_sr=file_sr, target_sr=sr) for ch in y])
        file_sr = sr
    return y, file_sr


def out_path(kind: str, track_id: str, ext: str = "json") -> Path:
    p = OUT / kind
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{track_id}.{ext}"


def parse_only(argv: list[str]) -> list[str] | None:
    return [a for a in argv if not a.startswith("-")] or None
