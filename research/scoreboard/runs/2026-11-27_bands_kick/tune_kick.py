"""Tuning of the kick detector of BandKickSlotsAudioAnalyzer, on the OPEN tracks only (odd ids).

Step 1 (capture): play each open track through the production Listener and keep, per tick, the rise of each of
the 32 bands as the analyzer sees it on arrival (`analyzer.dE`). Tick k is the music at k / 60 s.
Step 2 (sweep): replay the detector rule offline over that capture for a grid of settings and grade each
against the truth kicks (levels M1 and M2, 50 ms), averaged over the open tracks.

The even-numbered tracks are never read here: they are the check set of the pilot.

Run from the repository root:
    research/analyzer_trials/.venv/Scripts/python.exe research/scoreboard/runs/2026-11-27_bands_kick/tune_kick.py capture
    research/analyzer_trials/.venv/Scripts/python.exe research/scoreboard/runs/2026-11-27_bands_kick/tune_kick.py sweep
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
CAPTURE = REPO / "research" / "scoreboard" / "output" / "tune_kick"
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
OPEN = [t for t in TRACKS["tracks"] if int(t["id"]) % 2 == 1]
DT = 1.0 / 60.0
KICK_W = (2.0, 1.8, 1.2)            # weights of the three lowest bands in the analyzer's kick stream
SNARE = ((4, 1.2), (5, 1.2), (14, 0.8), (15, 0.8), (16, 0.8))


def capture() -> None:
    from music.api import Listener
    from tools.choreography_probe import HOP, OfflineClock, load_audio_mono, step_listener
    from tools.listener_config import build_listener_infos

    CAPTURE.mkdir(parents=True, exist_ok=True)
    for t in OPEN:
        mono = load_audio_mono(str(REPO / TRACKS["audio_dir"] / t["file"]))
        n = len(mono) // HOP
        with OfflineClock() as clock:
            listener = Listener(build_listener_infos())
            listener.dynamic_audio_latency = 0.0
            rise = np.zeros((n, listener.analyzer.nb_bands), dtype=np.float32)
            for k in range(n):
                step_listener(listener, mono, k * HOP, clock)
                rise[k] = listener.analyzer.dE
        np.savez_compressed(CAPTURE / f"{t['id']}.npz", rise=rise)
        print(f"[{t['id']}] {n} ticks", flush=True)


def detect(rise: np.ndarray, over_avg: float, share_peak: float, low_share: float, snare_ratio: float,
           refractory: float = 0.09, avg_s: float = 1.0, peak_fall_s: float = 4.0) -> np.ndarray:
    """The rule of the candidate, replayed offline. Returns kick times in seconds."""
    y = KICK_W[0] * rise[:, 0] + KICK_W[1] * rise[:, 1] + KICK_W[2] * rise[:, 2]
    snare = sum(w * rise[:, b] for b, w in SNARE)
    avg = peak = 0.0
    last = -1e9
    out = []
    for k in range(2, len(y)):
        avg += min(1.0, DT / avg_s) * (y[k] - avg)
        peak = max(y[k], peak * 0.5 ** (DT / peak_fall_s))
        p = y[k - 1]
        if p > y[k - 2] and p >= y[k] and p > over_avg * avg and p > share_peak * peak:
            t = (k - 1) * DT
            if t - last < refractory:
                continue
            if KICK_W[0] * rise[k - 1, 0] < low_share * p:              # a kick lives in the lowest band
                continue
            if snare[k - 1] > snare_ratio * p:                          # a snare rises much more in the middle
                continue
            out.append(t)
            last = t
    return np.array(out)


def sweep() -> None:
    from research.scoreboard import grade

    data = []
    for t in OPEN:
        truth = json.loads((REPO / "research" / "truth" / "tracks" / f"{t['id']}.json").read_text(encoding="utf-8"))
        rows = truth["drums"]["pieces"]["kick"]
        data.append((t["id"], np.load(CAPTURE / f"{t['id']}.npz")["rise"].astype(float),
                     [r[0] for r in rows], [r[2] != "W" for r in rows]))
    # second grid: the first one (2 to 4, 0.15 to 0.5, 0 to 0.55, snare test 0.5 to off) had its best at the upper edge
    grid = itertools.product((2.5, 3.0, 4.0, 5.0, 6.0), (0.25, 0.35, 0.5, 0.6, 0.7), (0.0, 0.15, 0.25, 0.4), (1e9, 1.0))
    results = []
    for over_avg, share_peak, low_share, snare_ratio in grid:
        f1, found, right = [], [], []
        for _, rise, times, ok in data:
            res = grade.event_score(detect(rise, over_avg, share_peak, low_share, snare_ratio), times, 0.05, ok)
            f1.append(res["f1"]); found.append(res["found"]); right.append(res["right"])
        results.append((float(np.mean(f1)), float(np.mean(found)), float(np.nanmean(right)), float(np.min(f1)),
                        over_avg, share_peak, low_share, snare_ratio))
    results.sort(reverse=True)
    print(f"open tracks: {[d[0] for d in data]}")
    print("  F1  found right worst | over_avg share_peak low_share snare_ratio")
    for r in results[:12]:
        print(f"{100 * r[0]:5.1f} {100 * r[1]:5.1f} {100 * r[2]:5.1f} {100 * r[3]:5.1f} | {r[4]:7.1f} {r[5]:9.2f} {r[6]:9.2f} {r[7]:10.1f}")
    base = [r for r in results if r[4:] == (2.5, 0.25, 0.0, 1e9)][0]
    print(f"first version (2.5, 0.25, no extra test): F1 {100 * base[0]:.1f}, found {100 * base[1]:.1f}, right {100 * base[2]:.1f}")
    best = results[0]
    per = []
    for tid, rise, times, ok in data:
        res = grade.event_score(detect(rise, *best[4:]), times, 0.05, ok)
        per.append(f"{tid}:{100 * res['f1']:.0f}")
    print("best setting, track by track:", " ".join(per))


if __name__ == "__main__":
    {"capture": capture, "sweep": sweep}[sys.argv[1]]()
