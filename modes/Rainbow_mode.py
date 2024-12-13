import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import calculations.colors as colors
import time

class Rainbow_mode(Mode.Mode):
    
    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        #Used to calculate the hue and the intensity of each pixel
        self.delta_margin=float(self.nb_of_leds)/(self.listener.nb_of_fft_band-1)
        self.nb_of_fft_band = self.listener.nb_of_fft_band

        self.minimum_hue = colors.red_hue
        self.maximum_hue = colors.blue_hue

    
    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()
        #====================================================================================
        #   
        for led_index in range(self.nb_of_leds):
            #hue de 0 à 1 pour aller du rouge au bleu
            hue = self.minimum_hue + (self.maximum_hue - self.minimum_hue) * float(led_index)/self.nb_of_leds
            
            #low margin est l'index du plus proche fft_asserv par le bas, high margin par le haut
            low_margin = int(led_index / self.delta_margin)
            high_margin= low_margin+1

            position_coef = 1 -(led_index / self.delta_margin - low_margin)
            intensity = 0.1 + 0.9 *(position_coef * self.listener.asserved_fft_band[low_margin] + (1-position_coef) * self.listener.asserved_fft_band[high_margin])
        
            super().smooth(0.5 , led_index , RGB_HSV.fromHSV_toRGB(hue,1.0,intensity))

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)


                    