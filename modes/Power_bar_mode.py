import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import random
import numpy as np
import time

class Power_bar_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        #height of the color bar
        self.power_height = 0
        #height of the white dot
        self.white_dot_height = 0.0
        #color of the bar
        self.hue = random.uniform(0,1)
        self.color = RGB_HSV.fromHSV_toRGB(self.hue,1.0,1.0)

        #speed at wich the white dot comes down
        self.white_speed = float((self.nb_of_leds)/20)

    
    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================
        
        """
        calculate
        """
        new_power = self.listener.asserved_total_power
        new_height = new_power*self.nb_of_leds
        #could put some sensi here
        self.power_height = (self.power_height+new_height)/2

        #if the new value is superior to the nb_of_leds (wich should be impossible) we bring it back to a nb_of_leds-1
        if (self.power_height>self.nb_of_leds):
            self.power_height=self.nb_of_leds-1

        #we make sure the white dot is always above the coloured bar
        if(self.power_height>self.white_dot_height):
            self.white_dot_height=np.min([self.nb_of_leds-1,self.power_height+1])
        else:
            #we bring the white dot down
            self.white_dot_height -= self.white_speed
            if(self.white_dot_height<0):
                self.white_dot_height=0

        """
        show
        """
        #we color the bar
        for led_index in range(int(self.power_height+1)):
                super().smooth(0.5,led_index,self.color)

        #we color the white dot
        super().smooth(0.5,int(self.white_dot_height),self.white)

        #we smoothly brings the rest to zero
        for led_index in range(int(self.white_dot_height+1),self.nb_of_leds):
                super().smooth(0.5,led_index,(0,0,0))

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)
        

