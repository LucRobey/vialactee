"""
benchmarks/plot_diagnostics.py - High-Resolution Visual Inspection & Diagnostic Tool.

Renders 4-tier diagnostic graphs:
1. Audio Waveform with Ground Truth (green) vs Predicted Beats (magenta)
2. Spectral Flux / Energy Dynamics
3. Continuous Flywheel Phase Sawtooth ϕ(t)
4. Estimated BPM over time with Failure Episode Highlight Zones
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
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional, Tuple

from core.AudioAnalyzer import AudioAnalyzer
from benchmarks.engine.evaluator import run_benchmark_on_track, load_audio_file, load_beats_file
from benchmarks.engine.episode_slicer import extract_failure_episodes


def plot_track_diagnostics(
    audio_path: str,
    beats_path: str,
    output_png: str,
    time_window: Optional[Tuple[float, float]] = None,
    analyzer_class=AudioAnalyzer
) -> str:
    """
    Runs the analyzer on the track, captures telemetry, and generates
    a multi-panel diagnostic figure highlighting beat alignment and failure episodes.
    """
    track_name = os.path.splitext(os.path.basename(audio_path))[0]
    print(f"📊 Generating visual diagnostics for: {track_name}...")

    res = run_benchmark_on_track(analyzer_class, audio_path, beats_path)
    scorecard = res["scorecard"]
    true_beats = res["true_beats"]
    est_beats = res["est_beats"]
    telemetry = res["telemetry"]

    episodes = extract_failure_episodes(track_name, true_beats, est_beats, telemetry, scorecard)

    # Telemetry arrays
    times = np.array([r.get("time", 0.0) for r in telemetry])
    phases = np.array([r.get("beat_phase", 0.0) for r in telemetry])
    bpms = np.array([r.get("bpm", 120.0) for r in telemetry])
    fluxes = np.array([r.get("custom_flux", 0.0) for r in telemetry])
    confidences = np.array([r.get("confidence", 0.0) for r in telemetry])

    # Load audio snippet
    y, sr = load_audio_file(audio_path, target_sr=44100)
    audio_duration = len(y) / sr

    # Determine display window
    if time_window is not None:
        t_min, t_max = time_window
    elif len(episodes) > 0:
        # Focus on the first failure episode + 3s margin
        ep_w = episodes[0].get("time_window", [0.0, 15.0])
        t_min = max(0.0, ep_w[0] - 2.0)
        t_max = min(audio_duration, ep_w[1] + 3.0)
    else:
        # Default first 15 seconds
        t_min = 0.0
        t_max = min(audio_duration, 15.0)

    # Slice data to window
    mask_telem = (times >= t_min) & (times <= t_max)
    w_times = times[mask_telem]
    w_phases = phases[mask_telem]
    w_bpms = bpms[mask_telem]
    w_fluxes = fluxes[mask_telem]
    w_conf = confidences[mask_telem]

    w_true = true_beats[(true_beats >= t_min) & (true_beats <= t_max)]
    w_est = est_beats[(est_beats >= t_min) & (est_beats <= t_max)]

    s_start = int(t_min * sr)
    s_end = int(t_max * sr)
    w_audio = y[s_start:s_end]
    w_audio_t = np.linspace(t_min, t_max, len(w_audio))

    # --- Plot Setup ---
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1.2, 1.2, 1]})
    fig.patch.set_facecolor('#0f111a')

    for ax in axes:
        ax.set_facecolor('#1a1c29')
        ax.tick_params(colors='#8b9bb4')
        ax.spines['bottom'].set_color('#2e344e')
        ax.spines['top'].set_color('#2e344e')
        ax.spines['left'].set_color('#2e344e')
        ax.spines['right'].set_color('#2e344e')
        ax.xaxis.label.set_color('#8b9bb4')
        ax.yaxis.label.set_color('#8b9bb4')
        ax.title.set_color('#e2e8f0')

    # Subplot 1: Waveform & Beat Ticks
    ax0 = axes[0]
    ax0.plot(w_audio_t, w_audio, color='#4a5568', alpha=0.6, linewidth=0.8, label='Audio Waveform')
    
    # Ground truth: green vertical stems
    for tb in w_true:
        ax0.axvline(tb, color='#10b981', linestyle='-', linewidth=2.0, alpha=0.9, label='True Beat' if tb == w_true[0] else "")
    # Estimated beats: magenta dashed stems
    for eb in w_est:
        ax0.axvline(eb, color='#ec4899', linestyle='--', linewidth=2.0, alpha=0.9, label='Model Beat' if eb == w_est[0] else "")

    ax0.set_title(f"Diagnostic Inspection: {track_name} | F1@50ms: {scorecard['f1_50ms']*100:.1f}% | CMLt: {scorecard['cmlt']*100:.1f}% | Jitter: {scorecard['phase_jitter_ms']:.1f}ms", fontsize=12, fontweight='bold', pad=10)
    ax0.set_ylabel("Amplitude", fontsize=9)
    ax0.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # Subplot 2: Onset Spectral Flux
    ax1 = axes[1]
    ax1.plot(w_times, w_fluxes, color='#f59e0b', linewidth=1.5, label='Spectral Flux (ODF)')
    ax1.set_ylabel("ODF Flux", fontsize=9)
    ax1.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # Subplot 3: Flywheel Speaker Phase Sawtooth ϕ(t)
    ax2 = axes[2]
    ax2.plot(w_times, w_phases, color='#38bdf8', linewidth=1.5, label='Flywheel Phase ϕ(t)')
    ax2.axhline(0.0, color='#64748b', linestyle=':', alpha=0.5)
    ax2.axhline(1.0, color='#64748b', linestyle=':', alpha=0.5)
    for eb in w_est:
        ax2.axvline(eb, color='#ec4899', linestyle='--', alpha=0.4, linewidth=1.0)
    ax2.set_ylabel("Phase [0, 1)", fontsize=9)
    ax2.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # Subplot 4: BPM & Confidence
    ax3 = axes[3]
    ax3.plot(w_times, w_bpms, color='#a855f7', linewidth=1.5, label='Estimated BPM')
    ax3.set_ylabel("BPM", fontsize=9)
    ax3.set_xlabel("Time (seconds)", fontsize=10)

    # Overlay Failure Episode Zones across all subplots
    colors = {
        "PHASE_INVERSION_UPBEAT": ("#ef4444", 0.25, "Upbeat Inversion Zone"),
        "GHOST_BEAT_BURST": ("#6b7280", 0.30, "Ghost Beat Breakdown Zone"),
        "HIGH_PHASE_JITTER": ("#eab308", 0.20, "High Phase Jitter Zone")
    }
    for ep in episodes:
        ftype = ep.get("failure_type", "")
        ew = ep.get("time_window", [0.0, 0.0])
        color, alpha, lbl = colors.get(ftype, ("#ef4444", 0.2, "Failure Zone"))
        if ew[1] >= t_min and ew[0] <= t_max:
            for ax in axes:
                ax.axvspan(max(t_min, ew[0]), min(t_max, ew[1]), color=color, alpha=alpha, label=lbl if ax == axes[0] else "")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    plt.savefig(output_png, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

    print(f"✅ Diagnostic plot saved to: {output_png}")
    return output_png


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate visual diagnostic plots for beat tracking.")
    parser.add_argument("--track", type=str, default="synthetic_step_tempo", help="Track name or prefix")
    parser.add_argument("--tmin", type=float, default=None, help="Start time in seconds")
    parser.add_argument("--tmax", type=float, default=None, help="End time in seconds")
    parser.add_argument("--out", type=str, default=None, help="Output PNG path")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Locate track in synthetic or natural
    cand_dirs = [
        os.path.join(repo_root, "benchmarks", "ground_truth", "synthetic_cache"),
        os.path.join(repo_root, "benchmarks", "ground_truth", "natural")
    ]
    
    audio_path = None
    beats_path = None

    for d in cand_dirs:
        for f in os.listdir(d):
            if f.startswith(args.track) and f.endswith((".wav", ".mp3", ".m4a")):
                audio_path = os.path.join(d, f)
                b_name = f.replace(".wav", ".beats.txt").replace(".mp3", ".beats.txt").replace(".m4a", ".beats.txt")
                beats_path = os.path.join(d, b_name)
                break
        if audio_path and os.path.exists(beats_path):
            break

    if not audio_path or not beats_path or not os.path.exists(beats_path):
        # Look in assets/musics/mp3_files
        mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
        natural_dir = os.path.join(repo_root, "benchmarks", "ground_truth", "natural")
        for f in os.listdir(natural_dir):
            if f.startswith(args.track) and f.endswith(".beats.txt"):
                beats_path = os.path.join(natural_dir, f)
                base = f.replace(".beats.txt", "")
                cand1 = os.path.join(mp3_dir, f"{base}.mp3")
                cand2 = os.path.join(mp3_dir, f"{base}.m4a")
                audio_path = cand1 if os.path.exists(cand1) else cand2
                break

    if not audio_path or not beats_path or not os.path.exists(beats_path):
        print(f"Could not find track '{args.track}'")
        sys.exit(1)

    t_win = (args.tmin, args.tmax) if (args.tmin is not None and args.tmax is not None) else None
    out_file = args.out or os.path.join(repo_root, "experiments", "plots", f"{args.track}_diagnostic.png")
    plot_track_diagnostics(audio_path, beats_path, out_file, time_window=t_win)
