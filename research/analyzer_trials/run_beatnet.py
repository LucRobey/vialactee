"""BeatNet rerun at the correct speed -> output/beatnet/<id>.json

Same model and settings as research/benchmarks/ground_truth/extract_neural_reference.py (BeatNet 1, offline, DBN),
but the audio is decoded and resampled to 22.05 kHz here, so it cannot be mislabelled by the benchmark's cache
loader (which is what stretched part of the existing reference to 2x).

Usage: python run_beatnet.py [track ids...]
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import numpy as np
import soundfile as sf

from common import load_audio, load_tracks, out_path, parse_only

SR = 22050


def main() -> None:
    from BeatNet.BeatNet import BeatNet

    estimator = BeatNet(1, mode="offline", inference_model="DBN", plot=[], thread=False)
    for t in load_tracks(parse_only(sys.argv[1:])):
        dest = out_path("beatnet", t["id"])
        if dest.exists():
            print(f"[{t['id']}] exists, skipping")
            continue
        t0 = time.time()
        y, _ = load_audio(t["path"], sr=SR, mono=True)
        duration = y.shape[1] / SR
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            sf.write(tmp, y[0], SR, subtype="PCM_16")
            out = np.asarray(estimator.process(tmp))  # (N, 2): time in seconds, position in bar
        finally:
            os.remove(tmp)
        beats = [round(float(b), 4) for b in out[:, 0]] if len(out) else []
        downbeats = [round(float(b), 4) for b, pos in out if int(pos) == 1] if len(out) else []
        res = {
            "id": t["id"],
            "file": t["file"],
            "duration": round(duration, 2),
            "beats": beats,
            "downbeats": downbeats,
            "seconds": round(time.time() - t0, 1),
        }
        dest.write_text(json.dumps(res), encoding="utf-8")
        bpm = 60.0 / float(np.median(np.diff(beats))) if len(beats) > 2 else float("nan")
        last = beats[-1] if beats else 0.0
        print(f"[{t['id']}] {len(beats)} beats / {len(downbeats)} downbeats, {bpm:.1f} BPM, last beat {last:.0f}s of {duration:.0f}s, {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
