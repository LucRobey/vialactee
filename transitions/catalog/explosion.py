"""
transitions/catalog/explosion.py - 3-Act Radial Shockwave Explosion.
"""

import math
import numpy as np

from transitions.catalog._common import ROOM_MAX_X, ROOM_MAX_Y, TransitionFamily as F, TransitionSpec, central_epicenter


def apply_explosion(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """Concentric inward-collapsing rings to a brief blackout, then a radial shockwave explosion."""
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
    dist = np.sqrt(dx ** 2 + dy ** 2)
    angle = np.arctan2(dy, dx)
    max_radius = float(math.hypot(max(cx, ROOM_MAX_X - cx), max(cy, ROOM_MAX_Y - cy)))
    max_radius = max(120.0, max_radius)

    t_implode = 0.52
    t_blackout = 0.60

    if progress < t_implode:
        p1 = progress / t_implode
        implode_horizon = max_radius * (1.05 - 0.92 * (p1 ** 1.35))
        darken_factor = max(0.0, 1.0 - (p1 * 1.4))
        np.multiply(rgb_list_old, darken_factor, out=rgb_list_old, casting="unsafe")
        rgb_list_old[dist > implode_horizon] = 0

        time_mapped = (p1 ** 2.2) * 55.0
        dist_warp = dist ** 0.82
        rings = np.cos(dist_warp * 0.14 + time_mapped)

        mask_energy = (rings > 0.78) & (dist <= implode_horizon)
        if np.any(mask_energy):
            rgb_list_old[mask_energy] = [200, 230, 255]
        core_mask = dist < max(18.0, max_radius * 0.12 * (1.0 - 0.5 * p1))
        if np.any(core_mask):
            rgb_list_old[core_mask] = [255, 255, 255]

    elif progress < t_blackout:
        rgb_list_old.fill(0)

    else:
        p2 = (progress - t_blackout) / (1.0 - t_blackout)
        beam_raw1 = np.sin(angle * 12.0)
        beam_raw2 = np.sin(angle * 19.0 + 1.4)
        beam_shape = (np.clip(beam_raw1, 0, 1) ** 3) * 0.22 + (np.clip(beam_raw2, 0, 1) ** 2) * 0.18
        front_depth = max(65.0, max_radius * 0.28)
        base_expansion = (max_radius + front_depth) * (p2 ** 0.85)
        jagged_radius = base_expansion * (0.88 + beam_shape)

        mask_swallowed = dist < jagged_radius
        rgb_list_old.fill(0)
        np.copyto(rgb_list_old, rgb_list_new, where=mask_swallowed[:, np.newaxis])

        dist_from_front = jagged_radius - dist
        mask_blast = (dist_from_front > 0) & (dist_from_front < front_depth)

        if np.any(mask_blast):
            edge_intensity = 1.0 - (dist_from_front[mask_blast] / front_depth)
            global_energy = 1.0 - (p2 ** 1.6)
            fire_alpha = np.clip(edge_intensity * global_energy * 1.25, 0.0, 1.0)[:, np.newaxis]
            base_color = rgb_list_old[mask_blast]
            blast_color = np.array([255, 255, 255], dtype=np.int32)
            blended = (base_color * (1.0 - fire_alpha) + blast_color * fire_alpha).astype(np.int32)
            rgb_list_old[mask_blast] = blended


SPEC = TransitionSpec(
    name="explosion",
    families=frozenset({F.ROOM_EPI_2D, F.RHYTHMIC_CHOP}),
    duration=2.4,
    kind="spatial_room",
    handler=apply_explosion,
    aliases=("transient_blip",),
)
