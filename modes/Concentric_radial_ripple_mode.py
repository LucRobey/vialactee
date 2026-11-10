"""
modes/Concentric_radial_ripple_mode.py
Expanding concentric liquid shockwave rings from architectural core.
Lead: beat
Secondary: level
"""

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Concentric_radial_ripple_mode(Mode):
    """
    Concentric Radial Ripple: High-speed liquid shockwaves expanding from the architectural core.
    Lead: beat (>= 70% algorithmic, >= 85% perceptual)
    Secondary: level (<= 20%)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("level",)

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

        self.ring_speed: float = float(infos.get("ring_speed", 1.2))
        self.cooldown: float = 0.0
        self.prev_beat_phase: float = 0.0

        # Pre-seed staggered concentric rings so all segments across r in [0.05, 0.75] illuminate immediately
        self.rings_r: np.ndarray = np.array([0.08, 0.34, 0.60], dtype=np.float64)
        self.rings_a: np.ndarray = np.array([0.92, 0.80, 0.68], dtype=np.float64)

        n = max(1, self.nb_of_leds)
        self._intensity: np.ndarray = np.zeros(n, dtype=np.float64)
        self._ring_scratch: np.ndarray = np.zeros(n, dtype=np.float64)
        self._radius: np.ndarray = np.zeros(n, dtype=np.float64)
        self._target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self._r_col: np.ndarray = self._target_rgb[:, 0]
        self._g_col: np.ndarray = self._target_rgb[:, 1]
        self._b_col: np.ndarray = self._target_rgb[:, 2]

        self._recompute_radius()

    def _recompute_radius(self) -> None:
        """Recompute Euclidean distance from architectural centroid (0.620, 0.450) in place."""
        np.subtract(self.spatial.x_norm, 0.620, out=self._radius)
        np.multiply(self._radius, self._radius, out=self._radius)
        np.subtract(self.spatial.y_norm, 0.450, out=self._ring_scratch)
        np.multiply(self._ring_scratch, self._ring_scratch, out=self._ring_scratch)
        np.add(self._radius, self._ring_scratch, out=self._radius)
        np.sqrt(self._radius, out=self._radius)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment and synchronize _radius."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._recompute_radius()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "ring_speed",
                "label": "Propagation Velocity",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 2.5,
                "default": 1.2,
                "step": 0.1,
                "attr": "ring_speed",
            },
        ]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        if ctx is not None and getattr(ctx, "is_silent", False):
            self.rings_a.fill(0.0)
            self.cooldown = 0.0
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        phase = float(getattr(self.listener, "beat_phase", 0.0))

        delta_p = (phase - self.prev_beat_phase) % 1.0
        if delta_p > 0.5:
            delta_p = 0.0
        self.prev_beat_phase = phase

        if self.cooldown > 0.0:
            self.cooldown = max(0.0, self.cooldown - self.dt)

        # Re-seed staggered rings after silence recovery or on drop impact
        if self.rings_a[0] <= 0.05 and self.rings_a[1] <= 0.05 and self.rings_a[2] <= 0.05:
            if energy > 0.08 or self.drop_hit:
                base_a = 0.72 + 0.28 * energy
                self.rings_r[0] = 0.08
                self.rings_r[1] = 0.34
                self.rings_r[2] = 0.60
                self.rings_a[0] = base_a
                self.rings_a[1] = base_a * 0.88
                self.rings_a[2] = base_a * 0.76
                self.cooldown = 0.20

        # Metrical wave velocity coupled to beat_phase (Lead: beat) and acoustic fallback (Secondary: level)
        lock_gate = min(1.0, self.rhythm_lock / 0.45)
        vel_rhythmic = delta_p * 1.35 * self.ring_speed * self.mood_pace
        vel_acoustic = self.dt * 1.15 * self.ring_speed * self.mood_pace * (0.45 + 0.55 * energy)
        vel = lock_gate * vel_rhythmic + (1.0 - lock_gate) * vel_acoustic
        decay = math.exp(-vel * (1.15 / self.mood_trail))

        spawn_amp = 1.15 if self.drop_hit else (0.72 + 0.28 * energy)
        for k in range(3):
            rk = self.rings_r[k] + vel
            if rk >= 0.78:
                rk %= 0.78
                self.rings_a[k] = spawn_amp
            else:
                self.rings_a[k] *= decay
            self.rings_r[k] = rk

        self._intensity.fill(0.0)
        sigma = 0.065
        inv_two_s_sq = -1.0 / (2.0 * sigma * sigma)

        for k in range(3):
            ak = self.rings_a[k]
            if ak > 0.01:
                np.subtract(self._radius, self.rings_r[k], out=self._ring_scratch)
                np.multiply(self._ring_scratch, self._ring_scratch, out=self._ring_scratch)
                np.multiply(self._ring_scratch, inv_two_s_sq, out=self._ring_scratch)
                np.exp(self._ring_scratch, out=self._ring_scratch)
                np.multiply(self._ring_scratch, ak, out=self._ring_scratch)
                np.add(self._intensity, self._ring_scratch, out=self._intensity)

        # Modulate amplitude with confidence-blended beat pulse (Lead) and level envelope (Secondary)
        pulse = self.beat_pulse(sharpness=2.2)
        gain = 0.22 + 0.58 * pulse + 0.20 * (energy * energy)
        np.multiply(self._intensity, gain, out=self._intensity)
        np.clip(self._intensity, 0.0, 1.0, out=self._intensity)

        # Color: True Ultraviolet (#9D00FF: 157, 0, 255) maintaining S = 1.000 >= 0.92
        np.multiply(self._intensity, 157.0, out=self._r_col)
        self._g_col.fill(0.0)
        np.multiply(self._intensity, 255.0, out=self._b_col)

        np.maximum(0.0, self._target_rgb, out=self._target_rgb)
        np.minimum(255.0, self._target_rgb, out=self._target_rgb)
        np.copyto(self.rgb_list, self._target_rgb, casting="unsafe")


ConcentricRadialRipple = Concentric_radial_ripple_mode
