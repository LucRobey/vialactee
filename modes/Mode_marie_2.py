import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV

class Mode_marie_2(Mode.Mode):

    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)

        self.hue = 1
       
    def decaler(self):
        for k in range(self.nb_of_leds):
            self.rgb_list[self.nb_of_leds-1-k] = self.rgb_list[self.nb_of_leds-1-k-1]

    def update(self):
        self.decaler()
        color = RGB_HSV.fromHSV_toRGB(self.hue,1.0,1.0)
        self.rgb_list[0] = color
        self.hue = self.hue + 0.01
        if (self.hue > 1):
            self.hue=0
