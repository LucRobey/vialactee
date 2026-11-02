"""
transitions/catalog/flash_cut.py - Zero-Latency Transient Impact Cut.
"""

import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec


def apply_flash_cut(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Zero-latency transient impact cut for real-time drops.
    Flashes brightly at progress ~ 0 and decays smoothly into the incoming mode.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    if progress < 0.15:
        p1 = progress / 0.15
        flash = p1 * 160.0
        blended = rgb_old * (1.0 - p1 * 0.5) + rgb_new * (0.5 + 0.5 * p1) + flash
    else:
        p2 = (progress - 0.15) / 0.85
        decay_exp = max(1.2, min(4.0, float(ACTIVE_PARAMS.get("flash_decay", 2.2)) * 0.4))
        decay = ((1.0 - p2) ** decay_exp) * 160.0
        blended = rgb_new + decay
    np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="flash_cut",
    families=frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    duration=0.8,
    kind="strip_1d",
    handler=apply_flash_cut,
)
