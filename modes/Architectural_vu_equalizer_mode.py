"""
modes/Architectural_vu_equalizer_mode.py
Unified structural VU meter rising through floor to canopy across all 11 chandelier segments.
Lead: level (master hydraulic fluid column altitude and volume breathing).
Secondary: spectrum (spectral_tilt lateral/meniscus modulation).
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Architectural_vu_equalizer_mode(Mode):
    """
    Architectural VU Equalizer: Solid vertical liquid columns across all pillars, bridges, and canopy.
    Lead: level (>= 70% algorithmic, >= 85% perceptual)
    Secondary: spectrum (<= 20%)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "level"
    SECONDARY: tuple = ("spectrum",)

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.spatial = SegmentSpatialProfile(
            segment_name=segment_name,
            nb_of_leds=self.nb_of_leds,
            tags=infos.get("tags", ()),
            orientation=infos.get("orientation"),
        )

        self.gain: float = float(infos.get("gain", 1.0))
        self.decay_rate: float = float(infos.get("decay_rate", 6.0))
        self.level_h: float = 0.0

        n = max(1, self.nb_of_leds)
        self._intensity = np.zeros(n, dtype=np.float64)
        self._intensity_2d = self._intensity[:, np.newaxis]
        self._diff_scratch = np.zeros(n, dtype=np.float64)
        self._target_rgb = np.zeros((n, 3), dtype=np.float64)
        self._color_gradient = np.zeros((n, 3), dtype=np.float64)
        self._z = self.spatial.altitude
        self._compute_color_gradient()

    def _compute_color_gradient(self) -> None:
        """Precompute the high-saturation altitude color gradient (S = 1.0) in place."""
        n = max(1, self.nb_of_leds)
        self._z = self.spatial.altitude
        for i in range(n):
            zi = float(self._z[i])
            if zi < 0.65:
                t = zi / 0.65
                self._color_gradient[i, 0] = 255.0
                self._color_gradient[i, 1] = 153.0 + 62.0 * t
                self._color_gradient[i, 2] = 0.0
            elif zi < 0.88:
                t = (zi - 0.65) / 0.23
                self._color_gradient[i, 0] = 255.0
                self._color_gradient[i, 1] = 215.0 * (1.0 - t)
                self._color_gradient[i, 2] = 0.0
            else:
                self._color_gradient[i, 0] = 255.0
                self._color_gradient[i, 1] = 0.0
                self._color_gradient[i, 2] = 51.0

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates and refresh altitude gradient."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._compute_color_gradient()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "gain",
                "label": "Meter Sensitivity",
                "valueType": "number",
                "min": 0.5,
                "max": 2.0,
                "default": 1.0,
                "step": 0.1,
                "attr": "gain",
            },
            {
                "key": "decay_rate",
                "label": "Ballistic Gravity Falloff",
                "valueType": "number",
                "min": 2.0,
                "max": 12.0,
                "default": 6.0,
                "step": 0.5,
                "attr": "decay_rate",
            },
        ]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        if ctx is not None and getattr(ctx, "is_silent", False):
            # Asymmetric ballistic drain during silence (prevents post-silence frame 1 popping)
            self.level_h = max(0.0, self.level_h - self.dt * 6.0)
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        target_h = min(1.0, energy * self.gain * self.mood_pace)

        if target_h > self.level_h:
            alpha_attack = 1.0 - math.exp(-self.dt * 32.0)
            self.level_h += (target_h - self.level_h) * alpha_attack
        else:
            alpha_decay = 1.0 - math.exp(-self.dt * self.decay_rate)
            self.level_h += (target_h - self.level_h) * alpha_decay

        tilt = float(getattr(ctx, "spectral_tilt", 0.0)) if ctx is not None else 0.0
        tilt_scale = 0.12 if self.spatial.pillar_index in (0, 3) else -0.05
        h_eff = max(0.0, min(1.0, self.level_h * (1.0 + tilt_scale * tilt)))

        # Zero-allocation in-place continuous meniscus evaluation
        np.subtract(self._z, h_eff, out=self._diff_scratch)
        np.maximum(0.0, self._diff_scratch, out=self._diff_scratch)
        np.multiply(self._diff_scratch, -14.0, out=self._diff_scratch)
        np.exp(self._diff_scratch, out=self._intensity)

        np.multiply(self._color_gradient, self._intensity_2d, out=self._target_rgb)

        np.maximum(0.0, self._target_rgb, out=self._target_rgb)
        np.minimum(255.0, self._target_rgb, out=self._target_rgb)
        np.copyto(self.rgb_list, self._target_rgb, casting="unsafe")


ArchitecturalVUEqualizer = Architectural_vu_equalizer_mode
