import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import random

class Shining_stars_mode(Mode.Mode):

    # size of the sub_segment that we will replicate in order to save some calculus
    sub_segment_size = 40

    # nb of iterations to wait before showing again the color representing each band
    iteration_wait = 30

    # threshold to activate each band (with listener.asserv_segm_fft)
    threshold = 0.6

    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)

        self.nb_of_fft_bands = len(self.listener.asserv_segm_fft)

        # memory of the nb of iterations to wait before showing again the color for each band
        self.wait_times = []
        for _ in range(self.nb_of_fft_bands):
            self.wait_times.append(0)
        self.wait_times=np.array(self.wait_times)

        # colors representing each band (red = basses ; blue = aigus)
        self.colors = []
        for band_index in range(self.nb_of_fft_bands):
            new_colors = RGB_HSV.fromHSV_toRGB(float(band_index)/(self.nb_of_fft_bands-1),1.0,1.0)
            self.wait_times.append(new_colors)
        self.wait_times=np.array(self.wait_times)

    def update(self):
        # first we fade to black
        self.fade_to_black(0.2)

        # then, for each band, we look if we have waited long enough to show the band's color again
        for band_index in range(self.nb_of_fft_bands):
            if self.wait_times[band_index] > 0:
                # if not, we lower the number of iterations to wait
                self.wait_times[band_index] -= 1
            else:
                #else, we look if the value of asserv_segm_fft[band] is over the treshold
                if self.listener.asserv_segm_fft[band_index] > self.threshold :
                    #if it is, we show the color on each sub_segments and we indicate that we have to wait n iterations before showing it again 
                    self.lightUp(band_index)
                    self.wait_times[band_index] = self.iteration_wait

    
    def lightUp(self , band_index):
        
        # we get a random pos under the size of the sub_segment than we show the led at this position modulo the sub_segment size
        random_pos = random.randint(0,self.sub_segment_size)

        segment_number = 0
        while ( segment_number * self.sub_segment_size + random_pos ) < self.nb_of_leds:
            self.rgb_list[segment_number * self.sub_segment_size + random_pos] = self.colors[band_index]
            segment_number+=1



