import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode

import numpy as np

class Segment:
    
    listener = None

    def __init__(self , name ,listener , leds ):
        self.name = name
        self.leds = leds
        if(self.listener==None):
            self.listener = listener
        self.fused_list = []
        self.rgb_list=[]
        for _ in range((len(leds))):
            self.rgb_list.append((0,0,0))

        self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Bary_rainbow_mode.Bary_rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Middle_bar_mode.Middle_bar_mode(self.listener , self.leds , self.rgb_list),
                      Shining_stars_mode.Shining_stars_mode(self.listener , self.leds , self.rgb_list)]
        
        self.modes_names = ["Rainbow_mode",
                            "Bary_rainbow_mode",
                            "Middle_bar_mode",
                            "Shining_stars_mode"]
        self.activ_mode = 0


    def update_leds(self, list):
        for k in range(len(list)):
            self.leds[k]=list[k]

    def update(self,global_mode_rgb_list):

        self.modes[2].update()
        self.fused_list = self.rgb_list.copy()
        self.fuse_rgb_list(global_mode_rgb_list, "Priority")
        self.update_leds(self.fused_list)


    def fuse_rgb_list(self,list, fusion_type):
        if fusion_type == "Priority":
            for k in range(len(list)):
                self.fused_list[k] = list[k]


    def change_mode(self , mode_name):
        for mode_index in range(len(self.modes)):
            if (self.modes_names[mode_index]==mode_name):
                self.activ_mode=mode_index
                print("le segment ",self.name, " change de mode pour ", mode_name)