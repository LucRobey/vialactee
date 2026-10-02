"""
Flying Ball Mode
A luminous cluster gliding across the strip using spring-damper physics tracking ctx.vertical_center.
Scales ball radius and glow by ctx.energy and settles in the center during silence.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Flying_ball_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.ball_pos: float = float(self.nb_of_leds / 2.0)
        self.ball_vel: float = 0.0

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.indices: np.ndarray = np.arange(self.nb_of_leds, dtype=np.float64)
        self.dists: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.glow_weights: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.ball_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        mood = self.mood_colors

        # 1. Target Position & Silence Settling
        if is_silent:
            target_pos = float(self.nb_of_leds / 2.0)
        else:
            target_pos = v_center * float(self.nb_of_leds - 1)

        # 2. Spring-Damper Physics
        stiffness = 14.0
        damping = 4.5
        accel = stiffness * (target_pos - self.ball_pos) - damping * self.ball_vel
        self.ball_vel += accel * dt
        self.ball_pos += self.ball_vel * dt
        self.ball_pos = float(np.clip(self.ball_pos, 0.0, self.nb_of_leds - 1))

        # 3. Scale Ball Radius and Glow by ctx.energy
        radius = (1.5 + 3.0 * energy) if not is_silent else 1.0
        intensity = (0.25 + 0.75 * energy) if not is_silent else 0.06

        # 4. Vectorized Gaussian Glow calculation
        two_r_sq = 2.0 * (radius ** 2)
        np.subtract(self.indices, self.ball_pos, out=self.dists)
        np.square(self.dists, out=self.dists)
        np.divide(-self.dists, two_r_sq, out=self.glow_weights)
        np.exp(self.glow_weights, out=self.glow_weights)
        self.glow_weights *= intensity

        # 5. Color from mood_colors interpolated by v_center
        m0, m2 = mood[0], mood[2]
        self.ball_color[0] = (1.0 - v_center) * float(m0[0]) + v_center * float(m2[0])
        self.ball_color[1] = (1.0 - v_center) * float(m0[1]) + v_center * float(m2[1])
        self.ball_color[2] = (1.0 - v_center) * float(m0[2]) + v_center * float(m2[2])
        np.multiply(self.glow_weights[:, None], self.ball_color, out=self.target_rgb)
        np.clip(self.target_rgb, 0.0, 255.0, out=self.target_rgb)

        # 6. Smooth blend with motion blur trail
        self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
        self.smooth_segment_vectorized(0.85, 0, self.nb_of_leds - 1, self.target_rgb)
