"""
Extending Waves Mode
Subpixel wave propagation driven by dt * speed(bpm, tension).
Wave injection on ctx.is_real_beat. Waves implode inward during BUILDUP and explode outward on DROP_IMPACT.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Extending_waves_mode(Mode.Mode):
    MAX_WAVES: int = 8

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle_idx: int = self.nb_of_leds // 2
        self.half_len: int = self.middle_idx + 1

        # Pre-allocated scratch wave arrays (ZERO runtime heap allocation)
        self.wave_positions: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_velocities: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_amps: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_colors: np.ndarray = np.zeros((self.MAX_WAVES, 3), dtype=np.float64)
        self.wave_active: np.ndarray = np.zeros(self.MAX_WAVES, dtype=bool)
        self.wave_slot: int = 0
        self.wave_count: int = 0
        self.time_since_wave: float = 1.0
        self.wave_width: float = 2.2

        # Coordinate and color buffers
        self.half_coords: np.ndarray = np.arange(self.half_len, dtype=np.float64)
        self.half_dists: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.wave_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.wave_scratch_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)
        self.half_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        mood = self.mood_colors

        tension = float(ctx.tension if ctx is not None else 0.0)
        scene = getattr(ctx, "scene", None)
        is_buildup = bool(scene == "BUILDUP")
        drop_prog = float(getattr(ctx, "drop_progress", 0.0))
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))

        self.time_since_wave += dt

        # 1. Subpixel Wave Propagation Speed
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        base_speed = (float(self.half_len) / frames_per_beat) * fps_ratio * (1.0 + 0.6 * tension)
        if is_drop:
            base_speed *= 2.0

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += self.wave_velocities[w] * base_speed
                self.wave_amps[w] *= (1.0 - 0.035 * fps_ratio)

                # Boundary checking
                if self.wave_velocities[w] > 0 and self.wave_positions[w] >= (self.half_len + 2.0):
                    self.wave_active[w] = False
                elif self.wave_velocities[w] < 0 and self.wave_positions[w] <= -2.0:
                    self.wave_active[w] = False
                elif self.wave_amps[w] < 0.015:
                    self.wave_active[w] = False

        # 2. Wave Injection: Gated on ctx.is_real_beat, Implode in BUILDUP, Explode on DROP_IMPACT
        min_wave_interval = 0.35 * (60.0 / bpm)
        should_trigger = is_drop or (is_real and self.time_since_wave >= min_wave_interval)

        if should_trigger:
            self.time_since_wave = 0.0
            slot = self.wave_slot
            self.wave_slot = (self.wave_slot + 1) % self.MAX_WAVES
            self.wave_active[slot] = True
            self.wave_count += 1

            if is_drop:
                # Explode outward on drop impact
                self.wave_positions[slot] = 0.0
                self.wave_velocities[slot] = 2.0
                self.wave_amps[slot] = 1.0
                self.wave_colors[slot] = mood[3]
            elif is_buildup:
                # Implode inward during buildup
                self.wave_positions[slot] = float(self.half_len)
                self.wave_velocities[slot] = -1.0
                self.wave_amps[slot] = 0.85 + 0.15 * tension
                self.wave_colors[slot] = mood[2]
            else:
                # Normal outward propagation
                self.wave_positions[slot] = 0.0
                self.wave_velocities[slot] = 1.0
                self.wave_amps[slot] = 0.90
                self.wave_colors[slot] = mood[self.wave_count % 3]

        # 3. Synthesize Half-Strip Energy & Colors
        self.half_rgb.fill(0.0)
        two_w_sq = 2.0 * ((self.wave_width * (1.0 - 0.20 * tension)) ** 2)

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                np.square(self.half_dists, out=self.half_dists)
                np.negative(self.half_dists, out=self.wave_profile)
                np.divide(self.wave_profile, two_w_sq, out=self.wave_profile)
                np.exp(self.wave_profile, out=self.wave_profile)
                np.multiply(self.wave_profile, self.wave_amps[w], out=self.wave_profile)
                col = self.wave_colors[w]
                for c in range(3):
                    np.multiply(self.wave_profile, float(col[c]), out=self.wave_scratch_rgb[:, c])
                np.add(self.half_rgb, self.wave_scratch_rgb, out=self.half_rgb)

        np.clip(self.half_rgb, 0.0, 255.0, out=self.half_rgb)

        # 4. Symmetrical Mirroring to Full Segment
        if self.middle_idx > 0:
            left_view = self.half_rgb[1:self.middle_idx + 1][::-1]
            self.smooth_segment_vectorized(0.75, 0, self.middle_idx - 1, left_view)

        self.smooth_segment_vectorized(0.75, self.middle_idx, self.middle_idx, self.half_rgb[0])

        right_len = self.nb_of_leds - (self.middle_idx + 1)
        if right_len > 0:
            right_view = self.half_rgb[1:right_len + 1]
            self.smooth_segment_vectorized(0.75, self.middle_idx + 1, self.nb_of_leds - 1, right_view)
