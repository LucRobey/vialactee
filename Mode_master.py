import random
import time

from Mode_Globaux.Mode_Global import Mode_Global
from Mode_Globaux import Matrix_General as Matrix_General
from Mode_Globaux import Matrix as Matrix
from Mode_Globaux import Matrix_data as Matrix_data
from Mode_Globaux import Segments_Locations as Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou as Mode_Tchou_Tchou

import Segment as Segment
import Listener as Listener
import data.Data_reader as Data_reader

import board
import neopixel

class Mode_master:

    segments_list = []
    activ_configuration = 0
    configurations = []
    configuration_duration = 60
    next_change_of_configuration_time = 0 
    current_time = time.time()

    def __init__(self):

        self.load_configurations()

        self.leds = neopixel.NeoPixel(board.D18, 39, brightness=1)

        self.listener = Listener.Listener()

        self.matrix = Matrix.Matrix()
        self.mode_tchou_tchou = Mode_Tchou_Tchou.Mode_Tchou_Tchou(self.matrix)
        self.matrix_general = Matrix_General.Matrix_General(self.mode_tchou_tchou)   

        self.segments_list.append(Segment.Segment("segment1",self.listener, self.leds))

        self.initiate_configuration()
        
    
    def update(self):
        self.matrix_general.update()
        list_rgbd = self.matrix_general.get_segments()[1]
        self.segments_list[0].update(list_rgbd)


        self.current_time = time.time()
        if(self.current_time > self.next_change_of_configuration_time):
            self.change_configuration()

    def load_configurations(self):
        self.data_reader = Data_reader.Data_reader()
        self.configurations = self.data_reader.configurations

    def update_segments_modes(self):
        for segment in self.segments_list:
            segment.change_mode(self.configurations[self.activ_configuration])

    def initiate_configuration(self):
        self.activ_configuration = random.randint(0,len(self.configurations))
        self.update_segments_modes()
        self.next_change_of_configuration_time = time.time() + self.configuration_duration

    def change_configuration(self):
        last_configuration = self.activ_configuration
        while (last_configuration==self.activ_configuration):
            self.activ_configuration = random.randint(0,len(self.configurations))
        self.update_segments_modes()
        self.next_change_of_configuration_time = self.current_time + self.configuration_duration