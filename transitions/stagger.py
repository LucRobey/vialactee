"""
transitions/stagger.py - Staggered Offsets & Per-Cohort Transition Techniques.

Provides spatial and cohort-aware timing patterns:
1. Cascading ripples (top-down / bottom-up / center-out)
2. Complementary techniques across cohorts (e.g. vertical wipes on pillars,
   radial fades/expansions on horizontal rings)

Guarantees:
- AXIOM-01: Zero overhead in steady-state; configuration generation is fast (< 0.05 ms).
- AXIOM-07: Code length <= 500 lines.
- Sealed room: Zero imports from core, modes, config, connectors, or hardware.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class StaggerPattern(str, Enum):
    """Spatial propagation patterns for staggered transitions."""
    SIMULTANEOUS = "SIMULTANEOUS"
    CASCADE_DOWN = "CASCADE_DOWN"
    CASCADE_UP = "CASCADE_UP"
    CENTER_OUT = "CENTER_OUT"
    COHORT_COMPLEMENTARY = "COHORT_COMPLEMENTARY"


def select_stagger_pattern(context: Optional[Any] = None) -> StaggerPattern:
    """
    Selects a stagger pattern based on musical context.
    - High energy or drop impacts: SIMULTANEOUS (unison impact, zero lag).
    - Rhythmic grooves: COHORT_COMPLEMENTARY or CASCADE_DOWN.
    - Ambient / Chill: CASCADE_DOWN or CENTER_OUT.
    """
    if context is not None:
        if getattr(context, "is_drop_impact", False):
            return StaggerPattern.SIMULTANEOUS
        energy = float(getattr(context, "energy", 0.5) or 0.5)
        if energy >= 0.85:
            return StaggerPattern.SIMULTANEOUS
        salience = float(getattr(context, "salience", 0.5) or 0.5)
        if getattr(context, "is_rhythmic", False) or salience >= 0.60:
            return StaggerPattern.COHORT_COMPLEMENTARY
        raw_scene = getattr(context, "scene", "")
        scene = str(getattr(raw_scene, "value", getattr(raw_scene, "name", raw_scene)) or "").upper()
        if scene in ("CHILL", "DEEP_AMBIENT", "FLOATING_PULSE"):
            return StaggerPattern.CENTER_OUT

    return StaggerPattern.CASCADE_DOWN


def get_max_transition_duration(configs: Dict[str, Dict[str, Any]], default: float = 2.0) -> float:
    """Calculates the maximum completion timestamp across all segment configs."""
    max_t = 0.0
    for cfg in configs.values():
        offset = float(cfg.get("start_offset", 0.0))
        dur = float(cfg.get("duration", default))
        if offset + dur > max_t:
            max_t = offset + dur
    return max_t if max_t > 0.0 else default


def discover_segment_cohorts(segments: List[Any]) -> Tuple[List[str], List[List[str]]]:
    """Discovers vertical pillars and horizontal rings from segments list."""
    verticals: List[str] = []
    rings_dict: Dict[str, List[str]] = {}

    for seg in segments:
        name = getattr(seg, "name", "")
        orientation = getattr(seg, "orientation", "")
        if orientation == "vertical" or " v" in name or " s" in name:
            verticals.append(name)
        elif orientation == "horizontal" or " h" in name:
            prefix = name.split()[1][:2] if len(name.split()) > 1 and len(name.split()[1]) >= 2 else "h"
            rings_dict.setdefault(prefix, []).append(name)
        else:
            rings_dict.setdefault("other", []).append(name)

    verticals.sort()
    rings = [sorted(rings_dict[k]) for k in sorted(rings_dict.keys())]
    return verticals, rings


def generate_staggered_configs(
    allocation: Dict[str, str],
    verticals: List[str],
    rings: List[List[str]],
    base_technique: str = "fade_in_out",
    base_duration: float = 2.0,
    pattern: StaggerPattern = StaggerPattern.CASCADE_DOWN,
    step_delay: float = 0.15,
    pillar_wipe: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Builds per-segment transition configurations with staggered start offsets
    and/or complementary techniques across physical cohorts.

    Args:
        allocation: Mapping of {segment_name: target_mode_name}.
        verticals: List of vertical pillar segment names.
        rings: List of horizontal ring cohorts (each is a list of segment names).
        base_technique: Fallback technique name (e.g., 'fade_in_out').
        base_duration: Base duration in seconds for each segment.
        pattern: Selected StaggerPattern.
        step_delay: Time step delay in seconds between successive cohorts.
        pillar_wipe: If True, uses 'vertical_wipe' for vertical pillars.

    Returns:
        Dict mapping segment_name to transition config dictionary.
    """
    configs: Dict[str, Dict[str, Any]] = {}
    if not allocation:
        return configs

    vert_set = set(verticals)
    has_rings = len(rings) > 0 and any(len(r) > 0 for r in rings)

    if pattern == StaggerPattern.SIMULTANEOUS:
        for seg in allocation:
            configs[seg] = {
                "type": base_technique,
                "duration": base_duration,
                "start_offset": 0.0,
                "direction": None,
            }
        return configs

    if pattern == StaggerPattern.COHORT_COMPLEMENTARY:
        # Vertical pillars wipe vertically; horizontal rings fade with staggered delay
        vert_tech = "vertical_wipe" if pillar_wipe else base_technique
        vert_dur = min(base_duration, 1.2)
        ring_tech = "fade_in_out" if base_technique in ("vertical_wipe", "explosion") else base_technique

        for seg in verticals:
            if seg in allocation:
                configs[seg] = {
                    "type": vert_tech,
                    "duration": vert_dur,
                    "start_offset": 0.0,
                    "direction": "DOWN",
                }

        ring_start_base = 0.20 if verticals else 0.0
        if has_rings:
            for ring_idx, ring in enumerate(rings):
                offset = round(ring_start_base + (ring_idx * step_delay), 3)
                for seg in ring:
                    if seg in allocation:
                        configs[seg] = {
                            "type": ring_tech,
                            "duration": base_duration,
                            "start_offset": offset,
                            "direction": None,
                        }
        else:
            # If no rings, stagger verticals after the first
            for idx, seg in enumerate(verticals):
                if seg in allocation:
                    configs[seg] = {
                        "type": vert_tech,
                        "duration": vert_dur,
                        "start_offset": round(idx * step_delay, 3),
                        "direction": "DOWN",
                    }

    elif pattern == StaggerPattern.CASCADE_DOWN:
        # Top-down cascade: rings ripple downward from top ring to bottom ring
        vert_tech = "vertical_wipe" if pillar_wipe else base_technique
        for seg in verticals:
            if seg in allocation:
                configs[seg] = {
                    "type": vert_tech,
                    "duration": base_duration,
                    "start_offset": 0.0,
                    "direction": "DOWN",
                }

        if has_rings:
            for ring_idx, ring in enumerate(rings):
                offset = round(ring_idx * step_delay, 3)
                for seg in ring:
                    if seg in allocation:
                        configs[seg] = {
                            "type": base_technique,
                            "duration": base_duration,
                            "start_offset": offset,
                            "direction": None,
                        }
        else:
            for idx, seg in enumerate(verticals):
                if seg in allocation:
                    configs[seg] = {
                        "type": vert_tech,
                        "duration": base_duration,
                        "start_offset": round(idx * step_delay, 3),
                        "direction": "DOWN",
                    }

    elif pattern == StaggerPattern.CASCADE_UP:
        # Bottom-up cascade: rings ripple upward from bottom ring to top ring
        vert_tech = "vertical_wipe" if pillar_wipe else base_technique
        for seg in verticals:
            if seg in allocation:
                configs[seg] = {
                    "type": vert_tech,
                    "duration": base_duration,
                    "start_offset": 0.0,
                    "direction": "UP",
                }

        if has_rings:
            num_rings = len(rings)
            for ring_idx, ring in enumerate(rings):
                offset = round((num_rings - 1 - ring_idx) * step_delay, 3)
                for seg in ring:
                    if seg in allocation:
                        configs[seg] = {
                            "type": base_technique,
                            "duration": base_duration,
                            "start_offset": offset,
                            "direction": None,
                        }
        else:
            num_v = len(verticals)
            for idx, seg in enumerate(verticals):
                if seg in allocation:
                    configs[seg] = {
                        "type": vert_tech,
                        "duration": base_duration,
                        "start_offset": round((num_v - 1 - idx) * step_delay, 3),
                        "direction": "UP",
                    }

    elif pattern == StaggerPattern.CENTER_OUT:
        # Center-out ripple: center ring ripples outward symmetrically
        vert_tech = "vertical_wipe" if pillar_wipe else base_technique
        for seg in verticals:
            if seg in allocation:
                configs[seg] = {
                    "type": vert_tech,
                    "duration": base_duration,
                    "start_offset": 0.0,
                    "direction": None,
                }

        if has_rings:
            num_rings = len(rings)
            mid = (num_rings - 1) / 2.0
            for ring_idx, ring in enumerate(rings):
                dist = abs(ring_idx - mid)
                offset = round(dist * step_delay, 3)
                for seg in ring:
                    if seg in allocation:
                        configs[seg] = {
                            "type": base_technique,
                            "duration": base_duration,
                            "start_offset": offset,
                            "direction": None,
                        }
        else:
            num_v = len(verticals)
            mid_v = (num_v - 1) / 2.0
            for idx, seg in enumerate(verticals):
                if seg in allocation:
                    dist = abs(idx - mid_v)
                    configs[seg] = {
                        "type": vert_tech,
                        "duration": base_duration,
                        "start_offset": round(dist * step_delay, 3),
                        "direction": None,
                    }

    # Catch any remaining segments not belonging to verticals or rings
    for seg in allocation:
        if seg not in configs:
            configs[seg] = {
                "type": base_technique,
                "duration": base_duration,
                "start_offset": 0.0,
                "direction": None,
            }

    return configs
