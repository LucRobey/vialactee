import numpy as np
import calculations.rgb_hsv as RGB_HSV
import modes.Mode as Mode

class Metronome_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.brightness_multiplier = infos.get("metronome_brightness", 1.0)

    def run(self):
        # Retrieve the continuous Phase-Locked Loop data
        phase = self.listener.beat_phase # 0.0 -> 1.0 continuously
        count = self.listener.beat_count
        
        # Alternate between White (beats) and Blue (sub-beats)
        if count % 2 == 0:
            base_color = np.array([255.0, 255.0, 255.0]) * self.brightness_multiplier
        else:
            base_color = np.array([0.0, 0.0, 255.0]) * self.brightness_multiplier
        
        # Flashing ADSR envelope: 
        # Peaks instantly at phase=0, then fades to black (0) by halfway through the phase
        flash_envelope = max(0.0, 1.0 - (phase * 2.0))
        
        # Power curve to make the strobe punchier
        brightness = (flash_envelope ** 1.5)
        
        active_color = base_color * brightness
        
        # Paint the entire bar instantaneously with the calculated color
        self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, active_color)
