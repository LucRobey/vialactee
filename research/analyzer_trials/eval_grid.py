"""Does averaging the trackers give better beat times? Measured against drum hits in the Demucs drum stem.

For every grid beat that all three trackers marked (so each method is judged on the same beats), find the nearest
drum onset within 80 ms and record the signed distance, for: each tracker alone, their average, and the smoothed
average. Per method: bias = median distance, jitter = robust spread around that bias (lower = steadier timing).

The drum onsets are an independent reference (they come from the audio, not from a beat tracker), but they are
themselves detected by an algorithm (librosa onset detection, ~6 ms steps), so differences of a few ms mean nothing.

Usage: python eval_grid.py [track ids...]     (only tracks whose stems exist)
"""
from __future__ import annotations

import json
import sys

import librosa
import numpy as np

from common import OUT, load_audio, load_tracks, parse_only

SR, HOP, WIN = 22050, 128, 0.08
METHODS = ["beat_this", "beatnet", "librosa", "average", "smoothed"]


def drum_onsets(tid: str) -> np.ndarray:
    y, _ = load_audio(str(OUT / "stems" / tid / "drums.wav"), sr=SR, mono=True)
    env = librosa.onset.onset_strength(y=y[0], sr=SR, hop_length=HOP)
    return librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time")


def spread(d: np.ndarray) -> tuple[float, float]:
    med = float(np.median(d))
    return med * 1000, float(1.4826 * np.median(np.abs(d - med))) * 1000


def main() -> None:
    rows = []
    print(f"{'id':3s} {'track':24s} {'beats':>5s}   " + "  ".join(f"{m:>10s}" for m in METHODS) + "   (jitter in ms; lower is steadier)")
    for t in load_tracks(parse_only(sys.argv[1:])):
        gp, sp = OUT / "grid" / f"{t['id']}.json", OUT / "stems" / t["id"] / "drums.wav"
        if not gp.exists() or not sp.exists():
            continue
        beats = [b for b in json.loads(gp.read_text(encoding="utf-8"))["beats"] if b["votes"] == 3]
        on = drum_onsets(t["id"])
        if len(beats) < 30 or len(on) < 30:
            continue
        times = {m: np.array([b["members"][m] for b in beats]) for m in METHODS[:3]}
        times["average"] = np.array([b["t"] for b in beats])
        times["smoothed"] = np.array([b["t_smooth"] for b in beats])
        # same drum onset for every method: the one nearest to the average time
        idx = np.clip(np.searchsorted(on, times["average"]), 1, len(on) - 1)
        near = np.where(np.abs(on[idx - 1] - times["average"]) < np.abs(on[idx] - times["average"]), on[idx - 1], on[idx])
        keep = np.abs(near - times["average"]) < WIN
        if keep.sum() < 30:
            continue
        res = {m: spread(times[m][keep] - near[keep]) for m in METHODS}
        rows.append([res[m][1] for m in METHODS])
        print(f"{t['id']:3s} {t['file'][:24]:24s} {int(keep.sum()):5d}   " + "  ".join(f"{res[m][1]:10.1f}" for m in METHODS)
              + "   bias ms: " + " ".join(f"{res[m][0]:+.0f}" for m in METHODS), flush=True)
    if rows:
        m = np.mean(np.array(rows), axis=0)
        print(f"{'':3s} {'MEAN over ' + str(len(rows)) + ' tracks':24s} {'':5s}   " + "  ".join(f"{v:10.1f}" for v in m))
        best = np.argmin(np.array(rows), axis=1)
        print("    steadiest method per track: " + ", ".join(f"{METHODS[i]} x{int((best == i).sum())}" for i in range(len(METHODS)) if (best == i).any()))


if __name__ == "__main__":
    main()
