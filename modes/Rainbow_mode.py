import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV

class Rainbow_mode(Mode.Mode):
    
    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)
        
        #Used to calculate the hue and the intensity of each pixel
        self.delta_margin=float(self.nb_of_leds)/(self.listener.nb_of_segm_fft-1)
        self.nb_of_fft_segment = len(self.listener.asserv_segm_fft)

    
    def update(self):
        for led_index in range(self.nb_of_leds):
            #hue de 0 à 1 pour aller du rouge au bleu
            hue = led_index/self.nb_of_leds
            
            #low margin est l'index du plus proche fft_asserv par le bas, high margin par le haut
            low_margin = int(led_index / self.delta_margin)
            high_margin= low_margin+1

            position_coef = 1 -(led_index / self.delta_margin - low_margin)
            intensity = position_coef * self.listener.asserv_segm_fft[low_margin] + (1-position_coef) * self.listener.asserv_segm_fft[high_margin]
        
            rgb_color = RGB_HSV.fromHSV_toRGB(hue,1.0,intensity)

            super().smooth(0.5,led_index,rgb_color)


                    