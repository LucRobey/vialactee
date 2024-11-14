import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode

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
        self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.rgb_list)]
        self.activ_mode = 0

    def update(self):
        self.modes[0].update()
        
        for k in range(len(self.rgb_list)):
            self.leds[k]=self.rgb_list[k]