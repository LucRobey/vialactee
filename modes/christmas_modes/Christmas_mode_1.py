import modes.Mode as Mode
import modes.christmas_modes.christmas_colors as colors
import time

class Christmas_mode_1(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)
        #self.christmass_red = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)


    def update(self): 
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================
        u = 0
        while 5*u < self.nb_of_leds:
            for w in range(5):
                if(5*u + w < self.nb_of_leds):
                    if(u%2==0):
                        self.rgb_list[5*u + w] = colors.red
                    else:
                        self.rgb_list[5*u + w] = colors.green
            u+=1

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)