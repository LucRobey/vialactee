import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode
import modes.Alcool_randomer as Alcool_randomer

import numpy as np

class Segment:
    
    listener = None

    def __init__(self , name ,listener , leds , global_rgb):
        self.name = name
        self.leds = leds
        self.nb_of_leds=len(self.leds)
        if(self.listener==None):
            self.listener = listener
        self.fused_list = []
        self.rgb_list = []
        for _ in range((len(leds))):
            self.rgb_list.append((0,0,0))
            self.fused_list.append((0,0,0))
        self.global_rgb_list = global_rgb
        
        self.isBlocked = False

        self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Bary_rainbow_mode.Bary_rainbow_mode(self.listener , self.leds , self.rgb_list),
                      Middle_bar_mode.Middle_bar_mode(self.listener , self.leds , self.rgb_list),
                      Shining_stars_mode.Shining_stars_mode(self.listener , self.leds , self.rgb_list),
                      Alcool_randomer.Alcool_randomer(self.listener , self.leds , self.rgb_list)]
        
        self.modes_names = ["Rainbow_mode",
                            "Bary_rainbow_mode",
                            "Middle_bar_mode",
                            "Shining_stars_mode",
                            "Alcool_randomer"]
        self.activ_mode = 0


    def update_leds(self):
        for led_index in range(self.nb_of_leds):
            self.leds[led_index]=self.fused_list[led_index]

    def update(self):
        
        self.modes[self.activ_mode].update()
        
        self.fuse_rgb_list("Priority")
        print("fused" , self.fused_list)
        
        self.update_leds()
        
        
        if(self.isBlocked):
            if(self.modes[self.activ_mode].hasEnded):
                self.isBlocked = False


    def fuse_rgb_list(self, fusion_type):
        if fusion_type == "Priority":
            print(len(self.global_rgb_list),len(self.fused_list) )
            for led_index in range(len(self.global_rgb_list)):
                if (self.global_rgb_list[led_index] != (0,0,0)):
                    self.fused_list[led_index] = self.global_rgb_list[led_index]
                else:
                    self.fused_list[led_index] = self.rgb_list[led_index]


    def change_mode(self , mode_name):
        #mode_name="Alcool_randomer"
        for mode_index in range(len(self.modes)):
            if (self.modes_names[mode_index]==mode_name):
                self.activ_mode=mode_index
                print("le segment ",self.name, " change de mode pour ", mode_name)
                
    def get_current_mode(self):
        return self.modes_names[self.activ_mode]
    
    def prepare_for_alcool_randomer(self):
        self.change_mode("Alcool_randomer")

        
    def block(self):
        self.isBlocked = True