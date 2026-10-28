"""
tools/choreography_matrix.py
Synthetic music stimulus runner, response metrics, and 13 x 4 choreography measurement matrix.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
import math
import numpy as np

from utils.choreography import DRIVERS, MUTE_CHANNELS
from utils.driver_mute import DriverMuteProxy

SYNTHETIC_CLIP_VERSION: str = "1"
DEFAULT_NB_BANDS: int = 8
MATRIX_CONFIG: Dict[str, int] = {
    "num_leds": 40,
    "warmup_frames": 30,
    "eval_frames": 120,
}


def compute_response_metrics(frames: np.ndarray) -> Tuple[float, float]:
    """
    Compute (R_std, R_diff) over a (T, nb_of_leds, 3) frame history.
    - R_std: mean per-LED temporal standard deviation (amplitude budget metric).
    - R_diff: mean per-LED frame-to-frame absolute delta (velocity / busyness indicator).
    """
    if frames.ndim != 3 or frames.shape[0] < 2:
        return 0.0, 0.0
    f64 = frames.astype(np.float64)
    r_std = float(np.mean(np.std(f64, axis=0)))
    r_diff = float(np.mean(np.abs(np.diff(f64, axis=0))))
    return r_std, r_diff


class SyntheticContext:
    def __init__(self) -> None:
        self.is_silent: bool = False
        self.energy: float = 0.5
        self.power: float = 0.5
        self.tension: float = 0.2
        self.beat_trust: float = 0.90
        self.salience: float = 0.85
        self.is_locked: bool = True
        self.is_real_beat: bool = False
        self.is_syncopated: bool = False
        self.is_drop_impact: bool = False
        self.is_drop_imminent: bool = False
        self.is_structural_cut: bool = False
        self.drop_progress: float = 0.0
        self.drop_countdown: float = 0.0
        self.scene: str = "GROOVE"
        self.spectral_tilt: float = 0.0
        self.vertical_center: float = 0.5


class SyntheticListener:
    def __init__(self, nb_bands: int = DEFAULT_NB_BANDS) -> None:
        self.dt: float = 1.0 / 60.0
        self.fps_ratio: float = 1.0
        self.bpm: float = 124.0
        self.beat_phase: float = 0.0
        self.beat_count: int = 0
        self.is_beat: bool = False
        self.is_real_beat: bool = False
        self.beat_confidence: float = 0.90
        self.beat_trust: float = 0.90
        self.rhythm_salience: float = 0.85
        self.live_rhythm_salience: float = 0.85
        self.asserved_total_power: float = 0.5
        self.smoothed_total_power: float = 0.5
        self.live_asserved_total_power: float = 0.5
        self.asserved_novelty: float = 0.2
        self.nb_of_fft_band: int = nb_bands
        self.asserved_fft_band: np.ndarray = np.full(nb_bands, 0.35, dtype=np.float64)
        self._delayed_asserved_fft_band: np.ndarray = self.asserved_fft_band.copy()
        self.smoothed_fft_band_values: np.ndarray = self.asserved_fft_band.copy()
        self.fft_band_values: np.ndarray = self.asserved_fft_band.copy()
        self.band_proportion: np.ndarray = np.full(nb_bands, 1.0 / nb_bands, dtype=np.float64)
        self.band_flux: np.ndarray = np.zeros(nb_bands, dtype=np.float64)
        self.beat_tag: str = "Bass/Kick"
        self.is_song_change: bool = False
        self.is_verse_chorus_change: bool = False
        self.context: SyntheticContext = SyntheticContext()


def step_synthetic_music(listener: SyntheticListener, frame_idx: int, live_modifiers: np.ndarray) -> None:
    """
    Advance the deterministic synthetic music clip by one 60 Hz frame.
    Simultaneously exercises beat, level, spectrum, transient, and macro channels
    with non-harmonic frequencies so their temporal contributions are orthogonal.
    """
    dt = listener.dt
    t = frame_idx * dt
    ctx = listener.context
    nb = listener.nb_of_fft_band

    # 1. Beat envelope (124 BPM = 2.0667 Hz)
    prev_phase = listener.beat_phase
    listener.beat_phase = (t * (listener.bpm / 60.0)) % 1.0
    wrapped = frame_idx > 0 and listener.beat_phase < prev_phase
    if wrapped:
        listener.beat_count += 1

    # 2. Level swell (slow 0.55 Hz + 1.17 Hz envelope in [0.12, 0.94])
    lvl = 0.53 + 0.30 * math.sin(2.0 * math.pi * 0.55 * t) + 0.11 * math.cos(2.0 * math.pi * 1.17 * t)
    lvl = max(0.08, min(0.98, lvl))
    listener.asserved_total_power = lvl
    listener.smoothed_total_power = lvl
    listener.live_asserved_total_power = lvl
    ctx.energy = lvl
    ctx.power = lvl

    # 3. Spectrum movement (traveling spectral peak at 0.83 Hz)
    center_pos = 0.50 + 0.38 * math.sin(2.0 * math.pi * 0.83 * t)
    for b in range(nb):
        b_norm = b / max(1.0, float(nb - 1))
        dist = b_norm - center_pos
        val = 0.10 + 0.80 * math.exp(-(dist * dist) / 0.08)
        listener.asserved_fft_band[b] = val
    listener._delayed_asserved_fft_band[:] = listener.asserved_fft_band
    listener.smoothed_fft_band_values[:] = listener.asserved_fft_band
    listener.fft_band_values[:] = listener.asserved_fft_band
    tot_b = float(np.sum(listener.asserved_fft_band))
    if tot_b > 1e-6:
        listener.band_proportion[:] = listener.asserved_fft_band / tot_b
    half = nb // 2
    bass_sum = float(np.sum(listener.asserved_fft_band[:half]))
    high_sum = float(np.sum(listener.asserved_fft_band[half:]))
    ctx.spectral_tilt = (high_sum - bass_sum) / max(1e-6, high_sum + bass_sum)
    ctx.vertical_center = float(
        np.sum(np.arange(nb, dtype=np.float64) * listener.asserved_fft_band) / max(1e-6, (nb - 1) * tot_b)
    )

    # 4. Transients (1-frame beat hits, spectral flux bursts, and periodic drop_hit)
    listener.is_beat = wrapped
    listener.is_real_beat = wrapped
    ctx.is_real_beat = wrapped
    ctx.is_drop_impact = (frame_idx in (90, 210))
    tags = ("Bass/Kick", "Snare/Mid", "Hi-hat/Cymbal")
    listener.beat_tag = tags[listener.beat_count % 3]
    listener.band_flux.fill(0.0)
    if wrapped or (frame_idx % 19 == 0):
        active_b = (frame_idx // 19 + listener.beat_count) % nb
        listener.band_flux[active_b] = 28.0
        listener.band_flux[0] = max(listener.band_flux[0], 0.85 if wrapped else 0.45)

    # 5. Macro modifiers & tension
    ctx.tension = 0.45 + 0.35 * math.sin(2.0 * math.pi * 0.31 * t)
    ctx.drop_progress = max(0.0, 1.0 - ((frame_idx - 90) / 45.0)) if 90 <= frame_idx < 135 else 0.0
    live_modifiers[0] = 1.0 + 0.18 * math.sin(2.0 * math.pi * 0.25 * t)  # mood_pace
    live_modifiers[1] = 1.0 + 0.15 * math.cos(2.0 * math.pi * 0.25 * t)  # mood_sharpness
    live_modifiers[2] = 1.0 - 0.10 * math.sin(2.0 * math.pi * 0.25 * t)  # mood_trail
    live_modifiers[3] = 0.12 + 0.10 * math.sin(2.0 * math.pi * 0.35 * t)  # mood_accent


def run_mode_under_mutes(
    mode_cls: Any,
    muted_channels: Sequence[str] = (),
    num_leds: int = MATRIX_CONFIG["num_leds"],
    warmup_frames: int = MATRIX_CONFIG["warmup_frames"],
    eval_frames: int = MATRIX_CONFIG["eval_frames"],
    nb_bands: int = DEFAULT_NB_BANDS,
    return_lock_trace: bool = False,
) -> Any:
    """
    Run `mode_cls` on the deterministic synthetic music clip under `muted_channels`.
    Returns `(R_std, R_diff)` by default, or `(R_std, R_diff, lock_trace)` when `return_lock_trace=True`.
    """
    import random
    import modes.Mode as BaseModeMod

    random.seed(42)
    np.random.seed(42)

    listener = SyntheticListener(nb_bands=nb_bands)
    proxy = DriverMuteProxy(listener)
    live_modifiers = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)

    # Pre-seed running means over 60 unmuted frames so frozen values are true clip means
    for f in range(60):
        step_synthetic_music(listener, f, live_modifiers)
        proxy.observe(alpha=0.10)

    for ch in muted_channels:
        proxy.set_muted(ch, True)

    rgb_list = np.zeros((num_leds, 3), dtype=np.int32)
    indexes = list(range(num_leds))
    mode = mode_cls(mode_cls.__name__, "test_segment", proxy, None, indexes, rgb_list, {})

    recorded = np.zeros((eval_frames, num_leds, 3), dtype=np.int32)
    lock_trace = np.zeros(eval_frames, dtype=np.float64)
    total_frames = warmup_frames + eval_frames
    try:
        for f in range(total_frames):
            step_synthetic_music(listener, f, live_modifiers)
            proxy.observe(alpha=0.05)
            proxy.sync_macro_modifiers(BaseModeMod.Mode, live_modifiers)
            mode.run()
            if f >= warmup_frames:
                idx = f - warmup_frames
                recorded[idx] = mode.rgb_list
                if return_lock_trace:
                    lock_trace[idx] = float(mode.rhythm_lock)
    finally:
        BaseModeMod.Mode.reset_mood_colors()

    r_std, r_diff = compute_response_metrics(recorded)
    if return_lock_trace:
        return r_std, r_diff, lock_trace
    return r_std, r_diff


def measure_mode_choreography(
    mode_cls: Any,
    num_leds: int = MATRIX_CONFIG["num_leds"],
    warmup_frames: int = MATRIX_CONFIG["warmup_frames"],
    eval_frames: int = MATRIX_CONFIG["eval_frames"],
    nb_bands: int = DEFAULT_NB_BANDS,
) -> Dict[str, Any]:
    """
    Evaluate a mode across `full`, `mute_lead`, `mute_sec`, `mute_all`, and all 4 individual driver mutes.
    Returns a dictionary of R_std, R_diff, and ablation contributions `R_std(full) - R_std(mute_d)`.
    """
    lead = getattr(mode_cls, "LEAD", "")
    sec_tuple = getattr(mode_cls, "SECONDARY", ())
    sec = sec_tuple[0] if sec_tuple else None

    r_std_full, r_diff_full = run_mode_under_mutes(
        mode_cls, (), num_leds, warmup_frames, eval_frames, nb_bands=nb_bands
    )
    by_driver: Dict[str, Tuple[float, float]] = {}
    for drv in DRIVERS:
        by_driver[drv] = run_mode_under_mutes(
            mode_cls, (drv,), num_leds, warmup_frames, eval_frames, nb_bands=nb_bands
        )

    r_std_mute_lead, r_diff_mute_lead = by_driver.get(lead, (r_std_full, r_diff_full))
    if sec is not None:
        r_std_mute_sec, r_diff_mute_sec = by_driver[sec]
    else:
        r_std_mute_sec, r_diff_mute_sec = r_std_full, r_diff_full

    r_std_mute_all, r_diff_mute_all = run_mode_under_mutes(
        mode_cls, MUTE_CHANNELS, num_leds, warmup_frames, eval_frames, nb_bands=nb_bands
    )

    contributions = {drv: r_std_full - by_driver[drv][0] for drv in DRIVERS}
    lead_contrib = contributions.get(lead, 0.0)
    sec_contrib = contributions.get(sec, 0.0) if sec is not None else 0.0

    return {
        "mode": mode_cls.__name__,
        "lead": lead,
        "secondary": sec or "none",
        "r_std_full": r_std_full,
        "r_diff_full": r_diff_full,
        "r_std_mute_lead": r_std_mute_lead,
        "r_diff_mute_lead": r_diff_mute_lead,
        "r_std_mute_sec": r_std_mute_sec,
        "r_diff_mute_sec": r_diff_mute_sec,
        "r_std_mute_all": r_std_mute_all,
        "r_diff_mute_all": r_diff_mute_all,
        "lead_contrib": lead_contrib,
        "sec_contrib": sec_contrib,
        "lead_share": (lead_contrib / r_std_full) if r_std_full > 1e-6 else 0.0,
        "sec_retained": (r_std_mute_sec / r_std_full) if r_std_full > 1e-6 else 1.0,
        "contributions": contributions,
    }


def measure_all_registered_modes(
    num_leds: int = MATRIX_CONFIG["num_leds"],
    warmup_frames: int = MATRIX_CONFIG["warmup_frames"],
    eval_frames: int = MATRIX_CONFIG["eval_frames"],
    nb_bands: int = DEFAULT_NB_BANDS,
) -> List[Dict[str, Any]]:
    """Measure all modes registered in `config/modes.json` in canonical catalog order."""
    import importlib
    import json
    import os

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    modes_json = os.path.join(repo_root, "config", "modes.json")
    with open(modes_json, "r", encoding="utf-8") as f:
        entries = json.load(f).get("standard_modes", [])

    results: List[Dict[str, Any]] = []
    for entry in entries:
        mod = importlib.import_module(f"modes.{entry['module']}")
        cls = getattr(mod, entry["class"])
        results.append(
            measure_mode_choreography(cls, num_leds, warmup_frames, eval_frames, nb_bands=nb_bands)
        )
    return results


def format_measurement_report(results: Sequence[Dict[str, Any]]) -> str:
    """Format the 13 x 4 conditions matrix and per-driver ablation table."""
    lines: List[str] = []
    header = (
        f"{'Mode':<28} {'Lead':<10} {'Sec':<10} "
        f"{'R_std(full)':>11} {'R_std(-lead)':>12} {'R_std(-sec)':>11} {'R_std(-all)':>11} "
        f"{'d(lead)':>9} {'d(sec)':>9} {'R_diff':>8}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        lines.append(
            f"{r['mode']:<28} {r['lead']:<10} {r['secondary']:<10} "
            f"{r['r_std_full']:11.2f} {r['r_std_mute_lead']:12.2f} {r['r_std_mute_sec']:11.2f} {r['r_std_mute_all']:11.2f} "
            f"{r['lead_contrib']:+9.2f} {r['sec_contrib']:+9.2f} {r['r_diff_full']:8.2f}"
        )
    lines.append("")
    ablation_hdr = (
        f"{'Mode':<28} {'Lead':<10} {'d(beat)':>10} {'d(level)':>10} "
        f"{'d(spectrum)':>12} {'d(transient)':>13}"
    )
    lines.append(ablation_hdr)
    lines.append("-" * len(ablation_hdr))
    for r in results:
        c = r["contributions"]
        lines.append(
            f"{r['mode']:<28} {r['lead']:<10} {c['beat']:+10.2f} {c['level']:+10.2f} "
            f"{c['spectrum']:+12.2f} {c['transient']:+13.2f}"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the 13 x 4 choreography stimulus measurement matrix.")
    parser.add_argument(
        "--bands",
        type=int,
        default=DEFAULT_NB_BANDS,
        help=f"Number of FFT frequency bands (default: {DEFAULT_NB_BANDS})",
    )
    args = parser.parse_args(argv)
    print(format_measurement_report(measure_all_registered_modes(nb_bands=args.bands)))


if __name__ == "__main__":
    main()
