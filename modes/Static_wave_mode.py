"""
Static Wave Mode
Central pulsing color bar driven by beat_phase ADSR envelope when locked.
Tightens boundaries with ctx.tension and maps colors to GlobalMoodManager mood_colors.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Static_wave_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle: int = self.nb_of_leds // 2
        self.max_size: float = max(1.0, (self.nb_of_leds / 2.0) - 1.0)
        self.real_size: float = self.nb_of_leds / 4.0
        self.size_int: float = float(int(self.real_size + 1))

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.inner_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.cap_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        is_locked = bool(ctx.is_locked if ctx is not None else getattr(self.listener, "beat_confidence", 0.0) >= 0.5)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tension = float(ctx.tension if ctx is not None else 0.0)
        mood = self.mood_colors

        # 1. Drive pulse ADSR envelope with beat_phase when is_locked
        if is_locked:
            decay = (1.0 - phase) ** (1.5 + 1.5 * tension)
            pulse_power = 0.35 * energy + 0.65 * (energy * decay)
        else:
            pulse_power = energy

        bands = getattr(self.listener, "_delayed_asserved_fft_band", None)
        if bands is not None and len(bands) >= 2:
            bass_val = float(bands[0] + bands[1]) * 0.5
            combined_drive = float(np.clip(0.5 * pulse_power + 0.5 * bass_val, 0.0, 1.0))
        else:
            combined_drive = float(np.clip(pulse_power, 0.0, 1.0))

        # 2. Tighten boundaries with ctx.tension
        tightness = max(0.25, 1.0 - 0.45 * tension)
        target_len = self.max_size * combined_drive * tightness
        self.real_size = 0.5 * (self.real_size + target_len)
        if self.real_size >= self.max_size:
            self.real_size = self.max_size - 1.0

        if self.real_size > self.size_int:
            self.size_int = float(int(self.real_size + 1))
        if self.real_size < self.size_int - 1.0:
            self.size_int = max(0.0, self.size_int - 0.2)

        current_len = int(np.clip(self.real_size, 0, self.max_size))
        start_idx = max(0, self.middle - current_len)
        end_idx = min(self.nb_of_leds - 1, self.middle + current_len)

        # 3. Map colors to self.mood_colors
        m0, m1, m3 = mood[0], mood[1], mood[3]
        for c in range(3):
            self.inner_color[c] = ((1.0 - tension) * float(m0[c]) + tension * float(m1[c])) * combined_drive
            self.cap_color[c] = float(m3[c]) * combined_drive

        self.smooth_segment_vectorized(0.6, start_idx, end_idx, self.inner_color)

        boundary_p1 = min(self.nb_of_leds - 1, self.middle + int(self.size_int))
        boundary_p2 = max(0, self.middle - int(self.size_int))
        self.smooth_segment_vectorized(0.6, boundary_p1, boundary_p1, self.cap_color)
        self.smooth_segment_vectorized(0.6, boundary_p2, boundary_p2, self.cap_color)

        if boundary_p2 > 0:
            self.fade_to_black_segment_vectorized(0.5, 0, boundary_p2 - 1)
        if boundary_p1 < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(0.5, boundary_p1 + 1, self.nb_of_leds - 1)
