"""Section-boundary baseline -> output/sections/<id>.json

Tool: librosa only (beat-synchronous chroma + MFCC, agglomerative clustering with k segments).
This yields BOUNDARIES without labels (no "verse"/"chorus"); it is the stand-in until all-in-one
(allin1) can run - allin1 needs madmom, which does not build on this machine (no C++ compiler).

Usage: python run_sections.py [track ids...]
"""
from __future__ import annotations

import json
import sys

import librosa
import numpy as np

from common import load_audio, load_tracks, out_path, parse_only


def main() -> None:
    for t in load_tracks(parse_only(sys.argv[1:])):
        dest = out_path("sections", t["id"])
        if dest.exists():
            print(f"[{t['id']}] exists, skipping")
            continue
        y, sr = load_audio(t["path"], sr=22050, mono=True)
        y = y[0]
        dur = len(y) / sr
        hop = 512
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
        # sync to ~0.5 s windows for stable, cheap clustering
        step = int(0.5 * sr / hop)
        edges = np.arange(0, chroma.shape[1], step)
        feat = np.vstack(
            [
                librosa.util.normalize(librosa.util.sync(chroma, edges, aggregate=np.median), axis=0),
                librosa.util.normalize(librosa.util.sync(mfcc[1:], edges, aggregate=np.mean), axis=0),
            ]
        )
        # Foote novelty: self-similarity matrix, checkerboard kernel slid along the diagonal, peak picking.
        # (numpy/scipy only: scikit-learn's DLLs are blocked by this machine's Windows app-control policy.)
        f = feat / (np.linalg.norm(feat, axis=0, keepdims=True) + 1e-9)
        ssm = f.T @ f
        half = 12  # 12 windows = 6 s each side
        g = np.outer(np.sign(np.arange(-half, half) + 0.5), np.sign(np.arange(-half, half) + 0.5))
        g = g * np.outer(np.hanning(2 * half), np.hanning(2 * half))
        n = ssm.shape[0]
        pad = np.pad(ssm, half, mode="edge")
        nov = np.array([(pad[i : i + 2 * half, i : i + 2 * half] * g).sum() for i in range(n)])
        nov = np.maximum(nov, 0)
        k = int(np.clip(round(dur / 25), 4, 14))  # aim for about one section per 25 s
        from scipy.signal import find_peaks

        peaks, props = find_peaks(nov, distance=int(12 / 0.5), prominence=0)  # boundaries >= 12 s apart
        top = peaks[np.argsort(props["prominences"])[::-1][: k - 1]]
        times = sorted({round(float(i * 0.5), 2) for i in top if 0 < i * 0.5 < dur - 6})
        dest.write_text(json.dumps({"id": t["id"], "method": "foote_novelty", "boundaries": times}), encoding="utf-8")
        print(f"[{t['id']}] {dur:5.0f}s -> {len(times)} boundaries", flush=True)


if __name__ == "__main__":
    main()
