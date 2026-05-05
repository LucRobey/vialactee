import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import random
import numpy as np
import time

class Magnetic_ball_mode(Mode.Mode):

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        self.ball_pos = float(self.nb_of_leds / 2)
        self.ball_speed = 0.0
        self.ball_size = 4
        
        self.friction = 0.96 # Multiplier applied per frame
        self.gravity_well = self.nb_of_leds / 2 # Slowly pulls it back to the center
        self.gravity_strength = 0.05
        
        self.hue = random.uniform(0.0, 1.0)
        self.last_beat_count = 0
        
    def run(self):
        power = self.listener.asserved_total_power
        
        # Audio injects chaotic momentum/acceleration on beats
        if self.listener.beat_count != self.last_beat_count:
            self.last_beat_count = self.listener.beat_count
            
            # Change hue softly
            self.hue = (self.hue + 0.05) % 1.0
            
            # Kick it in a random direction with force proportional to audio power
            kick_direction = random.choice([-1.0, 1.0])
            kick_force = power * (self.nb_of_leds * 0.15) # 15% of strip length max kick
            self.ball_speed += kick_direction * kick_force
            
        # Add a magnetic pull towards the center if no sound is pushing it
        dist_to_center = self.gravity_well - self.ball_pos
        self.ball_speed += dist_to_center * self.gravity_strength
        
        # Apply speed to position
        self.ball_pos += self.ball_speed
        
        # Apply friction
        self.ball_speed *= self.friction
        
        # Wall collision detection (perfect elastic bounce)
        if self.ball_pos < 0:
            self.ball_pos_pos = 0.1
            self.ball_speed = abs(self.ball_speed) * 0.9 # bounce with energy loss
        elif self.ball_pos >= self.nb_of_leds:
            self.ball_pos = self.nb_of_leds - 1.1
            self.ball_speed = -abs(self.ball_speed) * 0.9
            
        # Draw the ball
        center_idx = int(self.ball_pos)
        
        # Size grows dynamically with volume
        dynamic_size = int(self.ball_size + (power * 4))
        start_idx = max(0, center_idx - dynamic_size)
        end_idx = min(self.nb_of_leds - 1, center_idx + dynamic_size)
        
        # Solidly lit center to simulate the physical mass
        rgb = RGB_HSV.fromHSV_toRGB(self.hue, 1.0, 1.0)
        self.smooth_segment_vectorized(0.7, start_idx, end_idx, rgb)
        
        # Everything else slowly fades for a motion blur effect
        if start_idx > 0:
             self.fade_to_black_segment_vectorized(0.3, 0, start_idx - 1)
        if end_idx < self.nb_of_leds - 1:
             self.fade_to_black_segment_vectorized(0.3, end_idx + 1, self.nb_of_leds - 1)
             
