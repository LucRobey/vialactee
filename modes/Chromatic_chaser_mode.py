import numpy as np
import utils.rgb_hsv as RGB_HSV
import modes.Mode as Mode

class Chromatic_chaser_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.position = 0.0
        self.speed = infos.get("chaser_speed", 2.0)
        self.direction = 1
        self.fade_ratio = infos.get("chaser_fade_ratio", 0.05)
        
    def run(self):
        # 1. Update the position of the laser head
        self.position += self.speed * self.direction
        
        # Bounce mechanism for the edges
        if self.position >= self.nb_of_leds - 1:
            self.position = self.nb_of_leds - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
            
        # 2. Derive the color dynamically dependent on the track's pitch gravity (Barycenter)
        fft_band_values = self.listener.smoothed_fft_band_values
        a = 0
        b = 0.0001
        for band_index in range(self.listener.nb_of_fft_band):
            a += fft_band_values[band_index] * band_index
            b += fft_band_values[band_index]
            
        middle_hue = np.min([(float(a)/b) / (self.listener.nb_of_fft_band-1), 0.84])
        color = RGB_HSV.fromHSV_toRGB(middle_hue, 1.0, 1.0)
        
        # 3. Apply the heavily saturated color to the head of the snake
        self.smooth(1.0, int(self.position), color)
        
        # 4. Fade Tails (Vectorized)
        self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
