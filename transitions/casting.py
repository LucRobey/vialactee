"""
transitions/casting.py - Mode Coherence Casting Engine.

Implements the trigger-time allocation pipeline:
1. Per-zone grouping draw with recency decay
2. Fixed placement pinning for blocked segments
3. Log-domain initial mode draw under maxDifferentModes and forbid rules
4. 3-sweep Gibbs refinement (single-group moves + joint mode-class moves)
5. Anti-repeat guard (up to 5 redraws if exact match in memory)
6. Non-crashing fallback (retains active mode and logs warning if unsatisfiable)

Strictly sealed: zero file I/O, zero external imports. Complies with AXIOM-07.
"""

from dataclasses import dataclass
import logging
import math
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from transitions.api import SegmentDescriptor
from transitions.memory import TransitionMemory
from transitions.policy import CompiledGrouping, CompiledPolicy, evaluate_rule

logger = logging.getLogger("transitions.casting")


@dataclass(frozen=True)
class _FreeGroup:
    index: int
    free_segments: Tuple[str, ...]
    all_segments: Tuple[str, ...]
    allowed_modes: Tuple[str, ...]


@dataclass(frozen=True)
class CastResult:
    """Complete result and telemetry of a single transition cast."""
    orders_by_segment_name: Dict[str, str]
    full_cast_by_id: Dict[str, str]
    groupings_by_zone: Dict[str, str]
    groups: Tuple[Tuple[str, ...], ...]
    matched_rules: Tuple[str, ...]
    forbid_violations: int
    redraw_count: int
    fallback_segments: Tuple[str, ...]
    elapsed_ms: float


def compute_mode_fit(
    mode_dna: Tuple[float, float, float, float],
    target_dna: Dict[str, float],
) -> float:
    """Compute fit(m) = 1 / (1 + 4 * d^2) between 4D mode DNA and target DNA."""
    et = float(target_dna.get("energy", 0.5))
    pt = float(target_dna.get("punch", 0.5))
    rt = float(target_dna.get("rhythm", 0.5))
    ct = float(target_dna.get("complexity", 0.5))
    d_sq = (
        (mode_dna[0] - et) ** 2
        + (mode_dna[1] - pt) ** 2
        + (mode_dna[2] - rt) ** 2
        + (mode_dna[3] - ct) ** 2
    )
    return 1.0 / (1.0 + 4.0 * d_sq)


def _sample_from_log_weights(
    candidates: Sequence[str],
    log_weights: Sequence[float],
    rng: Any,
) -> str:
    """Sample one candidate from log-weights using max-subtraction to prevent underflow."""
    if len(candidates) == 1:
        return candidates[0]
    max_lw = max(log_weights)
    weights = [math.exp(max(-700.0, lw - max_lw)) for lw in log_weights]
    return rng.choices(candidates, weights=weights, k=1)[0]


def _pick_zone_groupings(
    policy: CompiledPolicy,
    memory: TransitionMemory,
    rng: Any,
) -> Tuple[Dict[str, str], List[Tuple[str, ...]], List[Tuple[str, ...]]]:
    """Step 2: Draw one grouping per zone weighted by catalogue weight and recency."""
    repeat_penalty = policy.settings.repeat_penalty
    chosen_by_zone: Dict[str, str] = {}
    all_groups: List[Tuple[str, ...]] = []
    all_allowed: List[Tuple[str, ...]] = []

    for zone_name, zone in policy.zones.items():
        groupings: Sequence[CompiledGrouping] = zone.groupings
        if len(groupings) == 1:
            picked = groupings[0]
        else:
            weights = [
                memory.grouping_weight(zone_name, g.id, g.weight, repeat_penalty)
                for g in groupings
            ]
            picked = rng.choices(groupings, weights=weights, k=1)[0]
        chosen_by_zone[zone_name] = picked.id
        all_groups.extend(picked.groups)
        all_allowed.extend(picked.allowed_modes_per_group)

    return chosen_by_zone, all_groups, all_allowed


def cast_transition(
    policy: CompiledPolicy,
    target_dna: Dict[str, float],
    segments: Sequence[SegmentDescriptor],
    memory: TransitionMemory,
    rng: Optional[Any] = None,
    gibbs_sweeps: int = 3,
    max_redraws: int = 5,
) -> CastResult:
    """Run the 6-step Mode Coherence casting algorithm."""
    t0 = time.perf_counter()
    rand = rng if rng is not None else random

    if not policy.segment_ids:
        return CastResult({}, {}, {}, (), (), 0, 0, (), 0.0)

    temperature = policy.settings.temperature
    inv_temp = 1.0 / temperature
    repeat_penalty = policy.settings.repeat_penalty
    max_modes = policy.settings.max_different_modes

    forbid_rules = tuple(r for r in policy.rules if r.is_forbid)
    soft_rules = tuple(r for r in policy.rules if not r.is_forbid)

    # Precompute (1/T) * ln(fit(m)) for every mode
    log_fit_scaled: Dict[str, float] = {}
    for mname in policy.mode_names:
        dna = policy.mode_dna.get(mname, (0.5, 0.5, 0.5, 0.5))
        fit = compute_mode_fit(dna, target_dna)
        log_fit_scaled[mname] = inv_temp * math.log(max(1e-12, fit))

    # Map current active modes & blocked status by canonical segment ID
    active_by_id: Dict[str, str] = {}
    blocked_cast: Dict[str, str] = {}
    default_mode = policy.mode_names[0] if policy.mode_names else "Rainbow"
    for s in segments:
        sid = policy.segment_name_to_id.get(getattr(s, "id", "") or s.name) or policy.segment_name_to_id.get(s.name)
        if not sid:
            continue
        cur = s.active_mode or (s.available_modes[0] if s.available_modes else default_mode)
        active_by_id[sid] = cur
        if s.is_blocked:
            blocked_cast[sid] = cur

    best_cast: Dict[str, str] = {}
    best_groupings: Dict[str, str] = {}
    best_groups: Tuple[Tuple[str, ...], ...] = ()
    best_fallbacks: Tuple[str, ...] = ()
    redraw_count = 0

    total_attempts = max(1, 1 + max_redraws)
    for attempt in range(total_attempts):
        chosen_groupings, raw_groups, raw_allowed = _pick_zone_groupings(policy, memory, rand)

        # Build free groups (excluding blocked segments)
        free_groups: List[_FreeGroup] = []
        for idx, (grp_segs, allowed) in enumerate(zip(raw_groups, raw_allowed)):
            free_segs = tuple(s for s in grp_segs if s not in blocked_cast)
            if free_segs:
                free_groups.append(_FreeGroup(idx, free_segs, grp_segs, allowed))

        # Step 4: Initial draw (with inner retries if random group order dead-ends)
        group_modes: Dict[int, str] = {}
        fallback_group_indices: Set[int] = set()

        for init_try in range(5):
            group_modes.clear()
            fallback_group_indices.clear()
            partial_cast = dict(blocked_cast)
            used_modes = set(partial_cast.values())
            visit_order = list(free_groups)
            rand.shuffle(visit_order)
            dead_end = False

            for fg in visit_order:
                legal_cands: List[str] = []
                log_weights: List[float] = []
                for m in fg.allowed_modes:
                    if m not in used_modes and len(used_modes) >= max_modes:
                        continue
                    for s in fg.free_segments:
                        partial_cast[s] = m
                    if any(evaluate_rule(r, partial_cast) for r in forbid_rules):
                        for s in fg.free_segments:
                            partial_cast.pop(s, None)
                        continue
                    var = memory.variety_factor(fg.free_segments, m, repeat_penalty)
                    rule_lw = sum(r.log_weight for r in soft_rules if evaluate_rule(r, partial_cast))
                    lw = log_fit_scaled[m] + math.log(max(1e-12, var)) + rule_lw
                    legal_cands.append(m)
                    log_weights.append(lw)
                    for s in fg.free_segments:
                        partial_cast.pop(s, None)

                if not legal_cands:
                    dead_end = True
                    if init_try == 4:
                        fallback_group_indices.add(fg.index)
                        for s in fg.free_segments:
                            partial_cast[s] = active_by_id.get(s, default_mode)
                    else:
                        break
                else:
                    picked_m = _sample_from_log_weights(legal_cands, log_weights, rand)
                    group_modes[fg.index] = picked_m
                    for s in fg.free_segments:
                        partial_cast[s] = picked_m
                    used_modes.add(picked_m)

            if not dead_end:
                break

        # Build full cast from blocked + drawn + fallback
        cast: Dict[str, str] = dict(blocked_cast)
        active_free_groups = [fg for fg in free_groups if fg.index not in fallback_group_indices]
        for fg in free_groups:
            if fg.index in fallback_group_indices:
                for s in fg.free_segments:
                    cast[s] = active_by_id.get(s, default_mode)
            else:
                m = group_modes[fg.index]
                for s in fg.free_segments:
                    cast[s] = m

        # Step 5: Rule-aware Gibbs refinement (3 sweeps: group moves + mode-class moves)
        if active_free_groups and gibbs_sweeps > 0:
            for _ in range(gibbs_sweeps):
                # 5a. Group moves
                sweep_groups = list(active_free_groups)
                rand.shuffle(sweep_groups)
                for fg in sweep_groups:
                    cur_m = group_modes[fg.index]
                    other_modes: Set[str] = set(blocked_cast.values())
                    for other_fg in active_free_groups:
                        if other_fg.index != fg.index:
                            other_modes.add(group_modes[other_fg.index])

                    cands: List[str] = []
                    lws: List[float] = []
                    for m in fg.allowed_modes:
                        if m != cur_m and m not in other_modes and len(other_modes) >= max_modes:
                            continue
                        for s in fg.free_segments:
                            cast[s] = m
                        if any(evaluate_rule(r, cast) for r in forbid_rules):
                            continue
                        var = memory.variety_factor(fg.free_segments, m, repeat_penalty)
                        rule_lw = sum(r.log_weight for r in soft_rules if evaluate_rule(r, cast))
                        cands.append(m)
                        lws.append(log_fit_scaled[m] + math.log(max(1e-12, var)) + rule_lw)

                    if cands:
                        chosen_m = _sample_from_log_weights(cands, lws, rand)
                    else:
                        chosen_m = cur_m
                    group_modes[fg.index] = chosen_m
                    for s in fg.free_segments:
                        cast[s] = chosen_m

                # 5b. Mode-class moves (jointly re-draw all free groups sharing a mode)
                distinct_free_modes = list(dict.fromkeys(group_modes.values()))
                rand.shuffle(distinct_free_modes)
                for class_mode in distinct_free_modes:
                    class_fgs = [fg for fg in active_free_groups if group_modes.get(fg.index) == class_mode]
                    if not class_fgs:
                        continue
                    other_modes = set(blocked_cast.values())
                    for other_fg in active_free_groups:
                        if group_modes[other_fg.index] != class_mode:
                            other_modes.add(group_modes[other_fg.index])

                    common_allowed = [
                        m for m in class_fgs[0].allowed_modes
                        if all(m in fg.allowed_modes for fg in class_fgs[1:])
                    ]
                    class_segs = tuple(s for fg in class_fgs for s in fg.free_segments)
                    cands = []
                    lws = []
                    for m in common_allowed:
                        if m != class_mode and m not in other_modes and len(other_modes) >= max_modes:
                            continue
                        for s in class_segs:
                            cast[s] = m
                        if any(evaluate_rule(r, cast) for r in forbid_rules):
                            continue
                        var = memory.variety_factor(class_segs, m, repeat_penalty)
                        rule_lw = sum(r.log_weight for r in soft_rules if evaluate_rule(r, cast))
                        cands.append(m)
                        lws.append(log_fit_scaled[m] + math.log(max(1e-12, var)) + rule_lw)

                    chosen_m = _sample_from_log_weights(cands, lws, rand) if cands else class_mode
                    for fg in class_fgs:
                        group_modes[fg.index] = chosen_m
                    for s in class_segs:
                        cast[s] = chosen_m

        fallbacks = tuple(
            s for fg in free_groups if fg.index in fallback_group_indices for s in fg.free_segments
        )
        best_cast = cast
        best_groupings = chosen_groupings
        best_groups = tuple(raw_groups)
        best_fallbacks = fallbacks

        # Step 6: Anti-repeat guard
        if attempt < total_attempts - 1 and memory.is_exact_repeat(best_cast):
            redraw_count += 1
            continue
        break

    if best_fallbacks:
        logger.warning(
            "Coherence casting fallback: keeping current mode on segments %s (no legal mode satisfied all constraints)",
            list(best_fallbacks),
        )

    fallback_set = set(best_fallbacks)
    orders_by_name: Dict[str, str] = {}
    for sid, mname in best_cast.items():
        if sid in blocked_cast or sid in fallback_set:
            continue
        seg_name = policy.segment_id_to_name.get(sid, sid)
        orders_by_name[seg_name] = mname

    ordered_only_cast = {
        sid: m for sid, m in best_cast.items() if sid not in blocked_cast and sid not in fallback_set
    }
    violations = sum(1 for r in forbid_rules if evaluate_rule(r, ordered_only_cast))
    matched_soft = tuple(r.id for r in soft_rules if evaluate_rule(r, best_cast))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return CastResult(
        orders_by_segment_name=orders_by_name,
        full_cast_by_id=best_cast,
        groupings_by_zone=best_groupings,
        groups=best_groups,
        matched_rules=matched_soft,
        forbid_violations=violations,
        redraw_count=redraw_count,
        fallback_segments=best_fallbacks,
        elapsed_ms=elapsed_ms,
    )
