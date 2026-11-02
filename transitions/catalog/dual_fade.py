"""
transitions/catalog/dual_fade.py - Smooth Cosine Crossfade.
"""

import math
import numpy as np

from transitions.catalog._common import TransitionFamily as F, TransitionSpec


def apply_dual_fade(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float) -> None:
    """Crossfades old mode softly into new mode using smooth cosine curve."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    w = 0.5 * (1.0 - math.cos(math.pi * progress))
    np.multiply(rgb_list_old, 1.0 - w, out=rgb_list_old, casting="unsafe")
    np.add(rgb_list_old, rgb_list_new * w, out=rgb_list_old, casting="unsafe")


SPEC = TransitionSpec(
    name="fade_in_out",
    families=frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.0,
    kind="strip_1d",
    handler=apply_dual_fade,
    aliases=("smooth_cosine_crossfade",),
    self_typed_aliases=("fade_to_black", "cosine_fade"),
)
