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
    "beam_thickness": 0.04,
    "edge_width": 0.22,
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
        "beam_thickness": 0.04,
        "edge_width": 0.22,
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
    Divides the strip into 6 interlocking comb zones; even zones sweep forward
    while odd zones sweep backward, locking together like a zipper.
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
    scaled = u * 6.0
    zone = np.floor(scaled).astype(np.int32)
    local_u = scaled - zone
    field = np.where((zone % 2) == 0, local_u, 1.0 - local_u)
    win = max(0.08, float(ACTIVE_PARAMS.get("edge_width", 0.22)))
    t = np.clip((progress * (1.0 + win) - field) / win, 0.0, 1.0)
    _blend_with_crest(rgb_old, rgb_new, t, crest_gain=0.20)


# =============================================================================
# FAMILY C: KINETIC & PHYSICS-INSPIRED HANDOFFS
# =============================================================================

def apply_collider(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Two energy particles launch from opposite strip ends (u=0, u=1), accelerate toward
    focal_u (default 0.5), collide at progress=0.45, and unleash an expanding shockwave.
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

    if progress < 0.45:
        p1 = (progress / 0.45) ** 1.8
        head_dist = 1.0 - p1
        wake_mask = dist_center > head_dist
        rgb_old[wake_mask] = (rgb_old[wake_mask] * 0.22).astype(np.int32)

        d_head = np.abs(dist_center - head_dist)
        glow = np.clip(1.0 - d_head / 0.14, 0.0, 1.0) ** 2
        if np.any(glow > 0.0):
            g = glow[:, np.newaxis]
            surge = rgb_old * (1.0 - g * 0.5) + rgb_new * (g * 0.8) + (220.0 * g)
            np.clip(surge, 0, 255, out=rgb_old, casting="unsafe")
    else:
        p2 = ((progress - 0.45) / 0.55) ** 0.75
        win = 0.20
        t = np.clip((p2 * (1.0 + win) - dist_center) / win, 0.0, 1.0)
        w = (t * t * (3.0 - 2.0 * t))[:, np.newaxis]
        rim = (4.0 * t * (1.0 - t) * (1.0 - p2 * 0.7))[:, np.newaxis]
        out = rgb_old * (1.0 - w) * 0.22 + rgb_new * w + (180.0 * rim)
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
