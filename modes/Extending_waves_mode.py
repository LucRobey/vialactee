"""
Extending Waves Mode
Subpixel wave propagation driven by dt * speed(bpm, tension) * mood_pace.
Wave injection on every rhythmic tempo tick (flywheel listener.is_beat, real beat, or phase wrap).
Waves always propagate outward from the center with no scene branching.
Harmonized with the mood sector's mood_colors and mood_modifiers with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Extending_waves_mode(Mode.Mode):
    """Center-outward traveling color waves whose flow speed scales with audio energy.

    Lead: level (flow speed = energy). Secondary: beat (tints stream hue/brightness). Macro: color drift, mood_pace.
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
        self.time_since_wave: float = 1.0
        self.prev_phase: float = 0.0
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

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = self.dt
        fps_ratio = self.fps_ratio
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        mood = self.mood_colors

        tension = float(ctx.tension if ctx is not None else 0.0)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        lock = self.rhythm_lock
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        phase_wrapped = (phase < self.prev_phase) and (self.prev_phase > 0.5) and (not is_silent)
        self.prev_phase = phase

        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        band_flux = getattr(self.listener, "band_flux", None)
        bass_flux_peak = False
        if (not is_silent) and (lock < 0.25) and band_flux is not None and len(band_flux) >= 2:
            bass_flux_peak = float(band_flux[0] + band_flux[1]) > 0.35

        # Flywheel tempo tick: fires once per beat period even when no acoustic transient backs it.
        is_tick = bool(getattr(self.listener, "is_beat", False)) or is_real or phase_wrapped or bass_flux_peak

        self.time_since_wave += dt

        # 1. Subpixel Wave Propagation Speed (nudged smoothly by mood_pace)
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        base_speed = (float(self.half_len) / frames_per_beat) * fps_ratio * (1.0 + 0.6 * tension) * self.mood_pace
        damping = (0.035 / max(0.5, self.mood_trail)) * fps_ratio

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += self.wave_velocities[w] * base_speed
                self.wave_amps[w] *= max(0.0, 1.0 - damping)

                # Boundary checking
                if self.wave_velocities[w] > 0 and self.wave_positions[w] >= (self.half_len + 2.0):
                    self.wave_active[w] = False
                elif self.wave_velocities[w] < 0 and self.wave_positions[w] <= -2.0:
                    self.wave_active[w] = False
                elif self.wave_amps[w] < 0.015:
                    self.wave_active[w] = False

        # 2. Wave Injection: one outward wave per rhythmic tempo tick (no scene reversal)
        min_wave_interval = 0.35 * (60.0 / bpm)
        seed_wave = self._enter_progress < 0.25 and not bool(np.any(self.wave_active))
        should_trigger = (
            (not is_silent)
            and ((is_tick and self.time_since_wave >= min_wave_interval) or seed_wave)
            and self._exit_progress <= 0.40
        )

        if should_trigger:
            self.time_since_wave = 0.0
            slot = self.wave_slot
            self.wave_slot = (self.wave_slot + 1) % self.MAX_WAVES
            self.wave_active[slot] = True
            self.wave_count += 1
            self.wave_positions[slot] = 0.0
            self.wave_velocities[slot] = 1.0
            self.wave_amps[slot] = 0.90
            beat_tag = str(getattr(self.listener, "beat_tag", "Bass/Kick"))
            tag_offset = 1 if beat_tag == "Snare/Mid" else (2 if beat_tag == "Hi-hat/Cymbal" else 0)
            base_c = mood[(self.wave_count + tag_offset) % 3]
            accent = self.mood_accent
            if accent > 0.001:
                hi = self.highlight_color
                inv_acc = 1.0 - accent
                for c in range(3):
                    self.wave_colors[slot, c] = inv_acc * float(base_c[c]) + accent * float(hi[c])
            else:
                self.wave_colors[slot] = base_c

        # 3. Synthesize Half-Strip Energy & Colors
        self.half_rgb.fill(0.0)
        two_w_sq = 2.0 * ((self.wave_width * (1.0 - 0.20 * tension)) ** 2)
        inv_two_w_sq = float(-1.0 / two_w_sq) if two_w_sq > 0 else -1.0

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                np.square(self.half_dists, out=self.half_dists)
                np.multiply(self.half_dists, inv_two_w_sq, out=self.wave_profile)
                np.exp(self.wave_profile, out=self.wave_profile)
                np.multiply(self.wave_profile, self.wave_amps[w], out=self.wave_profile)
                col = self.wave_colors[w]
                for c in range(3):
                    np.multiply(self.wave_profile, float(col[c]), out=self.wave_scratch_rgb[:, c])
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
