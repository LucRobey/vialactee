"""
transitions/catalog/supernova.py - 3-Act Gravitational Collapse & Supernova Big Bang.
"""

import math
from typing import Optional
import numpy as np

from transitions.catalog._common import (
    TransitionFamily as F,
    TransitionSpec,
    central_epicenter,
    get_hash,
    norm_coords,
)


def apply_supernova(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act Gravitational Collapse & Supernova:
    - Act I (0.00..0.42): Event horizon shrinks inward, shifting old mode to Doppler violet.
    - Act II (0.42..0.56): Total room blackout except an accelerating white-hot core strobe.
    - Act III (0.56..1.00): Fast cyan precursor ring + wide gold-white plasma blast & stardust.
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
    nx, ny = norm_coords(n, coords, room_max_x, room_max_y)
    cx, cy = central_epicenter()
    dx = nx - cx
    dy = ny - cy
    max_span = max(0.35, float(math.hypot(max(cx, 1.0 - cx), max(cy, 1.0 - cy))))
    r_norm = np.clip(np.sqrt(dx * dx + dy * dy) / max_span, 0.0, 1.0)
    angle = np.arctan2(dy, dx)

    if progress < 0.42:
        p1 = progress / 0.42
        horizon = 1.05 - 0.88 * (p1 ** 1.35)
        luma = np.max(rgb_old, axis=1, keepdims=True) * (1.0 - 0.75 * p1)
        doppler = rgb_old * (1.0 - p1 * 0.85) + luma * np.array([0.45, 0.22, 1.0]) * (p1 * 0.85)
        np.clip(doppler, 0, 255, out=rgb_old, casting="unsafe")
        rgb_old[r_norm > horizon] = 0

        rings = np.cos((r_norm ** 0.8) * 18.0 + (p1 ** 2.0) * 28.0)
        mask_ring = (rings > 0.72) & (r_norm <= horizon)
        if np.any(mask_ring):
            rgb_old[mask_ring] = np.clip(rgb_old[mask_ring] + np.array([150, 110, 255]), 0, 255)
    elif progress < 0.56:
        p2 = (progress - 0.42) / 0.14
        rgb_old.fill(0)
        core_r = max(0.06, 0.18 * (1.0 - 0.35 * p2))
        core_mask = r_norm <= core_r
        if np.any(core_mask):
            strobe = 0.65 + 0.35 * math.cos((p2 ** 1.6) * 25.0)
            falloff = ((1.0 - r_norm[core_mask] / core_r) ** 1.4)[:, np.newaxis] * strobe
            rgb_old[core_mask] = np.clip(falloff * np.array([255, 245, 255]), 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.56) / 0.44
        rgb_old.fill(0)
        rays = 0.08 * np.sin(angle * 9.0 + 0.7) + 0.06 * np.cos(angle * 15.0)
        r_fast = (p3 ** 0.68) * 1.32
        r_main = ((p3 ** 0.86) * 1.18) * (0.94 + rays)

        mask_revealed = r_norm <= r_main
        np.copyto(rgb_old, rgb_new, where=mask_revealed[:, np.newaxis])

        fade = max(0.0, 1.0 - (p3 ** 1.45))
        precursor = (np.clip(1.0 - np.abs(r_norm - r_fast) / 0.09, 0.0, 1.0) ** 2) * fade
        blast = (np.clip(1.0 - np.abs(r_norm - r_main) / 0.18, 0.0, 1.0) ** 1.5) * fade
        sparks = (get_hash(n) > 0.78) & mask_revealed
        stardust = np.where(sparks, fade * 140.0, 0.0)

        out = (
            rgb_old
            + precursor[:, np.newaxis] * np.array([0, 235, 255])
            + blast[:, np.newaxis] * np.array([255, 235, 175])
            + stardust[:, np.newaxis]
        )
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="supernova",
    families=frozenset({F.ROOM_EPI_2D, F.RHYTHMIC_CHOP}),
    duration=3.4,
    kind="spatial_spectacle",
    handler=apply_supernova,
)
