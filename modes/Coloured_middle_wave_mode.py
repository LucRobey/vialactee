"""
Coloured Middle Wave Mode
Divides the strip symmetrically from the center outwards into frequency band sections.
Pre-allocates all scratch arrays in __init__ for zero-allocation performance.
Modulates center expansion with ctx.energy, self.beat_pulse(), ctx.spectral_tilt, and mood_pace.
Harmonized with the mood sector's mood_colors and mood_accent.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Coloured_middle_wave_mode(Mode.Mode):
    """Center-mirrored frequency band equalizer from bass heart to treble tips.

    Lead: spectrum (band sections). Secondary: beat (zoom, modest). Macro: palette.
    """
    LEAD = "spectrum"
    SECONDARY = ("beat",)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle: int = self.nb_of_leds // 2
        self.half_len: int = self.middle + 1
        self.nb_bands: int = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8

        # Pre-allocate all scratch arrays (ZERO runtime heap allocation - AXIOM-02)
        self.pos_array: np.ndarray = np.arange(self.half_len, dtype=np.float32)
        self.fractions: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.float_band_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.lower_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.int32)
        self.upper_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.int32)
        self.blend_factors: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.local_powers: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.vol_lowers: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.vol_uppers: np.ndarray = np.zeros(self.half_len, dtype=np.float32)
        self.mood_weights: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self.mood_3x3: np.ndarray = np.zeros((3, 3), dtype=np.float32)
        self.target_colors: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float32)
        self._fallback_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float32)

        self.right_start = self.middle
        self.right_end = min(self.nb_of_leds - 1, self.middle + self.half_len - 1)
        self.right_len = max(0, self.right_end - self.right_start + 1)

        self.left_end = self.middle - 1
        self.left_start = max(0, self.middle - self.half_len + 1)
        self.left_len = max(0, self.left_end - self.left_start + 1)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.30, 0, self.nb_of_leds - 1)
            return

        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        mood = self.mood_colors

        # 1. Modulate center expansion with energy, beat_pulse(), spectral_tilt, and mood_pace
        pulse = self.beat_pulse()
        raw_exp = (0.45 + 0.50 * energy + 0.25 * pulse - 0.30 * tilt) * self.mood_pace
        expansion_factor = max(0.25, min(2.0, raw_exp))
        denom = max(1.0, float(self.half_len) * expansion_factor)
        np.divide(self.pos_array, denom, out=self.fractions)
        self.fractions.clip(0.0, 1.0, out=self.fractions)

        # 2. Vectorized Band Index Interpolation (zero-allocation np.take)
        np.multiply(self.fractions, self.nb_bands - 1, out=self.float_band_idxs)
        np.floor(self.float_band_idxs, out=self.lower_idxs, casting="unsafe")
        np.add(self.lower_idxs, 1, out=self.upper_idxs)
        self.upper_idxs.clip(0, self.nb_bands - 1, out=self.upper_idxs)
        np.subtract(self.float_band_idxs, self.lower_idxs, out=self.blend_factors)

        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_bands:
            bands = self._fallback_bands

        np.take(bands, self.lower_idxs, out=self.vol_lowers)
        np.take(bands, self.upper_idxs, out=self.vol_uppers)
        np.subtract(self.vol_uppers, self.vol_lowers, out=self.local_powers)
        np.multiply(self.local_powers, self.blend_factors, out=self.local_powers)
        np.add(self.local_powers, self.vol_lowers, out=self.local_powers)

        # 3. Vectorized Color Gradient from mood_colors via BLAS matmul
        t_mid = self.mood_weights[:, 1]
        np.multiply(self.fractions, 2.0, out=t_mid)
        t_mid.clip(0.0, 1.0, out=t_mid)

        t_high = self.mood_weights[:, 2]
        np.subtract(self.fractions, 0.5, out=t_high)
        np.multiply(t_high, 2.0, out=t_high)
        t_high.clip(0.0, 1.0, out=t_high)

        t_inv = self.mood_weights[:, 0]
        np.subtract(1.0, t_mid, out=t_inv)
        np.subtract(t_mid, t_high, out=t_mid)

        np.multiply(t_inv, self.local_powers, out=t_inv)
        np.multiply(t_mid, self.local_powers, out=t_mid)
        np.multiply(t_high, self.local_powers, out=t_high)

        self.mood_3x3[:] = mood[:3]
        accent = self.mood_accent
        if accent > 0.001:
            hi = self.highlight_color
            inv_acc = 1.0 - accent
            for c in range(3):
                self.mood_3x3[:, c] = inv_acc * self.mood_3x3[:, c] + accent * float(hi[c])
        np.matmul(self.mood_weights, self.mood_3x3, out=self.target_colors)
        self.target_colors.clip(0.0, 255.0, out=self.target_colors)

        # 4. Symmetrical segment smoothing at full dynamic range (scaled by dt and mood_trail)
        ratio = float(np.clip(self.alpha(18.0) / max(0.5, self.mood_trail), 0.10, 0.85))
        if self.right_len > 0:
            self.smooth_segment_vectorized(ratio, self.right_start, self.right_end, self.target_colors[:self.right_len])
        if self.left_len > 0:
            self.smooth_segment_vectorized(ratio, self.left_start, self.left_end, self.target_colors[self.left_len:0:-1])
