import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Power_bar_mode as Power_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode
import modes.Proportion_rainbow_mode as Proportion_rainbow_mode
import modes.PSG_mode as PSG_mode
import modes.Opposite_sides_mode as Opposite_sides_mode

import modes.christmas_modes.Christmas_mode_1 as Christmas_mode_1
import modes.christmas_modes.Christmas_mode_2 as Christmas_mode_2

import modes.Alcool_randomer as Alcool_randomer

import numpy as np

class Segment:
    
    listener = None

    def __init__(self , name ,listener , leds , indexes , orientation , alcool , infos):
        self.name = name
        self.leds = leds
        self.indexes = indexes
        self.infos = infos
        self.useGlobalMatrix = infos["useGlobalMatrix"]
        self.nb_of_leds=len(self.indexes)
        if(self.listener==None):
            self.listener = listener
        self.fused_list = []
        self.rgb_list = []
        for _ in range((len(indexes))):
            self.rgb_list.append([0,0,0])
        self.global_rgb_list = []
        
        self.isBlocked = False

        self.modes=[]
        self.modes_names=[]
        self.initiate_modes(orientation , alcool)

        
        self.way="UP"

        self.activ_mode = 3



    def update(self):
        
        #sécurité, enlevable
        if(self.modes[self.activ_mode].isActiv):
            self.modes[self.activ_mode].update()
        else:
            print("(S) erreur, on update un mode qui n'a pas été start ")
        
        self.update_leds("Priority")
        

    def initiate_modes(self , orientation , alcool):
        self.modes = [Rainbow_mode.Rainbow_mode                        ("Rainbow"           , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Bary_rainbow_mode.Bary_rainbow_mode            ("Bary Rainbow"      , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Middle_bar_mode.Middle_bar_mode                ("Middle Bar"        , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Shining_stars_mode.Shining_stars_mode          ("Shining Stars"     , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Proportion_rainbow_mode.Proportion_rainbow_mode("Proportion Rainbow", self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        PSG_mode.PSG_mode                              ("PSG"               , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Opposite_sides_mode.Opposite_sides_mode        ("Opposite Sides"    , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Christmas_mode_1.Christmas_mode_1              ("Christmas_mode_1"  , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Christmas_mode_2.Christmas_mode_2              ("Christmas_mode_2"  , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos)
                        ]
        self.modes_names = ["Rainbow",
                                "Bary Rainbow",
                                "Middle Bar",
                                "Shining Stars",
                                "Proportion Rainbow",
                                "PSG",
                                "Opposite Sides",
                                "Christmas 1",
                                "Christmas 2"
                                ]

        if(orientation == "horizontal"):
            pass
                      
        if(orientation == "vertical"):
            self.modes.append(Power_bar_mode.Power_bar_mode("Power_bar" , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos))
            self.modes_names.append("Power Bar")

        if (alcool):
            self.modes.append(Alcool_randomer.Alcool_randomer("Shot" , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos))
            self.modes_names.append("Shot")
        
    def update_leds(self, fusion_type):
        luminosite = self.listener.luminosite
        if (self.useGlobalMatrix):
            if fusion_type == "Priority":
                print(len(self.global_rgb_list),len(self.fused_list) )
                for led_index in range(len(self.global_rgb_list)):
                    if (self.global_rgb_list[led_index] != (0,0,0)):
                        self.leds[self.indexes[led_index]] = luminosite * self.global_rgb_list[led_index]
                    else:
                        if(self.way=="UP"):
                            self.leds[self.indexes[led_index]] = luminosite * self.rgb_list[led_index]
                        else:
                            self.leds[self.indexes[self.nb_of_leds-1-led_index]] = luminosite * self.rgb_list[led_index]
        else:
            
            for led_index in range(self.nb_of_leds):
                new_color = []
                for rgb_index in range(3):
                    new_color.append(int(luminosite * self.rgb_list[led_index][rgb_index]))
                if(self.way=="UP"):
                    self.leds[self.indexes[led_index]] = new_color
                else:
                    self.leds[self.indexes[self.nb_of_leds-1-led_index]] = new_color

    def change_way(self , new_way , info_margin , showInfos):
        if(showInfos):
            print (info_margin + "(S) le " + self.name +"change de sens "+ self.way +" pour " + new_way)
        self.way = new_way

    def switch_way(self , info_margin , showInfos):
        if(self.way == "UP"):
            new_way = "DOWN"
        else:
            new_way = "UP"
        if(showInfos):
            print (info_margin + "(S) switch ")
        self.change_way(new_way ,  info_margin , showInfos)
        

    def change_mode(self , mode_name , info_margin , showInfos):
        mode_name = "Opposite Sides"
        if(not self.isBlocked):
            #On terminate l'ancien mode
            self.modes[self.activ_mode].terminate( info_margin+"   " , showInfos)
            if (not mode_name in self.modes_names):
                mode_name = mode_name[1:]
            for mode_index in range(len(self.modes)):
                found_a_mode = False
                if (self.modes_names[mode_index]==mode_name):
                    # On change l'index et on start
                    self.activ_mode = mode_index
                    self.modes[self.activ_mode].start(info_margin+"   " , showInfos)
                    if(showInfos):
                        print(info_margin,"(S) ",self.name, " a changé de mode pour ", mode_name)
                    found_a_mode = True
                    break
            if (not found_a_mode):
                print("ALERTE CE MODE :" , mode_name ," n'existe pas pour " , self.name)
        else:
            if (self.show_modes_details):
                print("(S) le "+self.name +" est bloqué et ne peut pas passer au "+mode_name)

    def force_mode(self , mode_name , info_margin , showInfos):
        #On terminate l'ancien mode
        self.modes[self.activ_mode].terminate(info_margin +"   ", showInfos)
        for mode_index in range(len(self.modes)):
            if (self.modes_names[mode_index]==mode_name):
                # On change l'index et on start
                self.activ_mode = mode_index
                self.modes[self.activ_mode].start(info_margin +"   ", showInfos)
                if (self.show_modes_details):
                    print("(S) le segment ",self.name, " change de mode pour ", mode_name)
                
                
    def get_current_mode(self):
        return self.modes_names[self.activ_mode]
         
    def block(self):
        self.isBlocked = True

    def unBlock(self):
        self.isBlocked = False