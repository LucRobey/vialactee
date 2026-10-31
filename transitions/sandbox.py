"""
transitions/sandbox.py - Run the transition sector alone and watch its decisions.

    python -m transitions.sandbox [--seconds 120] [--interval 8] [--bpm 120] [--seed 1] [--report]

Feeds scripted fake music into the front door at 30 fps, accepts every order, and prints
each transition: when it fired, why, which technique, and which mode each segment got.
With `--report`, prints summary coherence statistics (distinct modes, grouping histograms,
rule hit rates, forbid violations, mean time-to-repeat, same-mode no-ops, mean DNA distance,
and p99 casting execution time).
No audio, no hardware, no project code.
"""
import argparse
from collections import Counter
import math
import random
from typing import Any, Callable, Dict, List, Optional

from transitions.api import OrderAck, TransitionOrders, create_transition_service
from transitions.fakes import fake_installation, fake_music

FPS = 30.0


def _dna_distance(
    mode_dna: tuple,
    target_dna: Dict[str, float],
) -> float:
    et = float(target_dna.get("energy", 0.5))
    pt = float(target_dna.get("punch", 0.5))
    rt = float(target_dna.get("rhythm", 0.5))
    ct = float(target_dna.get("complexity", 0.5))
    return math.sqrt(
        (mode_dna[0] - et) ** 2
        + (mode_dna[1] - pt) ** 2
        + (mode_dna[2] - rt) ** 2
        + (mode_dna[3] - ct) ** 2
    )


def run(
    seconds: float = 120.0,
    interval: float = 8.0,
    bpm: float = 120.0,
    seed: Optional[int] = 1,
    echo: Optional[Callable[[str], None]] = print,
    report: bool = False,
) -> List[TransitionOrders]:
    """Simulate `seconds` of music and return every set of orders the sector produced."""
    if seed is not None:
        random.seed(seed)
    service = create_transition_service({"auto_transition_time": interval})
    inst = fake_installation()
    service.set_installation(inst)
    boot_modes = service.allocate_initial(fake_music(0.0, bpm))
    active_modes: Dict[str, str] = dict(boot_modes)

    fired: List[TransitionOrders] = []
    distinct_counts: List[int] = []
    grouping_counts: Counter = Counter()
    rule_hits: Counter = Counter()
    forbid_violations = 0
    same_mode_noops = 0
    total_segment_orders = 0
    dna_distances: List[float] = []
    cast_times_ms: List[float] = []
    last_seen_transition_idx: Dict[str, Dict[str, int]] = {s.name: {} for s in inst.segments}
    repeat_intervals: List[int] = []

    for seg_name, mname in active_modes.items():
        last_seen_transition_idx.setdefault(seg_name, {})[mname] = 0

    mgr = getattr(service, "_manager", None)
    cp = mgr.compiled_policy if mgr is not None else None

    dt = 1.0 / FPS
    t = 0.0
    trans_idx = 0
    while t < seconds:
        music = fake_music(t, bpm)
        orders = service.update(dt, music)
        if orders is not None:
            trans_idx += 1
            fired.append(orders)
            cast_res = getattr(mgr, "last_cast_result", None) if mgr is not None else None
            target_dna = mgr.evaluate_target_dna(music) if mgr is not None else {}

            if cast_res is not None:
                for zname, gid in cast_res.groupings_by_zone.items():
                    grouping_counts[f"{zname}:{gid}"] += 1
                for rid in cast_res.matched_rules:
                    rule_hits[rid] += 1
                forbid_violations += cast_res.forbid_violations
                cast_times_ms.append(cast_res.elapsed_ms)

            distinct_modes = {o.target_mode for o in orders.orders}
            distinct_counts.append(len(distinct_modes))

            for o in orders.orders:
                total_segment_orders += 1
                prev_mode = active_modes.get(o.segment)
                if prev_mode == o.target_mode:
                    same_mode_noops += 1
                seg_seen = last_seen_transition_idx.setdefault(o.segment, {})
                if o.target_mode in seg_seen:
                    repeat_intervals.append(trans_idx - seg_seen[o.target_mode])
                seg_seen[o.target_mode] = trans_idx
                active_modes[o.segment] = o.target_mode
                if cp is not None and o.target_mode in cp.mode_dna:
                    dna_distances.append(_dna_distance(cp.mode_dna[o.target_mode], target_dna))

            if echo:
                techniques = sorted({o.technique for o in orders.orders})
                echo(
                    f"[{t:6.1f}s] {music.scene:<11} energy={music.energy:.2f} "
                    f"reason={orders.reason:<12} technique={','.join(techniques)} "
                    f"duration={orders.orders[0].duration:.1f}s"
                )
                for o in orders.orders:
                    echo(f"           {o.segment:<12} -> {o.target_mode}")
            service.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))
        t += dt

    if echo:
        echo(f"{len(fired)} transitions in {seconds:.0f}s")
        if report:
            from transitions.policy import KNOWN_MODE_TAGS
            used_tags = set().union(*cp.mode_tags.values()) if (cp is not None and cp.mode_tags) else set()
            unused_vocab = sorted(KNOWN_MODE_TAGS - used_tags) if used_tags else []
            _print_report(
                echo=echo,
                num_transitions=len(fired),
                distinct_counts=distinct_counts,
                max_cap=cp.settings.max_different_modes if cp is not None else 3,
                grouping_counts=grouping_counts,
                rule_hits=rule_hits,
                forbid_violations=forbid_violations,
                repeat_intervals=repeat_intervals,
                same_mode_noops=same_mode_noops,
                total_segment_orders=total_segment_orders,
                dna_distances=dna_distances,
                cast_times_ms=cast_times_ms,
                unused_vocab=unused_vocab,
            )
    return fired


def _print_report(
    echo: Callable[[str], None],
    num_transitions: int,
    distinct_counts: List[int],
    max_cap: int,
    grouping_counts: Counter,
    rule_hits: Counter,
    forbid_violations: int,
    repeat_intervals: List[int],
    same_mode_noops: int,
    total_segment_orders: int,
    dna_distances: List[float],
    cast_times_ms: List[float],
    unused_vocab: Optional[List[str]] = None,
) -> None:
    echo("--- Mode Coherence Report ---")
    mean_distinct = (sum(distinct_counts) / len(distinct_counts)) if distinct_counts else 0.0
    max_distinct = max(distinct_counts) if distinct_counts else 0
    echo(f"Distinct modes      : mean={mean_distinct:.2f}, max={max_distinct} (cap={max_cap})")
    grp_str = ", ".join(f"{k}={v}" for k, v in sorted(grouping_counts.items())) or "none"
    echo(f"Grouping histogram  : {grp_str}")
    if rule_hits and num_transitions > 0:
        rules_str = ", ".join(f"{k}={v}/{num_transitions} ({100.0 * v / num_transitions:.0f}%)" for k, v in sorted(rule_hits.items()))
    else:
        rules_str = "0 hits"
    echo(f"Rule hit rates      : {rules_str}")
    echo(f"Forbid violations   : {forbid_violations}")
    mean_ttr = (sum(repeat_intervals) / len(repeat_intervals)) if repeat_intervals else float(num_transitions)
    echo(f"Mean time-to-repeat : {mean_ttr:.2f} transitions")
    noop_pct = (100.0 * same_mode_noops / total_segment_orders) if total_segment_orders > 0 else 0.0
    echo(f"Same-mode no-ops    : {same_mode_noops}/{total_segment_orders} ({noop_pct:.1f}%)")
    mean_dna = (sum(dna_distances) / len(dna_distances)) if dna_distances else 0.0
    echo(f"Mean DNA distance   : {mean_dna:.4f}")
    if cast_times_ms:
        sorted_ms = sorted(cast_times_ms)
        p99_idx = min(len(sorted_ms) - 1, max(0, int(math.ceil(0.99 * len(sorted_ms))) - 1))
        p99_ms = sorted_ms[p99_idx]
    else:
        p99_ms = 0.0
    echo(f"Casting latency p99 : {p99_ms:.3f} ms")
    echo(f"Unused vocabulary   : {', '.join(unused_vocab) if unused_vocab else 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the transition sector with fake music.")
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=8.0, help="auto transition interval (s)")
    parser.add_argument("--bpm", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--report", action="store_true", help="print Mode Coherence summary report")
    args = parser.parse_args()
    run(args.seconds, args.interval, args.bpm, args.seed, report=args.report)


if __name__ == "__main__":
    main()
