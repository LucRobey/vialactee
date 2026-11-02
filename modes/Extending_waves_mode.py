"""
Extending Waves Mode
Subpixel center-outward wave propagation whose wave spawning (via a continuous level accumulator),
flow speed, wave amplitude, and center bed glow are driven by ctx.energy (LEAD="level").
Decoupled from discrete beat ticks: self.beat_pulse() only tints the wave color and crest shimmer
(SECONDARY=("beat",)). Waves always propagate outward from the center with no scene branching.
Harmonized with the mood sector's mood_colors and mood_modifiers with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Extending_waves_mode(Mode.Mode):
    """Center-outward traveling color waves spawned and propelled by audio energy.

    Lead: level (level accumulator spawns waves; energy sets flow speed, wave amplitude, and bed reach). Secondary: beat (tints wave color and crest shimmer). Macro: color drift, mood_pace, mood_trail.
    """
    LEAD = "level"
    SECONDARY = ("beat",)
    MAX_WAVES: int = 8

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle_idx: int = self.nb_of_leds // 2
        self.half_len: int = self.middle_idx + 1

        # Pre-allocated scratch wave arrays (ZERO runtime heap allocation)
        self.wave_positions: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_velocities: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_amps: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_colors: np.ndarray = np.zeros((self.MAX_WAVES, 3), dtype=np.float32)
        self.wave_active: np.ndarray = np.zeros(self.MAX_WAVES, dtype=bool)
        self.wave_slot: int = 0
        self.wave_count: int = 0
        self.time_since_wave: float = 0.0
        self.level_accum: float = 1.0
        self._ema_energy: float = 0.35
        self._prev_energy: float = -1.0
        self.wave_width: float = 2.2
        self.breath_phase: float = 6.2831853 * self.segment_phase_offset

        # Coordinate and color buffers
        self.half_coords: np.ndarray = np.arange(self.half_len, dtype=np.float32)
        self.half_dists: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.wave_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.wave_scratch_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.half_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.center_falloff: np.ndarray = np.exp(- (self.half_coords ** 2) / 8.0).astype(np.float32)
        self.glow_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.half_pos: np.ndarray = (self.half_coords / max(1.0, float(self.half_len))).astype(np.float32)
        self.bed_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.tinted_col: np.ndarray = np.zeros(3, dtype=np.float32)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = self.dt
        fps_ratio = self.fps_ratio
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        mood = self.mood_colors

        tension = float(ctx.tension if ctx is not None else 0.0)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        if (not is_silent) and energy <= 0.0:
            energy = float(getattr(self.listener, "asserved_total_power", 0.0))
        lock = self.rhythm_lock
        pulse = self.beat_pulse()

        if self._prev_energy < 0.0:
            self._prev_energy = energy
            self._ema_energy = energy

        d_energy = abs(energy - self._prev_energy)
        swell = max(0.0, energy - self._ema_energy)
        self._prev_energy = energy
        self._ema_energy += self.alpha(3.0) * (energy - self._ema_energy)

        self.time_since_wave += dt

        # 1. Subpixel Wave Propagation Speed (Lead: level sets flow speed; nudged smoothly by mood_pace)
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        lvl = min(1.0, 1.45 * energy)
        flow_gain = 0.45 + 1.15 * lvl
        base_speed = (float(self.half_len) / frames_per_beat) * fps_ratio * flow_gain * (1.0 + 0.5 * tension) * self.mood_pace
        damping = (0.045 / max(0.5, self.mood_trail)) * fps_ratio

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += self.wave_velocities[w] * base_speed
                self.wave_amps[w] *= max(0.0, 1.0 - damping)

                if self.wave_velocities[w] > 0 and self.wave_positions[w] >= (self.half_len + 2.0):
                    self.wave_active[w] = False
                elif self.wave_velocities[w] < 0 and self.wave_positions[w] <= -2.0:
                    self.wave_active[w] = False
                elif self.wave_amps[w] < 0.015:
                    self.wave_active[w] = False

        # 2. Wave Injection from Level Accumulator (decoupled from beat ticks)
        unlocked_drive = max(0.0, 1.0 - (lock / 0.35)) * energy * dt * 1.6 if lock < 0.35 else 0.0
        if not is_silent and energy > 0.04:
            self.level_accum += (9.5 * swell + 6.0 * d_energy) * (0.65 + 0.70 * lvl) * self.mood_pace + unlocked_drive
        else:
            self.level_accum = 0.0

        min_wave_interval = 0.35 * (60.0 / bpm) / max(0.5, 0.75 + 0.50 * lvl)
        seed_wave = self._enter_progress < 0.25 and not bool(np.any(self.wave_active))
        should_trigger = (
            (not is_silent)
            and energy > 0.04
            and ((self.level_accum >= 1.0 and self.time_since_wave >= min_wave_interval) or seed_wave)
            and self._exit_progress <= 0.40
        )

        if should_trigger:
            self.time_since_wave = 0.0
            self.level_accum = 0.0
            slot = self.wave_slot
            self.wave_slot = (self.wave_slot + 1) % self.MAX_WAVES
            self.wave_active[slot] = True
            self.wave_count += 1
            self.wave_positions[slot] = 0.0
            self.wave_velocities[slot] = 1.0
            self.wave_amps[slot] = 0.50 + 0.50 * min(1.0, lvl)
            base_c = mood[self.wave_count % 3]
            hi = self.highlight_color
            # Secondary (beat): pulse tints the spawned wave toward highlight_color
            tint = min(1.0, self.mood_accent + 0.28 * pulse)
            inv_tint = 1.0 - tint
            for c in range(3):
                self.wave_colors[slot, c] = inv_tint * float(base_c[c]) + tint * float(hi[c])

        # 3. Synthesize Half-Strip Energy & Colors (level sets bed and wave brightness; beat tints & shimmers crests)
        self.half_rgb.fill(0.0)
        if not is_silent:
            np.subtract(1.15 * lvl, self.half_pos, out=self.bed_profile)
            np.clip(self.bed_profile, 0.0, 1.0, out=self.bed_profile)
            np.multiply(self.bed_profile, 1.00 * self.transition_scale, out=self.bed_profile)
            m1 = mood[1]
            for c in range(3):
                np.multiply(self.bed_profile, float(m1[c]), out=self.half_rgb[:, c])

        crest_gain = 0.68 * (0.40 + 0.60 * lvl) * (0.86 + 0.14 * pulse)
        two_w_sq = 2.0 * ((self.wave_width * (1.0 - 0.20 * tension)) ** 2)
        inv_two_w_sq = float(-1.0 / two_w_sq) if two_w_sq > 0 else -1.0
        hi = self.highlight_color
        beat_tint = 0.22 * pulse

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                np.square(self.half_dists, out=self.half_dists)
                np.multiply(self.half_dists, inv_two_w_sq, out=self.wave_profile)
                np.exp(self.wave_profile, out=self.wave_profile)
                np.multiply(self.wave_profile, self.wave_amps[w] * crest_gain, out=self.wave_profile)
                col = self.wave_colors[w]
                for c in range(3):
                    tc = (1.0 - beat_tint) * float(col[c]) + beat_tint * float(hi[c])
                    np.multiply(self.wave_profile, tc, out=self.wave_scratch_rgb[:, c])
                np.add(self.half_rgb, self.wave_scratch_rgb, out=self.half_rgb)

        # Gentle acoustic center breathing when flywheel is lost so stalled phase never freezes the strip
        if (not is_silent) and (lock < 0.5) and not bool(np.any(self.wave_active)):
            self.breath_phase = (self.breath_phase + dt * 2.4 * self.mood_pace) % 6.2831853
            breath_amp = (1.0 - 2.0 * lock) * energy * (0.15 + 0.20 * (0.5 + 0.5 * float(np.sin(self.breath_phase))))
            m0 = mood[0]
            for c in range(3):
                np.multiply(self.center_falloff, breath_amp * float(m0[c]), out=self.glow_rgb[:, c])
            np.add(self.half_rgb, self.glow_rgb, out=self.half_rgb)

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
