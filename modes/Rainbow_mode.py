"""
Rainbow Mode
Continuous smooth rainbow spectrum distributed across the strip.
Modulates base intensity and pulse sharpness by ctx.scene:
Pastel drift in CHILL, punchy percussive decay in GROOVE, and saturated burst on DROP_IMPACT.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
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

        # Precomputed vectors to avoid calculating them every frame (ZERO runtime heap allocation)
        self.led_indices: np.ndarray = np.arange(self.nb_of_leds, dtype=np.float64)
        self.hues: np.ndarray = self.minimum_hue + (self.maximum_hue - self.minimum_hue) * (self.led_indices / max(1.0, float(self.nb_of_leds)))
        self.active_hues: np.ndarray = np.copy(self.hues)
        self.sats: np.ndarray = np.ones(self.nb_of_leds, dtype=np.float64)
        self.drift_offset: float = 0.0

        self.low_margins: np.ndarray = (self.led_indices / self.delta_margin).astype(np.int32)
        self.high_margins: np.ndarray = np.clip(self.low_margins + 1, 0, self.nb_of_fft_band - 1)
        self.position_coefs: np.ndarray = 1.0 - (self.led_indices / self.delta_margin - self.low_margins)

        self.fft_bands_array: np.ndarray = np.zeros(self.nb_of_fft_band, dtype=np.float64)
        self.band_energy: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.intensities: np.ndarray = np.zeros(self.nb_of_leds, dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.int32)
        self.base_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        self.target_float_rgb: np.ndarray = np.zeros((self.nb_of_leds, 3), dtype=np.float64)
        if self.nb_of_leds > 0:
            RGB_HSV.fromHSV_toRGB_vectorized(self.hues, 1.0, 1.0, out=self.target_rgb)
            self.base_rgb[:] = self.target_rgb

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        scene = getattr(ctx, "scene", None)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.5))
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"

        delayed_bands = getattr(self.listener, "_delayed_asserved_fft_band", None)
        if delayed_bands is None or len(delayed_bands) < self.nb_of_fft_band:
            delayed_bands = getattr(self.listener, "asserved_fft_band", None)
        if delayed_bands is None or len(delayed_bands) < self.nb_of_fft_band:
            delayed_bands = np.zeros(self.nb_of_fft_band)

        self.fft_bands_array[:] = delayed_bands[:self.nb_of_fft_band]
        b_low = self.fft_bands_array[self.low_margins]
        b_high = self.fft_bands_array[self.high_margins]
        np.multiply(self.position_coefs, b_low, out=self.band_energy)
        self.band_energy += (1.0 - self.position_coefs) * b_high
        band_energy = self.band_energy

        # 1. Modulate base intensity, pulse sharpness, and drift by ctx.scene
        if is_drop:
            # Saturated burst on DROP_IMPACT
            self.active_hues[:] = self.hues
            self.sats.fill(1.0)
            self.intensities.fill(1.0)
        elif scene == "CHILL":
            # Pastel drift in CHILL
            self.drift_offset = (self.drift_offset + dt * 0.04) % 1.0
            np.add(self.hues, self.drift_offset, out=self.active_hues)
            np.mod(self.active_hues, 1.0, out=self.active_hues)
            self.sats.fill(0.55)  # Soft pastel saturation
            sine_breath = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase))
            base_int = self.intensity_base * (0.8 + 0.4 * sine_breath)
            np.multiply(self.intensity_mult * 0.5 * energy, band_energy, out=self.intensities)
            self.intensities += base_int
        else:
            # Punchy in GROOVE / BUILDUP
            self.active_hues[:] = self.hues
            self.sats.fill(1.0)
            decay = (1.0 - phase) ** 2.2
            rhythmic_drive = 0.35 * band_energy + 0.65 * (energy * decay)
            np.multiply(self.intensity_mult, rhythmic_drive, out=self.intensities)
            self.intensities += self.intensity_base

        np.clip(self.intensities, 0.0, 1.0, out=self.intensities)
        if scene == "CHILL":
            RGB_HSV.fromHSV_toRGB_vectorized(self.active_hues, self.sats, self.intensities, out=self.target_rgb)
        else:
            np.multiply(self.base_rgb, self.intensities[:, None], out=self.target_float_rgb)
            np.copyto(self.target_rgb, self.target_float_rgb, casting='unsafe')
        self.smooth_vectorized(self.smooth_ratio, self.target_rgb)