"""
transitions/catalog/collider.py - 3-Act Hadron Particle Accelerator Transition.
"""

import math
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, get_u


def apply_collider(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    3-Act Hadron Particle Accelerator:
    - Act I (0.00..0.42): Vacuum drain + Cyan (u=0) and Magenta-Gold (u=1) packets accelerate toward focal_u.
    - Act II (0.42..0.56): Collision criticality — trembling white-violet plasma singularity in total darkness.
    - Act III (0.56..1.00): Dual shockwave detonation erupts outward to both strip ends at full power.
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
    focal = float(ACTIVE_PARAMS.get("focal_u", 0.5))
    span = max(focal, 1.0 - focal, 0.1)
    dist_center = np.clip(np.abs(u - focal) / span, 0.0, 1.0)

    if progress < 0.42:
        p1 = progress / 0.42
        vac = max(0.04, (1.0 - p1 * 1.35) ** 2) if p1 < 0.72 else 0.04
        np.multiply(rgb_old, vac, out=rgb_old, casting="unsafe")
        head_dist = 1.0 - (p1 ** 1.85)
        d_head = dist_center - head_dist
        trail = np.where((d_head >= 0.0) & (d_head < 0.28), (1.0 - d_head / 0.28) ** 2, 0.0)
        head = np.clip(1.0 - np.abs(d_head) / 0.11, 0.0, 1.0) ** 2
        tint = np.where((u <= focal)[:, np.newaxis], np.array([0, 235, 255]), np.array([255, 70, 220]))
        surge = rgb_old + trail[:, np.newaxis] * tint * 0.75 + head[:, np.newaxis] * np.array([255, 255, 255])
        np.clip(surge, 0, 255, out=rgb_old, casting="unsafe")
    elif progress < 0.56:
        p2 = (progress - 0.42) / 0.14
        rgb_old.fill(0)
        core_r = 0.08 + 0.07 * math.sin(p2 * math.pi)
        core_glow = np.clip(1.0 - dist_center / max(0.04, core_r), 0.0, 1.0) ** 1.5
        if np.any(core_glow > 0.0):
            c = core_glow[:, np.newaxis]
            pulse = 0.75 + 0.25 * math.cos(p2 * 18.0)
            rgb_old[:] = np.clip(c * pulse * np.array([235, 210, 255]) + (c ** 3) * 120.0, 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.56) / 0.44
        blast_r = (p3 ** 0.78) * 1.16
        rgb_old.fill(0)
        mask_swallowed = dist_center <= blast_r
        np.copyto(rgb_old, rgb_new, where=mask_swallowed[:, np.newaxis])
        fade_out = max(0.0, 1.0 - (p3 ** 1.5))
        rim = (np.clip(1.0 - np.abs(dist_center - blast_r) / 0.16, 0.0, 1.0) ** 1.6) * fade_out
        aftershock = (np.clip(1.0 - np.abs(dist_center - blast_r * 0.62) / 0.09, 0.0, 1.0) ** 2) * fade_out * 0.65
        out = rgb_old + rim[:, np.newaxis] * np.array([230, 250, 255]) + aftershock[:, np.newaxis] * np.array([255, 90, 230])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="collider",
    families=frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE}),
    duration=3.0,
    kind="strip_1d",
    handler=apply_collider,
)
