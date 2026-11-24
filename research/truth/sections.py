"""Section changes, found from our own measurements and placed on the first beat of a bar.

A section change is a bar line where the music after it is clearly not the music before it: a family of
instruments enters or leaves, the loudness steps, the sound opens or closes. For each bar line we compare the
average of the few bars before with the few bars after, over every curve the pipeline measures, and keep the
bar lines where that difference peaks. Each kept change says what changed, in words.

No trained model, no notion of verse or chorus: this works the same on techno and on rock.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

DB_FLOOR: float = -60.0
DB_UNIT: float = 6.0            # a 6 dB change in one curve counts as one unit of difference
CONTEXT_BARS: int = 8           # bars averaged on each side of a bar line
MIN_GAP_BARS: int = 8           # two changes are at least this many bars apart
MIN_SCORE: float = 2.5          # a change needs at least this much difference
LEVEL_CURVES: Tuple[Tuple[str, str], ...] = (
    ("stem_drums_db", "drums"), ("stem_bass_db", "bass"), ("stem_vocals_db", "voice"), ("stem_other_db", "instruments"),
    ("kick_db", "kick"), ("sub_db", "sub"), ("high_db", "treble"), ("loud_db", "loudness"),
)
ENTER_DB: float = 12.0          # a family rising or falling by this much has entered or left
REFINE_S: float = 2.0           # the exact instant is searched by comparing this many seconds before and after
SNAP_S: float = 0.35            # ...and moved onto a main beat when one is this close


def bar_lines(beats: Sequence[dict], duration: float) -> np.ndarray:
    """Start times of the bars: the beats numbered 1, with the gaps (no beat, unknown bars) filled evenly."""
    ones = np.array([b["t"] for b in beats if b.get("main", True) and b.get("bar_pos") == 1 and not b.get("no_beat")])
    if len(ones) < 4:
        return np.arange(0.0, duration, 2.0)
    bar = float(np.median(np.diff(ones)))
    pts = [0.0] if ones[0] > 0.5 * bar else []
    pts += list(ones) + [duration]
    out: List[float] = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(round((b - a) / bar))) if b - a > 1.5 * bar else 1
        out.extend(a + (b - a) * k / n for k in range(n))
    return np.array(out)


def scaled_frames(curves: Dict[str, np.ndarray]) -> Tuple[np.ndarray, List[str]]:
    """Every curve side by side, one row per frame, in comparable units."""
    names = [n for n, _ in LEVEL_CURVES if n in curves] + [n for n in ("bright_oct", "fullness") if n in curves]
    cols = []
    for name in names:
        c = np.nan_to_num(np.asarray(curves[name], dtype=float), nan=0.0)
        if name.endswith("_db"):
            c = np.clip(c, DB_FLOOR, 0.0) / DB_UNIT
        elif name == "fullness":
            c = c * 4.0             # the whole range from empty to full counts as four units
        cols.append(c)
    n = min(len(c) for c in cols)
    return np.stack([c[:n] for c in cols], axis=1), names


def bar_features(lines: np.ndarray, frames: np.ndarray, hz: int, duration: float) -> np.ndarray:
    """One row per bar: the average of every curve over that bar."""
    edges = np.append(lines, duration)
    rows = np.zeros((len(lines), frames.shape[1]))
    for i in range(len(lines)):
        a = int(edges[i] * hz)
        seg = frames[a : max(a + 1, int(edges[i + 1] * hz))]
        if len(seg):
            rows[i] = seg.mean(axis=0)
    return rows


def refine(t: float, bar: float, frames: np.ndarray, hz: int, beat_times: np.ndarray) -> float:
    """The exact instant of a change found at a bar line: the sharpest step within one bar, put on a beat."""
    w = int(REFINE_S * hz)
    lo, hi = max(w, int((t - bar) * hz)), min(len(frames) - w, int((t + bar) * hz))
    if hi <= lo:
        return t
    csum = np.vstack([np.zeros(frames.shape[1]), np.cumsum(frames, axis=0)])
    ks = np.arange(lo, hi + 1)
    step = np.linalg.norm((csum[ks + w] - csum[ks]) - (csum[ks] - csum[ks - w]), axis=1) / w
    best = float(ks[int(np.argmax(step))]) / hz
    if len(beat_times):
        j = int(np.argmin(np.abs(beat_times - best)))
        if abs(beat_times[j] - best) <= SNAP_S:
            return float(beat_times[j])
    return best


def _describe(delta: np.ndarray, names: List[str]) -> List[str]:
    """What changed across a bar line, in plain words, strongest first."""
    words: List[Tuple[float, str]] = []
    labels = dict(LEVEL_CURVES)
    for d, name in zip(delta, names):
        if name in labels and name != "loud_db" and abs(d) * DB_UNIT >= ENTER_DB:
            words.append((abs(d), f"{labels[name]} {'in' if d > 0 else 'out'}"))
        elif name == "loud_db" and abs(d) * DB_UNIT >= 3.0:
            words.append((abs(d), f"{'louder' if d > 0 else 'quieter'} {abs(d) * DB_UNIT:.0f} dB"))
        elif name == "bright_oct" and abs(d) >= 0.5:
            words.append((abs(d), "brighter" if d > 0 else "darker"))
        elif name == "fullness" and abs(d) >= 1.0:
            words.append((abs(d), "fuller" if d > 0 else "sparser"))
    return [w for _, w in sorted(words, reverse=True)[:3]]


def section_changes(beats: Sequence[dict], curves: Dict[str, np.ndarray], hz: int, duration: float) -> List[dict]:
    """Bar lines where the music changes, each as {t, strength 0..1, score, why}."""
    lines = bar_lines(beats, duration)
    if len(lines) < 2 * CONTEXT_BARS:
        return []
    frames, names = scaled_frames(curves)
    feats = bar_features(lines, frames, hz, duration)
    bar = float(np.median(np.diff(lines)))
    beat_times = np.array([b["t"] for b in beats if b.get("main", True)])
    n = len(lines)
    score = np.zeros(n)
    delta = np.zeros_like(feats)
    for i in range(1, n):
        before = feats[max(0, i - CONTEXT_BARS) : i].mean(axis=0)
        after = feats[i : min(n, i + CONTEXT_BARS)].mean(axis=0)
        delta[i] = after - before
        score[i] = float(np.linalg.norm(delta[i]))
    picked: List[int] = []
    for i in np.argsort(-score):
        if score[i] < MIN_SCORE:
            break
        if all(abs(int(i) - j) >= MIN_GAP_BARS for j in picked):
            picked.append(int(i))
    top = float(score.max()) or 1.0
    out = [
        {"t": round(refine(float(lines[i]), bar, frames, hz, beat_times), 3), "strength": round(float(score[i] / top), 2),
         "score": round(float(score[i]), 2), "why": _describe(delta[i], names)}
        for i in sorted(picked)
    ]
    return sorted(out, key=lambda c: c["t"])
