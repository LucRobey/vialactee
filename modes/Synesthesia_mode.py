"""
Synesthesia Mode
Maps musical harmony directly to light color using a 12-dimensional chromagram pitch analysis.
Modulates harmonic wash with ctx.energy. Triggers smooth chord morph on ctx.is_structural_cut.
Base saturation and harmonic wash tied to GlobalMoodManager mood_colors.
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

        # Pre-compute trigonometric coordinates for the 12 chromatic pitches (C, C#, D...)
        self.angles: np.ndarray = 2.0 * np.pi * np.arange(12, dtype=np.float64) / 12.0
        self.x_components: np.ndarray = np.cos(self.angles)
        self.y_components: np.ndarray = np.sin(self.angles)

        # Pre-allocated scratch buffers (ZERO runtime heap allocation)
        self.hue_arr: np.ndarray = np.zeros(1, dtype=np.float64)
        self.sat_arr: np.zeros = np.zeros(1, dtype=np.float64)
        self.val_arr: np.zeros = np.zeros(1, dtype=np.float64)
        self.chord_rgb: np.ndarray = np.zeros((1, 3), dtype=np.int32)
        self.final_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        is_cut = bool(ctx.is_structural_cut if ctx is not None else False)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        mood = self.mood_colors

        if is_silent:
            self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
            return

        chroma = getattr(self.listener, "smoothed_chroma_values", None)
        if chroma is None or len(chroma) < 12:
            chroma = getattr(self.listener, "chroma_values", None)
        if chroma is None or len(chroma) < 12:
            chroma = np.zeros(12)

        total_chroma = float(np.sum(chroma))

        # 1. Modulate harmonic wash with ctx.energy
        brightness = float(np.clip(energy * self.brightness_multiplier, 0.0, 1.0))

        if total_chroma > 0.001:
            x = float(np.sum(chroma * self.x_components))
            y = float(np.sum(chroma * self.y_components))
            hue_angle = np.arctan2(y, x)
            hue = (hue_angle / (2.0 * np.pi)) % 1.0
            magnitude = float(np.sqrt(x ** 2 + y ** 2)) / total_chroma

            # Base saturation tied to chroma purity and mood harmony
            saturation = float(np.clip(magnitude * 1.40, 0.45, 1.0))

            self.hue_arr[0] = hue
            self.sat_arr[0] = saturation
            self.val_arr[0] = brightness
            RGB_HSV.fromHSV_toRGB_vectorized(self.hue_arr, self.sat_arr, self.val_arr, out=self.chord_rgb)

            # Harmonize with mood_colors: 70% chromatic chord, 30% curated mood palette
            m0 = mood[0]
            r = float(self.chord_rgb[0, 0])
            g = float(self.chord_rgb[0, 1])
            b = float(self.chord_rgb[0, 2])
            self.final_color[0] = 0.70 * r + 0.30 * float(m0[0]) * brightness
            self.final_color[1] = 0.70 * g + 0.30 * float(m0[1]) * brightness
            self.final_color[2] = 0.70 * b + 0.30 * float(m0[2]) * brightness
        else:
            m0 = mood[0]
            self.final_color[0] = float(m0[0]) * brightness
            self.final_color[1] = float(m0[1]) * brightness
            self.final_color[2] = float(m0[2]) * brightness

        # 2. Trigger smooth chord morph on ctx.is_structural_cut
        effective_ratio = 0.06 if is_cut else self.fade_ratio

        np.clip(self.final_color, 0.0, 255.0, out=self.final_color)
        self.smooth_segment_vectorized(effective_ratio, 0, self.nb_of_leds - 1, self.final_color)
