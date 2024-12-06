import random
import time

from Mode_Globaux.Mode_Global import Mode_Global
from Mode_Globaux import Matrix_General as Matrix_General
from Mode_Globaux import Matrix as Matrix
from Mode_Globaux import Matrix_data as Matrix_data
from Mode_Globaux import Segments_Locations as Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou as Mode_Tchou_Tchou

import connectors.ESP32_Connector as ESP32_Connector
import connectors.Connector as  Connector
import Segment as Segment
import Listener as Listener
import data.Data_reader as Data_reader


class Mode_master:

    useGlobalMatrix = False
    printTimeOfCalculation = False
    show_modes_details = True

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

        self.leds = neopixel.NeoPixel(board.D21, 173+47+48+47+173+89+207+1, brightness=1,auto_write=False) #self.leds = [[0 , 255 , 128] for _ in range(900)]
        self.leds2 = neopixel.NeoPixel(board.D18, 800, brightness=1,auto_write=False)#self.leds2 = [[0 , 255, 128] for _ in range(800)]
        
        #print(self.leds)
        
        #self.ESP_connector = ESP32_Connector.ESP32_Connector(self.leds,self.leds2)

        
        self.listener = Listener.Listener()

        if (self.useGlobalMatrix):
            self.matrix = Matrix.Matrix()
            self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
            self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)
        

        self.initiate_segments()

        self.initiate_configuration("",self.show_modes_details)
   
    
    def update(self):

        #==============================================
        if (self.printTimeOfCalculation):
            time1 = time.time()

        orders = self.appli_connector.update()
        if(orders!=[] and orders!=None):
            for order in orders:
                self.obey_order(order)

        if (self.printTimeOfCalculation):
            duration1 = time.time() - time1
        #==============================================

        #==============================================
        if (self.printTimeOfCalculation):
            time2 = time.time()

        self.listener.update()

        if (self.printTimeOfCalculation):    
            duration2 = time.time() - time2
        #==============================================

        #==============================================
        if (self.printTimeOfCalculation):
            time3 = time.time()

        if (self.useGlobalMatrix):
            self.matrix_general.update()

        if (self.printTimeOfCalculation):    
            duration3 = time.time() - time3
        #==============================================
        
        #==============================================
        if (self.printTimeOfCalculation):
            time4 = time.time()

        for seg_index in range(len(self.segments_list)):
            if (self.useGlobalMatrix):
                self.segments_list[seg_index].global_rgb_list = self.matrix_general.segment_values[0]
            self.segments_list[seg_index].update()
        
        if (self.printTimeOfCalculation):
            duration4 = time.time() - time3
        #==============================================

        #==============================================
        if (self.printTimeOfCalculation):
            time5 = time.time()
        self.ESP_connector.send_to_ESP1()
        if (self.printTimeOfCalculation):
            duration5 = time.time() - time5
        #==============================================

        #==============================================
        self.current_time = time.time()
        if(self.current_time > self.next_change_of_configuration_time):
            self.change_configuration()
        #==============================================

        if (self.printTimeOfCalculation):
            total = duration1 + duration2 + duration3 + duration4 + duration5
            print("total = ", total)
            print("app :", 100*(duration1/total),
                    " , listen() :" , 100*(duration2/total),
                    " update() :"   , 100*(duration3/total) ,
                    " global : "    , 100*(duration4/total),
                    " espConn : "   , 100*(duration5/total) )

    def load_configurations(self):
        #Le Data_reader load depuis google excel et construit notre dictionnaire
        self.data_reader = Data_reader.Data_reader()
        self.configurations , self.playlists = self.data_reader.configurations , self.data_reader.playlists
        #On initialise le bloquage des playlists (Par default, on les prend toutes)
        for _ in self.playlists:
            self.blocked_playlists.append(False)

    def update_segments_modes(self , info_margin , showInfos):
        for segment in self.segments_list:
            if (not segment.isBlocked):
                if(showInfos):
                    print(info_margin,"(MM) update_segments_modes : ",segment.name," non bloqué donc on ordonne de le changer")
                segment.change_mode(self.activ_configuration["modes"][segment.name], info_margin+"   " , showInfos)
                    

    def initiate_configuration(self , info_margin , showInfos):
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self.activ_configuration = self.pick_a_random_conf(info_margin+"   " , showInfos)
        self.update_segments_modes(info_margin , showInfos)
        #On set un temps pour le futur changement de conf
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        if(showInfos):
            print(info_margin + "(MM)   initiate_configuration()  :     next_change_of_conf_time = " , self.next_change_of_configuration_time)

        

    def initiate_segments(self):
        if(not self.useGlobalMatrix):
            self.useGlobalMatrix=[0]
        indexes = [i for i in range(173)]
        segment_v4 = Segment.Segment("Segment v4",self.listener, self.leds ,indexes, self.matrix_general.segment_values[0],"vertical",False,self.show_modes_details , self.useGlobalMatrix)
        indexes = [i for i in range(173,173+48)]
        segment_h32 = Segment.Segment("Segment h32",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+48,173+48+48)]
        segment_h31 = Segment.Segment("Segment h31",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+48+48,173+48+48+47)]
        segment_h30 = Segment.Segment("Segment h30",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+48+48+47,173+48+48+47+173)]
        segment_v3 = Segment.Segment("Segment v3",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"vertical",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+48+48+47+173,173+48+48+47+173+91)]
        segment_h20 = Segment.Segment("Segment h20",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",True,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+48+48+47+173+91,173+48+48+47+173+91+205)]
        segment_h00 = Segment.Segment("Segment h00",self.listener, self.leds , indexes,self.matrix_general.segment_values[0],"horizontal",True,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(0,173)]
        segment_v2 = Segment.Segment("Segment v2",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"vertical",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173,173+87)]
        segment_h11 = Segment.Segment("Segment h11",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"horizontal",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+87,173+87+86)]
        segment_h10 = Segment.Segment("Segment h10",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"horizontal",False,self.show_modes_details,self.useGlobalMatrix)
        indexes = [i for i in range(173+87+86,173+87+86+173)]
        segment_v1 = Segment.Segment("Segment v1",self.listener, self.leds2 , indexes,self.matrix_general.segment_values[0],"vertical",False,self.show_modes_details,self.useGlobalMatrix)
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

        if(showInfos):
            print(info_margin + "(MM)   pick_a_random_conf() :     conf = " + str(new_conf))
        return new_conf

        
        
    def obey_order(self,order):
        splited_order = order.split(":")
        category = splited_order[0]                     #str category c ["block","unblock","change","force","update","special"]
        
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
            self.segments_list[self.segments_names_to_index[segment_name]].change_mode(new_mode , "" , self.show_modes_details)
            

        elif (category == "force"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            print("(MM) On FORCE le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].force_mode(new_mode)

        elif (category == "update"):
            parametre = splited_order[1]                            #str parametre c ["sensibilite","luminosite"]
            new_value = int(splited_order[2])                       #int sensi,lum c [0:100]
            print("(MM) New "+parametre+" = "+new_value)
            if (parametre == "sensibilite"):
                self.listener.sensi = float(new_value)/100          #On ramene la sensi entre 0 et 1 
            if (parametre == "luminosite"):
                self.listener.luminosite = float(new_value)/100     #On ramene la luminosite entre 0 et 1 
            
        elif (category == "special"):
            print("(MM) On lance le shot ")
            self.segments_list[self.segments_names_to_index["Segment h20"]].modes[4].activate()
            self.segments_list[self.segments_names_to_index["Segment h00"]].modes[4].activate()

        
 
            
            

            