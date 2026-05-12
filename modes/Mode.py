import utils.rgb_hsv as RGB_HSV
import time
import numpy as np
from typing import List, Dict, Any, Tuple, Union
import logging

ModeSettingValue = Union[str, int, float, bool]

class Mode:

    listener = None
    white = RGB_HSV.fromHSV_toRGB(0,0,1.0)

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        self.name = name
        self.segment_name = segment_name
        self.infos = infos

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

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return []

    def get_settings_catalog(self) -> Dict[str, Any]:
        schema = self.get_settings_schema()
        if len(schema) == 0:
            return {}

        return {
            "mode": self.name,
            "label": self.name,
            "settings": [self._public_setting_descriptor(descriptor) for descriptor in schema],
        }

    def export_settings(self) -> Dict[str, ModeSettingValue]:
        exported: Dict[str, ModeSettingValue] = {}
        for descriptor in self.get_settings_schema():
            key = descriptor.get("key")
            if not isinstance(key, str):
                continue

            attr_name = self._setting_attr_name(descriptor)
            current_value = getattr(self, attr_name, descriptor.get("default"))
            normalized_value, ok = self.normalize_setting_value(descriptor, current_value)
            if ok:
                exported[key] = normalized_value
            elif "default" in descriptor:
                exported[key] = descriptor["default"]
        return exported

    def apply_settings(self, settings: Dict[str, Any]) -> Dict[str, ModeSettingValue]:
        if not isinstance(settings, dict):
            return {}

        descriptors_by_key: Dict[str, Dict[str, Any]] = {}
        for descriptor in self.get_settings_schema():
            key = descriptor.get("key")
            if isinstance(key, str):
                descriptors_by_key[key] = descriptor

        applied: Dict[str, ModeSettingValue] = {}
        for key, raw_value in settings.items():
            descriptor = descriptors_by_key.get(key)
            if descriptor is None:
                continue

            normalized_value, ok = self.normalize_setting_value(descriptor, raw_value)
            if not ok:
                continue

            setattr(self, self._setting_attr_name(descriptor), normalized_value)
            applied[key] = normalized_value

        if len(applied) > 0:
            self.on_settings_applied(applied)

        return applied

    def on_settings_applied(self, applied_settings: Dict[str, ModeSettingValue]) -> None:
        return None

    @staticmethod
    def normalize_setting_value(descriptor: Dict[str, Any], value: Any) -> Tuple[ModeSettingValue, bool]:
        value_type = descriptor.get("valueType")

        if value_type == "boolean":
            if not isinstance(value, bool):
                return False, False
            normalized_value: ModeSettingValue = value
        elif value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return 0.0, False
            normalized_number = float(value)
            min_value = descriptor.get("min")
            max_value = descriptor.get("max")
            if isinstance(min_value, (int, float)):
                normalized_number = max(float(min_value), normalized_number)
            if isinstance(max_value, (int, float)):
                normalized_number = min(float(max_value), normalized_number)
            if descriptor.get("integer", False):
                normalized_value = int(round(normalized_number))
            else:
                normalized_value = normalized_number
        else:
            if not isinstance(value, str):
                return "", False
            normalized_value = value

        options = descriptor.get("options")
        if isinstance(options, list) and len(options) > 0:
            allowed_values = [
                option.get("value")
                for option in options
                if isinstance(option, dict) and "value" in option
            ]
            if len(allowed_values) > 0 and normalized_value not in allowed_values:
                return normalized_value, False

        return normalized_value, True

    def _public_setting_descriptor(self, descriptor: Dict[str, Any]) -> Dict[str, Any]:
        public_descriptor = {}
        for key, value in descriptor.items():
            if key != "attr":
                public_descriptor[key] = value

        if "default" in public_descriptor:
            normalized_default, ok = self.normalize_setting_value(descriptor, public_descriptor["default"])
            if ok:
                public_descriptor["default"] = normalized_default

        return public_descriptor

    def _setting_attr_name(self, descriptor: Dict[str, Any]) -> str:
        attr_name = descriptor.get("attr")
        if isinstance(attr_name, str) and len(attr_name) > 0:
            return attr_name
        return str(descriptor.get("key", ""))


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