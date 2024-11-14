import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import random
import numpy as np

class Power_bar_mode(Mode.Mode):

    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)

        self.power_height = 0
        self.white_dot_height = 0.0
        self.hue = random.uniform(0,1)
        self.color = RGB_HSV.fromHSV_toRGB(self.hue,1.0,1.0)

        self.white_speed = float((self.nb_of_leds)/20)

    
    def update(self):

        """
        calculate
        """
        new_power = self.listener.total_power
        new_height = new_power*self.nb_of_leds
        self.power_height = (self.power_height+new_height)/2

        if (self.power_height>self.nb_of_leds):
            self.power_height=self.nb_of_leds-1

        if(self.power_height>self.white_dot_height):
            self.white_dot_height=np.min([self.nb_of_leds-1,self.power_height+1])
        else:
            self.white_dot_height -= self.white_speed

        """
        show
        """
        for led_index in range(self.power_height+1):
            if (led_index<=self.power_height):
                super().smooth(0.5,led_index,self.color)
            else:
                super().smooth(0.5,led_index,(0,0,0))
        super().smooth(0.5,self.white_dot_height,(1,1,1))

