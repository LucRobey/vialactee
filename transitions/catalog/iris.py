"""
transitions/catalog/iris.py - Symmetrical 1D Curtain Wipes (iris_open & iris_close).
"""

import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    TransitionFamily as F,
    TransitionSpec,
    blend_with_crest,
    get_u,
)


def apply_iris_transition(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    progress: float,
    close_in: bool = False,
) -> None:
    """
    Symmetrical 1D curtain wipe around focal_u (default 0.5):
    - close_in=False ('iris_open'): blooms from focal_u to both tips (u=0, 1).
    - close_in=True ('iris_close'): sweeps from both tips inward to meet at focal_u.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    n = len(rgb_old)
    if n == 0:
        return
    u = get_u(n)
    focal = float(ACTIVE_PARAMS.get("focal_u", 0.5))
    span = max(focal, 1.0 - focal, 0.1)
    dist_center = np.clip(np.abs(u - focal) / span, 0.0, 1.0)
    field = (1.0 - dist_center) if close_in else dist_center
    win = 0.20
    t = np.clip((progress * (1.0 + win) - field) / win, 0.0, 1.0)
    blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.25)


def apply_iris_open(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    apply_iris_transition(rgb_old, rgb_new, progress, close_in=False)


def apply_iris_close(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    apply_iris_transition(rgb_old, rgb_new, progress, close_in=True)


SPECS = (
    TransitionSpec(
        name="iris_open",
        families=frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
        duration=1.8,
        kind="strip_1d",
        handler=apply_iris_open,
    ),
    TransitionSpec(
        name="iris_close",
        families=frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
        duration=1.8,
        kind="strip_1d",
        handler=apply_iris_close,
    ),
)
