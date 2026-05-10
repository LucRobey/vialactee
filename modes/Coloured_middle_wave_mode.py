import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import random

class Coloured_middle_wave_mode(Mode.Mode):

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.middle = int(self.nb_of_leds / 2)
        
        # We pre-calculate a Hue palette mapping for the 8 bands
        # Band 0 gets roughly red, band 7 gets purple
        self.band_hues = [float(i) / 8.0 for i in range(self.listener.nb_of_fft_band)]
        
    def run(self):
        # The logic: interpolate the 8 frequency bands spatially from the middle to the ends
        # Center = Bass (Band 0). Edges = Treble (Band 7).
        
        segment_half_len = float(self.nb_of_leds / 2.0)
        import numpy as np
        pos_array = np.arange(int(segment_half_len) + 1)
        fractions = pos_array / segment_half_len
        
        float_band_idxs = fractions * (self.listener.nb_of_fft_band - 1)
        lower_idxs = float_band_idxs.astype(np.int32)
        upper_idxs = np.clip(lower_idxs + 1, 0, self.listener.nb_of_fft_band - 1)
        blend_factors = float_band_idxs - lower_idxs
        
        vol_lowers = self.listener._delayed_asserved_fft_band[lower_idxs]
        vol_uppers = self.listener._delayed_asserved_fft_band[upper_idxs]
        local_powers = (vol_lowers * (1.0 - blend_factors)) + (vol_uppers * blend_factors)
        
        band_hues_arr = np.array(self.band_hues)
        hue_lowers = band_hues_arr[lower_idxs]
        hue_uppers = band_hues_arr[upper_idxs]
        local_hues = (hue_lowers * (1.0 - blend_factors)) + (hue_uppers * blend_factors)
        
        target_colors = np.zeros((len(pos_array), 3), dtype=np.int32)
        RGB_HSV.fromHSV_toRGB_vectorized(local_hues, 1.0, local_powers, out=target_colors)
        
        right_start = self.middle
        right_end = min(self.nb_of_leds - 1, self.middle + len(pos_array) - 1)
        right_len = right_end - right_start + 1
        self.smooth_segment_vectorized(0.5, right_start, right_end, target_colors[:right_len])
        
        left_end = self.middle - 1
        left_start = max(0, self.middle - len(pos_array) + 1)
        left_len = left_end - left_start + 1
        if left_len > 0:
            self.smooth_segment_vectorized(0.5, left_start, left_end, target_colors[1:left_len+1][::-1])
