"""
transitions/catalog/silk_wipe.py - Soft-Feathered 1D Strip Wipes (Forward & Reverse).
"""

import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    TransitionFamily as F,
    TransitionSpec,
    blend_with_crest,
    get_u,
)


def apply_silk_wipe(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    progress: float,
    reverse: bool = False,
) -> None:
    """Soft-feathered 1D strip wipe with an S-curve wavefront and mode-tinted crest."""
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
    field = (1.0 - u) if reverse else u
    win = max(0.06, float(ACTIVE_PARAMS.get("edge_width", 0.22)))
    t = np.clip((progress * (1.0 + win) - field) / win, 0.0, 1.0)
    blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.25)


def apply_silk_wipe_forward(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    apply_silk_wipe(rgb_old, rgb_new, progress, reverse=False)


def apply_silk_wipe_reverse(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    apply_silk_wipe(rgb_old, rgb_new, progress, reverse=True)


SPECS = (
    TransitionSpec(
        name="silk_wipe",
        families=frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
        duration=1.8,
        kind="strip_1d",
        handler=apply_silk_wipe_forward,
    ),
    TransitionSpec(
        name="silk_wipe_reverse",
        families=frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
        duration=1.8,
        kind="strip_1d",
        handler=apply_silk_wipe_reverse,
    ),
)
