"""
Chromatic Chaser Mode
Twin kinetic laser runners sweeping symmetrically from the strip ends to collide at the center on every beat.
Beat phase (0 -> 1) drives runner position from the outer edges to the center collision point and beat_pulse()
modulates runner/collision brightness (LEAD="beat"), while ctx.energy scales the leading spark halo and
center collision burst size (SECONDARY=("level",)). Stays alive when unlocked via continuous phase fallback.
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Chromatic_chaser_mode(Mode.Mode):
    """Twin laser runners sweeping from the strip ends to collide at the center on every beat.

    Lead: beat (beat_phase 0->1 moves twin runners from ends to center collision; beat_pulse sets brightness). Secondary: level (spark halo and collision burst size). Macro: trail via mood_trail, pace via mood_pace, warmth via mood_accent.
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
        self.speed: float = float(infos.get("chaser_speed", 2.0))
        self.fade_ratio: float = float(infos.get("chaser_fade_ratio", 0.05))
        self.bounce_enabled: bool = bool(infos.get("chaser_bounce_enabled", True))
        self.direction: int = 1

        n = max(1, self.nb_of_leds)
        self.mid_left: int = (n - 1) // 2
        self.mid_right: int = n // 2
        self.position: float = 0.0
        self.right_position: float = float(n - 1)
        self._prev_cyc: float = 0.0
        self._prev_raw_phase: float = -1.0
        self._free_phase: float = self.segment_phase_offset
        self._initialized: bool = False

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.head_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.spark_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        n = self.nb_of_leds
        if n <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        effective_fade = float(np.clip((self.fade_ratio * 2.2) / max(0.5, self.mood_trail), 0.02, 0.65))
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(max(0.25, effective_fade), 0, n - 1)
            return

        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        tension = float(ctx.tension if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.0))
        pulse = self.beat_pulse()
        lock = self.rhythm_lock
        mood = self.mood_colors

        # 1. Lead (beat): beat_phase 0 -> 1 drives twin runners from outer edges to center collision.
        #    If beat_phase is held static while unlocked (e.g. unit test with beat_trust == 0), advance _free_phase.
        raw_phase = float(getattr(self.listener, "beat_phase", 0.0)) % 1.0
        phase_stalled = abs(raw_phase - self._prev_raw_phase) < 1e-9
        self._prev_raw_phase = raw_phase

        speed_mult = max(0.1, float(self.speed) / 2.0)
        if phase_stalled and lock < 0.50:
            self._free_phase = (
                self._free_phase + self.dt * (bpm / 60.0) * speed_mult * self.mood_pace * (0.40 + 0.80 * energy)
            ) % 1.0
            cyc = self._free_phase
        else:
            cyc = (raw_phase * speed_mult) % 1.0

        wrapped = self._initialized and (cyc < self._prev_cyc and (self._prev_cyc - cyc) > 0.15)
        self._prev_cyc = cyc

        # bounce_enabled=True: ends -> center collision; False: center -> ends
        self.direction = 1 if self.bounce_enabled else -1
        travel = cyc if self.bounce_enabled else (1.0 - cyc)

        prev_l = int(np.clip(round(self.position), 0, self.mid_left))
        prev_r = int(np.clip(round(self.right_position), self.mid_right, n - 1))

        self.position = travel * float(self.mid_left)
        self.right_position = float(n - 1) - travel * float((n - 1) - self.mid_right)
        idx_l = int(np.clip(round(self.position), 0, self.mid_left))
        idx_r = int(np.clip(round(self.right_position), self.mid_right, n - 1))

        if not self._initialized:
            prev_l, prev_r = idx_l, idx_r
            self._initialized = True

        # 2. Color from mood_colors, spectral vertical_center, and mood_accent; brightness led by beat_pulse()
        m0, m2 = mood[0], mood[2]
        hi = self.highlight_color
        warmth = min(1.0, max(0.0, (tension - 0.30) * 0.45) + self.mood_accent)
        t_scale = self.transition_scale
        head_gain = (0.35 + 0.65 * pulse) * t_scale
        for c in range(3):
            base_c = (1.0 - v_center) * float(m0[c]) + v_center * float(m2[c])
            self.head_color[c] = ((1.0 - warmth) * base_c + warmth * float(hi[c])) * head_gain

        # 3. Fade trail, then paint continuous swept spans for both runners (no dark holes on fast steps)
        self.fade_to_black_segment_vectorized(effective_fade, 0, n - 1)

        if wrapped:
            if self.bounce_enabled:
                self.smooth_segment_vectorized(1.0, min(prev_l, self.mid_left), self.mid_left, self.head_color)
                self.smooth_segment_vectorized(1.0, self.mid_right, max(prev_r, self.mid_right), self.head_color)
                self.smooth_segment_vectorized(1.0, 0, idx_l, self.head_color)
                self.smooth_segment_vectorized(1.0, idx_r, n - 1, self.head_color)
            else:
                self.smooth_segment_vectorized(1.0, 0, max(0, prev_l), self.head_color)
                self.smooth_segment_vectorized(1.0, min(n - 1, prev_r), n - 1, self.head_color)
                self.smooth_segment_vectorized(1.0, idx_l, self.mid_left, self.head_color)
                self.smooth_segment_vectorized(1.0, self.mid_right, idx_r, self.head_color)
        else:
            self.smooth_segment_vectorized(1.0, min(prev_l, idx_l), max(prev_l, idx_l), self.head_color)
            self.smooth_segment_vectorized(1.0, min(prev_r, idx_r), max(prev_r, idx_r), self.head_color)

        # 4. Secondary (level): spark halo ahead of each runner and center collision burst scaled by ctx.energy
        halo = int(round((0.5 + 3.5 * energy) * max(1.0, float(n) / 40.0)))
        if halo > 0:
            spark_gain = (0.30 + 0.70 * min(1.0, energy)) * t_scale
            for c in range(3):
                self.spark_color[c] = (0.35 * self.head_color[c] + 0.65 * float(hi[c]) * spark_gain)

            if self.bounce_enabled:
                lead_l = min(self.mid_left, idx_l + halo)
                lead_r = max(self.mid_right, idx_r - halo)
                self.smooth_segment_vectorized(0.75, idx_l, lead_l, self.spark_color)
                self.smooth_segment_vectorized(0.75, lead_r, idx_r, self.spark_color)
            else:
                lead_l = max(0, idx_l - halo)
                lead_r = min(n - 1, idx_r + halo)
                self.smooth_segment_vectorized(0.75, lead_l, idx_l, self.spark_color)
                self.smooth_segment_vectorized(0.75, idx_r, lead_r, self.spark_color)

            # Center collision spark burst when runners meet on the beat
            if wrapped or travel >= 0.82:
                burst = max(1, halo + 1)
                c_start = max(0, self.mid_left - burst)
                c_end = min(n - 1, self.mid_right + burst)
                self.smooth_segment_vectorized(0.85, c_start, c_end, self.spark_color)
