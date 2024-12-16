import modes.Mode as Mode
import calculations.colors as colors
import time

class PSG_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        self.maxSize = int(self.nb_of_leds/3)

        self.lower_height = 0
        self.higher_height = 0

        self.white_dot_pos = 0
        
        
        
    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time() 
        #====================================================================================
        

        self.lower_height  = int(self.maxSize * (self.listener.asserved_fft_band[0]  + self.listener.asserved_fft_band[1] )/2)
        self.higher_height = int(self.maxSize * (self.listener.asserved_fft_band[-1] + self.listener.asserved_fft_band[-2])/2)

        self.smooth_segment(0.5,0,self.lower_height,colors.red)
        self.fade_to_black_segment(0.5,self.lower_height+1,self.nb_of_leds-1-self.higher_height-1)
        self.smooth_segment(0.5,self.nb_of_leds-1-self.higher_height,self.nb_of_leds-1,colors.blue)

        if (self.higher_height==self.lower_height):
            coef = 0
        else :
            coef = float(self.higher_height - self.lower_height)/(self.higher_height + self.lower_height)

        self.white_dot_pos = int((self.nb_of_leds/2) *(1 + coef))
        if(self.white_dot_pos > self.nb_of_leds-1):
            self.white_dot_pos = self.nb_of_leds-1
        if(self.white_dot_pos < 0):
            self.white_dot_pos = 0
        
        if(self.printThisModeDetail):
            print("(PSG)     lower_height = ",self.lower_height)
            print("(PSG)     higher_height = ",self.higher_height)
            print("(PSG)     coef = ",coef)
        self.rgb_list[self.white_dot_pos] = colors.white

        

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)