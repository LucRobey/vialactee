import config.Configuration_manager as Configuration_manager
import core.Transition_Engine as Transition_Engine

import numpy as np
import logging
import importlib
import json
import os

class Segment:
    
    listener = None
    _configuration_manager = Configuration_manager.Configurations_manager()

    def __init__(self , name ,listener , leds , indexes , orientation , alcool , infos):
        self.name = name
        self.logger = logging.getLogger(f"Segment.{self.name}")
        self.leds = leds
        self.indexes = indexes
        self.infos = infos
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
        coords_list = self._configuration_manager.get_segment_coordinates(self.name)
        if coords_list is None:
            self.logger.warning(f"Could not find coordinates for {self.name} in segments_locations.json")
        elif len(coords_list) < self.nb_of_leds:
            self.logger.warning(f"Coordinate length mismatch for {self.name}. Expected {self.nb_of_leds}, got {len(coords_list)}")
        else:
            self.coords_array = np.array(coords_list[:self.nb_of_leds])

        
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
        
    #Load the json modes.json and initiate the modes 
    def initiate_modes(self , orientation , alcool):
        self.modes = []
        self.modes_names = []
        
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'modes.json')
        try:
            with open(config_path, 'r') as f:
                mode_config = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load modes.json: {e}")
            return
            
        args = (self.name, self.listener, self.leds, self.indexes, self.rgb_list, self.infos)
        
        def load_mode_list(mode_list):
            for mode_info in mode_list:
                try:
                    mode_name = mode_info["name"]
                    module_name = f"modes.{mode_info['module']}"
                    class_name = mode_info["class"]
                    
                    module = importlib.import_module(module_name)
                    mode_class = getattr(module, class_name)
                    
                    self.modes_names.append(mode_name)
                    self.modes.append(mode_class(mode_name, *args))
                except Exception as e:
                    self.logger.error(f"Failed to load mode {mode_info.get('name', 'Unknown')}: {e}")

        # Load standard modes
        load_mode_list(mode_config.get("standard_modes", []))

        if(orientation == "horizontal"):
            pass
                      
        if(orientation == "vertical"):
            load_mode_list(mode_config.get("vertical_modes", []))
            
        # Ensure the default mode is started upon initialization
        if 0 <= self.activ_mode < len(self.modes):
            self.modes[self.activ_mode].start()
        
    def update_leds(self, fusion_type):
        luminosite = self.listener.luminosite
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