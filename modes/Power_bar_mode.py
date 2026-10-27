"""
Power Bar Mode
Classic audio VU peak meter designed for vertical or linear segments.
Scales peak gravity with fps_ratio and mood_pace. Drives height continuously with
ctx.energy and self.beat_pulse(), tinting the gradient with ctx.spectral_tilt and mood_accent.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Power_bar_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.power_height: float = 0.0
        self.white_dot_height: float = 0.0
        self.white_speed: float = float(self.nb_of_leds) / 25.0
        self.flutter_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.spatial_coords: np.ndarray = np.linspace(0.0, 1.0, max(1, self.nb_of_leds))[:, None]
        self.bar_colors: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.dot_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.peak_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        fps_ratio = self.fps_ratio
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        mood = self.mood_colors

        # 1. Drive height with energy, beat_pulse(), drop_decay, and subtle VU flutter when beat is lost
        self.flutter_phase = (self.flutter_phase + self.dt * 3.2 * self.mood_pace) % (2.0 * math.pi)
        if is_silent:
            drive = 0.0
        else:
            flutter = (1.0 - self.rhythm_lock) * 0.08 * math.sin(self.flutter_phase)
            drive = float(np.clip((0.60 * energy + 0.40 * self.beat_pulse() + 0.20 * self.drop_decay + flutter) * self.mood_pace, 0.0, 1.0))
        target_height = drive * float(self.nb_of_leds - 1) * self.transition_scale
        self.power_height = 0.5 * (self.power_height + target_height)
        self.power_height = float(np.clip(self.power_height, 0.0, self.nb_of_leds - 1))

        # 2. Scale peak gravity with fps_ratio and mood_pace
        if self.power_height >= self.white_dot_height:
            self.white_dot_height = min(float(self.nb_of_leds - 1), self.power_height + 1.0)
        else:
            self.white_dot_height -= (self.white_speed * fps_ratio * self.mood_pace) / max(0.5, self.mood_trail)
            if self.white_dot_height < 0.0:
                self.white_dot_height = 0.0

        if is_silent and self.power_height < 0.5 and self.white_dot_height < 0.5:
            self.fade_to_black_segment_vectorized(0.40, 0, self.nb_of_leds - 1)
            return

        # 3. Tint gradient with ctx.spectral_tilt, mood_colors, and mood_accent
        tilt_factor = float(np.clip((tilt + 1.0) * 0.5, 0.0, 1.0))
        m0, m1, m2 = mood[0], mood[1], mood[2]
        hi = self.highlight_color
        accent = self.mood_accent
        for c in range(3):
            base_peak = (1.0 - tilt_factor) * float(m1[c]) + tilt_factor * float(m2[c])
            self.peak_color[c] = (1.0 - accent) * base_peak + accent * float(hi[c])
            self.bar_colors[:, c] = (1.0 - self.spatial_coords[:, 0]) * float(m0[c]) + self.spatial_coords[:, 0] * self.peak_color[c]
        self.dot_color[:] = hi

        # 4. Render active bar, fade unlit region above bar, then paint peak hold dot
        p_int = int(self.power_height)
        if p_int >= 0:
            self.smooth_segment_vectorized(0.65, 0, p_int, self.bar_colors[:p_int + 1])

        if p_int + 1 < self.nb_of_leds:
            self.fade_to_black_segment_vectorized(0.40, p_int + 1, self.nb_of_leds - 1)

        dot_idx = int(np.clip(self.white_dot_height, 0, self.nb_of_leds - 1))
        self.smooth_segment_vectorized(0.85, dot_idx, dot_idx, self.dot_color)
