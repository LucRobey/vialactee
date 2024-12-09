import modes.Mode as Mode
import modes.christmas_modes.christmas_colors as colors

class Christmas_mode_1(Mode.Mode):

    def __init__(self , listener , leds , indexes , rgb_list):
        super().__init__(listener , leds , indexes , rgb_list)
        
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)


    def update(self):    
        u = 0
        while 5*u < self.nb_of_leds:
            for w in range(5):
                if(5*u + w < self.nb_of_leds):
                    if(u%2==0):
                        self.rgb_list[5*u + w] = colors.red
                    else:
                        self.rgb_list[5*u + w] = colors.green
            u+=1