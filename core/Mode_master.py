import numpy as np
import asyncio
import logging
import random
import time

import core.Segment as Segment
import core.Listener as Listener
import core.Transition_Director as Transition_Director



from contextlib import contextmanager

class Profiler:
    """
    A simple context-manager based profiler to measure execution time of code blocks.
    """
    def __init__(self, active, logger):
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
    def measure(self, name):
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

    def print_results(self):
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

    segments_list = []
    segments_names_to_index = {}
    activ_configuration = 0
    configurations = {}
    playlists = []
    blocked_playlists = []
    configuration_duration = 6
    next_change_of_configuration_time = 0
    current_time = time.time()

    def __init__(self, listener, infos, leds1, leds2):
        """
        Initialize the Mode_master.

        Args:
            listener: Reference to the global audio listener.
            infos (dict): Dictionary containing global configuration and metadata.
            leds1: Reference to the primary LED strip hardware/simulator.
            leds2: Reference to the secondary LED strip hardware/simulator.
        """
        self.infos = infos
        self.listener = listener
        self.onRaspberry            = infos.get("onRaspberry", False)
        self.printTimeOfCalculation = infos.get("printTimeOfCalculation", False)
        self.printModesDetails      = infos.get("printModesDetails", False)
        self.printAppDetails        = infos.get("printAppDetails", False)
        self.printConfigChanges     = infos.get("printConfigChanges", False)

        self.leds = leds1
        self.leds2 = leds2
        self.logger = logging.getLogger("Mode_master")
        self.profiler = Profiler(self.printTimeOfCalculation, self.logger)

        self.load_configurations()

        self.initiate_segments()
        self.initiate_configuration()
        self.transition_director = Transition_Director.Transition_Director(self.listener, self.infos)

    def set_connector(self, connector):
        """
        Set the application connector for external communications.

        Args:
            connector: The connector instance.
        """
        self.appli_connector = connector

    async def update_forever(self):
        """
        Continuously update the system at approximately 30 FPS.
        """
        while True:
            await self.update()
            await asyncio.sleep(1/30)

    async def update(self):
        """
        Perform a single update loop iteration.

        Updates the audio listener, flushes hardware LED buffers, updates all
        segments, and evaluates global transitions via the Transition_Director.
        """
        # Profiler cleans up the time_time() boilerplate
        with self.profiler.measure("listener.update()"):
            self.listener.update()

        with self.profiler.measure("leds.show()"):
            is_rpi_hardware = "Rpi_NeoPixels" in str(type(self.leds))
            if self.infos.get("onRaspberry", False) or self.infos.get("HARDWARE_MODE") == "rpi" or is_rpi_hardware:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.leds.show)
                await loop.run_in_executor(None, self.leds2.show)
            else:
                self.leds.show()
                self.leds2.show()

        with self.profiler.measure("segments.update()"):
            for seg_index in range(len(self.segments_list)):
                self.segments_list[seg_index].update()

        #==============================================
        self.current_time = time.time()
        
        action, transition_config = self.transition_director.evaluate_context(self.current_time, self.next_change_of_configuration_time)
        
        if action == "force_standby":
            await self.force_standby_playlist(transition_config)
            self.transition_director.is_in_standby = True
        elif action == "allow_change":
            await self.change_configuration(transition_config)

        self.profiler.print_results()
        # Clean profiler values for next frame
        self.profiler.durations.clear()
        self.profiler.names.clear()


    def load_configurations(self):
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

        # On initialise le bloquage des playlists (Par défaut, on les prend toutes)
        for _ in self.playlists:
            self.blocked_playlists.append(False)
        self.shuffle_bag = []
    def update_segments_modes(self, transition_config=None):
        """
        Apply the active configuration to all relevant segments.

        Args:
            transition_config (dict, optional): Configuration defining the type and
                duration of the transition. Defaults to None.
        """
        targeted_segments = None
        if transition_config and "segments" in transition_config:
            targeted_segments = transition_config["segments"]

        for segment in self.segments_list:
            if not segment.isBlocked:
                # Skip segments entirely if a local change targeted specific ones
                if targeted_segments is not None and segment.name not in targeted_segments:
                    continue

                self.logger.debug(f"(MM) update_segments_modes : {segment.name} non bloqué donc on ordonne de le changer")
                segment.change_mode(self.activ_configuration["modes"][segment.name], transition_config)
                segment.change_way(self.activ_configuration["way"][segment.name])

 

    def initiate_configuration(self):
        """
        Initialize the starting configuration by picking a random one from available playlists.
        """
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self.pick_a_random_conf()
        self.update_segments_modes()
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        self.logger.debug(f"(MM)   initiate_configuration()  :     next_change_of_conf_time = {self.next_change_of_configuration_time}")

        

    def initiate_segments(self):
        """
        Initialize all segments based on the segments.json configuration file.
        """
        def add_segments(info_list , leds):
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
            
        add_segments(data["segs_1"],self.leds)
        add_segments(data["segs_2"],self.leds2)


    async def change_configuration(self, transition_config=None):
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
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = self.current_time + self.configuration_duration
        self.logger.debug(f"(MM)   change_configuration()  :     next_change_of_conf_time = {self.next_change_of_configuration_time}")

    def pick_a_random_conf(self):
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

            