"""
transitions/catalog/tesla_arc.py - 3-Act High-Voltage Yellow Lightning Charge & Plasma Surge.
"""

import math
from typing import Optional
import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    TransitionFamily as F,
    TransitionSpec,
    get_hash,
    norm_coords,
)


def apply_tesla_arc(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act High-Voltage Yellow Lightning Charge & Bottom-to-Top Surge:
    - Act I (0.00..0.28): Short-circuit drain with crackling electric yellow spark nodes.
    - Act II (0.28..0.65): Downward yellow-white lightning bolts charge the bottom capacitor pool.
    - Act III (0.65..1.00): Bottom-to-top vertical plasma surge snaps incoming mode on.
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
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))
    h = get_hash(n)

    if progress < 0.28:
        p1 = progress / 0.28
        drain_line = p1 * 0.75
        dim = np.where(ny < drain_line, 0.08 * (1.0 - p1), 1.0 - 0.72 * p1)[:, np.newaxis]
        spark_wave = np.sin(nx * 29.0 + ny * 19.0 - p1 * 38.0 + seed) + 0.5 * np.cos(h * 31.0 + p1 * 24.0)
        yellow_sparks = np.clip((spark_wave - 0.65) / 0.75, 0.0, 1.0)[:, np.newaxis] * spark
        base_charge = np.clip((ny - (0.92 - 0.14 * p1)) / 0.16, 0.0, 1.0)[:, np.newaxis] * p1
        out = (
            rgb_old * dim
            + yellow_sparks * np.array([255.0, 230.0, 35.0])
            + base_charge * np.array([255.0, 210.0, 25.0])
        )
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")
    elif progress < 0.65:
        p2 = (progress - 0.28) / 0.37
        rgb_old.fill(0)
        strikes = float(max(3, int(ACTIVE_PARAMS.get("chop_count", 4))))
        s_pos = p2 * strikes
        s_idx = math.floor(s_pos)
        s_frac = s_pos - s_idx

        bolt_y = min(1.05, s_frac * 1.45)
        jag_x = 0.48 + 0.44 * (0.5 + 0.5 * math.sin(s_idx * 2.7 + seed)) + 0.08 * np.sin(ny * 18.0 + s_idx * 4.0)
        dist_x = np.abs(nx - jag_x)
        branch = np.clip(1.0 - dist_x / 0.24, 0.0, 1.0) * np.clip(1.0 - np.abs(ny - bolt_y) / 0.42, 0.0, 1.0)
        cross_arc = np.clip(np.cos(nx * 18.0 + ny * 14.0 - p2 * 36.0 + seed) - 0.52, 0.0, 0.48) / 0.48
        bolt = np.clip(branch * 1.15 + cross_arc * 0.65 * (1.0 - 0.4 * s_frac), 0.0, 1.0)[:, np.newaxis] * spark

        cap_top = 0.96 - 0.24 * p2
        cap_glow = np.clip((ny - cap_top) / 0.20, 0.0, 1.0)[:, np.newaxis] * (0.65 + 0.35 * math.sin(p2 * 30.0))

        arc_rgb = (
            (bolt + cap_glow) * np.array([255.0, 220.0, 30.0])
            + ((bolt ** 2.5) + (cap_glow ** 2.0)) * np.array([255.0, 255.0, 195.0])
        )
        np.clip(arc_rgb, 0, 255, out=rgb_old, casting="unsafe")
    else:
        p3 = (progress - 0.65) / 0.35
        surge_y = 1.05 - (p3 ** 0.80) * 1.20
        rgb_old.fill(0)
        mask_ignited = ny >= surge_y
        np.copyto(rgb_old, rgb_new, where=mask_ignited[:, np.newaxis])
        corona = np.clip(1.0 - np.abs(ny - surge_y) / 0.18, 0.0, 1.0) * (1.0 - p3 * 0.75)
        afterglow = (1.0 - p3) ** 2 * 0.35
        out = rgb_old + (corona[:, np.newaxis] + afterglow) * np.array([150.0, 225.0, 255.0])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="tesla_arc",
    families=frozenset({F.ROOM_EPI_2D, F.STOCHASTIC_ORGANIC, F.RHYTHMIC_CHOP}),
    duration=2.8,
    kind="spatial_spectacle",
    handler=apply_tesla_arc,
)
