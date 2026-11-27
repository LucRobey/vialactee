"""Grading: how close a recorded signal is to the truth. One function per kind of signal.

Every function returns plain numbers between 0 and 1 (and delays in seconds). Nothing here knows about tracks,
files or the Listener: inputs are times, masks and curves on the song's clock.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

MAY_GRADE = ("H", "A", "M2", "X")      # levels of evidence allowed to grade the analyzer (paper P1)


def rising_edges(values: np.ndarray, fps: float) -> np.ndarray:
    """Times at which an event signal fires: frames where it becomes true (or above 0) after being false."""
    on = np.nan_to_num(values, nan=0.0) > 0
    idx = np.flatnonzero(on & ~np.concatenate(([False], on[:-1])))
    return idx / fps


def match_events(est: Sequence[float], ref: Sequence[float], tol: float) -> Tuple[np.ndarray, np.ndarray]:
    """Pair each truth event with at most one estimated event within tol. Returns (ref -> est index or -1, offsets)."""
    est, ref = np.asarray(est, dtype=float), np.asarray(ref, dtype=float)
    pair = np.full(len(ref), -1, dtype=int)
    used = np.zeros(len(est), dtype=bool)
    j0 = 0
    for i, r in enumerate(ref):
        while j0 < len(est) and est[j0] < r - tol:
            j0 += 1
        best, bd = -1, tol
        j = j0
        while j < len(est) and est[j] <= r + tol:
            d = abs(est[j] - r)
            if not used[j] and d <= bd:
                best, bd = j, d
            j += 1
        if best >= 0:
            pair[i] = best
            used[best] = True
    offsets = np.array([est[p] - ref[i] for i, p in enumerate(pair) if p >= 0])
    return pair, offsets


def event_score(est: Sequence[float], ref: Sequence[float], tol: float, gradeable: Optional[Sequence[bool]] = None) -> Dict[str, float]:
    """Hits, misses and false alarms of an event signal.

    With `gradeable` (one flag per truth event), only flagged events count as hits or misses; an estimate that
    lands on an unflagged truth event is ignored rather than called a false alarm.
    """
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    pair, offsets = match_events(est, ref, tol)
    flag = np.ones(len(ref), dtype=bool) if gradeable is None else np.asarray(gradeable, dtype=bool)
    hits = int(np.sum((pair >= 0) & flag))
    misses = int(np.sum((pair < 0) & flag))
    false_alarms = int(len(est) - np.sum(pair >= 0))
    found = hits / (hits + misses) if hits + misses else float("nan")
    right = hits / (hits + false_alarms) if hits + false_alarms else float("nan")
    f1 = 2 * found * right / (found + right) if hits else (0.0 if (hits + misses) or false_alarms else float("nan"))
    return {"f1": f1, "found": found, "right": right, "n_truth": int(flag.sum()), "n_est": int(len(est)),
            "offset_ms": float(np.median(offsets) * 1000) if len(offsets) else float("nan")}


def regions_to_mask(regions: Sequence[Sequence[float]], n: int, fps: float) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    for a, b in regions:
        mask[max(0, int(round(a * fps))) : max(0, int(round(b * fps)))] = True
    return mask


def state_score(est: np.ndarray, ref: np.ndarray, fps: float, valid: Optional[np.ndarray] = None, edge_window: float = 5.0) -> Dict[str, float]:
    """A yes/no signal against a yes/no truth, frame by frame.

    `balanced` is the fair summary: the average of "right while the thing is on" and "right while it is off",
    so a signal stuck on one answer scores 0.5 whatever the song.
    """
    n = min(len(est), len(ref))
    est, ref = est[:n].astype(bool), ref[:n].astype(bool)
    ok = np.ones(n, dtype=bool) if valid is None else valid[:n]
    on, off = ref & ok, ~ref & ok
    when_on = float(np.mean(est[on])) if on.any() else float("nan")
    when_off = float(np.mean(~est[off])) if off.any() else float("nan")
    parts = [v for v in (when_on, when_off) if not np.isnan(v)]
    delays: List[float] = []
    for want in (True, False):                              # truth switches on, then truth switches off
        r_edges = np.flatnonzero(np.diff(ref.astype(np.int8)) == (1 if want else -1)) + 1
        e_edges = np.flatnonzero(np.diff(est.astype(np.int8)) == (1 if want else -1)) + 1
        for r in r_edges:
            if len(e_edges):
                d = (e_edges[np.argmin(np.abs(e_edges - r))] - r) / fps
                if abs(d) <= edge_window:
                    delays.append(float(d))
    return {"balanced": float(np.mean(parts)) if len(parts) == 2 else float("nan"),
            "when_on": when_on, "when_off": when_off,
            "share_on_truth": float(np.mean(ref[ok])) if ok.any() else float("nan"),
            "edge_delay_s": float(np.median(delays)) if delays else float("nan"), "edges_found": len(delays)}


def follow_score(est: np.ndarray, est_fps: float, ref: np.ndarray, ref_hz: float, valid: Optional[np.ndarray] = None,
                 max_lag: float = 1.0) -> Dict[str, float]:
    """How well a level follows the truth curve: best correlation within +-max_lag, and the lag that gives it.

    A positive lag means the signal is late. Units do not matter (dB against 0..1), only the shape does.
    """
    step = int(round(est_fps / ref_hz))
    m = min(len(est) // step, len(ref))
    if m < 20:
        return {"corr": float("nan"), "lag_ms": float("nan")}
    e = np.nan_to_num(est[: m * step].astype(float)).reshape(m, step).mean(axis=1)
    r = np.nan_to_num(ref[:m].astype(float))
    ok = np.ones(m, dtype=bool) if valid is None else valid[:m]
    best, best_lag = -2.0, 0
    for lag in range(-int(max_lag * ref_hz), int(max_lag * ref_hz) + 1):
        a = e[max(0, lag) : m + min(0, lag)]
        b = r[max(0, -lag) : m - max(0, lag)]
        k = ok[max(0, -lag) : m - max(0, lag)]
        if k.sum() < 20 or np.std(a[k]) < 1e-9 or np.std(b[k]) < 1e-9:
            continue
        c = float(np.corrcoef(a[k], b[k])[0, 1])
        if c > best:
            best, best_lag = c, lag
    if best < -1.5:
        return {"corr": float("nan"), "lag_ms": float("nan")}
    return {"corr": best, "lag_ms": 1000.0 * best_lag / ref_hz}


def tempo_score(est_bpm: np.ndarray, fps: float, beat_times: Sequence[float], beat_bpm: Sequence[float]) -> Dict[str, float]:
    """Tempo read at each truth beat: right level, double, half, or other."""
    t, ref = np.asarray(beat_times, dtype=float), np.asarray(beat_bpm, dtype=float)
    idx = np.clip(np.round(t * fps).astype(int), 0, len(est_bpm) - 1)
    est = est_bpm[idx]
    ok = (ref > 0) & np.isfinite(est) & (est > 0)
    if not ok.any():
        return {"right": float("nan"), "double": float("nan"), "half": float("nan"), "n": 0}
    ratio = est[ok] / ref[ok]
    return {"right": float(np.mean(np.abs(ratio - 1.0) <= 0.04)), "double": float(np.mean(np.abs(ratio - 2.0) <= 0.08)),
            "half": float(np.mean(np.abs(ratio - 0.5) <= 0.02)), "n": int(ok.sum())}


def equal_score(est: np.ndarray, ref: np.ndarray, valid: Optional[np.ndarray] = None) -> float:
    """Share of the samples where a counted value (bar position, layers...) equals the truth."""
    n = min(len(est), len(ref))
    ok = np.isfinite(est[:n]) if valid is None else (valid[:n] & np.isfinite(est[:n]))
    return float(np.mean(np.round(est[:n][ok]) == np.round(ref[:n][ok]))) if ok.any() else float("nan")


def peak_times(values: np.ndarray, fps: float, rel: float = 0.3, min_sep: float = 0.1) -> np.ndarray:
    """Times of the local peaks of a curve above `rel` times its loud level (99th percentile)."""
    v = np.nan_to_num(values.astype(float))
    thr = rel * float(np.percentile(v, 99))
    if thr <= 0:
        return np.array([])
    idx = np.flatnonzero((v[1:-1] >= thr) & (v[1:-1] > v[:-2]) & (v[1:-1] >= v[2:])) + 1
    keep: List[int] = []
    sep = max(1, int(round(min_sep * fps)))
    for i in idx[np.argsort(-v[idx], kind="stable")]:
        if all(abs(i - j) >= sep for j in keep):
            keep.append(int(i))
    return np.sort(np.array(keep, dtype=float)) / fps
