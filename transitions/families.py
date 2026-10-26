"""
transitions/families.py - Abstract Multi-Family Contracts & Generative Parameter Rollers.

Each TransitionFamily is an abstract trait/contract. A transition can belong to
as many families as it needs, and its family memberships automatically define:
  1. Which generative parameters are rolled on each trigger (epicenter, focal_u, seed, chops...).
  2. Which chandelier stagger choreographies (StaggerPattern) are physically valid.
  3. Whether full-strip mode exit/enter handshakes (MODE_COOPERATIVE) are active.
"""

from enum import Enum
import random
from typing import Any, Dict, FrozenSet, Tuple

from transitions.stagger import StaggerPattern


class TransitionFamily(str, Enum):
    """Abstract transition contract traits. A transition may belong to multiple families."""
    ROOM_EPI_2D = "ROOM_EPI_2D"
    ROOM_SWEEP_2D = "ROOM_SWEEP_2D"
    STRIP_SWEEP_1D = "STRIP_SWEEP_1D"
    STRIP_FOCAL_1D = "STRIP_FOCAL_1D"
    STAGGERABLE = "STAGGERABLE"
    STOCHASTIC_ORGANIC = "STOCHASTIC_ORGANIC"
    RHYTHMIC_CHOP = "RHYTHMIC_CHOP"
    MODE_COOPERATIVE = "MODE_COOPERATIVE"


F = TransitionFamily

# Multi-family registry: each transition declares all abstract contracts it satisfies
TRANSITION_FAMILIES: Dict[str, FrozenSet[TransitionFamily]] = {
    # 2D Room-Space Epicenter Transitions (always SIMULTANEOUS across segments)
    "explosion": frozenset({F.ROOM_EPI_2D, F.RHYTHMIC_CHOP}),
    "transient_blip": frozenset({F.ROOM_EPI_2D, F.RHYTHMIC_CHOP}),
    "spiral": frozenset({F.ROOM_EPI_2D, F.MODE_COOPERATIVE}),
    "box_wipe": frozenset({F.ROOM_EPI_2D, F.MODE_COOPERATIVE}),
    "weird_glitch": frozenset({F.ROOM_EPI_2D, F.STOCHASTIC_ORGANIC}),
    # 2D Room-Space Plane / Gravity Sweeps
    "vertical_wipe": frozenset({F.ROOM_SWEEP_2D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "directional_wipe": frozenset({F.ROOM_SWEEP_2D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "wipe_left_to_right": frozenset({F.ROOM_SWEEP_2D, F.MODE_COOPERATIVE}),
    "wipe_right_to_left": frozenset({F.ROOM_SWEEP_2D, F.MODE_COOPERATIVE}),
    "gravity_drop": frozenset({F.ROOM_SWEEP_2D, F.MODE_COOPERATIVE}),
    # 1D Strip-Intrinsic Directional Sweeps
    "silk_wipe": frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "silk_wipe_reverse": frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "prism_sweep": frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "zipper_merge": frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    # 1D Strip-Intrinsic Focal / Aperture Effects
    "iris_open": frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "iris_close": frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "collider": frozenset({F.STRIP_FOCAL_1D, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    # Photonic & Organic Dissolves
    "ember_dissolve": frozenset({F.STOCHASTIC_ORGANIC, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "luma_melt": frozenset({F.STOCHASTIC_ORGANIC, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "breath_dip": frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "fade_in_out": frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "fade_to_black": frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "smooth_cosine_crossfade": frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "cosine_fade": frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    "global_change": frozenset({F.STOCHASTIC_ORGANIC, F.STAGGERABLE, F.MODE_COOPERATIVE}),
    # Rhythmic & DJ Cuts (non-cooperative hard cuts between full-power modes)
    "flash_cut": frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    "staccato_shutter": frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    "transformer_cut": frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
}

# Deterministic default parameters (used when engine functions are called directly in unit tests)
DEFAULT_PARAMS: Dict[str, Any] = {
    "epicenter_x": 0.5,
    "epicenter_y": 0.5,
    "spiral_sign": 1.0,
    "beam_thickness": 0.15,
    "edge_width": 0.14,
    "focal_u": 0.5,
    "seed": 0.0,
    "spark_intensity": 1.0,
    "chop_count": 3,
    "flash_decay": 5.5,
    "mode_handshake": False,
}

# Architectural 2D anchor regions inside the physical chandelier body (normalized [0..1] coordinates)
_ARCHITECTURAL_EPICENTERS: Tuple[Tuple[float, float], ...] = (
    (0.55, 0.50),  # Inner Bay Center (between v1 and v2)
    (0.64, 0.48),  # Chandelier Heart (h11 / v2 core)
    (0.68, 0.52),  # Central Pillar v2 Midpoint
    (0.73, 0.46),  # Main Bay Center (between v2 and v3)
    (0.60, 0.56),  # Lower-Mid Core (h10 / v2)
)


def get_families(technique: str) -> FrozenSet[TransitionFamily]:
    """Return the set of abstract TransitionFamily contracts satisfied by `technique`."""
    return TRANSITION_FAMILIES.get(technique, frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}))


def is_staggerable(technique: str) -> bool:
    """Return True if `technique` belongs to STAGGERABLE and is not a 2D room epicenter transition."""
    fams = get_families(technique)
    if F.ROOM_EPI_2D in fams:
        return False
    return F.STAGGERABLE in fams


def is_mode_cooperative(technique: str) -> bool:
    """Return True if `technique` activates physical on_transition_exit/enter mode handshakes."""
    return F.MODE_COOPERATIVE in get_families(technique)


def get_allowed_stagger_patterns(technique: str) -> Tuple[StaggerPattern, ...]:
    """Return the tuple of physically valid chandelier StaggerPatterns for `technique`."""
    if not is_staggerable(technique):
        return (StaggerPattern.SIMULTANEOUS,)
    fams = get_families(technique)
    if F.RHYTHMIC_CHOP in fams:
        return (
            StaggerPattern.SIMULTANEOUS,
            StaggerPattern.COHORT_COMPLEMENTARY,
            StaggerPattern.CASCADE_DOWN,
            StaggerPattern.ALTITUDE_CASCADE_DOWN,
        )
    if F.STRIP_SWEEP_1D in fams:
        return (
            StaggerPattern.BAY_WAVE_LR,
            StaggerPattern.BAY_WAVE_RL,
            StaggerPattern.CASCADE_DOWN,
            StaggerPattern.CASCADE_UP,
            StaggerPattern.ALTITUDE_CASCADE_DOWN,
            StaggerPattern.ALTITUDE_CASCADE_UP,
            StaggerPattern.COHORT_COMPLEMENTARY,
            StaggerPattern.SIMULTANEOUS,
        )
    return (
        StaggerPattern.CASCADE_DOWN,
        StaggerPattern.CASCADE_UP,
        StaggerPattern.CENTER_OUT,
        StaggerPattern.ALTITUDE_CASCADE_DOWN,
        StaggerPattern.ALTITUDE_CASCADE_UP,
        StaggerPattern.BAY_WAVE_LR,
        StaggerPattern.BAY_WAVE_RL,
        StaggerPattern.COHORT_COMPLEMENTARY,
        StaggerPattern.SIMULTANEOUS,
    )


def roll_transition_params(technique: str) -> Dict[str, Any]:
    """
    Sample fresh generative parameters based on every TransitionFamily contract
    that `technique` belongs to. Ensures triggering the same transition twice
    produces a distinct spatial epicenter, focal point, or organic seed.
    """
    fams = get_families(technique)
    params = dict(DEFAULT_PARAMS)
    params["mode_handshake"] = F.MODE_COOPERATIVE in fams

    if F.ROOM_EPI_2D in fams:
        ax, ay = random.choice(_ARCHITECTURAL_EPICENTERS)
        params["epicenter_x"] = round(max(0.46, min(0.78, ax + random.uniform(-0.04, 0.04))), 3)
        params["epicenter_y"] = round(max(0.38, min(0.64, ay + random.uniform(-0.04, 0.04))), 3)
        params["spiral_sign"] = random.choice((-1.0, 1.0))

    if F.ROOM_SWEEP_2D in fams:
        params["beam_thickness"] = round(random.uniform(0.08, 0.22), 3)

    if F.STRIP_SWEEP_1D in fams:
        params["edge_width"] = round(random.uniform(0.10, 0.22), 3)
        params["reverse"] = technique == "silk_wipe_reverse"

    if F.STRIP_FOCAL_1D in fams:
        params["focal_u"] = round(random.uniform(0.28, 0.72), 3)

    if F.STOCHASTIC_ORGANIC in fams:
        params["seed"] = round(random.uniform(0.0, 99.9), 3)
        params["spark_intensity"] = round(random.uniform(0.85, 1.25), 3)

    if F.RHYTHMIC_CHOP in fams:
        params["chop_count"] = random.choice((3, 4, 5))
        params["flash_decay"] = round(random.uniform(4.5, 7.5), 2)

    return params
