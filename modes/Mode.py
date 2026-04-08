import calculations.rgb_hsv as RGB_HSV
import time
import numpy as np
from typing import List, Dict, Any

class Mode:

    listener = None
    white = RGB_HSV.fromHSV_toRGB(0,0,1.0)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        self.name = name
        self.segment_name = segment_name

        self.printTimeOfCalculation = infos["printTimeOfCalculation"]

        self.printThisModeDetail = False
        if(infos["printModesDetails"]):
            if (self.name in infos["modesToPrintDetails"]):
                self.printThisModeDetail = True

        if(self.listener==None):
            self.listener = listener
            
        #rgb_list est la liste donnée au mode
        self.rgb_list = rgb_list
        self.leds     = leds
        self.indexes = indexes
        
        self.nb_of_leds = len(indexes)

        self.isActiv = False


    def smooth(self , ratio_new: float , led_index: int , new_color: List[int]):
        old_col=self.leds[self.indexes[led_index]]
        mixed_color=((1-ratio_new)*old_col[0]+ratio_new*new_color[0] , (1-ratio_new)*old_col[1]+ratio_new*new_color[1] , (1-ratio_new)*old_col[2]+ratio_new*new_color[2])
        self.rgb_list[led_index]=mixed_color

    def smooth_vectorized(self, ratio_new: float, target_rgb_matrix: np.ndarray):
        """
        Vectorized smoothing running entirely in numpy.
        Blends the new colors with the internal rgb_list correctly avoiding hardware-dimming bugs.
        """
        np.multiply(self.rgb_list, 1.0 - ratio_new, out=self.rgb_list, casting='unsafe')
        np.add(self.rgb_list, target_rgb_matrix * ratio_new, out=self.rgb_list, casting='unsafe')

    def smooth_segment(self , ratio_new , start_index , stop_index , new_color):
        for led_index in range(start_index , stop_index+1):
            self.smooth(ratio_new , led_index , new_color)

    def fade_to_black(self , ratio_black):
        for led_index in range(self.nb_of_leds):
            self.smooth( ratio_black , led_index , [0,0,0])

    def fade_to_black_led(self , ratio_black , led_index):
        self.smooth( ratio_black , led_index , [0,0,0])

    def fade_to_black_segment(self , ratio_black , start_index , stop_index ):
        for led_index in range(start_index , stop_index+1):
            self.fade_to_black_led(ratio_black , led_index)

    def smooth_segment_vectorized(self, ratio_new: float, start_index: int, stop_index: int, new_color):
        if start_index <= stop_index and start_index >= 0 and stop_index < self.nb_of_leds:
            if not isinstance(new_color, np.ndarray):
                target = np.array(new_color)
            else:
                target = new_color
            view = self.rgb_list[start_index:stop_index+1]
            np.multiply(view, 1.0 - ratio_new, out=view, casting='unsafe')
            np.add(view, target * ratio_new, out=view, casting='unsafe')
            
    def fade_to_black_segment_vectorized(self, ratio_black: float, start_index: int, stop_index: int):
        if start_index <= stop_index and start_index >= 0 and stop_index < self.nb_of_leds:
            view = self.rgb_list[start_index:stop_index+1]
            np.multiply(view, 1.0 - ratio_black, out=view, casting='unsafe')

    def fill(self, color):
        for led_index in range(self.nb_of_leds):
            self.rgb_list[led_index] = color


    def terminate(self , info_margin , showInfos):
        self.isActiv = False
        if(showInfos):
            print(info_margin + "(Mode)  on désactive le "+self.name+" du "+self.segment_name)

    def start(self , info_margin , showInfos):
        self.isActiv = True
        if(showInfos):
            print(info_margin + "(Mode)  on active le "+self.name+" du "+self.segment_name)

    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()
        
        self.run()

        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)

    def run(self):
        pass