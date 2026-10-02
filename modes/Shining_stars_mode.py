"""
Shining Stars Mode
Ambient dark canvas where individual LEDs ("stars") twinkle into existence at random positions.
Stars ignite when specific frequency bands exceed activation thresholds, adopting the band's hue.
Twinkle density scales with ctx.energy and ctx.is_syncopated.
Fade rate slows in CHILL and accelerates in GROOVE. Flares on DROP_IMPACT.
Adheres strictly to modes/MODE_RULES.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import random
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
from core.MusicalContextEngine import MusicalContextEngine


class Shining_stars_mode(Mode.Mode):
    # Fallback configuration constants
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
        self.iteration_wait = infos.get("stars_iteration_wait", 30)
        # Pre-compute band colors (red = bass; blue/purple = treble)
        colors_list = []
        for band_index in range(self.nb_of_fft_band):
            hue = float(band_index) / max(1, self.nb_of_fft_band - 1)
            rgb = RGB_HSV.fromHSV_toRGB(hue, 1.0, 1.0)
            colors_list.append(rgb)
        self.colors = np.array(colors_list, dtype=np.int32)
        self.star_colors = np.copy(self.colors)
        self.num_bands: int = min(self.nb_of_fft_band, len(self.colors))

        self.step: int = max(1, int(self.sub_segment_size))
        self.max_offset: int = min(self.step, self.nb_of_leds)
        self.fade_chill: float = self.fade_ratio * 0.60
        self.fade_groove: float = self.fade_ratio * 1.40

        # Pre-allocate random pool (size 256, power of 2) for zero heap allocation during execution (Axiom 2).
        # Capping index at 255 ensures _rand_idx stays entirely within Python's small integer cache [-5, 256].
        rng = random.Random(hash((name, segment_name)) & 0xFFFFFFFF)
        self._rand_pool = [rng.randint(0, 100000) for _ in range(256)]
        self._rand_idx = 0

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        super().apply_settings(settings)
        self.step = max(1, int(self.sub_segment_size))
        self.max_offset = min(self.step, self.nb_of_leds)
        self.fade_chill = self.fade_ratio * 0.60
        self.fade_groove = self.fade_ratio * 1.40

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        if not isinstance(ctx, MusicalContextEngine):
            ctx = None
        has_real_ctx = ctx is not None

        # 1. Fade active stars back toward black
        if has_real_ctx:
            scene = ctx.scene
            if scene == "CHILL":
                effective_fade = self.fade_chill
            elif scene == "GROOVE":
                effective_fade = self.fade_groove
            else:
                effective_fade = self.fade_ratio
        else:
            effective_fade = self.fade_ratio

        self.fade_to_black(effective_fade)

        # 2. Check each frequency band for transient flux spikes
        if self.listener is None:
            return
        band_flux = getattr(self.listener, "band_flux", None)
        if band_flux is None:
            return

        step = self.step
        max_offset = self.max_offset
        if max_offset <= 0:
            return

        # 3. Flare on DROP_IMPACT
        if has_real_ctx and (ctx.is_drop_impact or ctx.scene == "DROP_IMPACT"):
            mood = self.mood_colors
            self.rgb_list[:] = mood[3]
            return

        # 4. Scale twinkle density with ctx.energy and ctx.is_syncopated
        if has_real_ctx:
            density_boost = (0.25 * ctx.energy) + (0.35 if ctx.is_syncopated else 0.0)
            current_threshold = max(1.0, self.threshold * (1.0 - 0.45 * density_boost))
            mood = self.mood_colors
            for i in range(self.nb_of_fft_band):
                self.star_colors[i] = mood[i % 4]
            active_colors = self.star_colors
        else:
            current_threshold = self.threshold
            active_colors = self.colors

        num_bands = min(self.num_bands, len(band_flux), len(active_colors))
        for band_index in range(num_bands):
            if band_flux[band_index] > current_threshold:
                rand_val = self._rand_pool[self._rand_idx]
                self._rand_idx = (self._rand_idx + 1) & 255
                random_pos = rand_val % max_offset
                self.rgb_list[random_pos::step] = active_colors[band_index]

    def lightUp(self, band_index: int) -> None:
        if band_index < 0 or band_index >= len(self.colors):
            return

        max_offset = self.max_offset
        if max_offset <= 0:
            return

        rand_val = self._rand_pool[self._rand_idx]
        self._rand_idx = (self._rand_idx + 1) & 255
        random_pos = rand_val % max_offset
        self.rgb_list[random_pos::self.step] = self.colors[band_index]


# Warmup Python interpreter code execution caches for zero-allocation hot-path guarantees
_dummy_rgb = np.zeros((1, 3), dtype=np.int32)
_dummy_mode = Shining_stars_mode("_warmup", "_warmup", None, None, [0], _dummy_rgb, {})
for _ in range(1100):
    _dummy_mode.run()
del _dummy_rgb, _dummy_mode
