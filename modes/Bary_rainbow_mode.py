import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import time

class Bary_rainbow_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        if (self.nb_of_leds%2 == 0):
            self.hasAMiddle = False
            self.middle_index = [int(self.nb_of_leds/2) , int(self.nb_of_leds/2 +1)]
        else:
             self.hasAMiddle = True
             self.middle_index = [int((self.nb_of_leds+1)/2) , int((self.nb_of_leds+1)/2)]
        
        #the maximum size of a side bar
        self.max_size = int((self.nb_of_leds+1)/2)
        
        self.left_hues_base = np.arange(self.middle_index[0]) / self.middle_index[0]
        if self.nb_of_leds > self.middle_index[1] + 1:
            self.right_led_indices_ratio = (np.arange(self.middle_index[1]+1, self.nb_of_leds) - self.middle_index[1]) / (self.nb_of_leds - self.middle_index[1])
            self.target_right = np.zeros((self.nb_of_leds - self.middle_index[1] - 1, 3), dtype=np.int32)
        else:
            self.right_led_indices_ratio = None
            
        self.target_left = np.zeros((self.middle_index[0], 3), dtype=np.int32)
    def run(self):
        fft_band_values = self.listener.smoothed_fft_band_values
        
        a = 0
        b = 0.0001
        
        for band_index in range(self.listener.nb_of_fft_band):
            a += fft_band_values[band_index] * band_index
            b += fft_band_values[band_index]
            
        middle_hue = np.min([(float(a)/b) / (self.listener.nb_of_fft_band-1),0.84])
        
        # Vectorize left side
        left_hues = self.left_hues_base * middle_hue
        RGB_HSV.fromHSV_toRGB_vectorized(left_hues, 1.0, 1.0, out=self.target_left)
        self.rgb_list[:self.middle_index[0]] = self.target_left
        
        # Center
        self.rgb_list[self.middle_index[0]] = RGB_HSV.fromHSV_toRGB(middle_hue,1.0,1.0)
        if self.middle_index[1] < self.nb_of_leds:
            self.rgb_list[self.middle_index[1]] = RGB_HSV.fromHSV_toRGB(middle_hue,1.0,1.0)
        
        # Vectorize right side
        if self.right_led_indices_ratio is not None:
            right_hues = middle_hue + (0.85 - middle_hue) * self.right_led_indices_ratio
            RGB_HSV.fromHSV_toRGB_vectorized(right_hues, 1.0, 1.0, out=self.target_right)
            self.rgb_list[self.middle_index[1]+1:self.nb_of_leds] = self.target_right