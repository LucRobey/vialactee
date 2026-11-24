"""Bars: where the "1" is, from the downbeats of two trackers laid on the merged beat grid.

Nothing here decides alone. Where the two trackers put the "1" on the same beat the answer is marked agreed;
where they do not, the position is given with the stronger tracker's choice and marked for review by ear.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

DOWNBEAT_TOL_S: float = 0.07
RUN_BREAK_FACTOR: float = 1.75     # a gap this many times the usual beat ends a run of beats
BLOCK_BEATS: int = 16


def flag_downbeats(beat_times: np.ndarray, downbeats: Sequence[float], tol: float = DOWNBEAT_TOL_S) -> np.ndarray:
    """For each grid beat: does this tracker call it a downbeat?"""
    flags = np.zeros(len(beat_times), dtype=bool)
    if len(beat_times) == 0:
        return flags
    for d in downbeats:
        i = int(np.argmin(np.abs(beat_times - d)))
        if abs(beat_times[i] - d) <= tol:
            flags[i] = True
    return flags


def beats_per_bar(flags: np.ndarray) -> Optional[int]:
    """Most common number of grid beats from one downbeat to the next."""
    idx = np.flatnonzero(flags)
    if len(idx) < 3:
        return None
    steps = np.diff(idx)
    vals, counts = np.unique(steps, return_counts=True)
    return int(vals[np.argmax(counts)])


def beat_runs(beat_times: np.ndarray, no_beat: np.ndarray) -> List[List[int]]:
    """Unbroken stretches of beats: split on long gaps and wherever a no-beat stretch starts or ends."""
    n = len(beat_times)
    if n == 0:
        return []
    iv = np.diff(beat_times)
    usual = float(np.median(iv)) if len(iv) else 0.5
    runs: List[List[int]] = [[0]]
    for i in range(1, n):
        local = float(np.median(iv[max(0, i - 9) : i])) if i > 1 else usual
        if iv[i - 1] > RUN_BREAK_FACTOR * local or bool(no_beat[i]) != bool(no_beat[i - 1]):
            runs.append([])
        runs[-1].append(i)
    return runs


def main_beat_mask(beat_times: np.ndarray, no_beat: np.ndarray, confirmed: np.ndarray, block: int = BLOCK_BEATS) -> np.ndarray:
    """Which grid beats are the beat a person would tap, and which are only the half-beats in between.

    The merged grid is drawn at the fastest level any tracker follows. Where the trackers agree on every
    other beat only (confirmed, not, confirmed, not...), the confirmed ones are the main beat.
    """
    mask = np.ones(len(beat_times), dtype=bool)
    for run in beat_runs(beat_times, no_beat):
        for a in range(0, len(run), block):
            idx = np.array(run[a : a + block])
            v = confirmed[idx]
            if len(idx) >= 8 and v.mean() < 0.7 and np.mean(v[1:] != v[:-1]) > 0.8:
                mask[idx] = v
    return mask


def _best_phase(flags: np.ndarray, pos: np.ndarray, meter: int) -> Optional[int]:
    counts = np.array([int(flags[pos % meter == p].sum()) for p in range(meter)])
    if counts.sum() == 0:
        return None
    return int(np.argmax(counts))


def bar_positions(
    beat_times: np.ndarray,
    no_beat: np.ndarray,
    flags_a: np.ndarray,
    flags_b: np.ndarray,
    meter: int = 4,
) -> Dict[str, np.ndarray]:
    """Position in the bar (1..meter) for every beat, block by block, and whether the two trackers agree.

    flags_a is the tracker followed when the two disagree. Returns arrays `pos` (0 where unknown) and
    `agreed` (True where both trackers put the "1" on the same beat of the block).
    """
    n = len(beat_times)
    pos_out = np.zeros(n, dtype=int)
    agreed = np.zeros(n, dtype=bool)
    for run in beat_runs(beat_times, no_beat):
        if not run or bool(no_beat[run[0]]):
            continue
        idx = np.array(run)
        local = np.arange(len(idx))
        for a in range(0, len(idx), BLOCK_BEATS):
            blk = slice(a, a + BLOCK_BEATS)
            pa = _best_phase(flags_a[idx[blk]], local[blk], meter)
            pb = _best_phase(flags_b[idx[blk]], local[blk], meter)
            phase = pa if pa is not None else pb
            if phase is None:
                continue
            pos_out[idx[blk]] = (local[blk] - phase) % meter + 1
            agreed[idx[blk]] = pa is not None and pa == pb
    return {"pos": pos_out, "agreed": agreed}


def local_bpm(beat_times: np.ndarray, no_beat: np.ndarray, span: int = 8) -> np.ndarray:
    """Tempo around each beat: from the median of the nearby beat intervals inside the same run."""
    bpm = np.zeros(len(beat_times))
    for run in beat_runs(beat_times, no_beat):
        if len(run) < 2:
            continue
        t = beat_times[run]
        iv = np.diff(t)
        for k, i in enumerate(run):
            seg = iv[max(0, k - span // 2) : k + span // 2]
            if len(seg):
                bpm[i] = 60.0 / float(np.median(seg))
    return bpm
