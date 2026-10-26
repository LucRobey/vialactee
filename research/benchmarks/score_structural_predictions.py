"""
research/benchmarks/score_structural_predictions.py - Structural Music Event Scoring Benchmark.

Scores model-predicted musical boundaries, buildups, and drops against ground-truth
annotations in research/benchmarks/ground_truth/structural_annotations.json.

Evaluates:
1. Section Boundary Precision, Recall, and F1@0.5s tolerance (standard MIR tolerance).
2. Climax / Drop Timing Error (jitter in ms) and Anticipation Lead-Time (seconds in advance).
3. False Alarm Rate (FAR per minute) during unannotated steady sections.
"""

from __future__ import annotations
import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple, Union

# Ensure repository root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np


# =====================================================================
# DATA TYPES & NORMALIZATION
# =====================================================================

def load_ground_truth(gt_path: str) -> Dict[str, Any]:
    """Loads ground-truth structural annotations JSON file."""
    if not os.path.exists(gt_path):
        raise FileNotFoundError(f"Ground truth file not found: {gt_path}")
    with open(gt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "tracks" not in data:
        raise ValueError(f"Invalid annotations schema: missing 'tracks' key in {gt_path}")
    return data


def normalize_track_predictions(raw_pred: Any) -> Dict[str, Any]:
    """
    Normalizes arbitrary prediction formats into standardized structure:
    {
        "boundaries": [float, ...],
        "drops": [{"time_sec": float, "announced_at_sec": Optional[float], "lead_time_sec": Optional[float]}, ...]
    }
    """
    boundaries: List[float] = []
    drops: List[Dict[str, Any]] = []

    # If dict has "events" key (e.g. ground-truth format or event array)
    if isinstance(raw_pred, dict) and "events" in raw_pred:
        raw_pred = raw_pred["events"]

    if isinstance(raw_pred, list):
        for item in raw_pred:
            if isinstance(item, (int, float)):
                boundaries.append(float(item))
            elif isinstance(item, dict):
                t = float(item.get("time_sec", item.get("time", 0.0)))
                etype = item.get("type", "SECTION_CHANGE").upper()
                if "DROP" in etype or "CLIMAX" in etype:
                    drops.append({
                        "time_sec": t,
                        "announced_at_sec": item.get("announced_at_sec"),
                        "lead_time_sec": item.get("lead_time_sec"),
                    })
                elif "BUILDUP" in etype or "RISER" in etype:
                    # Buildups link to drops/lead-time, not macro section boundaries
                    pass
                else:
                    boundaries.append(t)

    elif isinstance(raw_pred, dict):
        # Format: {"boundaries": [...], "drops": [...]}
        raw_bounds = raw_pred.get("boundaries", [])
        for b in raw_bounds:
            if isinstance(b, (int, float)):
                boundaries.append(float(b))
            elif isinstance(b, dict):
                boundaries.append(float(b.get("time_sec", b.get("time", 0.0))))

        raw_drops = raw_pred.get("drops", raw_pred.get("climaxes", []))
        for d in raw_drops:
            if isinstance(d, (int, float)):
                drops.append({"time_sec": float(d), "announced_at_sec": None, "lead_time_sec": None})
            elif isinstance(d, dict):
                drops.append({
                    "time_sec": float(d.get("time_sec", d.get("time", 0.0))),
                    "announced_at_sec": d.get("announced_at_sec"),
                    "lead_time_sec": d.get("lead_time_sec"),
                })

    return {
        "boundaries": sorted(boundaries),
        "drops": sorted(drops, key=lambda x: x["time_sec"]),
    }


# =====================================================================
# METRIC EVALUATION FUNCTIONS
# =====================================================================

def evaluate_boundaries(
    gt_boundaries: List[float],
    pred_boundaries: List[float],
    tolerance: float = 0.5
) -> Dict[str, Any]:
    """
    Computes bipartite greedy matching between ground truth and predicted
    section boundaries within +/- tolerance window using minimum-distance matching.
    """
    gt_sorted = sorted(gt_boundaries)
    pred_sorted = sorted(pred_boundaries)

    candidates: List[Tuple[float, int, int]] = []
    for p_idx, p_time in enumerate(pred_sorted):
        for g_idx, g_time in enumerate(gt_sorted):
            dist = abs(p_time - g_time)
            if dist <= tolerance:
                candidates.append((dist, p_idx, g_idx))

    candidates.sort(key=lambda x: x[0])

    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    matched_pairs: List[Tuple[float, float, float]] = []  # (gt, pred, error_ms)

    for dist, p_idx, g_idx in candidates:
        if p_idx not in matched_pred and g_idx not in matched_gt:
            matched_pred.add(p_idx)
            matched_gt.add(g_idx)
            matched_pairs.append((gt_sorted[g_idx], pred_sorted[p_idx], dist * 1000.0))

    tp = len(matched_pairs)
    fp = len(pred_sorted) - tp
    fn = len(gt_sorted) - tp

    if tp + fp > 0:
        precision = tp / float(tp + fp)
    else:
        precision = 1.0 if fn == 0 else 0.0

    if tp + fn > 0:
        recall = tp / float(tp + fn)
    else:
        recall = 1.0 if fp == 0 else 0.0

    if precision + recall > 0:
        f1 = 2.0 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    timing_errors = [m[2] for m in matched_pairs]
    mean_error = float(np.mean(timing_errors)) if timing_errors else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_timing_error_ms": mean_error,
        "matched_pairs": matched_pairs,
        "unmatched_gt": [gt_sorted[i] for i in range(len(gt_sorted)) if i not in matched_gt],
        "unmatched_pred": [pred_sorted[i] for i in range(len(pred_sorted)) if i not in matched_pred],
    }


def evaluate_drops(
    gt_events: List[Dict[str, Any]],
    pred_drops: List[Dict[str, Any]],
    tolerance: float = 1.0
) -> Dict[str, Any]:
    """
    Evaluates drop / climax detections: timing jitter (ms) and anticipation
    lead time (seconds in advance) using minimum-distance bipartite matching.
    """
    # Extract ground truth drops and buildup partners
    gt_drops = [e for e in gt_events if e.get("type", "").upper() in ("CLIMAX_OR_DROP", "DROP", "CLIMAX")]
    gt_buildups = {
        e.get("pair_id"): e for e in gt_events
        if e.get("type", "").upper() in ("BUILDUP_OR_RISER", "BUILDUP", "RISER") and e.get("pair_id")
    }

    gt_sorted = sorted(gt_drops, key=lambda x: x["time_sec"])
    pred_sorted = sorted(pred_drops, key=lambda x: x["time_sec"])

    candidates: List[Tuple[float, int, int]] = []
    for p_idx, p_obj in enumerate(pred_sorted):
        p_time = p_obj["time_sec"]
        for g_idx, g_obj in enumerate(gt_sorted):
            dist = abs(p_time - g_obj["time_sec"])
            if dist <= tolerance:
                candidates.append((dist, p_idx, g_idx))

    candidates.sort(key=lambda x: x[0])

    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    matched_records: List[Dict[str, Any]] = []

    for dist, p_idx, g_idx in candidates:
        if p_idx not in matched_pred and g_idx not in matched_gt:
            matched_pred.add(p_idx)
            matched_gt.add(g_idx)
            g_obj = gt_sorted[g_idx]
            p_obj = pred_sorted[p_idx]
            p_time = p_obj["time_sec"]
            jitter_ms = dist * 1000.0

            # Compute lead time (seconds in advance)
            lead_sec = 0.0
            if p_obj.get("lead_time_sec") is not None:
                lead_sec = float(p_obj["lead_time_sec"])
            elif p_obj.get("announced_at_sec") is not None:
                lead_sec = max(0.0, g_obj["time_sec"] - float(p_obj["announced_at_sec"]))

            # Buildup coverage if linked
            coverage = None
            pid = g_obj.get("pair_id")
            if pid and pid in gt_buildups:
                buildup_start = gt_buildups[pid]["time_sec"]
                buildup_dur = max(0.1, g_obj["time_sec"] - buildup_start)
                coverage = min(1.0, max(0.0, lead_sec / buildup_dur))

            matched_records.append({
                "gt_time": g_obj["time_sec"],
                "pred_time": p_time,
                "jitter_ms": jitter_ms,
                "lead_time_sec": lead_sec,
                "buildup_coverage": coverage,
                "pair_id": pid,
            })

    tp = len(matched_records)
    fp = len(pred_sorted) - tp
    fn = len(gt_sorted) - tp

    if tp + fp > 0:
        precision = tp / float(tp + fp)
    else:
        precision = 1.0 if fn == 0 else 0.0

    if tp + fn > 0:
        recall = tp / float(tp + fn)
    else:
        recall = 1.0 if fp == 0 else 0.0

    if precision + recall > 0:
        f1 = 2.0 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    jitters = [r["jitter_ms"] for r in matched_records]
    leads = [r["lead_time_sec"] for r in matched_records]
    covs = [r["buildup_coverage"] for r in matched_records if r["buildup_coverage"] is not None]

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_jitter_ms": float(np.mean(jitters)) if jitters else 0.0,
        "median_jitter_ms": float(np.median(jitters)) if jitters else 0.0,
        "max_jitter_ms": float(np.max(jitters)) if jitters else 0.0,
        "mean_lead_time_sec": float(np.mean(leads)) if leads else 0.0,
        "mean_buildup_coverage": float(np.mean(covs)) if covs else 0.0,
        "matched_records": matched_records,
    }


def evaluate_steady_false_alarms(
    gt_events: List[Dict[str, Any]],
    all_predictions: List[float],
    total_duration_sec: float,
    tolerance: float = 0.5
) -> Dict[str, Any]:
    """
    Computes false alarm rate during unannotated steady sections.
    Steady sections are defined as track duration excluding any GT event +/- tolerance.
    """
    if total_duration_sec <= 0:
        return {"steady_duration_sec": 0.0, "false_alarm_count": 0, "false_alarm_rate_per_min": 0.0}

    # Build exclusion intervals around all GT events
    intervals: List[Tuple[float, float]] = []
    for e in gt_events:
        t = float(e["time_sec"])
        s = max(0.0, t - tolerance)
        en = min(total_duration_sec, t + tolerance)
        intervals.append((s, en))

    intervals.sort(key=lambda x: x[0])

    # Merge overlapping exclusion intervals
    merged: List[Tuple[float, float]] = []
    for iv in intervals:
        if not merged:
            merged.append(iv)
        else:
            prev_s, prev_e = merged[-1]
            if iv[0] <= prev_e:
                merged[-1] = (prev_s, max(prev_e, iv[1]))
            else:
                merged.append(iv)

    # Invert merged intervals to find steady regions
    steady_intervals: List[Tuple[float, float]] = []
    curr = 0.0
    for s, en in merged:
        if s > curr:
            steady_intervals.append((curr, s))
        curr = max(curr, en)
    if curr < total_duration_sec:
        steady_intervals.append((curr, total_duration_sec))

    steady_duration = sum(en - s for s, en in steady_intervals)

    # Count predictions landing in steady intervals
    false_alarms = []
    for p in all_predictions:
        in_steady = False
        for s, en in steady_intervals:
            if s <= p <= en:
                in_steady = True
                break
        if in_steady:
            false_alarms.append(p)

    count_fa = len(false_alarms)
    far_per_min = (count_fa / steady_duration * 60.0) if steady_duration > 1.0 else 0.0

    return {
        "steady_duration_sec": steady_duration,
        "false_alarm_count": count_fa,
        "false_alarm_rate_per_min": far_per_min,
        "false_alarm_timestamps": false_alarms,
    }


# =====================================================================
# AGGREGATE EVALUATION PIPELINE
# =====================================================================

def score_structural_predictions(
    ground_truth: Union[str, Dict[str, Any]],
    predictions: Union[str, Dict[str, Any]],
    tolerance: float = 0.5,
    drop_tolerance: float = 1.0,
    filter_tracks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Runs comprehensive structural evaluation across all available tracks.
    """
    if isinstance(ground_truth, str):
        gt_data = load_ground_truth(ground_truth)
    else:
        gt_data = ground_truth

    if isinstance(predictions, str):
        if not os.path.exists(predictions):
            raise FileNotFoundError(f"Predictions file not found: {predictions}")
        with open(predictions, "r", encoding="utf-8") as f:
            pred_data = json.load(f)
    else:
        pred_data = predictions

    gt_tracks = gt_data.get("tracks", {})
    results: Dict[str, Any] = {
        "tolerance_sec": tolerance,
        "drop_tolerance_sec": drop_tolerance,
        "tracks": {},
        "overall": {},
    }

    tot_bound_tp = 0
    tot_bound_fp = 0
    tot_bound_fn = 0
    bound_f1_list: List[float] = []

    tot_drop_tp = 0
    tot_drop_fp = 0
    tot_drop_fn = 0
    drop_jitters: List[float] = []
    drop_leads: List[float] = []

    tot_steady_sec = 0.0
    tot_false_alarms = 0

    eval_tracks = list(gt_tracks.keys())
    if filter_tracks:
        eval_tracks = [t for t in eval_tracks if t in filter_tracks]

    for t_name in eval_tracks:
        t_gt = gt_tracks[t_name]
        dur = float(t_gt.get("duration_sec", 0.0))
        gt_events = t_gt.get("events", [])

        # Extract GT boundaries (SECTION_CHANGE, BREAKDOWN_OR_SOLO)
        gt_bound_times = [
            e["time_sec"] for e in gt_events
            if e.get("type") in ("SECTION_CHANGE", "BREAKDOWN_OR_SOLO")
        ]

        # Normalize track predictions
        raw_track_pred = pred_data.get(t_name, {})
        norm_pred = normalize_track_predictions(raw_track_pred)

        # 1. Section Boundary Score
        bound_metrics = evaluate_boundaries(gt_bound_times, norm_pred["boundaries"], tolerance=tolerance)
        tot_bound_tp += bound_metrics["tp"]
        tot_bound_fp += bound_metrics["fp"]
        tot_bound_fn += bound_metrics["fn"]
        bound_f1_list.append(bound_metrics["f1"])

        # 2. Climax / Drop Score
        drop_metrics = evaluate_drops(gt_events, norm_pred["drops"], tolerance=drop_tolerance)
        tot_drop_tp += drop_metrics["tp"]
        tot_drop_fp += drop_metrics["fp"]
        if t_gt.get("has_climaxes", True):
            tot_drop_fn += drop_metrics["fn"]
            for r in drop_metrics["matched_records"]:
                drop_jitters.append(r["jitter_ms"])
                drop_leads.append(r["lead_time_sec"])

        # 3. Steady False Alarm Score
        all_pred_times = sorted(set(norm_pred["boundaries"] + [d["time_sec"] for d in norm_pred["drops"]]))
        steady_metrics = evaluate_steady_false_alarms(gt_events, all_pred_times, dur, tolerance=tolerance)
        tot_steady_sec += steady_metrics["steady_duration_sec"]
        tot_false_alarms += steady_metrics["false_alarm_count"]

        results["tracks"][t_name] = {
            "duration_sec": dur,
            "has_climaxes": t_gt.get("has_climaxes", True),
            "status": t_gt.get("status", "unreviewed"),
            "num_gt_boundaries": len(gt_bound_times),
            "num_gt_drops": len([e for e in gt_events if e.get("type", "").upper() in ("CLIMAX_OR_DROP", "DROP", "CLIMAX")]),
            "boundaries": bound_metrics,
            "drops": drop_metrics,
            "steady": steady_metrics,
        }

    # Macro & Micro aggregation
    # Boundaries
    micro_p = tot_bound_tp / float(tot_bound_tp + tot_bound_fp) if (tot_bound_tp + tot_bound_fp) > 0 else 0.0
    micro_r = tot_bound_tp / float(tot_bound_tp + tot_bound_fn) if (tot_bound_tp + tot_bound_fn) > 0 else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) > 0 else 0.0
    macro_f1 = float(np.mean(bound_f1_list)) if bound_f1_list else 0.0

    # Drops
    drop_p = tot_drop_tp / float(tot_drop_tp + tot_drop_fp) if (tot_drop_tp + tot_drop_fp) > 0 else 0.0
    drop_r = tot_drop_tp / float(tot_drop_tp + tot_drop_fn) if (tot_drop_tp + tot_drop_fn) > 0 else 0.0
    drop_f1 = (2 * drop_p * drop_r / (drop_p + drop_r)) if (drop_p + drop_r) > 0 else 0.0

    # Overall steady FAR
    overall_far = (tot_false_alarms / tot_steady_sec * 60.0) if tot_steady_sec > 1.0 else 0.0

    results["overall"] = {
        "num_tracks": len(eval_tracks),
        "boundary_micro_precision": micro_p,
        "boundary_micro_recall": micro_r,
        "boundary_micro_f1": micro_f1,
        "boundary_macro_f1": macro_f1,
        "drop_precision": drop_p,
        "drop_recall": drop_r,
        "drop_f1": drop_f1,
        "drop_mean_jitter_ms": float(np.mean(drop_jitters)) if drop_jitters else 0.0,
        "drop_median_jitter_ms": float(np.median(drop_jitters)) if drop_jitters else 0.0,
        "drop_mean_lead_time_sec": float(np.mean(drop_leads)) if drop_leads else 0.0,
        "total_steady_duration_sec": tot_steady_sec,
        "total_steady_false_alarms": tot_false_alarms,
        "steady_false_alarm_rate_per_min": overall_far,
    }

    return results


def print_scorecard(results: Dict[str, Any]) -> None:
    """Pretty prints the structural evaluation results table."""
    ov = results.get("overall", {})
    tol = results.get("tolerance_sec", 0.5)

    print("\n" + "=" * 88)
    print(f"       VIALACTEE STRUCTURAL NOVELTY & DROP BENCHMARK SCORECARD")
    print(f"       Boundary Window: +/-{tol*1000:.0f}ms | Evaluated Tracks: {ov.get('num_tracks', 0)}")
    print("=" * 88)
    header = f"{'Track':<36} | {'Bound F1':<8} | {'Drop F1':<8} | {'Jitter':<9} | {'Lead(s)':<8} | {'Steady FAR'}"
    print(header)
    print("-" * 88)

    for t_name, t_res in results.get("tracks", {}).items():
        short_name = (t_name[:33] + "...") if len(t_name) > 36 else t_name
        b_res = t_res["boundaries"]
        d_res = t_res["drops"]
        is_unreviewed = (t_res.get("status") == "unreviewed")

        if is_unreviewed and t_res.get("num_gt_boundaries", 0) == 0:
            b_f1 = "Unrev"
        else:
            b_f1 = f"{b_res['f1']:.3f}"

        if not t_res.get("has_climaxes"):
            d_f1 = "N/A" if d_res["fp"] == 0 else f"0.000 ({d_res['fp']}FP)"
        elif is_unreviewed and t_res.get("num_gt_drops", 0) == 0:
            d_f1 = "Unrev" if d_res["fp"] == 0 else f"0.000 ({d_res['fp']}FP)"
        else:
            d_f1 = f"{d_res['f1']:.3f}"

        jit = f"{d_res['mean_jitter_ms']:.1f}ms" if d_res["tp"] > 0 else "-"
        lead = f"{d_res['mean_lead_time_sec']:.2f}s" if d_res["tp"] > 0 else "-"
        far = f"{t_res['steady']['false_alarm_rate_per_min']:.2f}/min"

        print(f"{short_name:<36} | {b_f1:<8} | {d_f1:<8} | {jit:<9} | {lead:<8} | {far}")

    print("=" * 88)
    print("  OVERALL AGGREGATE SUMMARY:")
    print(f"  * Boundary Micro F1@0.5s:    {ov.get('boundary_micro_f1', 0.0):.4f} (P: {ov.get('boundary_micro_precision', 0.0):.3f}, R: {ov.get('boundary_micro_recall', 0.0):.3f})")
    print(f"  * Boundary Macro F1:         {ov.get('boundary_macro_f1', 0.0):.4f}")
    print(f"  * Drop Detection F1:         {ov.get('drop_f1', 0.0):.4f} (P: {ov.get('drop_precision', 0.0):.3f}, R: {ov.get('drop_recall', 0.0):.3f})")
    print(f"  * Drop Timing Jitter:        {ov.get('drop_mean_jitter_ms', 0.0):.1f} ms (Median: {ov.get('drop_median_jitter_ms', 0.0):.1f} ms)")
    print(f"  * Drop Mean Lead Time:       {ov.get('drop_mean_lead_time_sec', 0.0):.2f} s in advance")
    print(f"  * Steady False Alarm Rate:   {ov.get('steady_false_alarm_rate_per_min', 0.0):.2f} alarms / min ({ov.get('total_steady_false_alarms', 0)} total across {ov.get('total_steady_duration_sec', 0)/60.0:.1f} min)")
    print("=" * 88 + "\n")


# =====================================================================
# LIVE MODEL EVALUATION SIMULATOR
# =====================================================================

def run_model_predictions_simulation(model_name: str, tracks: List[str]) -> Dict[str, Any]:
    """
    Runs a live audio analyzer model (or StructuralNoveltyDetector) across benchmark tracks
    at 60 FPS using fast cached audio arrays, extracting predicted structural changes.
    """
    from music.StructuralNoveltyDetector import StructuralNoveltyDetector
    from music.RhythmConfig import RhythmConfig

    predictions: Dict[str, Any] = {}

    for t_name in tracks:
        res = resolve_audio_from_cache(t_name)
        if res is None:
            continue
        y, sr = res
        duration = len(y) / float(sr)
        print(f"  Simulating structural novelty on '{t_name}' ({duration:.1f}s)...", flush=True)

        config = RhythmConfig()
        detector = StructuralNoveltyDetector(nb_fft_bands=8, config=config)

        # 60 FPS audio stepping across full track length
        hop = int(round(sr / 60.0))
        n_frames = max(0, (len(y) - 1024) // hop)
        dt = 1.0 / 60.0

        if n_frames <= 0:
            continue

        window = np.hanning(1024)
        sub_y = y[:n_frames * hop + 1024]
        if len(sub_y) < 1024:
            continue

        # Vectorized batch FFT (30x faster)
        chunks = np.lib.stride_tricks.sliding_window_view(sub_y, 1024)[::hop][:n_frames]
        fft_mags = np.abs(np.fft.rfft(chunks * window, axis=1))

        all_bands = np.column_stack([
            np.mean(fft_mags[:, :8], axis=1),
            np.mean(fft_mags[:, 8:16], axis=1),
            np.mean(fft_mags[:, 16:32], axis=1),
            np.mean(fft_mags[:, 32:64], axis=1),
            np.mean(fft_mags[:, 64:128], axis=1),
            np.mean(fft_mags[:, 128:256], axis=1),
            np.mean(fft_mags[:, 256:384], axis=1),
            np.mean(fft_mags[:, 384:512], axis=1),
        ]).astype(np.float32)

        powers = np.sum(all_bands, axis=1)

        for i in range(len(all_bands)):
            bands = all_bands[i]
            tot_p = float(powers[i])
            timbre = bands / max(1e-4, tot_p)
            t_sec = i * dt
            detector.update(timbre, tot_p, t_sec, dt, 1.0)

        pred_bounds = detector.structural_changes_times + detector.song_changes_times
        predictions[t_name] = {
            "boundaries": sorted(pred_bounds),
            "drops": [],
        }

    return predictions


def resolve_audio_from_cache(track_name: str) -> Optional[Tuple[np.ndarray, int]]:
    """Cache and audio resolver supporting .npz and fallback audio files."""
    from tools.structural_annotator import resolve_audio_file
    return resolve_audio_file(track_name, _REPO_ROOT)


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Score Structural Predictions against Ground Truth")
    parser.add_argument("--ground-truth", type=str, default=None, help="Path to structural_annotations.json")
    parser.add_argument("--predictions", type=str, default=None, help="Path to predictions JSON file")
    parser.add_argument("--run-model", type=str, default=None, help="Run model on benchmark tracks directly")
    parser.add_argument("--tolerance", type=float, default=0.5, help="Section boundary tolerance in seconds (default: 0.5s)")
    parser.add_argument("--drop-tolerance", type=float, default=1.0, help="Climax / drop tolerance in seconds (default: 1.0s)")
    parser.add_argument("--json-out", type=str, default=None, help="Path to save output scorecard JSON")
    args = parser.parse_args()

    gt_path = args.ground_truth
    if not gt_path:
        gt_path = os.path.join(_REPO_ROOT, "research", "benchmarks", "ground_truth", "structural_annotations.json")

    if not os.path.exists(gt_path):
        print(f"Ground truth file '{gt_path}' does not exist.")
        print("Run 'python tools/structural_annotator.py' to create ground truth annotations first.")
        sys.exit(1)

    if args.run_model:
        print(f"Running live simulation for model '{args.run_model}'...")
        gt_data = load_ground_truth(gt_path)
        tracks = list(gt_data.get("tracks", {}).keys())
        predictions = run_model_predictions_simulation(args.run_model, tracks)
    elif args.predictions:
        with open(args.predictions, "r", encoding="utf-8") as f:
            predictions = json.load(f)
    else:
        # Self-evaluation (Ground truth vs itself as sanity verification)
        print("[Notice] No predictions file supplied. Running sanity self-evaluation (Ground Truth vs Ground Truth).")
        predictions = load_ground_truth(gt_path).get("tracks", {})

    results = score_structural_predictions(
        ground_truth=gt_path,
        predictions=predictions,
        tolerance=args.tolerance,
        drop_tolerance=args.drop_tolerance,
    )

    print_scorecard(results)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Scorecard JSON saved to {args.json_out}")


if __name__ == "__main__":
    main()
