"""
Barycentric Rainbow Mode
Displays a symmetrical rainbow gradient mirrored outward from the strip's center.
Driven continuously by ctx.vertical_center, ctx.energy, and self.beat_pulse()
with subtle hue drift so it stays fluid even when beat tracking is lost.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Bary_rainbow_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        mid = self.nb_of_leds // 2
        if self.nb_of_leds % 2 == 0:
            self.middle_index = [max(0, mid - 1), min(self.nb_of_leds - 1, mid)]
        else:
            self.middle_index = [mid, mid]

        self.hue_drift: float = self.segment_phase_offset

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.int32)
        self.hues: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        left_len = self.middle_index[0]
        self.left_hues_base: np.ndarray = np.arange(left_len, dtype=np.float64) / max(1.0, float(left_len))
        self.left_hues: np.ndarray = self.hues[:left_len]

        right_len = max(0, self.nb_of_leds - (self.middle_index[1] + 1))
        if right_len > 0:
            self.right_led_indices_ratio: Optional[np.ndarray] = np.arange(1, right_len + 1, dtype=np.float64) / max(1.0, float(right_len))
            self.right_hues: Optional[np.ndarray] = self.hues[self.middle_index[1] + 1:self.nb_of_leds]
        else:
            self.right_led_indices_ratio = None
            self.right_hues = None

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        # 1. Fade to black when ctx.is_silent
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        # 2. Continuous center hue from spectral vertical_center + gentle drift
        self.hue_drift = (self.hue_drift + self.dt * 0.025 * self.mood_pace) % 1.0
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        drift_nudge = 0.06 * np.sin(2.0 * np.pi * self.hue_drift)
        middle_hue = float(np.clip(v_center * 0.84 + drift_nudge, 0.02, 0.84))

        # 3. Modulate brightness and saturation with ctx.energy and beat_pulse()
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        pulse = self.beat_pulse(2.0)
        drive = 0.55 * energy + 0.45 * pulse
        val = float(np.clip(0.20 + 0.80 * drive, 0.0, 1.0))
        sat = float(np.clip(0.55 + 0.45 * energy - 0.20 * self.mood_accent, 0.35, 1.0))

        # 4. Vectorize left, center, and right hues in a single contiguous buffer
        if self.middle_index[0] > 0:
            np.multiply(self.left_hues_base, middle_hue, out=self.left_hues)
        if self.middle_index[0] < self.nb_of_leds:
            self.hues[self.middle_index[0]] = middle_hue
        if self.middle_index[1] < self.nb_of_leds:
            self.hues[self.middle_index[1]] = middle_hue
        if self.right_hues is not None and self.right_led_indices_ratio is not None:
            np.multiply(self.right_led_indices_ratio, 0.85 - middle_hue, out=self.right_hues)
            np.add(self.right_hues, middle_hue, out=self.right_hues)

        RGB_HSV.fromHSV_toRGB_vectorized(self.hues, sat, val, out=self.target_rgb)
        self.smooth_vectorized(self.alpha(14.0), self.target_rgb)
