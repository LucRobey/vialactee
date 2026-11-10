"""
modes/Tableaux_mode.py
Cast global mode: the chandelier holds a stage-lighting pose and cuts to a new pose every N bars.
Lead: beat
Secondary: level
"""

from typing import Any, Dict, List

from modes.Cast_mode_base import Cast_mode_base
from utils.cast import OFF, TABLEAUX_POSES, mix_index, topology_slot


class Tableaux_mode(Cast_mode_base):
    """
    Tableaux: held architectural poses (the gate, the ladders, the pillars, the canopy...).
    Nothing moves between cuts; every N bars the whole chandelier cuts to a new pose.
    Lead: beat (bar-quantized pose cuts)
    Secondary: level (energy at the cut picks sparse / medium / full pose density)
    """

    LEAD: str = "beat"
    SECONDARY: tuple = ("level",)
    DEFAULT_LOOK: str = "neon"

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any,
                 indexes: List[int], rgb_list: Any, infos: Dict[str, Any]) -> None:
        self.bars_per_pose: float = float(infos.get("bars_per_pose", 1.0))
        self._pose = TABLEAUX_POSES[1][0]
        self._pose_key = (-1, -1)
        self._pose_index: int = -1
        self._force_full: bool = False
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

    def cast_settings(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "bars_per_pose",
                "label": "Bars per Pose",
                "valueType": "number",
                "min": 1.0,
                "max": 4.0,
                "default": 1.0,
                "step": 1.0,
                "attr": "bars_per_pose",
            },
        ]

    def on_reset(self) -> None:
        self._pose_key = (-1, -1)
        self._pose_index = -1
        self._force_full = False

    def on_frame(self, ctx: Any) -> None:
        if self.drop_hit:
            self._force_full = True    # the next cut lands on a full pose
            self.request_restrike()

    def on_step(self, clock: Any) -> None:
        steps_per_pose = 4 * max(1, int(round(self.bars_per_pose)))
        pose_index = clock.step // steps_per_pose
        if pose_index == self._pose_index:
            return
        self._pose_index = pose_index
        if self._force_full:
            density = 2
            self._force_full = False
        elif self.energy < 0.40:
            density = 0
        elif self.energy < 0.72:
            density = 1
        else:
            density = 2
        poses = TABLEAUX_POSES[density]
        idx = mix_index(pose_index, density, len(poses))
        if (density, idx) == self._pose_key:
            idx = (idx + 1) % len(poses)    # never hold the same pose twice in a row
        self._pose_key = (density, idx)
        self._pose = poses[idx]

    def segment_slot(self, seg_id: str) -> int:
        return topology_slot(seg_id) if seg_id in self._pose else OFF


Tableaux = Tableaux_mode
