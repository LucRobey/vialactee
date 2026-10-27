"""
Shining Stars Mode
Ambient dark canvas where soft 3-LED stars twinkle into existence across frequency bands.
Never branches on ctx.scene and eliminates the 1.5s solid fill on DROP_IMPACT.
Star trail fade scales smoothly with mood_trail, twinkle density scales with energy and mood_pace,
and star colours are sampled across the 256-entry palette_lut for all 8 bands.
Adheres strictly to docs/contracts/mode_contract.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import random
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Shining_stars_mode(Mode.Mode):
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
        self.num_bands: int = min(self.nb_of_fft_band, len(self.colors))
        self._band_lut_idx = np.linspace(0, 255, max(1, self.num_bands), dtype=np.intp)

        self.step: int = max(1, int(self.sub_segment_size))
        self.max_offset: int = min(self.step, self.nb_of_leds)

        rng = random.Random(hash((name, segment_name)) & 0xFFFFFFFF)
        self._rand_pool = [rng.randint(0, 100000) for _ in range(256)]
        self._rand_idx = 0

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        super().apply_settings(settings)
        self.step = max(1, int(self.sub_segment_size))
        self.max_offset = min(self.step, self.nb_of_leds)

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

        # 2. Sample 8 distinct band colours from palette_lut, gently warmed by mood_accent
        lut = self.palette_lut
        hi = self.highlight_color
        accent = self.mood_accent
        for i in range(self.num_bands):
            base_c = lut[self._band_lut_idx[i]]
            for c in range(3):
                val = int((1.0 - accent) * float(base_c[c]) + accent * float(hi[c]))
                self.star_colors[i, c] = val
                self.neighbor_colors[i, c] = (val * 2) // 5  # 40% soft halo neighbor

        # 3. Scale twinkle density with energy, mood_pace, and syncopation
        if has_real_ctx:
            energy = float(getattr(ctx, "energy", 0.0))
            is_sync = bool(getattr(ctx, "is_syncopated", False))
            density_boost = (0.30 * energy * self.mood_pace) + (0.25 if is_sync else 0.0)
            current_threshold = max(0.5, self.threshold * (1.0 - 0.50 * density_boost))
            bands = getattr(self.listener, "asserved_fft_band", None)
            lock = self.rhythm_lock
        else:
            current_threshold = self.threshold
            bands = None
            lock = 1.0

        band_flux = getattr(self.listener, "band_flux", None)
        if band_flux is None and bands is None:
            return

        n_leds = self.nb_of_leds
        for band_index in range(self.num_bands):
            flux_val = float(band_flux[band_index]) if (band_flux is not None and band_index < len(band_flux)) else 0.0
            band_val = float(bands[band_index]) if (bands is not None and band_index < len(bands)) else 0.0
            # When flywheel is lost or flux is flat during sustained notes, allow spectral band energy to twinkle
            drive = max(flux_val, (1.0 - 0.6 * lock) * band_val * self.threshold * 2.8)
            if drive > current_threshold:
                star_c = self.star_colors[band_index]
                neigh_c = self.neighbor_colors[band_index]
                base = 0
                while base < n_leds:
                    seg_len = step if (base + step) <= n_leds else (n_leds - base)
                    rand_val = self._rand_pool[self._rand_idx]
                    self._rand_idx = (self._rand_idx + 1) & 255
                    pos = base + (rand_val % seg_len)
                    self.rgb_list[pos] = star_c
                    if seg_len >= 3:
                        if pos > base:
                            self.rgb_list[pos - 1] = neigh_c
                        if pos + 1 < base + seg_len:
                            self.rgb_list[pos + 1] = neigh_c
                    base += step
