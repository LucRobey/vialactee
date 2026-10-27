import numpy as np
from typing import List, Dict, Any
import utils.rgb_hsv as RGB_HSV
from modes.Mode import Mode, ModeSettingValue


class Custom_Vectorized_Mode(Mode):
    """
    Template for creating high-performance visual modes in Vialactee.
    Uses pure NumPy broadcasting, pre-allocated scratch arrays, and zero runtime heap allocations
    for smooth 30 FPS execution on Raspberry Pi (AXIOM-01, AXIOM-02).
    """

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        # Precompute normalized spatial coordinate grid [0.0, 1.0] and scratch buffers in __init__
        self.spatial_positions = np.linspace(0.0, 1.0, self.nb_of_leds, endpoint=False)
        self._hues = np.zeros(self.nb_of_leds, dtype=np.float64)
        self._saturations = np.ones(self.nb_of_leds, dtype=np.float64)
        self._values = np.zeros(self.nb_of_leds, dtype=np.float64)
        self._target_rgb = np.zeros((self.nb_of_leds, 3), dtype=np.int32)

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
        Main frame calculation. DO NOT use Python 'for' loops over LEDs or allocate arrays here!
        Compute all colors simultaneously using pre-allocated NumPy buffers.
        """
        if self.nb_of_leds <= 0:
            return
        ctx = getattr(self.listener, "context", None)
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        # 1. Fetch audio and timing state from Mode helpers and Listener facade
        asserved_bands = getattr(self.listener, "asserved_fft_band", None)
        bass_boost = 1.0
        if self.react_to_bass and asserved_bands is not None and len(asserved_bands) > 0:
            bass_boost += float(asserved_bands[0]) * 1.5

        # 2. Advance phase using self.dt and mood_pace (blended with beat_phase via rhythm_lock)
        self.phase = (self.phase + self.dt * self.speed * self.mood_pace * bass_boost) % 1.0
        lock = self.rhythm_lock
        beat_phase = float(getattr(self.listener, "beat_phase", 0.0))
        effective_phase = lock * beat_phase + (1.0 - lock) * self.phase

        # 3. In-place vectorized Hue, Saturation, Value computation
        np.add(self.spatial_positions, self.base_hue + effective_phase, out=self._hues)
        np.remainder(self._hues, 1.0, out=self._hues)

        np.add(self.spatial_positions, effective_phase, out=self._values)
        np.multiply(self._values, 2.0 * np.pi, out=self._values)
        np.sin(self._values, out=self._values)
        np.multiply(self._values, 0.5, out=self._values)
        np.add(self._values, 0.5, out=self._values)
        np.multiply(self._values, max(0.15, self.beat_pulse(2.2)), out=self._values)
        np.clip(self._values, 0.0, 1.0, out=self._values)

        # 4. Vectorized conversion from HSV to pre-allocated RGB matrix (nb_of_leds, 3) and smooth blend
        RGB_HSV.fromHSV_toRGB_vectorized(self._hues, self._saturations, self._values, out=self._target_rgb)
        self.smooth_vectorized(self.alpha(self.fade_ratio * 30.0), self._target_rgb)
