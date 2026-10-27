"""
Rainbow Mode
Continuous smooth rainbow spectrum distributed across the strip with uninterrupted hue drift.
Never branches on ctx.scene (eliminating the snap back to 0.0 when leaving CHILL and the 1.5s
flat override on DROP_IMPACT). Modulates intensity continuously with band_energy and beat_pulse(),
while mood_pace and mood_accent gently nudge drift speed and highlight warmth.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import utils.colors as colors


class Rainbow_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "smoothRatio",
                "label": "Smoothing",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "attr": "smooth_ratio",
            },
            {
                "key": "intensityBase",
                "label": "Base Intensity",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.1,
                "attr": "intensity_base",
            },
            {
                "key": "intensityMultiplier",
                "label": "Intensity Boost",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 2.0,
                "step": 0.05,
                "default": 0.9,
                "attr": "intensity_mult",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.nb_of_fft_band: int = getattr(self.listener, "nb_of_fft_band", 8) if self.listener is not None else 8
        self.delta_margin: float = float(self.nb_of_leds) / max(1.0, float(self.nb_of_fft_band - 1))

        self.minimum_hue: float = colors.red_hue
        self.maximum_hue: float = colors.blue_hue

        self.smooth_ratio: float = float(infos.get("rainbow_smooth_ratio", infos.get("smoothRatio", 0.5)))
        self.intensity_base: float = float(infos.get("rainbow_intensity_base", infos.get("intensityBase", 0.1)))
        self.intensity_mult: float = float(infos.get("rainbow_intensity_mult", infos.get("intensityMultiplier", 0.9)))

        # Precomputed vectors and 256-entry rainbow LUT (ZERO runtime heap allocation)
        self.led_indices: np.ndarray = np.arange(self.nb_of_leds, dtype=np.float64)
        self.hues: np.ndarray = self.minimum_hue + (self.maximum_hue - self.minimum_hue) * (self.led_indices / max(1.0, float(self.nb_of_leds)))
        self.active_hues: np.ndarray = np.copy(self.hues)
        self.lut_idx: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.intp)
        lut_hues = np.linspace(0.0, 1.0, 256, endpoint=False)
        self.rainbow_lut: np.ndarray = RGB_HSV.fromHSV_toRGB_vectorized(lut_hues, 1.0, 1.0).astype(np.float64)
        self.drift_offset: float = self.segment_phase_offset

        self.low_margins: np.ndarray = (self.led_indices / self.delta_margin).astype(np.int32)
        self.high_margins: np.ndarray = np.clip(self.low_margins + 1, 0, self.nb_of_fft_band - 1)
        self.position_coefs: np.ndarray = 1.0 - (self.led_indices / self.delta_margin - self.low_margins)

        self.fft_bands_array: np.ndarray = np.zeros(self.nb_of_fft_band, dtype=np.float64)
        self.band_energy: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.intensities: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.int32)
        self.base_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.target_float_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        dt = self.dt
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.5))

        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) < self.nb_of_fft_band:
            self.fft_bands_array.fill(0.0)
        else:
            self.fft_bands_array[:] = bands[:self.nb_of_fft_band]

        b_low = self.fft_bands_array[self.low_margins]
        b_high = self.fft_bands_array[self.high_margins]
        np.multiply(self.position_coefs, b_low, out=self.band_energy)
        self.band_energy += (1.0 - self.position_coefs) * b_high

        # 1. Continuous hue drift in all scenes (scaled smoothly by mood_pace)
        self.drift_offset = (self.drift_offset + dt * 0.04 * self.mood_pace) % 1.0
        np.add(self.hues, self.drift_offset, out=self.active_hues)
        np.mod(self.active_hues, 1.0, out=self.active_hues)
        np.multiply(self.active_hues, 255.0, out=self.active_hues)
        self.lut_idx[:] = self.active_hues
        np.take(self.rainbow_lut, self.lut_idx, axis=0, out=self.base_rgb, mode="clip")

        # 2. Continuous intensity from spectrum + confidence-blended beat_pulse()
        pulse = self.beat_pulse()
        np.multiply(self.band_energy, 0.40, out=self.intensities)
        self.intensities += 0.60 * (0.35 * energy + 0.65 * pulse)
        np.multiply(self.intensities, self.intensity_mult, out=self.intensities)
        self.intensities += self.intensity_base * (0.75 + 0.25 * pulse)
        np.clip(self.intensities, 0.0, 1.0, out=self.intensities)

        np.multiply(self.base_rgb, self.intensities[:, None], out=self.target_float_rgb)
        accent = self.mood_accent * 0.35
        if accent > 0.001:
            hi = self.highlight_color
            inv_acc = 1.0 - accent
            for c in range(3):
                self.target_float_rgb[:, c] = inv_acc * self.target_float_rgb[:, c] + accent * float(hi[c]) * self.intensities

        np.copyto(self.target_rgb, self.target_float_rgb, casting="unsafe")
        self.smooth_vectorized(self.smooth_ratio, self.target_rgb)
