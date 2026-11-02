"""
transitions/catalog/horizontal_wipe.py - 2D Horizontal Room Plane Wipes (L->R and R->L).
"""

import numpy as np

from transitions.catalog._common import ROOM_MAX_X, TransitionFamily as F, TransitionSpec, apply_field_wipe


def apply_horizontal_wipe(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
    reverse: bool = False,
) -> None:
    """Sweeps horizontally across the room with a dark void trench and laser boundary line."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    nx = coords[:, 0] / max(1.0, float(ROOM_MAX_X))
    if reverse:
        nx = 1.0 - nx
    apply_field_wipe(rgb_list_old, rgb_list_new, nx, progress, beam_thickness)


def apply_wipe_left_to_right(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    apply_horizontal_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness, reverse=False)


def apply_wipe_right_to_left(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    apply_horizontal_wipe(rgb_list_old, rgb_list_new, coords, progress, beam_thickness, reverse=True)


SPECS = (
    TransitionSpec(
        name="wipe_left_to_right",
        families=frozenset({F.ROOM_SWEEP_2D, F.MODE_COOPERATIVE}),
        duration=2.2,
        kind="spatial_wipe",
        handler=apply_wipe_left_to_right,
    ),
    TransitionSpec(
        name="wipe_right_to_left",
        families=frozenset({F.ROOM_SWEEP_2D, F.MODE_COOPERATIVE}),
        duration=2.2,
        kind="spatial_wipe",
        handler=apply_wipe_right_to_left,
    ),
)
