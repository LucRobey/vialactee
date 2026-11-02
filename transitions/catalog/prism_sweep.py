"""
transitions/catalog/prism_sweep.py - Chromatic Dispersion Rainbow Edge Wipe.
"""

import math
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, get_u


def apply_prism_sweep(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Chromatic dispersion wipe: R, G, and B channels sweep with slight phase offsets,
    refracting the modes' colors into a natural rainbow prism edge at the boundary.
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
    win = max(0.08, float(ACTIVE_PARAMS.get("edge_width", 0.20)))
    shift = 0.08 * math.sin(progress * math.pi)
    for ch, offset in enumerate((shift, 0.0, -shift)):
        p_ch = np.clip(progress + offset, 0.0, 1.0)
        t = np.clip((p_ch * (1.0 + win) - u) / win, 0.0, 1.0)
        w = t * t * (3.0 - 2.0 * t)
        crest = 4.0 * t * (1.0 - t) * 0.22
        val = rgb_old[:, ch] * (1.0 - w) + rgb_new[:, ch] * w + (rgb_old[:, ch] + rgb_new[:, ch]) * crest
        rgb_old[:, ch] = np.clip(val, 0, 255).astype(np.int32)


SPEC = TransitionSpec(
    name="prism_sweep",
    families=frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.0,
    kind="strip_1d",
    handler=apply_prism_sweep,
)
