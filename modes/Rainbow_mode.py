import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import calculations.colors as colors
import time
import numpy as np
from typing import List, Dict, Any

class Rainbow_mode(Mode.Mode):
    
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Used to calculate the hue and the intensity of each pixel
        self.delta_margin = float(self.nb_of_leds) / (self.listener.nb_of_fft_band - 1)
        self.nb_of_fft_band = self.listener.nb_of_fft_band

        self.minimum_hue = colors.red_hue
        self.maximum_hue = colors.blue_hue
        
        # Extracted Magic Numbers
        self.smooth_ratio = float(infos.get("rainbow_smooth_ratio", 0.5))
        self.intensity_base = float(infos.get("rainbow_intensity_base", 0.1))
        self.intensity_mult = float(infos.get("rainbow_intensity_mult", 0.9))
        
        # Precomputed vectors to avoid calculating them every frame
        self.led_indices = np.arange(self.nb_of_leds)
        self.hues = self.minimum_hue + (self.maximum_hue - self.minimum_hue) * (self.led_indices / self.nb_of_leds)
        
        self.low_margins = (self.led_indices / self.delta_margin).astype(np.int32)
        self.high_margins = self.low_margins + 1
        
        # Secure high_margins
        self.high_margins = np.clip(self.high_margins, 0, self.nb_of_fft_band - 1)
        
        self.position_coefs = 1.0 - (self.led_indices / self.delta_margin - self.low_margins)

        # Preallocated arrays for GC pause avoidance
        self.fft_bands_array = np.zeros(self.nb_of_fft_band)
        self.intensities = np.zeros(self.nb_of_leds)
        self.target_rgb = np.zeros((self.nb_of_leds, 3), dtype=np.int32)

    def run(self):
        self.fft_bands_array[:] = self.listener.asserved_fft_band
        
        self.intensities[:] = self.intensity_base + self.intensity_mult * (
            self.position_coefs * self.fft_bands_array[self.low_margins] + 
            (1.0 - self.position_coefs) * self.fft_bands_array[self.high_margins]
        )
        
        RGB_HSV.fromHSV_toRGB_vectorized(self.hues, 1.0, self.intensities, out=self.target_rgb)
        
        self.smooth_vectorized(self.smooth_ratio, self.target_rgb)