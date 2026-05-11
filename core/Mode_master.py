import numpy as np
import asyncio
import logging
import random
import time
from typing import Dict, Any, List, Optional

import core.Segment as Segment
import core.Listener as Listener
import core.Transition_Director as Transition_Director



from contextlib import contextmanager

class Profiler:
    """
    A simple context-manager based profiler to measure execution time of code blocks.
    """
    def __init__(self, active: bool, logger: logging.Logger) -> None:
        """
        Initialize the Profiler.

        Args:
            active (bool): Whether the profiler is active and should record times.
            logger (logging.Logger): The logger instance to use for output.
        """
        self.active = active
        self.logger = logger
        self.durations = []
        self.names = []
        self.start_times = {}

    @contextmanager
    def measure(self, name: str) -> Any:
        """
        Context manager to measure the execution time of a block of code.

        Args:
            name (str): The name/label for this measurement block.
        """
        if self.active:
            start = time.time()
            yield
            self.durations.append(time.time() - start)
            self.names.append(name)
        else:
            yield

    def print_results(self) -> None:
        """
        Print the accumulated profiling results to the logger.
        """
        if self.active and self.durations:
            self.logger.debug("=======================================================================")
            total = np.sum(self.durations)
            self.logger.debug(f"   |(MM) total = {total:.5f} secondes")
            if total > 0:
                nb_of_it_per_sec = 1 / total
                self.logger.debug(f"   |(MM) soit {nb_of_it_per_sec:.2f} itérations par seconde")
                for k in range(len(self.durations)):
                    percentage = 100 * float(self.durations[k]) / total
                    self.logger.debug(f"   |(MM) {self.names[k]}  :  {percentage:.2f}%")


class Mode_master:
    """
    Master controller for all visual segments, modes, and configurations.

    Manages the global state, playlists, and transitions between different
    configurations across the entire installation.
    """

    def __init__(self, listener: Any, infos: Dict[str, Any], *leds: Any) -> None:
        """
        Initialize the Mode_master.

        Args:
            listener: Reference to the global audio listener.
            infos (dict): Dictionary containing global configuration and metadata.
            *leds: References to the LED strip hardware/simulators.
        """
        self.infos = infos
        self.listener = listener
        self.onRaspberry            = infos.get("onRaspberry", False)
        self.printTimeOfCalculation = infos.get("printTimeOfCalculation", False)
        self.printModesDetails      = infos.get("printModesDetails", False)
        self.printAppDetails        = infos.get("printAppDetails", False)
        self.printConfigChanges     = infos.get("printConfigChanges", False)

        self.leds_list = leds
        self.logger = logging.getLogger("Mode_master")
        self.profiler = Profiler(self.printTimeOfCalculation, self.logger)
        self.current_time = time.time()
        self.appli_connector = None
        self.segments_list: List[Segment.Segment] = []
        self.segments_names_to_index: Dict[str, int] = {}
        self.activ_configuration: Dict[str, Any] = {}
        self.configurations: Dict[str, List[Dict[str, Any]]] = {}
        self.playlists: List[str] = []
        self.blocked_playlists: List[bool] = []
        self.shuffle_bag: List[Dict[str, Any]] = []
        self.transition_locked = False
        self.selected_transition_config = {"type": "fade_in_out", "duration": 2.0}
        self.queued_configuration_name: Optional[str] = None

        self.load_configurations()

        self.initiate_segments()
        self.initiate_configuration()
        self.transition_director = Transition_Director.Transition_Director(self, self.listener, self.infos)

    def set_connector(self, connector: Any) -> None:
        """
        Set the application connector for external communications.

        Args:
            connector: The connector instance.
        """
        self.appli_connector = connector

    async def update_forever(self) -> None:
        """
        Continuously update the system at approximately 30 FPS.
        """
        while True:
            await self.update()
            await asyncio.sleep(1/30)

    async def update(self) -> None:
        """
        Perform a single update loop iteration.

        Updates the audio listener, flushes hardware LED buffers, updates all
        segments, and evaluates global transitions via the Transition_Director.
        """
        # Profiler cleans up the time_time() boilerplate
        with self.profiler.measure("listener.update()"):
            self.listener.update()

        with self.profiler.measure("leds.show()"):
            is_rpi_hardware = len(self.leds_list) > 0 and "Rpi_NeoPixels" in str(type(self.leds_list[0]))
            if self.infos.get("onRaspberry", False) or self.infos.get("HARDWARE_MODE") == "rpi" or is_rpi_hardware:
                loop = asyncio.get_running_loop()
                for led_strip in self.leds_list:
                    await loop.run_in_executor(None, led_strip.show)
            else:
                for led_strip in self.leds_list:
                    led_strip.show()

        with self.profiler.measure("segments.update()"):
            for seg_index in range(len(self.segments_list)):
                self.segments_list[seg_index].update(self.transition_director)

        #==============================================
        self.current_time = time.time()
        
        await self.transition_director.update(self.current_time)

        self.profiler.print_results()
        # Clean profiler values for next frame
        self.profiler.durations.clear()
        self.profiler.names.clear()


    def load_configurations(self) -> None:
        """
        Load modes and playlists from the configurations.json file.
        """
        import json
        import os
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "configurations.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.configurations = data.get('configurations', {})
            self.playlists = data.get('playlists', [])
            if self.printConfigChanges:
                self.logger.debug(f"(MM) Loaded {len(self.playlists)} playlists from {file_path}")
        except Exception as e:
            self.logger.error(f"Error reading JSON configuration file: {e}")
            self.configurations = {}
            self.playlists = []

        self.blocked_playlists = [False for _ in self.playlists]
        self.shuffle_bag = []
    def update_segments_modes(self, transition_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply the active configuration to all relevant segments.

        Args:
            transition_config (dict, optional): Configuration defining the type and
                duration of the transition. Defaults to None.
        """
        if transition_config is not None:
            self.transition_director.start_transition(transition_config)
            
        active_modes = self.activ_configuration.get("modes", {})
        active_way = self.activ_configuration.get("way", {})
        for segment in self.segments_list:
            if not segment.isBlocked:
                self.logger.debug(f"(MM) update_segments_modes : {segment.name} non bloqué donc on ordonne de le changer")
                mode_name = active_modes.get(segment.name)
                if mode_name is not None:
                    segment.change_mode(mode_name, transition_config)
                way = active_way.get(segment.name)
                if way is not None:
                    segment.change_way(way)

 

    def initiate_configuration(self) -> None:
        """
        Initialize the starting configuration by picking a random one from available playlists.
        """
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self.pick_a_random_conf()
        self.update_segments_modes()

        

    def initiate_segments(self) -> None:
        """
        Initialize all segments based on the segments.json configuration file.
        """
        def add_segments(info_list: List[Dict[str, Any]], leds: Any) -> None:
            offset = 0
            for segment_index in range(len(info_list)):
                seg_infos = info_list[segment_index]
                indexes = [i for i in range(offset,offset+seg_infos["size"])]
                new_segment = Segment.Segment(seg_infos["name"],self.listener, leds ,indexes,seg_infos["orientation"],self.infos)
                offset += seg_infos["size"]
                self.segments_list.append(new_segment)
                self.segments_names_to_index[seg_infos["name"]]=seg_infos["order"]
                
        import json
        import os
        file_path = os.path.join(os.path.dirname(__file__), "..", "config", "segments.json")
        with open(file_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            
        for i, leds in enumerate(self.leds_list):
            key = f"segs_{i+1}"
            if key in data:
                add_segments(data[key], leds)


    async def change_configuration(self, transition_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Change the global active configuration to a new random one.

        Args:
            transition_config (dict, optional): Configuration defining the type and
                duration of the transition. Defaults to None.
        """
        #on pick une conf nouvelle au pif
        last_configuration = self.activ_configuration
        loop_guard = 0
        while (last_configuration==self.activ_configuration and loop_guard < 10):
            self.activ_configuration = self.pick_a_random_conf()
            loop_guard += 1
        #on l'applique à tous les segments
        self.update_segments_modes(transition_config)

    def _normalize_transition(self, transition_name: Any) -> Dict[str, Any]:
        if not isinstance(transition_name, str):
            return {"type": "fade_in_out", "duration": 2.0}

        normalized = transition_name.strip().upper()
        if normalized == "CUT":
            return {"type": "explosion", "duration": 0.0}
        if normalized == "CROSSFADE":
            return {"type": "global_change", "duration": 3.0}
        if normalized == "FADE IN/OUT":
            return {"type": "fade_in_out", "duration": 2.0}
        return {"type": "fade_in_out", "duration": 2.0}

    def _segment_name_from_id(self, segment_id: Any) -> Optional[str]:
        if not isinstance(segment_id, str) or len(segment_id.strip()) == 0:
            return None
        return f"Segment {segment_id.strip()}"

    def _find_segment_by_name(self, segment_name: str) -> Optional[Segment.Segment]:
        for segment in self.segments_list:
            if segment.name == segment_name:
                return segment
        return None

    def _set_only_playlist_active(self, playlist_name: Any) -> bool:
        if not isinstance(playlist_name, str):
            return False

        normalized_name = playlist_name.strip()
        if normalized_name.upper() == "CUSTOM":
            return False

        selected_index = None
        for index, name in enumerate(self.playlists):
            if name.lower() == normalized_name.lower():
                selected_index = index
                break

        if selected_index is None:
            return False

        self.blocked_playlists = [idx != selected_index for idx in range(len(self.playlists))]
        self.shuffle_bag = []
        return True

    def _find_configuration(self, configuration_name: Any, playlist_name: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        if not isinstance(configuration_name, str):
            return None
        wanted_name = configuration_name.strip().lower()

        candidate_playlists = []
        if isinstance(playlist_name, str):
            candidate_playlists = [p for p in self.playlists if p.lower() == playlist_name.strip().lower()]
        if len(candidate_playlists) == 0:
            candidate_playlists = list(self.playlists)

        for playlist in candidate_playlists:
            for conf in self.configurations.get(playlist, []):
                if conf.get("name", "").strip().lower() == wanted_name:
                    return {
                        "playlist": playlist,
                        "index": -1,
                        "name": conf.get("name"),
                        "modes": conf.get("modes", {}),
                        "way": conf.get("way", {}),
                    }
        return None

    def _apply_configuration(self, config: Dict[str, Any], transition_config: Optional[Dict[str, Any]]) -> None:
        self.activ_configuration = config
        self.update_segments_modes(transition_config)

    async def process_instruction(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        page = instruction.get("page")
        action = instruction.get("action")
        payload = instruction.get("payload", {})

        if not isinstance(payload, dict):
            return {"applied": False, "reason": "invalid_payload"}

        if page == "live_deck":
            if action == "set_luminosity":
                value = payload.get("value")
                if isinstance(value, (int, float)):
                    self.listener.luminosite = max(0.0, min(1.0, float(value) / 100.0))
                    return {"applied": True}
                return {"applied": False, "reason": "invalid_value"}

            if action == "set_sensibility":
                value = payload.get("value")
                if isinstance(value, (int, float)):
                    self.listener.sensi = max(0.0, float(value) / 100.0)
                    return {"applied": True}
                return {"applied": False, "reason": "invalid_value"}

            if action == "select_transition":
                self.selected_transition_config = self._normalize_transition(payload.get("transition"))
                return {"applied": True}

            if action == "select_configuration":
                configuration_name = payload.get("configuration")
                config = self._find_configuration(configuration_name)
                if config is not None:
                    self.queued_configuration_name = config["name"]
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_configuration"}

            if action == "select_playlist":
                if self._set_only_playlist_active(payload.get("playlist")):
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_playlist"}

            if action == "go_to_next_configuration":
                self.selected_transition_config = self._normalize_transition(payload.get("transition"))
                configuration_name = payload.get("configuration")
                config = self._find_configuration(configuration_name)
                if config is None:
                    config = self.pick_a_random_conf()
                self._apply_configuration(config, self.selected_transition_config)
                return {"applied": True}

            if action == "manual_drop":
                config = self._find_configuration(self.queued_configuration_name) if self.queued_configuration_name else None
                if config is None:
                    config = self.pick_a_random_conf()
                self._apply_configuration(config, self.selected_transition_config)
                return {"applied": True}

            if action == "lock_current_configuration":
                locked = payload.get("locked")
                self.transition_locked = bool(locked)
                return {"applied": True}

        if page == "topology":
            if action == "select_playlist_slot":
                if self._set_only_playlist_active(payload.get("playlist")):
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_playlist"}

            if action == "select_configuration":
                if self._set_only_playlist_active(payload.get("playlist")):
                    self.shuffle_bag = []
                config = self._find_configuration(payload.get("configuration"), payload.get("playlist"))
                if config is not None:
                    self._apply_configuration(config, self.selected_transition_config)
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_configuration"}

            if action == "select_segment_mode":
                segment_name = self._segment_name_from_id(payload.get("segmentId"))
                mode_name = payload.get("mode")
                if segment_name is None or not isinstance(mode_name, str):
                    return {"applied": False, "reason": "invalid_segment_or_mode"}
                segment = self._find_segment_by_name(segment_name)
                if segment is None:
                    return {"applied": False, "reason": "unknown_segment"}
                segment.execute_mode_swap(mode_name)
                return {"applied": True}

            if action == "toggle_segment_direction":
                segment_name = self._segment_name_from_id(payload.get("segmentId"))
                direction = payload.get("direction")
                if segment_name is None or direction not in ("UP", "DOWN"):
                    return {"applied": False, "reason": "invalid_segment_or_direction"}
                segment = self._find_segment_by_name(segment_name)
                if segment is None:
                    return {"applied": False, "reason": "unknown_segment"}
                segment.change_way(direction)
                return {"applied": True}

            if action in {"set_editor_mode", "select_segment", "build_configuration", "modify_configuration"}:
                return {"applied": True}

        if page == "auto_dj":
            value = payload.get("value")
            if isinstance(value, (int, float)):
                if action == "set_rainbow_color_intensity":
                    self.infos["rainbow_color_intensity"] = float(value)
                    return {"applied": True}
                if action == "set_pulsar_tail_length":
                    self.infos["pulsar_tail_length"] = float(value)
                    return {"applied": True}
                if action == "set_trigger_interval":
                    self.infos["trigger_interval"] = float(value)
                    return {"applied": True}
                if action == "set_sweep_duration":
                    self.infos["sweep_duration"] = float(value)
                    return {"applied": True}
            return {"applied": False, "reason": "invalid_value"}

        if page == "system":
            if action in {"restart_python_loop", "restart_raspberry_pi"}:
                self.logger.warning("(MM) System action requested via web interface: %s", action)
                return {"applied": False, "reason": "system_action_not_implemented"}

        return {"applied": False, "reason": "unsupported_instruction"}

    def pick_a_random_conf(self) -> Dict[str, Any]:
        """
        Select a random configuration from the unblocked playlists using a shuffle bag approach.

        Returns:
            dict: The selected configuration dictionary.
        """
        # If our shuffle bag is empty, we must refill it with all available configurations
        if len(self.shuffle_bag) == 0:
            for playlist_index in range(len(self.playlists)):
                if not self.blocked_playlists[playlist_index]:
                    playlist_name = self.playlists[playlist_index]
                    # Add every configuration from this playlist into the bag
                    for conf_index in range(len(self.configurations[playlist_name])):
                        self.shuffle_bag.append({
                            "playlist": playlist_name,
                            "index": conf_index,
                            "name": self.configurations[playlist_name][conf_index]["name"],
                            "modes": self.configurations[playlist_name][conf_index]["modes"],
                            "way": self.configurations[playlist_name][conf_index]["way"]
                        })
            # Shuffle the bag like a deck of cards
            random.shuffle(self.shuffle_bag)

        # Fallback just in case all playlists are somehow blocked preventing refill
        if len(self.shuffle_bag) == 0:
            return self.activ_configuration

        # Pop the next configuration from the shuffle bag
        new_conf = self.shuffle_bag.pop()

        self.logger.debug(f"(MM)   pick_a_random_conf() :     conf = {new_conf}")
        return new_conf

            