"""
Plasma Fire Mode
Simulates a rising column of fiery plasma optimized for vertical chandelier segments.
Flame height driven by ctx.energy. Temperature gradient shifts toward white-hot plasma with ctx.tension.
Erupts to 100% on DROP_IMPACT. Harmonized with GlobalMoodManager mood_colors.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Plasma_fire_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.fade_ratio: float = float(infos.get("fire_fade_ratio", 0.30))
        self.height_multiplier: float = float(infos.get("fire_height_multiplier", 1.20))

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
        scene = getattr(ctx, "scene", None)
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"
        mood = self.mood_colors

        # 1. Flame height driven by ctx.energy (Eruption to 100% on DROP_IMPACT)
        if is_drop:
            fire_height = self.nb_of_leds
        else:
            fire_height = int(np.clip(energy * self.height_multiplier * self.nb_of_leds, 0, self.nb_of_leds))

        # 2. Temperature gradient shifts toward white-hot plasma with ctx.tension
        # Tip blends secondary mood[1] into white-hot highlight mood[3]
        m1, m3 = mood[1], mood[3]
        self.tip_color[0] = (1.0 - tension) * float(m1[0]) + tension * float(m3[0])
        self.tip_color[1] = (1.0 - tension) * float(m1[1]) + tension * float(m3[1])
        self.tip_color[2] = (1.0 - tension) * float(m1[2]) + tension * float(m3[2])

        if fire_height > 0:
            t = self.spatial_coords[:fire_height, 0]
            m0 = mood[0]
            for c in range(3):
                self.target_colors[:fire_height, c] = (1.0 - t) * float(m0[c]) + t * self.tip_color[c]

            if is_drop:
                # White-hot plasma flare across the whole column
                for c in range(3):
                    self.target_colors[:fire_height, c] = 0.3 * self.target_colors[:fire_height, c] + 0.7 * float(m3[c])

            np.clip(self.target_colors[:fire_height], 0.0, 255.0, out=self.target_colors[:fire_height])
            self.smooth_segment_vectorized(0.80, 0, fire_height - 1, self.target_colors[:fire_height])

        # 3. Fade unlit LEDs above the current flame column
        if fire_height < self.nb_of_leds:
            self.fade_to_black_segment_vectorized(self.fade_ratio, fire_height, self.nb_of_leds - 1)
