"""
transitions/engine.py - Spatial and alpha pixel blending routines.
"""
import numpy as np
import logging
import math
from typing import Optional

from transitions.assets import spatial_images, load_spatial_images
from transitions.effects import (
    ACTIVE_PARAMS, apply_breath_dip, apply_collider, apply_ember_dissolve, apply_flash_cut,
    apply_iris_transition, apply_luma_melt, apply_prism_sweep, apply_silk_wipe,
    apply_staccato_shutter, apply_transformer_cut, apply_zipper_merge, set_transition_params,
)
from transitions.spectacles import (
    apply_fuse_detonate, apply_liquid_geyser, apply_pendulum_sweep,
    apply_shatter_ice, apply_supernova, apply_tesla_arc,
)

ROOM_MAX_X = 430
ROOM_MAX_Y = 246
logger = logging.getLogger("Transition_Engine")
TRANSITION_DEFAULTS = {"g": 7000.0, "e": 0.6, "dt": 0.003}

def set_room_bounds(max_x: float, max_y: float) -> None:
    """Set the physical room extent used by the spatial transitions (pushed in from outside)."""
    global ROOM_MAX_X, ROOM_MAX_Y
    if max_x > 0 and max_y > 0:
        ROOM_MAX_X = max_x
        ROOM_MAX_Y = max_y


def apply_dual_fade(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float) -> None:
    """ Crossfades old mode softly into new mode using smooth cosine curve. """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    w = 0.5 * (1.0 - math.cos(math.pi * progress))
    np.multiply(rgb_list_old, 1.0 - w, out=rgb_list_old, casting='unsafe')
    np.add(rgb_list_old, rgb_list_new * w, out=rgb_list_old, casting='unsafe')

def apply_colorful_glitch(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float) -> None:
    """3-Act Prism Rave Takeover (`global_change`): neon block strobe -> polyrhythmic cascade -> smooth bloom."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
    n = len(rgb_list_old)
    if n == 0: return
    u = np.arange(n, dtype=np.float64) / max(1.0, float(n - 1))
    palette = np.array(
        [[255, 20, 180], [0, 245, 255], [255, 215, 0], [160, 40, 255], [40, 255, 140], [255, 90, 20]],
        dtype=np.float64,
    )
    if progress < 0.32:
        p1 = progress / 0.32
        step = int(p1 * 6.0)
        blocks = np.floor(u * (4.0 + step)).astype(np.int32)
        active = (blocks % 2) == (step % 2)
        prism = palette[(blocks + step) % len(palette)]
        rgb_list_old[~active] = (rgb_list_old[~active] * (0.25 * (1.0 - p1))).astype(np.int32)
        rgb_list_old[active] = np.clip(rgb_list_old[active] * 0.35 + prism[active] * 0.85, 0, 255).astype(np.int32)
    elif progress < 0.72:
        p2 = (progress - 0.32) / 0.40
        step = int(p2 * 10.0)
        blocks = np.floor((u + step * 0.13) * (6.0 + step * 0.8)).astype(np.int32)
        mode_sel = (blocks + step) % 3
        c_idx = (blocks * 2 + step) % len(palette)
        rgb_list_old.fill(0)
        np.copyto(rgb_list_old, rgb_list_new, where=(mode_sel == 0)[:, np.newaxis])
        mask_prism = mode_sel == 1
        if np.any(mask_prism):
            rgb_list_old[mask_prism] = np.clip(
                rgb_list_new[mask_prism] * 0.35 + palette[c_idx[mask_prism]] * 0.90, 0, 255
            ).astype(np.int32)
    else:
        p3 = (progress - 0.72) / 0.28
        smooth = p3 * p3 * (3.0 - 2.0 * p3)
        c_idx = (np.floor(u * 8.0).astype(np.int32) + int(p3 * 6.0)) % len(palette)
        shimmer = (1.0 - smooth) * 0.55 * (0.5 + 0.5 * np.cos((u * 12.0 - p3 * 8.0) * math.pi))[:, np.newaxis]
        np.clip(rgb_list_new + palette[c_idx] * shimmer, 0, 255, out=rgb_list_old, casting="unsafe")


def apply_gravity_drop(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """Architectural Marble-Run Cascade: left-to-right horizontal travel + vertical gravity drops down pillars."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
    nx = np.clip(coords[:, 0] / max(1.0, float(ROOM_MAX_X)), 0.0, 1.0)
    ny = np.clip(coords[:, 1] / max(1.0, float(ROOM_MAX_Y)), 0.0, 1.0)
    cascade_t = 0.56 * nx + 0.32 * (ny ** 0.78)
    lead_p = progress * 0.98
    ahead_d = cascade_t - lead_p
    trench = (ahead_d > 0.0) & (ahead_d < 0.18)
    if np.any(trench):
        t_fade = (ahead_d[trench] / 0.18) ** 1.5
        rgb_list_old[trench] = (rgb_list_old[trench] * (0.08 + 0.92 * t_fade[:, np.newaxis])).astype(np.int32)
    np.copyto(rgb_list_old, rgb_list_new, where=(cascade_t <= lead_p)[:, np.newaxis])
    tail_fade = 1.0 if progress < 0.84 else max(0.0, (1.0 - progress) / 0.16) ** 1.4
    if tail_fade <= 1e-3: return
    marbles = (
        (0.00, np.array([255.0, 215.0, 60.0])),
        (0.07, np.array([0.0, 235.0, 255.0])),
        (0.14, np.array([255.0, 60.0, 200.0])),
        (0.21, np.array([180.0, 255.0, 120.0])),
    )
    pillar_xs = (205.0 / 430.0, 292.0 / 430.0, 383.0 / 430.0, 1.0)
    glow = np.zeros((len(rgb_list_old), 3), dtype=np.float64)
    for delay, color in marbles:
        mp = progress - delay
        if mp <= 0.0: continue
        roll_nx = (mp - 0.32 * (ny ** 0.78)) / 0.56
        h_orb = np.clip(1.0 - np.abs(nx - roll_nx) / 0.09, 0.0, 1.0) ** 1.8
        glow += h_orb[:, np.newaxis] * color
        for px in pillar_xs:
            t_pillar = mp - 0.56 * px
            if 0.0 < t_pillar < 0.42:
                drop_ny = min(1.05, 0.05 + 1.85 * ((t_pillar / 0.34) ** 1.65))
                on_pillar = np.clip(1.0 - np.abs(nx - px) / 0.04, 0.0, 1.0)
                v_orb = on_pillar * (np.clip(1.0 - np.abs(ny - drop_ny) / 0.16, 0.0, 1.0) ** 1.6)
                glow += v_orb[:, np.newaxis] * (color * 0.7 + np.array([255.0, 255.0, 255.0]) * 0.5)
    np.clip(rgb_list_old + glow * tail_fade, 0, 255, out=rgb_list_old, casting="unsafe")


def apply_weird_glitch(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """
    3-Act Cyberpunk Sector Corruption & Matrix Reboot:
    - Act I (0.00..0.32): Quantized sector freeze, RGB channel tear & scanline blackouts.
    - Act II (0.32..0.72): High-contrast pitch-black void with teleporting neon cyber-blocks.
    - Act III (0.72..1.00): Progressive digital scanline resync locking smoothly into `rgb_list_new`.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    nx = np.clip(coords[:, 0] / max(1.0, float(ROOM_MAX_X)), 0.0, 1.0)
    ny = np.clip(coords[:, 1] / max(1.0, float(ROOM_MAX_Y)), 0.0, 1.0)
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))

    # Quantized architectural blocks & sample-and-hold digital frame steps
    bx = np.floor(nx * 7.0)
    by = np.floor(ny * 5.0)
    step = math.floor(progress * 22.0)
    b_hash = np.mod(np.sin(bx * 127.1 + by * 311.7 + step * 19.3 + seed) * 43758.5453, 1.0)
    static_h = np.mod(np.sin(bx * 73.1 + by * 157.3 + seed) * 19731.3, 1.0)

    if progress < 0.32:
        p1 = progress / 0.32
        infected = static_h < (0.25 + 0.75 * p1)
        dropout = infected & (b_hash < 0.42)
        tear_c = infected & (b_hash >= 0.42) & (b_hash < 0.72)
        tear_m = infected & (b_hash >= 0.72)
        rgb_list_old[dropout] = 0
        if np.any(tear_c):
            # Cyan chromatic channel tear (zero Red, boost Green/Blue)
            rgb_list_old[tear_c, 0] = 0
            rgb_list_old[tear_c, 1] = np.clip(rgb_list_old[tear_c, 1] + 150, 0, 255)
            rgb_list_old[tear_c, 2] = 255
        if np.any(tear_m):
            # Magenta chromatic channel tear (boost Red/Blue, zero Green)
            rgb_list_old[tear_m, 0] = 255
            rgb_list_old[tear_m, 1] = 0
            rgb_list_old[tear_m, 2] = np.clip(rgb_list_old[tear_m, 2] + 150, 0, 255)
    elif progress < 0.72:
        p2 = (progress - 0.32) / 0.40
        rgb_list_old.fill(0)
        # High-contrast cyber blocks jumping across pitch-black negative space
        m_new = (b_hash >= 0.28) & (b_hash < (0.55 + 0.25 * p2))
        m_cyan = (b_hash >= 0.80) & (b_hash < 0.87)
        m_mag = (b_hash >= 0.87) & (b_hash < 0.94)
        m_yel = b_hash >= 0.94
        np.copyto(rgb_list_old, rgb_list_new, where=m_new[:, np.newaxis])
        rgb_list_old[m_cyan] = [0, 250, 255]
        rgb_list_old[m_mag] = [255, 0, 210]
        rgb_list_old[m_yel] = [255, 235, 0]
    else:
        p3 = (progress - 0.72) / 0.28
        scan_lock = 0.65 * ny + 0.35 * static_h
        locked = scan_lock <= (p3 * 1.15)
        rgb_list_old.fill(0)
        np.copyto(rgb_list_old, rgb_list_new, where=locked[:, np.newaxis])
        if np.any(~locked):
            rgb_list_old[~locked] = (rgb_list_new[~locked] * p3).astype(np.int32)
        sync_bar = np.clip(1.0 - np.abs(ny - p3) / 0.14, 0.0, 1.0) * ((1.0 - p3) ** 1.4)
        out = rgb_list_old + sync_bar[:, np.newaxis] * np.array([0.0, 240.0, 255.0])
        np.clip(out, 0, 255, out=rgb_list_old, casting="unsafe")


def apply_explosion(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """Concentric inward-collapsing rings to a brief blackout, then a radial shockwave explosion."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    raw_ex = float(ACTIVE_PARAMS.get("epicenter_x", 0.60))
    ex = 0.60 if abs(raw_ex - 0.5) < 1e-3 else raw_ex
    cx = ROOM_MAX_X * ex
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.50))
    dx = coords[:, 0] - cx
    dy = coords[:, 1] - cy
    dist = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)
    max_radius = float(math.hypot(max(cx, ROOM_MAX_X - cx), max(cy, ROOM_MAX_Y - cy)))
    max_radius = max(120.0, max_radius)

    t_implode = 0.52
    t_blackout = 0.60

    if progress < t_implode:
        # --- PHASE 1: CONCENTRATION (Shrinking horizon + inward rings collapsing to center) ---
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
        # --- PHASE 2: COMPRESSION BLACKOUT ---
        rgb_list_old.fill(0)

    else:
        # --- PHASE 3: RADIAL SHOCKWAVE EXPLOSION ---
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

_WHITE_BEAM = np.array([255, 255, 255])


def _apply_field_wipe(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    field: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    """Wipes incoming buffer across a normalized scalar field [0..1] with a dark void trench and glowing laser crest."""
    taper = math.sin(progress * math.pi)
    eff_beam = max(0.02, float(beam_thickness)) * (0.4 + 0.6 * taper)
    half_beam = eff_beam * 0.5
    trench_w = min(0.22, max(0.08, float(ACTIVE_PARAMS.get("trench_width", 0.14)))) * taper

    mask_new = field < (progress - half_beam)
    np.copyto(rgb_list_old, rgb_list_new, where=mask_new[:, np.newaxis])

    trench_dist = field - (progress + half_beam)
    mask_trench = (trench_dist > 0.0) & (trench_dist <= trench_w)
    if np.any(mask_trench) and trench_w > 1e-4:
        trench_fade = ((trench_dist[mask_trench] / trench_w) ** 1.6)[:, np.newaxis]
        rgb_list_old[mask_trench] = (rgb_list_old[mask_trench] * (0.06 + 0.94 * trench_fade)).astype(np.int32)

    beam_dist = np.abs(field - progress)
    mask_beam = beam_dist <= half_beam
    if np.any(mask_beam) and half_beam > 1e-4:
        core = (1.0 - (beam_dist[mask_beam] / half_beam) ** 1.5)[:, np.newaxis]
        base = rgb_list_new[mask_beam]
        rgb_list_old[mask_beam] = np.clip(base * (1.0 - core * 0.65) + _WHITE_BEAM * core, 0, 255).astype(np.int32)


def apply_horizontal_wipe(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float, beam_thickness: float = 0.04, reverse: bool = False) -> None:
    """ Sweeps horizontally across the room with a laser boundary line. """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    nx = coords[:, 0] / max(1.0, float(ROOM_MAX_X))
    if reverse:
        nx = 1.0 - nx
    _apply_field_wipe(rgb_list_old, rgb_list_new, nx, progress, beam_thickness)


def apply_vertical_wipe(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float, beam_thickness: float = 0.04) -> None:
    """ Sweeps vertically across the room with a laser boundary line. """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    ny = coords[:, 1] / max(1.0, float(ROOM_MAX_Y))
    _apply_field_wipe(rgb_list_old, rgb_list_new, ny, progress, beam_thickness)


def apply_box_wipe(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float, beam_thickness: float = 0.04) -> None:
    """Sweeps outwards from the active 2D room epicenter in a wide, high-contrast rectangular frame."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    raw_ex = float(ACTIVE_PARAMS.get("epicenter_x", 0.60))
    ex = 0.60 if abs(raw_ex - 0.5) < 1e-3 else raw_ex
    cx = ROOM_MAX_X * ex
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.50))
    span_x = max(cx, ROOM_MAX_X - cx, 1.0)
    span_y = max(cy, ROOM_MAX_Y - cy, 1.0)
    dist = np.maximum(np.abs(coords[:, 0] - cx) / span_x, np.abs(coords[:, 1] - cy) / span_y)
    # Widen beam substantially so perpendicular intersections illuminate a bold segment
    wide_beam = max(0.30, float(beam_thickness) * 2.2)
    _apply_field_wipe(rgb_list_old, rgb_list_new, dist, progress, wide_beam)


def apply_spiral_transition(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float, beam_thickness: float = 0.04) -> None:
    """3-Act Logarithmic Galaxy Vortex: spin-up gravity drain -> eye of the storm -> multi-arm spiral shockwave unwind."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    raw_ex = float(ACTIVE_PARAMS.get("epicenter_x", 0.60))
    ex = 0.60 if abs(raw_ex - 0.5) < 1e-3 else raw_ex
    cx = ROOM_MAX_X * ex
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.50))
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
        _apply_field_wipe(rgb_list_old, rgb_list_new, spiral_field, p3, beam_thickness)


_STRIP_HANDLERS = {
    "ember_dissolve": apply_ember_dissolve, "luma_melt": apply_luma_melt, "breath_dip": apply_breath_dip,
    "silk_wipe": lambda o, n, p: apply_silk_wipe(o, n, p, reverse=False),
    "silk_wipe_reverse": lambda o, n, p: apply_silk_wipe(o, n, p, reverse=True),
    "iris_open": lambda o, n, p: apply_iris_transition(o, n, p, close_in=False),
    "iris_close": lambda o, n, p: apply_iris_transition(o, n, p, close_in=True),
    "zipper_merge": apply_zipper_merge, "collider": apply_collider, "fuse_detonate": apply_fuse_detonate,
    "prism_sweep": apply_prism_sweep, "flash_cut": apply_flash_cut,
    "staccato_shutter": apply_staccato_shutter, "transformer_cut": apply_transformer_cut,
}

_SPECTACLE_HANDLERS = {
    "supernova": apply_supernova, "shatter_ice": apply_shatter_ice, "tesla_arc": apply_tesla_arc,
    "liquid_geyser": apply_liquid_geyser, "pendulum_sweep": apply_pendulum_sweep,
}


def apply_transition(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float, transition_name: str, coords: Optional[np.ndarray] = None, beam_thickness: float = 0.04) -> None:
    """ 
    Route transition requests to specifically written geometric handlers or PNG spatial maps.
    """
    if transition_name in ("fade_to_black", "fade_in_out", "smooth_cosine_crossfade", "cosine_fade"):
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
    elif transition_name in _STRIP_HANDLERS:
        _STRIP_HANDLERS[transition_name](rgb_list_old, rgb_list_new, progress)
    elif transition_name in _SPECTACLE_HANDLERS:
        _SPECTACLE_HANDLERS[transition_name](rgb_list_old, rgb_list_new, coords, progress, ROOM_MAX_X, ROOM_MAX_Y)
    elif transition_name == "global_change":
        apply_colorful_glitch(rgb_list_old, rgb_list_new, progress)
    elif coords is None:
        # Fallback if coordinates are completely missing for spatial
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
    elif transition_name == "wipe_left_to_right":
        apply_horizontal_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness, reverse=False)
    elif transition_name == "wipe_right_to_left":
        apply_horizontal_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness, reverse=True)
    elif transition_name == "vertical_wipe":
        apply_vertical_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness)
    elif transition_name == "box_wipe":
        apply_box_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness)
    elif transition_name == "spiral":
        apply_spiral_transition(rgb_list_old, rgb_list_new, coords, progress, beam_thickness)
    elif transition_name == "gravity_drop":
        apply_gravity_drop(rgb_list_old, rgb_list_new, coords, progress)
    elif transition_name == "weird_glitch":
        apply_weird_glitch(rgb_list_old, rgb_list_new, coords, progress)
    elif transition_name == "explosion":
        apply_explosion(rgb_list_old, rgb_list_new, coords, progress)
    else:
        # Fallback to PNG-based transitions
        progress = max(0.0, min(1.0, progress))
        if progress <= 0.0: return
        if progress >= 1.0:
            np.copyto(rgb_list_old, rgb_list_new)
            return
            
        load_spatial_images()
        if transition_name not in spatial_images:
            apply_dual_fade(rgb_list_old, rgb_list_new, progress)
            return
            
        image = spatial_images[transition_name]
        
        # Clip coordinates to avoid IndexErrors just in case segments are out of bounds
        x_coords = np.clip(coords[:, 0], 0, image.shape[0] - 1).astype(int)
        y_coords = np.clip(coords[:, 1], 0, image.shape[1] - 1).astype(int)
        
        # Extract threshold for each physical coordinate dynamically
        led_thresholds = image[x_coords, y_coords]
        _apply_field_wipe(rgb_list_old, rgb_list_new, led_thresholds, progress, beam_thickness)

