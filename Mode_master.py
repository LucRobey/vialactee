from Mode_Globaux.Mode_Global import Mode_Global
from Mode_Globaux import Matrix_General
from Mode_Globaux import Matrix
from Mode_Globaux import Matrix_data
from Mode_Globaux import Segments_Locations
from Mode_Globaux import Mode_Tchou_Tchou
from Segment import Segment
from Listener import Listener

import board
import neopixel

class Mode_master:


    def __init__(self):
        self.leds = neopixel.NeoPixel(board.D18, 39, brightness=1)

        self.listener = Listener()

        self.matrix = Matrix()
        self.mode_tchou_tchou = Mode_Tchou_Tchou(self.matrix)
        self.matrix_general = Matrix_General(self.mode_tchou_tchou)   

        self.segment = Segment(self.listener, self.leds)
        
        
    
    def update(self):
        self.matrix_general.update()
        list_rgbd = self.matrix_general.get_segments()[0]
        self.segment.update(list_rgbd)


    def build_configurations(self):
        pass