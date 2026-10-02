"""
Beat Runner Mode
Dynamic BPM-scaled kinematic laser runner for speaker-time latency and boundary sync verification.
Sweeps a concentrated luminous bead across the strip, striking segment boundaries precisely on beat ticks.
Diffuses into an expanded, volume-reactive cloud when beat tracking confidence drops.
Adheres strictly to modes/MODE_RULES.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import utils.colors as colors


class Beat_runner_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "motion_style",
                "label": "Motion Style",
                "control": "list",
                "valueType": "string",
                "default": "pendulum",
                "options": [
                    {"label": "Harmonic Bounce (Pendulum)", "value": "pendulum"},
                    {"label": "Unidirectional Sweep", "value": "sweep"},
                ],
                "attr": "motion_style",
            },
            {
                "key": "base_hue",
                "label": "Laser Hue",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.08,  # Fiery neon orange / amber
                "attr": "base_hue",
            },
            {
                "key": "head_width",
                "label": "Laser Width",
                "control": "slider",
                "valueType": "number",
                "min": 0.8,
                "max": 4.0,
                "step": 0.2,
                "default": 1.5,
                "attr": "head_width",
            },
            {
                "key": "trail_decay",
                "label": "Trail Decay",
                "control": "slider",
                "valueType": "number",
                "min": 0.05,
                "max": 0.50,
                "step": 0.05,
                "default": 0.22,
                "attr": "trail_decay",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Configurable parameters
        self.motion_style = str(infos.get("beat_runner_motion_style", "pendulum"))
        self.base_hue = float(infos.get("beat_runner_base_hue", 0.08))
        self.head_width = float(infos.get("beat_runner_head_width", 1.5))
        self.trail_decay = float(infos.get("beat_runner_trail_decay", 0.22))

        # Pre-allocated spatial arrays (ZERO runtime heap allocation)
        self.led_indices: np.ndarray = np.arange(self.nb_of_leds, dtype=np.float64)
        self.dist_sq: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.gauss_weights: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)

        self.hues: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.sats: np.ndarray = np.ones(self.nb_of_leds, dtype=np.float64)
        self.vals: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.beam_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 1:
            return

        # 1. Decay previous frame tails for smooth motion blur
        self.fade_to_black_segment_vectorized(self.trail_decay, 0, self.nb_of_leds - 1)

        # 2. Read rhythmic state and MusicalContextEngine facade
        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        power = float(ctx.power if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        energy = float(ctx.energy if ctx is not None else power)
        tension = float(ctx.tension if ctx is not None else 0.0)
        is_locked = bool(ctx.is_locked if ctx is not None else (float(getattr(self.listener, "beat_confidence", 0.0)) >= 0.5))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False)
        confidence = float(ctx.beat_trust if ctx is not None else getattr(self.listener, "beat_confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        # 3. Calculate target cursor position mapped strictly to continuous phase θ
        max_idx = float(self.nb_of_leds - 1)
        if self.motion_style == "sweep":
            # Unidirectional sweep: travels 0 -> max_idx over 1 beat cycle
            cursor_pos = phase * max_idx
        else:
            # Harmonic pendulum: oscillates 0 -> max_idx -> 0 over 1 beat cycle
            harmonic_factor = 0.5 * (1.0 - np.cos(2.0 * np.pi * phase))
            cursor_pos = harmonic_factor * max_idx

        # 4. Confidence-Weighted Beam Width & Fallback (MODE_RULES Rule 1)
        # Tension narrows beam into sharp laser bead; low confidence diffuses into cloud
        sigma = (self.head_width + (1.0 - confidence) * 4.0) * (1.0 - 0.25 * tension)
        two_sigma_sq = 2.0 * (sigma ** 2)

        # 5. Vectorized Gaussian Intensity Calculation
        np.subtract(self.led_indices, cursor_pos, out=self.dist_sq)
        np.square(self.dist_sq, out=self.dist_sq)
        np.divide(-self.dist_sq, two_sigma_sq, out=self.gauss_weights)
        np.exp(self.gauss_weights, out=self.gauss_weights)

        # Intensity blend: confidence gives laser power, fallback scales with visual energy
        base_intensity = confidence * 1.0 + (1.0 - confidence) * max(0.2, energy)
        np.multiply(self.gauss_weights, base_intensity, out=self.vals)
        drop_progress = float(ctx.drop_progress if ctx is not None else 0.0)
        is_drop_impact_scene = bool(getattr(ctx, "scene", None) == "DROP_IMPACT")
        if is_drop or is_drop_impact_scene:
            flare = 0.90 * (drop_progress if drop_progress > 0.0 else 1.0)
            np.maximum(self.vals, flare, out=self.vals)
        np.clip(self.vals, 0.0, 1.0, out=self.vals)

        # 6. Boundary Strike Real-Beat Impact (MODE_RULES Rule 2)
        # On verified acoustic hits or drop impacts, ignite a sharp boundary spark
        is_beat = getattr(self.listener, "is_beat", False)
        mood = self.mood_colors
        if (is_beat and is_real and (confidence > 0.4 or is_locked)) or is_drop:
            strike_idx = 0 if cursor_pos < (max_idx * 0.5) else int(max_idx)
            self.smooth_segment_vectorized(1.0, strike_idx, strike_idx, mood[3])

        # 7. Vectorized Color Synthesis using GlobalMoodManager mood_colors
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        accent_weight = float(np.clip(0.5 * tension + 0.25 * (tilt + 1.0), 0.0, 1.0))
        m0, m2 = mood[0], mood[2]
        self.beam_color[0] = (1.0 - accent_weight) * float(m0[0]) + accent_weight * float(m2[0])
        self.beam_color[1] = (1.0 - accent_weight) * float(m0[1]) + accent_weight * float(m2[1])
        self.beam_color[2] = (1.0 - accent_weight) * float(m0[2]) + accent_weight * float(m2[2])
        np.multiply(self.vals[:, None], self.beam_color, out=self.target_rgb)

        # 8. Additive blend into the fading segment with crisp punch
        self.smooth_segment_vectorized(0.85, 0, self.nb_of_leds - 1, self.target_rgb)
