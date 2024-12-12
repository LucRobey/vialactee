import modes.Mode as Mode
import calculations.colors as colors
import calculations.rgb_hsv as RGB_HSV
import time

class Opposite_sides_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        self.bass_hue = 0.0
        self.high_hue = 0.8

        self.bass_color = RGB_HSV.fromHSV_toRGB(self.bass_hue,1.0,1.0)
        self.high_color = RGB_HSV.fromHSV_toRGB(self.high_hue,1.0,1.0)
        
        self.middleSize = int(self.nb_of_leds/4)
        self.middle_start_index = int(3*self.nb_of_leds/8) #middle_pos - middleSize/2 == int(self.nb_of_leds/2 - self.nb_of_leds/8)
        self.middle_end_index = int(5*self.nb_of_leds/8)   #middle_pos + middleSize/2
        
        self.maxSize = int(self.nb_of_leds/3)

        self.lower_height = 0
        self.higher_height = 0  

        self.firstUpdate = True

    def start(self , info_margin , showInfos):
        super().start(info_margin,showInfos)
        self.firstUpdate = True

    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time() 
        #====================================================================================
        
        if (self.firstUpdate):
            for led_index in range(self.middle_start_index,self.middle_end_index+1):
                hue = self.bass_hue + (self.high_hue - self.bass_hue) * (float(led_index - self.middle_start_index)/(self.middle_end_index - self.middle_start_index))
                color = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)
                self.rgb_list[led_index] = color
            self.firstUpdate = False

        self.lower_height  = int(self.maxSize * (self.listener.asserved_fft_band[0]  + self.listener.asserved_fft_band[1] )/2)
        self.higher_height = int(self.maxSize * (self.listener.asserved_fft_band[-1] + self.listener.asserved_fft_band[-2])/2)

        self.fade_to_black_segment(0.5,0,self.middle_start_index-1-self.lower_height-1)
        self.smooth_segment(0.5,self.middle_start_index-1-self.lower_height,self.middle_start_index-1,self.bass_color)
        self.smooth_segment(0.5,self.middle_end_index+1,self.middle_end_index+1+self.higher_height,self.high_color)
        self.fade_to_black_segment(0.5,self.middle_end_index+1+self.higher_height+1,self.nb_of_leds-1)

        self.fade_to_black_segment(0.5,self.lower_height+1,self.nb_of_leds-1-self.higher_height-1)
        self.smooth_segment(0.5,self.nb_of_leds-1-self.higher_height,self.nb_of_leds-1,colors.blue)

        if(self.printThisModeDetail):
            print("(PSG)     lower_height = ",self.lower_height)
            print("(PSG)     higher_height = ",self.higher_height)

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)