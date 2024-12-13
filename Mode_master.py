import numpy as np
import asyncio
import random
import time

from Mode_Globaux import Matrix_General as Matrix_General
from Mode_Globaux import Matrix as Matrix
from Mode_Globaux import Matrix_data as Matrix_data
from Mode_Globaux import Segments_Locations as Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou as Mode_Tchou_Tchou

import Segment as Segment
import Listener as Listener
import data.Data_reader as Data_reader


import Fake_leds
#import neopixel
#import board


class Mode_master:

    segments_list = []
    segments_names_to_index = {}
    activ_configuration = 0
    configurations = {}
    playlists = []
    blocked_playlists = []
    configuration_duration = 600000
    next_change_of_configuration_time = 0
    current_time = time.time()

    def __init__(self, listener , infos):
        self.infos = infos
        self.listener = listener
        self.useGlobalMatrix        = infos["useGlobalMatrix"]
        self.onRaspberry            = infos["onRaspberry"]
        self.printTimeOfCalculation = infos["printTimeOfCalculation"]
        self.printModesDetails      = infos["printModesDetails"]
        self.printAppDetails        = infos["printAppDetails"]
        self.printConfigChanges     = infos["printConfigChanges"]

        self.load_configurations()

        if(self.onRaspberry):
            #self.leds = neopixel.NeoPixel(board.D21, 173 + 47 + 48 + 47 + 173 + 89 + 207 + 1, brightness=1, auto_write=False)
            #self.leds2 = neopixel.NeoPixel(board.D18, 800, brightness=1, auto_write=False)
            pass
        else:
            self.leds = Fake_leds.Fake_leds(173 + 47 + 48 + 47 + 173 + 89 + 207 + 1)
            self.leds2 = Fake_leds.Fake_leds(800)

        if (self.useGlobalMatrix):
            self.matrix = Matrix.Matrix()
            self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
            self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)

        self.initiate_segments()
        self.initiate_configuration()

    def set_connector(self, connector):
        self.appli_connector = connector

    async def update_forever(self):
        while True:
            await self.update()
            await asyncio.sleep(0.0001)

    async def update(self):
        if self.printTimeOfCalculation:
            duration = []
            names_of_durations = []

        #==============================================
        if self.printTimeOfCalculation:
            time_listener_update = time.time()

        self.listener.update()

        if self.printTimeOfCalculation:
            duration.append(time.time() - time_listener_update)
            names_of_durations.append("listener.update()")
        #==============================================

        #==============================================
        if self.printTimeOfCalculation:
            time_matrix_general_update = time.time()

        if self.useGlobalMatrix:
            self.matrix_general.update()

        if self.printTimeOfCalculation:
            duration.append(time.time() - time_matrix_general_update)
            names_of_durations.append("matrix_general.update()")
        #==============================================

        #==============================================
        if self.printTimeOfCalculation:
            time_led_show = time.time()

        self.leds.show()
        self.leds2.show()

        if self.printTimeOfCalculation:
            duration.append(time.time() - time_led_show)
            names_of_durations.append("leds.show()")
        #==============================================

        #==============================================
        if self.printTimeOfCalculation:
            time_segments_update= time.time()

        for seg_index in range(len(self.segments_list)):
            if self.useGlobalMatrix:
                self.segments_list[seg_index].global_rgb_list = self.matrix_general.segment_values[0]
            self.segments_list[seg_index].update()

        if self.printTimeOfCalculation:
            duration.append(time.time() - time_segments_update)
            names_of_durations.append("segments.update()")
        #==============================================

        #==============================================
        self.current_time = time.time()
        if self.current_time > self.next_change_of_configuration_time:
            await self.change_configuration()
        #==============================================

        if self.printTimeOfCalculation:
            print("=======================================================================")
            total = np.sum(duration)
            print("   |(MM) total = ", total , " secondes")
            nb_of_it_per_sec = 1 / total
            print("   |(MM) soit ", nb_of_it_per_sec, " itérations par seconde")
            for k in range(len(duration)):
                print("   |(MM) " ,names_of_durations[k], "  :  " , 100*float(duration[k])/total , "%")


    def load_configurations(self):
        # Le Data_reader load depuis google excel et construit notre dictionnaire
        self.data_reader = Data_reader.Data_reader(self.infos)
        self.configurations, self.playlists = self.data_reader.configurations, self.data_reader.playlists
        # On initialise le bloquage des playlists (Par défaut, on les prend toutes)
        for _ in self.playlists:
            self.blocked_playlists.append(False)

    async def change_configuration(self):
        """Add your configuration change logic here."""
        # Implement configuration change here, as this seems to involve asynchronous activity
        pass

    def update_segments_modes(self, info_margin, showInfos):
        for segment in self.segments_list:
            if not segment.isBlocked:
                if showInfos:
                    print(info_margin, "(MM) update_segments_modes : ", segment.name, "non bloqué donc on ordonne de le changer")
                segment.change_mode(self.activ_configuration["modes"][segment.name] , info_margin + "   ", showInfos)
                segment.change_way(self.activ_configuration["way"][segment.name] , info_margin + "   ", showInfos)

 

    def initiate_configuration(self):
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self.activ_configuration = self.pick_a_random_conf("   " , self.printConfigChanges)
        self.update_segments_modes("   " , self.printConfigChanges)
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        if(self.printConfigChanges):
            print("(MM)   initiate_configuration()  :     next_change_of_conf_time = " , self.next_change_of_configuration_time)

        

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
                
        v4 =  {"name":"Segment v4"  , "size" : 173 , "order" : 0 , "orientation" : "vertical"   , "alcool" : False}
        h32 = {"name":"Segment h32" , "size" : 48  , "order" : 1 , "orientation" : "horizontal" , "alcool" : False}
        h31 = {"name":"Segment h31" , "size" : 48  , "order" : 2 , "orientation" : "horizontal" , "alcool" : False}
        h30 = {"name":"Segment h30" , "size" : 47  , "order" : 3 , "orientation" : "horizontal" , "alcool" : False}
        v3 =  {"name":"Segment v3"  , "size" : 173 , "order" : 4 , "orientation" : "horizontal" , "alcool" : False}
        h20 = {"name":"Segment h20" , "size" : 91  , "order" : 5 , "orientation" : "horizontal" , "alcool" : True }
        h00 = {"name":"Segment h00" , "size" : 205 , "order" : 6 , "orientation" : "horizontal" , "alcool" : True }

        v2 =  {"name":"Segment v2"  , "size" : 173 , "order" : 7 , "orientation" : "vertical"   , "alcool" : False}
        h11 = {"name":"Segment h11" , "size" : 87  , "order" : 8 , "orientation" : "horizontal" , "alcool" : False}
        h10 = {"name":"Segment h10" , "size" : 86  , "order" : 9 , "orientation" : "horizontal" , "alcool" : False}
        v1 =  {"name":"Segment v1"  , "size" : 173 , "order" : 10 ,"orientation" : "horizontal" , "alcool" : False}

        segs_1 = [v4 , h32 , h31 , h30 , v3 , h20 , h00]
        segs_2 = [v2 , h11 , h10 , v1]

        add_segments(segs_1,self.leds)
        add_segments(segs_2,self.leds2)



        

        

        """
        
        indexes = [i for i in range(173)]
        segment_v4 = Segment.Segment("Segment v4",self.listener, self.leds ,indexes,"vertical",False,self.infos)
        indexes = [i for i in range(173,173+48)]
        segment_h32 = Segment.Segment("Segment h32",self.listener, self.leds , indexes,"horizontal",False,self.infos)
        indexes = [i for i in range(173+48,173+48+48)]
        segment_h31 = Segment.Segment("Segment h31",self.listener, self.leds , indexes,"horizontal",False,self.infos)
        indexes = [i for i in range(173+48+48,173+48+48+47)]
        segment_h30 = Segment.Segment("Segment h30",self.listener, self.leds , indexes,"horizontal",False,self.infos)
        indexes = [i for i in range(173+48+48+47,173+48+48+47+173)]
        segment_v3 = Segment.Segment("Segment v3",self.listener, self.leds , indexes,"vertical",False,self.infos)
        indexes = [i for i in range(173+48+48+47+173,173+48+48+47+173+91)]
        segment_h20 = Segment.Segment("Segment h20",self.listener, self.leds , indexes,"horizontal",True,self.infos)
        indexes = [i for i in range(173+48+48+47+173+91,173+48+48+47+173+91+205)]
        segment_h00 = Segment.Segment("Segment h00",self.listener, self.leds , indexes,"horizontal",True,self.infos)
        indexes = [i for i in range(0,173)]
        segment_v2 = Segment.Segment("Segment v2",self.listener, self.leds2 , indexes,"vertical",False,self.infos)
        indexes = [i for i in range(173,173+87)]
        segment_h11 = Segment.Segment("Segment h11",self.listener, self.leds2 , indexes,"horizontal",False,self.infos)
        indexes = [i for i in range(173+87,173+87+86)]
        segment_h10 = Segment.Segment("Segment h10",self.listener, self.leds2 , indexes,"horizontal",False,self.infos)
        indexes = [i for i in range(173+87+86,173+87+86+173)]
        segment_v1 = Segment.Segment("Segment v1",self.listener, self.leds2 , indexes,"vertical",False,self.infos)
        self.segments_list.append(segment_v4)
        self.segments_list.append(segment_h32)
        self.segments_list.append(segment_h31)
        self.segments_list.append(segment_h30)
        self.segments_list.append(segment_v3)
        self.segments_list.append(segment_h20)
        self.segments_list.append(segment_h00)
        self.segments_list.append(segment_v2)
        self.segments_list.append(segment_h11)
        self.segments_list.append(segment_h10)
        self.segments_list.append(segment_v1)
        self.segments_names_to_index["Segment v4"]=0
        self.segments_names_to_index["Segment h32"]=1
        self.segments_names_to_index["Segment h31"]=2
        self.segments_names_to_index["Segment h30"]=3
        self.segments_names_to_index["Segment v3"]=4
        self.segments_names_to_index["Segment h20"]=5
        self.segments_names_to_index["Segment h00"]=6
        self.segments_names_to_index["Segment v2"]=7
        self.segments_names_to_index["Segment h11"]=8
        self.segments_names_to_index["Segment h10"]=9
        self.segments_names_to_index["Segment v1"]=10
"""

    def change_configuration(self , info_margin , showInfos):
        #on pick une conf nouvelle au pif
        last_configuration = self.activ_configuration
        while (last_configuration==self.activ_configuration):
            self.activ_configuration = self.pick_a_random_conf( info_margin+"   " , showInfos)
        #on l'applique à tous les segments
        self.update_segments_modes( info_margin , showInfos )
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = self.current_time + self.configuration_duration
        if(showInfos):
            print(info_margin + "(MM)   change_configuration()  :     next_change_of_conf_time = " + self.next_change_of_configuration_time)

    def pick_a_random_conf(self , info_margin , showInfos):
        reachable_playlists = []
        new_conf={}
        #On charge les playlists activées
        for playlist_index in range(len(self.playlists)):
            if (not self.blocked_playlists[playlist_index]) :
                reachable_playlists.append(self.playlists[playlist_index])

        #On en choisit une au pif
        random_playlist_index = random.randint(0,len(reachable_playlists)-1)
        playlist_name = reachable_playlists[random_playlist_index]

        new_conf["playlist"] = playlist_name

        #On pick une conf au pif dans cette playlist
        random_conf_index = random.randint(0,len(self.configurations[playlist_name])-1)
        new_conf["index"] = random_conf_index
        new_conf["name"] = self.configurations[playlist_name][random_conf_index]["name"]
        new_conf["modes"] = self.configurations[playlist_name][random_conf_index]["modes"]
        new_conf["way"] = self.configurations[playlist_name][random_conf_index]["way"]

        if(showInfos):
            print(info_margin + "(MM)   pick_a_random_conf() :     conf = " + str(new_conf))
        return new_conf

    def obey_orders(self,orders):
        for order in orders:
            self.obey_order(order)
        
    def obey_order(self,order):
        splited_order = order.split(":")
        category = splited_order[0]                     #str category c ["block","unblock","change","force","update","special"]
        
        print("category = ",category)
        if (category == "block"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                print("(MM) On veut bloquer le segment "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].block()
            

        elif (category == "unblock"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                print("(MM) On veut débloquer le segment "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].unBlock()
            

        elif (category == "change_mode"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            if (self.printAppDetails):
                print("(MM) On veut changer le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].change_mode(new_mode , "" , self.show_modes_details)
            
        elif (category == "change_way"):
            segment_name = splited_order[1]
            new_way = splited_order[2]
            if (self.printAppDetails):
                print("(MM) On veut changer le "+segment_name+" pour le sens "+new_way)
            self.segments_list[self.segments_names_to_index[segment_name]].change_way(new_way , "" , self.show_modes_details)
            
        elif (category == "switch_way"):
            segment_name = splited_order[1]
            if (self.printAppDetails):
                print("(MM) On veut switch le "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].switch_way("" , self.show_modes_details)
            

        elif (category == "force"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            if (self.printAppDetails):
                print("(MM) On veut FORCER le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].force_mode(new_mode , "" , self.show_modes_details)

        elif (category == "update"):
            parametre = splited_order[1]                            #str parametre c ["sensibilite","luminosite"]
            new_value = int(splited_order[2])
            if (self.printAppDetails):#int sensi,lum c [0:100]
                print("(MM) On veut changer "+parametre+" = "+str(new_value))
            if (parametre == "sensibilite"):
                self.listener.sensi = float(new_value)/100          #On ramene la sensi entre 0 et 1 
            if (parametre == "luminosite"):
                self.listener.luminosite = float(new_value)/100     #On ramene la luminosite entre 0 et 1
                
        elif (category == "calibration"):
            type_cal = splited_order[1]
            phase = splited_order[2]     #str type_cal c ["silence , "bb"]
            if (self.printAppDetails):
                    print("(MM) On veut "+ phase+" une calibration "+type_cal)
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
                print("(MM) On veut lancer le shot ")
            self.segments_list[self.segments_names_to_index["Segment h20"]].modes[4].activate()
            self.segments_list[self.segments_names_to_index["Segment h00"]].modes[4].activate()


            