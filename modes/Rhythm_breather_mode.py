"""
Rhythm Breather Mode
Continuous phase-locked breathing visual with confidence-weighted graceful degradation.
Tests the Anticipation Flywheel's continuous phase θ in [0.0, 1.0) and verifies smooth
crossfading into fluid acoustic volume breathing when beat confidence drops.
Adheres strictly to modes/MODE_RULES.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


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
        self.current_hue_offset: float = 0.0

        # Pre-allocated spatial arrays (ZERO runtime heap allocation)
        self.spatial_coords: np.ndarray = np.linspace(0.0, 1.0, self.nb_of_leds, dtype=np.float64)
        # Subtle spatial hue gradient across the strip for visual depth
        self.spatial_hue_spread: np.ndarray = self.spatial_coords * 0.12

        self.hues: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.sats: np.ndarray = np.ones(self.nb_of_leds, dtype=np.float64)
        self.vals: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.grad_colors: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.spatial_blend: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        dt = getattr(self.listener, "dt", 1.0 / 60.0)

        # 1. Read rhythmic metrics and MusicalContextEngine facade
        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        power = float(ctx.power if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        energy = float(ctx.energy if ctx is not None else power)
        tension = float(ctx.tension if ctx is not None else 0.0)
        spectral_tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        confidence = float(ctx.beat_trust if ctx is not None else getattr(self.listener, "beat_confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        is_locked = bool(ctx.is_locked if ctx is not None else (confidence >= 0.5))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        scene = getattr(ctx, "scene", None)
        is_drop_impact_scene = bool(scene == "DROP_IMPACT")
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or is_drop_impact_scene
        drop_progress = float(ctx.drop_progress if ctx is not None else 0.0)
        is_silent = bool(ctx.is_silent if ctx is not None else False)

        # 2. Compute Rhythmic vs Acoustic energy components (MODE_RULES Rule 1)
        # Tension sharpens pulse decay for snappier percussive response
        effective_sharpness = self.pulse_sharpness + 1.2 * tension
        rhythmic_energy = (1.0 - phase) ** effective_sharpness

        # Acoustic Fallback component: Direct smoothed volume / master energy
        # Modulated with a gentle sinusoidal breath for organic feeling
        sine_breath = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase - (np.pi / 2.0)))
        acoustic_energy = 0.0 if is_silent else energy * (0.6 + 0.4 * sine_breath)

        # 3. Graceful Degradation Blend
        # High confidence -> Tight percussive pumping
        # Low confidence -> Fluid, ambient acoustic breathing
        blended_energy = (confidence * rhythmic_energy) + ((1.0 - confidence) * acoustic_energy)
        effective_floor = 0.0 if is_silent else self.ambient_floor
        effective_brightness = effective_floor + (1.0 - effective_floor) * blended_energy
        effective_brightness = max(0.0, min(1.0, effective_brightness))

        # 4. Gated Real-Beat transient boost (MODE_RULES Rule 2) & Drop Flare
        is_beat = getattr(self.listener, "is_beat", False)
        if is_drop or is_drop_impact_scene:
            flash_punch = 0.50 * (drop_progress if drop_progress > 0.0 else 1.0)
        elif is_beat and is_real and (confidence > 0.4 or is_locked):
            flash_punch = 0.20 + 0.15 * tension
        else:
            flash_punch = 0.0

        # 5. Spatial color gradient derived from self.mood_colors
        mood = self.mood_colors
        # Base gradient blends Primary (0) and Secondary (1)
        np.add(self.spatial_coords, 0.1 * spectral_tilt, out=self.spatial_blend)
        np.clip(self.spatial_blend, 0.0, 1.0, out=self.spatial_blend)
        m0, m1 = mood[0], mood[1]
        for c in range(3):
            m0_c = float(m0[c])
            diff = float(m1[c]) - m0_c
            np.multiply(self.spatial_blend, diff, out=self.grad_colors[:, c])
            np.add(self.grad_colors[:, c], m0_c, out=self.grad_colors[:, c])

        # On transient punch or drop impact, blend toward Accent (2) / Highlight (3)
        if flash_punch > 0.01:
            accent_target = mood[3] if is_drop else mood[2]
            punch_weight = min(1.0, flash_punch * 1.5)
            inv_punch = 1.0 - punch_weight
            for c in range(3):
                np.multiply(self.grad_colors[:, c], inv_punch, out=self.grad_colors[:, c])
                np.add(self.grad_colors[:, c], punch_weight * float(accent_target[c]), out=self.grad_colors[:, c])

        # 6. Vectorized Intensity Synthesis (Zero Allocation)
        final_val = min(1.0, effective_brightness + flash_punch)
        np.multiply(self.grad_colors, final_val, out=self.target_rgb)

        # 7. Vectorized smooth segment write with high color punch
        self.smooth_segment_vectorized(0.55, 0, self.nb_of_leds - 1, self.target_rgb)
