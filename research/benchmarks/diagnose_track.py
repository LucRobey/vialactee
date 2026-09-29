"""
research/benchmarks/diagnose_track.py - Deep Single-Track Rhythm & DSP Diagnostic Tool.

Usage:
    # Diagnostic of a single model on a track:
    python -m research.benchmarks.diagnose_track --track "Stayin' Alive" --model AudioAnalyzer

    # Side-by-side comparison between baseline and candidate on a track:
    python -m research.benchmarks.diagnose_track --track "Nightcall" --baseline AudioAnalyzer --candidate PhaseInertiaAudioAnalyzer

    # Test parameter override on a track:
    python -m research.benchmarks.diagnose_track --track "Stayin' Alive" --model AudioAnalyzer --param high_snap_ratio=0.35

    # Focus on a specific time window:
    python -m research.benchmarks.diagnose_track --track "Stayin' Alive" --window 35,45
"""

from __future__ import annotations
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import argparse
from typing import Dict, Any, List, Optional, Tuple, Type
import numpy as np

from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioAnalyzer import AudioAnalyzer
from core.RhythmConfig import RhythmConfig
from research.benchmarks.run_benchmark import (
    discover_tracks,
    load_model_class,
    build_rhythm_config,
    load_music_catalog
)
from research.benchmarks.engine.evaluator import run_benchmark_on_track, load_audio_file
from research.benchmarks.engine.episode_slicer import extract_failure_episodes


def find_target_track(track_query: str, repo_root: str, suite: str = "all") -> Tuple[str, str, str]:
    """Finds matching track (name, audio_path, beats_path) by substring."""
    all_tracks = discover_tracks(suite=suite, repo_root=repo_root)
    matches = [t for t in all_tracks if track_query.lower() in t[0].lower()]
    if not matches:
        raise ValueError(
            f"No track matching '{track_query}' found in suite '{suite}'. "
            f"Available: {[t[0] for t in all_tracks[:10]]}..."
        )
    # Pick best match (exact or shortest match)
    matches.sort(key=lambda x: len(x[0]))
    return matches[0]


def analyze_spectral_balance_at_beats(
    audio_path: str,
    true_beats: np.ndarray,
    telemetry: List[Dict[str, Any]],
    window_sec: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Analyzes multi-band Mel energy at true downbeats vs estimated upbeats (phase ~0.5).
    Reveals whether offbeat hi-hat sizzle overpowers downbeat kick/snare fundamentals.
    """
    from research.benchmarks.engine.evaluator import MockAudioIngestion

    y, sr = load_audio_file(audio_path, target_sr=44100)
    ingestion = MockAudioIngestion(nb_of_fft_band=8, sample_rate=sr, buffer_size=1024)

    fps = 60
    chunk_samples = int(sr / fps)
    total_frames = len(y) // chunk_samples

    t_start, t_end = window_sec if window_sec else (0.0, float(len(y) / sr))

    downbeat_bands = []
    upbeat_bands = []

    # Map telemetry time to phase
    time_to_phase = {}
    for r in telemetry:
        t = r.get("time", 0.0)
        p = r.get("beat_phase", 0.0)
        time_to_phase[round(t, 2)] = p

    current_pos = 0
    rolling_buffer = np.zeros(1024, dtype=np.float32)

    for frame_idx in range(total_frames):
        incoming = y[current_pos : current_pos + chunk_samples]
        current_pos += chunk_samples
        if len(incoming) < chunk_samples:
            break

        current_time = frame_idx / fps
        if current_time < t_start or current_time > t_end:
            continue

        rolling_buffer[:-chunk_samples] = rolling_buffer[chunk_samples:]
        rolling_buffer[-chunk_samples:] = incoming
        ingestion.process_frame(rolling_buffer)

        # Check proximity to true beats (downbeat)
        dists = np.abs(true_beats - current_time)
        if len(dists) > 0 and np.min(dists) < 0.035:
            downbeat_bands.append(ingestion.fft_band_values.copy())

        # Check proximity to true upbeats (midway between true beats)
        true_upbeats = (true_beats[:-1] + true_beats[1:]) / 2.0
        up_dists = np.abs(true_upbeats - current_time)
        if len(up_dists) > 0 and np.min(up_dists) < 0.035:
            upbeat_bands.append(ingestion.fft_band_values.copy())

    mean_down = np.mean(downbeat_bands, axis=0) if downbeat_bands else np.zeros(8)
    mean_up = np.mean(upbeat_bands, axis=0) if upbeat_bands else np.zeros(8)

    # Ratios: Kick (0-1), Snare (2-3), Hi-Hat (6-7)
    kick_down = float(np.sum(mean_down[0:2]))
    kick_up = float(np.sum(mean_up[0:2]))
    snare_down = float(np.sum(mean_down[2:4]))
    snare_up = float(np.sum(mean_up[2:4]))
    hihat_down = float(np.sum(mean_down[6:8]))
    hihat_up = float(np.sum(mean_up[6:8]))

    return {
        "downbeat_bands_mean": mean_down.round(2).tolist(),
        "upbeat_bands_mean": mean_up.round(2).tolist(),
        "kick_ratio_down_vs_up": round(kick_down / (kick_up + 1e-6), 2),
        "snare_ratio_down_vs_up": round(snare_down / (snare_up + 1e-6), 2),
        "hihat_ratio_up_vs_down": round(hihat_up / (hihat_down + 1e-6), 2),
    }


def render_ascii_beat_alignment(
    true_beats: np.ndarray,
    est_beats: np.ndarray,
    t_start: float,
    t_end: float,
    width: int = 70,
    tolerance: float = 0.05
) -> str:
    """
    Renders a high-resolution ASCII timeline comparing True ground-truth beats
    against Estimated tracker beats across a specific time window.
    Legend:
        '|' = True beat or locked match
        'o' = Missed true beat (False Negative)
        '!' = Spurious extra beat (False Positive)
        '.' = Empty frame
    """
    dur = max(0.1, t_end - t_start)
    tb = true_beats[(true_beats >= t_start) & (true_beats <= t_end)]
    eb = est_beats[(est_beats >= t_start) & (est_beats <= t_end)]

    gt_line = ["."] * width
    est_line = ["."] * width
    match_line = [" "] * width

    # Place True Beats
    for t in tb:
        col = int(round((t - t_start) / dur * (width - 1)))
        if 0 <= col < width:
            gt_line[col] = "|"

    # Evaluate Estimated Beats
    matched_gt = set()
    for e in eb:
        col = int(round((e - t_start) / dur * (width - 1)))
        if not (0 <= col < width):
            continue

        # Check if matched to any true beat within tolerance
        dists = np.abs(tb - e) if len(tb) > 0 else np.array([999.0])
        min_idx = int(np.argmin(dists)) if len(dists) > 0 else -1
        if min_idx >= 0 and dists[min_idx] <= tolerance:
            est_line[col] = "|"
            match_line[col] = "="
            matched_gt.add(min_idx)
        else:
            est_line[col] = "!"
            match_line[col] = "x"

    # Mark misses on GT line
    for idx, t in enumerate(tb):
        if idx not in matched_gt:
            col = int(round((t - t_start) / dur * (width - 1)))
            if 0 <= col < width:
                gt_line[col] = "o"

    time_labels = f"[{t_start:5.1f}s" + " " * (width - 16) + f"{t_end:5.1f}s]"
    lines = [
        f"Timeline:  {time_labels}",
        f"GT Beats:  {''.join(gt_line)}",
        f"EST Beats: {''.join(est_line)}",
        f"Sync Map:  {''.join(match_line)}  (=: locked | x: offset/spurious | o: missed GT)"
    ]
    return "\n".join(lines)


def detect_phase_anomalies(telemetry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detects sudden phase jumps (>0.30) and sustained coasting regions."""
    anomalies = []
    prev_phase = None
    prev_time = 0.0

    for r in telemetry:
        t = r.get("time", 0.0)
        p = r.get("beat_phase", 0.0)

        if prev_phase is not None:
            # Expected linear progression: phase wraps 1.0 -> 0.0
            dt = t - prev_time
            expected_p = (prev_phase + dt * (r.get("bpm", 120.0) / 60.0)) % 1.0
            phase_err = (p - expected_p + 0.5) % 1.0 - 0.5

            if abs(phase_err) > 0.30:
                anomalies.append({
                    "time": round(t, 2),
                    "type": "PHASE_JUMP",
                    "delta_phase": round(float(phase_err), 3),
                    "bpm": round(r.get("bpm", 0.0), 1),
                    "confidence": round(r.get("confidence", 0.0), 3)
                })

        prev_phase = p
        prev_time = t

    return anomalies


def print_single_scorecard(name: str, sc: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Prints formatted scorecard block for a model."""
    print("=" * 75)
    print(f"📊 EVALUATION SCORECARD: {name}")
    print("=" * 75)
    print(f"  • F1@50ms (LED Sync):     {sc.get('f1_50ms', 0)*100:>6.1f}%   (Precision/Recall within 50ms)")
    print(f"  • F1@70ms (MIREX):        {sc.get('f1_70ms', 0)*100:>6.1f}%")
    print(f"  • CMLt (Correct Metric):  {sc.get('cmlt', 0)*100:>6.1f}%   (Strict tempo & phase tracking)")
    print(f"  • AMLt (Any Metric):      {sc.get('amlt', 0)*100:>6.1f}%   (Includes double/half/offbeat)")
    print(f"  • Upbeat Gap (AMLt-CMLt): {sc.get('upbeat_gap', 0):>6.2f}    (>0.10 indicates 180° upbeat trap)")
    print(f"  • Mean Phase Bias:        {sc.get('mean_phase_bias_ms', 0):>+6.1f}ms  (+ = lag, - = rush)")
    print(f"  • Phase Jitter (StdDev):  {sc.get('phase_jitter_ms', 0):>6.1f}ms  (Flywheel stability)")
    print(f"  • Avg CPU / Frame:        {sc.get('avg_frame_time_ms', 0):>6.2f}ms  (RPi 60 FPS budget: <=3.0ms)")
    print(f"  • Ground Truth Beats:     {sc.get('total_ref_beats', 0)} beats")
    print(f"  • Emitted Beats:          {sc.get('total_est_beats', 0)} beats")
    print("=" * 75)


def print_comparison_diff(base_name: str, cand_name: str, base_sc: Dict[str, Any], cand_sc: Dict[str, Any]) -> None:
    """Prints formatted side-by-side comparison table."""
    d_f1 = (cand_sc["f1_50ms"] - base_sc["f1_50ms"]) * 100.0
    d_cmlt = (cand_sc["cmlt"] - base_sc["cmlt"]) * 100.0
    d_amlt = (cand_sc["amlt"] - base_sc["amlt"]) * 100.0
    d_gap = cand_sc["upbeat_gap"] - base_sc["upbeat_gap"]
    d_bias = cand_sc["mean_phase_bias_ms"] - base_sc["mean_phase_bias_ms"]
    d_jitter = cand_sc["phase_jitter_ms"] - base_sc["phase_jitter_ms"]
    d_cpu = cand_sc["avg_frame_time_ms"] - base_sc["avg_frame_time_ms"]

    verdict = "IMPROVED" if (d_f1 > 0.5 or d_cmlt > 1.0) else ("REGRESSED" if (d_f1 < -0.5 or d_cmlt < -1.0) else "NEUTRAL")

    print("\n" + "=" * 80)
    print(f"⚖️ MODEL COMPARISON: Baseline [{base_name}] vs Candidate [{cand_name}]")
    print("=" * 80)
    print(f"{'Metric':<25} {'Baseline':<12} {'Candidate':<12} {'Delta':<15} {'Verdict'}")
    print("-" * 80)
    print(f"{'F1@50ms (Tight LED)':<25} {base_sc['f1_50ms']*100:>6.1f}%      {cand_sc['f1_50ms']*100:>6.1f}%      {d_f1:>+6.1f}%         {'✅ +' if d_f1>0 else ('❌ -' if d_f1<0 else '⚖️')}")
    print(f"{'CMLt (Correct Metric)':<25} {base_sc['cmlt']*100:>6.1f}%      {cand_sc['cmlt']*100:>6.1f}%      {d_cmlt:>+6.1f}%         {'✅ +' if d_cmlt>0 else ('❌ -' if d_cmlt<0 else '⚖️')}")
    print(f"{'AMLt (Any Metric)':<25} {base_sc['amlt']*100:>6.1f}%      {cand_sc['amlt']*100:>6.1f}%      {d_amlt:>+6.1f}%         {'✅ +' if d_amlt>0 else ('❌ -' if d_amlt<0 else '⚖️')}")
    print(f"{'Upbeat Gap (AMLt-CMLt)':<25} {base_sc['upbeat_gap']:>6.2f}        {cand_sc['upbeat_gap']:>6.2f}        {d_gap:>+6.2f}          {'✅ Lower' if d_gap<0 else ('❌ Higher' if d_gap>0 else '⚖️')}")
    print(f"{'Phase Jitter':<25} {base_sc['phase_jitter_ms']:>6.1f}ms      {cand_sc['phase_jitter_ms']:>6.1f}ms      {d_jitter:>+6.1f}ms       {'✅ Lower' if d_jitter<0 else ('❌ Higher' if d_jitter>0 else '⚖️')}")
    print(f"{'CPU Time / Frame':<25} {base_sc['avg_frame_time_ms']:>6.2f}ms      {cand_sc['avg_frame_time_ms']:>6.2f}ms      {d_cpu:>+6.2f}ms       {'RPi Budget Pass' if cand_sc['avg_frame_time_ms'] <= 3.0 else '⚠️ High Latency'}")
    print("=" * 80)
    print(f"🎯 SINGLE-TRACK VERDICT: {verdict}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vialactée Single-Track Deep Rhythm Diagnostic Tool")
    parser.add_argument("--track", type=str, required=True, help="Track name substring (e.g. 'Nightcall', 'Stayin')")
    parser.add_argument("--model", type=str, default="AudioAnalyzer", help="Model to diagnose (default: AudioAnalyzer)")
    parser.add_argument("--baseline", type=str, default="", help="Baseline model for side-by-side comparison")
    parser.add_argument("--candidate", type=str, default="", help="Candidate model for side-by-side comparison")
    parser.add_argument("--suite", type=str, default="all", help="Suite search space (default: all)")
    parser.add_argument("--window", type=str, default="", help="Focus window in seconds: start,end (e.g. 35,50)")
    parser.add_argument("--param", action="append", help="Inline RhythmConfig overrides: key=value")
    parser.add_argument("--json", action="store_true", help="Output full JSON report")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Parse focus window if specified
    focus_window = None
    if args.window:
        parts = [float(x.strip()) for x in args.window.split(",")]
        if len(parts) == 2:
            focus_window = (parts[0], parts[1])

    # Find track
    track_name, audio_path, beats_path = find_target_track(args.track, repo_root, suite=args.suite)
    catalog = load_music_catalog(repo_root)
    track_meta = catalog.get(track_name, {})

    print(f"\n🎵 TARGET TRACK: {track_name}")
    print(f"   • Genre: {track_meta.get('genre', 'Unknown')} | Meter: {track_meta.get('meter', 'Unknown')} | Character: {track_meta.get('tempo_character', 'Unknown')}")
    print(f"   • Audio: {audio_path}")
    print(f"   • Beats: {beats_path}")
    if focus_window:
        print(f"   • Focused Time Window: {focus_window[0]:.1f}s - {focus_window[1]:.1f}s")
    print()

    # Determine mode: Single Model vs Comparison
    is_comparison = bool(args.baseline and args.candidate)

    if is_comparison:
        base_cls = load_model_class(args.baseline, repo_root)
        cand_cls = load_model_class(args.candidate, repo_root)
        cfg = build_rhythm_config(param_overrides=args.param)

        print(f"⚡ Simulating Baseline [{args.baseline}]...")
        base_res = run_benchmark_on_track(base_cls, audio_path, beats_path, config=cfg)

        print(f"⚡ Simulating Candidate [{args.candidate}]...")
        cand_res = run_benchmark_on_track(cand_cls, audio_path, beats_path, config=cfg)

        print_comparison_diff(args.baseline, args.candidate, base_res["scorecard"], cand_res["scorecard"])

        # Compare failure episodes
        base_eps = extract_failure_episodes(track_name, base_res["true_beats"], base_res["est_beats"], base_res["telemetry"], base_res["scorecard"])
        cand_eps = extract_failure_episodes(track_name, cand_res["true_beats"], cand_res["est_beats"], cand_res["telemetry"], cand_res["scorecard"])

        print("🔍 FAILURE EPISODE DELTAS:")
        print(f"   • Baseline Active Episodes:  {len(base_eps)}")
        print(f"   • Candidate Active Episodes: {len(cand_eps)}")
        if cand_eps:
            print("\n   Candidate Failure Moments:")
            for ep in cand_eps:
                w = ep.get("time_window", [0.0, 0.0])
                print(f"     [{w[0]:5.1f}s - {w[1]:5.1f}s] {ep.get('failure_type'):<24} (Dur: {ep.get('event_duration_sec',0):.1f}s, Beats: {ep.get('inverted_beats_count',0)})")

        target_res = cand_res
    else:
        model_name = args.model
        model_cls = load_model_class(model_name, repo_root)
        cfg = build_rhythm_config(param_overrides=args.param)

        print(f"⚡ Simulating [{model_name}] on {track_name}...")
        target_res = run_benchmark_on_track(model_cls, audio_path, beats_path, config=cfg)
        print_single_scorecard(model_name, target_res["scorecard"], track_meta)

        # Failure episodes
        episodes = extract_failure_episodes(
            track_name, target_res["true_beats"], target_res["est_beats"], target_res["telemetry"], target_res["scorecard"]
        )
        print(f"🔍 FAILURE EPISODES DETECTED: {len(episodes)}")
        if episodes:
            for ep in episodes:
                w = ep.get("time_window", [0.0, 0.0])
                print(f"   [{w[0]:5.1f}s - {w[1]:5.1f}s] {ep.get('failure_type'):<24} (Dur: {ep.get('event_duration_sec',0):.1f}s, Beats: {ep.get('inverted_beats_count',0)})")
                if ep.get("diagnostic_notes"):
                    print(f"          Notes: {ep.get('diagnostic_notes')}")
        else:
            print("   ✅ No severe failure episodes sliced on this track.")

    # Visual ASCII beat-grid alignment
    vis_window = focus_window
    if not vis_window:
        if is_comparison and cand_eps:
            w0 = cand_eps[0].get("time_window", [10.0, 18.0])
            vis_window = (w0[0], min(w0[0] + 8.0, max(w0[0] + 4.0, w0[1])))
        elif not is_comparison and episodes:
            w0 = episodes[0].get("time_window", [10.0, 18.0])
            vis_window = (w0[0], min(w0[0] + 8.0, max(w0[0] + 4.0, w0[1])))
        else:
            vis_window = (10.0, 18.0)

    print("\n📊 VISUAL BEAT-GRID ALIGNMENT:")
    print(f"   Window: {vis_window[0]:.1f}s - {vis_window[1]:.1f}s (Tolerance: 50ms)")
    if is_comparison:
        print(f"\n--- Baseline [{args.baseline}] ---")
        print(render_ascii_beat_alignment(base_res["true_beats"], base_res["est_beats"], vis_window[0], vis_window[1]))
        print(f"\n--- Candidate [{args.candidate}] ---")
        print(render_ascii_beat_alignment(cand_res["true_beats"], cand_res["est_beats"], vis_window[0], vis_window[1]))
    else:
        print(render_ascii_beat_alignment(target_res["true_beats"], target_res["est_beats"], vis_window[0], vis_window[1]))

    # Spectral and phase anomaly analysis
    print("\n🥁 SPECTRAL & UPBEAT/DOWNBEAT ENERGY DISTRIBUTION:")
    spectral_diag = analyze_spectral_balance_at_beats(
        audio_path, target_res["true_beats"], target_res["telemetry"], window_sec=focus_window
    )
    print(f"   • Downbeat Energy Profile (Bands 0-7): {spectral_diag['downbeat_bands_mean']}")
    print(f"   • Upbeat Energy Profile (Bands 0-7):   {spectral_diag['upbeat_bands_mean']}")
    print(f"   • Kick Downbeat/Upbeat Ratio:          {spectral_diag['kick_ratio_down_vs_up']}x (Values > 1.0 indicate strong kick on downbeat)")
    print(f"   • Snare Downbeat/Upbeat Ratio:         {spectral_diag['snare_ratio_down_vs_up']}x")
    print(f"   • Hi-Hat Upbeat/Downbeat Ratio:        {spectral_diag['hihat_ratio_up_vs_down']}x (Values > 1.0 indicate offbeat hi-hat sizzle dominance)")

    anomalies = detect_phase_anomalies(target_res["telemetry"])
    print(f"\n🔄 DETECTED FLYWHEEL PHASE JUMPS (|Δϕ| > 0.30): {len(anomalies)}")
    for a in anomalies[:5]:
        print(f"   [t={a['time']:5.1f}s] Δϕ={a['delta_phase']:+.3f} at {a['bpm']} BPM (Confidence: {a['confidence']})")
    if len(anomalies) > 5:
        print(f"   ... and {len(anomalies)-5} more phase jumps.")

    if args.json:
        report = {
            "track": track_name,
            "metadata": track_meta,
            "scorecard": target_res["scorecard"],
            "spectral": spectral_diag,
            "anomalies": anomalies
        }
        print("\n" + json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
