import random
import time

from Mode_Globaux.Mode_Global import Mode_Global
from Mode_Globaux import Matrix_General as Matrix_General
from Mode_Globaux import Matrix as Matrix
from Mode_Globaux import Matrix_data as Matrix_data
from Mode_Globaux import Segments_Locations as Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou as Mode_Tchou_Tchou

import Connector
import Segment as Segment
import Listener as Listener
import data.Data_reader as Data_reader

import board
import neopixel

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

    def __init__(self):
            
        self.appli_connector = Connector.Connector()

        self.load_configurations()

        self.leds = neopixel.NeoPixel(board.D21, 173+47+48+47+173+89+207+1, brightness=1,auto_write=False)
        self.leds2 = neopixel.NeoPixel(board.D18, 800, brightness=1,auto_write=False)

        
        self.listener = Listener.Listener()

        self.matrix = Matrix.Matrix()
        self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
        self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)
        
        #print(self.matrix_general.get_segments())

        self.initiate_segments()

        self.initiate_configuration()
        
    
    def update(self):
        orders = self.appli_connector.update()
        if(orders!=[] and orders!=None):
            for order in orders:
                self.obey_order(order)
        
        self.listener.update()
        #self.matrix_general.update()
        
        for seg_index in range(len(self.segments_list)):
            #print("matrix" , self.matrix_general.segment_values[0])
            #self.segments_list[seg_index].global_rgb_list = self.matrix_general.segment_values[0]
            self.segments_list[seg_index].update()
        self.leds.show()
        self.leds2.show()

        self.current_time = time.time()
        if(self.current_time > self.next_change_of_configuration_time):
            self.change_configuration()

    def load_configurations(self):
        self.data_reader = Data_reader.Data_reader()
        self.configurations , self.playlists = self.data_reader.configurations
        for _ in self.playlists:
            self.blocked_playlists = False

    def update_segments_modes(self , info_margin , showInfos):
        for segment in self.segments_list:
            if (not segment.isBlocked):
                if(showInfos):
                    print(info_margin,"(MM) update_segments_modes : ",segment.name," non bloqué donc on le change")
                segment.change_mode(self.activ_configuration["modes"][segment.name], info_margin+"   " , showInfos)
                    

    def initiate_configuration(self , info_margin , showInfos):
        self.activ_configuration = self.activ_configuration = self.pick_a_random_conf(info_margin+"   " , showInfos)
        self.update_segments_modes(info_margin , showInfos)
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        if(showInfos):
            print(info_margin + "(MM)   initiate_configuration()  :     next_change_of_conf_time = " + self.next_change_of_configuration_time)

        

    def initiate_segments(self):
        indexes = [i for i in range(173)]
        segment_v4 = Segment.Segment("Segment v4",self.listener, self.leds ,indexes, self.matrix_general.segment_values[0],"vertical",False)
        indexes = [i for i in range(173,173+48)]
        segment_h32 = Segment.Segment("Segment h32",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False)
        indexes = [i for i in range(173+48,173+48+48)]
        segment_h31 = Segment.Segment("Segment h31",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False)
        indexes = [i for i in range(173+48+48,173+48+48+47)]
        segment_h30 = Segment.Segment("Segment h30",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False)
        indexes = [i for i in range(173+48+48+47,173+48+48+47+173)]
        segment_v3 = Segment.Segment("Segment v3",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"vertical",False)
        indexes = [i for i in range(173+48+48+47+173,173+48+48+47+173+91)]
        segment_h20 = Segment.Segment("Segment h20",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",True)
        indexes = [i for i in range(173+48+48+47+173+91,173+48+48+47+173+91+205)]
        segment_h00 = Segment.Segment("Segment h00",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",True)
        indexes = [i for i in range(0,173)]
        segment_v2 = Segment.Segment("Segment v2",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"vertical",False)
        indexes = [i for i in range(173,173+87)]
        segment_h11 = Segment.Segment("Segment h11",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"horizontal",False)
        indexes = [i for i in range(173+87,173+87+86)]
        segment_h10 = Segment.Segment("Segment h10",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"horizontal",False)
        indexes = [i for i in range(173+87+86,173+87+86+173)]
        segment_v1 = Segment.Segment("Segment v1",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"vertical",False)
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


    def change_configuration(self , info_margin , showInfos):
        last_configuration = self.activ_configuration
        while (last_configuration==self.activ_configuration):
            self.activ_configuration = self.pick_a_random_conf( info_margin+"   " , showInfos)
        self.update_segments_modes( info_margin , showInfos )
        self.next_change_of_configuration_time = self.current_time + self.configuration_duration
        if(showInfos):
            print(info_margin + "(MM)   change_configuration()  :     next_change_of_conf_time = " + self.next_change_of_configuration_time)

    def pick_a_random_conf(self , info_margin , showInfos):
        reachable_playlists = []
        new_conf={}
        for playlist_index in range(len(self.playlists)):
            if (not self.blocked_playlists[playlist_index]) :
                reachable_playlists.append(self.playlists[playlist_index])

        random_playlist_index = random.randint(0,len(reachable_playlists)-1)
        playlist_name = reachable_playlists[random_playlist_index]

        new_conf["playlist"] = playlist_name
        random_conf_index = random.randint(0,len(self.configurations[playlist_name])-1)
        new_conf["index"] = random_conf_index

        new_conf["name"] = self.configurations[playlist_name][random_conf_index]["name"]

        new_conf["modes"] = self.configurations[playlist_name][random_conf_index]["modes"]

        if(showInfos):
            print(info_margin + "(MM)   pick_a_random_conf() :     conf = " + new_conf)
        return new_conf

        
    def force_alcool_randomer(self):
        self.segments_list[0].prepare_for_alcool_randomer()
        self.segments_list[0].block()
        self.waitEndOfBlockage[0] = True
        
    def obey_order(self,order):
        splited_order = order.split(":")
        category = splited_order[0]
        
        if (category == "block"):
            segment_name = splited_order[1]
            print("(MM) On bloque le segment "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].block()
            

        elif (category == "unblock"):
            segment_name = splited_order[1]
            print("(MM) On  débloque le segment "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].unBlock()
            

        elif (category == "change"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            print("(MM) On essaie de changer le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].change_mode(new_mode)
            

        elif (category == "force"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            print("(MM) On FORCE le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].force_mode(new_mode)
            
        elif (category == "special"):
            print("(MM) On lance le shot ")
            self.segments_list[self.segments_names_to_index["Segment h20"]].modes[4].activate()
            self.segments_list[self.segments_names_to_index["Segment h00"]].modes[4].activate()
 
            
            

            