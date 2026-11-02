"""
transitions/spectacles.py - 3-Act Theatrical Showstopper Transitions.

Implements multi-stage spatial and strip-intrinsic spectacles:
  1. apply_supernova      : Event horizon violet drain -> unstable core -> dual-wave Big Bang
  2. apply_shatter_ice    : Flash-freeze crystal -> fault-line cracks -> gravity shard collapse
  3. apply_tesla_arc      : Power grid brownout -> jumping high-voltage arcs -> vertical surge
  4. apply_fuse_detonate  : Blackout silhouette -> burning gunpowder fuse -> backfire detonation
  5. apply_liquid_geyser  : Gravity meniscus drain -> boiling floor pool -> pressurized geyser
  6. apply_pendulum_sweep : Stage dim -> fiery eraser swing -> prismatic painter return swing

Guarantees:
- AXIOM-01 / AXIOM-02: Strictly O(N) vectorized NumPy, mutates `rgb_old` in place.
- AXIOM-07: File length <= 500 lines.
- Sealed room: Standard library + NumPy + internal `transitions.effects` helpers only.
"""

import math
from typing import Optional, Tuple
import numpy as np

from transitions.effects import ACTIVE_PARAMS, _get_hash, _get_u


def _norm_coords(
    n: int,
    coords: Optional[np.ndarray],
    room_max_x: float,
    room_max_y: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return normalized 1D arrays (nx, ny) in [0..1] from 2D coords or 1D strip fallback."""
    if coords is not None and len(coords) == n:
        nx = np.clip(coords[:, 0] / max(1.0, float(room_max_x)), 0.0, 1.0)
        ny = np.clip(coords[:, 1] / max(1.0, float(room_max_y)), 0.0, 1.0)
        return nx, ny
    u = _get_u(n)
    return u, u


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
    nx, ny = _norm_coords(n, coords, room_max_x, room_max_y)
    cx = float(ACTIVE_PARAMS.get("epicenter_x", 0.5))
    cy = float(ACTIVE_PARAMS.get("epicenter_y", 0.5))
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
        sparks = (_get_hash(n) > 0.78) & mask_revealed
        stardust = np.where(sparks, fade * 140.0, 0.0)

        out = (
            rgb_old
            + precursor[:, np.newaxis] * np.array([0, 235, 255])
            + blast[:, np.newaxis] * np.array([255, 235, 175])
            + stardust[:, np.newaxis]
        )
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


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
    - Act III (0.55..1.00): Frozen shards fall downward with gravity, unveiling incoming mode.
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
    nx, ny = _norm_coords(n, coords, room_max_x, room_max_y)
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
        frost_crest = (4.0 * w * (1.0 - w) * 110.0 * spark)
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
        delay = shard_h * 0.22
        fall_t = np.clip((p3 - delay) / np.maximum(0.1, 1.0 - delay), 0.0, 1.0)
        fall_offset = (fall_t ** 2) * (1.15 + 0.45 * shard_h)
        virtual_y = ny - fall_offset

        cleared = (virtual_y < 0.0) | (fall_t >= 0.92)
        rgb_old.fill(0)
        np.copyto(rgb_old, rgb_new, where=cleared[:, np.newaxis])

        falling = (~cleared) & (edge_dist >= 0.06)
        if np.any(falling):
            fade_shard = ((1.0 - fall_t[falling]) ** 1.2)[:, np.newaxis]
            rgb_old[falling] = (ice_rgb[falling] * fade_shard).astype(np.int32)

        glint = (np.abs(fall_t - 0.25) < 0.18) & (~cleared)
        if np.any(glint):
            rgb_old[glint] = np.clip(rgb_old[glint] + np.array([120, 210, 255]), 0, 255)


def apply_tesla_arc(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act High-Voltage Short-Circuit & Tesla Arc Ignition:
    - Act I (0.00..0.28): Power grid brownout flicker to 10% warm amber filament glow.
    - Act II (0.28..0.65): Electric blue-white lightning arcs jump across chandelier sectors.
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
    nx, ny = _norm_coords(n, coords, room_max_x, room_max_y)
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))

    if progress < 0.28:
        p1 = progress / 0.28
        flicker = 0.18 if math.sin(p1 * 32.0) < 0.15 else (1.0 - 0.75 * p1)
        amber = np.array([255.0, 140.0, 45.0]) * (0.12 * p1)
        out = rgb_old * flicker + amber
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")
    elif progress < 0.65:
        p2 = (progress - 0.28) / 0.37
        rgb_old.fill(0)
        chops = float(max(3, int(ACTIVE_PARAMS.get("chop_count", 4))))
        step = math.floor(p2 * chops * 2.0)
        bolt_field = np.sin(nx * 17.0 - ny * 11.0 + step * 2.3 + seed) + 0.5 * np.cos(ny * 23.0 + p2 * 40.0)
        bolt_core = np.clip((bolt_field - 0.55) / 0.90, 0.0, 1.0)
        if np.any(bolt_core > 0.0):
            b = (bolt_core[:, np.newaxis] * spark)
            arc_color = b * np.array([135.0, 215.0, 255.0]) + (b ** 3) * np.array([255.0, 255.0, 255.0])
            np.clip(arc_color, 0, 255, out=rgb_old, casting="unsafe")
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
    u = _get_u(n)
    h = _get_hash(n)
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


def apply_liquid_geyser(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    coords: Optional[np.ndarray],
    progress: float,
    room_max_x: float = 430.0,
    room_max_y: float = 246.0,
) -> None:
    """
    3-Act Fluid Drain & Pressurized Geyser Eruption:
    - Act I (0.00..0.42): Glowing meniscus drains old mode top-to-bottom into darkness.
    - Act II (0.42..0.58): Molten amber-magenta pool boils at the bottom of the pillars.
    - Act III (0.58..1.00): High-pressure geyser blasts bottom-to-top with foaming white-cyan crest.
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
    _, ny = _norm_coords(n, coords, room_max_x, room_max_y)
    h = _get_hash(n)

    if progress < 0.42:
        p1 = progress / 0.42
        meniscus_y = 0.84 * (p1 ** 1.25)
        rgb_old[ny < meniscus_y] = 0
        rim = np.clip(1.0 - np.abs(ny - meniscus_y) / 0.09, 0.0, 1.0) ** 2
        if np.any(rim > 0.0):
            rgb_old[:] = np.clip(rgb_old + rim[:, np.newaxis] * np.array([120, 230, 255]), 0, 255).astype(np.int32)
    elif progress < 0.58:
        p2 = (progress - 0.42) / 0.16
        rgb_old.fill(0)
        pool_mask = ny >= 0.78
        if np.any(pool_mask):
            boil = 0.5 + 0.5 * np.sin(h[pool_mask] * 25.0 + p2 * 18.0)
            b = boil[:, np.newaxis]
            rgb_old[pool_mask] = np.clip(b * np.array([255, 150, 40]) + (1.0 - b) * np.array([255, 50, 170]), 0, 255).astype(np.int32)
        droplets = (ny >= 0.52) & (ny < 0.78) & (np.abs(h - p2) < 0.12)
        if np.any(droplets):
            rgb_old[droplets] = [255, 200, 110]
    else:
        p3 = (progress - 0.58) / 0.42
        jet_y = 1.02 - (p3 ** 0.76) * 1.18
        rgb_old.fill(0)
        mask_filled = ny >= jet_y
        np.copyto(rgb_old, rgb_new, where=mask_filled[:, np.newaxis])
        fade = max(0.0, 1.0 - (p3 ** 1.5))
        foam = (np.clip(1.0 - np.abs(ny - jet_y) / 0.16, 0.0, 1.0) ** 1.4) * fade
        out = rgb_old + foam[:, np.newaxis] * np.array([220, 250, 255])
        np.clip(out, 0, 255, out=rgb_old, casting="unsafe")


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
    nx, ny = _norm_coords(n, coords, room_max_x, room_max_y)
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
