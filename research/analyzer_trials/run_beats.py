"""Beat / downbeat trials -> output/beats/<id>.json

Tools:
  beat_this  - Beat This! (CPJKU, ISMIR 2024), beats + downbeats, no DBN post-processing
  librosa    - librosa.beat.beat_track baseline (beats + tempo only)
  beatnet    - reused from the repo's existing research/benchmarks/ground_truth/neural/ files

Usage: python run_beats.py [track ids...]
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from common import REPO, load_audio, load_tracks, out_path, parse_only

NEURAL = REPO / "research" / "benchmarks" / "ground_truth" / "neural"


def read_times(p) -> list[float]:
    if not p.exists():
        return []
    vals = []
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts and not parts[0].startswith("#"):
            vals.append(round(float(parts[0]), 4))
    return vals


def main() -> None:
    from beat_this.inference import File2Beats

    f2b = File2Beats(device="cpu", dbn=False)
    import librosa

    for t in load_tracks(parse_only(sys.argv[1:])):
        dest = out_path("beats", t["id"])
        if dest.exists():
            print(f"[{t['id']}] exists, skipping")
            continue
        res: dict = {"id": t["id"], "file": t["file"]}
        t0 = time.time()
        beats, downbeats = f2b(t["path"])
        res["beat_this"] = {
            "beats": [round(float(b), 4) for b in beats],
            "downbeats": [round(float(b), 4) for b in downbeats],
            "seconds": round(time.time() - t0, 1),
        }
        t0 = time.time()
        y, sr = load_audio(t["path"], sr=22050, mono=True)
        tempo, frames = librosa.beat.beat_track(y=y[0], sr=sr)
        res["librosa"] = {
            "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
            "beats": [round(float(b), 4) for b in librosa.frames_to_time(frames, sr=sr)],
            "seconds": round(time.time() - t0, 1),
        }
        stem = t["file"].rsplit(".", 1)[0]
        res["beatnet_existing"] = {
            "beats": read_times(NEURAL / f"{stem}.beats.txt"),
            "downbeats": read_times(NEURAL / f"{stem}.downbeats.txt"),
        }
        dest.write_text(json.dumps(res), encoding="utf-8")
        print(
            f"[{t['id']}] beat_this {len(res['beat_this']['beats'])} beats / "
            f"{len(res['beat_this']['downbeats'])} downbeats, librosa {res['librosa']['tempo']} BPM, "
            f"beatnet {len(res['beatnet_existing']['beats'])} beats",
            flush=True,
        )


if __name__ == "__main__":
    main()
