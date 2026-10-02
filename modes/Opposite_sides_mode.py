"""
Opposite Sides Mode
Dual complementary audio-reactive bars advancing toward each other across a central gap.
Strip all per-frame logger.debug calls and pre-allocate arrays in __init__.
Balance point driven directly by ctx.spectral_tilt [-1.0, 1.0] and bar depths scaled by ctx.energy.
Harmonized with GlobalMoodManager mood_colors.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Opposite_sides_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle_len: int = max(2, int(self.nb_of_leds / 4))
        self.maxSize: int = max(1, int(self.nb_of_leds / 3))

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.bass_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.high_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.gradient_buffer: np.ndarray = np.zeros((self.middle_len, 3), dtype=np.float64)
        self.t_coords: np.ndarray = np.linspace(0.0, 1.0, self.middle_len)[:, None]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        mood = self.mood_colors

        # 1. Balance point driven directly by ctx.spectral_tilt [-1.0, 1.0]
        nominal_center = self.nb_of_leds / 2.0
        center_shift = tilt * (self.nb_of_leds * 0.15)
        center_pos = int(np.clip(nominal_center + center_shift, 0, self.nb_of_leds - 1))

        half_mid = self.middle_len // 2
        mid_start = max(0, center_pos - half_mid)
        mid_end = min(self.nb_of_leds - 1, mid_start + self.middle_len - 1)
        actual_mid_len = mid_end - mid_start + 1

        # 2. Colors from mood_colors
        self.bass_color[:] = mood[0]
        self.high_color[:] = mood[1]

        # Draw center equilibrium gradient
        m0, m1 = mood[0], mood[1]
        t = self.t_coords[:actual_mid_len, 0]
        for c in range(3):
            self.gradient_buffer[:actual_mid_len, c] = (1.0 - t) * float(m0[c]) + t * float(m1[c])
        self.smooth_segment_vectorized(0.5, mid_start, mid_end, self.gradient_buffer[:actual_mid_len])

        # 3. Bar depths scaled by ctx.energy
        lower_height = int(np.clip(self.maxSize * energy * (1.0 - 0.4 * max(0.0, tilt)), 0, self.maxSize))
        higher_height = int(np.clip(self.maxSize * energy * (1.0 + 0.4 * min(0.0, tilt)), 0, self.maxSize))

        bass_start = max(0, mid_start - 1 - lower_height)
        bass_end = max(0, mid_start - 1)
        if bass_end >= bass_start and mid_start > 0:
            self.smooth_segment_vectorized(0.5, bass_start, bass_end, self.bass_color)
        if bass_start > 0:
            self.fade_to_black_segment_vectorized(0.5, 0, bass_start - 1)

        treble_start = min(self.nb_of_leds - 1, mid_end + 1)
        treble_end = min(self.nb_of_leds - 1, mid_end + 1 + higher_height)
        if treble_end >= treble_start and mid_end < self.nb_of_leds - 1:
            self.smooth_segment_vectorized(0.5, treble_start, treble_end, self.high_color)
        if treble_end < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(0.5, treble_end + 1, self.nb_of_leds - 1)