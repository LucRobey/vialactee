"""
Middle Bar Mode
A solid colored bar expanding and contracting symmetrically from the strip center.
Width expands continuously with ctx.energy, self.beat_pulse(), and ctx.vertical_center,
nudged smoothly by mood_pace and mood_accent without branching on ctx.scene.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Middle_bar_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        mid = self.nb_of_leds // 2
        if self.nb_of_leds % 2 == 0:
            self.middle_index = [max(0, mid - 1), min(self.nb_of_leds - 1, mid)]
        else:
            self.middle_index = [mid, mid]

        self.max_size: int = int((self.nb_of_leds + 1) / 2)
        self.size: float = 0.0
        self.breath_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch color (ZERO runtime heap allocation)
        self.bar_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        mood = self.mood_colors

        # 1. Continuous width drive from energy, beat_pulse(), and gentle breathing fallback
        self.breath_phase = (self.breath_phase + self.dt * 2.2 * self.mood_pace) % (2.0 * math.pi)
        pulse = self.beat_pulse()
        breath_nudge = 0.0 if is_silent else (1.0 - self.rhythm_lock) * 0.12 * (0.5 + 0.5 * math.sin(self.breath_phase))
        drive = (0.55 * energy + 0.45 * pulse + breath_nudge) * self.mood_pace

        t_scale = self.transition_scale
        target_width = float(self.max_size) * drive * (0.45 + 0.95 * v_center) * t_scale
        self.size = 0.5 * (self.size + target_width)
        s_int = int(np.clip(self.size, 0, self.max_size))

        # 2. Continuous color interpolation from mood_colors + mood_accent warmth
        m0, m1 = mood[0], mood[1]
        hi = self.highlight_color
        accent = self.mood_accent
        inv_acc = 1.0 - accent
        for c in range(3):
            base_c = (1.0 - v_center) * float(m0[c]) + v_center * float(m1[c])
            self.bar_color[c] = inv_acc * base_c + accent * float(hi[c])

        # 3. Render middle bar and fade outer bounds
        start_idx = max(0, int(self.middle_index[0] - max(0, s_int - 1)))
        end_idx = min(self.nb_of_leds - 1, int(self.middle_index[1] + max(0, s_int - 1)))

        self.smooth_segment_vectorized(0.7, start_idx, end_idx, self.bar_color)
        fade_out = float(np.clip(0.5 / max(0.5, self.mood_trail), 0.1, 0.9))
        if start_idx > 0:
            self.fade_to_black_segment_vectorized(fade_out, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(fade_out, end_idx + 1, self.nb_of_leds - 1)
