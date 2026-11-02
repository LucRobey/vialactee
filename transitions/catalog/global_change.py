"""
transitions/catalog/global_change.py - 3-Act Prism Rave Takeover (`global_change`).
"""

import math
import numpy as np

from transitions.catalog._common import TransitionFamily as F, TransitionSpec


def apply_colorful_glitch(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float) -> None:
    """3-Act Prism Rave Takeover (`global_change`): neon block strobe -> polyrhythmic cascade -> smooth bloom."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
    n = len(rgb_list_old)
    if n == 0:
        return
    u = np.arange(n, dtype=np.float64) / max(1.0, float(n - 1))
    palette = np.array(
        [[255, 20, 180], [0, 245, 255], [255, 215, 0], [160, 40, 255], [40, 255, 140], [255, 90, 20]],
        dtype=np.float64,
    )
    if progress < 0.32:
        p1 = progress / 0.32
        step = int(p1 * 6.0)
        blocks = np.floor(u * (4.0 + step)).astype(np.int32)
        active = (blocks % 2) == (step % 2)
        prism = palette[(blocks + step) % len(palette)]
        rgb_list_old[~active] = (rgb_list_old[~active] * (0.25 * (1.0 - p1))).astype(np.int32)
        rgb_list_old[active] = np.clip(rgb_list_old[active] * 0.35 + prism[active] * 0.85, 0, 255).astype(np.int32)
    elif progress < 0.72:
        p2 = (progress - 0.32) / 0.40
        step = int(p2 * 10.0)
        blocks = np.floor((u + step * 0.13) * (6.0 + step * 0.8)).astype(np.int32)
        mode_sel = (blocks + step) % 3
        c_idx = (blocks * 2 + step) % len(palette)
        rgb_list_old.fill(0)
        np.copyto(rgb_list_old, rgb_list_new, where=(mode_sel == 0)[:, np.newaxis])
        mask_prism = mode_sel == 1
        if np.any(mask_prism):
            rgb_list_old[mask_prism] = np.clip(
                rgb_list_new[mask_prism] * 0.35 + palette[c_idx[mask_prism]] * 0.90, 0, 255
            ).astype(np.int32)
    else:
        p3 = (progress - 0.72) / 0.28
        smooth = p3 * p3 * (3.0 - 2.0 * p3)
        c_idx = (np.floor(u * 8.0).astype(np.int32) + int(p3 * 6.0)) % len(palette)
        shimmer = (1.0 - smooth) * 0.55 * (0.5 + 0.5 * np.cos((u * 12.0 - p3 * 8.0) * math.pi))[:, np.newaxis]
        np.clip(rgb_list_new + palette[c_idx] * shimmer, 0, 255, out=rgb_list_old, casting="unsafe")


SPEC = TransitionSpec(
    name="global_change",
    families=frozenset({F.STOCHASTIC_ORGANIC, F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    duration=2.0,
    kind="strip_1d",
    handler=apply_colorful_glitch,
)
