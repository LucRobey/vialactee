"""
transitions/catalog/_common.py - Shared contracts, active parameters, and O(N) math kernels.

Forms the zero-dependency root of the `transitions/catalog/` DAG:
  _common.py -> catalog/<transition>.py -> catalog/__init__.py -> families.py / manager.py / engine.py
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Callable, Dict, FrozenSet, Optional, Tuple
import numpy as np


class TransitionFamily(str, Enum):
    """Abstract transition contract traits. A transition may belong to multiple families."""
    ROOM_EPI_2D = "ROOM_EPI_2D"
    ROOM_SWEEP_2D = "ROOM_SWEEP_2D"
    STRIP_SWEEP_1D = "STRIP_SWEEP_1D"
    STRIP_FOCAL_1D = "STRIP_FOCAL_1D"
    STAGGERABLE = "STAGGERABLE"
    STOCHASTIC_ORGANIC = "STOCHASTIC_ORGANIC"
    RHYTHMIC_CHOP = "RHYTHMIC_CHOP"
    MODE_COOPERATIVE = "MODE_COOPERATIVE"


@dataclass(frozen=True)
class TransitionSpec:
    """Self-contained specification co-locating a transition's contract metadata and pixel shader."""
    name: str
    families: FrozenSet[TransitionFamily]
    duration: float
    kind: str  # "strip_1d" | "spatial_spectacle" | "spatial_wipe" | "spatial_room"
    handler: Callable[..., None]
    aliases: Tuple[str, ...] = ()
    self_typed_aliases: Tuple[str, ...] = ()


ROOM_MAX_X: float = 430.0
ROOM_MAX_Y: float = 246.0
_WHITE_BEAM = np.array([255, 255, 255])

_BASE_PARAMS: Dict[str, Any] = {
    "epicenter_x": 0.60,
    "epicenter_y": 0.50,
    "spiral_sign": 1.0,
    "spiral_arms": 2,
    "beam_thickness": 0.15,
    "trench_width": 0.14,
    "edge_width": 0.14,
    "teeth_count": 4,
    "focal_u": 0.5,
    "seed": 0.0,
    "spark_intensity": 1.0,
    "chop_count": 3,
    "flash_decay": 5.5,
    "mode_handshake": False,
}

ACTIVE_PARAMS: Dict[str, Any] = dict(_BASE_PARAMS)

_U_CACHE: Dict[int, np.ndarray] = {}
_HASH_CACHE: Dict[int, np.ndarray] = {}


def set_room_bounds(max_x: float, max_y: float) -> None:
    """Update the shared physical room dimensions used by 2D spatial transitions."""
    global ROOM_MAX_X, ROOM_MAX_Y
    if max_x > 0 and max_y > 0:
        ROOM_MAX_X = float(max_x)
        ROOM_MAX_Y = float(max_y)


def set_transition_params(params: Optional[Dict[str, Any]] = None) -> None:
    """Update or reset the active generative transition parameters."""
    ACTIVE_PARAMS.update(_BASE_PARAMS)
    if params:
        ACTIVE_PARAMS.update(params)


def get_u(n: int) -> np.ndarray:
    """Return cached 1D normalized coordinate array u in [0.0, 1.0] of length n."""
    arr = _U_CACHE.get(n)
    if arr is None:
        arr = np.linspace(0.0, 1.0, max(1, n), dtype=np.float32)
        _U_CACHE[n] = arr
    return arr


def get_hash(n: int) -> np.ndarray:
    """Return cached deterministic pseudo-random threshold array in [0.0, 1.0] of length n."""
    arr = _HASH_CACHE.get(n)
    if arr is None:
        idx = np.arange(max(1, n), dtype=np.float32)
        arr = np.mod(np.sin(idx * 12.9898 + 78.233) * 43758.5453, 1.0).astype(np.float32)
        _HASH_CACHE[n] = arr
    return arr


def blend_with_crest(
    rgb_old: np.ndarray,
    rgb_new: np.ndarray,
    t: np.ndarray,
    crest_gain: float = 0.25,
) -> None:
    """In-place smoothstep blend between rgb_old and rgb_new with a self-colored luminance crest."""
    w = (t * t * (3.0 - 2.0 * t))[:, np.newaxis]
    crest = (4.0 * t * (1.0 - t) * crest_gain)[:, np.newaxis]
    blended = rgb_old * (1.0 - w) + rgb_new * w + (rgb_old + rgb_new) * crest
    np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")


def norm_coords(
    n: int,
    coords: Optional[np.ndarray],
    room_max_x: Optional[float] = None,
    room_max_y: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return normalized 1D arrays (nx, ny) in [0..1] from 2D coords or 1D strip fallback."""
    rx = ROOM_MAX_X if room_max_x is None else float(room_max_x)
    ry = ROOM_MAX_Y if room_max_y is None else float(room_max_y)
    if coords is not None and len(coords) == n:
        nx = np.clip(coords[:, 0] / max(1.0, rx), 0.0, 1.0)
        ny = np.clip(coords[:, 1] / max(1.0, ry), 0.0, 1.0)
        return nx, ny
    u = get_u(n)
    return u, u


def central_epicenter() -> Tuple[float, float]:
    """Return normalized (ex, ey) epicenter, mapping legacy 0.5 default to the chandelier heart (0.60, 0.50)."""
    raw_ex = float(ACTIVE_PARAMS.get("epicenter_x", 0.60))
    ex = 0.60 if abs(raw_ex - 0.5) < 1e-3 else raw_ex
    ey = float(ACTIVE_PARAMS.get("epicenter_y", 0.50))
    return ex, ey


def apply_field_wipe(
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
