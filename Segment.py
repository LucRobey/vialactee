import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Power_bar_mode as Power_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode
import modes.Alcool_randomer as Alcool_randomer

import numpy as np

class Segment:
    
    listener = None

    def __init__(self , name ,listener , leds , indexes  , orientation , alcool):
        self.name = name
        self.leds = leds
        self.indexes = indexes
        self.nb_of_leds=len(self.indexes)
        if(self.listener==None):
            self.listener = listener
        self.fused_list = []
        self.rgb_list = []
        for _ in range((len(indexes))):
            self.rgb_list.append((0,0,0))
            self.fused_list.append((0,0,0))
        #self.global_rgb_list = global_rgb
        
        self.isBlocked = False

        self.modes=[]
        self.modes_names=[]
        self.initiate_modes(orientation , alcool)

        

        self.activ_mode = 3




    def update_leds(self):
        for led_index in range(self.nb_of_leds):
            self.leds[self.indexes[led_index]]=self.fused_list[led_index]
        

    def update(self):
        
        #sécurité, enlevable
        #if(self.modes[self.activ_mode].isActiv):
        self.modes[self.activ_mode].update()
        #else:
        #    print("(S) erreur, on update un mode qui n'a pas été start")
        
        self.fuse_rgb_list("Priority")
        #self.update_leds()
        

    def initiate_modes(self , orientation , alcool):
        if(orientation == "horizontal"):
            self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Bary_rainbow_mode.Bary_rainbow_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Middle_bar_mode.Middle_bar_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Shining_stars_mode.Shining_stars_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        ]
        
            self.modes_names = ["Rainbow",
                                "Bary rainbow",
                                "Middle bar",
                                "Shining Stars",
                                ]
        else:
            self.modes = [Rainbow_mode.Rainbow_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Bary_rainbow_mode.Bary_rainbow_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Middle_bar_mode.Middle_bar_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Shining_stars_mode.Shining_stars_mode(self.listener , self.leds , self.indexes , self.rgb_list),
                        Power_bar_mode.Power_bar_mode(self.listener , self.leds , self.indexes , self.rgb_list)]
        
            self.modes_names = ["Rainbow",
                                "Bary rainbow",
                                "Middle bar",
                                "Shining Stars",
                                "Power bar"]
        
        if (alcool):
            self.modes.append(Alcool_randomer.Alcool_randomer(self.listener , self.leds , self.indexes , self.rgb_list))
            self.modes_names.append("Shot")
        
    def fuse_rgb_list(self, fusion_type):
        """
        if fusion_type == "Priority":
            #print(self.global_rgb_list,self.fused_list)
            for led_index in range(len(self.global_rgb_list)):
                print(self.global_rgb_list[led_index])
                if (self.global_rgb_list[led_index] != [0,0,0]):
                    print
                    self.fused_list[led_index] = self.global_rgb_list[led_index]
                else:
                    self.fused_list[led_index] = self.rgb_list[led_index]
                """
        
        for led_index in range(self.nb_of_leds):
            self.leds[self.indexes[led_index]] = self.rgb_list[led_index]

        #self.leds[self.indexes] = self.rgb_list
        


    def change_mode(self , mode_name , info_margin , showInfos):
        if(not self.isBlocked):
            #On terminate l'ancien mode
            self.modes[self.activ_mode].terminate( info_margin+"   " , showInfos)
            for mode_index in range(len(self.modes)):
                found_a_mode = False
                if (self.modes_names[mode_index]==mode_name):
                    
                    # On change l'index et on start
                    self.activ_mode=mode_index
                    self.modes[self.activ_mode].start(info_margin+"   " , showInfos)
                    if(showInfos):
                        print(info_margin,"(S) ",self.name, " a changé de mode pour ", mode_name)
                    found_a_mode = True
                    break
            if (not found_a_mode):
                print("ALERTE CE MODE :" , mode_name ," n'existe pas pour " , self.name)
        else:
            print("(S) le "+self.name +" est bloqué et ne peut pas passer au "+mode_name)

    def force_mode(self , mode_name):
        #On terminate l'ancien mode
        self.modes[self.activ_mode].terminate()
        for mode_index in range(len(self.modes)):
            if (self.modes_names[mode_index]==mode_name):
                # On change l'index et on start
                self.activ_mode=mode_index
                self.modes[self.activ_mode].start()
                print("(S) le segment ",self.name, " change de mode pour ", mode_name)
                
                
    def get_current_mode(self):
        return self.modes_names[self.activ_mode]
         
    def block(self):
        self.isBlocked = True

    def unBlock(self):
        self.isBlocked = False