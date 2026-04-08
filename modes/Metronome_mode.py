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
        
        # Ping-pong scanning behavior based on the exact beat
        if count % 2 == 0:
            pos = phase # Draw Left to Right on even beats
        else:
            pos = 1.0 - phase # Draw Right to Left on odd beats
            
        # Identify the exact physical LED index of the sweeping head
        head_index = int(pos * (self.nb_of_leds - 1))
        
        # Every subsequent beat shifts the hue automatically
        hue = (count * 0.15) % 1.0
        head_color = RGB_HSV.fromHSV_toRGB_vectorized(hue, 1.0, self.brightness_multiplier)[0]
        
        # The background acts as a physical grid downbeat accent
        # It flares up slightly on the exact beat (phase=0), then fades
        bg_flash = max(0.0, 1.0 - (phase * 4)) # Visible only for the first 25% of the beat interval
        bg_brightness = (bg_flash ** 2) * 0.3 * self.brightness_multiplier
        bg_color = RGB_HSV.fromHSV_toRGB_vectorized(hue, 1.0, bg_brightness)[0]
        
        # 1. Paint the background grid pulse smoothly
        self.smooth_segment_vectorized(0.3, 0, self.nb_of_leds - 1, bg_color)
        
        # 2. Hard draw the anticipating laser head 
        self.smooth(1.0, head_index, head_color) 
        
        # Add a subtle anti-aliased glow around the head to make it thicker and punchier
        if head_index > 0:
            self.smooth(0.8, head_index - 1, head_color)
        if head_index < self.nb_of_leds - 1:
            self.smooth(0.8, head_index + 1, head_color)
