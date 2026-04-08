import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import random
import time

class Shining_stars_mode(Mode.Mode):

    # size of the sub_segment that we will replicate in order to save some calculus
    # these are used as fallbacks if not found in self.infos
    sub_segment_size_default = 40

    # threshold to activate each band (with listener.asserv_segm_fft)
    threshold = 0.6

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        self.nb_of_fft_band = listener.nb_of_fft_band
        self.sub_segment_size = infos.get("stars_sub_segment_size", self.sub_segment_size_default)
        self.iteration_wait = infos.get("stars_iteration_wait", 30)

        # colors representing each band (red = basses ; blue = aigus)
        self.colors = []
        for band_index in range(self.nb_of_fft_band):
            new_colors = RGB_HSV.fromHSV_toRGB(float(band_index)/(self.nb_of_fft_band-1),1.0,1.0)
            self.colors.append(new_colors)
        self.colors=np.array(self.colors)

    def run(self):
        # first we fade to black
        self.fade_to_black_segment_vectorized(0.1, 0, self.nb_of_leds - 1)

        total = 0
        for band_index in range(self.nb_of_fft_band):
            total += self.listener.band_peak[band_index]

        for band_index in range(self.nb_of_fft_band):
            if self.listener.band_peak[band_index] > 0:
                self.lightUp(band_index)


    
    def lightUp(self , band_index):
        
        # we get a random pos under the size of the sub_segment than we show the led at this position modulo the sub_segment size
        random_pos = random.randint(0,self.sub_segment_size)

        segment_number = 0
        while ( segment_number * self.sub_segment_size + random_pos ) < self.nb_of_leds:
            self.rgb_list[segment_number * self.sub_segment_size + random_pos] = self.colors[band_index]
            segment_number+=1



