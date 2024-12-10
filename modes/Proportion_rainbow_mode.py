import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import numpy as np
import time

class Proportion_rainbow_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        self.minimum_hue = 0.8
        self.maximum_hue = 0.8

        self.N = (self.nb_of_leds-1)/(self.listener.nb_of_fft_band-1)
        
        
        
    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time() 
        #====================================================================================
        

        sum_dhue = ((self.N+1)/2) * (self.listener.asserved_fft_band[0]+self.listener.asserved_fft_band[-1]) + self.N * np.sum(self.listener.asserved_fft_band[1:-1])
        hue = self.minimum_hue

        if(self.printThisModeDetail):
            mem_dhue = []
            mem_hue = [self.minimum_hue]
            print("(PRM)     sum_dhue = ",sum_dhue)


        for led_index in range(self.nb_of_leds-1):
            
            self.smooth(0.5,led_index,RGB_HSV.fromHSV_toRGB(hue,1.0,1.0))

            #low margin est l'index du plus proche fft_asserv par le bas, high margin par le haut
            low_margin = int(led_index / self.N)
            high_margin= low_margin+1

            position_coef = 1 -(led_index / self.N - low_margin)
            dhue = (self.maximum_hue-self.minimum_hue) * (position_coef * self.listener.asserved_fft_band[low_margin] + (1-position_coef) * self.listener.asserved_fft_band[high_margin]) / (sum_dhue)
            
            hue += dhue
            if(self.printThisModeDetail):
                mem_dhue.append(dhue)
                mem_hue.append(hue)

        self.smooth(0.5,self.nb_of_leds-1,RGB_HSV.fromHSV_toRGB(self.maximum_hue,1.0,1.0))   
        if(self.printThisModeDetail):
            print("(PRM)     mem_hue = ",mem_hue)
            print("(PRM)     mem_dhue = ",mem_dhue)

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)