"""
PSG (Paris Saint-Germain) Mode
Split-spectrum visualizer featuring club colors and a dynamic balance dot.
Stripped of per-frame logging. White balance dot driven directly by ctx.spectral_tilt.
Modulates bar power with ctx.energy and harmonized with GlobalMoodManager mood_colors.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class PSG_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.maxSize: int = max(1, int(self.nb_of_leds / 3))

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.left_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.right_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.white_dot_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        mood = self.mood_colors

        # 1. Modulate bar power with ctx.energy and spectral_tilt
        lower_height = int(np.clip(self.maxSize * energy * (1.0 - 0.4 * max(0.0, tilt)), 0, self.maxSize))
        higher_height = int(np.clip(self.maxSize * energy * (1.0 + 0.4 * min(0.0, tilt)), 0, self.maxSize))

        self.left_color[:] = mood[0]
        self.right_color[:] = mood[1]
        self.white_dot_color[:] = mood[3]

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

        # 3. White balance dot driven directly by ctx.spectral_tilt [-1.0, 1.0]
        white_dot_pos = int(np.clip((self.nb_of_leds / 2.0) * (1.0 + tilt), 0, self.nb_of_leds - 1))
        self.smooth_segment_vectorized(1.0, white_dot_pos, white_dot_pos, self.white_dot_color)