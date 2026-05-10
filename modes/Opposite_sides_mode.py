import modes.Mode as Mode
import utils.colors as colors
import utils.rgb_hsv as RGB_HSV
import time

class Opposite_sides_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        self.bass_hue = 0.0
        self.high_hue = 0.7

        self.bass_color = RGB_HSV.fromHSV_toRGB(self.bass_hue,1.0,1.0)
        self.high_color = RGB_HSV.fromHSV_toRGB(self.high_hue,1.0,1.0)
        
        self.middleSize = int(self.nb_of_leds/4)
        self.middle_start_index = int(3*self.nb_of_leds/8) #middle_pos - middleSize/2 == int(self.nb_of_leds/2 - self.nb_of_leds/8)
        self.middle_end_index = int(5*self.nb_of_leds/8)   #middle_pos + middleSize/2
        
        self.maxSize = int(self.nb_of_leds/3)

        self.lower_height = 0
        self.higher_height = 0  

        self.firstUpdate = True

    def start(self):
        super().start()
        self.firstUpdate = True

    def run(self):
        if (self.firstUpdate):
            length = self.middle_end_index + 1 - self.middle_start_index
            if length > 0:
                import numpy as np
                hues = np.linspace(self.bass_hue, self.high_hue, length)
                view = self.rgb_list[self.middle_start_index : self.middle_end_index + 1]
                RGB_HSV.fromHSV_toRGB_vectorized(hues, 1.0, 1.0, out=view)
            self.firstUpdate = False

        self.lower_height  = int(self.maxSize * (self.listener._delayed_asserved_fft_band[0]  + self.listener._delayed_asserved_fft_band[1] )/2)
        self.higher_height = int(self.maxSize * (self.listener._delayed_asserved_fft_band[-1] + self.listener._delayed_asserved_fft_band[-2])/2)

        self.fade_to_black_segment_vectorized(0.5,0,self.middle_start_index-1-self.lower_height-1)
        self.smooth_segment_vectorized(0.5,self.middle_start_index-1-self.lower_height,self.middle_start_index-1,self.bass_color)
        self.smooth_segment_vectorized(0.5,self.middle_end_index+1,self.middle_end_index+1+self.higher_height,self.high_color)
        self.fade_to_black_segment_vectorized(0.5,self.middle_end_index+1+self.higher_height+1,self.nb_of_leds-1)

        if(self.printThisModeDetail):
            self.logger.debug(f"(PSG)     lower_height = {self.lower_height}")
            self.logger.debug(f"(PSG)     higher_height = {self.higher_height}")