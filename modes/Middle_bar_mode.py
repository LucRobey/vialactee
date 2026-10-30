"""
Middle Bar Mode
A solid colored bar expanding and contracting symmetrically from the strip center.
Bar length follows self.beat_pulse() alone (which already blends the rhythm-locked pump with acoustic
energy when beat_trust is low, so the mode stays alive without the flywheel). The outer caps are lit
by bass energy (spectrum), while color, trail and tension modulate as macro. No ctx.scene branching.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Middle_bar_mode(Mode.Mode):
    """Beat-pumped bar expanding symmetrically from the center.

    Lead: beat (bar length). Secondary: spectrum (bass lights the caps). Macro: trail, color, tension.
    """
    LEAD = "beat"
    SECONDARY = ("spectrum",)

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
        self.cap_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        tension = float(ctx.tension if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        mood = self.mood_colors

        # 1. Bar length driven by beat_pulse() alone (+ tension macro and a gentle unlocked breathing nudge)
        self.breath_phase = (self.breath_phase + self.dt * 2.2 * self.mood_pace) % (2.0 * math.pi)
        if is_silent:
            drive = 0.0
        else:
            pulse = self.beat_pulse()
            breath_nudge = (1.0 - self.rhythm_lock) * 0.12 * (0.5 + 0.5 * math.sin(self.breath_phase))
            drive = (0.20 + 0.80 * pulse * (1.0 + 0.25 * tension) + breath_nudge) * self.mood_pace

        t_scale = self.transition_scale
        target_width = float(self.max_size) * min(1.0, drive) * t_scale
        self.size = 0.5 * (self.size + target_width)
        if is_silent and self.size < 0.5:
            fade_out = float(np.clip(0.5 / max(0.5, self.mood_trail), 0.1, 0.9))
            self.fade_to_black_segment_vectorized(fade_out, 0, self.nb_of_leds - 1)
            return
        s_int = int(np.clip(self.size, 0, self.max_size))

        # 2. Body color from mood_colors + mood_accent warmth (spectrum only tints it faintly)
        m0, m1 = mood[0], mood[1]
        hi = self.highlight_color
        accent = self.mood_accent
        inv_acc = 1.0 - accent
        for c in range(3):
            base_c = (1.0 - 0.35 * v_center) * float(m0[c]) + 0.35 * v_center * float(m1[c])
            self.bar_color[c] = inv_acc * base_c + accent * float(hi[c])

        # 3. Render middle bar and fade outer bounds
        start_idx = max(0, int(self.middle_index[0] - max(0, s_int - 1)))
        end_idx = min(self.nb_of_leds - 1, int(self.middle_index[1] + max(0, s_int - 1)))

        self.smooth_segment_vectorized(0.7, start_idx, end_idx, self.bar_color)

        # 3b. Secondary (spectrum): bass energy lights the two outer cap LEDs of the bar
        bands = getattr(self.listener, "asserved_fft_band", None)
        bass = 0.0
        if bands is not None and len(bands) >= 2:
            bass = float(np.clip(0.5 * (float(bands[0]) + float(bands[1])), 0.0, 1.0))
        if bass > 0.01 and not is_silent:
            for c in range(3):
                self.cap_color[c] = (1.0 - bass) * self.bar_color[c] + bass * float(hi[c])
            self.smooth_segment_vectorized(0.7, start_idx, min(end_idx, start_idx + 1), self.cap_color)
            self.smooth_segment_vectorized(0.7, max(start_idx, end_idx - 1), end_idx, self.cap_color)
        fade_out = float(np.clip(0.5 / max(0.5, self.mood_trail), 0.1, 0.9))
        if start_idx > 0:
            self.fade_to_black_segment_vectorized(fade_out, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(fade_out, end_idx + 1, self.nb_of_leds - 1)
