import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import numpy as np
import time

class Proportion_rainbow_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        self.minimum_hue = 0.0
        self.maximum_hue = 0.8

        self.N = (self.nb_of_leds-1)/(self.listener.nb_of_fft_band-1)
        
        self.led_indices = np.arange(self.nb_of_leds - 1)
        self.low_margins = (self.led_indices / self.N).astype(np.int32)
        self.high_margins = self.low_margins + 1
        self.position_coefs = 1.0 - (self.led_indices / self.N - self.low_margins)
        
        self.fft_bands_array = np.zeros(self.listener.nb_of_fft_band)
        self.target_rgb = np.zeros((self.nb_of_leds - 1, 3), dtype=np.int32)
        self.hues = np.zeros(self.nb_of_leds - 1)
    def run(self):
        sum_dhue = ((self.N+1)/2) * (self.listener.asserved_fft_band[0]+self.listener.asserved_fft_band[-1]) + self.N * np.sum(self.listener.asserved_fft_band[1:-1])
        self.fft_bands_array[:] = self.listener.asserved_fft_band
        
        # Calculate dhues
        dhues = (self.maximum_hue - self.minimum_hue) * (
            self.position_coefs * self.fft_bands_array[self.low_margins] + 
            (1.0 - self.position_coefs) * self.fft_bands_array[self.high_margins]
        ) / sum_dhue
        
        # Calculate cumulative hues
        self.hues[:] = self.minimum_hue + np.cumsum(np.concatenate(([0], dhues[:-1])))
        
        RGB_HSV.fromHSV_toRGB_vectorized(self.hues, 1.0, 1.0, out=self.target_rgb)
        
        self.smooth_segment_vectorized(0.5, 0, self.nb_of_leds - 2, self.target_rgb)
        self.smooth(0.5, self.nb_of_leds - 1, RGB_HSV.fromHSV_toRGB(self.maximum_hue, 1.0, 1.0))