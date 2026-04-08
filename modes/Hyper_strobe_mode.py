import numpy as np
import modes.Mode as Mode
import calculations.colors as colors

class Hyper_strobe_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        # High threshold so it only triggers on definitive, isolating kick drums
        self.flux_threshold = infos.get("strobe_flux_threshold", 0.7)
        self.decay_ratio = infos.get("strobe_decay_ratio", 0.3)
        self.listen_band = infos.get("strobe_listen_band", 1) # Generally band 0 or 1 captures the bass transients!
        
    def run(self):
        # Trigger an aggressive absolute whiteout on heavy kicks
        if self.listener.band_flux[self.listen_band] > self.flux_threshold:
            self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, colors.white)
        else:
            # Falloff smoothly tracking the ADSR decay envelope naturally via the ratio!
            self.fade_to_black_segment_vectorized(self.decay_ratio, 0, self.nb_of_leds - 1)
