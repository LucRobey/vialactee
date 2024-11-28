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
    configurations = []
    configuration_duration = 60
    next_change_of_configuration_time = 0 
    current_time = time.time()

    def __init__(self):
            
        self.connector = Connector.Connector()

        self.load_configurations()

        self.leds = neopixel.NeoPixel(board.D18, 51, brightness=1)

        self.listener = Listener.Listener()

        self.matrix = Matrix.Matrix()
        self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
        self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)
        
        print(self.matrix_general.get_segments())

        self.initiate_segments()

        self.initiate_configuration()
        
    
    def update(self):
        orders = self.connector.update()
        if(orders!=[] and orders!=None):
            for order in orders:
                self.obey_order(order)
        
        #self.matrix_general.update()
        
        for seg_index in range(len(self.segments_list)):
            #print("matrix" , self.matrix_general.segment_values[0])
            #self.segments_list[seg_index].global_rgb_list = self.matrix_general.segment_values[0]
            self.segments_list[seg_index].update()
            if ( self.waitEndOfBlockage[seg_index] ):
                if ( not self.segments_list[seg_index].isBlocked ):
                    self.waitEndOfBlockage[seg_index] = False
                    self.segments_list[seg_index].change_mode("Rainbow_mode")

        self.current_time = time.time()
        if(self.current_time > self.next_change_of_configuration_time):
            self.change_configuration()

    def load_configurations(self):
        self.data_reader = Data_reader.Data_reader()
        self.configurations = self.data_reader.configurations

    def update_segments_modes(self):
        for segment in self.segments_list:
            if (not segment.isBlocked):
                if(self.configurations[self.activ_configuration]!=segment.get_current_mode()):
                    print("self.configurations = ",self.configurations)
                    print("self.configurations[self.activ_configuration] = ",self.configurations[self.activ_configuration])
                    segment.change_mode(self.configurations[self.activ_configuration]["config"])
                    

    def initiate_configuration(self):
        self.activ_configuration = random.randint(0,len(self.configurations)-1)
        print("(MM) initialisation : configuration numéro :" , self.activ_configuration)
        self.update_segments_modes()
        self.next_change_of_configuration_time = time.time() + self.configuration_duration
        
        self.waitEndOfBlockage = []
        for _ in range(len(self.segments_list)):
            self.waitEndOfBlockage.append(False)

    def initiate_segments(self):
        segment_h00 = Segment.Segment("Segment h00",self.listener, self.leds , self.matrix_general.segment_values[0],"horizontal",True)
        self.segments_list.append(segment_h00)
        self.segments_names_to_index["Segment h00"]=0

    def change_configuration(self):
        last_configuration = self.activ_configuration
        while (last_configuration==self.activ_configuration):
            self.activ_configuration = random.randint(0,len(self.configurations))
        self.update_segments_modes()
        self.next_change_of_configuration_time = self.current_time + self.configuration_duration
        
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
            

        if (category == "unblock"):
            segment_name = splited_order[1]
            print("(MM) On  débloque le segment "+segment_name)
            self.segments_list[self.segments_names_to_index[segment_name]].unBlock()
            

        if (category == "change"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            print("(MM) On essaie de changer le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].change_mode(new_mode)
            

        if (category == "force"):
            segment_name = splited_order[1]
            new_mode = splited_order[2]
            print("(MM) On FORCE le segment "+segment_name+" pour le mode "+new_mode)
            self.segments_list[self.segments_names_to_index[segment_name]].force_mode(new_mode)
            

            