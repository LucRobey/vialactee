"""
Coloured Middle Wave Mode
Divides the strip symmetrically from the center outwards into frequency band sections.
Pre-allocates all scratch arrays in __init__ for zero-allocation performance.
Modulates center expansion with ctx.energy and ctx.spectral_tilt.
Harmonized with GlobalMoodManager mood_colors.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Coloured_middle_wave_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.middle: int = self.nb_of_leds // 2
        self.half_len: int = self.middle + 1
        self.nb_bands: int = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8

        # Pre-allocate all scratch arrays (ZERO runtime heap allocation)
        self.pos_array: np.ndarray = np.arange(self.half_len, dtype=np.float64)
        self.fractions: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.float_band_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.lower_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.int32)
        self.upper_idxs: np.ndarray = np.zeros(self.half_len, dtype=np.int32)
        self.blend_factors: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.local_powers: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.target_colors: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)
        self.target_half: np.ndarray = np.zeros((self.half_len, 3), dtype=np.float64)
        self.t_mid: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.t_high: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.t_inv: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.t_diff: np.ndarray = np.zeros(self.half_len, dtype=np.float64)
        self.t_scratch: np.ndarray = np.zeros(self.half_len, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        mood = self.mood_colors

        # 1. Modulate center expansion with ctx.energy and ctx.spectral_tilt
        expansion_factor = float(np.clip(0.5 + 0.7 * energy - 0.3 * tilt, 0.25, 2.0))
        denom = max(1.0, float(self.half_len) * expansion_factor)
        np.divide(self.pos_array, denom, out=self.fractions)
        np.clip(self.fractions, 0.0, 1.0, out=self.fractions)

        # 2. Vectorized Band Index Interpolation
        np.multiply(self.fractions, self.nb_bands - 1, out=self.float_band_idxs)
        np.floor(self.float_band_idxs, out=self.lower_idxs, casting='unsafe')
        np.clip(self.lower_idxs + 1, 0, self.nb_bands - 1, out=self.upper_idxs)
        np.subtract(self.float_band_idxs, self.lower_idxs, out=self.blend_factors)

        bands = getattr(self.listener, "_delayed_asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_bands:
            bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_bands:
            bands = np.zeros(self.nb_bands)

        vol_lowers = bands[self.lower_idxs]
        vol_uppers = bands[self.upper_idxs]
        np.subtract(vol_uppers, vol_lowers, out=self.local_powers)
        np.multiply(self.local_powers, self.blend_factors, out=self.local_powers)
        np.add(self.local_powers, vol_lowers, out=self.local_powers)

        # 3. Vectorized Color Gradient from mood_colors
        # Bass (center) -> mood[0], Mid -> mood[1], Treble (outer) -> mood[2]
        np.multiply(self.fractions, 2.0, out=self.t_mid)
        np.clip(self.t_mid, 0.0, 1.0, out=self.t_mid)
        np.subtract(self.fractions, 0.5, out=self.t_high)
        np.multiply(self.t_high, 2.0, out=self.t_high)
        np.clip(self.t_high, 0.0, 1.0, out=self.t_high)

        np.subtract(1.0, self.t_mid, out=self.t_inv)
        np.subtract(self.t_mid, self.t_high, out=self.t_diff)

        np.multiply(self.t_inv, self.local_powers, out=self.t_inv)
        np.multiply(self.t_diff, self.local_powers, out=self.t_diff)
        np.multiply(self.t_high, self.local_powers, out=self.t_high)

        m0 = mood[0]
        m1 = mood[1]
        m2 = mood[2]
        for c in range(3):
            tc = self.target_colors[:, c]
            np.multiply(self.t_inv, float(m0[c]), out=tc)
            np.multiply(self.t_diff, float(m1[c]), out=self.t_scratch)
            np.add(tc, self.t_scratch, out=tc)
            np.multiply(self.t_high, float(m2[c]), out=self.t_scratch)
            np.add(tc, self.t_scratch, out=tc)

        np.clip(self.target_colors, 0.0, 255.0, out=self.target_colors)

        # 4. Symmetrical segment smoothing
        np.multiply(self.target_colors, 0.5, out=self.target_half)

        right_start = self.middle
        right_end = min(self.nb_of_leds - 1, self.middle + self.half_len - 1)
        right_len = right_end - right_start + 1
        if right_len > 0:
            view_r = self.rgb_list[right_start:right_end + 1]
            np.multiply(view_r, 0.5, out=view_r, casting='unsafe')
            np.add(view_r, self.target_half[:right_len], out=view_r, casting='unsafe')

        left_end = self.middle - 1
        left_start = max(0, self.middle - self.half_len + 1)
        left_len = left_end - left_start + 1
        if left_len > 0:
            view_l = self.rgb_list[left_start:left_end + 1]
            np.multiply(view_l, 0.5, out=view_l, casting='unsafe')
            np.add(view_l, self.target_half[left_len:0:-1], out=view_l, casting='unsafe')
