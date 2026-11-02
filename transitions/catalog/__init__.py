"""
transitions/catalog/__init__.py - Single-source-of-truth registry of all self-contained transitions.

Aggregates every `TransitionSpec` from `transitions/catalog/*.py` so `families.py`,
`manager.py`, and `engine.py` derive their contracts, durations, and handlers from one place.
"""

from typing import Any, Dict, Tuple

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    TransitionFamily,
    TransitionSpec,
    apply_field_wipe,
    set_room_bounds,
    set_transition_params,
)
from transitions.catalog.box_wipe import SPEC as _BOX_WIPE_SPEC, apply_box_wipe
from transitions.catalog.breath_dip import SPEC as _BREATH_DIP_SPEC
from transitions.catalog.collider import SPEC as _COLLIDER_SPEC
from transitions.catalog.dual_fade import SPEC as _DUAL_FADE_SPEC, apply_dual_fade
from transitions.catalog.ember_dissolve import SPEC as _EMBER_DISSOLVE_SPEC
from transitions.catalog.explosion import SPEC as _EXPLOSION_SPEC, apply_explosion
from transitions.catalog.flash_cut import SPEC as _FLASH_CUT_SPEC
from transitions.catalog.fuse_detonate import SPEC as _FUSE_DETONATE_SPEC
from transitions.catalog.global_change import SPEC as _GLOBAL_CHANGE_SPEC, apply_colorful_glitch
from transitions.catalog.gravity_drop import SPEC as _GRAVITY_DROP_SPEC, apply_gravity_drop
from transitions.catalog.horizontal_wipe import SPECS as _HORIZONTAL_WIPE_SPECS, apply_horizontal_wipe
from transitions.catalog.iris import SPECS as _IRIS_SPECS
from transitions.catalog.liquid_geyser import SPEC as _LIQUID_GEYSER_SPEC
from transitions.catalog.luma_melt import SPEC as _LUMA_MELT_SPEC
from transitions.catalog.pendulum_sweep import SPEC as _PENDULUM_SWEEP_SPEC
from transitions.catalog.prism_sweep import SPEC as _PRISM_SWEEP_SPEC
from transitions.catalog.shatter_ice import SPEC as _SHATTER_ICE_SPEC
from transitions.catalog.silk_wipe import SPECS as _SILK_WIPE_SPECS
from transitions.catalog.spiral import SPEC as _SPIRAL_SPEC, apply_spiral_transition
from transitions.catalog.staccato_shutter import SPEC as _STACCATO_SHUTTER_SPEC
from transitions.catalog.supernova import SPEC as _SUPERNOVA_SPEC
from transitions.catalog.tesla_arc import SPEC as _TESLA_ARC_SPEC
from transitions.catalog.transformer_cut import SPEC as _TRANSFORMER_CUT_SPEC
from transitions.catalog.vertical_wipe import SPEC as _VERTICAL_WIPE_SPEC, apply_vertical_wipe
from transitions.catalog.weird_glitch import SPEC as _WEIRD_GLITCH_SPEC, apply_weird_glitch
from transitions.catalog.zipper_merge import SPEC as _ZIPPER_MERGE_SPEC

ALL_SPECS: Tuple[TransitionSpec, ...] = (
    _EXPLOSION_SPEC,
    _SUPERNOVA_SPEC,
    _SPIRAL_SPEC,
    _TESLA_ARC_SPEC,
    _BOX_WIPE_SPEC,
    _WEIRD_GLITCH_SPEC,
    _SHATTER_ICE_SPEC,
    _LIQUID_GEYSER_SPEC,
    _PENDULUM_SWEEP_SPEC,
    _GRAVITY_DROP_SPEC,
    _VERTICAL_WIPE_SPEC,
    *_HORIZONTAL_WIPE_SPECS,
    _ZIPPER_MERGE_SPEC,
    _COLLIDER_SPEC,
    _FUSE_DETONATE_SPEC,
    *_SILK_WIPE_SPECS,
    *_IRIS_SPECS,
    _PRISM_SWEEP_SPEC,
    _EMBER_DISSOLVE_SPEC,
    _LUMA_MELT_SPEC,
    _BREATH_DIP_SPEC,
    _DUAL_FADE_SPEC,
    _GLOBAL_CHANGE_SPEC,
    _FLASH_CUT_SPEC,
    _STACCATO_SHUTTER_SPEC,
    _TRANSFORMER_CUT_SPEC,
)

CATALOG: Dict[str, TransitionSpec] = {}
TECHNIQUE_CONFIGS: Dict[str, Dict[str, Any]] = {}

for _spec in ALL_SPECS:
    CATALOG[_spec.name] = _spec
    TECHNIQUE_CONFIGS[_spec.name] = {"type": _spec.name, "duration": _spec.duration}
    for _alias in _spec.aliases:
        CATALOG[_alias] = _spec
        TECHNIQUE_CONFIGS[_alias] = {"type": _spec.name, "duration": _spec.duration}
    for _self_alias in _spec.self_typed_aliases:
        CATALOG[_self_alias] = _spec
        TECHNIQUE_CONFIGS[_self_alias] = {"type": _self_alias, "duration": _spec.duration}

__all__ = [
    "ACTIVE_PARAMS",
    "ALL_SPECS",
    "CATALOG",
    "TECHNIQUE_CONFIGS",
    "TransitionFamily",
    "TransitionSpec",
    "apply_box_wipe",
    "apply_colorful_glitch",
    "apply_dual_fade",
    "apply_explosion",
    "apply_field_wipe",
    "apply_gravity_drop",
    "apply_horizontal_wipe",
    "apply_spiral_transition",
    "apply_vertical_wipe",
    "apply_weird_glitch",
    "set_room_bounds",
    "set_transition_params",
]
