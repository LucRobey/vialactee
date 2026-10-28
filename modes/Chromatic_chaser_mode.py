"""
Chromatic Chaser Mode
Concentrated laser head sweeping across the strip leaving an exponential decay trail.
Synchronizes chaser speed to listener.bpm, ctx.tension, and mood_pace, while scaling trail
persistence with mood_trail and color warmth with mood_accent.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Chromatic_chaser_mode(Mode.Mode):
    """Kinetic laser runner sweeping across the strip with exponential decay trail.

    Lead: beat (collision on the beat). Secondary: level (spark size). Macro: period via mood_pace; tension shortens it.
    """
    LEAD = "beat"
    SECONDARY = ("level",)

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
        self.position: float = self.segment_phase_offset * max(0, self.nb_of_leds - 1)
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
        effective_fade = float(np.clip(self.fade_ratio / max(0.5, self.mood_trail), 0.005, 0.60))
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(max(0.25, effective_fade), 0, self.nb_of_leds - 1)
            return

        fps_ratio = self.fps_ratio
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        tension = float(ctx.tension if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        mood = self.mood_colors

        # 1. Synchronize chaser speed to listener.bpm (gated by rhythm_lock), tension, and mood_pace
        bpm_factor = 1.0 + self.rhythm_lock * ((bpm / 120.0) - 1.0)
        effective_speed = self.speed * bpm_factor * (1.0 + 0.55 * tension) * self.mood_pace * fps_ratio
        if not self.bounce_enabled:
            self.direction = 1
        prev_idx = int(np.clip(self.position, 0, self.nb_of_leds - 1))
        step = effective_speed * self.direction
        self.position += step
        wrapped = False
        full_lap = abs(step) >= float(max(1, self.nb_of_leds - 1)) and not self.bounce_enabled

        if self.bounce_enabled:
            if self.position >= self.nb_of_leds - 1:
                self.position = float(self.nb_of_leds - 1)
                self.direction = -1
            elif self.position <= 0:
                self.position = 0.0
                self.direction = 1
        else:
            if self.position >= self.nb_of_leds:
                self.position %= float(self.nb_of_leds)
                wrapped = True
            elif self.position < 0:
                self.position %= float(self.nb_of_leds)
                wrapped = True

        # 2. Derive color from vertical_center, mood_colors, and mood_accent
        m0, m2 = mood[0], mood[2]
        hi = self.highlight_color
        warmth = min(1.0, max(0.0, (tension - 0.35) * 0.5) + self.mood_accent)
        for c in range(3):
            base_c = (1.0 - v_center) * float(m0[c]) + v_center * float(m2[c])
            self.head_color[c] = (1.0 - warmth) * base_c + warmth * float(hi[c])

        # 3. Fade the tail first (scaled by mood_trail), then paint the continuous swept span
        head_idx = int(np.clip(self.position, 0, self.nb_of_leds - 1))
        self.fade_to_black_segment_vectorized(effective_fade, 0, self.nb_of_leds - 1)
        if full_lap:
            self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.head_color)
        elif wrapped and not self.bounce_enabled:
            if step >= 0.0:
                self.smooth_segment_vectorized(1.0, prev_idx, self.nb_of_leds - 1, self.head_color)
                self.smooth_segment_vectorized(1.0, 0, head_idx, self.head_color)
            else:
                self.smooth_segment_vectorized(1.0, 0, prev_idx, self.head_color)
                self.smooth_segment_vectorized(1.0, head_idx, self.nb_of_leds - 1, self.head_color)
        else:
            span_start = min(prev_idx, head_idx)
            span_end = max(prev_idx, head_idx)
            self.smooth_segment_vectorized(1.0, span_start, span_end, self.head_color)
