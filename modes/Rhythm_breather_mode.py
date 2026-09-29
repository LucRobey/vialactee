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

    def run(self) -> None:
        dt = getattr(self.listener, "dt", 1.0 / 60.0)

        # 1. Read rhythmic metrics from Listener facade
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        raw_conf = float(getattr(self.listener, "beat_confidence", 0.0))
        confidence = max(0.0, min(1.0, raw_conf))

        # 2. Compute Rhythmic vs Acoustic energy components (MODE_RULES Rule 1)
        # Locked Rhythmic component: Snappy exponential decay tied to continuous phase
        # Peaks instantly at phase=0.0 (beat strike) and decays over the duration of the beat
        rhythmic_energy = (1.0 - phase) ** self.pulse_sharpness

        # Acoustic Fallback component: Direct smoothed volume power
        # Modulated with a gentle sinusoidal breath for organic feeling
        power = float(getattr(self.listener, "asserved_total_power", 0.0))
        sine_breath = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase - (np.pi / 2.0)))
        acoustic_energy = power * (0.6 + 0.4 * sine_breath)

        # 3. Graceful Degradation Blend
        # High confidence -> Tight percussive pumping
        # Low confidence -> Fluid, ambient acoustic breathing
        blended_energy = (confidence * rhythmic_energy) + ((1.0 - confidence) * acoustic_energy)
        effective_brightness = self.ambient_floor + (1.0 - self.ambient_floor) * blended_energy
        effective_brightness = max(0.0, min(1.0, effective_brightness))

        # 4. Gated Real-Beat transient boost (MODE_RULES Rule 2)
        # On verified acoustic hits, provide an instant subtle contrast punch
        is_beat = getattr(self.listener, "is_beat", False)
        is_real = getattr(self.listener, "is_real_beat", False)
        if is_beat and is_real and confidence > 0.4:
            flash_punch = 0.20
        else:
            flash_punch = 0.0

        # 5. Slow chromatic hue drift
        self.current_hue_offset = (self.current_hue_offset + dt * self.drift_speed) % 1.0
        target_hue = (self.base_hue + self.current_hue_offset) % 1.0

        # 6. Vectorized Color Calculation (Zero Allocation)
        np.add(target_hue, self.spatial_hue_spread, out=self.hues)
        np.mod(self.hues, 1.0, out=self.hues)

        final_val = min(1.0, effective_brightness + flash_punch)
        self.vals.fill(final_val)

        # Pure 100% saturation for intense, vivid color
        self.sats.fill(1.0)

        target_rgb = RGB_HSV.fromHSV_toRGB_vectorized(self.hues, self.sats, self.vals)

        # 7. Vectorized smooth segment write with high color punch
        self.smooth_segment_vectorized(0.55, 0, self.nb_of_leds - 1, target_rgb)
