"""
Chromatic Chaser Mode
Concentrated laser head sweeping across the strip leaving an exponential decay trail.
Replaces the python loop with precomputed ctx.vertical_center.
Synchronizes chaser speed to listener.bpm with ctx.tension acceleration.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Chromatic_chaser_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "speed",
                "label": "Travel Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 8.0,
                "step": 0.2,
                "default": 2.0,
                "attr": "speed",
            },
            {
                "key": "fadeRatio",
                "label": "Trail Fade",
                "control": "slider",
                "valueType": "number",
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "default": 0.05,
                "attr": "fade_ratio",
            },
            {
                "key": "bounceEnabled",
                "label": "Bounce At Edges",
                "control": "switch",
                "valueType": "boolean",
                "default": True,
                "attr": "bounce_enabled",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.position: float = 0.0
        self.speed: float = float(infos.get("chaser_speed", infos.get("speed", 2.0)))
        self.direction: int = 1
        self.fade_ratio: float = float(infos.get("chaser_fade_ratio", infos.get("fadeRatio", 0.05)))
        self.bounce_enabled: bool = bool(infos.get("chaser_bounce_enabled", infos.get("bounceEnabled", True)))

        # Pre-allocated scratch color vector (ZERO runtime heap allocation)
        self.head_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        tension = float(ctx.tension if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        mood = self.mood_colors

        # 1. Synchronize chaser speed to listener.bpm with ctx.tension acceleration
        bpm_factor = bpm / 120.0
        effective_speed = self.speed * bpm_factor * (1.0 + 0.75 * tension) * fps_ratio
        self.position += effective_speed * self.direction

        if self.bounce_enabled:
            if self.position >= self.nb_of_leds - 1:
                self.position = float(self.nb_of_leds - 1)
                self.direction = -1
            elif self.position <= 0:
                self.position = 0.0
                self.direction = 1
        else:
            if self.position >= self.nb_of_leds:
                self.position = 0.0
            elif self.position < 0:
                self.position = float(self.nb_of_leds - 1)
            self.direction = 1

        # 2. Derive color directly from ctx.vertical_center and mood_colors (no python loop)
        m0, m2 = mood[0], mood[2]
        self.head_color[0] = (1.0 - v_center) * float(m0[0]) + v_center * float(m2[0])
        self.head_color[1] = (1.0 - v_center) * float(m0[1]) + v_center * float(m2[1])
        self.head_color[2] = (1.0 - v_center) * float(m0[2]) + v_center * float(m2[2])
        if tension > 0.4:
            t_white = (tension - 0.4) * 0.7
            m3 = mood[3]
            self.head_color[0] = (1.0 - t_white) * self.head_color[0] + t_white * float(m3[0])
            self.head_color[1] = (1.0 - t_white) * self.head_color[1] + t_white * float(m3[1])
            self.head_color[2] = (1.0 - t_white) * self.head_color[2] + t_white * float(m3[2])

        # 3. Paint the head and fade the tail
        head_idx = int(np.clip(self.position, 0, self.nb_of_leds - 1))
        self.smooth_segment_vectorized(1.0, head_idx, head_idx, self.head_color)
        self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)
