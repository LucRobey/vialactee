import numpy as np
import calculations.rgb_hsv as RGB_HSV
import modes.Mode as Mode

class Plasma_fire_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.fade_ratio = infos.get("fire_fade_ratio", 0.3)
        self.height_multiplier = infos.get("fire_height_multiplier", 1.2)
        self.hues = np.linspace(0.0, 0.15, self.nb_of_leds)
        self.target_colors = np.zeros((self.nb_of_leds, 3), dtype=np.int32)
        
    def run(self):
        # Base fire height on the ADSR smoothed total track power
        power = self.listener.asserved_total_power * self.height_multiplier
        fire_height = int(np.clip(power * self.nb_of_leds, 0, self.nb_of_leds - 1))
        
        if fire_height > 0:
            # Map the entire vector of hues to an RGB matrix instantly
            RGB_HSV.fromHSV_toRGB_vectorized(self.hues[:fire_height], 1.0, 1.0, out=self.target_colors[:fire_height])
            
            # Flush the entire dynamic gradient to the strip
            self.smooth_segment_vectorized(0.8, 0, fire_height - 1, self.target_colors[:fire_height])
            
        # Seamlessly fade any left-over LEDs above the current fire height to black
        if fire_height < self.nb_of_leds:
            self.fade_to_black_segment_vectorized(self.fade_ratio, fire_height, self.nb_of_leds - 1)
