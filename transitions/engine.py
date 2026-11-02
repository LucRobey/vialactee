"""
transitions/engine.py - Spatial and 1D transition dispatcher backed by `transitions/catalog/`.
"""

import logging
from typing import Optional
import numpy as np

from transitions.assets import load_spatial_images, spatial_images
from transitions.catalog import (
    ACTIVE_PARAMS,
    CATALOG,
    apply_box_wipe,
    apply_breath_dip,
    apply_collider,
    apply_colorful_glitch,
    apply_dual_fade,
    apply_ember_dissolve,
    apply_explosion,
    apply_field_wipe as _apply_field_wipe,
    apply_flash_cut,
    apply_fuse_detonate,
    apply_gravity_drop,
    apply_horizontal_wipe,
    apply_iris_transition,
    apply_liquid_geyser,
    apply_luma_melt,
    apply_pendulum_sweep,
    apply_prism_sweep,
    apply_shatter_ice,
    apply_silk_wipe,
    apply_spiral_transition,
    apply_staccato_shutter,
    apply_supernova,
    apply_tesla_arc,
    apply_transformer_cut,
    apply_vertical_wipe,
    apply_weird_glitch,
    apply_zipper_merge,
    set_room_bounds as _set_catalog_room_bounds,
    set_transition_params,
)

ROOM_MAX_X = 430
ROOM_MAX_Y = 246
logger = logging.getLogger("Transition_Engine")
TRANSITION_DEFAULTS = {"g": 7000.0, "e": 0.6, "dt": 0.003}


def set_room_bounds(max_x: float, max_y: float) -> None:
    """Set the physical room extent used by spatial transitions (pushed in from outside)."""
    global ROOM_MAX_X, ROOM_MAX_Y
    if max_x > 0 and max_y > 0:
        ROOM_MAX_X = max_x
        ROOM_MAX_Y = max_y
        _set_catalog_room_bounds(max_x, max_y)


def apply_transition(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    progress: float,
    transition_name: str,
    coords: Optional[np.ndarray] = None,
    beam_thickness: float = 0.04,
) -> None:
    """Route transition requests to self-contained `transitions/catalog/` handlers or PNG spatial maps."""
    spec = CATALOG.get(transition_name)
    if spec is not None:
        if spec.kind == "strip_1d":
            spec.handler(rgb_list_old, rgb_list_new, progress)
        elif spec.kind == "spatial_spectacle":
            spec.handler(rgb_list_old, rgb_list_new, coords, progress, ROOM_MAX_X, ROOM_MAX_Y)
        elif coords is None:
            apply_dual_fade(rgb_list_old, rgb_list_new, progress)
        elif spec.kind == "spatial_wipe":
            spec.handler(rgb_list_old, rgb_list_new, coords, progress, beam_thickness)
        else:
            spec.handler(rgb_list_old, rgb_list_new, coords, progress)
        return

    if coords is None:
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
        return

    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    load_spatial_images()
    if transition_name not in spatial_images:
        apply_dual_fade(rgb_list_old, rgb_list_new, progress)
        return

    image = spatial_images[transition_name]
    x_coords = np.clip(coords[:, 0], 0, image.shape[0] - 1).astype(int)
    y_coords = np.clip(coords[:, 1], 0, image.shape[1] - 1).astype(int)
    led_thresholds = image[x_coords, y_coords]
    _apply_field_wipe(rgb_list_old, rgb_list_new, led_thresholds, progress, beam_thickness)


__all__ = [
    "ACTIVE_PARAMS",
    "ROOM_MAX_X",
    "ROOM_MAX_Y",
    "TRANSITION_DEFAULTS",
    "apply_box_wipe",
    "apply_breath_dip",
    "apply_collider",
    "apply_colorful_glitch",
    "apply_dual_fade",
    "apply_ember_dissolve",
    "apply_explosion",
    "apply_flash_cut",
    "apply_fuse_detonate",
    "apply_gravity_drop",
    "apply_horizontal_wipe",
    "apply_iris_transition",
    "apply_liquid_geyser",
    "apply_luma_melt",
    "apply_pendulum_sweep",
    "apply_prism_sweep",
    "apply_shatter_ice",
    "apply_silk_wipe",
    "apply_spiral_transition",
    "apply_staccato_shutter",
    "apply_supernova",
    "apply_tesla_arc",
    "apply_transition",
    "apply_transformer_cut",
    "apply_vertical_wipe",
    "apply_weird_glitch",
    "apply_zipper_merge",
    "set_room_bounds",
    "set_transition_params",
]
