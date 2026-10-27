"""
Magnetic Ball Mode
Physics-based simulation of an elastic ball with mass, friction, and a center gravity well.
Blends rhythmic kicks on verified beats with a continuous spectral/energy orbital drive when
the beat tracker is lost, and never pins the ball to the wall on DROP_IMPACT.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
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
        self.orbit_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch color vector (ZERO runtime heap allocation)
        self.ball_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        fps_ratio = self.fps_ratio
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tension = float(ctx.tension if ctx is not None else 0.0)
        mood = self.mood_colors

        t_scale = self.transition_scale
        lock = self.rhythm_lock

        # 1. Rhythmic kicks on verified beats + continuous orbital force when flywheel is lost
        if (not is_silent) and (is_real or self.drop_hit):
            kick_dir = 1.0 if (self.ball_pos <= self.gravity_well) else -1.0
            kick_force = energy * (self.nb_of_leds * 0.18) * self.mood_pace * t_scale
            self.ball_speed += kick_dir * kick_force

        if not is_silent:
            self.orbit_phase = (self.orbit_phase + self.dt * 3.0 * self.mood_pace) % (2.0 * math.pi)
            continuous_force = (1.0 - 0.7 * lock) * energy * (self.nb_of_leds * 0.025) * math.sin(self.orbit_phase) * t_scale
            self.ball_speed += continuous_force * fps_ratio

        # 2. Spring stiffness scales with ctx.tension and mood_pace
        stiffness = (0.04 + 0.14 * tension + 0.20 * self._exit_progress) * fps_ratio * self.mood_pace
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

        trail_fade = float(np.clip(0.35 / max(0.5, self.mood_trail), 0.08, 0.75))
        if is_silent:
            self.fade_to_black_segment_vectorized(trail_fade, 0, self.nb_of_leds - 1)
            return

        # 3. Continuous color blend from mood_colors + mood_accent warmth
        m0, m2 = mood[0], mood[2]
        hi = self.highlight_color
        accent = self.mood_accent
        t_w = float(np.clip(tension, 0.0, 1.0))
        for c in range(3):
            base_c = (1.0 - t_w) * float(m0[c]) + t_w * float(m2[c])
            self.ball_color[c] = (1.0 - accent) * base_c + accent * float(hi[c])

        # 4. Render ball and motion blur tails (scaled by mood_trail)
        center_idx = int(self.ball_pos)
        dynamic_size = max(1, int((self.ball_size + (energy * 4.0)) * t_scale))
        start_idx = max(0, center_idx - dynamic_size)
        end_idx = min(self.nb_of_leds - 1, center_idx + dynamic_size)

        self.smooth_segment_vectorized(0.75, start_idx, end_idx, self.ball_color)

        trail_fade = float(np.clip(0.35 / max(0.5, self.mood_trail), 0.08, 0.75))
        if start_idx > 0:
            self.fade_to_black_segment_vectorized(trail_fade, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(trail_fade, end_idx + 1, self.nb_of_leds - 1)
