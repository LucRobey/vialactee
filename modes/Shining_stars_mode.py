"""
Shining Stars Mode
Ambient dark canvas where individual LEDs ("stars") twinkle into existence at random positions.
Stars ignite when specific frequency bands exceed activation thresholds, adopting the band's hue.
Active stars gradually fade back to black, creating a gentle celestial constellation effect.
Replicates across sub-segments to optimize computational overhead on long strips.
Adheres strictly to modes/MODE_RULES.md with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import random
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


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

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
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

        # Pre-allocate random pool (size 256, power of 2) for zero heap allocation during execution (Axiom 2).
        # Capping index at 255 ensures _rand_idx stays entirely within Python's small integer cache [-5, 256].
        rng = random.Random(hash((name, segment_name)) & 0xFFFFFFFF)
        self._rand_pool = [rng.randint(0, 100000) for _ in range(256)]
        self._rand_idx = 0

    def run(self):
        if self.nb_of_leds <= 0:
            return

        # 1. First fade active stars back toward black
        self.fade_to_black(self.fade_ratio)

        # 2. Check each frequency band for transient flux spikes
        if self.listener is None:
            return
        band_flux = getattr(self.listener, "band_flux", None)
        if band_flux is None:
            return

        step = max(1, int(self.sub_segment_size))
        max_offset = min(step, self.nb_of_leds)
        if max_offset <= 0:
            return

        num_bands = min(self.nb_of_fft_band, len(band_flux), len(self.colors))
        for band_index in range(num_bands):
            if band_flux[band_index] > self.threshold:
                rand_val = self._rand_pool[self._rand_idx]
                self._rand_idx = (self._rand_idx + 1) & 255
                random_pos = rand_val % max_offset
                self.rgb_list[random_pos::step] = self.colors[band_index]

    def lightUp(self, band_index: int):
        if band_index < 0 or band_index >= len(self.colors):
            return

        step = max(1, int(self.sub_segment_size))
        max_offset = min(step, self.nb_of_leds)
        if max_offset <= 0:
            return

        # Advance pre-allocated random pointer (zero heap allocation in render hot path)
        rand_val = self._rand_pool[self._rand_idx]
        self._rand_idx = (self._rand_idx + 1) & 255
        random_pos = rand_val % max_offset

        # Broadcast the star across sub-segments using step slicing
        self.rgb_list[random_pos::step] = self.colors[band_index]
