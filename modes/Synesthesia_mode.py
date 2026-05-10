import numpy as np
import utils.rgb_hsv as RGB_HSV
import modes.Mode as Mode

class Synesthesia_mode(Mode.Mode):
    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.fade_ratio = infos.get("synesthesia_fade_ratio", 0.2)
        self.brightness_multiplier = infos.get("synesthesia_brightness", 1.0)
        
        # Pre-compute trigonometric coordinates for the 12 chromatic pitches (C, C#, D...)
        # We spread the 12 notes evenly around the 360-degree color wheel (2*pi radians)
        self.angles = 2 * np.pi * np.arange(12) / 12.0
        self.x_components = np.cos(self.angles)
        self.y_components = np.sin(self.angles)

    def run(self):
        # 1. Grab the smoothed 12-dimensional chromagram
        chroma = self.listener.smoothed_chroma_values
        
        total_energy = np.sum(chroma)
        
        if total_energy > 0:
            # 2. Calculate the "Center of Mass" of the playing chord on the Hue Wheel
            # Example: A pure C note pulls the mass directly towards angle 0.
            # A C-Major chord (C, E, G) pulls the mass across 3 notes, blending the vectors.
            x = np.sum(chroma * self.x_components)
            y = np.sum(chroma * self.y_components)
            
            # 3. Pull the Hue (angle) and Saturation (distance from center)
            hue_angle = np.arctan2(y, x)
            
            # Map [-pi, pi] onto the [0.0, 1.0] HSV color wheel
            hue = (hue_angle / (2 * np.pi)) % 1.0
            
            # Magnitude drops if notes are perfectly opposing on the circle (dissonance/messiness)
            magnitude = np.sqrt(x**2 + y**2) / total_energy
            
            # Minimum saturation so it doesn't instantly wash out to solid white during heavy tracks
            saturation = np.clip(magnitude * 1.5, 0.4, 1.0)
            
            # 4. Use overall volume scaling for brightness
            asserv_total = self.listener._delayed_asserved_fft_band
            brightness = np.clip(np.sum(asserv_total) * 0.3 * self.brightness_multiplier, 0.0, 1.0)
            
            # Generate the true target color of the musical chord!
            color = RGB_HSV.fromHSV_toRGB_vectorized(hue, saturation, brightness)
            
            # Smooth the entire segment towards this new harmonic wash
            self.smooth_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1, color)
        else:
            # Fade to black smoothly if there is absolute silence
            self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
