import numpy as np
import modes.Mode as Mode
import utils.colors as colors

class Hyper_strobe_mode(Mode.Mode):
    def get_settings_schema(self):
        band_options = [
            {"label": f"Band {band_index + 1}", "value": band_index}
            for band_index in range(self.listener.nb_of_fft_band)
        ]
        return [
            {
                "key": "fluxThreshold",
                "label": "Trigger Threshold",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.7,
                "attr": "flux_threshold",
            },
            {
                "key": "decayRatio",
                "label": "Decay",
                "control": "slider",
                "valueType": "number",
                "min": 0.01,
                "max": 1.0,
                "step": 0.05,
                "default": 0.3,
                "attr": "decay_ratio",
            },
            {
                "key": "listenBand",
                "label": "Trigger Band",
                "control": "list",
                "valueType": "number",
                "integer": True,
                "default": 1,
                "options": band_options,
                "attr": "listen_band",
            },
        ]

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
