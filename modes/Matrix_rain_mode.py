import numpy as np
import modes.Mode as Mode
import calculations.colors as colors

class Matrix_rain_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.flux_threshold = infos.get("rain_flux_threshold", 0.5)
        self.fade_ratio = infos.get("rain_fade_ratio", 0.15)
        self.rain_color = infos.get("rain_color", colors.green)
        self.listen_band = infos.get("rain_listen_band", -1) # Default highest band

    def run(self):
        # 1. Shift down by 1 index (falling effect) using safe numpy assignment
        self.rgb_list[1:] = self.rgb_list[:-1]
        
        # 2. Decay the entire strip proportionally to create falling tails
        self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
        
        # 3. Spawn a new bright raindrop if the high-frequency flux peaks (snares/hi-hats)
        if self.listener.band_flux[self.listen_band] > self.flux_threshold:
            self.smooth(1.0, 0, self.rain_color)
