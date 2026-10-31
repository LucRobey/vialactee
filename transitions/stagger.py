"""
transitions/stagger.py - Staggered Offsets & Per-Cohort Transition Techniques.

# Note: wired into the automatic `timer` / `song_change` / `structural_change` triggers
# (see transitions/service.py STAGGERED_AUTO_REASONS); drop triggers stay simultaneous.
# Manual requests stay instant unless a caller passes staggered=True.

Provides spatial and cohort-aware timing patterns:
1. Cascading ripples (top-down / bottom-up / center-out)
2. Complementary techniques across cohorts (e.g. vertical wipes on pillars,
   radial fades/expansions on horizontal rings)
3. Tag-based altitude tier and bay column derivation with seamless legacy fallback

Guarantees:
- AXIOM-01: Zero overhead in steady-state; configuration generation is fast (< 0.05 ms).
- AXIOM-07: Code length <= 500 lines.
- Sealed room: Zero imports from core, modes, config, connectors, or hardware.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class StaggerPattern(str, Enum):
    """Spatial propagation patterns for staggered transitions."""
    SIMULTANEOUS = "SIMULTANEOUS"
    CASCADE_DOWN = "CASCADE_DOWN"
    CASCADE_UP = "CASCADE_UP"
    CENTER_OUT = "CENTER_OUT"
    COHORT_COMPLEMENTARY = "COHORT_COMPLEMENTARY"
    ALTITUDE_CASCADE_DOWN = "ALTITUDE_CASCADE_DOWN"
    ALTITUDE_CASCADE_UP = "ALTITUDE_CASCADE_UP"
    BAY_WAVE_LR = "BAY_WAVE_LR"
    BAY_WAVE_RL = "BAY_WAVE_RL"


# Canonical physical Y-altitude tier mapping for full-profile horizontal segments (legacy fallback)
_ALTITUDE_TIER_BY_SUFFIX: Dict[str, int] = {
    "h30": 0, "h00": 0, "h20": 0,  # Canopy tier (Y = 1..16)
    "h11": 1, "h32": 1,            # Mid tier (Y = 73..85)
    "h31": 2, "h10": 2,            # Low tier (Y = 171..189)
}

# Canonical left-to-right horizontal bay column order across the full chandelier (legacy fallback)
_BAY_COLUMN_BY_SUFFIX: Dict[str, int] = {
    "h00": 0,
    "v1": 1, "s1": 0,
    "h10": 2, "h11": 2,
    "v2": 3, "s2": 1,
    "h20": 4,
    "v3": 5, "s3": 2,
    "h30": 6, "h31": 6, "h32": 6,
    "v4": 7,
}

_TIER_NAME_TO_INT: Dict[str, int] = {
    "canopy": 0,
    "top": 0,
    "mid": 1,
    "middle": 1,
    "center": 1,
    "low": 2,
    "bottom": 2,
}


def _segment_suffix(seg_name: str) -> str:
    """Extracts the terminal token/suffix from a segment identifier or name."""
    parts = seg_name.strip().lower().split()
    return parts[-1] if parts else seg_name.lower()


def _extract_segment_info(seg: Any) -> Tuple[str, Tuple[str, ...], str]:
    """
    Extracts (name, tags, suffix) from a segment identifier, SegmentDescriptor, dict, or object.
    Robust to strings, dataclasses, dicts, and None values.
    """
    if seg is None:
        return "", (), ""
    if isinstance(seg, str):
        suffix = _segment_suffix(seg)
        return seg, (), suffix
    if isinstance(seg, dict):
        name = str(seg.get("name") or seg.get("id") or "")
        raw_tags = seg.get("tags") or ()
        tags = tuple(raw_tags) if isinstance(raw_tags, (list, tuple, set)) else ()
        suffix = str(seg.get("id") or _segment_suffix(name)).strip().lower()
        return name, tags, suffix

    # Objects (SegmentDescriptor, Segment, SimpleNamespace, etc.)
    name = str(getattr(seg, "name", "") or getattr(seg, "id", "") or str(seg))
    raw_tags = getattr(seg, "tags", ()) or ()
    tags = tuple(raw_tags) if isinstance(raw_tags, (list, tuple, set)) else ()
    seg_id = getattr(seg, "id", "")
    suffix = str(seg_id or _segment_suffix(name)).strip().lower()
    return name, tags, suffix


def get_segment_altitude_tier(seg: Any, default: int = 1) -> int:
    """
    Resolves the physical altitude tier index (0=Canopy, 1=Mid, 2=Low).
    Inspects segment tags first ('tier:canopy', 'tier:mid', 'tier:low', or numeric 'tier:0'),
    then seamlessly falls back to legacy suffix table _ALTITUDE_TIER_BY_SUFFIX.
    """
    _, tags, suffix = _extract_segment_info(seg)
    for tag in tags:
        if isinstance(tag, str) and tag.startswith("tier:"):
            val = tag[5:].strip().lower()
            if val in _TIER_NAME_TO_INT:
                return _TIER_NAME_TO_INT[val]
            if val.isdigit():
                return int(val)
    return _ALTITUDE_TIER_BY_SUFFIX.get(suffix, default)


_BAY_BY_GEOMETRY_TAGS: Dict[Tuple[str, str], int] = {
    ("left", "size:long"): 0,
    ("left", "pos:outer"): 1,
    ("left", "size:medium"): 2,
    ("left", "pos:inner"): 3,
    ("right", "size:medium"): 4,
    ("right", "pos:inner"): 5,
    ("right", "size:short"): 6,
    ("right", "pos:outer"): 7,
}


def get_segment_bay_column(seg: Any, default: int = 0) -> int:
    """
    Resolves the horizontal bay column index (0..7 left-to-right).
    Inspects segment tags first ('half:*' + 'pos:*'/'size:*' or 'pos:<int>'),
    then seamlessly falls back to legacy suffix table _BAY_COLUMN_BY_SUFFIX.
    """
    _, tags, suffix = _extract_segment_info(seg)
    pos_num: Optional[int] = None
    half_side: Optional[str] = None
    pos_or_size: Optional[str] = None
    for tag in tags:
        if not isinstance(tag, str):
            continue
        if tag.startswith("pos:"):
            val = tag[4:].strip().lower()
            if val.isdigit():
                pos_num = int(val)
            elif val in ("outer", "inner"):
                pos_or_size = f"pos:{val}"
        elif tag.startswith("size:"):
            val = tag[5:].strip().lower()
            if val in ("long", "medium", "short"):
                pos_or_size = f"size:{val}"
        elif tag == "half:left":
            half_side = "left"
        elif tag == "half:right":
            half_side = "right"
    if pos_num is not None:
        return pos_num
    if half_side is not None and pos_or_size is not None:
        mapped = _BAY_BY_GEOMETRY_TAGS.get((half_side, pos_or_size))
        if mapped is not None:
            return mapped
    if suffix in _BAY_COLUMN_BY_SUFFIX:
        return _BAY_COLUMN_BY_SUFFIX[suffix]
    if half_side is not None:
        return 0 if half_side == "left" else 1
    return default


def resolve_stagger_tags(seg: Any) -> Tuple[int, int]:
    """
    Convenience helper resolving (altitude_tier, bay_column) from segment tags or legacy fallbacks.
    """
    return (get_segment_altitude_tier(seg), get_segment_bay_column(seg))


def stagger_by_altitude_tier(
    segments: Sequence[Any],
    reverse: bool = False,
) -> List[List[str]]:
    """
    Partitions segments by physical Y-altitude tier (Canopy -> Mid -> Low).
    Accepts flat segment sequences or nested ring cohorts.
    Inspects segment tags first with graceful fallback to legacy suffix tables.
    Returns a list of cohorts (one list per tier), each cohort sorted by segment name.
    """
    tiers: Dict[int, List[str]] = {}
    flat_items = []
    for item in segments:
        if isinstance(item, (list, tuple)):
            flat_items.extend(item)
        else:
            flat_items.append(item)

    for seg in flat_items:
        name, _, _ = _extract_segment_info(seg)
        tier = get_segment_altitude_tier(seg)
        tiers.setdefault(tier, []).append(name)

    return [sorted(tiers[k]) for k in sorted(tiers.keys(), reverse=reverse)]


def stagger_by_bay_column(
    segments: Sequence[Any],
    reverse: bool = False,
) -> List[List[str]]:
    """
    Partitions segments by horizontal bay column index (0..7 left-to-right).
    Inspects segment tags first with graceful fallback to legacy suffix tables.
    Returns a list of cohorts (one list per bay column), each cohort sorted by segment name.
    """
    cols: Dict[int, List[str]] = {}
    flat_items = []
    for item in segments:
        if isinstance(item, (list, tuple)):
            flat_items.extend(item)
        else:
            flat_items.append(item)

    for seg in flat_items:
        name, _, _ = _extract_segment_info(seg)
        col = get_segment_bay_column(seg)
        cols.setdefault(col, []).append(name)

    return [sorted(cols[k]) for k in sorted(cols.keys(), reverse=reverse)]


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
        if scene == "CHILL":
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
        name, tags, _ = _extract_segment_info(seg)
        orientation = getattr(seg, "orientation", "")
        for tag in tags:
            if tag == "orientation:vertical":
                orientation = "vertical"
                break
            elif tag == "orientation:horizontal":
                orientation = "horizontal"
                break

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


def _group_rings_by_altitude(rings: List[List[str]]) -> List[List[str]]:
    """Re-groups horizontal segments by physical Y-altitude tier (Canopy -> Mid -> Low)."""
    return stagger_by_altitude_tier(rings)


def _step_distance(idx: int, total: int, pattern: StaggerPattern) -> float:
    """Computes the cohort step multiplier for a given index and stagger pattern."""
    if pattern in (StaggerPattern.CASCADE_UP, StaggerPattern.ALTITUDE_CASCADE_UP):
        return float(total - 1 - idx)
    if pattern == StaggerPattern.CENTER_OUT:
        return abs(idx - (total - 1) / 2.0)
    return float(idx)


def generate_staggered_configs(
    allocation: Dict[str, str],
    verticals: List[str],
    rings: List[List[str]],
    base_technique: str = "fade_in_out",
    base_duration: float = 2.0,
    pattern: StaggerPattern = StaggerPattern.CASCADE_DOWN,
    step_delay: float = 0.15,
    pillar_wipe: bool = True,
    segments: Optional[Sequence[Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Builds per-segment transition configurations with staggered start offsets
    and/or complementary techniques across physical cohorts.
    """
    configs: Dict[str, Dict[str, Any]] = {}
    if not allocation:
        return configs

    seg_map: Dict[str, Any] = {}
    if segments:
        for s in segments:
            n, _, _ = _extract_segment_info(s)
            seg_map[n] = s
            sid = getattr(s, "id", None)
            if sid:
                seg_map[sid] = s

    def _resolve_col(seg_key: str) -> int:
        return get_segment_bay_column(seg_map.get(seg_key, seg_key))

    if pattern == StaggerPattern.SIMULTANEOUS:
        for seg in allocation:
            configs[seg] = {
                "type": base_technique,
                "duration": base_duration,
                "start_offset": 0.0,
                "direction": None,
            }
        return configs

    if pattern in (StaggerPattern.BAY_WAVE_LR, StaggerPattern.BAY_WAVE_RL):
        reverse_wave = pattern == StaggerPattern.BAY_WAVE_RL
        cols = sorted({_resolve_col(s) for s in allocation})
        num_cols = max(1, len(cols))
        col_rank = {c: (num_cols - 1 - i if reverse_wave else i) for i, c in enumerate(cols)}
        vert_set = set(verticals)
        for seg in allocation:
            rank = col_rank.get(_resolve_col(seg), 0)
            is_vert = seg in vert_set
            h_wipe = "silk_wipe_reverse" if reverse_wave else "silk_wipe"
            tech = ("iris_open" if base_technique == "fade_in_out" else base_technique) if is_vert else (
                h_wipe if base_technique in ("fade_in_out", "vertical_wipe") else base_technique
            )
            configs[seg] = {
                "type": tech,
                "duration": base_duration,
                "start_offset": round(rank * step_delay, 3),
                "direction": None if is_vert else ("DOWN" if reverse_wave else "UP"),
            }
        return configs

    if pattern in (StaggerPattern.ALTITUDE_CASCADE_DOWN, StaggerPattern.ALTITUDE_CASCADE_UP):
        if segments:
            tagged_rings = [[seg_map.get(s, s) for s in r] for r in rings]
            active_rings = stagger_by_altitude_tier(tagged_rings)
        else:
            active_rings = stagger_by_altitude_tier(rings)
    else:
        active_rings = rings

    has_rings = any(len(r) > 0 for r in active_rings)
    is_complementary = pattern == StaggerPattern.COHORT_COMPLEMENTARY
    vert_tech = (
        "vertical_wipe"
        if (pillar_wipe and base_technique in ("fade_in_out", "vertical_wipe"))
        else base_technique
    )
    vert_dur = min(base_duration, 1.2) if is_complementary else base_duration
    ring_tech = (
        ("fade_in_out" if base_technique in ("vertical_wipe", "explosion") else base_technique)
        if is_complementary
        else base_technique
    )
    vert_dir = (
        "UP" if pattern in (StaggerPattern.CASCADE_UP, StaggerPattern.ALTITUDE_CASCADE_UP)
        else (None if pattern == StaggerPattern.CENTER_OUT else "DOWN")
    )
    ring_start_base = 0.20 if (is_complementary and verticals) else 0.0

    if has_rings:
        for seg in verticals:
            if seg in allocation:
                configs[seg] = {
                    "type": vert_tech,
                    "duration": vert_dur,
                    "start_offset": 0.0,
                    "direction": vert_dir,
                }
        num_rings = len(active_rings)
        for ring_idx, ring in enumerate(active_rings):
            offset = round(ring_start_base + _step_distance(ring_idx, num_rings, pattern) * step_delay, 3)
            for seg in ring:
                if seg in allocation:
                    configs[seg] = {
                        "type": ring_tech,
                        "duration": base_duration,
                        "start_offset": offset,
                        "direction": None,
                    }
    else:
        num_v = len(verticals)
        for idx, seg in enumerate(verticals):
            if seg in allocation:
                offset = round(_step_distance(idx, num_v, pattern) * step_delay, 3)
                configs[seg] = {
                    "type": vert_tech,
                    "duration": vert_dur,
                    "start_offset": offset,
                    "direction": vert_dir,
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
