import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import random
import time

class Shining_stars_mode(Mode.Mode):

    # size of the sub_segment that we will replicate in order to save some calculus
    sub_segment_size = 40

    # nb of iterations to wait before showing again the color representing each band
    iteration_wait = 30

    # threshold to activate each band (with listener.asserv_segm_fft)
    threshold = 0.6

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        self.nb_of_fft_band = listener.nb_of_fft_band

        # colors representing each band (red = basses ; blue = aigus)
        self.colors = []
        for band_index in range(self.nb_of_fft_band):
            new_colors = RGB_HSV.fromHSV_toRGB(float(band_index)/(self.nb_of_fft_band-1),1.0,1.0)
            self.colors.append(new_colors)
        self.colors=np.array(self.colors)

    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================
        
        # first we fade to black
        self.fade_to_black(0.1)

        total = 0
        for band_index in range(self.nb_of_fft_band):
            total += self.listener.band_peak[band_index]

        for band_index in range(self.nb_of_fft_band):
            if self.listener.band_peak[band_index] > 0:
                self.lightUp(band_index)

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)


    
    def lightUp(self , band_index):
        
        # we get a random pos under the size of the sub_segment than we show the led at this position modulo the sub_segment size
        random_pos = random.randint(0,self.sub_segment_size)

        segment_number = 0
        while ( segment_number * self.sub_segment_size + random_pos ) < self.nb_of_leds:
            self.rgb_list[segment_number * self.sub_segment_size + random_pos] = self.colors[band_index]
            segment_number+=1



