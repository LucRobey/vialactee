"""
benchmarks/engine/episode_slicer.py - Slices continuous telemetry into structured failure episodes.

Scans continuous benchmark runs and extracts isolated 5-10 second windows of failure
phenomena (Phase Inversion, Breakdown Ghost Beats, Stubborn Groove Locks) into structured
JSON specifically designed for AI agents to analyze patterns and suggest mathematical improvements.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import numpy as np


def extract_failure_episodes(
    song_name: str,
    true_beats: np.ndarray,
    est_beats: np.ndarray,
    telemetry: List[Dict[str, Any]],
    scorecard: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Analyzes beat alignment and telemetry to extract semantic failure episodes.
    """
    episodes: List[Dict[str, Any]] = []

    if len(true_beats) < 4 or len(est_beats) < 4:
        return episodes

    # Convert telemetry to arrays for fast slicing
    times = np.array([record.get("time", 0.0) for record in telemetry])
    bpms = np.array([record.get("bpm", 120.0) for record in telemetry])
    confidences = np.array([record.get("confidence", 0.0) for record in telemetry])
    custom_fluxes = np.array([record.get("custom_flux", 0.0) for record in telemetry])
    beat_tags = [record.get("beat_tag", "Bass/Kick") for record in telemetry]

    # -------------------------------------------------------------------------
    # 1. DETECT PHASE INVERSION EPISODES (The Upbeat Lock)
    # -------------------------------------------------------------------------
    # Condition: Beats are detected at the right tempo, but consistently aligned
    # halfway between true beats (phase offset ratio ~ 0.40 - 0.60 of beat period).
    if scorecard.get("upbeat_gap", 0.0) > 0.15:
        # Scan through estimated beats and find contiguous regions with ~50% period offset
        inversion_runs: List[Tuple[float, float, float]] = []
        current_run: List[float] = []

        for est in est_beats:
            dists = est - true_beats
            # Find closest true beat before and after
            past = dists[dists >= 0]
            if len(past) == 0:
                continue
            closest_prev_dist = np.min(past)
            min_dist_idx = np.argmin(np.abs(dists))
            nearest_dist = dists[min_dist_idx]

            # Approximate local period tau
            local_period = 0.5  # default
            if min_dist_idx > 0 and min_dist_idx < len(true_beats):
                local_period = float(true_beats[min_dist_idx] - true_beats[min_dist_idx - 1])

            offset_ratio = abs(nearest_dist) / max(0.1, local_period)

            # If offset is near 0.40 - 0.60 of period, it's an offbeat/upbeat hit
            if 0.35 <= offset_ratio <= 0.65:
                current_run.append(est)
            else:
                if len(current_run) >= 4:  # At least 4 consecutive inverted beats
                    inversion_runs.append((current_run[0], current_run[-1], len(current_run)))
                current_run = []

        if len(current_run) >= 4:
            inversion_runs.append((current_run[0], current_run[-1], len(current_run)))

        for idx, (start_t, end_t, count) in enumerate(inversion_runs[:3]):  # Limit to top 3
            # Context window: 3 seconds before and after
            win_start = max(0.0, start_t - 3.0)
            win_end = end_t + 3.0
            mask = (times >= win_start) & (times <= win_end)

            avg_bpm = float(np.mean(bpms[mask])) if np.any(mask) else 120.0
            avg_conf = float(np.mean(confidences[mask])) if np.any(mask) else 0.0

            episodes.append({
                "episode_id": f"EP_PHASE_INV_{song_name}_{idx + 1}",
                "song": song_name,
                "failure_type": "PHASE_INVERSION_UPBEAT",
                "time_window": [round(win_start, 2), round(win_end, 2)],
                "event_duration_sec": round(end_t - start_t, 2),
                "inverted_beats_count": count,
                "detected_bpm": round(avg_bpm, 1),
                "mean_confidence": round(avg_conf, 3),
                "diagnostic": (
                    f"Tracker locked 180° out-of-phase on the upbeat for {count} consecutive beats. "
                    f"AMLt is high but CMLt is low (Upbeat Gap: {scorecard.get('upbeat_gap', 0.0):.2f})."
                ),
            })

    # -------------------------------------------------------------------------
    # 2. DETECT DROPOUT GHOST BEAT EPISODES (Breakdown Hallucinations)
    # -------------------------------------------------------------------------
    # Condition: Beats emitted during sustained near-zero spectral flux.
    if len(custom_fluxes) > 0:
        flux_baseline = float(np.median(custom_fluxes))
        low_flux_threshold = max(0.05, flux_baseline * 0.20)

        ghost_beats: List[float] = []
        for est in est_beats:
            # Find closest telemetry frame
            t_idx = np.argmin(np.abs(times - est))
            is_real = telemetry[t_idx].get("is_real_beat", True)
            if is_real and custom_fluxes[t_idx] < low_flux_threshold:
                # Only flag as ghost beat if true beats are distant (>150ms)
                min_true_dist = np.min(np.abs(true_beats - est)) if len(true_beats) > 0 else 999.0
                if min_true_dist > 0.15:
                    ghost_beats.append(est)

        # Cluster ghost beats into episodes
        if len(ghost_beats) >= 4:
            g_start = ghost_beats[0]
            g_end = ghost_beats[-1]
            episodes.append({
                "episode_id": f"EP_GHOST_BURST_{song_name}_1",
                "song": song_name,
                "failure_type": "GHOST_BEAT_BURST",
                "time_window": [round(g_start, 2), round(g_end, 2)],
                "ghost_beats_count": len(ghost_beats),
                "diagnostic": (
                    f"Detected {len(ghost_beats)} ghost beats emitted during low-energy interval "
                    f"(flux < {low_flux_threshold:.2f}). Tracker should coast with is_real_beat=False."
                ),
            })

    # -------------------------------------------------------------------------
    # 3. DETECT TIMING JITTER EPISODES (Unsteady / Wobbly Phase)
    # -------------------------------------------------------------------------
    if scorecard.get("phase_jitter_ms", 0.0) > 25.0:
        episodes.append({
            "episode_id": f"EP_HIGH_JITTER_{song_name}_1",
            "song": song_name,
            "failure_type": "HIGH_PHASE_JITTER",
            "phase_jitter_ms": scorecard.get("phase_jitter_ms", 0.0),
            "phase_bias_ms": scorecard.get("mean_phase_bias_ms", 0.0),
            "diagnostic": (
                f"Phase jitter standard deviation is {scorecard.get('phase_jitter_ms', 0.0):.1f}ms "
                f"(exceeds 25ms threshold). The flywheel soft-snap or phase back-projection is over-correcting."
            ),
        })

    return episodes
