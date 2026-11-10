"""
modes/Horizon_scanning_blade_mode.py
360-degree radar/lighthouse blade sweep around architectural centroid.
Lead: beat
Secondary: transient
"""

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Horizon_scanning_blade_mode(Mode):
    """
    Horizon Scanning Blade: Full-installation sweeping laser plane.
    Lead: beat (continuous 360-degree radar blade sweep driven by beat_phase and beat_pulse)
    Secondary: transient (white-hot leading-edge crest flare on is_real_beat and drop_hit)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)

    CORE_X: float = 0.620
    CORE_Y: float = 0.450

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

        self.sweep_speed: float = float(infos.get("sweep_speed", 1.0))
        self.blade_width: float = float(infos.get("blade_width", 0.15))

        self.angle: float = 0.0
        self.prev_phase: float = -1.0
        self.tip_flare: float = 0.0

        n = max(1, self.nb_of_leds)
        self._intensity = np.zeros(n, dtype=np.float64)
        self._wake = np.zeros(n, dtype=np.float64)
        self._ang_diff = np.zeros(n, dtype=np.float64)
        self._angles = np.zeros(n, dtype=np.float64)
        self._target_rgb = np.zeros((n, 3), dtype=np.float64)
        self._out_r = self._target_rgb[:, 0]
        self._out_g = self._target_rgb[:, 1]
        self._out_b = self._target_rgb[:, 2]

        self._update_angles()

    def _update_angles(self) -> None:
        """Compute polar angles around the architectural centroid in place."""
        n = max(1, self.nb_of_leds)
        np.subtract(self.spatial.x_norm[:n], self.CORE_X, out=self._intensity[:n])
        np.subtract(self.spatial.y_norm[:n], self.CORE_Y, out=self._ang_diff[:n])
        np.arctan2(self._ang_diff[:n], self._intensity[:n], out=self._angles[:n])
        self._intensity.fill(0.0)
        self._ang_diff.fill(0.0)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D room coordinates in place."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._update_angles()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "sweep_speed",
                "label": "Rotation Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 3.0,
                "default": 1.0,
                "step": 0.1,
                "attr": "sweep_speed",
            },
            {
                "key": "blade_width",
                "label": "Blade Thickness",
                "control": "slider",
                "valueType": "number",
                "min": 0.05,
                "max": 0.40,
                "default": 0.15,
                "step": 0.05,
                "attr": "blade_width",
            },
        ]

    def run(self) -> None:
        n = self.nb_of_leds
        if n <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        if ctx is not None and getattr(ctx, "is_silent", False):
            self.tip_flare = 0.0
            self._wake.fill(0.0)
            self.fade_to_black_segment_vectorized(0.35, 0, n - 1)
            return

        energy = float(getattr(ctx, "energy", 0.5)) if ctx is not None else 0.5
        phase = float(getattr(self.listener, "beat_phase", 0.0))

        if self.prev_phase < 0.0:
            self.prev_phase = phase
        d_phase = (phase - self.prev_phase) % 1.0
        if d_phase > 0.5:
            d_phase = 0.0
        self.prev_phase = phase

        eff_lock = max(self.rhythm_lock, float(getattr(self.listener, "beat_trust", 0.0)) * 0.65)
        lock_gate = min(1.0, eff_lock / 0.45)
        step_rhythmic = d_phase * 2.0 * math.pi * self.mood_pace * self.sweep_speed
        step_acoustic = self.dt * 3.2 * self.mood_pace * self.sweep_speed * (0.45 + 0.55 * energy)
        step = lock_gate * step_rhythmic + (1.0 - lock_gate) * step_acoustic
        self.angle = (self.angle + step + math.pi) % (2.0 * math.pi) - math.pi

        is_real_beat = bool(
            getattr(ctx, "is_real_beat", False)
            if ctx is not None
            else getattr(self.listener, "is_real_beat", False)
        )
        if self.drop_hit:
            self.tip_flare = 0.85
        elif is_real_beat:
            self.tip_flare = 0.55
        else:
            self.tip_flare *= math.exp(-self.dt * 12.0)

        # Symmetric 180-degree twin-beam horizon blade (angular distance modulo pi in [0, pi/2])
        ang_diff = self._ang_diff
        intensity = self._intensity
        wake = self._wake
        out = self._target_rgb

        np.subtract(self._angles, self.angle, out=ang_diff)
        np.add(ang_diff, 0.5 * math.pi, out=ang_diff)
        np.mod(ang_diff, math.pi, out=ang_diff)
        np.subtract(ang_diff, 0.5 * math.pi, out=ang_diff)
        np.abs(ang_diff, out=ang_diff)

        eff_width = max(0.01, self.blade_width) * (1.35 / max(0.5, self.mood_sharpness))
        inv_two_w_sq = 1.0 / (2.0 * eff_width * eff_width)
        np.multiply(ang_diff, ang_diff, out=ang_diff)
        np.multiply(ang_diff, -inv_two_w_sq, out=ang_diff)
        np.exp(ang_diff, out=intensity)

        # Modulate blade with confidence-blended beat pulse and maintain short phosphor wake
        pulse = self.beat_pulse(sharpness=2.2)
        gain = min(1.0, (0.35 + 0.65 * pulse + 0.20 * self.drop_decay) * self.transition_scale)
        np.multiply(intensity, gain, out=intensity)

        wake_decay = math.exp(-self.dt * (8.0 / max(0.5, self.mood_trail)))
        np.multiply(wake, wake_decay, out=wake)
        np.maximum(wake, intensity, out=wake)
        np.clip(wake, 0.0, 1.0, out=intensity)

        # Color: Emerald Neon (#00FF88: 0, 255, 136) with White-Hot leading edge
        np.multiply(intensity, self.tip_flare * 255.0, out=self._out_r)
        np.multiply(intensity, 255.0, out=self._out_g)
        flare_b = 136.0 + 119.0 * self.tip_flare
        np.multiply(intensity, flare_b, out=self._out_b)

        np.maximum(0.0, out, out=out)
        np.minimum(255.0, out, out=out)
        np.copyto(self.rgb_list, out, casting="unsafe")


HorizonScanningBlade = Horizon_scanning_blade_mode
