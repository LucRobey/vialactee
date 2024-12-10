import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import time

class Bary_rainbow_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        if (self.nb_of_leds%2 == 0):
            self.hasAMiddle = False
            self.middle_index = [int(self.nb_of_leds/2) , int(self.nb_of_leds/2 +1)]
        else:
             self.hasAMiddle = True
             self.middle_index = [int((self.nb_of_leds+1)/2) , int((self.nb_of_leds+1)/2)]
        
        #the maximum size of a side bar
        self.max_size = int((self.nb_of_leds+1)/2)
        
        
    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time() 
        #====================================================================================
         
        """
        calculate
        """

        fft_band_values = self.listener.smoothed_fft_band_values
        
        a = 0
        b = 0.0001
        
        for band_index in range(self.listener.nb_of_fft_band):
            a += fft_band_values[band_index] * band_index
            b += fft_band_values[band_index]
            
        middle_hue = np.min([(float(a)/b) / (self.listener.nb_of_fft_band-1),0.84])
        """
        show
        """
        for led_index in range(self.middle_index[0]):
            led_hue = (float(led_index)/self.middle_index[0]) * middle_hue
            self.rgb_list[led_index] = RGB_HSV.fromHSV_toRGB(led_hue,1.0,1.0)
        self.rgb_list[self.middle_index[0]] = RGB_HSV.fromHSV_toRGB(middle_hue,1.0,1.0)
        self.rgb_list[self.middle_index[1]] = RGB_HSV.fromHSV_toRGB(middle_hue,1.0,1.0)
        for led_index in range(self.middle_index[1]+1,self.nb_of_leds):
            led_hue = middle_hue + (0.85-middle_hue) * ( (float(led_index)-self.middle_index[1]) / (self.nb_of_leds - self.middle_index[1]))
            self.rgb_list[led_index] = RGB_HSV.fromHSV_toRGB(led_hue,1.0,1.0)
 
        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)