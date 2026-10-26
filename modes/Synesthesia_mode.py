"""
Synesthesia Mode
Maps musical harmony directly to light color using a 12-dimensional chromagram pitch analysis.
Modulates harmonic wash with ctx.energy, self.beat_pulse(), and a subtle traveling spatial wave
so the strip breathes organically even during sustained chords or lost beat tracking.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV


class Synesthesia_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.fade_ratio: float = float(infos.get("synesthesia_fade_ratio", 0.20))
        self.brightness_multiplier: float = float(infos.get("synesthesia_brightness", 1.0))
        self.wave_phase: float = 0.0

        # Pre-compute trigonometric coordinates for the 12 chromatic pitches (C, C#, D...)
        self.angles: np.ndarray = 2.0 * np.pi * np.arange(12, dtype=np.float64) / 12.0
        self.x_components: np.ndarray = np.cos(self.angles)
        self.y_components: np.ndarray = np.sin(self.angles)

        # Pre-allocated scratch buffers (ZERO runtime heap allocation)
        self.hue_arr: np.ndarray = np.zeros(1, dtype=np.float64)
        self.sat_arr: np.ndarray = np.zeros(1, dtype=np.float64)
        self.val_arr: np.ndarray = np.zeros(1, dtype=np.float64)
        self.chord_rgb: np.ndarray = np.zeros((1, 3), dtype=np.int32)
        self.final_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.spatial_angles: np.ndarray = np.linspace(0.0, 2.0 * np.pi, max(1, self.nb_of_leds), dtype=np.float64)
        self.spatial_wave: np.ndarray = np.zeros(max(1, self.nb_of_leds), dtype=np.float64)
        self.target_rgb: np.ndarray = np.zeros((max(1, self.nb_of_leds), 3), dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        mood = self.mood_colors

        if is_silent:
            self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
            return

        chroma = getattr(self.listener, "smoothed_chroma_values", None)
        if chroma is None or len(chroma) < 12:
            chroma = getattr(self.listener, "chroma_values", None)

        pulse = self.beat_pulse(2.0)
        brightness = float(np.clip((0.55 * energy + 0.45 * pulse) * self.brightness_multiplier, 0.0, 1.0))

        total_chroma = float(np.sum(chroma)) if (chroma is not None and len(chroma) >= 12) else 0.0

        if total_chroma > 0.001:
            x = float(np.sum(chroma * self.x_components))
            y = float(np.sum(chroma * self.y_components))
            hue_angle = np.arctan2(y, x)
            hue = (hue_angle / (2.0 * np.pi)) % 1.0
            magnitude = float(np.sqrt(x ** 2 + y ** 2)) / total_chroma

            saturation = float(np.clip(magnitude * 1.40, 0.45, 1.0))
            self.hue_arr[0] = hue
            self.sat_arr[0] = saturation
            self.val_arr[0] = brightness
            RGB_HSV.fromHSV_toRGB_vectorized(self.hue_arr, self.sat_arr, self.val_arr, out=self.chord_rgb)

            m0 = mood[0]
            self.final_color[0] = 0.70 * float(self.chord_rgb[0, 0]) + 0.30 * float(m0[0]) * brightness
            self.final_color[1] = 0.70 * float(self.chord_rgb[0, 1]) + 0.30 * float(m0[1]) * brightness
            self.final_color[2] = 0.70 * float(self.chord_rgb[0, 2]) + 0.30 * float(m0[2]) * brightness
        else:
            m0 = mood[0]
            self.final_color[0] = float(m0[0]) * brightness
            self.final_color[1] = float(m0[1]) * brightness
            self.final_color[2] = float(m0[2]) * brightness

        # Blend mood_accent warmth toward highlight_color
        accent = self.mood_accent
        if accent > 0.001:
            hi = self.highlight_color
            inv_acc = 1.0 - accent
            for c in range(3):
                self.final_color[c] = inv_acc * self.final_color[c] + accent * float(hi[c]) * brightness

        # Subtle traveling spatial wave so the strip shimmers continuously
        self.wave_phase = (self.wave_phase + self.dt * 1.8 * self.mood_pace) % (2.0 * np.pi)
        n = self.nb_of_leds
        np.add(self.spatial_angles[:n], self.wave_phase, out=self.spatial_wave[:n])
        np.sin(self.spatial_wave[:n], out=self.spatial_wave[:n])
        np.multiply(self.spatial_wave[:n], 0.18, out=self.spatial_wave[:n])
        np.add(self.spatial_wave[:n], 0.82, out=self.spatial_wave[:n])

        np.multiply(self.spatial_wave[:n, None], self.final_color, out=self.target_rgb[:n])
        np.clip(self.target_rgb[:n], 0.0, 255.0, out=self.target_rgb[:n])

        effective_ratio = self.fade_ratio / max(0.5, self.mood_trail)
        self.smooth_segment_vectorized(effective_ratio, 0, n - 1, self.target_rgb[:n])
