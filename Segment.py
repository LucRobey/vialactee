import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode

import numpy as np

class Segment:
    
    listener = None

    def __init__(self , listener , leds ):
        self.leds = leds
        if(self.listener==None):
            self.listener = listener
            
        self.rgb_list=[]
        for k in range((len(leds))):
            self.rgb_list.append((0,0,0))
        self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Bary_rainbow_mode.Bary_rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Middle_bar_mode.Middle_bar_mode(self.listener , self.leds , self.rgb_list),
                      Shining_stars_mode.Shining_stars_mode(self.listener , self.leds , self.rgb_list)]
        self.activ_mode = 0

    def update(self):
        self.modes[3].update()
        
        for k in range(len(self.rgb_list)):
            self.leds[k]=self.rgb_list[k]