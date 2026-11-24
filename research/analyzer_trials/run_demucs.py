"""Tool: Demucs (htdemucs) source separation -> output/stems/<id>/{drums,bass,other,vocals}.wav

Usage: python run_demucs.py [track ids...]   (default: all 20)
CPU-only. Decodes with libsndfile and calls demucs' python API directly, so no ffmpeg/torchcodec needed.
"""
from __future__ import annotations

import sys
import time

import numpy as np
import soundfile as sf
import torch

from common import OUT, load_audio, load_tracks, parse_only


def main() -> None:
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    torch.set_num_threads(max(1, torch.get_num_threads()))
    model = get_model("htdemucs")
    model.eval()
    sr = model.samplerate

    for t in load_tracks(parse_only(sys.argv[1:])):
        dest = OUT / "stems" / t["id"]
        if all((dest / f"{s}.wav").exists() for s in model.sources):
            print(f"[{t['id']}] stems exist, skipping")
            continue
        t0 = time.time()
        y, _ = load_audio(t["path"], sr=sr)
        if y.shape[0] == 1:
            y = np.repeat(y, 2, axis=0)
        wav = torch.from_numpy(y)
        ref = wav.mean(0)
        mean, std = ref.mean(), ref.std() + 1e-8
        with torch.no_grad():
            out = apply_model(model, ((wav - mean) / std)[None], device="cpu", split=True, overlap=0.25, progress=False)[0]
        out = out * std + mean
        dest.mkdir(parents=True, exist_ok=True)
        for name, stem in zip(model.sources, out):
            sf.write(dest / f"{name}.wav", stem.numpy().T, sr, subtype="PCM_16")
        dur = y.shape[1] / sr
        print(f"[{t['id']}] {t['file'][:40]:40s} {dur:6.1f}s audio -> {time.time() - t0:6.1f}s", flush=True)


if __name__ == "__main__":
    main()
