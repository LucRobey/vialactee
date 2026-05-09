import numpy as np
from PIL import Image
import os
import glob
import logging
from typing import Optional

ROOM_MAX_X = 430
ROOM_MAX_Y = 246

spatial_images = {}
logger = logging.getLogger("Transition_Engine")

def load_spatial_images() -> None:
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'transitions'))
    if not os.path.exists(assets_dir):
        logger.warning(f"Spatial transition folder not found at {assets_dir}")
        return

    png_files = glob.glob(os.path.join(assets_dir, "*.png"))
    for file_path in png_files:
        name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            img = Image.open(file_path).convert('L')
            # img size is (width=ROOM_MAX_X, height=ROOM_MAX_Y)
            # np.array(img) has shape (ROOM_MAX_Y, ROOM_MAX_X)
            # Transpose gives (ROOM_MAX_X, ROOM_MAX_Y) = (X, Y) layout to match coords
            arr = np.array(img).T.astype(np.float32) / 255.0
            spatial_images[name] = arr
            logger.debug(f"Loaded spatial transition image: {name}")
        except Exception as e:
            logger.error(f"Failed to load spatial image {file_path}: {e}")

# Load immediately on import
load_spatial_images()

def apply_dual_fade(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float) -> None:
    """ Crossfades old mode softly into new mode """
    progress = max(0.0, min(1.0, progress))
    if progress == 0.0: return
    if progress == 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    np.multiply(rgb_list_old, 1.0 - progress, out=rgb_list_old, casting='unsafe')
    np.add(rgb_list_old, rgb_list_new * progress, out=rgb_list_old, casting='unsafe')

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
    colors = [
        [255, 0, 0],   # Red
        [0, 255, 0],   # Green
        [0, 0, 255],   # Blue
        [255, 0, 255], # Magenta
        [0, 255, 255], # Cyan
        [255, 255, 0]  # Yellow
    ]
    
    # For every tier, generate blocky geometric tearing across the segment
    block_size = max(1, num_leds // max(1, tier + 2))
    blocks = np.arange(num_leds) // block_size
    
    # Create chaotic boolean mask based on the current tier parity
    mask_glitch = (blocks % 2 == tier % 2)
    
    if tier % 2 == 0:
        # Splash random vivid solid color where mask is active
        color = np.array(colors[tier % len(colors)])
        np.copyto(rgb_list_old, color, where=mask_glitch[:, np.newaxis])
        
        # Where mask is false, snap immediately to the incoming mode
        np.copyto(rgb_list_old, rgb_list_new, where=(~mask_glitch)[:, np.newaxis])
    else:
        # Inverse snap to black or incoming
        np.copyto(rgb_list_old, rgb_list_new, where=mask_glitch[:, np.newaxis])
        np.copyto(rgb_list_old, np.array([0, 0, 0]), where=(~mask_glitch)[:, np.newaxis])

def apply_gravity_drop(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, coords: np.ndarray, progress: float) -> None:
    """ 
    Discrete numerical integrator that simulates realistic physical mechanics for multiple bouncing balls.
    The primary ball (Index 0) defines the wipe boundary and transition states.
    """
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    H = float(ROOM_MAX_Y)
    
    # --- Tunable Physics Constraints --- #
    g = 7000.0  # Gravity (downward acceleration mapping)
    e = 0.6    # Coefficient of restitution (Bounciness)
    dt = 0.003  # Integration step size
    
    # Define deterministically spaced beautiful balls
    base_colors = [
        [255, 0, 50], [0, 200, 255], [150, 0, 255], [255, 200, 0],
        [50, 255, 50], [255, 100, 0]
    ]
    balls = []
    for i in range(len(base_colors)):
        if i == 0:
            # Primary ball remains fully grounded to dictate transition correctly
            balls.append({
                "color": np.array(base_colors[i], dtype=np.int32), 
                "delay": 0.0, 
                "v0": 50.0,
                "size_mult": 1.0
            })
        else:
            delay = 0.04 * i
            
            # Deterministic pseudo-random generation based on index to ensure NO visual jitter across frames
            # Velocity constrained from 0 to 100 using sine wave amplitude extraction
            pseudo_v0 = abs(np.sin(i * 4.56)) * 100.0  
            # Size constrained dynamically from 30% to 150% of base radius
            pseudo_size = 0.3 + abs(np.cos(i * 7.89)) * 1.2
            
            balls.append({
                "color": np.array(base_colors[i], dtype=np.int32), 
                "delay": delay, 
                "v0": pseudo_v0,
                "size_mult": pseudo_size
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
    
    # Pseudo-random hash per block
    block_hash = ((bx * 373 + by * 113) % 100) / 100.0
    
    # Outbreak mechanic: calculate distance from an epicenter (center of room)
    cx, cy = 500, 120
    dist_norm = np.sqrt((bx * block_size_x - cx)**2 + (by * block_size_y - cy)**2) / 800.0
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
        # Flicker calculates ultra-fast noise per individual pixel (not block!) 
        flicker_noise = np.sin(progress * 500.0 + coords[:, 0][mask_glitching] * 19.0 + coords[:, 1][mask_glitching] * 23.0)
        
        glitch_colors = rgb_list_old[mask_glitching].copy()
        
        # Sub-behaviors inside the glitch noise
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
    """ Concentric inwards falling rings accelerating to a blackout, then violently expelling bright branching beams. """
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0: return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return
        
    cx, cy = 500, 120
    dx = coords[:, 0] - cx
    dy = coords[:, 1] - cy
    dist = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)
    max_dist = 800.0
    
    # Timing assumes a ~5.0s total transition (3.9s implosion, 0.1s pitch black, 1.0s explosion)
    t_implode = 0.78 
    t_blackout = 0.80
    
    if progress < t_implode:
        # --- PHASE 1: CONCENTRATION (Concentric shrinking rings) ---
        p1 = progress / t_implode
        
        # Sucks energy entirely from background mode, ending in blackness before the actual blackout begins
        darken_factor = max(0.0, 1.0 - (p1 * 1.5))
        np.multiply(rgb_list_old, darken_factor, out=rgb_list_old, casting="unsafe")
        
        # Exponentially accelerating timing mapped for rings (the 'more and more' frantic pull)
        time_mapped = (p1 ** 2.5) * 100.0
        
        # Gravity well mapping: rings are packed much tighter together near the active center
        dist_warp = dist ** 0.8
        rings = np.cos(dist_warp * 0.12 + time_mapped)
        
        mask_energy = rings > 0.85
        white_blue = np.array([200, 230, 255], dtype=np.int32)
        
        if np.any(mask_energy):
            rgb_list_old[mask_energy] = white_blue
            
    elif progress < t_blackout:
        # --- PHASE 2: BLACKOUT ---
        # Absolutely zero energy for a split second (0.1s in a 5s duration)
        rgb_list_old.fill(0)
        
    else:
        # --- PHASE 3: EXPLOSION ---
        p2 = (progress - t_blackout) / (1.0 - t_blackout)
        
        # Generate entirely new high-density sharp branching beam patterns based purely on angle
        beam_raw1 = np.sin(angle * 24.0)
        beam_raw2 = np.sin(angle * 37.0 + 1.4)
        
        # By clipping heavily strictly to positive bounds and using extreme powers, we calculate piercing 'spokes' geometry
        beam_shape = (np.clip(beam_raw1, 0, 1)**6) * 1.0 + (np.clip(beam_raw2, 0, 1)**4) * 0.8
        
        # Rapid foundational spherical wave expansion
        base_expansion = max_dist * 1.5 * (p2 ** 0.7) 
        
        # Geometrically blast outward where the angular beam_shape spikes exist
        jagged_radius = base_expansion * (1.0 + beam_shape * 6.0)
        
        mask_swallowed = dist < jagged_radius
        
        # Before copying the new mode, maintain the absolute structural blackness for regions the blast has naturally not yet reached!
        rgb_list_old.fill(0)
        
        # Inject the loaded final mode completely underneath the explosion
        np.copyto(rgb_list_old, rgb_list_new, where=mask_swallowed[:, np.newaxis])
        
        # Synthesize ultra-hot blasting glowing fronts overlaying the perimeter of the jag bounds
        dist_from_front = jagged_radius - dist
        front_depth = 250.0  # thick aggressive bleeding streaks!
        
        mask_blast = (dist_from_front > 0) & (dist_from_front < front_depth)
        
        if np.any(mask_blast):
            # Alpha gradient linearly dropping behind the wavefront
            edge_intensity = 1.0 - (dist_from_front[mask_blast] / front_depth)
            
            # Entire atmospheric explosion extinguishes itself organically as p2 scales -> 1.0
            global_energy = 1.0 - (p2 ** 1.5)
            fire_alpha = (edge_intensity * global_energy)[:, np.newaxis]
            
            base_color = rgb_list_old[mask_blast]
            blast_color = np.array([255, 255, 255], dtype=np.int32)
            
            blended = (base_color * (1.0 - fire_alpha) + blast_color * fire_alpha).astype(np.int32)
            rgb_list_old[mask_blast] = blended

def apply_transition(rgb_list_old: np.ndarray, rgb_list_new: np.ndarray, progress: float, transition_name: str, coords: Optional[np.ndarray] = None, beam_thickness: float = 0.04) -> None:
    """ 
    Route transition requests to specifically written geometric handlers or PNG spatial maps.
    """
    if transition_name == "fade_to_black":
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
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
        apply_spiral_transition(rgb_list_old, rgb_list_new, coords, progress)
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
            
        if transition_name not in spatial_images:
            apply_dual_fade(rgb_list_old, rgb_list_new, progress)
            return
            
        image = spatial_images[transition_name]
        
        # Clip coordinates to avoid IndexErrors just in case segments are out of bounds
        x_coords = np.clip(coords[:, 0], 0, ROOM_MAX_X - 1).astype(int)
        y_coords = np.clip(coords[:, 1], 0, ROOM_MAX_Y - 1).astype(int)
        
        # Extract threshold for each physical coordinate dynamically
        led_thresholds = image[x_coords, y_coords]
        
        # The New Mode eats everything strictly behind the progress threshold line
        mask_new = led_thresholds < (progress - beam_thickness/2)
        np.copyto(rgb_list_old, rgb_list_new, where=mask_new[:, np.newaxis])
        
        # Paint the direct laser boundary beam white
        mask_laser = np.abs(led_thresholds - progress) <= (beam_thickness/2)
        np.copyto(rgb_list_old, np.array([255, 255, 255]), where=mask_laser[:, np.newaxis])

