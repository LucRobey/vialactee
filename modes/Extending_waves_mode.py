"""
Extending Waves Mode
Continuous center-outward scrolling wavelength wave stream ("musical timeline") with zero numerical diffusion.
Colors match the dominant playing wavelength (Band 0 bass/drums = Red -> Mids = Green/Cyan -> Treble = Blue/Violet),
rebalanced via per-band rolling-mean deviation, onset flux boosting, and anti-stagnation fatigue so colors evolve
constantly while drum hits regularly inject vivid Red peaks that extend outward at a steady, regular pace.
Adheres strictly to docs/contracts/mode_contract.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import utils.colors as colors


class Extending_waves_mode(Mode.Mode):
    """Center-outward scrolling wavelength waves driven by balanced FFT band deviations and onset peaks.

    Lead: spectrum (dominant wavelength color and spectral wave crests). Secondary: transient (drum/onset flux peaks). Macro: mood_pace, mood_trail, mood_accent.
    """
    LEAD = "spectrum"
    SECONDARY = ("transient",)
    MAX_WAVES: int = 8

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle_idx: int = self.nb_of_leds // 2
        self.half_len: int = self.middle_idx + 1
        self.nb_bands: int = max(2, int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8)
        self.hist_len: int = max(256, self.half_len + 32)

        # Precomputed 256-entry vivid rainbow LUT from Red (0.00, bass/drums) to Violet (0.82, treble)
        lut_hues = np.linspace(colors.red_hue, 0.82, 256, dtype=np.float64)
        self.rainbow_lut: np.ndarray = RGB_HSV.fromHSV_toRGB_vectorized(lut_hues, 1.0, 1.0).astype(np.float32)

        # Pre-allocated scratch wave arrays for peak crests and cooperative exit stacking (ZERO heap allocation)
        self.wave_positions: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_velocities: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_amps: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float32)
        self.wave_colors: np.ndarray = np.zeros((self.MAX_WAVES, 3), dtype=np.float32)
        self.wave_active: np.ndarray = np.zeros(self.MAX_WAVES, dtype=bool)
        self.wave_slot: int = 0
        self.wave_count: int = 0
        self.time_since_wave: float = 0.0
        self.wave_width: float = 2.0
        self._stack_frontier: float = float(self.half_len)

        # Balanced spectral wavelength tracking state (deviation + onset flux + anti-stagnation fatigue)
        self.fft_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self.flux_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._band_ema: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._prev_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._band_dev: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._band_rise: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._rel_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._norm_flux: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._band_scores: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._band_fatigue: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)
        self._flux_scale: float = 2.0
        self._current_hue: float = 0.0
        self._crest_env: float = 0.0
        self._spec_activity: float = 0.0
        self._silent_frames: int = 0
        self._initialized: bool = False
        self.dominant_band: int = 0
        self._band_hold_time: float = 0.0
        self._drum_cooldown: float = 0.0
        self._drum_hold_frames: int = 0

        # Zero-diffusion subpixel history ring buffer & coordinate scratch arrays
        self.scroll_pos: float = float(self.half_len + 4)
        self.hist_rgb: np.ndarray = np.zeros((self.hist_len, 3), dtype=np.float32)
        self._center_rgb: np.ndarray = np.zeros(3, dtype=np.float32)
        self._prev_center_rgb: np.ndarray = np.zeros(3, dtype=np.float32)

        self.half_coords: np.ndarray = np.arange(self.half_len, dtype=np.float32)
        self.half_pos: np.ndarray = (self.half_coords / max(1.0, float(self.half_len))).astype(np.float32)
        self._src_pos: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self._src_floor: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self._src_frac_2d: np.ndarray = np.zeros((self.half_len, 1), dtype=np.float32)
        self._src_frac: np.ndarray = self._src_frac_2d[:, 0]
        self._idx0: np.ndarray = np.zeros(self.half_len, dtype=np.intp)
        self._idx1: np.ndarray = np.zeros(self.half_len, dtype=np.intp)
        self._sample0: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self._sample1: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self._radial_env_2d: np.ndarray = np.zeros((self.half_len, 1), dtype=np.float32)
        self._radial_env: np.ndarray = self._radial_env_2d[:, 0]

        self.half_dists: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.wave_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.wave_scratch_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.half_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.bed_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float32)

    @property
    def transition_scale(self) -> float:
        """Keep full brightness on cooperative exit so white waves stack to 255 from edges inward."""
        if self._enter_progress < 1.0:
            p_in = self._enter_progress
            return float(0.15 + 0.85 * (1.0 - (1.0 - p_in) * (1.0 - p_in)))
        return 1.0

    def on_transition_reset(self) -> None:
        super().on_transition_reset()
        self._stack_frontier = float(self.half_len)

    def _ensure_band_capacity(self, nb: int) -> None:
        if nb > 1 and nb != self.nb_bands:
            self.nb_bands = nb
            self.fft_bands = np.zeros(nb, dtype=np.float32)
            self.flux_bands = np.zeros(nb, dtype=np.float32)
            self._band_ema = np.zeros(nb, dtype=np.float32)
            self._prev_bands = np.zeros(nb, dtype=np.float32)
            self._band_dev = np.zeros(nb, dtype=np.float32)
            self._band_rise = np.zeros(nb, dtype=np.float32)
            self._rel_bands = np.zeros(nb, dtype=np.float32)
            self._norm_flux = np.zeros(nb, dtype=np.float32)
            self._band_scores = np.zeros(nb, dtype=np.float32)
            self._band_fatigue = np.zeros(nb, dtype=np.float32)
            self._initialized = False

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        exit_prog = float(self._exit_progress)

        if is_silent and exit_prog <= 0.0:
            self._silent_frames += 1
            if self._silent_frames > 22:
                self.hist_rgb *= 0.85
                self.wave_active.fill(False)
                self.fade_to_black_segment_vectorized(0.20, 0, self.nb_of_leds - 1)
                return
        else:
            self._silent_frames = 0

        dt = self.dt
        fps_ratio = self.fps_ratio
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        tension = float(ctx.tension if ctx is not None else 0.0)
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        drop_hit = self.drop_hit
        lock = self.rhythm_lock
        unlocked_alive = max(0.0, 1.0 - (lock / 0.15)) if lock < 0.15 else 0.0

        self.time_since_wave += dt

        # 1. Steady, Regular Outward Extension Speed (gently linked to BPM and mood_pace, independent of volume)
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        base_speed = max(
            0.28 * fps_ratio,
            (float(self.half_len) / (2.2 * frames_per_beat)) * fps_ratio * self.mood_pace,
        )
        damping = (0.040 / max(0.5, self.mood_trail)) * fps_ratio

        if exit_prog <= 0.0:
            self._stack_frontier = float(self.half_len)

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += self.wave_velocities[w] * base_speed
                self.wave_amps[w] *= max(0.0, 1.0 - damping)

                if exit_prog > 0.0 and self.wave_velocities[w] > 0 and self.wave_positions[w] >= (self._stack_frontier - 1.2):
                    self._stack_frontier = max(-0.15 * float(self.half_len), self._stack_frontier - self.wave_width * 1.35)
                    self.wave_active[w] = False
                elif self.wave_velocities[w] > 0 and self.wave_positions[w] >= (self.half_len + 2.0):
                    self.wave_active[w] = False
                elif self.wave_velocities[w] < 0 and self.wave_positions[w] <= -2.0:
                    self.wave_active[w] = False
                elif self.wave_amps[w] < 0.015:
                    self.wave_active[w] = False

        # 2. Read Spectrum (LEAD) and Onset Flux (SECONDARY)
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is not None and len(bands) > 1:
            self._ensure_band_capacity(len(bands))
            self.fft_bands[:] = bands[:self.nb_bands]
        else:
            self.fft_bands.fill(0.35)

        prop = getattr(self.listener, "band_proportion", None)
        if prop is not None and len(prop) >= self.nb_bands and float(np.sum(prop[:self.nb_bands])) > 1e-6:
            # Blend unclipped band_proportion into fft_bands so big beats that clip asserved_fft_band at 1.0
            # preserve true inter-band wavelength contrast and continuous frame-to-frame motion.
            for b in range(self.nb_bands):
                p_scaled = min(1.25, float(prop[b]) * float(self.nb_bands) * 0.55)
                self.fft_bands[b] = 0.72 * float(self.fft_bands[b]) + 0.28 * p_scaled

        raw_flux = getattr(self.listener, "band_flux", None)
        if raw_flux is not None and len(raw_flux) >= self.nb_bands:
            self.flux_bands[:] = raw_flux[:self.nb_bands]
        else:
            self.flux_bands.fill(0.0)

        nb = self.nb_bands
        if not self._initialized:
            self._band_ema[:] = self.fft_bands
            self._prev_bands[:] = self.fft_bands
            self._band_fatigue.fill(0.0)

        # Frame-to-frame spectral change & positive attack
        np.subtract(self.fft_bands, self._prev_bands, out=self._band_rise)
        max_abs_delta = float(np.max(np.abs(self._band_rise)))
        np.clip(self._band_rise, 0.0, 1.0, out=self._band_rise)
        self._prev_bands[:] = self.fft_bands

        np.subtract(self.fft_bands, self._band_ema, out=self._band_dev)
        np.clip(self._band_dev, 0.0, 1.0, out=self._band_dev)
        ema_alpha = self.alpha(2.2)
        self._band_ema += ema_alpha * (self.fft_bands - self._band_ema)

        # Normalize onset flux (Secondary: transient)
        max_f = float(np.max(self.flux_bands))
        self._flux_scale = max(0.6, self._flux_scale * (1.0 - self.alpha(1.8)), max_f)
        np.divide(self.flux_bands, self._flux_scale, out=self._norm_flux)
        np.clip(self._norm_flux, 0.0, 1.0, out=self._norm_flux)

        # Mean-rebalanced relative band share
        np.add(self._band_ema, 0.12, out=self._band_scores)
        np.divide(self.fft_bands, self._band_scores, out=self._rel_bands)
        self._rel_bands -= float(np.min(self._rel_bands))

        # 3. Balanced Dominant Wavelength Scoring (Deviations + Onset Flux + Anti-Stagnation Fatigue)
        self._band_hold_time += dt
        self._drum_cooldown = max(0.0, self._drum_cooldown - dt)

        max_dev = float(np.max(self._band_dev))
        max_rise = float(np.max(self._band_rise))
        spec_moving = 1.0 if max_abs_delta > 1e-6 else 0.0
        inst_spec_act = min(
            1.0,
            2.8 * max_dev
            + 4.2 * max_rise
            + 0.45 * float(np.max(self._rel_bands)) * spec_moving
            + 0.35 * unlocked_alive,
        )
        self._spec_activity = max(inst_spec_act, self._spec_activity * (1.0 - self.alpha(2.8)))

        # Drum / Kick peak detection on rising bass transient (with cooldown so it creates a crisp Red peak, not a permanent red fill)
        low_flux = max(float(self._norm_flux[0]), 0.70 * float(self._norm_flux[1]) if nb > 1 else 0.0)
        bass_attack = (
            0.85 * float(self._band_rise[0])
            + 0.25 * float(self._band_dev[0])
            + 0.95 * low_flux * self._spec_activity
            + (0.35 if (is_real or drop_hit) and self._spec_activity > 0.05 else 0.0)
        )

        if self._drum_cooldown <= 0.0 and bass_attack > 0.30 and self._spec_activity > 0.05:
            self._drum_hold_frames = 4
            self._drum_cooldown = max(0.24, 0.42 * (60.0 / bpm))
            self._band_fatigue[0] *= 0.25

        is_drum_peak = self._drum_hold_frames > 0
        if self._drum_hold_frames > 0:
            self._drum_hold_frames -= 1
            if self._drum_hold_frames == 0:
                # Immediately fatigue Band 0 after the drum crest so the melody/other bands take over between beats
                self._band_fatigue[0] = min(2.2, float(self._band_fatigue[0]) + 1.10)

        for b in range(nb):
            dev_b = float(self._band_dev[b])
            rise_b = float(self._band_rise[b])
            rel_b = float(self._rel_bands[b])
            flx_b = float(self._norm_flux[b]) * (0.15 + 0.85 * self._spec_activity)
            # Mildly boost b >= 1 to counterbalance natural 1/f bass dominance in raw audio
            band_eq = 0.80 if b == 0 else (1.02 + 0.03 * min(6, b))
            raw_s = band_eq * (2.4 * dev_b + 3.0 * rise_b + 0.60 * rel_b + 0.85 * flx_b)

            if b == 0 and is_drum_peak:
                raw_s = (raw_s + 0.45) * 2.20
                eff_fatigue = 0.0
            else:
                eff_fatigue = float(self._band_fatigue[b])

            self._band_scores[b] = raw_s / (1.0 + 2.8 * eff_fatigue)

        cand_band = int(np.argmax(self._band_scores))
        if not self._initialized or is_drum_peak:
            b_star = 0 if is_drum_peak else cand_band
            if b_star != self.dominant_band:
                self._band_hold_time = 0.0
        else:
            cur_b = min(nb - 1, max(0, self.dominant_band))
            cur_score = float(self._band_scores[cur_b])
            cand_score = float(self._band_scores[cand_band])
            # Hold current wavelength for ~0.11s (6-7 frames = 3-4 LEDs) unless a strong new attack jumps ahead
            if cand_band != cur_b and (
                self._band_hold_time >= 0.11
                or cand_score > (cur_score * 2.15 + 0.08)
            ):
                b_star = cand_band
                self._band_hold_time = 0.0
            else:
                b_star = cur_b
        self.dominant_band = b_star

        # Update anti-stagnation fatigue so sustained bands yield to other active wavelengths
        self._band_fatigue *= (1.0 - self.alpha(2.0))
        if self._spec_activity > 0.02:
            self._band_fatigue[b_star] = min(2.2, float(self._band_fatigue[b_star]) + dt * 4.5)
            if b_star > 0:
                self._band_fatigue[b_star - 1] = min(2.2, float(self._band_fatigue[b_star - 1]) + dt * 0.65)
            if b_star + 1 < nb:
                self._band_fatigue[b_star + 1] = min(2.2, float(self._band_fatigue[b_star + 1]) + dt * 0.65)

        # Winner-take-most local hue interpolation (0.00 Red for drums/bass -> 0.82 Violet for treble)
        s_c = float(self._band_scores[b_star])
        s_l = float(self._band_scores[b_star - 1]) if b_star > 0 else 0.0
        s_r = float(self._band_scores[b_star + 1]) if (b_star + 1) < nb else 0.0
        local_offset = 0.35 * (s_r - s_l) / (s_c + s_l + s_r + 1e-6)
        w_pos = max(0.0, min(1.0, (float(b_star) + local_offset) / max(1.0, float(nb - 1))))
        target_hue = 0.0 if is_drum_peak else (0.82 * w_pos)

        if not self._initialized:
            self._current_hue = target_hue
        elif self._spec_activity > 0.01:
            hue_diff = abs(target_hue - self._current_hue)
            # Snap fast on drum peaks or cross-band jumps so Red drums never smear through Green
            hue_rate = 55.0 if is_drum_peak or hue_diff > 0.18 else 20.0
            self._current_hue += self.alpha(hue_rate) * (target_hue - self._current_hue)

        # 4. Synthesize Center Wavelength Color & Wave Crest Intensity
        lut_idx = int(max(0.0, min(255.0, (self._current_hue / 0.82) * 255.0)))
        base_col = self.rainbow_lut[lut_idx]

        # Wave crest envelope: sharp peaks on drum hits, spectral attacks, and onset flux, with deeper wave valleys
        trans_kick = max(
            float(self._norm_flux[b_star]),
            low_flux if is_drum_peak else 0.0,
            0.85 if (is_real or drop_hit) else 0.0,
        )
        # Gate secondary transient by spectral activity so spectrum remains the clear lead driver
        sec_punch = trans_kick * (0.10 + 0.90 * self._spec_activity)
        spec_crest = min(0.62, 0.85 * max_dev + 1.45 * max_rise)
        crest_target = min(
            1.0,
            spec_crest + 0.52 * sec_punch + (0.45 if is_drum_peak else 0.0),
        )
        if is_drum_peak:
            self._crest_env = max(self._crest_env, crest_target)
        elif crest_target >= self._crest_env:
            self._crest_env += self.alpha(55.0) * (crest_target - self._crest_env)
        else:
            self._crest_env += self.alpha(8.5) * (crest_target - self._crest_env)

        # Spatial wave undulation so extending waves show clear rhythmic crests and valleys
        wave_carrier = 0.5 + 0.5 * math.sin(self.scroll_pos * 1.25)
        mean_band = float(np.mean(self.fft_bands))
        base_floor = 0.18 * mean_band + 0.12 * self._spec_activity
        dynamic_wave = self._spec_activity * (0.14 + 0.26 * (wave_carrier * wave_carrier)) + 0.65 * self._crest_env
        center_val = max(0.0, min(1.0, base_floor + dynamic_wave)) * self.transition_scale

        hi = self.highlight_color
        accent_mix = min(0.18, 0.45 * self.mood_accent)
        inv_acc = 1.0 - accent_mix
        white_mix = min(1.0, exit_prog * 1.65)
        center_exit_atten = max(0.25, 1.0 - 0.65 * exit_prog) if exit_prog > 0.0 else 1.0
        for c in range(3):
            col_c = inv_acc * float(base_col[c]) + accent_mix * float(hi[c])
            tinted_c = (1.0 - white_mix) * col_c + white_mix * 255.0
            self._center_rgb[c] = tinted_c * center_val * center_exit_atten

        # 5. Advance Zero-Diffusion Subpixel History Ring Buffer (never reset mid-song!)
        if not self._initialized:
            self.hist_rgb[:] = self._center_rgb
            self._prev_center_rgb[:] = self._center_rgb
            self._initialized = True
        else:
            prev_slot = int(math.floor(self.scroll_pos))
            self.scroll_pos += base_speed
            curr_slot = int(math.floor(self.scroll_pos))
            steps = curr_slot - prev_slot
            if steps <= 0:
                self.hist_rgb[curr_slot % self.hist_len] = self._center_rgb
            elif steps == 1:
                self.hist_rgb[curr_slot % self.hist_len] = self._center_rgb
            else:
                steps_clamped = min(steps, self.hist_len)
                for s in range(1, steps_clamped + 1):
                    frac_s = float(s) / float(steps_clamped)
                    slot_idx = (prev_slot + s) % self.hist_len
                    for c in range(3):
                        self.hist_rgb[slot_idx, c] = (
                            (1.0 - frac_s) * float(self._prev_center_rgb[c]) + frac_s * float(self._center_rgb[c])
                        )
            self._prev_center_rgb[:] = self._center_rgb

        # 6. Discrete Wave Crest Injection (reinforces drum/spectral peaks & drives cooperative exit white stack)
        min_wave_interval = 0.28 * (60.0 / bpm)
        seed_wave = self._enter_progress < 0.25 and not bool(np.any(self.wave_active))
        exit_wave = exit_prog > 0.0 and exit_prog < 0.88 and self.time_since_wave >= (0.22 * (60.0 / bpm))
        peak_trigger = (is_drum_peak or self._crest_env > 0.32 or is_real or drop_hit) and self.time_since_wave >= min_wave_interval
        should_trigger = (
            (not is_silent or exit_prog > 0.0)
            and (peak_trigger or seed_wave or exit_wave)
            and exit_prog < 0.90
        )

        if should_trigger:
            self.time_since_wave = 0.0
            slot = self.wave_slot
            self.wave_slot = (self.wave_slot + 1) % self.MAX_WAVES
            self.wave_active[slot] = True
            self.wave_count += 1
            self.wave_positions[slot] = 0.0
            self.wave_velocities[slot] = 1.0
            self.wave_amps[slot] = max(exit_prog, min(1.0, 0.35 + 0.65 * self._crest_env))
            for c in range(3):
                self.wave_colors[slot, c] = (1.0 - white_mix) * float(base_col[c]) + white_mix * 255.0

        # 7. Sample Subpixel History Buffer Across the Half-Strip (Zero Allocation)
        np.subtract(self.scroll_pos, self.half_coords, out=self._src_pos)
        np.mod(self._src_pos, float(self.hist_len), out=self._src_pos)
        np.floor(self._src_pos, out=self._src_floor)
        np.subtract(self._src_pos, self._src_floor, out=self._src_frac)
        np.copyto(self._idx0, self._src_floor, casting="unsafe")
        np.add(self._idx0, 1, out=self._idx1)
        np.mod(self._idx1, self.hist_len, out=self._idx1)

        np.take(self.hist_rgb, self._idx0, axis=0, out=self._sample0)
        np.take(self.hist_rgb, self._idx1, axis=0, out=self._sample1)

        np.subtract(self._sample1, self._sample0, out=self.half_rgb)
        np.multiply(self.half_rgb, self._src_frac_2d, out=self.half_rgb)
        np.add(self.half_rgb, self._sample0, out=self.half_rgb)

        # Gentle radial trail attenuation toward outer tips (modulated by mood_trail)
        trail_falloff = 0.28 / max(0.5, self.mood_trail)
        np.multiply(self.half_pos, -trail_falloff, out=self._radial_env)
        np.add(self._radial_env, 1.0, out=self._radial_env)
        np.clip(self._radial_env, 0.45, 1.0, out=self._radial_env)
        np.multiply(self.half_rgb, self._radial_env_2d, out=self.half_rgb)

        # Add travelling peak wave crests
        two_w_sq = 2.0 * ((self.wave_width * (1.0 - 0.15 * tension)) ** 2)
        inv_two_w_sq = float(-1.0 / two_w_sq) if two_w_sq > 0 else -1.0
        crest_boost = (0.32 * self._spec_activity) if exit_prog <= 0.0 else 0.75

        if crest_boost > 0.001:
            for w in range(self.MAX_WAVES):
                if self.wave_active[w]:
                    np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                    np.square(self.half_dists, out=self.half_dists)
                    np.multiply(self.half_dists, inv_two_w_sq, out=self.wave_profile)
                    np.exp(self.wave_profile, out=self.wave_profile)
                    np.multiply(self.wave_profile, self.wave_amps[w] * crest_boost, out=self.wave_profile)
                    col = self.wave_colors[w]
                    white_w = min(1.0, exit_prog * 1.40)
                    for c in range(3):
                        tc = (1.0 - white_w) * float(col[c]) + white_w * 255.0
                        np.multiply(self.wave_profile, tc, out=self.wave_scratch_rgb[:, c])
                    np.add(self.half_rgb, self.wave_scratch_rgb, out=self.half_rgb)

        # Bespoke cooperative exit: white waves stack and accumulate from outer edges inward
        if exit_prog > 0.0:
            self._stack_frontier = min(self._stack_frontier, float(self.half_len) * (1.0 - 1.18 * exit_prog))
            stack_frontier = self._stack_frontier / max(1.0, float(self.half_len))
            np.subtract(self.half_pos, stack_frontier, out=self.bed_profile)
            np.multiply(self.bed_profile, 1.0 / 0.12, out=self.bed_profile)
            np.clip(self.bed_profile, 0.0, 1.0, out=self.bed_profile)
            np.multiply(self.bed_profile, 255.0 * min(1.0, 0.38 + exit_prog * 1.15), out=self.bed_profile)
            for c in range(3):
                np.maximum(self.half_rgb[:, c], self.bed_profile, out=self.half_rgb[:, c])

        np.clip(self.half_rgb, 0.0, 255.0, out=self.half_rgb)

        # 8. Symmetrical Mirroring to Full Segment
        if self.middle_idx > 0:
            left_view = self.half_rgb[1:self.middle_idx + 1][::-1]
            self.smooth_segment_vectorized(0.80, 0, self.middle_idx - 1, left_view)

        self.smooth_segment_vectorized(0.80, self.middle_idx, self.middle_idx, self.half_rgb[0])

        right_len = self.nb_of_leds - (self.middle_idx + 1)
        if right_len > 0:
            right_view = self.half_rgb[1:right_len + 1]
            self.smooth_segment_vectorized(0.80, self.middle_idx + 1, self.nb_of_leds - 1, right_view)

