import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import random
import numpy as np

class Extending_waves_mode(Mode.Mode):

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.middle = int(self.nb_of_leds / 2)
        # Array storing the color of each pixel on half the strip
        self.half_strip_history = np.zeros((self.middle + 1, 3))
        
        # We assign a static hue that maybe changes over extremely long times or on big drops
        self.current_hue = random.uniform(0.0, 1.0)
        self.time_tracker = 0
        
    def run(self):
        # Determine movement speed based on overall volume
        power = self.listener.asserved_total_power
        
        # Base speed is 1 pixel per frame. Loud music shifts faster (2-4 pixels).
        shift_amount = 1 + int(power * 3.0) 
        
        # Shift the array outwards
        if shift_amount > 0:
            self.half_strip_history = np.roll(self.half_strip_history, shift_amount, axis=0)
            self.half_strip_history[:shift_amount] = [0, 0, 0] # clear the new center
            
        # Is a beat hitting? Let's drop a new color wave in the center
        # We'll use the main beat confidence
        if self.listener.beat_count % 4 == 0 and self.listener.beat_phase < 0.1:
            # Change hue every 4 beats
            self.current_hue = (self.current_hue + 0.1) % 1.0
            
        brightness = self.listener.smoothed_total_power
        # Inject color at the center
        if brightness > 0.1: # Only register audible sound
            # We map 0-7 bands to make it react intensely to kicks
            color_rgb = RGB_HSV.fromHSV_toRGB(self.current_hue, 1.0, float(brightness))
            
            # Inject color at the center
            if shift_amount > 0:
                self.half_strip_history[:min(shift_amount, len(self.half_strip_history))] = color_rgb
                    
        # Render the half history symmetrically to the actual LEDs
        # Smooth injection logic prevents harsh pixelation on fast shifts
        
        self.smooth_segment_vectorized(0.5, self.middle, self.middle + self.middle - 1, self.half_strip_history[:self.middle])
        
        if self.middle > 0:
            left_view = self.half_strip_history[1:self.middle+1][::-1]
            end_mapping = self.middle - 1
            start_mapping = end_mapping - len(left_view) + 1
            if start_mapping >= 0:
                self.smooth_segment_vectorized(0.5, start_mapping, end_mapping, left_view)
            
        # Take care of the very last edge LED if the strip length is odd
        if self.nb_of_leds % 2 != 0:
            self.smooth(0.5, self.nb_of_leds - 1, tuple(self.half_strip_history[-1]))
