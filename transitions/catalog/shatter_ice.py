"""
transitions/catalog/shatter_ice.py - 3-Act Crystalline Freeze, Fracture & Gravity Collapse.
"""

from typing import Optional
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, norm_coords


def apply_shatter_ice(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act Crystalline Freeze, Fracture & Gravity Collapse (O(N) vectorized cell hash):
    - Act I (0.00..0.28): Cold wave flash-freezes outgoing mode into icy cyan-white crystal.
    - Act II (0.28..0.55): Bright white fault lines crack open into pitch-black fissures.
    - Act III (0.55..1.00): Frozen shards fall downward with gravity, unveiling incoming mode smoothly.
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

    jx = nx * 6.5 + 0.32 * np.sin(ny * 13.0 + seed)
    jy = ny * 4.5 + 0.32 * np.cos(nx * 11.0 + seed)
    cx = np.floor(jx)
    cy = np.floor(jy)
    edge_dist = 0.5 - np.maximum(np.abs(jx - cx - 0.5), np.abs(jy - cy - 0.5))
    shard_h = np.mod(np.sin(cx * 127.1 + cy * 311.7 + seed) * 43758.5453, 1.0)

    luma = np.max(rgb_old, axis=1, keepdims=True) * (1.0 / 255.0)
    ice_rgb = np.clip(luma * np.array([155.0, 230.0, 255.0]) + np.array([25.0, 45.0, 65.0]), 0, 255).astype(np.int32)

    if progress < 0.28:
        p1 = progress / 0.28
        w = np.clip((p1 * 1.25 - ny * 0.25) / 0.35, 0.0, 1.0)[:, np.newaxis]
        frost_crest = 4.0 * w * (1.0 - w) * 110.0 * spark
        blended = rgb_old * (1.0 - w) + ice_rgb * w + frost_crest
        np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")
    elif progress < 0.55:
        p2 = (progress - 0.28) / 0.27
        np.copyto(rgb_old, ice_rgb)
        crack_thresh = 0.16 * p2
        fissure_mask = edge_dist < (crack_thresh * 0.55)
        rim_mask = (edge_dist >= (crack_thresh * 0.55)) & (edge_dist < crack_thresh)
        rgb_old[fissure_mask] = 0
        if np.any(rim_mask):
            rgb_old[rim_mask] = np.clip(np.array([240, 252, 255]) * spark, 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.55) / 0.45
        delay = shard_h * 0.24 + (1.0 - ny) * 0.12
        fall_t = np.clip((p3 - delay) / np.maximum(0.15, 0.92 - delay), 0.0, 1.0)
        reveal_w = (fall_t * fall_t * (3.0 - 2.0 * fall_t))[:, np.newaxis]

        tail_settle = max(0.0, min(1.0, (p3 - 0.75) / 0.25))
        shard_body = (edge_dist >= 0.05).astype(np.float64)[:, np.newaxis]
        ice_weight = ((1.0 - fall_t) ** 1.5)[:, np.newaxis] * shard_body * (1.0 - tail_settle)

        glint_y = (p3 ** 1.25) * 1.25
        glint_band = np.clip(1.0 - np.abs(ny - glint_y) / 0.16, 0.0, 1.0) ** 2
        glint_spark = glint_band * (1.0 - p3) * (0.6 + 0.4 * shard_h) * spark

        out = (
            rgb_new * reveal_w
            + ice_rgb * ice_weight * (1.0 - 0.65 * reveal_w)
            + glint_spark[:, np.newaxis] * np.array([150.0, 230.0, 255.0])
        )
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="shatter_ice",
    families=frozenset({F.ROOM_SWEEP_2D, F.STOCHASTIC_ORGANIC}),
    duration=3.2,
    kind="spatial_spectacle",
    handler=apply_shatter_ice,
)
