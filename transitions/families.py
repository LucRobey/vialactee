"""
transitions/families.py - Abstract Multi-Family Contracts & Generative Parameter Rollers.

Each TransitionFamily is an abstract trait/contract. A transition can belong to
as many families as it needs, and its family memberships are declared directly on
its `TransitionSpec` inside `transitions/catalog/<name>.py`.
"""

import random
from typing import Any, Dict, FrozenSet, Tuple

from transitions.catalog import CATALOG, TransitionFamily
from transitions.stagger import StaggerPattern

F = TransitionFamily

# Derived directly from the self-contained transition catalog (single source of truth)
TRANSITION_FAMILIES: Dict[str, FrozenSet[TransitionFamily]] = {
    name: spec.families for name, spec in CATALOG.items()
}

# Deterministic default parameters (centered on the chandelier's central core)
DEFAULT_PARAMS: Dict[str, Any] = {
    "epicenter_x": 0.60,
    "epicenter_y": 0.50,
    "spiral_sign": 1.0,
    "spiral_arms": 2,
    "beam_thickness": 0.15,
    "trench_width": 0.14,
    "edge_width": 0.14,
    "teeth_count": 4,
    "focal_u": 0.5,
    "seed": 0.0,
    "spark_intensity": 1.0,
    "chop_count": 3,
    "flash_decay": 5.5,
    "mode_handshake": False,
}

# Central 2D anchor points tightly clustered in the heart of the chandelier body
_ARCHITECTURAL_EPICENTERS: Tuple[Tuple[float, float], ...] = (
    (0.58, 0.48),  # Central-Left Heart (h11 / v1-v2 center)
    (0.60, 0.50),  # Chandelier Geometric Center
    (0.62, 0.49),  # Chandelier Heart (h11 / v2 core)
    (0.64, 0.51),  # Central Pillar v2 Core
    (0.59, 0.52),  # Lower-Mid Core (h10 / v1-v2 center)
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
        params["epicenter_x"] = round(max(0.55, min(0.66, ax + random.uniform(-0.02, 0.02))), 3)
        params["epicenter_y"] = round(max(0.45, min(0.55, ay + random.uniform(-0.02, 0.02))), 3)
        params["spiral_sign"] = random.choice((-1.0, 1.0))
        params["spiral_arms"] = random.choice((2, 3))

    if F.ROOM_SWEEP_2D in fams:
        params["beam_thickness"] = round(random.uniform(0.10, 0.24), 3)
        params["trench_width"] = round(random.uniform(0.12, 0.22), 3)

    if F.STRIP_SWEEP_1D in fams:
        params["edge_width"] = round(random.uniform(0.10, 0.22), 3)
        params["teeth_count"] = random.choice((3, 4, 5))
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
