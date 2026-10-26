"""
transitions/engine.py - Spatial and alpha pixel blending routines.
"""
import numpy as np
import logging
import math
from typing import Optional

from transitions.assets import spatial_images, load_spatial_images
from transitions.effects import (
    ACTIVE_PARAMS,
    apply_breath_dip,
    apply_collider,
    apply_ember_dissolve,
    apply_flash_cut,
    apply_iris_transition,
    apply_luma_melt,
    apply_prism_sweep,
    apply_silk_wipe,
    apply_staccato_shutter,
    apply_transformer_cut,
    apply_zipper_merge,
    set_transition_params,
)

ROOM_MAX_X = 430
ROOM_MAX_Y = 246

logger = logging.getLogger("Transition_Engine")

TRANSITION_DEFAULTS = {
    "g": 7000.0,
    "e": 0.6,
    "dt": 0.003
}

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
    """ A 'not smooth', blocky, colorful rave flash to mask the mode transition. """
    progress = max(0.0, min(1.0, progress))
    if progress == 0.0: return
    if progress == 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    num_leds = len(rgb_list_old)
    
    # Non-smooth: Update only in large chunky tiers (e.g., 6 distinct flash frames)
    tier = int(progress * 8)
    
    # 6 intensely saturated colors
    colors = [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 0, 255], [0, 255, 255], [255, 255, 0]]
    block_size = max(1, num_leds // max(1, tier + 2))
    blocks = np.arange(num_leds) // block_size
    mask_glitch = (blocks % 2 == tier % 2)

    if tier % 2 == 0:
        color = np.array(colors[tier % len(colors)])
        np.copyto(rgb_list_old, color, where=mask_glitch[:, np.newaxis])
        np.copyto(rgb_list_old, rgb_list_new, where=(~mask_glitch)[:, np.newaxis])
    else:
        np.copyto(rgb_list_old, rgb_list_new, where=mask_glitch[:, np.newaxis])
        np.copyto(rgb_list_old, np.array([0, 0, 0]), where=(~mask_glitch)[:, np.newaxis])


def apply_gravity_drop(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """Discrete numerical integrator for multiple bouncing balls; primary ball defines the wipe boundary."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    H = float(ROOM_MAX_Y)
    g, e, dt = TRANSITION_DEFAULTS["g"], TRANSITION_DEFAULTS["e"], TRANSITION_DEFAULTS["dt"]
    base_colors = [[255, 0, 50], [0, 200, 255], [150, 0, 255], [255, 200, 0], [50, 255, 50], [255, 100, 0]]
    balls = []
    for i, c in enumerate(base_colors):
        if i == 0:
            balls.append({"color": np.array(c, dtype=np.int32), "delay": 0.0, "v0": 50.0, "size_mult": 1.0})
        else:
            balls.append({
                "color": np.array(c, dtype=np.int32),
                "delay": 0.04 * i,
                "v0": abs(np.sin(i * 4.56)) * 100.0,
                "size_mult": 0.3 + abs(np.cos(i * 7.89)) * 1.2,
            })
    
    ball_results = []
    
    # Process physics for every ball independently
    for b in balls:
        y = 0.0
        v = float(b["v0"])
        max_y_reached = 0.0
        first_hit_time = 1.0
        
        current_t = b["delay"]
        # Simulate forward through time up to our current progress
        while current_t < progress:
            v += g * dt
            y += v * dt
            
            if y >= H:
                if first_hit_time == 1.0:
                    first_hit_time = current_t
                y = H
                v = -v * e
                
            max_y_reached = max(max_y_reached, y)
            current_t += dt
            
        # Interpolate excess integration frames
        excess = current_t - progress
        if excess > 0 and progress > b["delay"]:
            y -= v * excess
            
        ball_results.append({
            "y": min(H, max(0.0, y)),
            "max_y_reached": max_y_reached,
            "first_hit_time": first_hit_time,
            "color": b["color"],
            "size_mult": b["size_mult"],
            "is_active": progress > b["delay"]
        })
        
    main_ball = ball_results[0]
    
    # Sweep incoming mode directly behind the path mapped by max extent of the PRIMARY ball
    mask_new = coords[:, 1] <= main_ball["max_y_reached"]
    np.copyto(rgb_list_old, rgb_list_new, where=mask_new[:, np.newaxis])
    
    # If primary ball hit the floor, apply the incoming mode permanently everywhere
    if main_ball["first_hit_time"] <= progress:
        np.copyto(rgb_list_old, rgb_list_new)
        
    # Begin fading out smoothly exactly from the moment of the primary ball's first impact
    if progress <= main_ball["first_hit_time"]:
        fade = 1.0
    else:
        fade_duration = 1.0 - main_ball["first_hit_time"]
        if fade_duration > 0.001:
            fade = max(0.0, 1.0 - ((progress - main_ball["first_hit_time"]) / fade_duration))
        else:
            fade = 0.0
            
    # Render all bouncing balls using the painter's algorithm
    # Draw lower/older balls first, so the Primary Ball (idx 0) stays fully crisp on top!
    for res in reversed(ball_results):
        if not res["is_active"]:
            continue
            
        dist = np.abs(coords[:, 1] - res["y"])
        # Radius mapped against the unique pseudo-random size multiplier of the ball
        radius = max(3.0 * res["size_mult"], 10.0 * res["size_mult"] * fade)  
        mask_ball_1d = dist < radius
        
        if np.any(mask_ball_1d):
            base_color = rgb_list_old[mask_ball_1d]
            blended = (base_color * (1.0 - fade) + res["color"] * fade).astype(np.int32)
            rgb_list_old[mask_ball_1d] = blended
            
def apply_weird_glitch(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """ Digital sector corruption transition that spreads like a virus. """
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    # Create quantized geometric 'blocks' for a chunky digital sector feel
    block_size_x, block_size_y = 60, 40
    bx = coords[:, 0] // block_size_x
    by = coords[:, 1] // block_size_y
    
    # Pseudo-random hash per block, permuted by active seed
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))
    block_hash = np.mod(((bx * 373 + by * 113) % 100) / 100.0 + seed, 1.0)
    
    # Outbreak mechanic: calculate distance from the active 2D room epicenter
    cx = ROOM_MAX_X * float(ACTIVE_PARAMS.get("epicenter_x", 0.5))
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.5))
    dist_scale = max(1.0, max(ROOM_MAX_X, ROOM_MAX_Y) * 1.5)
    dist_norm = np.sqrt((bx * block_size_x - cx)**2 + (by * block_size_y - cy)**2) / dist_scale
    dist_norm = np.clip(dist_norm, 0.0, 1.0)
    
    # Infection threshold combines outbreak wave + block randomness (0.0 to ~0.75 max)
    infection_threshold = dist_norm * 0.5 + block_hash * 0.25
    
    # Duration each infected block spends glitching before resolving to the new mode
    glitch_duration = 0.25
    local_prog = (progress - infection_threshold) / glitch_duration
    
    # Mask categorizations
    mask_resolved = local_prog >= 1.0
    mask_glitching = (local_prog >= 0.0) & (local_prog < 1.0)
    
    # 1. Apply resolved blocks aggressively
    np.copyto(rgb_list_old, rgb_list_new, where=mask_resolved[:, np.newaxis])
    
    # 2. Process actively glitching blocks
    if np.any(mask_glitching):
        flicker_noise = np.sin(progress * 500.0 + coords[:, 0][mask_glitching] * 19.0 + coords[:, 1][mask_glitching] * 23.0)
        glitch_colors = rgb_list_old[mask_glitching].copy()
        
        mask_white = flicker_noise > 0.8
        mask_black = flicker_noise < -0.8
        mask_peek = (flicker_noise > 0.4) & (flicker_noise <= 0.8)
        mask_color = (flicker_noise > -0.8) & (flicker_noise <= -0.4)
        
        glitch_colors[mask_white] = [255, 255, 255]
        glitch_colors[mask_black] = [0, 0, 0]
        
        new_colors_subset = rgb_list_new[mask_glitching]
        glitch_colors[mask_peek] = new_colors_subset[mask_peek]
        
        color_mod = (coords[:, 0][mask_glitching] + coords[:, 1][mask_glitching]) % 3
        synth_colors = np.zeros_like(glitch_colors)
        synth_colors[color_mod == 0] = [0, 255, 255] # Cyan
        synth_colors[color_mod == 1] = [255, 0, 255] # Magenta
        synth_colors[color_mod == 2] = [255, 255, 0] # Yellow
        
        glitch_colors[mask_color] = synth_colors[mask_color]
        rgb_list_old[mask_glitching] = glitch_colors

def apply_explosion(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """Concentric inward-collapsing rings to a brief blackout, then a radial shockwave explosion."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    cx = ROOM_MAX_X * float(ACTIVE_PARAMS.get("epicenter_x", 0.5))
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.5))
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
    """Wipes incoming buffer across a normalized scalar field [0..1] with a white laser boundary."""
    half_beam = beam_thickness / 2.0
    mask_new = field < (progress - half_beam)
    np.copyto(rgb_list_old, rgb_list_new, where=mask_new[:, np.newaxis])

    mask_beam = np.abs(field - progress) <= half_beam
    if np.any(mask_beam):
        np.copyto(rgb_list_old, _WHITE_BEAM, where=mask_beam[:, np.newaxis])


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
    """ Sweeps outwards from the active 2D room epicenter in a rectangular frame. """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    cx = ROOM_MAX_X * float(ACTIVE_PARAMS.get("epicenter_x", 0.5))
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.5))
    span_x = max(cx, ROOM_MAX_X - cx, 1.0)
    span_y = max(cy, ROOM_MAX_Y - cy, 1.0)
    dist = np.maximum(np.abs(coords[:, 0] - cx) / span_x, np.abs(coords[:, 1] - cy) / span_y)
    _apply_field_wipe(rgb_list_old, rgb_list_new, dist, progress, beam_thickness)


def apply_spiral_transition(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float, beam_thickness: float = 0.04) -> None:
    """ Radial clock wipe pivoting around the active 2D room epicenter. """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    cx = ROOM_MAX_X * float(ACTIVE_PARAMS.get("epicenter_x", 0.5))
    cy = ROOM_MAX_Y * float(ACTIVE_PARAMS.get("epicenter_y", 0.5))
    angles = (np.arctan2(coords[:, 1] - cy, coords[:, 0] - cx) + np.pi) / (2.0 * np.pi)
    if float(ACTIVE_PARAMS.get("spiral_sign", 1.0)) < 0.0:
        angles = 1.0 - angles
    _apply_field_wipe(rgb_list_old, rgb_list_new, angles, progress, beam_thickness)


_STRIP_HANDLERS = {
    "ember_dissolve": apply_ember_dissolve,
    "luma_melt": apply_luma_melt,
    "breath_dip": apply_breath_dip,
    "silk_wipe": lambda o, n, p: apply_silk_wipe(o, n, p, reverse=False),
    "silk_wipe_reverse": lambda o, n, p: apply_silk_wipe(o, n, p, reverse=True),
    "iris_open": lambda o, n, p: apply_iris_transition(o, n, p, close_in=False),
    "iris_close": lambda o, n, p: apply_iris_transition(o, n, p, close_in=True),
    "zipper_merge": apply_zipper_merge,
    "collider": apply_collider,
    "prism_sweep": apply_prism_sweep,
    "flash_cut": apply_flash_cut,
    "staccato_shutter": apply_staccato_shutter,
    "transformer_cut": apply_transformer_cut,
}


def apply_transition(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float, transition_name: str, coords: Optional[np.ndarray] = None, beam_thickness: float = 0.04) -> None:
    """ 
    Route transition requests to specifically written geometric handlers or PNG spatial maps.
    """
    if transition_name in ("fade_to_black", "fade_in_out", "smooth_cosine_crossfade", "cosine_fade"):
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
    elif transition_name in _STRIP_HANDLERS:
        _STRIP_HANDLERS[transition_name](rgb_list_old, rgb_list_new, progress)
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

