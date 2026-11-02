"""
transitions/catalog/liquid_geyser.py - 3-Act Hydraulic Gravity Drain, Elastic Splash & Rising Tide.
"""

import math
from typing import Optional
import numpy as np

from transitions.catalog._common import TransitionFamily as F, TransitionSpec, norm_coords


def apply_liquid_geyser(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act Hydraulic Gravity Drain, Elastic Splash & Rising Tide:
    - Act I (0.00..0.44): Sloshing cyan-white meniscus drains old mode top-to-bottom into darkness.
    - Act II (0.44..0.56): Drained liquid slams into the lower tiers, splashing upward & transmuting to new mode.
    - Act III (0.56..1.00): Continuous rising tide floods back up the pillars & horizontal tiers to the canopy.
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

    if progress < 0.44:
        p1 = progress / 0.44
        slosh = 0.035 * np.sin(nx * 14.0 + p1 * 12.0)
        level_y = 0.78 * (p1 ** 1.15) + slosh
        rgb_old[ny < level_y] = 0
        rim = np.clip(1.0 - np.abs(ny - level_y) / 0.12, 0.0, 1.0) ** 1.6
        if np.any(rim > 0.0):
            rgb_old[:] = np.clip(rgb_old + rim[:, np.newaxis] * np.array([120, 235, 255]), 0, 255).astype(np.int32)
    elif progress < 0.56:
        p2 = (progress - 0.44) / 0.12
        bounce_y = 0.78 - 0.14 * math.sin(p2 * math.pi) + 0.04 * np.cos(nx * 18.0 - p2 * 10.0)
        mix_new = p2 * p2 * (3.0 - 2.0 * p2)
        base_pool = rgb_old * (1.0 - mix_new) + rgb_new * mix_new
        rgb_old.fill(0)
        submerged = ny >= bounce_y
        if np.any(submerged):
            rgb_old[submerged] = np.clip(base_pool[submerged], 0, 255).astype(np.int32)
        splash = np.clip(1.0 - np.abs(ny - bounce_y) / 0.16, 0.0, 1.0) ** 1.4
        rgb_old[:] = np.clip(rgb_old + splash[:, np.newaxis] * np.array([180, 245, 255]), 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.56) / 0.44
        wave = 0.035 * np.sin(nx * 16.0 - p3 * 14.0) * (1.0 - p3)
        tide_y = 0.76 - (p3 ** 0.82) * 0.90 + wave
        rgb_old.fill(0)
        mask_filled = ny >= tide_y
        np.copyto(rgb_old, rgb_new, where=mask_filled[:, np.newaxis])
        fade = max(0.0, 1.0 - (p3 ** 1.45))
        foam = (np.clip(1.0 - np.abs(ny - tide_y) / 0.16, 0.0, 1.0) ** 1.4) * fade
        out = rgb_old + foam[:, np.newaxis] * np.array([200, 248, 255])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="liquid_geyser",
    families=frozenset({F.ROOM_SWEEP_2D}),
    duration=3.4,
    kind="spatial_spectacle",
    handler=apply_liquid_geyser,
)
