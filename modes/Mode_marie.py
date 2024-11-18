import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV

class Mode_marie(Mode.Mode):

    def __init__(self , listener , leds , rgb_list , pourcentage_de_coloriage):
        super().__init__(listener , leds , rgb_list)

        self.led_limite = self.nb_of_leds * (pourcentage_de_coloriage/100)


    def update(self):
        bary_center = self.listener.fft_bary

        hue = bary_center / self.listener.lenFFT

        color = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)

        for led_index in range(self.led_limite):
            self.smooth(0.5,led_index,color)




