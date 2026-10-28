"""
Opposite Sides Mode
Dual complementary audio-reactive bars advancing toward each other across a central equilibrium zone.
Balance point driven by ctx.spectral_tilt with gentle continuous sway, and bar depths scaled by
ctx.energy and self.beat_pulse(). Harmonized with mood_colors and mood_modifiers.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Opposite_sides_mode(Mode.Mode):
    """Opposing low-frequency vs high-frequency bars advancing toward a central equilibrium zone.

    Lead: spectrum (low vs high balance). Secondary: transient (frontier flash on drop_hit). Macro: color, tension.
    """
    LEAD = "spectrum"
    SECONDARY = ("transient",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle_len: int = max(2, int(self.nb_of_leds / 4))
        self.maxSize: int = max(1, int(self.nb_of_leds / 3))
        self.sway_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.bass_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.high_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.gradient_buffer: np.ndarray = np.zeros((self.middle_len, 3), dtype=np.float64)
        self.t_coords: np.ndarray = np.linspace(0.0, 1.0, self.middle_len)[:, None]

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

        # 1. Balance point driven by spectral_tilt + subtle continuous sway when beat is lost
        self.sway_phase = (self.sway_phase + self.dt * 2.0 * self.mood_pace) % (2.0 * math.pi)
        sway = 0.0 if is_silent else 0.25 * math.sin(self.sway_phase) * (1.0 - 0.5 * self.rhythm_lock)
        effective_tilt = float(np.clip(tilt + sway, -1.0, 1.0))

        nominal_center = self.nb_of_leds / 2.0
        center_shift = effective_tilt * (self.nb_of_leds * 0.16)
        center_pos = int(np.clip(nominal_center + center_shift, 0, self.nb_of_leds - 1))

        half_mid = self.middle_len // 2
        mid_start = max(0, center_pos - half_mid)
        mid_end = min(self.nb_of_leds - 1, mid_start + self.middle_len - 1)
        actual_mid_len = mid_end - mid_start + 1

        # 2. Colors from mood_colors gently warmed by mood_accent
        m0, m1 = mood[0], mood[1]
        hi = self.highlight_color
        accent = self.mood_accent
        for c in range(3):
            self.bass_color[c] = (1.0 - accent) * float(m0[c]) + accent * float(hi[c])
            self.high_color[c] = (1.0 - accent) * float(m1[c]) + accent * float(hi[c])

        t = self.t_coords[:actual_mid_len, 0]
        for c in range(3):
            self.gradient_buffer[:actual_mid_len, c] = (1.0 - t) * self.bass_color[c] + t * self.high_color[c]
        self.smooth_segment_vectorized(0.5, mid_start, mid_end, self.gradient_buffer[:actual_mid_len])

        # 3. Bar depths scaled by energy and beat_pulse()
        drive = (0.60 * energy + 0.40 * self.beat_pulse()) * self.mood_pace
        lower_height = int(np.clip(self.maxSize * drive * (1.0 - 0.4 * max(0.0, effective_tilt)), 0, self.maxSize))
        higher_height = int(np.clip(self.maxSize * drive * (1.0 + 0.4 * min(0.0, effective_tilt)), 0, self.maxSize))

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
