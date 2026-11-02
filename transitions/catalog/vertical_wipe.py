"""
transitions/catalog/vertical_wipe.py - 2D Vertical Room Plane Wipe.
"""

import numpy as np

from transitions.catalog._common import ROOM_MAX_Y, TransitionFamily as F, TransitionSpec, apply_field_wipe


def apply_vertical_wipe(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    """Sweeps vertically across the room with a dark void trench and laser boundary line."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    ny = coords[:, 1] / max(1.0, float(ROOM_MAX_Y))
    apply_field_wipe(rgb_list_old, rgb_list_new, ny, progress, beam_thickness)


SPEC = TransitionSpec(
    name="vertical_wipe",
    families=frozenset({F.ROOM_SWEEP_2D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.0,
    kind="spatial_wipe",
    handler=apply_vertical_wipe,
    aliases=("directional_wipe",),
)
