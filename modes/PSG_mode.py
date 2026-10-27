"""
PSG (Paris Saint-Germain) Mode
Split-spectrum visualizer featuring opposing bars and a dynamic balance dot.
Balance dot driven by ctx.spectral_tilt with gentle continuous oscillation,
and bar power driven by ctx.energy and self.beat_pulse().
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class PSG_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.maxSize: int = max(1, int(self.nb_of_leds / 3))
        self.dot_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.left_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.right_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.white_dot_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        mood = self.mood_colors

        # 1. Modulate bar power with energy, beat_pulse(), and spectral_tilt
        self.dot_phase = (self.dot_phase + self.dt * 2.2 * self.mood_pace) % (2.0 * math.pi)
        sway = 0.0 if is_silent else 0.22 * math.sin(self.dot_phase) * (1.0 - 0.5 * self.rhythm_lock)
        effective_tilt = float(np.clip(tilt + sway, -1.0, 1.0))

        drive = (0.60 * energy + 0.40 * self.beat_pulse()) * self.mood_pace
        lower_height = int(np.clip(self.maxSize * drive * (1.0 - 0.4 * max(0.0, effective_tilt)), 0, self.maxSize))
        higher_height = int(np.clip(self.maxSize * drive * (1.0 + 0.4 * min(0.0, effective_tilt)), 0, self.maxSize))

        m0, m1 = mood[0], mood[1]
        hi = self.highlight_color
        accent = self.mood_accent
        for c in range(3):
            self.left_color[c] = (1.0 - accent) * float(m0[c]) + accent * float(hi[c])
            self.right_color[c] = (1.0 - accent) * float(m1[c]) + accent * float(hi[c])
        self.white_dot_color[:] = hi

        # 2. Render left bar, middle gap fade, and right bar
        if lower_height >= 0:
            self.smooth_segment_vectorized(0.5, 0, lower_height, self.left_color)

        gap_start = lower_height + 1
        gap_end = self.nb_of_leds - 1 - higher_height - 1
        if gap_end >= gap_start and gap_start < self.nb_of_leds:
            self.fade_to_black_segment_vectorized(0.5, gap_start, gap_end)

        right_start = self.nb_of_leds - 1 - higher_height
        if right_start < self.nb_of_leds:
            self.smooth_segment_vectorized(0.5, right_start, self.nb_of_leds - 1, self.right_color)

        # 3. Balance dot driven by spectral_tilt + continuous sway
        white_dot_pos = int(np.clip((self.nb_of_leds / 2.0) * (1.0 + effective_tilt), 0, self.nb_of_leds - 1))
        self.smooth_segment_vectorized(1.0, white_dot_pos, white_dot_pos, self.white_dot_color)
