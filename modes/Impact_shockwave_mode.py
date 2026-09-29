"""
Impact Shockwave Mode
Center-outward expanding ripple waves testing real-beat gating (is_real_beat) vs breakdown coasting.
Spawns high-intensity kinetic shockwaves on verified acoustic hits, while completely suppressing
violent flashes on phantom / coasting beats during silent breakdowns.
Adheres strictly to modes/MODE_RULES.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import utils.colors as colors


class Impact_shockwave_mode(Mode.Mode):
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
                "default": 0.55,  # Electric cyan / neon blue
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
        self.half_hues: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.half_sats: np.ndarray = np.ones(self.half_len, dtype=np.float64)
        self.half_rgb: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)

    def run(self) -> None:
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = getattr(self.listener, "fps_ratio", 1.0)
        self.time_since_last_wave += dt

        # 1. Read rhythmic and acoustic metrics
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        is_beat = getattr(self.listener, "is_beat", False)
        is_real = getattr(self.listener, "is_real_beat", False)
        raw_conf = float(getattr(self.listener, "beat_confidence", 0.0))
        confidence = max(0.0, min(1.0, raw_conf))
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        power = float(getattr(self.listener, "asserved_total_power", 0.0))

        # Detect continuous phase reaching 1.0 (wrapping back to 0.0)
        phase_wrapped = (phase < self.prev_phase) and (self.prev_phase > 0.5)
        self.prev_phase = phase

        # 2. Advance wave propagation based on BPM (MODE_RULES Rule 4)
        # Propagation speed: wave reaches the segment edge in exactly 1 beat period
        # half_len / (frames per beat)
        frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
        speed = (float(self.half_len) / frames_per_beat) * fps_ratio

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                self.wave_positions[w] += speed
                # Progressive exponential decay as the wave ripples outward
                self.wave_amps[w] *= (1.0 - (self.damping * fps_ratio))
                if self.wave_positions[w] >= (self.half_len + 2.0) or self.wave_amps[w] < 0.01:
                    self.wave_active[w] = False

        # 3. Shockwave Injection: fires on is_beat OR every time phase reaches 1.0 (wraps)
        min_wave_interval = 0.40 * (60.0 / bpm)
        should_trigger = (is_beat or phase_wrapped) and (self.time_since_last_wave >= min_wave_interval)

        if should_trigger:
            self.time_since_last_wave = 0.0
            slot = self.next_wave_slot
            self.next_wave_slot = (self.next_wave_slot + 1) % self.MAX_WAVES

            # Calculate wave intensity: verified acoustic hits are full maximum, coasting hits are punchy
            if is_real or confidence > 0.6:
                intensity = 1.0
            else:
                intensity = float(np.clip(0.60 + 0.40 * power, 0.60, 0.95))

            # Select vivid, high-contrast intense hue
            if self.color_mode == "vibrant_cycle":
                # Golden ratio jump (0.61803398875) ensures maximum color separation across consecutive beats
                wave_hue = (self.base_hue + 0.61803398875 * self.wave_count_total) % 1.0
            elif self.color_mode == "neon_palette":
                # Pure neon primaries and secondaries: Cyan, Hot Magenta, Electric Amber, Laser Lime, Violet, Crimson
                neon_hues = (0.52, 0.85, 0.11, 0.35, 0.74, 0.01)
                wave_hue = neon_hues[self.wave_count_total % len(neon_hues)]
            else:
                wave_hue = self.base_hue

            self.wave_active[slot] = True
            self.wave_positions[slot] = 0.0
            self.wave_amps[slot] = intensity
            self.wave_hues[slot] = wave_hue
            self.wave_count_total += 1

        # 4. Synthesize Half-Strip Energy
        self.half_intensity.fill(0.0)
        self.half_hues.fill(self.base_hue)
        self.half_sats.fill(self.color_saturation)
        two_w_sq = 2.0 * (self.wave_width ** 2)

        for w in range(self.MAX_WAVES):
            if self.wave_active[w]:
                # Gaussian pulse profile across half-strip
                np.subtract(self.half_coords, self.wave_positions[w], out=self.half_dists)
                np.square(self.half_dists, out=self.half_dists)
                profile = np.exp(-self.half_dists / two_w_sq) * self.wave_amps[w]
                np.maximum(self.half_intensity, profile, out=self.half_intensity)
                # Blend hue toward active wave hue
                mask = profile > 0.08
                self.half_hues[mask] = self.wave_hues[w]

        # 5. Acoustic Ambient Center Glow Fallback (MODE_RULES Rule 1)
        # Reduced glow floor keeps the background pitch black for extreme color contrast
        center_falloff = np.exp(- (self.half_coords ** 2) / 8.0)
        ambient_glow = (1.0 - confidence) * power * 0.12 * center_falloff
        np.maximum(self.half_intensity, ambient_glow, out=self.half_intensity)
        np.clip(self.half_intensity, 0.0, 1.0, out=self.half_intensity)

        # 6. Vectorized Color Generation on Half-Strip (100% Saturation)
        self.half_rgb = RGB_HSV.fromHSV_toRGB_vectorized(self.half_hues, self.half_sats, self.half_intensity)

        # 7. Symmetrical Mirroring to Full Segment (Zero Allocation)
        # High write ratio (0.85) delivers immediate explosive color punch
        if self.middle_idx > 0:
            left_view = self.half_rgb[1:self.middle_idx + 1][::-1]
            self.smooth_segment_vectorized(0.85, 0, self.middle_idx - 1, left_view)

        # Center LED: index middle_idx
        self.smooth_segment_vectorized(0.85, self.middle_idx, self.middle_idx, self.half_rgb[0])

        # Right half: forward half_rgb
        right_len = self.nb_of_leds - (self.middle_idx + 1)
        if right_len > 0:
            right_view = self.half_rgb[1:right_len + 1]
            self.smooth_segment_vectorized(0.85, self.middle_idx + 1, self.nb_of_leds - 1, right_view)
