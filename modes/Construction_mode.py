"""
modes/Construction_mode.py
Cast global mode: the chandelier assembles itself one segment per beat, holds, blacks out, rebuilds.
Lead: beat
Secondary: transient
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import BUILD_ORDER, CAST_TOPOLOGY, OFF

PHRASE_STEPS: int = 16


class Construction_mode(Cast_mode_base):
    """
    Construction: each step switches on the next segment in architectural build order
    (core pillars -> low rungs -> outer pillars -> mid rungs -> wings -> crown), holds the full
    chandelier, blacks out on the last step of the phrase, and starts again.
    Lead: beat (one segment per step)
    Secondary: transient (drop_hit re-strikes every lit fixture)
    """

    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)
    DEFAULT_LOOK: str = "neon"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.blackout_steps: float = float(infos.get("blackout_steps", 1.0))
        self._built: int = 0
        self._dark: bool = False
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "blackout_steps",
                "label": "Blackout Beats",
                "valueType": "number",
                "min": 0.0,
                "max": 4.0,
                "default": 1.0,
                "step": 1.0,
                "attr": "blackout_steps",
            },
        ]

    def on_step(self, clock: Any) -> None:
        k = clock.step_in_phrase
        dark = max(0, min(4, int(round(self.blackout_steps))))
        self._dark = k >= PHRASE_STEPS - dark
        self._built = min(len(BUILD_ORDER), k + 1)

    def on_frame(self, ctx: Any) -> None:
        if self.drop_hit:
            self.request_restrike()

    def segment_slot(self, seg_id: str) -> int:
        if self._dark:
            return OFF
        entry = CAST_TOPOLOGY.get(seg_id)
        if entry is None or entry[3] >= self._built:
            return OFF
        return entry[1]


Construction = Construction_mode
