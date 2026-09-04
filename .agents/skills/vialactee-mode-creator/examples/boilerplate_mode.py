import numpy as np
from typing import List, Dict, Any
import utils.rgb_hsv as RGB_HSV
from modes.Mode import Mode, ModeSettingValue

class Custom_Vectorized_Mode(Mode):
    """
    Template for creating high-performance visual modes in Vialactee.
    Uses pure NumPy broadcasting and vectorized operations for smooth 60 FPS execution on Raspberry Pi.
    """
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        # Precompute normalized spatial coordinate grid [0.0, 1.0] across segment LEDs
        self.spatial_positions = np.linspace(0.0, 1.0, self.nb_of_leds, endpoint=False)
        
        # Internal state
        self.phase = 0.0
        
        # User configurable parameters with default values
        self.base_hue = float(self.infos.get("custom_base_hue", 0.6))
        self.speed = float(self.infos.get("custom_speed", 1.0))
        self.fade_ratio = float(self.infos.get("custom_fade_ratio", 0.15))
        self.react_to_bass = bool(self.infos.get("custom_react_to_bass", True))

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        """
        Exposes configurable parameters to the React Webapp & API catalog.
        """
        return [
            {
                "key": "custom_base_hue",
                "label": "Base Hue",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "default": 0.6,
                "step": 0.05,
                "attr": "base_hue"
            },
            {
                "key": "custom_speed",
                "label": "Animation Speed",
                "valueType": "number",
                "min": 0.1,
                "max": 5.0,
                "default": 1.0,
                "step": 0.1,
                "attr": "speed"
            },
            {
                "key": "custom_react_to_bass",
                "label": "React to Bass",
                "valueType": "boolean",
                "default": True,
                "attr": "react_to_bass"
            }
        ]

    def on_settings_applied(self, applied_settings: Dict[str, ModeSettingValue]) -> None:
        """
        Callback fired whenever settings are adjusted live via WebSocket or API.
        """
        self.logger.debug(f"[{self.name}] Settings updated: {applied_settings}")

    def run(self) -> None:
        """
        Main frame calculation. DO NOT use Python 'for' loops over LEDs!
        Compute all colors simultaneously using vectorized NumPy broadcasting.
        """
        # 1. Fetch audio and timing state from Listener facade
        dt = getattr(self.listener, 'dt', 1.0 / 60.0)
        smoothed_power = getattr(self.listener, 'smoothed_total_power', 0.5)
        asserved_bands = getattr(self.listener, 'asserved_fft_band', np.zeros(8))
        
        # Bass energy modulation (Band 0 & 1)
        bass_boost = 1.0
        if self.react_to_bass and len(asserved_bands) > 0:
            bass_boost += float(asserved_bands[0]) * 1.5

        # 2. Advance phase (or lock to beat_phase if rhythm-synced)
        self.phase = (self.phase + dt * self.speed * bass_boost) % 1.0

        # 3. Vectorized Hue, Saturation, Value matrices shaped (nb_of_leds,)
        hues = (self.base_hue + self.spatial_positions + self.phase) % 1.0
        saturations = np.ones(self.nb_of_leds)
        
        # Dynamic brightness pulse driven by beat or total power
        values = np.clip(np.sin((self.spatial_positions + self.phase) * np.pi * 2) * 0.5 + 0.5, 0.0, 1.0)
        values *= min(1.0, max(0.1, smoothed_power * 1.2))

        # 4. Instantaneous vectorized conversion from HSV to RGB matrix (nb_of_leds, 3)
        target_rgb_matrix = RGB_HSV.fromHSV_toRGB_vectorized(hues, saturations, values)

        # 5. Smooth blend into internal persistent buffer to prevent flicker
        self.smooth_vectorized(self.fade_ratio, target_rgb_matrix)
