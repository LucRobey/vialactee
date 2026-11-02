"""
Barycentric Rainbow Mode
Displays a symmetrical rainbow gradient mirrored outward from the strip's center.
Driven by spectrum (LEAD="spectrum"): ctx.vertical_center shifts the center hue pivot and
per-band FFT energy (asserved_fft_band) modulates radial brightness from center (bass) to tips (treble).
self.beat_pulse() adds a faint rhythmic breath (SECONDARY=("beat",)), with zero level competition (Law 7).
Zero runtime heap allocations.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Bary_rainbow_mode(Mode.Mode):
    """Symmetrical center-mirrored rainbow whose center hue and radial brightness follow the spectrum.

    Lead: spectrum (centroid hue pivot + radial band brightness). Secondary: beat (faint breath). Macro: hue drift via mood_pace, saturation via mood_accent.
    """
    LEAD = "spectrum"
    SECONDARY = ("beat",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.nb_bands: int = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8
        mid = self.nb_of_leds // 2
        if self.nb_of_leds % 2 == 0:
            self.middle_index = [max(0, mid - 1), min(self.nb_of_leds - 1, mid)]
        else:
            self.middle_index = [mid, mid]

        self.hue_drift: float = self.segment_phase_offset

        # Pre-allocated scratch arrays (ZERO runtime heap allocation)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.int32)
        self.hues: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.vals: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.fft_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float64)

        left_len = self.middle_index[0]
        self.left_hues_base: np.ndarray = np.arange(left_len, dtype=np.float64) / max(1.0, float(left_len))
        self.left_hues: np.ndarray = self.hues[:left_len]

        right_len = max(0, self.nb_of_leds - (self.middle_index[1] + 1))
        if right_len > 0:
            self.right_led_indices_ratio: Optional[np.ndarray] = np.arange(1, right_len + 1, dtype=np.float64) / max(1.0, float(right_len))
            self.right_hues: Optional[np.ndarray] = self.hues[self.middle_index[1] + 1:self.nb_of_leds]
        else:
            self.right_led_indices_ratio = None
            self.right_hues = None

        # Precomputed radial distance [0.0 at center -> 1.0 at outer tips] mapped to FFT band indices
        center_pos = 0.5 * float(self.middle_index[0] + self.middle_index[1]) if self.nb_of_leds > 0 else 0.0
        half_span = max(1.0, center_pos, float(self.nb_of_leds - 1) - center_pos)
        radial_norm = np.abs(np.arange(self.nb_of_leds, dtype=np.float64) - center_pos) / half_span
        band_pos = np.clip(radial_norm * max(1.0, float(self.nb_bands - 1)), 0.0, max(0.0, float(self.nb_bands - 1)))
        self.low_band_idx: np.ndarray = band_pos.astype(np.intp)
        self.high_band_idx: np.ndarray = np.clip(self.low_band_idx + 1, 0, max(0, self.nb_bands - 1))
        self.band_coef: np.ndarray = 1.0 - (band_pos - self.low_band_idx)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        # 1. Fade to black when ctx.is_silent
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        # 2. Lead (spectrum): continuous center hue from spectral vertical_center + gentle macro drift
        self.hue_drift = (self.hue_drift + self.dt * 0.025 * self.mood_pace) % 1.0
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        drift_nudge = 0.05 * np.sin(2.0 * np.pi * self.hue_drift)
        middle_hue = float(np.clip(v_center * 0.84 + drift_nudge, 0.02, 0.84))

        # 3. Lead (spectrum) radial per-LED brightness + Secondary (beat) faint rhythmic breath
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_bands:
            self.fft_bands.fill(0.45)
        else:
            self.fft_bands[:] = bands[:self.nb_bands]

        b_low = self.fft_bands[self.low_band_idx]
        b_high = self.fft_bands[self.high_band_idx]
        np.multiply(self.band_coef, b_low, out=self.vals)
        self.vals += (1.0 - self.band_coef) * b_high

        pulse = self.beat_pulse(2.0)
        beat_breath = 0.86 + 0.14 * pulse
        np.multiply(self.vals, 0.84 * beat_breath, out=self.vals)
        self.vals += 0.16 * beat_breath
        np.clip(self.vals, 0.0, 1.0, out=self.vals)

        sat = float(np.clip(0.92 - 0.22 * self.mood_accent, 0.40, 1.0))

        # 4. Vectorize left, center, and right hues in a single contiguous buffer
        if self.middle_index[0] > 0:
            np.multiply(self.left_hues_base, middle_hue, out=self.left_hues)
        if self.middle_index[0] < self.nb_of_leds:
            self.hues[self.middle_index[0]] = middle_hue
        if self.middle_index[1] < self.nb_of_leds:
            self.hues[self.middle_index[1]] = middle_hue
        if self.right_hues is not None and self.right_led_indices_ratio is not None:
            np.multiply(self.right_led_indices_ratio, 0.85 - middle_hue, out=self.right_hues)
            np.add(self.right_hues, middle_hue, out=self.right_hues)

        RGB_HSV.fromHSV_toRGB_vectorized(self.hues, sat, self.vals, out=self.target_rgb)
        self.smooth_vectorized(self.alpha(14.0), self.target_rgb)
