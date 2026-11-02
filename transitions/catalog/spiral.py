"""
transitions/catalog/spiral.py - 3-Act Logarithmic Galaxy Vortex.
"""

import math
import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    ROOM_MAX_X,
    ROOM_MAX_Y,
    TransitionFamily as F,
    TransitionSpec,
    apply_field_wipe,
    central_epicenter,
)


def apply_spiral_transition(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    """3-Act Logarithmic Galaxy Vortex: spin-up gravity drain -> eye of the storm -> multi-arm spiral shockwave unwind."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    ex, ey = central_epicenter()
    cx = ROOM_MAX_X * ex
    cy = ROOM_MAX_Y * ey
    dx = coords[:, 0] - cx
    dy = coords[:, 1] - cy
    max_r = max(120.0, float(math.hypot(max(cx, ROOM_MAX_X - cx), max(cy, ROOM_MAX_Y - cy))))
    r_norm = np.clip(np.sqrt(dx * dx + dy * dy) / max_r, 0.0, 1.0)
    angles = np.arctan2(dy, dx)
    sign = -1.0 if float(ACTIVE_PARAMS.get("spiral_sign", 1.0)) < 0.0 else 1.0
    arms = max(1, int(ACTIVE_PARAMS.get("spiral_arms", 2)))

    if progress < 0.34:
        p1 = progress / 0.34
        horizon = 1.05 - 0.82 * (p1 ** 1.3)
        np.multiply(rgb_list_old, max(0.0, 1.0 - p1 * 1.25), out=rgb_list_old, casting="unsafe")
        rgb_list_old[r_norm > horizon] = 0
        phase = arms * angles + sign * (7.5 * (r_norm ** 0.85) - (p1 ** 1.8) * 12.0)
        arm_crest = np.clip(np.cos(phase), 0.0, 1.0) ** 3
        mask_arm = (arm_crest > 0.35) & (r_norm <= horizon)
        if np.any(mask_arm):
            a = arm_crest[mask_arm][:, np.newaxis]
            rgb_list_old[mask_arm] = np.clip(rgb_list_old[mask_arm] + a * np.array([90, 210, 255]), 0, 255).astype(np.int32)
    elif progress < 0.44:
        p2 = (progress - 0.34) / 0.10
        rgb_list_old.fill(0)
        eye_mask = r_norm <= 0.22
        if np.any(eye_mask):
            spin = 0.5 + 0.5 * np.cos(arms * angles[eye_mask] - sign * p2 * 8.0)
            core = ((1.0 - r_norm[eye_mask] / 0.22) * spin)[:, np.newaxis]
            rgb_list_old[eye_mask] = np.clip(core * np.array([210, 245, 255]), 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.44) / 0.56
        arm_wave = 0.5 * (1.0 + np.cos(arms * angles + sign * (6.5 * (r_norm ** 0.85) - p3 * 8.0)))
        spiral_field = np.clip(0.70 * r_norm + 0.30 * (1.0 - arm_wave), 0.0, 1.0)
        rgb_list_old.fill(0)
        apply_field_wipe(rgb_list_old, rgb_list_new, spiral_field, p3, beam_thickness)


SPEC = TransitionSpec(
    name="spiral",
    families=frozenset({F.ROOM_EPI_2D}),
    duration=3.2,
    kind="spatial_wipe",
    handler=apply_spiral_transition,
)
