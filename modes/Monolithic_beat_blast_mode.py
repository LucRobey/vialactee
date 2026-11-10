"""
modes/Monolithic_beat_blast_mode.py
Monolithic radial expansion / whole-installation pulse shockwave.
Lead: beat
Secondary: transient
"""

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Monolithic_beat_blast_mode(Mode):
    """
    Monolithic Beat Blast: Radial plasma detonation from architectural core.
    Lead: beat (>= 70% algorithmic, >= 85% perceptual)
    Secondary: transient (<= 20%)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)

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

        self.wave_speed: float = float(infos.get("wave_speed", 1.0))
        self.wave_width: float = float(infos.get("wave_width", 0.08))

        self.wave_phase: float = 0.0
        self.prev_beat_phase: float = 0.0
        self.white_flash: float = 0.0

        n = max(1, self.nb_of_leds)
        self._intensity = np.zeros(n, dtype=np.float64)
        self._intensity_2d = self._intensity[:, np.newaxis]
        self._diff_scratch = np.zeros(n, dtype=np.float64)
        self._flash_scratch = np.zeros(n, dtype=np.float64)
        self._flash_2d = self._flash_scratch[:, np.newaxis]
        self._target_rgb = np.zeros((n, 3), dtype=np.float64)
        self._lut_rgb = np.zeros((n, 3), dtype=np.int32)
        self._radius = np.zeros(n, dtype=np.float64)
        self._lut_indices = np.zeros(n, dtype=np.int32)

        self._recompute_spatial_buffers()

    def _recompute_spatial_buffers(self) -> None:
        """Compute normalized radial distance from architectural centroid and LUT indices in place."""
        dx = self.spatial.x_norm - 0.620
        dy = self.spatial.y_norm - 0.450
        np.hypot(dx, dy, out=self._radius)
        np.clip((self._radius / 0.70 * 255.0).astype(np.int32), 0, 255, out=self._lut_indices)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._recompute_spatial_buffers()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "wave_speed",
                "label": "Shockwave Speed",
                "valueType": "number",
                "min": 0.5,
                "max": 2.5,
                "default": 1.0,
                "step": 0.1,
                "attr": "wave_speed",
            },
            {
                "key": "wave_width",
                "label": "Wavefront Thickness",
                "valueType": "number",
                "min": 0.04,
                "max": 0.20,
                "default": 0.08,
                "step": 0.02,
                "attr": "wave_width",
            },
        ]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        if ctx is not None and getattr(ctx, "is_silent", False):
            self.white_flash = 0.0
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        phase = float(getattr(self.listener, "beat_phase", 0.0))

        delta_p = (phase - self.prev_beat_phase) % 1.0
        if delta_p > 0.5:
            delta_p = 0.0
        self.prev_beat_phase = phase

        lock_gate = min(1.0, self.rhythm_lock / 0.45)
        step_rhythmic = delta_p * self.mood_pace * self.wave_speed
        step_acoustic = self.dt * 1.5 * self.mood_pace * self.wave_speed * (0.45 + 0.55 * energy)
        step = lock_gate * step_rhythmic + (1.0 - lock_gate) * step_acoustic
        self.wave_phase = (self.wave_phase + step) % 1.0

        is_hit = self.drop_hit or (ctx is not None and getattr(ctx, "is_real_beat", False) and self.rhythm_lock > 0.4)
        if is_hit:
            self.white_flash = 1.0
        else:
            self.white_flash *= math.exp(-self.dt * 15.0)

        # Radial shockwave fronts with wavelength 0.30 and pure-black inter-wave troughs
        radial_wavelength = 0.30
        target_r = self.wave_phase * radial_wavelength
        np.subtract(self._radius, target_r, out=self._diff_scratch)
        np.divide(self._diff_scratch, radial_wavelength, out=self._diff_scratch)
        np.add(self._diff_scratch, 0.5, out=self._diff_scratch)
        np.mod(self._diff_scratch, 1.0, out=self._diff_scratch)
        np.subtract(self._diff_scratch, 0.5, out=self._diff_scratch)
        np.multiply(self._diff_scratch, radial_wavelength, out=self._diff_scratch)

        sigma = max(0.01, self.wave_width * 0.75)
        inv_two_w_sq = 1.0 / (2.0 * sigma * sigma)
        np.multiply(self._diff_scratch, self._diff_scratch, out=self._diff_scratch)
        np.multiply(self._diff_scratch, -inv_two_w_sq, out=self._diff_scratch)
        np.exp(self._diff_scratch, out=self._intensity)
        np.subtract(self._intensity, 0.05, out=self._intensity)
        np.multiply(self._intensity, 1.0 / 0.95, out=self._intensity)
        np.maximum(0.0, self._intensity, out=self._intensity)

        pulse = self.beat_pulse(sharpness=2.4)
        gain = 0.20 + 0.80 * pulse + 0.25 * self.drop_decay
        np.multiply(self._intensity, gain, out=self._intensity)
        np.clip(self._intensity, 0.0, 1.0, out=self._intensity)

        np.take(self.palette_lut, self._lut_indices, axis=0, out=self._lut_rgb)
        np.multiply(self._lut_rgb, self._intensity_2d, out=self._target_rgb)

        if self.white_flash > 0.05:
            np.multiply(self._intensity, self.white_flash * 75.0, out=self._flash_scratch)
            np.add(self._target_rgb, self._flash_2d, out=self._target_rgb)

        np.maximum(0.0, self._target_rgb, out=self._target_rgb)
        np.minimum(255.0, self._target_rgb, out=self._target_rgb)
        np.copyto(self.rgb_list, self._target_rgb, casting="unsafe")


MonolithicBeatBlast = Monolithic_beat_blast_mode
