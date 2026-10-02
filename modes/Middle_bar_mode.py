"""
Middle Bar Mode
A solid colored bar expanding and contracting symmetrically from the strip center.
Width expands proportionally to ctx.energy weighted by ctx.vertical_center.
Contracts during BUILDUP and explodes to maximum width on DROP_IMPACT.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
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

        # Pre-allocated scratch color (ZERO runtime heap allocation)
        self.bar_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        scene = getattr(ctx, "scene", None)
        drop_prog = float(getattr(ctx, "drop_progress", 0.0))
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"
        mood = self.mood_colors

        # 1. Expand width proportionally to ctx.energy (weighted by ctx.vertical_center)
        target_width = float(self.max_size) * energy * (0.4 + 1.2 * v_center)

        # 2. Contract during BUILDUP
        if scene == "BUILDUP":
            contract = max(0.08, 1.0 - 0.85 * drop_prog)
            target_width *= contract

        # 3. Explode on DROP_IMPACT
        if is_drop:
            self.size = float(self.max_size)
        else:
            self.size = 0.5 * (self.size + target_width)
        s_int = int(np.clip(self.size, 0, self.max_size))

        # 4. Color selection from mood_colors
        if is_drop:
            self.bar_color[:] = mood[3]  # Highlight bloom
        elif scene == "BUILDUP":
            self.bar_color[:] = mood[2]  # Accent
        else:
            m0, m1 = mood[0], mood[1]
            self.bar_color[0] = (1.0 - v_center) * float(m0[0]) + v_center * float(m1[0])
            self.bar_color[1] = (1.0 - v_center) * float(m0[1]) + v_center * float(m1[1])
            self.bar_color[2] = (1.0 - v_center) * float(m0[2]) + v_center * float(m1[2])

        # 5. Render middle bar and fade outer bounds
        start_idx = max(0, int(self.middle_index[0] - max(0, s_int - 1)))
        end_idx = min(self.nb_of_leds - 1, int(self.middle_index[1] + max(0, s_int - 1)))

        self.smooth_segment_vectorized(0.7, start_idx, end_idx, self.bar_color)
        if start_idx > 0:
            self.fade_to_black_segment_vectorized(0.5, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(0.5, end_idx + 1, self.nb_of_leds - 1)
