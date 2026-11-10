"""
tools/ensemble_matrix.py
Per-part choreography measurement for ensemble Global Modes (Ensemble Law E3, the per-part mute test).

Runs a mode on the deterministic synthetic clip of tools/choreography_matrix.py, once unmuted and once
per muted driver, and reports the response of every declared part separately:
    python -m tools.ensemble_matrix Stalagmites_mode
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from tools.choreography_matrix import (
    DEFAULT_NB_BANDS,
    DEFAULT_PROFILE,
    SyntheticListener,
    step_synthetic_music,
)
from utils.choreography import DRIVERS, MUTE_CHANNELS
from utils.driver_mute import DriverMuteProxy

# Longer than MATRIX_CONFIG: the synthetic flux burst needs ~5 s to visit every band.
PART_MATRIX_CONFIG: Dict[str, int] = {
    "num_leds": 120,
    "warmup_frames": 60,
    "eval_frames": 480,
}
LEAD_FRACTION_F: float = 0.30      # same thresholds as Law 7, applied inside each part
RETAINED_G: float = 0.65


def run_parts_under_mutes(
    mode_cls: Any,
    muted_channels: Sequence[str] = (),
    num_leds: int = PART_MATRIX_CONFIG["num_leds"],
    warmup_frames: int = PART_MATRIX_CONFIG["warmup_frames"],
    eval_frames: int = PART_MATRIX_CONFIG["eval_frames"],
    nb_bands: int = DEFAULT_NB_BANDS,
    profile: str = DEFAULT_PROFILE,
) -> Dict[str, float]:
    """Run `mode_cls` on a composite strip under `muted_channels`; return R_std per part."""
    import modes.Mode as BaseModeMod

    listener = SyntheticListener(nb_bands=nb_bands, profile=profile)
    proxy = DriverMuteProxy(listener)
    live_modifiers = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
    for f in range(60):                      # pre-seed the running means used as frozen values
        step_synthetic_music(listener, f, live_modifiers)
        proxy.observe(alpha=0.10)
    for ch in muted_channels:
        proxy.set_muted(ch, True)

    rgb_list = np.zeros((num_leds, 3), dtype=np.int32)
    mode = mode_cls(mode_cls.__name__, "test_segment", proxy, None, list(range(num_leds)), rgb_list, {})
    mode.start()
    recorded = np.zeros((eval_frames, num_leds, 3), dtype=np.float64)
    try:
        for f in range(warmup_frames + eval_frames):
            step_synthetic_music(listener, f, live_modifiers)
            proxy.observe(alpha=0.05)
            proxy.sync_macro_modifiers(BaseModeMod.Mode, live_modifiers)
            mode.run()
            if f >= warmup_frames:
                recorded[f - warmup_frames] = mode.rgb_list
    finally:
        BaseModeMod.Mode.reset_mood_colors()

    per_led_std = np.std(recorded, axis=0).mean(axis=1)
    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for part, start, stop in mode.part_slices():
        sums[part] = sums.get(part, 0.0) + float(per_led_std[start:stop].sum())
        counts[part] = counts.get(part, 0) + (stop - start)
    return {part: sums[part] / max(1, counts[part]) for part in sums}


def measure_parts(mode_cls: Any, **config: Any) -> Dict[str, Dict[str, Any]]:
    """
    Per-part ablation table: for each declared part, R_std unmuted, with everything muted, and the
    contribution `R_std(full) - R_std(mute driver)` of each of the four drivers.
    """
    full = run_parts_under_mutes(mode_cls, (), **config)
    mute_all = run_parts_under_mutes(mode_cls, MUTE_CHANNELS, **config)
    by_driver = {drv: run_parts_under_mutes(mode_cls, (drv,), **config) for drv in DRIVERS}
    declared: Dict[str, str] = dict(getattr(mode_cls, "PARTS", {}))
    report: Dict[str, Dict[str, Any]] = {}
    for part, r_full in full.items():
        report[part] = {
            "driver": declared.get(part, ""),
            "r_std_full": r_full,
            "r_std_mute_all": mute_all.get(part, 0.0),
            "contributions": {drv: r_full - by_driver[drv].get(part, 0.0) for drv in DRIVERS},
            "retained": {
                drv: (by_driver[drv].get(part, 0.0) / r_full) if r_full > 1e-6 else 1.0 for drv in DRIVERS
            },
        }
    return report


def part_violations(report: Dict[str, Dict[str, Any]]) -> List[str]:
    """Ensemble Law E3 verdicts: empty when every part obeys its declared driver and only that one."""
    problems: List[str] = []
    for part, r in report.items():
        driver = r["driver"]
        contribs = r["contributions"]
        if driver not in DRIVERS:
            problems.append(f"{part}: no declared driver in PARTS")
            continue
        if r["r_std_full"] <= 1.0:
            problems.append(f"{part}: never moved on the synthetic clip (R_std={r['r_std_full']:.2f})")
            continue
        best = max(contribs, key=contribs.get)
        if best != driver:
            problems.append(f"{part}: declared {driver!r} but {best!r} dominates ({contribs})")
        budget = max(1e-6, r["r_std_full"] - r["r_std_mute_all"])
        if contribs[driver] < LEAD_FRACTION_F * budget:
            problems.append(f"{part}: {driver!r} carries {contribs[driver]:.2f} < {LEAD_FRACTION_F} x {budget:.2f}")
        for other in DRIVERS:
            if other != driver and r["retained"][other] < RETAINED_G:
                problems.append(f"{part}: muting {other!r} keeps only {r['retained'][other]:.2f} of its motion")
    return problems


def format_part_report(mode_name: str, report: Dict[str, Dict[str, Any]]) -> str:
    header = (
        f"{mode_name + ' part':<32} {'Driver':<10} {'R_std':>7} {'-all':>7} "
        f"{'d(beat)':>9} {'d(level)':>9} {'d(spectrum)':>12} {'d(transient)':>13}"
    )
    lines = [header, "-" * len(header)]
    for part, r in report.items():
        c = r["contributions"]
        lines.append(
            f"{part:<32} {r['driver']:<10} {r['r_std_full']:7.2f} {r['r_std_mute_all']:7.2f} "
            f"{c['beat']:+9.2f} {c['level']:+9.2f} {c['spectrum']:+12.2f} {c['transient']:+13.2f}"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> None:
    import argparse
    import importlib

    parser = argparse.ArgumentParser(description="Per-part mute test for an ensemble Global Mode.")
    parser.add_argument("module", help="Mode module / class name in modes/, e.g. Stalagmites_mode")
    args = parser.parse_args(argv)
    cls = getattr(importlib.import_module(f"modes.{args.module}"), args.module)
    report = measure_parts(cls)
    print(format_part_report(args.module, report))
    problems = part_violations(report)
    print("\nLaw E3: " + ("OK" if not problems else "\n  ".join(["VIOLATIONS"] + problems)))


if __name__ == "__main__":
    main()
