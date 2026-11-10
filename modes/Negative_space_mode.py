"""
modes/Negative_space_mode.py
Cast global mode: the whole chandelier is lit solid and the hits cut structural groups to black.
Lead: transient
Secondary: level
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import CANOPY, OFF, PILLARS, RUNGS, topology_slot

GROUPS = (PILLARS, RUNGS, CANOPY)
_GROUP_OF = {seg: g for g, members in enumerate(GROUPS) for seg in members}
_TAG_GROUP = {"Bass/Kick": 0, "Snare/Mid": 1, "Hi-hat/Cymbal": 2}
ONSET_THRESHOLD: float = 0.30
REFRACTORY_S: float = 0.12


class Negative_space_mode(Cast_mode_base):
    """
    Negative Space: darkness is the event. Every segment holds its structural colour; each hit
    blacks out one group for about one beat (kick -> pillars, snare -> rungs, hi-hat -> canopy),
    and the group re-strikes when it comes back.
    Lead: transient (validated beats tagged by beat_tag, band_flux onsets as fallback)
    Secondary: level (loud passages cut two groups at once)
    """

    LEAD: str = "transient"
    SECONDARY: tuple = ("level",)
    DEFAULT_LOOK: str = "snap"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.cut_beats: float = float(infos.get("cut_beats", 1.0))
        self._cut_mask: int = 0
        self._cut_timer: float = 0.0
        self._since_hit: float = 99.0
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "cut_beats",
                "label": "Cut Length (beats)",
                "valueType": "number",
                "min": 0.25,
                "max": 2.0,
                "default": 1.0,
                "step": 0.25,
                "attr": "cut_beats",
            },
        ]

    def on_reset(self) -> None:
        self._cut_mask = 0
        self._cut_timer = 0.0
        self._since_hit = 99.0

    def _onset_group(self) -> int:
        flux = getattr(self.listener, "band_flux", None)
        if flux is None or len(flux) < 4:
            return -1
        nb = len(flux)
        low = float(flux[0] + flux[1])
        mid = float(flux[nb // 2 - 1] + flux[nb // 2])
        high = float(flux[nb - 2] + flux[nb - 1])
        best = max(low, mid, high)
        if best < ONSET_THRESHOLD:
            return -1
        return 0 if best == low else (1 if best == mid else 2)

    def on_frame(self, ctx: Any) -> None:
        dt = self.dt
        self._since_hit += dt
        if self._cut_timer > 0.0:
            self._cut_timer -= dt
            if self._cut_timer <= 0.0:
                self._cut_mask = 0

        group = -1
        real_beat = bool(getattr(ctx, "is_real_beat", False)) if ctx is not None else False
        real_beat = real_beat or bool(getattr(self.listener, "is_real_beat", False))
        if real_beat:
            group = _TAG_GROUP.get(str(getattr(self.listener, "beat_tag", "Bass/Kick")), 0)
        elif self.drop_hit:
            group = 0
        elif self._since_hit >= REFRACTORY_S:
            group = self._onset_group()
        if group < 0:
            return

        mask = 1 << group
        if self.energy > 0.70:
            mask |= 1 << ((group + 1) % 3)
        bpm = float(getattr(self.listener, "bpm", 120.0)) or 120.0
        self._cut_mask = mask
        self._cut_timer = min(1.2, max(0.10, self.cut_beats * 60.0 / max(40.0, bpm)))
        self._since_hit = 0.0

    def segment_slot(self, seg_id: str) -> int:
        group = _GROUP_OF.get(seg_id, 0)
        return OFF if (self._cut_mask >> group) & 1 else topology_slot(seg_id)


NegativeSpace = Negative_space_mode
