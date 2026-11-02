"""
transitions/catalog/luma_melt.py - Content-Aware Luminance-Keyed Dissolve.
"""

import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, blend_with_crest


def apply_luma_melt(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Content-aware luminance-keyed dissolve: brightest features of the incoming mode
    burn through first while dim background regions melt last.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    if len(rgb_old) == 0:
        return
    luma_new = np.max(rgb_new, axis=1) * (1.0 / 255.0)
    luma_old = np.max(rgb_old, axis=1) * (1.0 / 255.0)
    threshold = np.clip(0.55 * (1.0 - luma_new) + 0.20 * luma_old, 0.0, 0.75)
    win = 0.25
    t = np.clip((progress - threshold) / win, 0.0, 1.0)
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))
    blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.15 * spark)


SPEC = TransitionSpec(
    name="luma_melt",
    families=frozenset({F.STOCHASTIC_ORGANIC, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.0,
    kind="strip_1d",
    handler=apply_luma_melt,
)
