"""
transitions/catalog/ember_dissolve.py - Sparkle / Spatial Dither Dissolve.
"""

import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    TransitionFamily as F,
    TransitionSpec,
    blend_with_crest,
    get_hash,
)


def apply_ember_dissolve(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Sparkle / spatial dither dissolve. Pixels flip in deterministic twinkling clusters
    with an ember glow peak, preventing the 50% grey brightness valley of linear fades.
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
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))
    base_h = get_hash(n)
    h = np.mod(base_h + seed, 1.0) if seed != 0.0 else base_h
    win = 0.28
    t = np.clip((progress * (1.0 + win) - h) / win, 0.0, 1.0)
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))
    blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.30 * spark)


SPEC = TransitionSpec(
    name="ember_dissolve",
    families=frozenset({F.STOCHASTIC_ORGANIC, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.2,
    kind="strip_1d",
    handler=apply_ember_dissolve,
)
