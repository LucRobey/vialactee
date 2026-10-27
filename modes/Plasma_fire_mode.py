"""
Plasma Fire Mode
Simulates a rising column of fiery plasma optimized for vertical chandelier segments.
Flame height driven continuously by ctx.energy, self.beat_pulse(), and organic thermal flicker
without branching on ctx.scene. Temperature gradient warms smoothly with ctx.tension and mood_accent.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


class Plasma_fire_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.fade_ratio: float = float(infos.get("fire_fade_ratio", 0.30))
        self.height_multiplier: float = float(infos.get("fire_height_multiplier", 1.20))
        self.flicker_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.spatial_coords: np.ndarray = np.linspace(0.0, 1.0, max(1, self.nb_of_leds))[:, None]
        self.target_colors: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.tip_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tension = float(ctx.tension if ctx is not None else 0.0)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        mood = self.mood_colors

        # 1. Continuous flame height from energy, beat_pulse(), drop_decay, and subtle thermal flicker
        self.flicker_phase = (self.flicker_phase + self.dt * 4.5 * self.mood_pace) % (2.0 * math.pi)
        if is_silent:
            drive = 0.0
        else:
            flicker = 0.08 * math.sin(self.flicker_phase)
            drive = (0.60 * energy + 0.40 * self.beat_pulse() + 0.20 * self.drop_decay + flicker) * self.mood_pace
        t_scale = self.transition_scale
        fire_height = int(np.clip(drive * self.height_multiplier * self.nb_of_leds * t_scale, 0, self.nb_of_leds))

        # 2. Temperature gradient shifts toward highlight_color with tension, drop_decay, and mood_accent
        m1 = mood[1]
        hi = self.highlight_color
        tip_warmth = min(1.0, 0.55 * tension + 0.20 * self.drop_decay + self.mood_accent)
        for c in range(3):
            self.tip_color[c] = (1.0 - tip_warmth) * float(m1[c]) + tip_warmth * float(hi[c])

        if fire_height > 0:
            t = self.spatial_coords[:fire_height, 0]
            m0 = mood[0]
            for c in range(3):
                self.target_colors[:fire_height, c] = (1.0 - t) * float(m0[c]) + t * self.tip_color[c]

            np.clip(self.target_colors[:fire_height], 0.0, 255.0, out=self.target_colors[:fire_height])
            self.smooth_segment_vectorized(0.80, 0, fire_height - 1, self.target_colors[:fire_height])

        # 3. Fade unlit LEDs above the current flame column (scaled by mood_trail)
        if fire_height < self.nb_of_leds:
            effective_fade = float(np.clip(self.fade_ratio / max(0.5, self.mood_trail), 0.05, 0.90))
            self.fade_to_black_segment_vectorized(effective_fade, fire_height, self.nb_of_leds - 1)
