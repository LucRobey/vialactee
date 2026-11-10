"""
modes/Mosaic_mode.py
Cast global mode: on every beat one random segment either switches on or changes colour, and stays.
Lead: beat
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import ALL_SEGMENTS, OFF, mix_index

COLOR_SLOTS: int = 3   # mood_colors primary / secondary / accent


class Mosaic_mode(Cast_mode_base):
    """
    Mosaic: the calmest cast rule. Segments that are on stay on. On each beat exactly one random
    segment changes: if it was dark it switches on, otherwise it takes a new palette colour.
    No other music reaction (no flashes, no drop effect); the chandelier slowly fills, then keeps
    re-colouring one segment per beat. It restarts dark after silence (Law 1.5).
    Lead: beat (one change per step)
    """

    LEAD: str = "beat"
    SECONDARY: tuple = ()
    DEFAULT_LOOK: str = "steady"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self._slots: Dict[str, int] = {seg: OFF for seg in ALL_SEGMENTS}
        self._last: str = ""
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def on_reset(self) -> None:
        for seg in ALL_SEGMENTS:
            self._slots[seg] = OFF
        self._last = ""

    def on_step(self, clock: Any) -> None:
        # Deterministic "random" (Cast Law C5): every segment instance makes the same pick.
        n = len(ALL_SEGMENTS)
        seg = ALL_SEGMENTS[mix_index(clock.step, 11, n)]
        if seg == self._last:
            seg = ALL_SEGMENTS[(ALL_SEGMENTS.index(seg) + 1 + mix_index(clock.step, 5, n - 1)) % n]
        self._last = seg
        current = self._slots[seg]
        if current == OFF:
            self._slots[seg] = mix_index(clock.step, 3, COLOR_SLOTS)
        else:
            self._slots[seg] = (current + 1 + mix_index(clock.step, 7, COLOR_SLOTS - 1)) % COLOR_SLOTS

    def segment_slot(self, seg_id: str) -> int:
        return self._slots.get(seg_id, OFF)


Mosaic = Mosaic_mode
