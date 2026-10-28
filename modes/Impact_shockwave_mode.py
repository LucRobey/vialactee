"""
Impact Shockwave Mode
Center-outward expanding ripple waves coupled to rhythmic beats when locked and bass spectral flux /
acoustic energy when the beat tracker is lost. Never branches on ctx.scene (eliminating the 1.5s
per-frame wave flood on DROP_IMPACT).
Adheres strictly to docs/contracts/mode_contract.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Impact_shockwave_mode(Mode.Mode):
    """Center-outward discrete shockwave rings spawned on beat phase wraps and drop hits.

    Lead: beat (phase wrap spawns one ring per beat; acoustic fallback when unlocked). Secondary: level (ring intensity/glow). Macro: palette, damping via mood_trail.
    """
    LEAD = "beat"
    SECONDARY = ("level",)
    MAX_WAVES: int = 6

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "color_mode",
                "label": "Color Mode",
                "control": "list",
                "valueType": "string",
                "default": "vibrant_cycle",
                "options": [
                    {"label": "Vibrant Rainbow Cycle (Golden Ratio)", "value": "vibrant_cycle"},
                    {"label": "Hyper Neon Palette", "value": "neon_palette"},
                    {"label": "Single Hue", "value": "single_hue"},
                ],
                "attr": "color_mode",
            },
            {
                "key": "color_saturation",
                "label": "Color Saturation",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 1.0,
                "step": 0.05,
                "default": 1.0,
                "attr": "color_saturation",
            },
            {
                "key": "base_hue",
                "label": "Base Hue",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.55,
                "attr": "base_hue",
            },
            {
                "key": "wave_width",
                "label": "Wavefront Width",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 4.0,
                "step": 0.2,
                "default": 2.2,
                "attr": "wave_width",
            },
            {
                "key": "enable_ghost_ripples",
                "label": "Ghost Ripples in Breakdowns",
                "control": "switch",
                "valueType": "boolean",
                "default": True,
                "attr": "enable_ghost_ripples",
            },
            {
                "key": "damping",
                "label": "Wave Damping",
                "control": "slider",
                "valueType": "number",
                "min": 0.005,
                "max": 0.15,
                "step": 0.005,
                "default": 0.02,
                "attr": "damping",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Configurable parameters
        self.color_mode = str(infos.get("shockwave_color_mode", "vibrant_cycle"))
        self.color_saturation = float(infos.get("shockwave_saturation", 1.0))
        self.base_hue = float(infos.get("shockwave_base_hue", 0.55))
        self.wave_width = float(infos.get("shockwave_width", 2.2))
        self.enable_ghost_ripples = bool(infos.get("shockwave_ghost_ripples", True))
        self.damping = float(infos.get("shockwave_damping", 0.02))

        # Geometric half-strip setup (symmetrical mirroring)
        self.middle_idx: int = self.nb_of_leds // 2
        self.half_len: int = self.middle_idx + 1

        # Pre-allocated scratch wave slots (ZERO runtime heap allocation)
        self.wave_positions: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_amps: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_hues: np.ndarray = np.zeros(self.MAX_WAVES, dtype=np.float64)
        self.wave_colors: np.ndarray = np.zeros((self.MAX_WAVES, 3), dtype=np.float64)
        self.wave_active: np.ndarray = np.zeros(self.MAX_WAVES, dtype=bool)
        self.next_wave_slot: int = 0
        self.wave_count_total: int = 0

        # Phase tracking & lockout state to catch every phase wrap
        self.prev_phase: float = 0.0
        self.time_since_last_wave: float = 1.0

        # Half-strip coordinate & color buffers
        self.half_coords: np.ndarray = np.arange(self.half_len, dtype=np.float64)
        self.half_dists: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.half_intensity: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.ambient_glow: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.half_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)
        self.center_falloff: np.ndarray = np.exp(- (self.half_coords ** 2) / 8.0)
        self.wave_scratch_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)
        self.wave_profile: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.glow_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        dt = self.dt
        fps_ratio = self.fps_ratio
        self.time_since_last_wave += dt

        # 1. Read rhythmic and acoustic metrics without branching on ctx.scene
        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        is_locked = bool(ctx.is_locked if ctx is not None else (float(getattr(self.listener, "beat_confidence", 0.0)) >= 0.5))
        drop_hit = self.drop_hit
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        lock = self.rhythm_lock
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        power = float(ctx.power if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        energy = float(ctx.energy if ctx is not None else power)
        tension = float(ctx.tension if ctx is not None else 0.0)

        # Detect continuous phase reaching 1.0 (wrapping back to 0.0)
        phase_wrapped = (phase < self.prev_phase) and (self.prev_phase > 0.5)
        self.prev_phase = phase

        # 2. Advance wave propagation based on BPM, tension, drop_decay, and mood_pace (docs/contracts/mode_contract.md)
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        speed = (float(self.half_len) / frames_per_beat) * fps_ratio * (1.0 + 0.15 * tension + 0.20 * self.drop_decay) * self.mood_pace
        effective_damping = (self.damping / max(0.5, self.mood_trail)) * fps_ratio

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += speed
                self.wave_amps[w] *= max(0.0, 1.0 - effective_damping)
                if self.wave_positions[w] >= (self.half_len + 2.0) or self.wave_amps[w] < 0.01:
                    self.wave_active[w] = False

        # 3. Shockwave Injection: debounced beat tick / phase wrap, 1-frame drop_hit, or bass flux fallback when lost
        beat_period = 60.0 / bpm
        min_wave_interval = 0.40 * beat_period
        band_flux = getattr(self.listener, "band_flux", None)
        bass_flux_peak = False
        if band_flux is not None and len(band_flux) >= 2:
            bass_flux_peak = float(band_flux[0] + band_flux[1]) > 0.35

        acoustic_pulse = (
            self.enable_ghost_ripples
            and (not is_silent)
            and (lock < 0.35)
            and (bass_flux_peak or (energy > 0.25 and self.time_since_last_wave >= beat_period))
        )
        verified_tick = drop_hit or (phase_wrapped and (is_locked or self.enable_ghost_ripples))
        should_trigger = (
            (not is_silent)
            and (verified_tick or acoustic_pulse)
            and (self.time_since_last_wave >= min_wave_interval)
        )

        if should_trigger:
            self.time_since_last_wave = 0.0
            slot = self.next_wave_slot
            self.next_wave_slot = (self.next_wave_slot + 1) % self.MAX_WAVES

            if drop_hit or is_real or is_locked or lock > 0.6:
                intensity = 1.0
            else:
                intensity = float(np.clip(0.55 + 0.45 * energy, 0.55, 0.95))

            if self.color_mode == "vibrant_cycle":
                wave_hue = (self.base_hue + 0.61803398875 * self.wave_count_total) % 1.0
            elif self.color_mode == "neon_palette":
                neon_hues = (0.52, 0.85, 0.11, 0.35, 0.74, 0.01)
                wave_hue = neon_hues[self.wave_count_total % len(neon_hues)]
            else:
                wave_hue = self.base_hue

            lut_c = self.palette_lut[int(wave_hue * 255.0) & 255]
            sat = max(0.0, min(1.0, float(self.color_saturation)))
            lum = (float(lut_c[0]) + float(lut_c[1]) + float(lut_c[2])) / 3.0
            self.wave_active[slot] = True
            self.wave_positions[slot] = 0.0
            self.wave_amps[slot] = intensity
            self.wave_hues[slot] = wave_hue
            for c in range(3):
                self.wave_colors[slot, c] = (1.0 - sat) * lum + sat * float(lut_c[c])
            self.wave_count_total += 1

        # 4. Synthesize Half-Strip Energy & Colors with self.mood_colors
        self.half_rgb.fill(0.0)
        self.half_intensity.fill(0.0)
        two_w_sq = 2.0 * ((self.wave_width * (1.0 - 0.20 * tension)) ** 2)

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                np.square(self.half_dists, out=self.half_dists)
                np.divide(-self.half_dists, two_w_sq, out=self.wave_profile)
                np.exp(self.wave_profile, out=self.wave_profile)
                self.wave_profile *= self.wave_amps[w]
                np.maximum(self.half_intensity, self.wave_profile, out=self.half_intensity)
                np.multiply(self.wave_profile[:, None], self.wave_colors[w], out=self.wave_scratch_rgb)
                np.add(self.half_rgb, self.wave_scratch_rgb, out=self.half_rgb)

        # 5. Continuous Center Glow (blended smoothly by rhythm_lock and mood_accent)
        mood = self.mood_colors
        if is_silent:
            self.ambient_glow.fill(0.0)
        else:
            glow_drive = ((1.0 - lock) * energy * 0.22) + (self.beat_pulse() * 0.18 * self.mood_accent)
            np.multiply(glow_drive, self.center_falloff, out=self.ambient_glow)

        np.maximum(self.half_intensity, self.ambient_glow, out=self.half_intensity)
        np.clip(self.half_intensity, 0.0, 1.0, out=self.half_intensity)

        accent = self.mood_accent
        hi = self.highlight_color
        m0 = mood[0]
        for c in range(3):
            self.glow_color[c] = (1.0 - accent) * float(m0[c]) + accent * float(hi[c])
        np.multiply(self.ambient_glow[:, None], self.glow_color, out=self.wave_scratch_rgb)
        np.add(self.half_rgb, self.wave_scratch_rgb, out=self.half_rgb)
        np.clip(self.half_rgb, 0.0, 255.0, out=self.half_rgb)

        # 6. Symmetrical Mirroring to Full Segment (Zero Allocation)
        if self.middle_idx > 0:
            left_view = self.half_rgb[1:self.middle_idx + 1][::-1]
            self.smooth_segment_vectorized(0.85, 0, self.middle_idx - 1, left_view)

        self.smooth_segment_vectorized(0.85, self.middle_idx, self.middle_idx, self.half_rgb[0])

        right_len = self.nb_of_leds - (self.middle_idx + 1)
        if right_len > 0:
            right_view = self.half_rgb[1:right_len + 1]
            self.smooth_segment_vectorized(0.85, self.middle_idx + 1, self.nb_of_leds - 1, right_view)
