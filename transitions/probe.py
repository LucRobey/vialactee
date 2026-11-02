"""
transitions/probe.py - Load-time Monte Carlo feasibility probe for compiled coherence policies.
Strictly sealed: zero file I/O. Imported (and re-exported) by transitions/policy.py.
"""

import random
from typing import TYPE_CHECKING

from transitions.api import PolicyError

if TYPE_CHECKING:
    from transitions.policy import CompiledPolicy


def run_feasibility_probe(compiled: "CompiledPolicy", casts_per_grouping: int = 200, seed: int = 42) -> bool:
    """Run load-time Monte Carlo feasibility probe across all groupings."""
    from transitions.policy import evaluate_rule  # lazy: policy imports this module
    max_diff, forbid_rules, zones_list = compiled.settings.max_different_modes, [r for r in compiled.rules if r.is_forbid], list(compiled.zones.values())
    targets = [(z_idx, g) for z_idx, zone in enumerate(zones_list) for g in zone.groupings]
    if compiled.whole is not None:
        targets.append((-1, compiled.whole))
    for z_idx, grouping in targets:
        if True:
            rng = random.Random(seed)
            if z_idx < 0:
                all_groups = list(zip(grouping.groups, grouping.allowed_modes_per_group))
            else:
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
                where = f"zone '{zones_list[z_idx].name}'" if z_idx >= 0 else "wholeInstallation"
                raise PolicyError(f"Grouping '{grouping.id}' in {where} failed {casts_per_grouping}-cast feasibility probe")
    return True
