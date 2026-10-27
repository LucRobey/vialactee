"""
Proportion Rainbow Mode
Full rainbow gradient spanning the strip whose color regions scale with FFT band energy.
Pre-allocates cumulative hue scratch buffers in __init__ (zero heap allocations).
Modulates brightness and saturation continuously with ctx.energy and self.beat_pulse()
without branching on ctx.scene. Fades to black in silence.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Proportion_rainbow_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.minimum_hue: float = 0.0
        self.maximum_hue: float = 0.80
        self.nb_bands: int = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8

        count = max(1, self.nb_of_leds - 1)
        self.N: float = max(1.0, float(count) / max(1.0, float(self.nb_bands - 1)))

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.led_indices: np.ndarray = np.arange(count, dtype=np.float64)
        self.low_margins: np.ndarray = (self.led_indices / self.N).astype(np.int32)
        self.high_margins: np.ndarray = np.clip(self.low_margins + 1, 0, self.nb_bands - 1)
        self.position_coefs: np.ndarray = 1.0 - (self.led_indices / self.N - self.low_margins)

        self.fft_bands_array: np.ndarray = np.zeros(self.nb_bands, dtype=np.float64)
        self.interp_band: np.ndarray = np.zeros(count, dtype=np.float64)
        self.dhues: np.ndarray = np.zeros(count, dtype=np.float64)
        self.cum_dhues: np.ndarray = np.zeros(count, dtype=np.float64)
        self.hues_full: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        if self.nb_of_leds > 0:
            self.hues_full[-1] = self.maximum_hue
        self.hues: np.ndarray = self.hues_full[:max(0, self.nb_of_leds - 1)]
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.int32)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        # 1. Fade to black in silence
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        pulse = self.beat_pulse(2.0)

        # 2. Continuous confidence-blended brightness & saturation (no scene branching)
        val = float(np.clip(0.35 * energy + 0.65 * pulse, 0.0, 1.0))
        sat = float(np.clip(0.68 + 0.32 * energy - 0.25 * self.mood_accent, 0.40, 1.0))

        # 3. FFT Band Proportions
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_bands:
            self.fft_bands_array.fill(0.0)
        else:
            self.fft_bands_array[:] = bands[:self.nb_bands]

        if self.nb_of_leds > 1:
            sum_dhue = ((self.N + 1) / 2.0) * (self.fft_bands_array[0] + self.fft_bands_array[-1]) + self.N * float(np.sum(self.fft_bands_array[1:-1]))
            if sum_dhue < 1e-4:
                sum_dhue = 1.0

            b_low = self.fft_bands_array[self.low_margins]
            b_high = self.fft_bands_array[self.high_margins]
            np.multiply(self.position_coefs, b_low, out=self.interp_band)
            self.interp_band += (1.0 - self.position_coefs) * b_high
            np.multiply(self.interp_band, (self.maximum_hue - self.minimum_hue) / sum_dhue, out=self.dhues)

            # 4. Zero-allocation cumulative sum
            self.cum_dhues[0] = 0.0
            if len(self.dhues) > 1:
                np.cumsum(self.dhues[:-1], out=self.cum_dhues[1:])

            np.add(self.minimum_hue, self.cum_dhues, out=self.hues)

        self.hues_full[-1] = self.maximum_hue
        RGB_HSV.fromHSV_toRGB_vectorized(self.hues_full, sat, val, out=self.target_rgb)
        self.smooth_vectorized(0.5, self.target_rgb)
