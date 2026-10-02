"""
Metronome Mode
Rhythm visualization lock-stepped to the Anticipation Flywheel beat tracker.
Modulates flash sharpness by ctx.beat_trust and dissolves into smooth sine breathing in CHILL or lost beat.
Fades to black in silence. Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Metronome_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "brightnessMultiplier",
                "label": "Brightness",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 2.0,
                "step": 0.1,
                "default": 1.0,
                "attr": "brightness_multiplier",
            },
            {
                "key": "alternateSubBeats",
                "label": "Alternate Sub-Beats",
                "control": "switch",
                "valueType": "boolean",
                "default": True,
                "attr": "alternate_sub_beats",
            },
            {
                "key": "accentColor",
                "label": "Accent Color",
                "control": "list",
                "valueType": "string",
                "default": "blue",
                "options": [
                    {"label": "Blue", "value": "blue"},
                    {"label": "Purple", "value": "purple"},
                    {"label": "Red", "value": "red"},
                    {"label": "Green", "value": "green"},
                ],
                "attr": "accent_color",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.brightness_multiplier = float(infos.get("metronome_brightness", infos.get("brightnessMultiplier", 1.0)))
        self.alternate_sub_beats = bool(infos.get("metronome_alternate_sub_beats", infos.get("alternateSubBeats", True)))
        self.accent_color = str(infos.get("metronome_accent_color", infos.get("accentColor", "blue")))

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.base_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.active_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.custom_accents: Dict[str, np.ndarray] = {
            "blue": np.array([0.0, 100.0, 255.0], dtype=np.float64),
            "purple": np.array([180.0, 0.0, 255.0], dtype=np.float64),
            "red": np.array([255.0, 30.0, 0.0], dtype=np.float64),
            "green": np.array([57.0, 255.0, 20.0], dtype=np.float64),
        }

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        count = int(getattr(self.listener, "beat_count", 0))
        mood = self.mood_colors

        if ctx is not None:
            if ctx.is_silent:
                self.fade_to_black_segment_vectorized(0.20, 0, self.nb_of_leds - 1)
                return

            trust = float(ctx.beat_trust)
            scene = getattr(ctx, "scene", None)
            is_chill = bool(scene == "CHILL" or trust < 0.35)
            energy = float(ctx.energy)

            # Modulate flash sharpness by ctx.beat_trust
            sharpness = 1.0 + 3.0 * trust
            flash_env = (max(0.0, 1.0 - (phase * 2.0))) ** sharpness

            # Sine breathing in CHILL or lost beat
            if is_chill:
                sine_breath = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase - (np.pi / 2.0)))
                effective_val = (trust * flash_env) + ((1.0 - trust) * sine_breath)
                effective_val = max(0.0, min(1.0, effective_val * (0.4 + 0.6 * energy)))
            else:
                effective_val = flash_env

            # Pick base color from mood_colors without heap allocation
            if count % 2 == 0 or not self.alternate_sub_beats:
                self.base_color[:] = mood[3]  # Highlight downbeat
            else:
                self.base_color[:] = mood[2]  # Accent sub-beat

            np.multiply(self.base_color, effective_val * self.brightness_multiplier, out=self.active_color)
            self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.active_color)
        else:
            flash_env = (max(0.0, 1.0 - (phase * 2.0))) ** 1.5
            if count % 2 == 0 or not self.alternate_sub_beats:
                self.base_color[:] = mood[3]
            else:
                self.base_color[:] = self.custom_accents.get(self.accent_color, mood[2])
            np.multiply(self.base_color, flash_env * self.brightness_multiplier, out=self.active_color)
            self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.active_color)
