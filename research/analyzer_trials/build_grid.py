"""Combine the three beat trackers into one grid -> output/grid/<id>.json

Idea (from listening in the viewer): the trackers mostly find the same beats but each is a little early or late,
and they do not always follow the same tempo level (one marks every beat, another only 1 and 3).

  1. Cluster: beats from different trackers within 70 ms of each other are the same beat. Its time is their average.
  2. Anchors: clusters found by at least two trackers.
  3. Fill: between two anchors, the local beat period says how many beats fit. Missing ones are taken from a single
     tracker if it has a beat there, otherwise interpolated. This puts the grid on the finest level any tracker follows.
  4. Reject: single-tracker beats that fit neither a grid position nor a half beat are dropped as off-grid.
  5. Smooth: each time is also given as the mean of its +-3 neighbours ("regular" version), without crossing breaks.

Each grid beat keeps `votes` (how many trackers marked it): 3 = all agree, 0 = interpolated.
Not done here: which beat is "1" (the trackers disagree on that too often to vote).

Usage: python build_grid.py [track ids...]
"""
from __future__ import annotations

import json
import sys

import numpy as np

from common import OUT, load_tracks, out_path, parse_only

TOL = 0.07  # s: beats closer than this (to the cluster mean) are the same beat


def load_trackers(tid: str) -> dict[str, np.ndarray]:
    b = json.loads((OUT / "beats" / f"{tid}.json").read_text(encoding="utf-8"))
    tr = {"beat_this": b["beat_this"]["beats"], "librosa": b["librosa"]["beats"]}
    p = OUT / "beatnet" / f"{tid}.json"
    if p.exists():
        tr["beatnet"] = json.loads(p.read_text(encoding="utf-8"))["beats"]
    return {k: np.asarray(v, dtype=float) for k, v in tr.items() if len(v) > 4}


def cluster(trackers: dict[str, np.ndarray]) -> list[dict]:
    items = sorted((float(t), name) for name, arr in trackers.items() for t in arr)
    out, cur = [], []
    for t, name in items:
        if cur and abs(t - np.mean([c[0] for c in cur])) <= TOL and name not in {c[1] for c in cur}:
            cur.append((t, name))
        else:
            if cur:
                out.append(cur)
            cur = [(t, name)]
    if cur:
        out.append(cur)
    return [{"t": float(np.mean([c[0] for c in g])), "who": sorted(c[1] for c in g), "members": dict((n, t) for t, n in g)} for g in out]


def base_period(trackers: dict[str, np.ndarray]) -> float:
    """Shortest beat period among trackers that sit at x1, x2 or x0.5 of Beat This (others are ignored)."""
    med = {k: float(np.median(np.diff(v))) for k, v in trackers.items()}
    ref = med.get("beat_this", min(med.values()))
    ok = [m for m in med.values() if any(abs(m / ref - r) < 0.08 * r for r in (0.5, 1.0, 2.0))]
    return min(ok) if ok else ref


def local_period_fn(trackers: dict[str, np.ndarray], p0: float):
    """Local beat period: median of all trackers' intervals within +-6 s, folded to the base level."""
    ts, ps = [], []
    for v in trackers.values():
        d = np.diff(v)
        k = np.round(d / p0)
        good = (k >= 1) & (k <= 4) & (np.abs(d / np.maximum(k, 1) - p0) < 0.25 * p0)
        ts.extend(((v[:-1] + v[1:]) / 2)[good])
        ps.extend((d / np.maximum(k, 1))[good])
    order = np.argsort(ts)
    ts, ps = np.asarray(ts)[order], np.asarray(ps)[order]

    def at(t: float) -> float:
        lo, hi = np.searchsorted(ts, t - 6), np.searchsorted(ts, t + 6)
        return float(np.median(ps[lo:hi])) if hi - lo >= 3 else p0

    return at


def build(trackers: dict[str, np.ndarray]) -> dict:
    cl = cluster(trackers)
    p0 = base_period(trackers)
    period = local_period_fn(trackers, p0)
    anchors = [c for c in cl if len(c["who"]) >= 2]
    singles = [c for c in cl if len(c["who"]) == 1]
    single_t = np.array([c["t"] for c in singles])
    used = np.zeros(len(singles), dtype=bool)

    grid: list[dict] = []
    breaks = 0
    for i, a in enumerate(anchors):
        if i:
            prev = anchors[i - 1]
            g = a["t"] - prev["t"]
            pl = period((a["t"] + prev["t"]) / 2)
            n = max(1, int(round(g / pl)))
            if abs(g / n - pl) > 0.2 * pl:
                breaks += 1
                grid[-1]["break_after"] = True  # irregular gap: tempo change, pause, or trackers lost
            else:
                tol = max(0.06, 0.15 * pl)
                for j in range(1, n):
                    pred = prev["t"] + g * j / n
                    k = int(np.argmin(np.abs(single_t - pred))) if len(single_t) else -1
                    if k >= 0 and not used[k] and abs(single_t[k] - pred) <= tol:
                        used[k] = True
                        grid.append({"t": singles[k]["t"], "who": singles[k]["who"], "members": singles[k]["members"]})
                    else:
                        grid.append({"t": pred, "who": [], "members": {}})
        grid.append({"t": a["t"], "who": a["who"], "members": a["members"]})

    # Classify the single-tracker beats that were not used.
    gt = np.array([b["t"] for b in grid])
    half = off = dup = 0
    for k, c in enumerate(singles):
        if used[k] or not len(gt) or c["t"] < gt[0] or c["t"] > gt[-1]:
            continue
        j = int(np.searchsorted(gt, c["t"]))
        lo, hi = gt[j - 1], gt[min(j, len(gt) - 1)]
        if min(c["t"] - lo, hi - c["t"]) < 0.1:
            dup += 1  # a late/early copy of a beat that is already in the grid
        elif abs(c["t"] - (lo + hi) / 2) <= max(0.06, 0.15 * (hi - lo)):
            half += 1
        else:
            off += 1

    # Smoothed ("regular") times: mean of +-3 neighbours, never across a break.
    t = np.array([b["t"] for b in grid])
    seg_start = 0
    smooth = t.copy()
    ends = [i for i, b in enumerate(grid) if b.get("break_after")] + [len(grid) - 1]
    for end in ends:
        for i in range(seg_start, end + 1):
            h = min(3, i - seg_start, end - i)
            smooth[i] = t[i - h : i + h + 1].mean()
        seg_start = end + 1

    votes = [len(b["who"]) for b in grid]
    return {
        "trackers": sorted(trackers),
        "base_bpm": round(60 / p0, 1),
        "beats": [
            {"t": round(float(t[i]), 4), "t_smooth": round(float(smooth[i]), 4), "votes": votes[i], "who": grid[i]["who"],
             "members": {k: round(v, 4) for k, v in grid[i]["members"].items()}}
            for i in range(len(grid))
        ],
        "stats": {
            "grid_beats": len(grid),
            "votes": {str(v): votes.count(v) for v in (3, 2, 1, 0)},
            "breaks": breaks,
            "rejected_half_beat": half,
            "rejected_off_grid": off,
            "rejected_duplicate": dup,
        },
    }


def main() -> None:
    for t in load_tracks(parse_only(sys.argv[1:])):
        trackers = load_trackers(t["id"])
        res = {"id": t["id"], "file": t["file"], **build(trackers)}
        out_path("grid", t["id"]).write_text(json.dumps(res), encoding="utf-8")
        s = res["stats"]
        print(
            f"[{t['id']}] {t['file'][:26]:26s} {res['base_bpm']:6.1f} BPM  {s['grid_beats']:4d} beats  "
            f"votes 3/2/1/0: {s['votes']['3']:4d}/{s['votes']['2']:4d}/{s['votes']['1']:4d}/{s['votes']['0']:4d}  "
            f"breaks {s['breaks']:3d}  rejected half/off/dup: {s['rejected_half_beat']}/{s['rejected_off_grid']}/{s['rejected_duplicate']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
