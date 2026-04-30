import calculations.rgb_hsv as RGB_HSV
import time
import numpy as np
from typing import List, Dict, Any
import logging

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
                
        self.logger = logging.getLogger(f"Mode.{self.name}")

        if(self.listener==None):
            self.listener = listener
            
        #rgb_list est la liste donnée au mode
        self.rgb_list = rgb_list
        self.leds     = leds
        self.indexes = indexes
        
        self.nb_of_leds = len(indexes)

        self.isActiv = False
        self.has_custom_transition = False


    def smooth(self, ratio_new: float, led_index: int, new_color: List[int]):
        target = np.array(new_color)
        view = self.rgb_list[led_index:led_index+1]
        np.multiply(view, 1.0 - ratio_new, out=view, casting='unsafe')
        np.add(view, target * ratio_new, out=view, casting='unsafe')

    def smooth_vectorized(self, ratio_new: float, target_rgb_matrix: np.ndarray):
        """
        Vectorized smoothing running entirely in numpy.
        Blends the new colors with the internal rgb_list correctly avoiding hardware-dimming bugs.
        """
        np.multiply(self.rgb_list, 1.0 - ratio_new, out=self.rgb_list, casting='unsafe')
        np.add(self.rgb_list, target_rgb_matrix * ratio_new, out=self.rgb_list, casting='unsafe')

    def smooth_segment(self, ratio_new: float, start_index: int, stop_index: int, new_color):
        self.smooth_segment_vectorized(ratio_new, start_index, stop_index, new_color)

    def fade_to_black(self, ratio_black: float):
        np.multiply(self.rgb_list, 1.0 - ratio_black, out=self.rgb_list, casting='unsafe')

    def fade_to_black_led(self, ratio_black: float, led_index: int):
        view = self.rgb_list[led_index:led_index+1]
        np.multiply(view, 1.0 - ratio_black, out=view, casting='unsafe')

    def fade_to_black_segment(self, ratio_black: float, start_index: int, stop_index: int):
        self.fade_to_black_segment_vectorized(ratio_black, start_index, stop_index)

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
        self.rgb_list[:] = color


    def terminate(self):
        self.isActiv = False
        self.logger.info("  on désactive le "+self.name+" du "+self.segment_name)

    def start(self):
        self.isActiv = True
        self.logger.info("  on active le "+self.name+" du "+self.segment_name)

    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()
        
        self.run()

        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            self.logger.debug(f"      (CM) temps pour {self.name} : {duration}")

    def run(self):
        pass