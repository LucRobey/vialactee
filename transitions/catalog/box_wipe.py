"""
transitions/catalog/box_wipe.py - Wide High-Contrast Rectangular Frame Wipe.
"""

import numpy as np

from transitions.catalog._common import (
    ROOM_MAX_X,
    ROOM_MAX_Y,
    TransitionFamily as F,
    TransitionSpec,
    apply_field_wipe,
    central_epicenter,
)


def apply_box_wipe(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
    beam_thickness: float = 0.04,
) -> None:
    """Sweeps outwards from the active 2D room epicenter in a wide, high-contrast rectangular frame."""
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    ex, ey = central_epicenter()
    cx = ROOM_MAX_X * ex
    cy = ROOM_MAX_Y * ey
    span_x = max(cx, ROOM_MAX_X - cx, 1.0)
    span_y = max(cy, ROOM_MAX_Y - cy, 1.0)
    dist = np.maximum(np.abs(coords[:, 0] - cx) / span_x, np.abs(coords[:, 1] - cy) / span_y)
    wide_beam = max(0.30, float(beam_thickness) * 2.2)
    apply_field_wipe(rgb_list_old, rgb_list_new, dist, progress, wide_beam)


SPEC = TransitionSpec(
    name="box_wipe",
    families=frozenset({F.ROOM_EPI_2D, F.ROOM_SWEEP_2D}),
    duration=2.2,
    kind="spatial_wipe",
    handler=apply_box_wipe,
)
