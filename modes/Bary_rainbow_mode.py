"""
Barycentric Rainbow Mode
Displays a symmetrical rainbow gradient mirrored outward from the strip's center.
Replaces the python loop with precomputed ctx.vertical_center.
Modulates brightness and saturation with ctx.energy and fades to black in silence.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
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

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        left_len = self.middle_index[0]
        self.left_hues_base: np.ndarray = np.arange(left_len, dtype=np.float64) / max(1.0, float(left_len))
        self.left_hues: np.ndarray = np.zeros(left_len, dtype=np.float64)
        self.target_left: np.ndarray = np.zeros((left_len, 3), dtype=np.int32)

        right_len = max(0, self.nb_of_leds - (self.middle_index[1] + 1))
        if right_len > 0:
            self.right_led_indices_ratio: Optional[np.ndarray] = np.arange(1, right_len + 1, dtype=np.float64) / max(1.0, float(right_len))
            self.right_hues: Optional[np.ndarray] = np.zeros(right_len, dtype=np.float64)
            self.target_right: Optional[np.ndarray] = np.zeros((right_len, 3), dtype=np.int32)
        else:
            self.right_led_indices_ratio = None
            self.right_hues = None
            self.target_right = None

        self.center_rgb: np.ndarray = np.zeros((1, 3), dtype=np.int32)
        self.center_hue_arr: np.ndarray = np.zeros(1, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        # 1. Fade to black when ctx.is_silent
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        # 2. Replace band loop with ctx.vertical_center
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        middle_hue = float(np.clip(v_center * 0.84, 0.0, 0.84))

        # 3. Modulate brightness and saturation with ctx.energy
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        val = float(np.clip(0.20 + 0.80 * energy, 0.0, 1.0))
        sat = float(np.clip(0.50 + 0.50 * energy, 0.0, 1.0))

        # 4. Vectorize left side
        if self.middle_index[0] > 0:
            np.multiply(self.left_hues_base, middle_hue, out=self.left_hues)
            RGB_HSV.fromHSV_toRGB_vectorized(self.left_hues, sat, val, out=self.target_left)
            self.rgb_list[:self.middle_index[0]] = self.target_left

        # 5. Center LEDs
        self.center_hue_arr[0] = middle_hue
        RGB_HSV.fromHSV_toRGB_vectorized(self.center_hue_arr, sat, val, out=self.center_rgb)
        if self.middle_index[0] < self.nb_of_leds:
            self.rgb_list[self.middle_index[0]] = self.center_rgb[0]
        if self.middle_index[1] < self.nb_of_leds:
            self.rgb_list[self.middle_index[1]] = self.center_rgb[0]

        # 6. Vectorize right side
        if self.target_right is not None and self.right_hues is not None and self.right_led_indices_ratio is not None:
            np.multiply(self.right_led_indices_ratio, 0.85 - middle_hue, out=self.right_hues)
            np.add(self.right_hues, middle_hue, out=self.right_hues)
            RGB_HSV.fromHSV_toRGB_vectorized(self.right_hues, sat, val, out=self.target_right)
            self.rgb_list[self.middle_index[1] + 1:self.nb_of_leds] = self.target_right