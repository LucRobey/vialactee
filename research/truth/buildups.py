"""First guess of the build-ups and of the possible drops, for the owner to correct in the review tool.

No tool finds a build-up or a drop. What can be measured is what usually surrounds them:

- a **release point**: the kick comes back after a break, or the music gets suddenly louder at a section change;
- before it, **tension rising**: the sound gets brighter (a filter opens, a sweep climbs), it gets louder, or the
  drum hits get closer and closer (a roll).

A build-up is proposed from where the tension starts rising to the release point, when enough of this is seen.
A possible drop is proposed at a release point that the main rule (kick return with a clear jump in loudness)
did not already take.

Everything here is level W (weak): a guess to save the owner's time, never used to grade the analyzer. It becomes
truth only when the owner has accepted, moved or redrawn it (research/truth/labels.py: levels A and H).
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np

from research.truth import measures

LOOK_BACK_S: float = 24.0         # a build-up starts at most this long before its release point
MIN_LENGTH_S: float = 2.0
EDGE_S: float = 0.3               # the tension is read this long before the release point, clear of the hit itself
BRIGHT_RISE_OCT: float = 0.5      # brightness climbs by at least this much
LOUD_RISE_DB: float = 4.0         # loudness climbs by at least this much
SMOOTH_S: float = 2.0             # the curves are smoothed over this long before looking for a climb
BRIGHT_DIP_OCT: float = 0.3       # a climb is broken by a fall of more than this
LOUD_DIP_DB: float = 3.0
STILL_CLIMBING_S: float = 3.0     # the climb must reach its top no earlier than this before the release point
FIRST_DROP_S: float = 5.0         # nothing in the first seconds of a file is a drop: the music is only starting
ROLL_LAST_S: float = 2.0          # a roll: the hits of the last two seconds...
ROLL_RATE_HZ: float = 4.0         # ...come at least this often
ROLL_FACTOR: float = 1.8          # ...and this many times more often than in the six seconds before
SECTION_JUMP_DB: float = 5.0      # a section change that gets this much louder is a release point
DROP_NEAR_S: float = 2.0          # two release points closer than this are the same one


def _jump_db(loud: np.ndarray, t: float, hz: int) -> float:
    """Loudness of the two seconds after t minus the two seconds before."""
    i, two = int(round(t * hz)), 2 * hz
    before, after = loud[max(0, i - two) : i], loud[i : i + two]
    return float(np.mean(after) - np.mean(before)) if len(before) and len(after) else 0.0


def release_points(moments: Sequence[dict], sections: Sequence[dict], loud: np.ndarray, hz: int) -> List[dict]:
    """Where the music comes back: every kick return, and every section change with a clear jump in loudness."""
    out = [{"t": float(m["t"]), "kind": "kick returns", "jump_db": float(m.get("loudness_jump_db", 0.0))}
           for m in moments if m.get("kind") == "kick_return"]
    for s in sections:
        t = float(s["t"])
        jump = _jump_db(loud, t, hz)
        if jump >= SECTION_JUMP_DB and all(abs(t - r["t"]) > DROP_NEAR_S for r in out):
            out.append({"t": t, "kind": "section change, much louder", "jump_db": round(jump, 1)})
    return sorted(out, key=lambda r: r["t"])


def possible_drops(releases: Sequence[dict], drops: Sequence[dict]) -> List[dict]:
    """Release points the main rule did not propose as a drop: weak proposals for the owner."""
    taken = [float(d["t"]) for d in drops]
    return [{"t": round(r["t"], 3), "level": "W", "loudness_jump_db": round(r["jump_db"], 1), "why": r["kind"]}
            for r in releases if r["t"] >= FIRST_DROP_S and all(abs(r["t"] - t) > DROP_NEAR_S for t in taken)]


def _rise(curve: np.ndarray, t0: float, t1: float, hz: int, dip: float) -> tuple:
    """The last climb of a smoothed curve before t1: how much it rises, and when it starts.

    Walking back from t1, the climb goes on as long as the curve keeps getting lower; it stops at the first place
    that is higher than the lowest point seen by more than `dip`. So a song that was simply quieter twenty seconds
    earlier does not count: only the unbroken rise that ends at t1 does, and it must still be rising near t1.
    """
    a, b = max(0, int(round(t0 * hz))), min(len(curve) - 1, int(round((t1 - EDGE_S) * hz)))
    if b - a < hz:
        return 0.0, t1
    seg = curve[a : b + 1]
    if not np.all(np.isfinite(seg)):
        seg = np.where(np.isfinite(seg), seg, np.nanmax(seg) if np.any(np.isfinite(seg)) else 0.0)
    low = len(seg) - 1
    for i in range(len(seg) - 2, -1, -1):
        if seg[i] < seg[low]:
            low = i
        elif seg[i] > seg[low] + dip:
            break
    rise = float(seg[-1] - seg[low])
    if rise <= 0.0:
        return 0.0, t1
    # still climbing at the end? a step up followed by a long flat stretch is not tension rising
    top = low + int(np.argmax(seg[low:] >= seg[low] + 0.9 * rise))
    if (len(seg) - 1 - top) / hz > STILL_CLIMBING_S:
        return 0.0, t1
    foot = low + int(np.nonzero(seg[low : top + 1] <= seg[low] + 0.1 * rise)[0][-1])       # where the climb really starts
    return rise, (a + foot) / hz


def _roll_start(hits: np.ndarray, t0: float, t1: float) -> float:
    """Start of a drum roll ending at t1 (hits getting much denser), or -1 when there is none."""
    last = hits[(hits >= t1 - ROLL_LAST_S) & (hits < t1)]
    before = hits[(hits >= max(t0, t1 - 8.0)) & (hits < t1 - ROLL_LAST_S)]
    rate_last = len(last) / ROLL_LAST_S
    rate_before = len(before) / max(1e-6, min(6.0, t1 - ROLL_LAST_S - t0))
    if rate_last < ROLL_RATE_HZ or rate_last < ROLL_FACTOR * rate_before:
        return -1.0
    run = hits[(hits >= t0) & (hits < t1)]
    start = float(run[-1])
    for a, b in zip(run[-2::-1], run[:0:-1]):          # walk back while the hits stay close together
        if b - a > 0.35:
            break
        start = float(a)
    return start


def buildups(releases: Sequence[dict], beats: Sequence[dict], curves: Dict[str, np.ndarray], pieces: Dict[str, list],
             kick_stretches: Sequence[dict], hz: int) -> List[dict]:
    """One proposal per release point that has rising tension before it. Level W."""
    bright = measures.smooth(curves["bright_oct"], SMOOTH_S, hz)
    loud = measures.smooth(curves["loud_db"], SMOOTH_S, hz)
    hits = np.array(sorted(float(h[0]) for name in ("snare", "tom", "kick") for h in pieces.get(name, []) if h[2] != "W"))
    main = np.array([b["t"] for b in beats if b.get("main")])
    out: List[dict] = []
    previous = 0.0
    for r in releases:
        t1 = r["t"]
        t0 = max(previous, t1 - LOOK_BACK_S, 0.0)
        previous = t1
        why, starts = [], []
        rise_b, at_b = _rise(bright, t0, t1, hz, BRIGHT_DIP_OCT)
        if rise_b >= BRIGHT_RISE_OCT and t1 - at_b >= MIN_LENGTH_S:
            why.append("getting brighter")
            starts.append(at_b)
        rise_l, at_l = _rise(loud, t0, t1, hz, LOUD_DIP_DB)
        if rise_l >= LOUD_RISE_DB and t1 - at_l >= MIN_LENGTH_S:
            why.append("getting louder")
            starts.append(at_l)
        roll = _roll_start(hits, t0, t1) if len(hits) else -1.0
        if roll >= 0.0:
            why.append("drum roll")
            starts.append(roll)
        kick_out = not any(k["start"] <= t1 - 1.0 < k["end"] for k in kick_stretches)
        needed = 1 if (kick_out and r["kind"] == "kick returns") else 2
        if len(why) < needed:
            continue
        start = min(starts)
        if len(main):
            start = float(main[int(np.argmin(np.abs(main - start)))])      # on a beat
        if t1 - start < MIN_LENGTH_S:
            continue
        out.append({"start": round(start, 3), "end": round(t1, 3), "level": "W",
                    "source": "guess: tension rising before the music comes back", "why": why + [r["kind"]]})
    return out
