import numpy as np
import utils.rgb_hsv as RGB_HSV
import modes.Mode as Mode

class Metronome_mode(Mode.Mode):
    def get_settings_schema(self):
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

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.brightness_multiplier = infos.get("metronome_brightness", 1.0)
        self.alternate_sub_beats = bool(infos.get("metronome_alternate_sub_beats", True))
        self.accent_color = str(infos.get("metronome_accent_color", "blue"))

    def _accent_rgb(self):
        accent_colors = {
            "blue": np.array([0.0, 0.0, 255.0]),
            "purple": np.array([180.0, 0.0, 255.0]),
            "red": np.array([255.0, 0.0, 0.0]),
            "green": np.array([0.0, 255.0, 0.0]),
        }
        return accent_colors.get(self.accent_color, accent_colors["blue"])

    def run(self):
        # Retrieve the continuous Phase-Locked Loop data
        phase = self.listener.beat_phase # 0.0 -> 1.0 continuously
        count = self.listener.beat_count
        
        # Alternate between White (beats) and Blue (sub-beats)
        if count % 2 == 0 or not self.alternate_sub_beats:
            base_color = np.array([255.0, 255.0, 255.0]) * self.brightness_multiplier
        else:
            base_color = self._accent_rgb() * self.brightness_multiplier
        
        # Flashing ADSR envelope: 
        # Peaks instantly at phase=0, then fades to black (0) by halfway through the phase
        flash_envelope = max(0.0, 1.0 - (phase * 2.0))
        
        # Power curve to make the strobe punchier
        brightness = (flash_envelope ** 1.5)
        
        active_color = base_color * brightness
        
        # Paint the entire bar instantaneously with the calculated color
        self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, active_color)
