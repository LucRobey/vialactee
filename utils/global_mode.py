"""
utils/global_mode.py - Spatial geometry and architectural role resolver for Global Modes.

Provides pre-allocated 2D room coordinates (x_norm, y_norm, altitude), strip-intrinsic
coordinates (u, u_center), and architectural roles ('pillar', 'bridge', 'canopy', or
'composite' in single-strip studio/test previews) so Global Modes can orchestrate all
11 segments of the chandelier as a single cohesive instrument with zero runtime allocations.
"""

from typing import Any, Dict, Optional, Sequence, Tuple
import numpy as np

ROOM_MAX_X: float = 431.0
ROOM_MAX_Y: float = 245.0

# Canonical full-profile segment geometry (start_x, start_y, step_x, step_y, role, tier, half, pillar_idx)
_CANONICAL_SEGMENTS: Dict[str, Tuple[int, int, int, int, str, str, str, int]] = {
    "v1":  (205, 188, 0, -1, "pillar", "pillar", "left",  0),
    "v2":  (292, 245, 0, -1, "pillar", "pillar", "left",  1),
    "v3":  (383, 245, 0, -1, "pillar", "pillar", "right", 2),
    "v4":  (431, 204, 0, -1, "pillar", "pillar", "right", 3),
    "h00": (0,   16,  1,  0, "canopy", "canopy", "left",  0),
    "h20": (292, 16,  1,  0, "canopy", "canopy", "right", 2),
    "h30": (383, 1,   1,  0, "canopy", "canopy", "right", 3),
    "h11": (205, 73,  1,  0, "bridge", "mid",    "left",  1),
    "h32": (383, 85,  1,  0, "bridge", "mid",    "right", 3),
    "h10": (205, 189, 1,  0, "bridge", "low",    "left",  0),
    "h31": (383, 171, 1,  0, "bridge", "low",    "right", 2),
    # Small profile (3 vertical strips -> mapped across the 3 architectural roles)
    "s1":  (100, 49,  0, -1, "canopy", "canopy", "left",  0),
    "s2":  (215, 108, 0, -1, "pillar", "pillar", "left",  1),
    "s3":  (330, 92,  0, -1, "bridge", "mid",    "right", 2),
}


def normalize_segment_id(segment_name: str) -> str:
    """Extract canonical segment id (e.g. 'v4', 'h00', 's1') from segment name."""
    raw = str(segment_name or "").strip()
    if raw.lower().startswith("segment "):
        raw = raw[8:].strip()
    elif raw.lower().startswith("segment_"):
        raw = raw[8:].strip()
    return raw.lower()


class SegmentSpatialProfile:
    """
    Pre-allocated spatial & architectural profile for a single segment inside a Global Mode.
    Zero heap allocations after initialization.
    """

    def __init__(
        self,
        segment_name: str,
        nb_of_leds: int,
        tags: Sequence[str] = (),
        orientation: Optional[str] = None,
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        self.nb_of_leds: int = max(0, int(nb_of_leds))
        n = max(1, self.nb_of_leds)
        self.seg_id: str = normalize_segment_id(segment_name)

        # Strip-intrinsic coordinates in [0, 1]
        self.u: np.ndarray = np.linspace(0.0, 1.0, n, dtype=np.float64)
        self.u_center: np.ndarray = np.abs(self.u * 2.0 - 1.0)

        # 2D room coordinates in [0, 1]
        self.x_norm: np.ndarray = np.zeros(n, dtype=np.float64)
        self.y_norm: np.ndarray = np.zeros(n, dtype=np.float64)
        self.altitude: np.ndarray = np.zeros(n, dtype=np.float64)

        # Architectural classification
        self.role: str = "composite"
        self.tier: str = "composite"
        self.half: str = "left"
        self.pillar_index: int = 0
        self.is_inner_pillar: bool = False

        # Composite slice boundaries (used when previewing in 1D mode_studio or unit tests)
        self.split_1: int = n // 3
        self.split_2: int = (2 * n) // 3

        self.bind(self.seg_id, orientation, tags, coords_array)

    def bind(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Resolve or update role, tags, and 2D room coordinates in place."""
        if seg_id:
            self.seg_id = normalize_segment_id(seg_id)

        n = max(1, self.nb_of_leds)
        tag_set = {str(t) for t in (tags or ())}

        if self.seg_id in _CANONICAL_SEGMENTS:
            sx, sy, dx, dy, role, tier, half, p_idx = _CANONICAL_SEGMENTS[self.seg_id]
            self.role = role
            self.tier = tier
            self.half = half
            self.pillar_index = p_idx
            self.is_inner_pillar = self.seg_id in ("v2", "v3", "s2")
            idx = np.arange(n, dtype=np.float64)
            self.x_norm[:] = np.clip((sx + idx * dx) / ROOM_MAX_X, 0.0, 1.0)
            self.y_norm[:] = np.clip((sy + idx * dy) / ROOM_MAX_Y, 0.0, 1.0)
        elif tag_set or orientation in ("vertical", "horizontal"):
            is_vert = (orientation == "vertical") or ("orientation:vertical" in tag_set)
            if is_vert:
                self.role = "pillar"
                self.tier = "pillar"
            elif "tier:canopy" in tag_set:
                self.role = "canopy"
                self.tier = "canopy"
            else:
                self.role = "bridge"
                self.tier = "low" if "tier:low" in tag_set else "mid"
            self.half = "right" if "half:right" in tag_set else "left"
            self.is_inner_pillar = "pos:inner" in tag_set
            self.pillar_index = 1 if self.is_inner_pillar else (3 if self.half == "right" else 0)
            self.x_norm[:] = self.u
            self.y_norm[:] = 1.0 - self.u if is_vert else 0.5
        else:
            # Studio / unit test preview: split strip into 3 architectural zones
            self.role = "composite"
            self.tier = "composite"
            self.half = "left"
            self.pillar_index = 1
            self.is_inner_pillar = True
            self.x_norm[:] = self.u
            self.y_norm[:] = 1.0 - self.u

        if coords_array is not None and len(coords_array) >= self.nb_of_leds and self.nb_of_leds > 0:
            self.x_norm[:self.nb_of_leds] = np.clip(coords_array[:self.nb_of_leds, 0] / ROOM_MAX_X, 0.0, 1.0)
            self.y_norm[:self.nb_of_leds] = np.clip(coords_array[:self.nb_of_leds, 1] / ROOM_MAX_Y, 0.0, 1.0)

        np.subtract(1.0, self.y_norm, out=self.altitude)
