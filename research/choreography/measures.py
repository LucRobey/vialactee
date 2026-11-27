"""Measures: numbers read from the rendered frames of a clip, to filter out what clearly does not work.

A measure is never a score to push up (paper P3): each will get a threshold, and a mode either passes or not.
No threshold is set yet; the numbers are shown next to the clips so the owner can see how they relate to what
looks good.

    kick punch      does the light jump on a kick, more than it does between two kicks?
    alive           outside silence, is there light, and does it move?
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np

PUNCH_BEFORE_S = (-0.08, -0.02)     # window before a kick: the level the light is at
PUNCH_AFTER_S = (0.0, 0.10)         # window after a kick: how high it jumps
DARK: float = 0.02


def _jump(bright: np.ndarray, fps: float, times: Sequence[float]) -> List[float]:
    out = []
    for t in times:
        a0, a1 = int((t + PUNCH_BEFORE_S[0]) * fps), int((t + PUNCH_BEFORE_S[1]) * fps) + 1
        b0, b1 = int((t + PUNCH_AFTER_S[0]) * fps), int((t + PUNCH_AFTER_S[1]) * fps) + 1
        if a0 < 0 or b1 > len(bright):
            continue
        out.append(float(bright[b0:b1].max() - bright[a0:a1].mean()))
    return out


def kick_punch(bright: np.ndarray, fps: float, kick_times: Sequence[float]) -> Dict[str, float]:
    """Jump of brightness on the true kicks, against the jump at the instants halfway between two kicks.

    `contrast` is the difference of the two medians, in share of full brightness: 0 means the light does not
    know where the kicks are, 0.2 means it jumps a fifth of full brightness more on a kick than off it.
    """
    kicks = sorted(t for t in kick_times if 0.0 <= t < len(bright) / fps)
    between = [(a + b) / 2.0 for a, b in zip(kicks[:-1], kicks[1:]) if 0.25 < b - a < 2.0]
    on, off = _jump(bright, fps, kicks), _jump(bright, fps, between)
    if len(on) < 4 or len(off) < 4:
        return {"contrast": float("nan"), "on_kick": float("nan"), "between": float("nan"), "kicks": len(on)}
    return {"contrast": float(np.median(on) - np.median(off)), "on_kick": float(np.median(on)),
            "between": float(np.median(off)), "kicks": len(on)}


def alive(bright: np.ndarray, silent: np.ndarray) -> Dict[str, float]:
    """Share of the non-silent frames that are lit, and how much the brightness moves there."""
    ok = ~silent[: len(bright)] if len(silent) >= len(bright) else np.ones(len(bright), dtype=bool)
    if not ok.any():
        return {"lit": float("nan"), "movement": float("nan")}
    return {"lit": float(np.mean(bright[ok] > DARK)), "movement": float(np.std(bright[ok]))}
