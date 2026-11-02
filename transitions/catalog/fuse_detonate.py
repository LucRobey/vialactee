"""
transitions/catalog/fuse_detonate.py - 3-Act Gunpowder Fuse & Backfire Detonation.
"""

import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, get_hash, get_u


def apply_fuse_detonate(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    progress: float,
) -> None:
    """
    3-Act Gunpowder Fuse & Backfire Detonation:
    - Act I (0.00..0.18): Chandelier drops to 6% dark silhouette as fuse spark ignites at u=0.
    - Act II (0.18..0.62): Scorching orange-white fuse sprints u=0->1 with sputtering gold embers.
    - Act III (0.62..1.00): Fuse hits u=1 and detonates backward (u=1->0), blasting new mode open.
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
    h = get_hash(n)
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))

    if progress < 0.18:
        p1 = progress / 0.18
        np.multiply(rgb_old, max(0.06, 1.0 - p1 * 0.94), out=rgb_old, casting="unsafe")
        ign = np.clip(1.0 - u / 0.14, 0.0, 1.0) * p1 * spark
        rgb_old[:] = np.clip(rgb_old + ign[:, np.newaxis] * np.array([255, 190, 80]), 0, 255).astype(np.int32)
    elif progress < 0.62:
        p2 = (progress - 0.18) / 0.44
        fuse_u = p2 ** 0.92
        ahead = u > fuse_u
        rgb_old[ahead] = (rgb_old[ahead] * 0.06).astype(np.int32)
        rgb_old[~ahead] = 0

        head = np.clip(1.0 - np.abs(u - fuse_u) / 0.10, 0.0, 1.0) ** 1.5
        tail_d = fuse_u - u
        tail = np.where((tail_d > 0.0) & (tail_d < 0.26), (1.0 - tail_d / 0.26) ** 2, 0.0)
        sputter = np.where((tail_d > 0.0) & (tail_d < 0.32) & (h > 0.65), 0.85, 0.0)
        fire = (
            rgb_old
            + (tail * (0.7 + 0.3 * sputter))[:, np.newaxis] * np.array([255, 120, 20]) * spark
            + (head ** 2)[:, np.newaxis] * np.array([255, 250, 220])
        )
        np.clip(fire, 0, 255, out=rgb_old, casting="unsafe")
    else:
        p3 = (progress - 0.62) / 0.38
        blast_u = 1.0 - (p3 ** 0.78) * 1.16
        rgb_old.fill(0)
        mask_open = u >= blast_u
        np.copyto(rgb_old, rgb_new, where=mask_open[:, np.newaxis])
        fade = max(0.0, 1.0 - (p3 ** 1.5))
        crest = (np.clip(1.0 - np.abs(u - blast_u) / 0.18, 0.0, 1.0) ** 1.5) * fade
        out = rgb_old + crest[:, np.newaxis] * np.array([255, 225, 150])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="fuse_detonate",
    families=frozenset({F.STRIP_SWEEP_1D, F.STRIP_FOCAL_1D, F.STAGGERABLE, F.STOCHASTIC_ORGANIC}),
    duration=3.0,
    kind="strip_1d",
    handler=apply_fuse_detonate,
)
