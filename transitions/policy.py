"""
transitions/policy.py - Mode Coherence Policy Compiler, Validator & Default Policy.
Strictly sealed: zero file I/O, zero external imports. Complies with AXIOM-07 (<= 500 lines).
"""

import copy
from dataclasses import dataclass, field
import logging
import math
import random
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple
import warnings

from transitions.api import ModeProfile, PolicyError, SegmentDescriptor

logger = logging.getLogger("transitions.policy")


class PolicyWarning(UserWarning): """Base warning for non-fatal policy issues."""
class NeutralRuleWeightWarning(PolicyWarning): """Issued when a rule has weight == 1.0 (no effect)."""
class UnusedModeTagWarning(PolicyWarning): """Issued when a rule references a vocabulary tag not present on any active mode."""


KNOWN_MODE_VOCABULARY: Dict[str, Tuple[str, ...]] = {
    "lead": ("beat", "level", "spectrum", "transient"), "axis": ("vertical", "horizontal"),
    "form": ("field", "bar", "wave", "head", "sparkle", "flash"),
    "origin": ("center", "bottom", "sweep", "global", "scatter"),
    "color": ("own-hue", "palette"), "layer": ("bed", "pulse", "meter", "accent"),
}
KNOWN_MODE_TAGS: FrozenSet[str] = frozenset(f"{ns}:{val}" for ns, vals in KNOWN_MODE_VOCABULARY.items() for val in vals)

DEFAULT_POLICY: Dict[str, Any] = {
    "version": 1, "settings": {"maxDifferentModes": 3, "temperature": 1.0, "memoryDepth": 8, "repeatPenalty": 3.0},
    "zones": {
        "pillars": {"segments": ["v1", "v2", "v3", "v4"], "groupings": [
            {"id": "pillars-all", "weight": 3, "groups": [["v1", "v2", "v3", "v4"]]},
            {"id": "pillars-halves", "weight": 2, "groups": [["v1", "v2"], ["v3", "v4"]]},
            {"id": "pillars-inner", "weight": 2, "groups": [["v2", "v3"], ["v1", "v4"]]},
        ]},
        "horizontals": {"segments": ["h00", "h10", "h11", "h20", "h30", "h31", "h32"], "groupings": [
            {"id": "h-all", "weight": 1, "groups": [["all"]]},
            {"id": "h-tiers", "weight": 2, "groups": [["tier:canopy"], ["tier:mid"], ["tier:low"]]},
            {"id": "h-halves", "weight": 2, "groups": [["half:left"], ["half:right"]]},
        ]},
    },
    "rules": [
        {"id": "no-vertical-axis-on-horizontals", "when": [{"at": "orientation:horizontal", "tag": "axis:vertical"}], "weight": 0.15},
        {"id": "no-horizontal-axis-on-verticals", "when": [{"at": "orientation:vertical", "tag": "axis:horizontal"}], "weight": 0.15},
    ],
}

DEFAULT_POLICY_SMALL: Dict[str, Any] = {
    "version": 1, "settings": {"maxDifferentModes": 2, "temperature": 1.0, "memoryDepth": 8, "repeatPenalty": 3.0},
    "zones": {"strips": {"segments": ["s1", "s2", "s3"], "groupings": [
        {"id": "strips-all", "weight": 3, "groups": [["all"]]},
        {"id": "strips-outer", "weight": 2, "groups": [["s1", "s3"], ["s2"]]},
        {"id": "strips-each", "weight": 1, "groups": [["s1"], ["s2"], ["s3"]]},
    ]}},
    "rules": [{"id": "no-horizontal-axis-on-verticals", "when": [{"at": "orientation:vertical", "tag": "axis:horizontal"}], "weight": 0.15}],
}


def _seg_id(seg: Any) -> str:
    sid = getattr(seg, "id", "") or ""
    if sid:
        return str(sid)
    name = str(getattr(seg, "name", seg) or "")
    return name[8:].strip() if name.startswith("Segment ") else name


def _seg_tags(seg: Any) -> Set[str]:
    tags = {str(t) for t in (getattr(seg, "tags", ()) or ()) if t}
    ori = getattr(seg, "orientation", "") or ""
    if not ori:
        name_l = str(getattr(seg, "name", "")).lower()
        ori = "horizontal" if " h" in name_l or name_l.startswith("h") else "vertical"
    tags.add(f"orientation:{ori}")
    return tags


def get_default_policy(segments: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    """Build an exact-partition default policy for the given installation segments."""
    if not segments:
        return copy.deepcopy(DEFAULT_POLICY)
    sids = [_seg_id(s) for s in segments]
    tag_map = {_seg_id(s): _seg_tags(s) for s in segments}
    all_tags = set().union(*tag_map.values()) if tag_map else set()
    if set(sids) == {"s1", "s2", "s3"}:
        return copy.deepcopy(DEFAULT_POLICY_SMALL)
    h_ids = ("h00", "h10", "h11", "h20", "h30", "h31", "h32")
    if set(sids) == {"v1", "v2", "v3", "v4", *h_ids}:
        if all(any(f"tier:{t}" in tag_map[h] for h in h_ids) for t in ("canopy", "mid", "low")) and all(
            any(f"half:{h}" in tag_map[s] for s in h_ids) for h in ("left", "right")
        ):
            return copy.deepcopy(DEFAULT_POLICY)
    verts = [s for s in sids if "orientation:vertical" in tag_map.get(s, set())]
    horizs = [s for s in sids if s not in verts]
    zones: Dict[str, Any] = {}
    if verts:
        v_grp: List[Dict[str, Any]] = [{"id": "pillars-all", "weight": 3, "groups": [["all"]]}]
        if len(verts) == 4:
            v_grp.extend([
                {"id": "pillars-halves", "weight": 2, "groups": [[verts[0], verts[1]], [verts[2], verts[3]]]},
                {"id": "pillars-inner", "weight": 2, "groups": [[verts[1], verts[2]], [verts[0], verts[3]]]},
            ])
        elif len(verts) == 3:
            v_grp.extend([
                {"id": "pillars-outer", "weight": 2, "groups": [[verts[0], verts[2]], [verts[1]]]},
                {"id": "pillars-each", "weight": 1, "groups": [[v] for v in verts]},
            ])
        elif len(verts) == 2:
            v_grp.append({"id": "pillars-each", "weight": 2, "groups": [[verts[0]], [verts[1]]]})
        zones["pillars"] = {"segments": verts, "groupings": v_grp}
    if horizs:
        h_grp: List[Dict[str, Any]] = [{"id": "h-all", "weight": 1, "groups": [["all"]]}]
        has_tiers = all(any(f"tier:{t}" in tag_map[h] for h in horizs) for t in ("canopy", "mid", "low"))
        has_halves = all(any(f"half:{hf}" in tag_map[h] for h in horizs) for hf in ("left", "right"))
        if has_tiers and has_halves:
            h_grp.extend([
                {"id": "h-tiers", "weight": 2, "groups": [["tier:canopy"], ["tier:mid"], ["tier:low"]]},
                {"id": "h-halves", "weight": 2, "groups": [["half:left"], ["half:right"]]},
            ])
        elif len(horizs) > 1:
            h_grp.append({"id": "h-each", "weight": 2, "groups": [[h] for h in horizs]})
        zones["horizontals"] = {"segments": horizs, "groupings": h_grp}
    rules: List[Dict[str, Any]] = []
    if "orientation:horizontal" in all_tags:
        rules.append({"id": "no-vertical-axis-on-horizontals", "when": [{"at": "orientation:horizontal", "tag": "axis:vertical"}], "weight": 0.15})
    if "orientation:vertical" in all_tags:
        rules.append({"id": "no-horizontal-axis-on-verticals", "when": [{"at": "orientation:vertical", "tag": "axis:horizontal"}], "weight": 0.15})
    return {
        "version": 1, "zones": zones, "rules": rules,
        "settings": {"maxDifferentModes": min(3, max(1, len(sids))), "temperature": 1.0, "memoryDepth": 8, "repeatPenalty": 3.0},
    }


@dataclass(frozen=True)
class PolicySettings:
    max_different_modes: int
    temperature: float
    memory_depth: int
    repeat_penalty: float
    maxDifferentModes = property(lambda self: self.max_different_modes)
    memoryDepth = property(lambda self: self.memory_depth)
    repeatPenalty = property(lambda self: self.repeat_penalty)


@dataclass(frozen=True)
class CompiledPlacement:
    at: Optional[str]
    target_segments: Tuple[str, ...]
    mode: Optional[str]
    tag: Optional[str]
    match: str
    matching_modes: FrozenSet[str]


@dataclass(frozen=True)
class CompiledRule:
    id: str
    is_forbid: bool
    weight: float
    log_weight: float
    note: str
    placements: Tuple[CompiledPlacement, ...]


@dataclass(frozen=True)
class CompiledGrouping:
    id: str
    weight: float
    groups: Tuple[Tuple[str, ...], ...]
    allowed_modes_per_group: Tuple[Tuple[str, ...], ...]


@dataclass(frozen=True)
class CompiledZone:
    name: str
    segments: Tuple[str, ...]
    groupings: Tuple[CompiledGrouping, ...]


@dataclass(frozen=True)
class CompiledPolicy:
    version: int
    settings: PolicySettings
    zones: Dict[str, CompiledZone]
    rules: Tuple[CompiledRule, ...]
    mode_names: Tuple[str, ...]
    mode_dna: Dict[str, Tuple[float, float, float, float]]
    mode_tags: Dict[str, FrozenSet[str]]
    segment_ids: Tuple[str, ...]
    segment_id_to_name: Dict[str, str]
    segment_name_to_id: Dict[str, str]
    segment_tags: Dict[str, FrozenSet[str]]
    raw: Dict[str, Any] = field(default_factory=dict)
    zone_names = property(lambda self: tuple(self.zones.keys()))


def evaluate_rule(rule: CompiledRule, cast: Dict[str, str]) -> bool:
    """Return True iff all placements in `rule` hold on the partial or full `cast` (seg_id -> mode_name)."""
    for p in rule.placements:
        if p.match == "all":
            if not p.target_segments or not all(cast.get(s) in p.matching_modes for s in p.target_segments):
                return False
        elif not any(cast.get(s) in p.matching_modes for s in p.target_segments):
            return False
    return True


def _is_valid_num(val: Any) -> bool:
    return not isinstance(val, bool) and isinstance(val, (int, float)) and not math.isnan(val) and not math.isinf(val)


def _validate_settings(raw: Any) -> PolicySettings:
    if not isinstance(raw, dict):
        raise PolicyError("Policy 'settings' must be a dict")
    defaults = {"maxDifferentModes": 3, "temperature": 1.0, "memoryDepth": 8, "repeatPenalty": 3.0}
    if set(raw.keys()) - set(defaults.keys()):
        raise PolicyError(f"Unknown settings keys: {sorted(set(raw.keys()) - set(defaults.keys()))}")
    m = {**defaults, **raw}
    md, temp, depth, pen = m["maxDifferentModes"], m["temperature"], m["memoryDepth"], m["repeatPenalty"]
    if isinstance(md, bool) or not isinstance(md, int) or md < 1:
        raise PolicyError(f"Setting 'maxDifferentModes' must be integer >= 1, got {md!r}")
    if not _is_valid_num(temp) or not (0.05 <= float(temp) <= 5.0):
        raise PolicyError(f"Setting 'temperature' must be in [0.05, 5.0], got {temp!r}")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
        raise PolicyError(f"Setting 'memoryDepth' must be integer >= 0, got {depth!r}")
    if not _is_valid_num(pen) or float(pen) < 0.0:
        raise PolicyError(f"Setting 'repeatPenalty' must be >= 0, got {pen!r}")
    return PolicySettings(int(md), float(temp), int(depth), float(pen))


def run_feasibility_probe(compiled: CompiledPolicy, casts_per_grouping: int = 200, seed: int = 42) -> bool:
    """Run load-time Monte Carlo feasibility probe across all groupings."""
    max_diff, forbid_rules, zones_list = compiled.settings.max_different_modes, [r for r in compiled.rules if r.is_forbid], list(compiled.zones.values())
    for z_idx, zone in enumerate(zones_list):
        for grouping in zone.groupings:
            rng = random.Random(seed)
            all_groups = [
                (grp_segs, allowed) for o_idx, o_zone in enumerate(zones_list)
                for grp_segs, allowed in zip((grouping if o_idx == z_idx else o_zone.groupings[0]).groups, (grouping if o_idx == z_idx else o_zone.groupings[0]).allowed_modes_per_group)
            ]
            feasible = False
            for _ in range(casts_per_grouping):
                cast, used, order, failed = {}, set(), list(range(len(all_groups))), False
                rng.shuffle(order)
                for step, idx in enumerate(order):
                    grp_segs, allowed = all_groups[idx]
                    rem_groups, rem_budget = len(order) - step, max_diff - len(used)
                    cands = [m for m in allowed if (m in used or rem_budget > 0) and not any(evaluate_rule(r, {**cast, **{s: m for s in grp_segs}}) for r in forbid_rules)]
                    if not cands:
                        failed = True
                        break
                    reusable, new_m = [m for m in cands if m in used], [m for m in cands if m not in used]
                    chosen = rng.choice(reusable) if (rem_groups > rem_budget and reusable and (not new_m or rng.random() < (rem_groups - rem_budget) / rem_groups)) else rng.choice(cands)
                    for s in grp_segs:
                        cast[s] = chosen
                    used.add(chosen)
                if not failed and len(used) <= max_diff and not any(evaluate_rule(r, cast) for r in forbid_rules):
                    feasible = True
                    break
            if not feasible:
                raise PolicyError(f"Grouping '{grouping.id}' in zone '{zone.name}' failed {casts_per_grouping}-cast feasibility probe")
    return True


def compile_policy(
    policy_raw: Dict[str, Any],
    segments: Sequence[SegmentDescriptor] = (),
    modes: Sequence[ModeProfile] = (),
) -> CompiledPolicy:
    """Parse, validate, and compile a raw policy dictionary into an immutable CompiledPolicy."""
    if not isinstance(policy_raw, dict):
        raise PolicyError(f"Policy must be a dict, got {type(policy_raw).__name__}")
    if "settings" in policy_raw and not isinstance(policy_raw["settings"], dict):
        raise PolicyError("Policy 'settings' must be a dict")
    if "zones" not in policy_raw:
        base = get_default_policy(segments)
        if "settings" in policy_raw:
            base["settings"].update(policy_raw["settings"])
        if "rules" in policy_raw:
            base["rules"] = policy_raw["rules"]
        policy_raw = base
    for req in ("settings", "zones", "rules"):
        if req not in policy_raw:
            raise PolicyError(f"Policy missing required top-level key: '{req}'")

    settings = _validate_settings(policy_raw["settings"])
    version = policy_raw.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise PolicyError(f"Policy 'version' must be integer >= 1, got {version!r}")

    seg_id_to_name, seg_name_to_id, seg_tag_map, seg_avail_modes, seg_ids_list = {}, {}, {}, {}, []
    for s in segments:
        sid, sname = _seg_id(s), getattr(s, "name", "") or _seg_id(s)
        if sid in seg_id_to_name:
            raise PolicyError(f"Duplicate segment id '{sid}'")
        seg_ids_list.append(sid)
        seg_id_to_name[sid], seg_name_to_id[sname], seg_name_to_id[sid] = sname, sid, sid
        seg_tag_map[sid] = frozenset(_seg_tags(s))
        if getattr(s, "available_modes", ()):
            seg_avail_modes[sid] = set(s.available_modes)

    mode_dna_map, mode_tag_map, mode_names_list, active_mode_tags = {}, {}, [], set()
    for m in modes:
        dna = tuple(float(x) for x in getattr(m, "dna", (0.5, 0.5, 0.5, 0.5)))
        if len(dna) != 4 or any(math.isnan(x) or x < 0.0 or x > 1.0 for x in dna):
            raise PolicyError(f"Mode '{m.name}' has invalid DNA: {dna!r}")
        mtags = frozenset(str(t) for t in getattr(m, "tags", ()))
        if any(":" not in t or t not in KNOWN_MODE_TAGS for t in mtags):
            raise PolicyError(f"Mode '{m.name}' has unknown vocabulary tag in {mtags}")
        if m.name not in mode_dna_map:
            mode_names_list.append(m.name)
        mode_dna_map[m.name], mode_tag_map[m.name] = (dna[0], dna[1], dna[2], dna[3]), mtags
        active_mode_tags.update(mtags)

    if not mode_names_list:
        from transitions.fakes import FAKE_MODE_PROFILES
        avail_union = set().union(*seg_avail_modes.values()) if seg_avail_modes else set()
        for fp in FAKE_MODE_PROFILES:
            if not avail_union or fp.name in avail_union:
                mode_names_list.append(fp.name)
                mode_dna_map[fp.name], mode_tag_map[fp.name] = fp.dna, frozenset(fp.tags)
                active_mode_tags.update(fp.tags)
        for extra in sorted(avail_union - set(mode_names_list)):
            mode_names_list.append(extra)
            mode_dna_map[extra], mode_tag_map[extra] = (0.5, 0.5, 0.5, 0.5), frozenset()

    mode_names_tuple, known_modes_set = tuple(mode_names_list), set(mode_names_list)
    zones_raw = policy_raw["zones"]
    if not isinstance(zones_raw, dict) or not zones_raw:
        raise PolicyError("Policy 'zones' must be a non-empty dict")

    if not seg_ids_list:
        for zdata in zones_raw.values():
            for s in (zdata.get("segments", []) if isinstance(zdata, dict) else []):
                if isinstance(s, str) and s not in seg_id_to_name:
                    seg_ids_list.append(s)
                    seg_id_to_name[s] = seg_name_to_id[s] = s
                    seg_tag_map[s] = frozenset({f"orientation:{'vertical' if s.startswith(('v', 's')) else 'horizontal'}"})

    inst_seg_set, seen_zone_segs, seen_grouping_ids = set(seg_ids_list), set(), set()
    zone_segs_by_name: Dict[str, Tuple[str, ...]] = {}
    expanded_zones: Dict[str, List[Tuple[str, float, Tuple[Tuple[str, ...], ...]]]] = {}

    for zname, zdata in zones_raw.items():
        if not isinstance(zname, str) or not zname.strip() or zname in seg_name_to_id or not isinstance(zdata, dict):
            raise PolicyError(f"Invalid zone '{zname}'")
        zsegs_raw, groupings_raw = zdata.get("segments"), zdata.get("groupings")
        if not isinstance(zsegs_raw, list) or not zsegs_raw or not isinstance(groupings_raw, list) or not groupings_raw:
            raise PolicyError(f"Zone '{zname}' requires non-empty 'segments' and 'groupings' lists")
        zsegs: List[str] = []
        for s in zsegs_raw:
            if not isinstance(s, str) or s not in seg_name_to_id:
                raise PolicyError(f"Zone '{zname}' references unknown segment '{s}'")
            sid = seg_name_to_id[s]
            if sid in zsegs or sid in seen_zone_segs:
                raise PolicyError(f"Duplicate or non-disjoint segment '{sid}' in zone '{zname}'")
            zsegs.append(sid)
            seen_zone_segs.add(sid)
        zsegs_tuple, zsegs_set = tuple(zsegs), set(zsegs)
        zone_segs_by_name[zname] = zsegs_tuple

        z_groupings: List[Tuple[str, float, Tuple[Tuple[str, ...], ...]]] = []
        for gdata in groupings_raw:
            if not isinstance(gdata, dict):
                raise PolicyError(f"Grouping in zone '{zname}' must be a dict")
            gid, gw, groups_raw = gdata.get("id"), gdata.get("weight"), gdata.get("groups")
            if not isinstance(gid, str) or not gid.strip() or gid in seen_grouping_ids:
                raise PolicyError(f"Invalid or duplicate grouping id '{gid}'")
            seen_grouping_ids.add(gid)
            if not _is_valid_num(gw) or float(gw) <= 0.0 or not isinstance(groups_raw, list) or not groups_raw:
                raise PolicyError(f"Grouping '{gid}' has invalid weight or groups")

            expanded_groups, covered = [], set()
            for grp in groups_raw:
                if not isinstance(grp, list) or not grp:
                    raise PolicyError(f"Group in '{gid}' must be a non-empty list")
                grp_exp: List[str] = []
                for member in grp:
                    if not isinstance(member, str) or not member.strip():
                        raise PolicyError(f"Invalid group member in '{gid}'")
                    matched = (
                        list(zsegs_tuple) if member == "all"
                        else ([s for s in zsegs_tuple if member in seg_tag_map.get(s, frozenset())] if ":" in member
                              else ([seg_name_to_id[member]] if (member in seg_name_to_id and seg_name_to_id[member] in zsegs_set) else []))
                    )
                    if not matched:
                        raise PolicyError(f"Member '{member}' in '{gid}' resolves to 0 segments in '{zname}'")
                    for s in matched:
                        if s in grp_exp or s in covered:
                            raise PolicyError(f"Segment '{s}' appears multiple times in grouping '{gid}'")
                        grp_exp.append(s)
                covered.update(grp_exp)
                expanded_groups.append(tuple(grp_exp))
            if covered != zsegs_set:
                raise PolicyError(f"Grouping '{gid}' does not partition zone '{zname}'")
            if gdata.get("enabled", True) is not False:
                z_groupings.append((gid, float(gw), tuple(expanded_groups)))
        if not z_groupings:
            raise PolicyError(f"Zone '{zname}' has no enabled groupings")
        expanded_zones[zname] = z_groupings

    if inst_seg_set and seen_zone_segs != inst_seg_set:
        raise PolicyError(f"Zones do not cover all installation segments; missing: {sorted(inst_seg_set - seen_zone_segs)}")

    rules_raw = policy_raw["rules"]
    if not isinstance(rules_raw, list):
        raise PolicyError("Policy 'rules' must be a list")

    compiled_rules, seen_rule_ids = [], set()
    for rdata in rules_raw:
        if not isinstance(rdata, dict):
            raise PolicyError("Rule must be a dict")
        rid, enabled = rdata.get("id"), rdata.get("enabled", True)
        if not isinstance(rid, str) or not rid.strip() or rid in seen_rule_ids or not isinstance(enabled, bool):
            raise PolicyError(f"Invalid rule id or enabled flag in '{rid}'")
        seen_rule_ids.add(rid)
        if ("effect" in rdata) == ("weight" in rdata):
            raise PolicyError(f"Rule '{rid}' must specify either 'effect': 'forbid' or 'weight'")

        is_forbid, rule_w = ("effect" in rdata), 1.0
        if is_forbid and rdata["effect"] != "forbid":
            raise PolicyError(f"Rule '{rid}' effect must be 'forbid'")
        if not is_forbid:
            rw = rdata["weight"]
            if not _is_valid_num(rw) or float(rw) <= 0.0:
                raise PolicyError(f"Rule '{rid}' weight must be > 0, got {rw!r}")
            rule_w = float(rw)
            if abs(rule_w - 1.0) < 1e-9:
                warnings.warn(f"Rule '{rid}' has weight 1.0 which has no effect.", category=NeutralRuleWeightWarning, stacklevel=2)

        when_raw = rdata.get("when")
        if not isinstance(when_raw, list) or not when_raw:
            raise PolicyError(f"Rule '{rid}' 'when' must be a non-empty list")
        placements: List[CompiledPlacement] = []
        for pdata in when_raw:
            if not isinstance(pdata, dict) or (set(pdata.keys()) - {"at", "mode", "tag", "match"}) or (("mode" in pdata) == ("tag" in pdata)):
                raise PolicyError(f"Placement in rule '{rid}' has invalid keys")
            pmode, ptag = pdata.get("mode"), pdata.get("tag")
            if pmode is not None:
                if not isinstance(pmode, str) or pmode not in known_modes_set:
                    raise PolicyError(f"Rule '{rid}' references unknown mode '{pmode}'")
                matching_modes = frozenset({pmode})
            else:
                if not isinstance(ptag, str) or ":" not in ptag or ptag not in KNOWN_MODE_TAGS:
                    raise PolicyError(f"Rule '{rid}' references unknown mode tag '{ptag}'")
                if modes and active_mode_tags and ptag not in active_mode_tags:
                    warnings.warn(f"Rule '{rid}' references unused mode tag '{ptag}'.", category=UnusedModeTagWarning, stacklevel=2)
                matching_modes = frozenset(m for m in mode_names_tuple if ptag in mode_tag_map.get(m, frozenset()))

            at_val, match_val = pdata.get("at"), pdata.get("match", "any")
            if match_val not in ("any", "all"):
                raise PolicyError(f"Rule '{rid}' placement 'match' must be 'any' or 'all'")
            if at_val is None:
                target_segs = tuple(seg_ids_list)
            elif not isinstance(at_val, str) or not at_val.strip():
                raise PolicyError(f"Rule '{rid}' placement 'at' must be a non-empty string")
            elif at_val in zone_segs_by_name:
                target_segs = zone_segs_by_name[at_val]
            elif at_val in seg_name_to_id:
                target_segs = (seg_name_to_id[at_val],)
            elif ":" in at_val:
                target_segs = tuple(s for s in seg_ids_list if at_val in seg_tag_map.get(s, frozenset()))
                if not target_segs:
                    raise PolicyError(f"Rule '{rid}' placement 'at': '{at_val}' resolves to 0 segments")
            else:
                raise PolicyError(f"Rule '{rid}' placement 'at': '{at_val}' is invalid")
            placements.append(CompiledPlacement(at_val, target_segs, pmode, ptag, match_val, matching_modes))

        if enabled:
            compiled_rules.append(CompiledRule(rid, is_forbid, rule_w, 0.0 if is_forbid else math.log(rule_w), str(rdata.get("note", "")), tuple(placements)))

    forbid_rules = [r for r in compiled_rules if r.is_forbid]
    compiled_zones: Dict[str, CompiledZone] = {}
    for zname, z_groupings in expanded_zones.items():
        comp_groupings: List[CompiledGrouping] = []
        for gid, gw, groups_tuple in z_groupings:
            allowed_per_group: List[Tuple[str, ...]] = []
            for grp_segs in groups_tuple:
                avail = [m for m in mode_names_tuple if all(m in seg_avail_modes[s] for s in grp_segs if s in seg_avail_modes)]
                surviving = [m for m in avail if not any(evaluate_rule(r, {s: m for s in grp_segs}) for r in forbid_rules)]
                if not surviving:
                    raise PolicyError(f"Static satisfiability failure: group {list(grp_segs)} in '{gid}' has 0 legal modes")
                allowed_per_group.append(tuple(surviving))
            comp_groupings.append(CompiledGrouping(gid, gw, groups_tuple, tuple(allowed_per_group)))
        compiled_zones[zname] = CompiledZone(zname, zone_segs_by_name[zname], tuple(comp_groupings))

    compiled = CompiledPolicy(
        version, settings, compiled_zones, tuple(compiled_rules), mode_names_tuple, mode_dna_map,
        mode_tag_map, tuple(seg_ids_list), seg_id_to_name, seg_name_to_id, seg_tag_map, policy_raw,
    )
    run_feasibility_probe(compiled, casts_per_grouping=200)
    return compiled
