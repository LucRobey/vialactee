import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np

class Flying_ball_mode(Mode.Mode):

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.ball_position = self.nb_of_leds / 2.0
        self.color_memory = 90.0 # corresponds roughly to Green/Blue in old CHSV
        
        # Scaling weights for the 8 bands to isolate "bass" vs "treble" 
        # using the old `localAsservissement[a] = pow(0.5 + 0.5 * (a/15), 2)` scaled to 8
        self.band_weights = np.array([((0.5 + 0.5 * (i / 7.0)) ** 2) for i in range(8)])
        self.ball_size = 3 
        
    def run(self):
        # We square the band powers like the old physical C++ engine did
        squared_powers = (self.listener.asserved_fft_band * self.band_weights) ** 2
        
        # Multiply by indices to find the Center of Mass
        music_gravity_center = np.sum(np.arange(8) * squared_powers)
        sound_weight = np.sum(squared_powers)
        
        if sound_weight > 0:
            # Scale down to 0.0 - 1.0 range
            music_gravity_center = (music_gravity_center / sound_weight) / 7.0
        else:
            music_gravity_center = 0.5
            
        # Old math exaggerated the bounds
        music_gravity_center = music_gravity_center ** 1.5
        
        if music_gravity_center > 0.6: 
            music_gravity_center = 0.5 * (1.0 + music_gravity_center)
        elif music_gravity_center < 0.4:
            music_gravity_center *= 0.6
            
        # Smooth color and position
        power = self.listener.asserved_total_power
        self.color_memory += 0.35 * power * ((180.0 * music_gravity_center) - self.color_memory)
        self.ball_position += 0.15 * ((self.nb_of_leds * music_gravity_center) - self.ball_position)
        
        self.color_memory += 0.002 * (90.0 - self.color_memory)
        self.ball_position += 0.08 * ((self.nb_of_leds / 2.0) - self.ball_position)
        
        # Constrain ball position safely
        pos = int(np.clip(self.ball_position, 0, self.nb_of_leds - 1))
        
        # Convert color format, 180 mapped to somewhere between blue/purple
        # We will use normalized HSV `self.color_memory / 255.0`
        hue = np.clip((self.color_memory / 255.0) + 0.1, 0.0, 1.0)
        
        # Enforce minimum brightness for trail
        power_scaled = 0.5 * (0.5 * (power + 1.0) + power) 
        rgb = RGB_HSV.fromHSV_toRGB(hue, 1.0, power_scaled)
        
        width = int(self.ball_size)
        start_idx = max(0, pos - width)
        end_idx = min(self.nb_of_leds - 1, pos + width)
        
        # Draw the wings
        self.smooth_segment_vectorized(0.5, start_idx, end_idx, rgb)
        
        # Fade black everything else with a slight inertia fade for cool trails
        if start_idx > 0:
            self.fade_to_black_segment_vectorized(0.5, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
            self.fade_to_black_segment_vectorized(0.5, end_idx + 1, self.nb_of_leds - 1)
