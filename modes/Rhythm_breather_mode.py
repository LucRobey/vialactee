"""
Rhythm Breather Mode
Continuous phase-locked breathing visual with confidence-weighted graceful degradation.
Uses self.beat_pulse(self.pulse_sharpness) and continuous breath progression so it remains
fluid even when beat_phase is stalled and beat_trust is zero, without branching on ctx.scene.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Rhythm_breather_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "base_hue",
                "label": "Base Hue",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.60,
                "attr": "base_hue",
            },
            {
                "key": "pulse_sharpness",
                "label": "Beat Sharpness",
                "control": "slider",
                "valueType": "number",
                "min": 1.0,
                "max": 4.0,
                "step": 0.2,
                "default": 2.2,
                "attr": "pulse_sharpness",
            },
            {
                "key": "ambient_floor",
                "label": "Ambient Floor",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 0.3,
                "step": 0.02,
                "default": 0.08,
                "attr": "ambient_floor",
            },
            {
                "key": "drift_speed",
                "label": "Hue Drift Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 0.05,
                "step": 0.005,
                "default": 0.01,
                "attr": "drift_speed",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Configurable parameters
        self.base_hue = float(infos.get("rhythm_breather_base_hue", 0.60))
        self.pulse_sharpness = float(infos.get("rhythm_breather_sharpness", 2.2))
        self.ambient_floor = float(infos.get("rhythm_breather_ambient_floor", 0.08))
        self.drift_speed = float(infos.get("rhythm_breather_drift_speed", 0.01))

        # Internal state
        self.current_hue_offset: float = self.segment_phase_offset
        self.breath_angle: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated spatial arrays (ZERO runtime heap allocation)
        self.spatial_coords: np.ndarray = np.linspace(0.0, 1.0, self.nb_of_leds, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.grad_colors: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.spatial_blend: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        tension = float(ctx.tension if ctx is not None else 0.0)
        spectral_tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        lock = self.rhythm_lock
        is_locked = bool(ctx.is_locked if ctx is not None else (lock >= 0.5))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        # 1. Confidence-blended beat_pulse() + continuous breath wave when beat_phase is stalled
        self.breath_angle = (self.breath_angle + self.dt * 2.2 * self.mood_pace) % (2.0 * math.pi)
        pulse = self.beat_pulse(self.pulse_sharpness)
        breath_mod = 0.85 + 0.15 * (0.5 + 0.5 * math.sin(self.breath_angle)) * (1.0 - lock)
        blended_energy = pulse * breath_mod

        effective_floor = self.ambient_floor
        effective_brightness = max(0.0, min(1.0, effective_floor + (1.0 - effective_floor) * blended_energy))

        # 2. Gated Real-Beat transient boost (1-frame only, no 1.5s scene lock)
        is_beat = bool(getattr(self.listener, "is_beat", False))
        if self.drop_hit or (is_beat and is_real and (lock > 0.35 or is_locked)):
            flash_punch = 0.20 + 0.15 * tension
        else:
            flash_punch = 0.0

        # 3. Spatial color gradient across all 3 mood palette slots via palette_sample
        self.current_hue_offset = (self.current_hue_offset + self.dt * self.drift_speed * self.mood_pace) % 1.0
        hue_nudge = (self.base_hue - 0.60) * 0.35 + 0.15 * math.sin(2.0 * math.pi * self.current_hue_offset)
        shift = 0.12 * spectral_tilt + 0.08 * math.sin(self.breath_angle) + hue_nudge
        np.add(self.spatial_coords, shift, out=self.spatial_blend)
        np.clip(self.spatial_blend, 0.0, 1.0, out=self.spatial_blend)
        self.palette_sample(self.spatial_blend, self.grad_colors)

        warmth = min(1.0, self.mood_accent + flash_punch * 1.2)
        if warmth > 0.005:
            hi = self.highlight_color
            inv_w = 1.0 - warmth
            for c in range(3):
                np.multiply(self.grad_colors[:, c], inv_w, out=self.grad_colors[:, c])
                np.add(self.grad_colors[:, c], warmth * float(hi[c]), out=self.grad_colors[:, c])

        # 4. Vectorized Intensity Synthesis (Zero Allocation)
        final_val = min(1.0, effective_brightness + flash_punch + 0.20 * self.drop_decay)
        np.multiply(self.grad_colors, final_val, out=self.target_rgb)

        # 5. Vectorized smooth segment write
        self.smooth_segment_vectorized(0.55, 0, self.nb_of_leds - 1, self.target_rgb)
