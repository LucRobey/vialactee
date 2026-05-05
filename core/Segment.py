import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import modes.Middle_bar_mode as Middle_bar_mode
import modes.Power_bar_mode as Power_bar_mode
import modes.Bary_rainbow_mode as Bary_rainbow_mode
import modes.Shining_stars_mode as Shining_stars_mode
import modes.Proportion_rainbow_mode as Proportion_rainbow_mode
import modes.PSG_mode as PSG_mode
import modes.Opposite_sides_mode as Opposite_sides_mode
import modes.Flying_ball_mode as Flying_ball_mode
import modes.Coloured_middle_wave_mode as Coloured_middle_wave_mode

import modes.Matrix_rain_mode as Matrix_rain_mode
import modes.Plasma_fire_mode as Plasma_fire_mode
import modes.Hyper_strobe_mode as Hyper_strobe_mode
import modes.Chromatic_chaser_mode as Chromatic_chaser_mode
import modes.Synesthesia_mode as Synesthesia_mode
import modes.Metronome_mode as Metronome_mode

import modes.Alcool_randomer as Alcool_randomer

import Mode_Globaux.Segments_Locations as Segments_Locations
import core.Transition_Engine as Transition_Engine

import numpy as np
import logging

class Segment:
    
    listener = None

    def __init__(self , name ,listener , leds , indexes , orientation , alcool , infos):
        self.name = name
        self.logger = logging.getLogger(f"Segment.{self.name}")
        self.leds = leds
        self.indexes = indexes
        self.infos = infos
        self.useGlobalMatrix = infos["useGlobalMatrix"]
        self.nb_of_leds=len(self.indexes)
        if(self.listener==None):
            self.listener = listener
        self.fused_list = []
        self.rgb_list = np.zeros((len(indexes), 3), dtype=np.int32)
        self.dual_rgb_list = np.zeros((len(indexes), 3), dtype=np.int32)
        self.global_rgb_list = None
        
        self.coords_array = None
        self._load_coordinates()
        
        self.isBlocked = False

        self.modes=[]
        self.modes_names=[]
        self.initiate_modes(orientation , alcool)

    def _load_coordinates(self):
        locations = Segments_Locations.Segments_Locations()
        if self.name in locations.segment_names:
            idx = locations.segment_names.index(self.name)
            coords_list = locations.segment_coords[idx]
            if len(coords_list) >= self.nb_of_leds:
                self.coords_array = np.array(coords_list[:self.nb_of_leds])
            else:
                self.logger.warning(f"Coordinate length mismatch for {self.name}. Expected {self.nb_of_leds}, got {len(coords_list)}")
        else:
            self.logger.warning(f"Could not find coordinates for {self.name} in Segments_Locations")

        
        self.way="UP"

        self.activ_mode = 3

        self.state = "NORMAL"
        self.transition_progress = 0.0
        self.transition_step = 0.05
        self.target_mode_name = None
        self.target_index = None
        self.transition_type = None



    def update(self):
        
        #sécurité, enlevable
        if(self.modes[self.activ_mode].isActiv):
            self.modes[self.activ_mode].update()
        else:
            self.logger.warning("(S) erreur, on update un mode qui n'a pas été start ")
            
        # State machine for transitions
        if self.state == "TRANSITION_DUAL":
            if not self.modes[self.activ_mode].has_custom_transition:
                self.transition_progress += self.transition_step
                
                # --- UPDATE NEW MODE INTO SECONDARY BUFFER ---
                # We point the incoming mode exclusively to our dual_rgb_list buffer
                self.modes[self.target_index].rgb_list = self.dual_rgb_list
                if self.modes[self.target_index].isActiv:
                    self.modes[self.target_index].update()
                
                # Immediately restore the pointer for data safety
                self.modes[self.target_index].rgb_list = self.rgb_list

                # --- SPATIAL MIX BOTH BUFFERS INTO PRIMARY BUFFER ---
                active_coords = self.coords_array
                if self.way == "DOWN" and self.coords_array is not None:
                    active_coords = self.coords_array[::-1]

                if self.transition_type in ["fade_to_black", "local_change"]:
                    Transition_Engine.apply_dual_fade(self.rgb_list, self.dual_rgb_list, self.transition_progress)
                elif self.transition_type == "global_change":
                    Transition_Engine.apply_colorful_glitch(self.rgb_list, self.dual_rgb_list, self.transition_progress)
                elif self.transition_type == "gravity_drop" and active_coords is not None:
                    Transition_Engine.apply_gravity_drop(self.rgb_list, self.dual_rgb_list, active_coords, self.transition_progress)
                elif active_coords is not None:
                    Transition_Engine.apply_spatial_transition(self.rgb_list, self.dual_rgb_list, active_coords, self.transition_progress, self.transition_type)

                
            if self.transition_progress >= 1.0 or self.modes[self.activ_mode].has_custom_transition:
                # Execution complete! Swap the modes and terminate old one.
                self.modes[self.activ_mode].terminate()
                self.activ_mode = self.target_index
                
                self.state = "NORMAL"
                self.transition_progress = 0.0
        
        self.update_leds("Priority")
        

    def initiate_modes(self , orientation , alcool):
        self.modes = [Rainbow_mode.Rainbow_mode                        ("Rainbow"           , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Bary_rainbow_mode.Bary_rainbow_mode            ("Bary Rainbow"      , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Middle_bar_mode.Middle_bar_mode                ("Middle Bar"        , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Shining_stars_mode.Shining_stars_mode          ("Shining Stars"     , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Proportion_rainbow_mode.Proportion_rainbow_mode("Proportion Rainbow", self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        PSG_mode.PSG_mode                              ("PSG"               , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Opposite_sides_mode.Opposite_sides_mode        ("Opposite Sides"    , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Matrix_rain_mode.Matrix_rain_mode              ("Matrix Rain"       , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Plasma_fire_mode.Plasma_fire_mode              ("Plasma Fire"       , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Hyper_strobe_mode.Hyper_strobe_mode            ("Hyper Strobe"      , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Chromatic_chaser_mode.Chromatic_chaser_mode    ("Chromatic Chaser"  , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Synesthesia_mode.Synesthesia_mode              ("Synesthesia"       , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Metronome_mode.Metronome_mode                  ("Metronome"         , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Flying_ball_mode.Flying_ball_mode              ("Flying Ball"       , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        Coloured_middle_wave_mode.Coloured_middle_wave_mode("Coloured Middle Wave"  , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos),
                        ]
        self.modes_names = ["Rainbow",
                                "Bary Rainbow",
                                "Middle Bar",
                                "Shining Stars",
                                "Proportion Rainbow",
                                "PSG",
                                "Opposite Sides",
                                "Matrix Rain",
                                "Plasma Fire",
                                "Hyper Strobe",
                                "Chromatic Chaser",
                                "Synesthesia",
                                "Metronome",
                                "Flying Ball",
                                "Coloured Middle Wave",

                                ]

        if(orientation == "horizontal"):
            pass
                      
        if(orientation == "vertical"):
            self.modes.append(Power_bar_mode.Power_bar_mode("Power_bar" , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos))
            self.modes_names.append("Power Bar")

        if (alcool):
            self.modes.append(Alcool_randomer.Alcool_randomer("Shot" , self.name , self.listener , self.leds , self.indexes , self.rgb_list , self.infos))
            self.modes_names.append("Shot")
            
        # Ensure the default mode is started upon initialization
        if 0 <= self.activ_mode < len(self.modes):
            self.modes[self.activ_mode].start()
        
    def update_leds(self, fusion_type):
        luminosite = self.listener.luminosite
        if (self.useGlobalMatrix):
            if fusion_type == "Priority":
                # print("len of global rgb list " ,len(self.global_rgb_list), "for segment ", {self.name}, " |len of fused list" ,len(self.fused_list) )
                for led_index in range(len(self.global_rgb_list)):
                    if (self.global_rgb_list[led_index] != (0,0,0)):
                        # print(f'led_index: {led_index}, length of leds: {len(self.global_rgb_list)}, segment name: {self.name}')
                        self.leds[self.indexes[led_index]] = [int(luminosite * x) for x in self.global_rgb_list[led_index]]
                    else:
                        if(self.way=="UP"):
                            
                            self.leds[self.indexes[led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]
                        else:
                            self.leds[self.indexes[self.nb_of_leds-1-led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]
        else:
            
            for led_index in range(self.nb_of_leds):
                if(self.way=="UP"):
                    self.leds[self.indexes[led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]
                else:
                    self.leds[self.indexes[self.nb_of_leds-1-led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]

    def change_way(self , new_way):
        self.logger.debug(f"le {self.name} change de sens {self.way} pour {new_way}")
        self.way = new_way

    def switch_way(self):
        if(self.way == "UP"):
            new_way = "DOWN"
        else:
            new_way = "UP"
        self.logger.debug("switch")
        self.change_way(new_way)
        

    def execute_mode_swap(self, mode_name):
        if self.state == "TRANSITION_DUAL":
            return
            
        mode_name = mode_name.strip()
        if mode_name not in self.modes_names:
            self.logger.warning(f"ALERTE CE MODE :{mode_name} n'existe pas pour {self.name}")
            return
            
        target_index = self.modes_names.index(mode_name)
        if target_index == self.activ_mode:
            return

        self.state = "NORMAL"
        self.transition_progress = 0.0
        # On terminate l'ancien mode
        self.modes[self.activ_mode].terminate()
        
        # On change l'index et on start
        self.activ_mode = target_index
        self.modes[self.activ_mode].start()
        self.logger.info(f"{self.name} a changé de mode pour {mode_name}")

    def change_mode(self, mode_name, transition_config=None):
        if(not self.isBlocked):
            if self.state == "TRANSITION_DUAL":
                # Ignore new requests entirely if a transition is in progress
                self.logger.debug(f"(S) Transition already in progress for {self.name}, ignoring request to {mode_name}")
                return
                
            if transition_config is not None:
                # Resolve target index
                target_name = mode_name.strip()
                if not target_name in self.modes_names:
                    self.logger.warning(f"ALERTE CE MODE :{target_name} n'existe pas pour {self.name}")
                    return
                
                self.target_index = self.modes_names.index(target_name)
                self.target_mode_name = target_name

                if self.target_index == self.activ_mode:
                    return

                # Pre-start the incoming mode so it processes data immediately
                if not self.modes[self.target_index].isActiv:
                    self.modes[self.target_index].start()

                self.state = "TRANSITION_DUAL"
                self.transition_progress = 0.0
                self.transition_type = transition_config["type"]
                
                # 30 fps approximation
                duration = transition_config.get("duration", 2.0)
                if duration > 0:
                    self.transition_step = (1.0 / 30.0) / duration
                else:
                    self.transition_step = 1.0
            else:
                self.execute_mode_swap(mode_name)
        else:
            self.logger.debug(f"(S) le {self.name} est bloqué et ne peut pas passer au {mode_name}")

    def force_mode(self , mode_name):
        if self.state == "TRANSITION_DUAL":
            return
            
        mode_name = mode_name.strip()
        if mode_name not in self.modes_names:
            self.logger.warning(f"ALERTE CE MODE :{mode_name} n'existe pas pour {self.name}")
            return

        target_index = self.modes_names.index(mode_name)
        if target_index == self.activ_mode:
            return

        self.state = "NORMAL"
        self.transition_progress = 0.0
        #On terminate l'ancien mode
        self.modes[self.activ_mode].terminate()
        
        # On change l'index et on start
        self.activ_mode = target_index
        self.modes[self.activ_mode].start()
        self.logger.debug(f"(S) le segment {self.name} change de mode pour {mode_name}")
                
                
    def get_current_mode(self):
        return self.modes_names[self.activ_mode]
         
    def block(self):
        self.isBlocked = True

    def unBlock(self):
        self.isBlocked = False