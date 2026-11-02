"""
transitions/catalog/staccato_shutter.py - Beat-Ratcheted Iris Shutter Transition.
"""

import math
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec
from transitions.catalog.iris import apply_iris_transition


def apply_staccato_shutter(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Beat-ratcheted iris shutter: snaps forward in N distinct kinetic surges
    instead of moving at constant linear velocity.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    steps = float(max(2, int(ACTIVE_PARAMS.get("chop_count", 4))))
    s = progress * steps
    k = math.floor(s)
    frac = s - k
    snapped_frac = min(1.0, frac * 1.8) ** 2
    p_ratchet = min(1.0, (k + snapped_frac) / steps)
    apply_iris_transition(rgb_old, rgb_new, p_ratchet, close_in=False)


SPEC = TransitionSpec(
    name="staccato_shutter",
    families=frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    duration=1.2,
    kind="strip_1d",
    handler=apply_staccato_shutter,
)
