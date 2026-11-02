"""
Shining Stars Mode
Ambient dark canvas where glowing stars twinkle into existence on dominant band-flux onsets.
Never branches on ctx.scene and eliminates the 1.5s solid fill on DROP_IMPACT.
Star trail fade scales smoothly with mood_trail, twinkle density scales with energy and mood_pace,
star count per sub-segment (1..2) scales with band_flux intensity, star colours are sampled across the
256-entry palette_lut per frequency band, and star brightness scales with band spectral energy and attack punch.
Adheres strictly to docs/contracts/mode_contract.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import zlib
import numpy as np
import random
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Shining_stars_mode(Mode.Mode):
    """Ambient dark canvas where glowing stars twinkle on dominant band-flux onsets.

    Lead: transient (dominant band flux decides when stars light and scales 1..2 stars per subsegment). Secondary: spectrum (band decides color and star brightness). Macro: density via mood_pace, trail via mood_trail.
    """
    LEAD = "transient"
    SECONDARY = ("spectrum",)
    sub_segment_size_default = 40
    threshold_default = 10.0
    fade_ratio_default = 0.1
    threshold = threshold_default

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "threshold",
                "label": "Activation Threshold",
                "control": "slider",
                "valueType": "number",
                "min": 1.0,
                "max": 100.0,
                "step": 1.0,
                "default": self.threshold_default,
                "attr": "threshold",
            },
            {
                "key": "fade_ratio",
                "label": "Star Fade Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.02,
                "max": 0.5,
                "step": 0.02,
                "default": self.fade_ratio_default,
                "attr": "fade_ratio",
            },
            {
                "key": "sub_segment_size",
                "label": "Constellation Spacing",
                "control": "slider",
                "valueType": "number",
                "integer": True,
                "min": 5,
                "max": 100,
                "step": 5,
                "default": self.sub_segment_size_default,
                "attr": "sub_segment_size",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.nb_of_fft_band = getattr(listener, "nb_of_fft_band", 8) if listener is not None else 8
        self.sub_segment_size = int(infos.get("stars_sub_segment_size", infos.get("sub_segment_size", self.sub_segment_size_default)))
        self.threshold = float(infos.get("stars_threshold", infos.get("threshold", self.threshold_default)))
        self.fade_ratio = float(infos.get("stars_fade_ratio", infos.get("fade_ratio", self.fade_ratio_default)))

        colors_list = []
        for band_index in range(self.nb_of_fft_band):
            hue = float(band_index) / max(1, self.nb_of_fft_band - 1)
            rgb = RGB_HSV.fromHSV_toRGB(hue, 1.0, 1.0)
            colors_list.append(rgb)
        self.colors = np.array(colors_list, dtype=np.int32)
        self.star_colors = np.copy(self.colors)
        self.neighbor_colors = np.zeros_like(self.star_colors)
        self.outer_colors = np.zeros_like(self.star_colors)
        self.num_bands: int = min(self.nb_of_fft_band, len(self.colors))
        self._band_lut_idx = np.linspace(0, 255, max(1, self.num_bands), dtype=np.intp)

        self.step: int = max(1, int(self.sub_segment_size))
        self.max_offset: int = min(self.step, self.nb_of_leds)

        seed = zlib.crc32(f"{name}:{segment_name}".encode("utf-8"))
        rng = random.Random(seed)
        self._rand_pool = [rng.randint(0, 100000) for _ in range(256)]
        self._rand_idx = 0
        self._fallback_tick: int = 0

    def apply_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        applied = super().apply_settings(settings)
        self.step = max(1, int(self.sub_segment_size))
        self.max_offset = min(self.step, self.nb_of_leds)
        return applied

    def _spawn_band_stars(self, band_index: int, n_leds: int, step: int, stars_per_seg: int = 1) -> None:
        star_c = self.star_colors[band_index]
        neigh_c = self.neighbor_colors[band_index]
        outer_c = self.outer_colors[band_index]
        base = 0
        while base < n_leds:
            seg_len = step if (base + step) <= n_leds else (n_leds - base)
            seg_end = base + seg_len
            count = stars_per_seg if seg_len >= 8 else 1
            for _ in range(count):
                rand_val = self._rand_pool[self._rand_idx]
                self._rand_idx = (self._rand_idx + 1) & 255
                pos = base + (rand_val % seg_len)
                self.rgb_list[pos] = star_c
                if seg_len >= 3:
                    if pos > base:
                        self.rgb_list[pos - 1] = neigh_c
                    if pos + 1 < seg_end:
                        self.rgb_list[pos + 1] = neigh_c
                if seg_len >= 6:
                    if pos - 1 > base:
                        self.rgb_list[pos - 2] = outer_c
                    if pos + 2 < seg_end:
                        self.rgb_list[pos + 2] = outer_c
            base += step

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        has_real_ctx = isinstance(getattr(ctx, "is_silent", None), bool)

        # 1. Continuous trail fade modulated smoothly by mood_trail (no scene branching)
        trail = self.mood_trail
        effective_fade = self.fade_ratio / (trail if trail > 0.5 else 0.5)
        if effective_fade < 0.01:
            effective_fade = 0.01
        elif effective_fade > 0.85:
            effective_fade = 0.85
        self.fade_to_black(effective_fade)
        if self._exit_progress > 0.50:
            return

        if self.listener is None:
            return
        if has_real_ctx and ctx.is_silent:
            return

        step = self.step
        max_offset = self.max_offset
        if max_offset <= 0:
            return

        # 2. Scale twinkle density with energy, mood_pace, and syncopation
        if has_real_ctx:
            energy = float(getattr(ctx, "energy", 0.0))
            is_sync = bool(getattr(ctx, "is_syncopated", False))
            density_boost = (0.30 * energy * self.mood_pace) + (0.25 if is_sync else 0.0)
            current_threshold = max(0.5, self.threshold * (1.0 - 0.50 * density_boost))
            bands = getattr(self.listener, "asserved_fft_band", None)
            lock = self.rhythm_lock
        else:
            current_threshold = self.threshold
            bands = getattr(self.listener, "asserved_fft_band", None)
            lock = 1.0

        band_flux = getattr(self.listener, "band_flux", None)
        if band_flux is None and bands is None:
            return

        # 3. Sample distinct band colours from palette_lut, scaled by each band's energy (SECONDARY="spectrum")
        #    and brightened at the core by transient attack strength.
        lut = self.palette_lut
        hi = self.highlight_color
        accent = self.mood_accent
        t_scale = (
            self.transition_scale
            if (self._exit_progress > 0.0 or self._enter_progress < 1.0)
            else 1.0
        )
        n_bands_avail = len(bands) if bands is not None else 0
        n_flux = min(self.num_bands, len(band_flux)) if band_flux is not None else 0
        thr_ref = max(1.0, current_threshold)

        for i in range(self.num_bands):
            base_c = lut[self._band_lut_idx[i]]
            if i < n_bands_avail:
                b_val = float(bands[i])
                if b_val < 0.0:
                    b_val = 0.0
                elif b_val > 1.0:
                    b_val = 1.0
                spec_gain = 0.52 + 0.48 * b_val
            else:
                spec_gain = 1.0

            f_val = float(band_flux[i]) if i < n_flux else 0.0
            flux_boost = min(1.0, max(0.0, f_val / (thr_ref * 2.2)))
            gain = min(1.0, spec_gain * (0.85 + 0.15 * flux_boost)) * t_scale
            core_hi = min(0.65, accent + 0.25 * flux_boost)
            for c in range(3):
                val = int(((1.0 - core_hi) * float(base_c[c]) + core_hi * float(hi[c])) * gain)
                if val > 255:
                    val = 255
                self.star_colors[i, c] = val
                self.neighbor_colors[i, c] = (val * 2) // 3   # 67% inner halo neighbor
                self.outer_colors[i, c] = (val * 3) // 10     # 30% outer soft glow

        # 4. Trigger only dominant band-flux onsets (LEAD="transient"), scaling star count (1..2) by flux,
        #    with sparse unlocked fallback (Law 1).
        n_leds = self.nb_of_leds
        max_flux = 0.0
        for i in range(n_flux):
            fv = float(band_flux[i])
            if fv > max_flux:
                max_flux = fv

        if max_flux > current_threshold:
            self._fallback_tick = 0
            dom_cutoff = 0.50 * max_flux
            for band_index in range(n_flux):
                flux_val = float(band_flux[band_index])
                if flux_val > current_threshold and flux_val >= dom_cutoff:
                    stars_per_seg = 2 if flux_val >= (1.8 * current_threshold) else 1
                    self._spawn_band_stars(band_index, n_leds, step, stars_per_seg=stars_per_seg)
        elif lock < 0.35 and n_bands_avail > 0:
            self._fallback_tick += 1
            if self._fallback_tick >= 10:
                self._fallback_tick = 0
                best_band = -1
                best_val = 0.35
                for i in range(min(self.num_bands, n_bands_avail)):
                    bv = float(bands[i])
                    if bv > best_val:
                        best_val = bv
                        best_band = i
                if best_band >= 0:
                    self._spawn_band_stars(best_band, n_leds, step, stars_per_seg=1)
