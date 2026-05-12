from typing import Dict, Any, List, Optional
import config.Configuration_manager as Configuration_manager
import core.Transition_Engine as Transition_Engine

import numpy as np
import logging
import importlib
import json
import os

class Segment:
    """
    Represents a physical LED segment in the installation.
    
    A segment manages its own local buffer, active mode, and transition state.
    It acts as the intermediary between the visual modes and the actual hardware 
    LED array.
    """
    
    listener = None
    _configuration_manager = Configuration_manager.Configurations_manager()

    def __init__(self, name: str, listener: Any, leds: Any, indexes: List[int], orientation: str, infos: Dict[str, Any]) -> None:
        """
        Initialize a new Segment.

        Args:
            name (str): The unique identifier name of the segment (e.g., 'Segment v4').
            listener: Reference to the global audio listener for reactivity.
            leds: Shared list/array of the global LED strip.
            indexes (list): The specific hardware indices belonging to this segment.
            orientation (str): 'horizontal' or 'vertical' layout orientation.
            infos: Additional configuration metadata.
        """
        self.name = name
        self.logger = logging.getLogger(f"Segment.{self.name}")
        self.leds = leds
        self.indexes = indexes
        self.infos = infos
        self.nb_of_leds=len(self.indexes)
        if self.listener is None:
            self.listener = listener
        self.fused_list = []
        self.rgb_list = np.zeros((len(indexes), 3), dtype=np.int32)
        self.dual_rgb_list = np.zeros((len(indexes), 3), dtype=np.int32)
        self.global_rgb_list = None
        
        self.coords_array = None
        self._load_coordinates()
        
        self.isBlocked = False

        self.way = "UP"
        self.activ_mode = "Shining Stars"

        self.is_in_transition = False
        self.target_mode_name = None

        self.modes = {}
        self.initiate_modes(orientation)

    def _load_coordinates(self) -> None:
        """
        Load the 2D spatial coordinates for this segment's LEDs from the configuration.
        
        This is used for physics-based spatial transitions (e.g., gravity drops).
        """
        coords_list = self._configuration_manager.get_segment_coordinates(self.name)
        if coords_list is None:
            self.logger.warning(f"Could not find coordinates for {self.name} in segments.json")
        elif len(coords_list) < self.nb_of_leds:
            self.logger.warning(f"Coordinate length mismatch for {self.name}. Expected {self.nb_of_leds}, got {len(coords_list)}")
        else:
            self.coords_array = np.array(coords_list[:self.nb_of_leds])



    def update(self, td: Any) -> None:
        """
        Update the current active mode and handle any ongoing visual transitions.
        
        This method executes the active visual mode, processes dual-buffer mixing 
        if a transition is in progress, and finally flushes the local buffer to 
        the global hardware LED array.
        """
        
        #sécurité, enlevable
        if self.modes[self.activ_mode].isActiv:
            self.modes[self.activ_mode].update()
        else:
            self.logger.warning("(S) erreur, on update un mode qui n'a pas été start ")
            
        # State machine for transitions
        if self.is_in_transition:
            if td.state == "TRANSITION_DUAL":
                if not self.modes[self.activ_mode].has_custom_transition:
                    
                    # --- UPDATE NEW MODE INTO SECONDARY BUFFER ---
                    # We point the incoming mode exclusively to our dual_rgb_list buffer
                    self.modes[self.target_mode_name].rgb_list = self.dual_rgb_list
                    if self.modes[self.target_mode_name].isActiv:
                        self.modes[self.target_mode_name].update()
                    
                    # Immediately restore the pointer for data safety
                    self.modes[self.target_mode_name].rgb_list = self.rgb_list

                    # --- SPATIAL MIX BOTH BUFFERS INTO PRIMARY BUFFER ---
                    active_coords = self.coords_array
                    if self.way == "DOWN" and self.coords_array is not None:
                        active_coords = self.coords_array[::-1]

                    import core.Transition_Engine as Transition_Engine
                    Transition_Engine.apply_transition(self.rgb_list, self.dual_rgb_list, td.transition_progress, td.transition_type, active_coords)

                
            if td.state == "PASSATION" or self.modes[self.activ_mode].has_custom_transition:
                # Execution complete! Swap the modes and terminate old one.
                self.modes[self.activ_mode].terminate()
                self.activ_mode = self.target_mode_name
                self.is_in_transition = False
        
        self.update_leds()

        # Forward mode info to hardware-side visualizers (only Fake_leds reacts;
        # real hardware does not implement this method and is bypassed).
        if hasattr(self.leds, "set_segment_mode"):
            target = self.target_mode_name if self.is_in_transition else None
            self.leds.set_segment_mode(self.name, self.activ_mode, target)
        
    #Load the json modes.json and initiate the modes 
    def initiate_modes(self, orientation: str) -> None:
        """
        Dynamically load and instantiate all available visual modes for this segment
        based on the modes.json configuration file.

        Args:
            orientation (str): Segment orientation ('vertical' or 'horizontal').
        """
        self.modes = {}
        
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
                    
                    self.modes[mode_name] = mode_class(mode_name, *args)
                except Exception as e:
                    self.logger.error(f"Failed to load mode {mode_info.get('name', 'Unknown')}: {e}")

        # Load standard modes
        load_mode_list(mode_config.get("standard_modes", []))

        if orientation == "horizontal":
            pass
                      
        if orientation == "vertical":
            load_mode_list(mode_config.get("vertical_modes", []))
            
        # Ensure the default mode is started upon initialization
        if self.activ_mode in self.modes:
            self.modes[self.activ_mode].start()
        
    def update_leds(self) -> None:
        """
        Flush the local segment RGB buffer to the global LED array.
        """
        luminosite = self.listener.luminosite
        for led_index in range(self.nb_of_leds):
            if self.way == "UP":
                self.leds[self.indexes[led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]
            else:
                self.leds[self.indexes[self.nb_of_leds-1-led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]

    def change_way(self, new_way: str) -> None:
        """
        Change the propagation direction of visual effects on the segment.

        Args:
            new_way (str): The new direction ('UP' or 'DOWN').
        """
        self.logger.debug(f"le {self.name} change de sens {self.way} pour {new_way}")
        self.way = new_way

    def switch_way(self) -> None:
        """
        Toggle the current propagation direction between 'UP' and 'DOWN'.
        """
        if self.way == "UP":
            new_way = "DOWN"
        else:
            new_way = "UP"
        self.logger.debug("switch")
        self.change_way(new_way)
        

    

    def execute_mode_swap(self, mode_name: str) -> None:
        """
        Instantly swap to a new visual mode without any transition effects.

        Args:
            mode_name (str): The name of the target mode to switch to.
        """
        if self.is_in_transition:
            return
            
        mode_name = self._normalize_mode_name(mode_name)
        if mode_name not in self.modes:
            self.logger.warning(f"ALERTE CE MODE :{mode_name} n'existe pas pour {self.name}")
            return
            
        if mode_name == self.activ_mode:
            return

        self.is_in_transition = False
        # On terminate l'ancien mode
        self.modes[self.activ_mode].terminate()
        
        # On change l'index et on start
        self.activ_mode = mode_name
        self.modes[self.activ_mode].start()
        self.logger.info(f"{self.name} a changé de mode pour {mode_name}")

    def change_mode(self, mode_name: str, transition_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Request a mode change, optionally using a dual-buffer transition effect.

        Args:
            mode_name (str): The name of the target mode.
            transition_config (dict, optional): Configuration defining the type and 
                duration of the transition. Defaults to None (instant swap).
        """
        if not self.isBlocked:
            if self.is_in_transition:
                # Ignore new requests entirely if a transition is in progress
                self.logger.debug(f"(S) Transition already in progress for {self.name}, ignoring request to {mode_name}")
                return
                
            if transition_config is not None:
                # Resolve target index
                target_name = self._normalize_mode_name(mode_name)
                if target_name not in self.modes:
                    self.logger.warning(f"ALERTE CE MODE :{target_name} n'existe pas pour {self.name}")
                    return
                
                self.target_mode_name = target_name

                if self.target_mode_name == self.activ_mode:
                    return

                # Pre-start the incoming mode so it processes data immediately
                if not self.modes[self.target_mode_name].isActiv:
                    self.modes[self.target_mode_name].start()

                self.is_in_transition = True
            else:
                self.execute_mode_swap(mode_name)
        else:
            self.logger.debug(f"(S) le {self.name} est bloqué et ne peut pas passer au {mode_name}")

    def force_mode(self, mode_name: str) -> None:
        """
        Forcefully change to a new mode, overriding any current state.

        Args:
            mode_name (str): The name of the target mode.
        """
        if self.is_in_transition:
            return
            
        mode_name = self._normalize_mode_name(mode_name)
        if mode_name not in self.modes:
            self.logger.warning(f"ALERTE CE MODE :{mode_name} n'existe pas pour {self.name}")
            return

        if mode_name == self.activ_mode:
            return

        self.is_in_transition = False
        #On terminate l'ancien mode
        self.modes[self.activ_mode].terminate()
        
        # On change l'index et on start
        self.activ_mode = mode_name
        self.modes[self.activ_mode].start()
        self.logger.debug(f"(S) le segment {self.name} change de mode pour {mode_name}")
                
                
    def get_current_mode(self) -> str:
        """
        Get the name of the currently active mode.

        Returns:
            str: The name of the active mode.
        """
        return self.activ_mode

    def get_mode_settings_catalog(self) -> List[Dict[str, Any]]:
        catalogs: List[Dict[str, Any]] = []
        for mode in self.modes.values():
            if not hasattr(mode, "get_settings_catalog"):
                continue
            catalog = mode.get_settings_catalog()
            if isinstance(catalog, dict) and isinstance(catalog.get("settings"), list) and len(catalog["settings"]) > 0:
                catalogs.append(catalog)
        return catalogs

    def export_mode_settings(self, mode_name: str) -> Dict[str, Any]:
        normalized_name = self._normalize_mode_name(mode_name)
        mode = self.modes.get(normalized_name)
        if mode is None or not hasattr(mode, "export_settings"):
            return {}
        exported = mode.export_settings()
        return exported if isinstance(exported, dict) else {}

    def apply_mode_settings(self, mode_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        normalized_name = self._normalize_mode_name(mode_name)
        mode = self.modes.get(normalized_name)
        if mode is None or not hasattr(mode, "apply_settings"):
            return {}
        applied = mode.apply_settings(settings)
        return applied if isinstance(applied, dict) else {}
         
    def block(self) -> None:
        """
        Block the segment from accepting new mode change requests.
        """
        self.isBlocked = True

    def unBlock(self) -> None:
        """
        Unblock the segment, allowing it to accept mode change requests again.
        """
        self.isBlocked = False


    #Pass from user friendly name (example : plasma fire) to the internal name (example : Plasma_Fire_mode)
    def _normalize_mode_name(self, mode_name: str) -> str:
        """
        Normalize a mode name, resolving legacy formatting.

        Converts old-style names (e.g., 'Plasma_fire_mode') to the standard 
        human-readable keys used in the modes dictionary (e.g., 'Plasma Fire').

        Args:
            mode_name (str): The requested mode name.

        Returns:
            str: The normalized mode name, or the original if no match was found.
        """
        mode_name = mode_name.strip()
        if mode_name in self.modes:
            return mode_name
            
        # Legacy support for "Metronome_mode", "Plasma_fire_mode", etc.
        for name in self.modes:
            if name.replace(" ", "").lower() == mode_name.replace("_mode", "").replace("_", "").lower():
                return name
                
        return mode_name