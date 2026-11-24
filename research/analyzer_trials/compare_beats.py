"""Agreement between the beat trackers (no ground truth yet: this measures how much the tools agree).

F-measure (mir_eval, 70 ms window) of each tool against each other, plus median tempo from beat intervals.
Usage: python compare_beats.py
"""
from __future__ import annotations

import json

import mir_eval
import numpy as np

from common import OUT, load_tracks


def bpm(beats: list[float]) -> float:
    return float(60.0 / np.median(np.diff(beats))) if len(beats) > 2 else float("nan")


def f(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    return float(mir_eval.beat.f_measure(mir_eval.beat.trim_beats(np.array(a)), mir_eval.beat.trim_beats(np.array(b))))


def main() -> None:
    print(f"{'id':3s} {'track':34s} {'BPM bt/bn/lb':>16s}   {'F bt~bn':>7s} {'F bt~lb':>7s} {'F bn~lb':>7s}")
    rows = []
    for t in load_tracks():
        p = OUT / "beats" / f"{t['id']}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        bt, bn, lb = r["beat_this"]["beats"], r["beatnet_existing"]["beats"], r["librosa"]["beats"]
        row = (f(bt, bn), f(bt, lb), f(bn, lb))
        rows.append(row)
        print(
            f"{t['id']:3s} {t['file'][:34]:34s} {bpm(bt):5.0f}/{bpm(bn):4.0f}/{r['librosa']['tempo']:4.0f}   "
            f"{row[0]:7.2f} {row[1]:7.2f} {row[2]:7.2f}"
        )
    if rows:
        m = np.nanmean(np.array(rows), axis=0)
        print(f"{'':3s} {'MEAN':34s} {'':>16s}   {m[0]:7.2f} {m[1]:7.2f} {m[2]:7.2f}")


if __name__ == "__main__":
    main()
