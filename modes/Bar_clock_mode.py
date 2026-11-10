"""
modes/Bar_clock_mode.py
Cast global mode: the chandelier counts the music (beat in bar, bar in phrase, phrase boundary).
Lead: beat
Secondary: transient
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import CANOPY, OFF, PILLARS, SLOT_CANOPY, SLOT_PILLAR, SLOT_RUNG

# Rungs light from the floor up as the bars of a 4-bar phrase accumulate.
RUNG_ORDER = ("h10", "h31", "h11", "h32")


class Bar_clock_mode(Cast_mode_base):
    """
    Bar Clock: pillar v1..v4 = beat 1..4 of the bar, rungs = bars 1..4 of the phrase (accumulating),
    canopy = the first beat of every phrase.
    Lead: beat (the count itself)
    Secondary: transient (drop_hit re-strikes every lit fixture with a white crest)
    """

    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)
    DEFAULT_LOOK: str = "snap"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.show_rungs: bool = bool(infos.get("show_rungs", True))
        self._beat: int = 0
        self._bar_in_phrase: int = 0
        self._phrase_beat: bool = True
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "show_rungs",
                "label": "Count Bars on Rungs",
                "valueType": "boolean",
                "default": True,
                "attr": "show_rungs",
            },
        ]

    def on_step(self, clock: Any) -> None:
        self._beat = clock.beat_in_bar
        self._bar_in_phrase = clock.bar % 4
        self._phrase_beat = clock.step_in_phrase == 0

    def on_frame(self, ctx: Any) -> None:
        if self.drop_hit:
            self.request_restrike()

    def segment_slot(self, seg_id: str) -> int:
        if seg_id in PILLARS:
            return SLOT_PILLAR if PILLARS.index(seg_id) == self._beat else OFF
        if seg_id in CANOPY:
            return SLOT_CANOPY if self._phrase_beat else OFF
        if self.show_rungs and seg_id in RUNG_ORDER:
            return SLOT_RUNG if RUNG_ORDER.index(seg_id) <= self._bar_in_phrase else OFF
        return OFF


BarClock = Bar_clock_mode
