"""Derive labels from Demucs stems -> output/vocals/<id>.json and output/drums/<id>.json

These are HEURISTIC readings of the separated stems, not outputs of a trained detector:
  vocals: frame RMS of vocals.wav, hysteresis threshold relative to the track's loud vocal level
  drums : onset detection on drums.wav, each onset labelled kick / snare / hat by band-energy ratios

Usage: python derive_from_stems.py [track ids...]
"""
from __future__ import annotations

import json
import sys

import librosa
import numpy as np

from common import OUT, load_audio, load_tracks, out_path, parse_only

SR = 22050
HOP = 512  # ~23 ms


def vocal_segments(y: np.ndarray) -> dict:
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
    db = 20 * np.log10(rms + 1e-9)
    ref = np.percentile(db, 95)  # "loud singing" level for this track
    on_thr, off_thr = ref - 25.0, ref - 30.0
    active = np.zeros_like(db, dtype=bool)
    state = False
    for i, v in enumerate(db):
        state = v > off_thr if state else v > on_thr
        active[i] = state
    t = librosa.frames_to_time(np.arange(len(db) + 1), sr=SR, hop_length=HOP)
    segs: list[list[float]] = []
    start = None
    for i, a in enumerate(active):
        if a and start is None:
            start = t[i]
        elif not a and start is not None:
            segs.append([start, t[i]])
            start = None
    if start is not None:
        segs.append([start, t[len(db)]])
    merged: list[list[float]] = []
    for s in segs:  # bridge gaps < 0.6 s (breaths), drop blips < 0.5 s
        if merged and s[0] - merged[-1][1] < 0.6:
            merged[-1][1] = s[1]
        else:
            merged.append(list(s))
    merged = [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= 0.5]
    total = len(y) / SR
    return {
        "segments": merged,
        "vocal_fraction": round(sum(b - a for a, b in merged) / total, 3),
        "ref_db": round(float(ref), 1),
    }


def drum_onsets(y: np.ndarray) -> dict:
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="frames")
    times = librosa.frames_to_time(frames, sr=SR, hop_length=HOP)
    win = int(0.06 * SR)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    band = {
        "low": (freqs >= 30) & (freqs < 150),
        "mid": (freqs >= 150) & (freqs < 3000),
        "high": (freqs >= 5000) & (freqs < 10000),
    }
    hann = np.hanning(win)
    hits = []
    for f, tm in zip(frames, times):
        s = int(tm * SR)
        seg = y[s : s + win]
        if len(seg) < win:
            continue
        spec = np.abs(np.fft.rfft(seg * hann)) ** 2
        e = {k: float(spec[m].sum()) + 1e-12 for k, m in band.items()}
        tot = sum(e.values())
        lo, hi = e["low"] / tot, e["high"] / tot
        label = "kick" if lo > 0.55 else ("hat" if hi > 0.45 else "snare")
        hits.append([round(float(tm), 3), label, round(float(env[f]), 2)])
    counts = {k: sum(1 for h in hits if h[1] == k) for k in ("kick", "snare", "hat")}
    return {"hits": hits, "counts": counts}


def main() -> None:
    for t in load_tracks(parse_only(sys.argv[1:])):
        d = OUT / "stems" / t["id"]
        if not (d / "vocals.wav").exists() or not (d / "drums.wav").exists():
            print(f"[{t['id']}] no stems yet, skipping")
            continue
        voc, _ = load_audio(str(d / "vocals.wav"), sr=SR, mono=True)
        drm, _ = load_audio(str(d / "drums.wav"), sr=SR, mono=True)
        v = vocal_segments(voc[0])
        out_path("vocals", t["id"]).write_text(json.dumps({"id": t["id"], **v}), encoding="utf-8")
        dr = drum_onsets(drm[0])
        out_path("drums", t["id"]).write_text(json.dumps({"id": t["id"], **dr}), encoding="utf-8")
        print(f"[{t['id']}] vocals {v['vocal_fraction']:.0%} of track in {len(v['segments'])} segments; drums {dr['counts']}", flush=True)


if __name__ == "__main__":
    main()
