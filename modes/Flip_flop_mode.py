"""
modes/Flip_flop_mode.py
Cast global mode: every mirror pair shows one side; the sides flip on every beat (checkerboard).
Lead: beat
Secondary: transient
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import MIRROR_PAIRS, OFF, topology_slot

_PAIR_OF = {seg: (p, side) for p, pair in enumerate(MIRROR_PAIRS) for side, seg in enumerate(pair)}


class Flip_flop_mode(Cast_mode_base):
    """
    Flip-Flop: the mirror pairs (v1/v4, v2/v3, h10/h31, h11/h32, h00/h30) act as binary switches.
    Neighbouring pairs sit in opposite phase, so the chandelier shows a left/right checkerboard that
    toggles on every step; the crown h20 lights on the first beat of each bar.
    Lead: beat (the flip)
    Secondary: transient (drop_hit re-strikes every lit fixture)
    """

    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)
    DEFAULT_LOOK: str = "snap"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.checker: bool = bool(infos.get("checker", True))
        self._step: int = 0
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "checker",
                "label": "Checkerboard (alternate pairs)",
                "valueType": "boolean",
                "default": True,
                "attr": "checker",
            },
        ]

    def on_step(self, clock: Any) -> None:
        self._step = clock.step

    def on_frame(self, ctx: Any) -> None:
        if self.drop_hit:
            self.request_restrike()

    def segment_slot(self, seg_id: str) -> int:
        entry = _PAIR_OF.get(seg_id)
        if entry is None:   # the crown
            return topology_slot(seg_id) if self._step % 4 == 0 else OFF
        pair_index, side = entry
        lit_side = (self._step + (pair_index if self.checker else 0)) % 2
        return topology_slot(seg_id) if side == lit_side else OFF


FlipFlop = Flip_flop_mode
