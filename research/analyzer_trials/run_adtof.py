"""Drum transcription with the trained ADTOF model (PyTorch port) -> output/adtof/<id>.json

ADTOF (Zehren et al., ISMIR 2021 / Signals 2023) gives five classes: kick, snare, tom, hi-hat, cymbal.
It was trained on full mixes of rock / metal / pop from rhythm games: electronic drums are outside what it saw.
Run twice per track, on the full mix (its intended input) and on the Demucs drum stem, so the two can be compared.
Each hit is [time, strength], strength being the model's activation at the hit (0..1), not a loudness.

Port cloned into vendor/ADTOF-pytorch (https://github.com/xavriley/ADTOF-pytorch, weights ship in the repo).

Usage: python run_adtof.py [track ids...]
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import torch

from common import HERE, OUT, load_tracks, out_path, parse_only

sys.path.insert(0, str(HERE / "vendor" / "ADTOF-pytorch" / "src"))
from adtof_pytorch import (  # noqa: E402
    FRAME_RNN_THRESHOLDS,
    PeakPicker,
    calculate_n_bins,
    create_frame_rnn_model,
    get_default_weights_path,
    load_audio_for_model,
    load_pytorch_weights,
)

FPS = 100
CLASSES = ["kick", "snare", "tom", "hat", "cymbal"]   # order of the model outputs (MIDI 35, 38, 47, 42, 49)


def transcribe(model: torch.nn.Module, path: str) -> dict:
    x = load_audio_for_model(path)
    with torch.no_grad():
        act = model(x).cpu().numpy()[0]            # (frames, 5)
    picked = PeakPicker(thresholds=FRAME_RNN_THRESHOLDS, fps=FPS).pick(act, labels=list(range(5)))[0]
    out = {}
    for i, name in enumerate(CLASSES):
        out[name] = [[round(t, 3), round(float(act[min(len(act) - 1, int(round(t * FPS))), i]), 3)] for t in picked[i]]
    return out


def main() -> None:
    model = create_frame_rnn_model(calculate_n_bins())
    model.eval()
    model = load_pytorch_weights(model, get_default_weights_path(), strict=False)
    for t in load_tracks(parse_only(sys.argv[1:])):
        t0 = time.time()
        res = {"id": t["id"], "file": t["file"], "classes": CLASSES, "mix": transcribe(model, t["path"])}
        stem = OUT / "stems" / t["id"] / "drums.wav"
        if stem.exists():
            res["stem"] = transcribe(model, str(stem))
        res["seconds"] = round(time.time() - t0, 1)
        out_path("adtof", t["id"]).write_text(json.dumps(res), encoding="utf-8")
        counts = {k: len(v) for k, v in res["mix"].items()}
        scounts = {k: len(v) for k, v in res.get("stem", {}).items()}
        print(f"[{t['id']}] {res['seconds']:5.1f}s  mix {counts}  stem {scounts}", flush=True)


if __name__ == "__main__":
    main()
