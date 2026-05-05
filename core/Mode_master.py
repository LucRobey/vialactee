import numpy as np
import asyncio
import logging
import random
import time

from Mode_Globaux import Matrix_General as Matrix_General
from Mode_Globaux import Matrix as Matrix
from Mode_Globaux import Matrix_data as Matrix_data
from Mode_Globaux import Segments_Locations as Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou as Mode_Tchou_Tchou

import core.Segment as Segment
import core.Listener as Listener
import core.Transition_Director as Transition_Director



from contextlib import contextmanager

class Profiler:
    def __init__(self, active, logger):
        self.active = active
        self.logger = logger
        self.durations = []
        self.names = []
        self.start_times = {}

    @contextmanager
    def measure(self, name):
        if self.active:
            start = time.time()
            yield
            self.durations.append(time.time() - start)
            self.names.append(name)
        else:
            yield

    def print_results(self):
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
        self.infos = infos
        self.listener = listener
        self.useGlobalMatrix        = infos.get("useGlobalMatrix", False)
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

        if (self.useGlobalMatrix):
            self.matrix = Matrix.Matrix()
            self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
            self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)

        self.initiate_segments()
        self.initiate_configuration()
        self.transition_director = Transition_Director.Transition_Director(self.listener, self.infos)

    def set_connector(self, connector):
        self.appli_connector = connector

    async def update_forever(self):
        while True:
            await self.update()
            await asyncio.sleep(1/30)

    async def update(self):
        # Profiler cleans up the time_time() boilerplate
        with self.profiler.measure("listener.update()"):
            self.listener.update()

        if self.useGlobalMatrix:
            with self.profiler.measure("matrix_general.update()"):
                self.matrix_general.update()

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
            if self.useGlobalMatrix:
                #get each segment its global value
                getsegments = self.matrix_general.get_segments()
                for seg in self.segments_list:
                    seg.global_rgb_list = getsegments[seg.name]
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
        elif action == "delay_change":
            self.logger.debug("(MM) Delaying configuration change due to audio context.")
            self.next_change_of_configuration_time += 1.0

        self.profiler.print_results()
        # Clean profiler values for next frame
        self.profiler.durations.clear()
        self.profiler.names.clear()


    def load_configurations(self):
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
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self.pick_a_random_conf()
        self.update_segments_modes()
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        self.logger.debug(f"(MM)   initiate_configuration()  :     next_change_of_conf_time = {self.next_change_of_configuration_time}")

        

    def initiate_segments(self):
        def add_segments(info_list , leds):
            offset = 0
            for segment_index in range(len(info_list)):
                seg_infos = info_list[segment_index]
                indexes = [i for i in range(offset,offset+seg_infos["size"])]
                new_segment = Segment.Segment(seg_infos["name"],self.listener, leds ,indexes,seg_infos["orientation"],seg_infos["alcool"],self.infos)
                offset += seg_infos["size"]
                self.segments_list.append(new_segment)
                self.segments_names_to_index[seg_infos["name"]]=seg_infos["order"]
                
        import json
        with open("config/segments.json", "r") as f:
            data = json.load(f)
            
        add_segments(data["segs_1"],self.leds)
        add_segments(data["segs_2"],self.leds2)


    async def change_configuration(self, transition_config=None):
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

    async def force_standby_playlist(self, transition_config=None):
        target_playlist = None
        for p in self.playlists:
            if "chill" in p.lower() or "standby" in p.lower():
                target_playlist = p
                break
                
        if not target_playlist and len(self.playlists) > 0:
            target_playlist = self.playlists[0]
            
        if target_playlist and len(self.configurations.get(target_playlist, [])) > 0:
            self.logger.info(f"(MM) Forcing Standby Playlist: {target_playlist}")
            conf = random.choice(self.configurations[target_playlist])
            self.activ_configuration = {
                "playlist": target_playlist,
                "index": self.configurations[target_playlist].index(conf),
                "name": conf["name"],
                "modes": conf["modes"],
                "way": conf["way"]
            }
            self.update_segments_modes(transition_config)
            self.next_change_of_configuration_time = self.current_time + self.configuration_duration

    def pick_a_random_conf(self):
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

    def obey_orders(self,orders):
        for order in orders:
            self.obey_order(order)
        
    def obey_order(self,order):
        splited_order = order.split(":")
        category = splited_order[0]                     #str category c ["block","unblock","change","force","update","special"]
        
        self.logger.debug(f"category = {category}")
        if (category == "block"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut bloquer le segment {segment_name}")
            self.segments_list[self.segments_names_to_index[segment_name]].block()
            

        elif (category == "unblock"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut débloquer le segment {segment_name}")
            self.segments_list[self.segments_names_to_index[segment_name]].unBlock()
            

        elif (category == "change_mode"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut changer le segment {segment_name} pour le mode {new_mode}")
            self.segments_list[self.segments_names_to_index[segment_name]].change_mode(new_mode)
            
        elif (category == "change_way"):
            segment_name = splited_order[1]
            new_way = splited_order[2]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut changer le {segment_name} pour le sens {new_way}")
            self.segments_list[self.segments_names_to_index[segment_name]].change_way(new_way)
            
        elif (category == "switch_way"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut switch le {segment_name}")
            self.segments_list[self.segments_names_to_index[segment_name]].switch_way()
            

        elif (category == "force"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            if (self.printAppDetails):
                self.logger.debug(f"(MM) On veut FORCER le segment {segment_name} pour le mode {new_mode}")
            self.segments_list[self.segments_names_to_index[segment_name]].force_mode(new_mode)

        elif (category == "update"):
            parametre = splited_order[1]                            #str parametre c ["sensibilite","luminosite"]
            new_value = int(splited_order[2])
            if (self.printAppDetails):#int sensi,lum c [0:100]
                self.logger.debug(f"(MM) On veut changer {parametre} = {new_value}")
            if (parametre == "sensibilite"):
                self.listener.sensi = float(new_value)/100          #On ramene la sensi entre 0 et 1 
            if (parametre == "luminosite"):
                self.listener.luminosite = float(new_value)/100     #On ramene la luminosite entre 0 et 1
                
        elif (category == "calibration"):
            type_cal = splited_order[1]
            phase = splited_order[2]     #str type_cal c ["silence , "bb"]
            if (self.printAppDetails):
                    self.logger.debug(f"(MM) On veut {phase} une calibration {type_cal}")
            if (type_cal == "silence"):
                if (phase == "start"):
                    self.listener.start_silence_calibration()
                elif(phase == "end"):
                    self.listener.stop_silence_calibration()
            elif (type_cal == "bb"):
                if (phase == "start"):
                    self.listener.start_bb_calibration()
                elif(phase == "end"):
                    self.listener.stop_bb_calibration()
            
        elif (category == "special"):
            if (self.printAppDetails):
                self.logger.debug("(MM) On veut lancer le shot ")
            for target_seg in ["Segment h20", "Segment h00"]:
                seg = self.segments_list[self.segments_names_to_index[target_seg]]
                for m_idx, m_name in enumerate(seg.modes_names):
                    if m_name == "Shot":
                        seg.modes[m_idx].activate()
                        break


            