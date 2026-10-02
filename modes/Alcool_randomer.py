"""
Alcool Randomer Mode
An arcade-style roulette wheel animation for shot-selection games.
Pulses with ctx.energy and GlobalMoodManager mood_colors when idle.
Celebrates winning selection with a DROP_IMPACT shockwave flare.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import time
import random


class Alcool_randomer(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.begining_speed: float = float(infos.get("shot_base_speed", max(1.0, self.nb_of_leds / 40.0)))
        self.end_of_phase_one_speed: float = float(infos.get("shot_max_speed", 4.0 * self.begining_speed))
        self.fade_to_black_ratio: float = float(infos.get("shot_fade_ratio", 0.40))

        self.activated: bool = False
        self.hasEnded: bool = False
        self.pos_int: int = self.nb_of_leds // 2
        self.pos_float: float = float(self.pos_int)
        self.last_pos_int: int = self.pos_int
        self.speed: float = 0.0
        self.direction: int = 1
        self.phase: int = 0

        # Celebration flare state
        self.flare_active: bool = False
        self.flare_radius: float = 0.0
        self.flare_amp: float = 0.0
        self.flare_center: float = float(self.pos_int)

        # Pre-allocated scratch buffers (ZERO runtime heap allocation)
        self.idle_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.head_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.flare_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.led_coords: np.ndarray = np.arange(self.nb_of_leds, dtype=np.float64)
        self.flare_dists: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.flare_intensity: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.flare_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        phase_beat = float(getattr(self.listener, "beat_phase", 0.0))
        mood = self.mood_colors

        self.fade_to_black(self.fade_to_black_ratio)

        # 1. Active Roulette Animation
        if self.activated:
            self.check_phase()
            if self.phase == 1:
                prog = float(self.new_time - self.starting_time) / max(0.001, self.first_phase_duration)
                self.speed = self.begining_speed + prog * (self.end_of_phase_one_speed - self.begining_speed)
            elif self.phase == 2:
                pass
            elif self.phase == 3:
                denom = max(0.001, self.third_phase_end_time - self.second_phase_end_time)
                self.speed = self.end_of_phase_one_speed * (1.0 - (float(self.new_time - self.second_phase_end_time) / denom))
            elif self.phase in (4, 5):
                self.speed = 0.0
            elif self.phase == 6:
                self.speed = 0.0
                self.activated = False
                self.hasEnded = True
                # Trigger winning shockwave celebration
                self.flare_active = True
                self.flare_radius = 0.0
                self.flare_amp = 1.0
                self.flare_center = float(self.pos_int)

            self.moove_ball()
            self.color_head(mood)

        # 2. Idle State: Pulse with ctx.energy and GlobalMoodManager mood_colors
        elif not self.flare_active:
            sine_pulse = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase_beat))
            glow = (0.06 + 0.20 * energy) * (0.6 + 0.4 * sine_pulse)
            m0 = mood[0]
            self.idle_color[0] = float(m0[0]) * glow
            self.idle_color[1] = float(m0[1]) * glow
            self.idle_color[2] = float(m0[2]) * glow
            self.smooth_segment_vectorized(0.3, 0, self.nb_of_leds - 1, self.idle_color)

        # 3. Winning Celebration: DROP_IMPACT shockwave flare
        if self.flare_active:
            self.flare_radius += (float(self.nb_of_leds) * 0.9) * dt
            self.flare_amp *= (1.0 - 0.045 * fps_ratio)

            if self.flare_amp < 0.02:
                self.flare_active = False
            else:
                two_w_sq = 8.0
                np.subtract(self.led_coords, self.flare_center, out=self.flare_dists)
                np.abs(self.flare_dists, out=self.flare_dists)
                np.subtract(self.flare_dists, self.flare_radius, out=self.flare_dists)
                np.square(self.flare_dists, out=self.flare_dists)
                np.divide(-self.flare_dists, two_w_sq, out=self.flare_intensity)
                np.exp(self.flare_intensity, out=self.flare_intensity)
                self.flare_intensity *= self.flare_amp

                m3, m2 = mood[3], mood[2]
                self.flare_color[0] = 0.75 * float(m3[0]) + 0.25 * float(m2[0])
                self.flare_color[1] = 0.75 * float(m3[1]) + 0.25 * float(m2[1])
                self.flare_color[2] = 0.75 * float(m3[2]) + 0.25 * float(m2[2])
                np.multiply(self.flare_intensity[:, None], self.flare_color, out=self.flare_rgb)
                self.smooth_segment_vectorized(0.85, 0, self.nb_of_leds - 1, self.flare_rgb)

                # Keep winning bead brightly illuminated
                self.smooth_segment_vectorized(1.0, self.pos_int, self.pos_int, mood[3])

    def activate(self) -> None:
        self.activated = True
        self.hasEnded = False
        self.flare_active = False
        self.time_to_spin = random.randint(self.infos.get("shot_min_spin", 15), self.infos.get("shot_max_spin", 20))
        self.direction = -1 if random.randint(0, 1) == 0 else 1
        self.speed = self.begining_speed
        self.last_moove = 0.0

        self.pos_int = self.nb_of_leds // 2
        self.pos_float = float(self.pos_int)
        self.last_pos_int = self.pos_int

        self.first_phase_duration = random.randint(2, max(2, int(0.33 * self.time_to_spin)))
        self.second_phase_duration = random.randint(2, max(2, int(0.33 * self.time_to_spin)))
        self.third_phase_duration = self.time_to_spin - self.first_phase_duration - self.second_phase_duration
        self.fourth_phase_duration = 1

        self.phase = 1
        self.starting_time = time.time()
        self.new_time = self.starting_time

        self.first_phase_end_time = self.starting_time + self.first_phase_duration
        self.second_phase_end_time = self.first_phase_end_time + self.second_phase_duration
        self.third_phase_end_time = self.second_phase_end_time + self.third_phase_duration
        self.fourth_phase_end_time = self.third_phase_end_time + self.fourth_phase_duration

    def check_phase(self) -> None:
        self.new_time = time.time()
        if self.new_time > self.first_phase_end_time:
            if self.new_time > self.second_phase_end_time:
                if self.new_time > self.third_phase_end_time:
                    if self.new_time > self.fourth_phase_end_time:
                        self.phase = 5
                    else:
                        self.phase = 4
                        if self.last_moove == 0.0:
                            self.last_moove = random.uniform(-5.0, 5.0)
                else:
                    self.phase = 3
            else:
                self.phase = 2

    def moove_ball(self) -> None:
        self.last_pos_int = self.pos_int
        self.pos_float += self.speed * self.direction
        if self.pos_float >= self.nb_of_leds:
            self.pos_float = float(self.nb_of_leds - 1)
            self.direction *= -1
        if self.pos_float < 0:
            self.pos_float = 0.0
            self.direction *= -1
        self.pos_int = int(self.pos_float)

        if self.phase == 5:
            self.pos_float += self.last_moove
            self.pos_int = int(self.pos_float)
            self.last_moove = 0.0

            if self.pos_int > self.nb_of_leds - 1:
                self.pos_int = self.nb_of_leds - 1
            if self.pos_int < 0:
                self.pos_int = 0
            self.phase = 6

    def color_head(self, mood: np.ndarray) -> None:
        start = min(self.pos_int, self.last_pos_int)
        end = max(self.pos_int, self.last_pos_int)
        self.head_color[:] = mood[3]
        self.smooth_segment_vectorized(1.0, start, end, self.head_color)
