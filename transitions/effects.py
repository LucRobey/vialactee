"""
transitions/effects.py - Strip-intrinsic (1D), photonic dissolve, kinetic physics,
and rhythmic DJ transition blending routines for the Vialactée chandelier.

Guarantees:
- AXIOM-01 / AXIOM-02: Mutates `rgb_old` in place, caches 1D coordinate arrays by strip length.
- AXIOM-07: File length <= 500 lines.
- Sealed room: Standard library + NumPy only.
"""
import math
from typing import Any, Dict, Optional
import numpy as np

# Pre-cached 1D strip normalized coordinates u in [0.0, 1.0] and deterministic hashes by strip length N
_U_CACHE: Dict[int, np.ndarray] = {}
_HASH_CACHE: Dict[int, np.ndarray] = {}

ACTIVE_PARAMS: Dict[str, Any] = {
    "epicenter_x": 0.5,
    "epicenter_y": 0.5,
    "spiral_sign": 1.0,
    "spiral_arms": 2,
    "beam_thickness": 0.04,
    "trench_width": 0.14,
    "edge_width": 0.22,
    "teeth_count": 4,
    "focal_u": 0.5,
    "seed": 0.0,
    "spark_intensity": 1.0,
    "chop_count": 4,
    "flash_decay": 2.2,
    "mode_handshake": False,
}


def set_transition_params(params: Optional[Dict[str, Any]] = None) -> None:
    """Update or reset the active generative transition parameters."""
    ACTIVE_PARAMS.update({
        "epicenter_x": 0.5,
        "epicenter_y": 0.5,
        "spiral_sign": 1.0,
        "spiral_arms": 2,
        "beam_thickness": 0.04,
        "trench_width": 0.14,
        "edge_width": 0.22,
        "teeth_count": 4,
        "focal_u": 0.5,
        "seed": 0.0,
        "spark_intensity": 1.0,
        "chop_count": 4,
        "flash_decay": 2.2,
        "mode_handshake": False,
    })
    if params:
        ACTIVE_PARAMS.update(params)


def _get_u(n: int) -> np.ndarray:
    """Return cached 1D normalized coordinate array u in [0.0, 1.0] of length n."""
    arr = _U_CACHE.get(n)
    if arr is None:
        arr = np.linspace(0.0, 1.0, max(1, n), dtype=np.float32)
        _U_CACHE[n] = arr
    return arr


def _get_hash(n: int) -> np.ndarray:
    """Return cached deterministic pseudo-random threshold array in [0.0, 1.0] of length n."""
    arr = _HASH_CACHE.get(n)
    if arr is None:
        idx = np.arange(max(1, n), dtype=np.float32)
        arr = np.mod(np.sin(idx * 12.9898 + 78.233) * 43758.5453, 1.0).astype(np.float32)
        _HASH_CACHE[n] = arr
    return arr


def _blend_with_crest(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    t: np.ndarray,
    crest_gain: float = 0.25,
) -> None:
    """
    In-place smoothstep blend between rgb_old and rgb_new using per-pixel progress t in [0..1],
    adding a subtle self-colored luminance crest at the wavefront (t ~ 0.5).
    """
    w = (t * t * (3.0 - 2.0 * t))[:, np.newaxis]
    crest = (4.0 * t * (1.0 - t) * crest_gain)[:, np.newaxis]
    blended = rgb_old * (1.0 - w) + rgb_new * w + (rgb_old + rgb_new) * crest
    np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")


# =============================================================================
# FAMILY A: ORGANIC & PHOTONIC DISSOLVES
# =============================================================================

def apply_ember_dissolve(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Sparkle / spatial dither dissolve. Pixels flip in deterministic twinkling clusters
    with an ember glow peak, preventing the 50% grey brightness valley of linear fades.
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
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))
    base_h = _get_hash(n)
    h = np.mod(base_h + seed, 1.0) if seed != 0.0 else base_h
    win = 0.28
    t = np.clip((progress * (1.0 + win) - h) / win, 0.0, 1.0)
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))
    _blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.30 * spark)


def apply_luma_melt(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Content-aware luminance-keyed dissolve: brightest features of the incoming mode
    burn through first while dim background regions melt last.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    if len(rgb_old) == 0:
        return
    luma_new = np.max(rgb_new, axis=1) * (1.0 / 255.0)
    luma_old = np.max(rgb_old, axis=1) * (1.0 / 255.0)
    threshold = np.clip(0.55 * (1.0 - luma_new) + 0.20 * luma_old, 0.0, 0.75)
    win = 0.25
    t = np.clip((progress - threshold) / win, 0.0, 1.0)
    spark = float(ACTIVE_PARAMS.get("spark_intensity", 1.0))
    _blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.15 * spark)


def apply_breath_dip(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Two-stage theatrical reset (Exhale to center darkness -> suspense pause -> Inhale bloom).
    Ideal for song changes and ambient breakdowns.
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
    dist_center = np.abs(2.0 * u - 1.0)

    if progress < 0.45:
        p1 = progress / 0.45
        edge_envelope = np.clip((1.0 - p1 * 1.15 - dist_center * p1) / max(0.05, 1.0 - p1 * 0.5), 0.0, 1.0)
        gain = (edge_envelope * (1.0 - p1 * p1))[:, np.newaxis]
        np.multiply(rgb_old, gain, out=rgb_old, casting="unsafe")
    elif progress < 0.55:
        rgb_old.fill(0)
    else:
        p2 = (progress - 0.55) / 0.45
        win = 0.25
        reveal = np.clip((p2 * (1.0 + win) - dist_center) / win, 0.0, 1.0)
        envelope = (reveal * reveal * (3.0 - 2.0 * reveal) * math.sin(p2 * math.pi * 0.5))[:, np.newaxis]
        np.multiply(rgb_new, envelope, out=rgb_old, casting="unsafe")


# =============================================================================
# FAMILY B: 1D STRIP-INTRINSIC SWEEPS (ORIENTATION-PROOF)
# =============================================================================

def apply_silk_wipe(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    progress: float,
    reverse: bool = False,
) -> None:
    """
    Soft-feathered 1D strip wipe with an S-curve wavefront and mode-tinted crest.
    Animates smoothly across both horizontal rungs and vertical pillars.
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
    field = (1.0 - u) if reverse else u
    win = max(0.06, float(ACTIVE_PARAMS.get("edge_width", 0.22)))
    t = np.clip((progress * (1.0 + win) - field) / win, 0.0, 1.0)
    _blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.25)


def apply_iris_transition(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    progress: float,
    close_in: bool = False,
) -> None:
    """
    Symmetrical 1D curtain wipe around focal_u (default 0.5):
    - close_in=False ('iris_open'): blooms from focal_u to both tips (u=0, 1).
    - close_in=True ('iris_close'): sweeps from both tips inward to meet at focal_u.
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
    focal = float(ACTIVE_PARAMS.get("focal_u", 0.5))
    span = max(focal, 1.0 - focal, 0.1)
    dist_center = np.clip(np.abs(u - focal) / span, 0.0, 1.0)
    field = (1.0 - dist_center) if close_in else dist_center
    win = 0.20
    t = np.clip((progress * (1.0 + win) - field) / win, 0.0, 1.0)
    _blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.25)


def apply_zipper_merge(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    3-Act Mechanical Interlock:
    - Act I (0.00..0.28): Slider spark rips down the strip, splitting old mode into pitch-black tooth sockets.
    - Act II (0.28..0.80): Bold full-brightness teeth of incoming mode slide from opposite ends to interlock.
    - Act III (0.80..1.00): Teeth slam shut at the zone seams with a crisp metallic lock flash.
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
    teeth = float(max(2, int(ACTIVE_PARAMS.get("teeth_count", 4))))
    scaled = u * teeth
    zone = np.minimum(np.floor(scaled).astype(np.int32), int(teeth) - 1)
    local_u = scaled - zone
    is_even = (zone % 2) == 0

    if progress < 0.28:
        p1 = progress / 0.28
        unzipped_odd = (~is_even) & (u <= p1)
        rgb_old[unzipped_odd] = (rgb_old[unzipped_odd] * 0.04).astype(np.int32)
        slider_glow = np.clip(1.0 - np.abs(u - p1) / 0.09, 0.0, 1.0) ** 2
        if np.any(slider_glow > 0.0):
            g = slider_glow[:, np.newaxis]
            rgb_old[:] = np.clip(rgb_old * (1.0 - g * 0.5) + g * np.array([255, 235, 160]), 0, 255).astype(np.int32)
    elif progress < 0.80:
        p2 = (progress - 0.28) / 0.52
        tooth_pos = np.where(is_even, local_u, 1.0 - local_u)
        edge_w = max(0.06, float(ACTIVE_PARAMS.get("edge_width", 0.14)) * 0.6)
        # Pitch-black socket ahead of each sliding tooth
        rgb_old[:] = (rgb_old * 0.04).astype(np.int32)
        mask_in = tooth_pos <= p2
        np.copyto(rgb_old, rgb_new, where=mask_in[:, np.newaxis])
        stud = np.clip(1.0 - np.abs(tooth_pos - p2) / edge_w, 0.0, 1.0) ** 2
        if np.any(stud > 0.0):
            s = stud[:, np.newaxis]
            rgb_old[:] = np.clip(rgb_old + s * np.array([255, 240, 190]), 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.80) / 0.20
        np.copyto(rgb_old, rgb_new)
        seam_dist = np.minimum(local_u, 1.0 - local_u)
        seam_flash = (np.clip(1.0 - seam_dist / 0.14, 0.0, 1.0) * ((1.0 - p3) ** 2) * 210.0)[:, np.newaxis]
        np.clip(rgb_old + seam_flash, 0, 255, out=rgb_old, casting="unsafe")


# =============================================================================
# FAMILY C: KINETIC & PHYSICS-INSPIRED HANDOFFS
# =============================================================================

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
    u = _get_u(n)
    focal = float(ACTIVE_PARAMS.get("focal_u", 0.5))
    span = max(focal, 1.0 - focal, 0.1)
    dist_center = np.clip(np.abs(u - focal) / span, 0.0, 1.0)

    if progress < 0.42:
        p1 = progress / 0.42
        vac = max(0.04, (1.0 - p1 * 1.35) ** 2) if p1 < 0.72 else 0.04
        np.multiply(rgb_old, vac, out=rgb_old, casting="unsafe")
        head_dist = 1.0 - (p1 ** 1.85)
        d_head = dist_center - head_dist
        # Contrail behind each particle + bright head
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


def apply_prism_sweep(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Chromatic dispersion wipe: R, G, and B channels sweep with slight phase offsets,
    refracting the modes' colors into a natural rainbow prism edge at the boundary.
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
    win = max(0.08, float(ACTIVE_PARAMS.get("edge_width", 0.20)))
    shift = 0.08 * math.sin(progress * math.pi)
    for ch, offset in enumerate((shift, 0.0, -shift)):
        p_ch = np.clip(progress + offset, 0.0, 1.0)
        t = np.clip((p_ch * (1.0 + win) - u) / win, 0.0, 1.0)
        w = t * t * (3.0 - 2.0 * t)
        crest = 4.0 * t * (1.0 - t) * 0.22
        val = rgb_old[:, ch] * (1.0 - w) + rgb_new[:, ch] * w + (rgb_old[:, ch] + rgb_new[:, ch]) * crest
        rgb_old[:, ch] = np.clip(val, 0, 255).astype(np.int32)


def apply_flash_cut(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Zero-latency transient impact cut for real-time drops.
    Flashes brightly at progress ~ 0 and decays smoothly into the incoming mode.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    if progress < 0.15:
        p1 = progress / 0.15
        flash = p1 * 160.0
        blended = rgb_old * (1.0 - p1 * 0.5) + rgb_new * (0.5 + 0.5 * p1) + flash
    else:
        p2 = (progress - 0.15) / 0.85
        decay_exp = max(1.2, min(4.0, float(ACTIVE_PARAMS.get("flash_decay", 2.2)) * 0.4))
        decay = ((1.0 - p2) ** decay_exp) * 160.0
        blended = rgb_new + decay
    np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")


# =============================================================================
# FAMILY D: RHYTHMIC & DJ-STYLE CUT TRANSITIONS
# =============================================================================

def apply_staccato_shutter(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Beat-ratcheted iris shutter: snaps forward in N distinct kinetic surges
    instead of moving at constant linear velocity.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    steps = float(max(2, int(ACTIVE_PARAMS.get("chop_count", 4))))
    s = progress * steps
    k = math.floor(s)
    frac = s - k
    snapped_frac = min(1.0, frac * 1.8) ** 2
    p_ratchet = min(1.0, (k + snapped_frac) / steps)
    apply_iris_transition(rgb_old, rgb_new, p_ratchet, close_in=False)


def apply_transformer_cut(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    DJ crossfader 'transformer' stutter: gates rapidly between old and new modes
    across rhythmic subdivisions with increasing duty cycle for the incoming mode.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    gates = float(max(4, int(ACTIVE_PARAMS.get("chop_count", 4)) * 2))
    g = progress * gates
    gate_idx = int(g)
    phase = g - gate_idx
    duty_new = 0.15 + 0.75 * progress
    show_new = phase < duty_new
    edge_punch = 1.0 + 0.20 * math.exp(-abs(phase - duty_new) * 12.0)

    if show_new:
        np.clip(rgb_new * edge_punch, 0, 255, out=rgb_old, casting="unsafe")
    else:
        np.clip(rgb_old * edge_punch, 0, 255, out=rgb_old, casting="unsafe")
