"""
Beat Runner Mode
Dynamic BPM-scaled kinematic laser runner for speaker-time latency and boundary sync.
Sweeps a concentrated luminous bead across the strip locked to beat_phase when confident,
and smoothly crossfades into a continuous tempo-paced sweep when beat tracking is lost.
Never washes out 90% of the strip on DROP_IMPACT. Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


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
                "default": 0.08,
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
        self.free_phase: float = 0.0

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

        # 1. Decay previous frame tails for smooth motion blur (scaled by mood_trail)
        effective_decay = float(np.clip(self.trail_decay / max(0.5, self.mood_trail), 0.03, 0.70))
        self.fade_to_black_segment_vectorized(effective_decay, 0, self.nb_of_leds - 1)

        # 2. Read rhythmic state without scene branching
        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        power = float(ctx.power if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        energy = float(ctx.energy if ctx is not None else power)
        tension = float(ctx.tension if ctx is not None else 0.0)
        is_locked = bool(ctx.is_locked if ctx is not None else (float(getattr(self.listener, "beat_confidence", 0.0)) >= 0.5))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        lock = self.rhythm_lock

        # Advance continuous fallback phase so the runner keeps gliding if beat_phase is stalled
        self.free_phase = (self.free_phase + self.dt * (bpm / 60.0) * 0.65 * self.mood_pace) % 1.0
        effective_phase = lock * phase + (1.0 - lock) * self.free_phase

        # 3. Calculate target cursor position mapped to effective_phase
        max_idx = float(self.nb_of_leds - 1)
        if self.motion_style == "sweep":
            cursor_pos = effective_phase * max_idx
        else:
            harmonic_factor = 0.5 * (1.0 - np.cos(2.0 * np.pi * effective_phase))
            cursor_pos = harmonic_factor * max_idx

        # 4. Confidence-Weighted Beam Width & Fallback (MODE_RULES Rule 1)
        sigma = (self.head_width + (1.0 - lock) * 3.0) * (1.0 - 0.20 * tension)
        two_sigma_sq = 2.0 * (sigma ** 2)

        # 5. Vectorized Gaussian Intensity Calculation
        np.subtract(self.led_indices, cursor_pos, out=self.dist_sq)
        np.square(self.dist_sq, out=self.dist_sq)
        np.divide(-self.dist_sq, two_sigma_sq, out=self.gauss_weights)
        np.exp(self.gauss_weights, out=self.gauss_weights)

        base_intensity = lock * 1.0 + (1.0 - lock) * max(0.25, energy)
        np.multiply(self.gauss_weights, base_intensity, out=self.vals)
        np.clip(self.vals, 0.0, 1.0, out=self.vals)

        # 6. Boundary Strike Real-Beat Impact (1-frame spark only, no 1.5s full-strip washout)
        is_beat = bool(getattr(self.listener, "is_beat", False))
        mood = self.mood_colors
        if (is_beat and is_real and (lock > 0.35 or is_locked)) or self.drop_hit:
            strike_idx = 0 if cursor_pos < (max_idx * 0.5) else int(max_idx)
            self.smooth_segment_vectorized(1.0, strike_idx, strike_idx, self.highlight_color)

        # 7. Vectorized Color Synthesis using mood_colors, base_hue, and mood_accent
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        hue_t = (self.base_hue + 0.35 * tension + 0.20 * (tilt + 1.0) + self.mood_accent) % 1.0
        lut_c = self.palette_lut[int(hue_t * 255.0) & 255]
        accent_weight = float(np.clip(0.45 * tension + 0.20 * (tilt + 1.0) + self.mood_accent, 0.0, 1.0))
        m0 = mood[0]
        for c in range(3):
            self.beam_color[c] = (1.0 - accent_weight) * float(m0[c]) + accent_weight * float(lut_c[c])
        np.multiply(self.vals[:, None], self.beam_color, out=self.target_rgb)

        # 8. Smooth blend into the fading segment
        self.smooth_segment_vectorized(0.85, 0, self.nb_of_leds - 1, self.target_rgb)
