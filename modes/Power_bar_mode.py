"""
Power Bar Mode
Classic audio VU peak meter designed for vertical or linear segments.
Scales peak gravity with fps_ratio = dt * 60.0. Drives height with ctx.energy.
Tints gradient with ctx.spectral_tilt and active GlobalMoodManager mood_colors.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Power_bar_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.power_height: float = 0.0
        self.white_dot_height: float = 0.0
        self.white_speed: float = float(self.nb_of_leds) / 25.0

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.spatial_coords: np.ndarray = np.linspace(0.0, 1.0, max(1, self.nb_of_leds))[:, None]
        self.bar_colors: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.dot_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.peak_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        mood = self.mood_colors

        # 1. Drive height with ctx.energy
        target_height = energy * float(self.nb_of_leds - 1)
        self.power_height = 0.5 * (self.power_height + target_height)
        self.power_height = float(np.clip(self.power_height, 0.0, self.nb_of_leds - 1))

        # 2. Scale peak gravity with fps_ratio = dt * 60.0
        if self.power_height >= self.white_dot_height:
            self.white_dot_height = min(float(self.nb_of_leds - 1), self.power_height + 1.0)
        else:
            self.white_dot_height -= self.white_speed * fps_ratio
            if self.white_dot_height < 0.0:
                self.white_dot_height = 0.0

        # 3. Tint gradient with ctx.spectral_tilt and mood_colors
        tilt_factor = float(np.clip((tilt + 1.0) * 0.5, 0.0, 1.0))
        m0, m1, m2 = mood[0], mood[1], mood[2]
        for c in range(3):
            self.peak_color[c] = (1.0 - tilt_factor) * float(m1[c]) + tilt_factor * float(m2[c])
            self.bar_colors[:, c] = (1.0 - self.spatial_coords[:, 0]) * float(m0[c]) + self.spatial_coords[:, 0] * self.peak_color[c]
        self.dot_color[:] = mood[3]

        # 4. Render active bar and peak hold dot
        p_int = int(self.power_height)
        if p_int >= 0:
            self.smooth_segment_vectorized(0.65, 0, p_int, self.bar_colors[:p_int + 1])

        dot_idx = int(np.clip(self.white_dot_height, 0, self.nb_of_leds - 1))
        self.smooth_segment_vectorized(0.85, dot_idx, dot_idx, self.dot_color)

        unlit_start = max(p_int + 1, dot_idx + 1)
        if unlit_start < self.nb_of_leds:
            self.fade_to_black_segment_vectorized(0.40, unlit_start, self.nb_of_leds - 1)
