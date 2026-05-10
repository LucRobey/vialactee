import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import random
import numpy as np

class Static_wave_mode(Mode.Mode):

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.color_hue = random.uniform(0.0, 1.0)
        
        self.real_size = self.nb_of_leds / 4.0
        self.max_size = (self.nb_of_leds / 2.0) - 1
        self.middle = int(self.nb_of_leds / 2)
        
        self.size_int = int(self.real_size + 1)
        
    def run(self):
        # We average the lowest 2 bands out of 8 (which represents the low bass and kick)
        # Old code used 0-3 out of 16.
        valuef = (self.listener._delayed_asserved_fft_band[0] + self.listener._delayed_asserved_fft_band[1]) / 2.0
        
        self.real_size = 0.5 * (self.real_size + (valuef * self.max_size))
        if self.real_size >= self.max_size:
            self.real_size = self.max_size - 1
            
        if self.real_size > self.size_int:
            self.size_int = int(self.real_size + 1)
        if self.real_size < self.size_int - 1:
            self.size_int -= 0.2
            
        # Draw the static pulse symmetrically from the middle
        power = self.listener.asserved_total_power
        rgb = RGB_HSV.fromHSV_toRGB(self.color_hue, 1.0, power)
        
        current_len = int(self.real_size)
        
        start_idx = max(0, self.middle - current_len)
        end_idx = min(self.nb_of_leds - 1, self.middle + current_len)
        
        # Color the lit section
        self.smooth_segment_vectorized(0.5, start_idx, end_idx, rgb)
        
        # The moving limit boundaries visually pulse instantly to black then fade
        # to give a sharp cutoff feel like the C++ code *local_sorted_leds[middle + size] = CHSV(color, 0, power)
        boundary_p1 = min(self.nb_of_leds - 1, self.middle + int(self.size_int))
        boundary_p2 = max(0, self.middle - int(self.size_int))
        
        boundary_rgb = RGB_HSV.fromHSV_toRGB(self.color_hue, 0.0, power) # Saturation 0 is white
        self.smooth(0.5, boundary_p1, boundary_rgb)
        self.smooth(0.5, boundary_p2, boundary_rgb)
        
        # Erase everything past the size limit
        if boundary_p2 > 0:
             self.fade_to_black_segment_vectorized(0.5, 0, boundary_p2 - 1)
        if boundary_p1 < self.nb_of_leds - 1:
             self.fade_to_black_segment_vectorized(0.5, boundary_p1 + 1, self.nb_of_leds - 1)
