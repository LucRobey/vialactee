"""
transitions/catalog/pendulum_sweep.py - 3-Act Giant Ceiling Pendulum Double-Sweep.
"""

import math
from typing import Optional
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, norm_coords


def apply_pendulum_sweep(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act Giant Ceiling Pendulum Double-Sweep:
    - Act I (0.00..0.16): Outgoing mode dims to 28% silhouette.
    - Act II (0.16..0.56): Swing 1 sweeps across the chandelier, erasing old mode into pitch darkness.
    - Act III (0.56..1.00): Swing 2 swings back faster, painting incoming mode behind a prismatic beam.
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
    raw_ex = float(ACTIVE_PARAMS.get("epicenter_x", 0.62))
    pivot_x = 0.62 if abs(raw_ex - 0.5) < 1e-3 else raw_ex
    pivot_y = -0.45

    angles = np.arctan2(nx - pivot_x, ny - pivot_y)
    a_min = math.atan2(0.0 - pivot_x, 1.0 - pivot_y)
    a_max = math.atan2(1.0 - pivot_x, 1.0 - pivot_y)
    alpha = np.clip((angles - a_min) / max(0.1, a_max - a_min), 0.0, 1.0)
    if float(ACTIVE_PARAMS.get("spiral_sign", 1.0)) < 0.0:
        alpha = 1.0 - alpha

    beam_w = max(0.09, float(ACTIVE_PARAMS.get("beam_thickness", 0.15)))

    if progress < 0.16:
        p1 = progress / 0.16
        np.multiply(rgb_old, 1.0 - 0.72 * p1, out=rgb_old, casting="unsafe")
    elif progress < 0.56:
        p2 = (progress - 0.16) / 0.40
        swing = 0.5 * (1.0 - math.cos(p2 * math.pi)) * (1.0 + beam_w) - 0.5 * beam_w
        np.multiply(rgb_old, 0.28, out=rgb_old, casting="unsafe")
        rgb_old[alpha <= swing] = 0
        comet = np.clip(1.0 - np.abs(alpha - swing) / beam_w, 0.0, 1.0) ** 1.6
        if np.any(comet > 0.0):
            c = comet[:, np.newaxis]
            rgb_old[:] = np.clip(rgb_old + c * np.array([255, 185, 75]) + (c ** 3) * 110.0, 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.56) / 0.44
        ret = 1.0 - (0.5 * (1.0 - math.cos(p3 * math.pi)) * (1.0 + beam_w) - 0.5 * beam_w)
        rgb_old.fill(0)
        mask_painted = alpha >= ret
        np.copyto(rgb_old, rgb_new, where=mask_painted[:, np.newaxis])
        fade = max(0.0, 1.0 - (p3 ** 1.6))
        crest = (np.clip(1.0 - np.abs(alpha - ret) / (beam_w * 1.15), 0.0, 1.0) ** 1.5) * fade
        out = rgb_old + crest[:, np.newaxis] * np.array([170, 240, 255])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="pendulum_sweep",
    families=frozenset({F.ROOM_EPI_2D, F.ROOM_SWEEP_2D}),
    duration=3.2,
    kind="spatial_spectacle",
    handler=apply_pendulum_sweep,
)
