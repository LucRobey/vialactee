"""
Magnetic Ball Mode
Physics-based simulation of an elastic ball with mass, friction, and a center gravity well.
Kicks gated on ctx.is_real_beat. Spring stiffness scales with ctx.tension.
Explosive release on DROP_IMPACT. Harmonized with GlobalMoodManager mood_colors.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Magnetic_ball_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.ball_pos: float = float(self.nb_of_leds / 2.0)
        self.ball_speed: float = 0.0
        self.ball_size: float = 3.0
        self.friction: float = 0.96
        self.gravity_well: float = float(self.nb_of_leds / 2.0)

        # Pre-allocated scratch color vector (ZERO runtime heap allocation)
        self.ball_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        is_beat = bool(getattr(self.listener, "is_beat", False))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tension = float(ctx.tension if ctx is not None else 0.0)
        scene = getattr(ctx, "scene", None)
        drop_prog = float(getattr(ctx, "drop_progress", 0.0))
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"
        mood = self.mood_colors

        # 1. Gate kicks on ctx.is_real_beat (Rule 2: no coasting phantom kicks)
        if is_real:
            kick_dir = 1.0 if (self.ball_pos <= self.gravity_well) else -1.0
            kick_force = energy * (self.nb_of_leds * 0.18)
            self.ball_speed += kick_dir * kick_force

        # 2. Explosive release on DROP_IMPACT
        if is_drop:
            launch_dir = 1.0 if (self.ball_pos <= self.gravity_well) else -1.0
            self.ball_speed = launch_dir * (self.nb_of_leds * 0.38) * fps_ratio

        # 3. Spring stiffness scales with ctx.tension
        stiffness = (0.04 + 0.16 * tension) * fps_ratio
        dist_to_center = self.gravity_well - self.ball_pos
        self.ball_speed += dist_to_center * stiffness

        # Apply speed and friction
        self.ball_pos += self.ball_speed * fps_ratio
        self.ball_speed *= (self.friction ** fps_ratio)

        # Elastic bounce at segment boundaries
        if self.ball_pos < 0.0:
            self.ball_pos = 0.1
            self.ball_speed = abs(self.ball_speed) * 0.85
        elif self.ball_pos >= self.nb_of_leds:
            self.ball_pos = float(self.nb_of_leds - 1.1)
            self.ball_speed = -abs(self.ball_speed) * 0.85

        # 4. Color from mood_colors
        if is_drop:
            self.ball_color[:] = mood[3]  # Highlight bloom
        elif tension > 0.45:
            self.ball_color[:] = mood[2]  # Accent when tense
        else:
            self.ball_color[:] = mood[0]  # Primary

        # 5. Render ball and motion blur tails
        center_idx = int(self.ball_pos)
        dynamic_size = int(self.ball_size + (energy * 4.0))
        start_idx = max(0, center_idx - dynamic_size)
        end_idx = min(self.nb_of_leds - 1, center_idx + dynamic_size)

        self.smooth_segment_vectorized(0.75, start_idx, end_idx, self.ball_color)

        if start_idx > 0:
            self.fade_to_black_segment_vectorized(0.35, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(0.35, end_idx + 1, self.nb_of_leds - 1)
