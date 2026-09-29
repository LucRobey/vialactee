"""
research/benchmarks/plot_beat_salience.py - Rhythmic Salience & Beat Importance Visualizer.

Generates multi-tier visual inspection dashboards plotting:
1. Audio Waveform with Ground Truth Beats color-coded by importance.
2. The Continuous Beat Importance Curve S(t) in [0.0, 1.0] with shaded priority zones:
   - High Rhythmic Priority (Groove / Drum Kit / Drop -> Crucial for Chandelier!)
   - Transitional / Mid-Salience (Light Percussion / Building Energy)
   - Free Tempo / Melodic Solo / Ambient (Guitar Solo / Pad / Breakdown -> Beat is NOT Important!)
3. Acoustic Evidence Breakdown: Percussive Kick/Snare Transient Energy vs Melodic/Harmonic Sustain.
4. (Optional) Real-Time Model bpm_trust / confidence_score comparison.
"""

from __future__ import annotations
import os
import sys

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add repo root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import argparse
import numpy as np
import librosa
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
from typing import List, Dict, Any, Optional, Tuple

from research.benchmarks.engine.evaluator import load_audio_file, load_beats_file, run_benchmark_on_track
from research.benchmarks.run_benchmark import load_model_class


def compute_beat_importance(
    audio_path: str,
    target_sr: int = 22050,
    hop_length: int = 512
) -> Dict[str, Any]:
    """
    Computes an objective, continuous Rhythmic Salience (Beat Importance) curve S(t) in [0.0, 1.0].
    
    Acoustic components:
    1. Low-end kick fundamental & snap transient flux (30 - 350 Hz).
    2. Snare body & crack transient flux (200 - 2500 Hz).
    3. Harmonic-percussive ratio (contrast against continuous guitar/synth/vocal sustain).
    4. Rolling crest factor (peak-to-mean transient sharpness).
    """
    y, sr = load_audio_file(audio_path, target_sr=target_sr)
    duration = len(y) / sr
    fps = sr / hop_length

    # 1. Short-Time Fourier Transform & Harmonic-Percussive Separation
    D = librosa.stft(y, n_fft=1024, hop_length=hop_length)
    D_harmonic, D_percussive = librosa.decompose.hpss(D, margin=2.0)

    # Compute energy envelopes
    power_perc = np.sum(np.abs(D_percussive)**2, axis=0)
    power_harm = np.sum(np.abs(D_harmonic)**2, axis=0) + 1e-6
    total_power = power_perc + power_harm
    perc_ratio = power_perc / (total_power + 1e-6)

    # 2. 32-Band Mel Filterbank on Percussive Component
    mel_basis = librosa.filters.mel(sr=sr, n_fft=1024, n_mels=32, fmin=20.0, fmax=8000.0)
    p_mel = np.dot(mel_basis, np.abs(D_percussive))
    h_mel = np.dot(mel_basis, np.abs(D_harmonic))

    # Per-band positive onset derivative: dE = max(0, E[t] - E[t-1])
    diff_p = np.diff(p_mel, axis=1)
    diff_p = np.maximum(0.0, diff_p)
    diff_p = np.pad(diff_p, ((0, 0), (1, 0)), mode='constant')

    # Band weighting:
    # Bands 0-2 (20 - 250 Hz): Kick drum fundamental
    # Bands 3-6 (250 - 900 Hz): Snare drum body
    # Bands 7-12 (900 - 2500 Hz): Snare crack & rimshot
    kick_weights = np.zeros(32)
    kick_weights[0:3] = 3.0
    kick_weights[3:7] = 2.0
    kick_weights[7:13] = 1.0

    percussive_transient_flux = np.dot(kick_weights, diff_p)

    # Guitar / Melodic harmonic sustain envelope (mid bands 4-16)
    harmonic_sustain = np.mean(h_mel[4:16], axis=0)

    # 3. Rolling Crest Factor (Peak-to-Average Ratio over 1.5s window)
    window_frames = max(1, int(1.5 * fps))
    smooth_flux = uniform_filter1d(percussive_transient_flux, size=max(1, int(0.12 * fps)))
    rolling_mean_flux = uniform_filter1d(smooth_flux, size=window_frames * 2) + 1e-6
    crest_factor = (smooth_flux - rolling_mean_flux) / (rolling_mean_flux + 1e-4)
    crest_factor = np.clip(crest_factor, 0.0, 6.0) / 6.0

    # 4. Normalized Transient Squelch Ratio
    # High when percussive attacks dwarf harmonic sustain; low when sustained guitar dominates
    relative_transient = percussive_transient_flux / (percussive_transient_flux + harmonic_sustain * 0.40 + 1e-6)

    # 5. Composite Raw Salience
    raw_salience = (
        0.40 * perc_ratio
        + 0.35 * relative_transient
        + 0.25 * crest_factor
    )
    raw_salience = np.clip(raw_salience, 0.0, 1.0)

    # 6. Smooth across musical phrase boundary (0.8s Gaussian filter)
    salience_smoothed = gaussian_filter1d(raw_salience, sigma=max(1, int(0.8 * fps)))

    # Adaptive contrast stretching to span [0.0, 1.0]
    p5 = np.percentile(salience_smoothed, 5)
    p95 = np.percentile(salience_smoothed, 95)
    if p95 > p5 + 1e-4:
        salience_norm = np.clip((salience_smoothed - p5) / (p95 - p5), 0.0, 1.0)
    else:
        salience_norm = salience_smoothed

    # Apply soft sigmoid expansion to sharpen the transition into the drop
    salience_curve = 1.0 / (1.0 + np.exp(-8.0 * (salience_norm - 0.38)))

    timeline = np.arange(len(salience_curve)) * hop_length / sr

    return {
        "times": timeline,
        "salience": salience_curve,
        "percussive_transients": smooth_flux,
        "harmonic_sustain": harmonic_sustain,
        "perc_ratio": perc_ratio,
        "duration": duration,
        "sr": sr,
        "fps": fps
    }


def plot_salience_dashboard(
    audio_path: str,
    beats_path: Optional[str] = None,
    output_png: Optional[str] = None,
    time_window: Optional[Tuple[float, float]] = None,
    model_name: Optional[str] = None
) -> str:
    """
    Renders an inspection dashboard displaying the Beat Importance Curve,
    audio waveform, ground truth beats, and acoustic decomposition.
    """
    track_name = os.path.splitext(os.path.basename(audio_path))[0]
    print(f"📈 Computing Beat Importance curve for: {track_name}...")

    data = compute_beat_importance(audio_path)
    times = data["times"]
    salience = data["salience"]
    duration = data["duration"]
    p_trans = data["percussive_transients"]
    h_sust = data["harmonic_sustain"]

    # Load audio waveform for top display
    y_full, sr_full = load_audio_file(audio_path, target_sr=22050)

    # Load ground truth beats if available
    true_beats = np.array([])
    if beats_path and os.path.exists(beats_path):
        true_beats = load_beats_file(beats_path)

    # Determine time window
    t_min = 0.0 if time_window is None else max(0.0, time_window[0])
    t_max = duration if time_window is None else min(duration, time_window[1])

    # Run model simulation if requested
    model_times = np.array([])
    model_conf = np.array([])
    model_est_beats = np.array([])
    if model_name:
        try:
            m_class = load_model_class(model_name, repo_root)
            sim_res = run_benchmark_on_track(m_class, audio_path, beats_path if beats_path else "")
            telem = sim_res["telemetry"]
            model_times = np.array([r.get("time", 0.0) for r in telem])
            model_conf = np.array([r.get("confidence", 0.0) for r in telem])
            model_est_beats = sim_res["est_beats"]
        except Exception as e:
            print(f"⚠️  Could not run model comparison for {model_name}: {e}")

    # Slice data to window
    mask_s = (times >= t_min) & (times <= t_max)
    w_t = times[mask_s]
    w_salience = salience[mask_s]
    w_ptrans = p_trans[mask_s]
    w_hsust = h_sust[mask_s]

    idx_start = int(t_min * sr_full)
    idx_end = int(t_max * sr_full)
    w_audio = y_full[idx_start:idx_end]
    w_audio_t = np.linspace(t_min, t_max, len(w_audio))

    w_beats = true_beats[(true_beats >= t_min) & (true_beats <= t_max)] if len(true_beats) > 0 else np.array([])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        num_plots, 1,
        figsize=(15, 3.2 * num_plots),
        sharex=True,
        gridspec_kw={'height_ratios': [1.8, 2.2, 1.5, 1.5][:num_plots]}
    )
    fig.patch.set_facecolor('#0f111a')

    for ax in axes:
        ax.set_facecolor('#1a1c29')
        ax.tick_params(colors='#8b9bb4', labelsize=9)
        ax.spines['bottom'].set_color('#2e344e')
        ax.spines['top'].set_color('#2e344e')
        ax.spines['left'].set_color('#2e344e')
        ax.spines['right'].set_color('#2e344e')
        ax.xaxis.label.set_color('#8b9bb4')
        ax.yaxis.label.set_color('#8b9bb4')
        ax.title.set_color('#e2e8f0')

    # --- Subplot 1: Audio Waveform & Beats Color-Coded by Salience ---
    ax0 = axes[0]
    ax0.plot(w_audio_t, w_audio, color='#475569', alpha=0.5, linewidth=0.7, label='Audio Waveform')

    # Draw beats with color corresponding to salience at that beat
    if len(w_beats) > 0:
        beat_saliences = np.interp(w_beats, times, salience)
        for b_t, b_s in zip(w_beats, beat_saliences):
            if b_s >= 0.60:
                col = '#10b981' # Bright emerald (high importance)
                alpha = 0.95
                lw = 2.0
            elif b_s >= 0.25:
                col = '#f59e0b' # Amber (transitional)
                alpha = 0.65
                lw = 1.3
            else:
                col = '#64748b' # Slate grey (unimportant)
                alpha = 0.35
                lw = 0.9
            ax0.axvline(b_t, color=col, linewidth=lw, alpha=alpha)

        # Legend proxy stems
        ax0.plot([], [], color='#10b981', linewidth=2.0, label='Essential Beat (S ≥ 0.60)')
        ax0.plot([], [], color='#f59e0b', linewidth=1.3, label='Transitional Beat (0.25 ≤ S < 0.60)')
        ax0.plot([], [], color='#64748b', linewidth=0.9, label='Free/Solo Beat (S < 0.25)')

    ax0.set_title(f"Beat Importance Ground Truth: {track_name}", fontsize=13, fontweight='bold', pad=10)
    ax0.set_ylabel("Amplitude", fontsize=9)
    ax0.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # --- Subplot 2: The Continuous Beat Importance Curve S(t) with Zones ---
    ax1 = axes[1]
    # Priority Zones Shading
    ax1.axhspan(0.60, 1.00, color='#10b981', alpha=0.12, label='High Rhythmic Priority (Groove / Drum Kit / Drop)')
    ax1.axhspan(0.25, 0.60, color='#f59e0b', alpha=0.08, label='Transitional Zone (Light Percussion / Build)')
    ax1.axhspan(0.00, 0.25, color='#ef4444', alpha=0.08, label='Free Tempo / Melodic Solo (Beat NOT Crucial)')

    # Shaded area under curve
    ax1.fill_between(w_t, 0, w_salience, color='#06b6d4', alpha=0.25)
    # The curve itself
    ax1.plot(w_t, w_salience, color='#22d3ee', linewidth=2.4, label='Rhythmic Salience Curve S(t)')

    # Threshold horizontal reference lines
    ax1.axhline(0.60, color='#10b981', linestyle='--', linewidth=1.0, alpha=0.6)
    ax1.axhline(0.25, color='#f59e0b', linestyle='--', linewidth=1.0, alpha=0.6)

    ax1.set_ylim(-0.02, 1.05)
    ax1.set_ylabel("Beat Importance S(t)", fontsize=10, fontweight='bold', color='#22d3ee')
    ax1.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # Annotate key stats
    mean_s = np.mean(w_salience)
    pct_high = np.mean(w_salience >= 0.60) * 100.0
    pct_low = np.mean(w_salience < 0.25) * 100.0
    stats_text = f"Window Mean S: {mean_s:.2f} | High Rhythm: {pct_high:.0f}% of time | Solo/Ambient: {pct_low:.0f}% of time"
    ax1.text(0.015, 0.06, stats_text, transform=ax1.transAxes, color='#94a3b8', fontsize=8.5,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f111a", edgecolor="#334155", alpha=0.85))

    # --- Subplot 3: Physical Signal Drivers (Acoustic Evidence) ---
    ax2 = axes[2]
    norm_p = w_ptrans / (np.percentile(p_trans, 95) + 1e-6)
    norm_h = w_hsust / (np.percentile(h_sust, 95) + 1e-6)

    ax2.plot(w_t, norm_p, color='#f43f5e', linewidth=1.4, alpha=0.9, label='Percussive Transient Flux (Kicks & Snares)')
    ax2.plot(w_t, norm_h, color='#38bdf8', linewidth=1.2, alpha=0.7, linestyle='-.', label='Harmonic Sustain (Guitar / Vocal Body)')
    ax2.set_ylabel("Relative Energy", fontsize=9)
    ax2.set_title("Acoustic Decomposition (Evidence Drivers)", fontsize=10, fontweight='semibold', pad=6)
    ax2.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)

    # --- Subplot 4: Model Comparison (If Model Specified) ---
    if num_plots == 4:
        ax3 = axes[3]
        mask_m = (model_times >= t_min) & (model_times <= t_max)
        wm_t = model_times[mask_m]
        wm_c = model_conf[mask_m]

        ax3.plot(w_t, w_salience, color='#22d3ee', linewidth=1.6, alpha=0.7, linestyle=':', label='Ground Truth Beat Importance S(t)')
        ax3.plot(wm_t, wm_c, color='#ec4899', linewidth=2.0, label=f'{model_name} Live bpm_trust / confidence')

        # Model predicted beats
        w_mbeats = model_est_beats[(model_est_beats >= t_min) & (model_est_beats <= t_max)]
        for mb in w_mbeats:
            ax3.axvline(mb, color='#ec4899', linestyle='--', alpha=0.3, linewidth=0.8)

        ax3.set_ylim(-0.02, 1.05)
        ax3.set_ylabel("Model Trust vs Salience", fontsize=9, fontweight='bold', color='#ec4899')
        ax3.legend(loc='upper right', facecolor='#1a1c29', edgecolor='#2e344e', labelcolor='#e2e8f0', fontsize=8)
        ax3.set_xlabel("Time (seconds)", fontsize=10)
    else:
        axes[-1].set_xlabel("Time (seconds)", fontsize=10)

    plt.tight_layout()

    if not output_png:
        out_dir = os.path.join(repo_root, "research", "experiments", "salience_plots")
        os.makedirs(out_dir, exist_ok=True)
        safe_name = track_name.replace(" ", "_").replace("'", "").replace('"', '')
        output_png = os.path.join(out_dir, f"salience_{safe_name}.png")

    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    plt.savefig(output_png, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

    print(f"✅ Beat Importance dashboard successfully generated and saved to:\n   {output_png}")
    return output_png


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot Beat Importance & Rhythmic Salience Curves.")
    parser.add_argument("--track", type=str, default="Sweet Child O' Mine", help="Track name or search substring")
    parser.add_argument("--tmin", type=float, default=None, help="Start time (seconds)")
    parser.add_argument("--tmax", type=float, default=None, help="End time (seconds)")
    parser.add_argument("--out", type=str, default=None, help="Custom output PNG path")
    parser.add_argument("--model", type=str, default=None, help="Optional model name to compare live bpm_trust (e.g. CostasLoopAudioAnalyzer)")
    args = parser.parse_args()

    mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
    neural_dir = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "neural")

    # Locate audio and beats
    audio_path = None
    beats_path = None

    if os.path.exists(mp3_dir):
        for f in os.listdir(mp3_dir):
            if f.endswith((".mp3", ".wav")) and args.track.lower() in f.lower():
                audio_path = os.path.join(mp3_dir, f)
                base = os.path.splitext(f)[0]
                cand_beats = os.path.join(neural_dir, f"{base}.beats.txt")
                if os.path.exists(cand_beats):
                    beats_path = cand_beats
                break

    if not audio_path:
        # Check neural directory
        if os.path.exists(neural_dir):
            for f in os.listdir(neural_dir):
                if f.endswith(".beats.txt") and args.track.lower() in f.lower():
                    beats_path = os.path.join(neural_dir, f)
                    base = f.replace(".beats.txt", "")
                    for ext in (".mp3", ".wav"):
                        cand_audio = os.path.join(mp3_dir, f"{base}{ext}")
                        if os.path.exists(cand_audio):
                            audio_path = cand_audio
                            break
                    break

    if not audio_path or not os.path.exists(audio_path):
        print(f"❌ Error: Track '{args.track}' not found in {mp3_dir}")
        sys.exit(1)

    t_win = (args.tmin, args.tmax) if (args.tmin is not None or args.tmax is not None) else None
    plot_salience_dashboard(
        audio_path=audio_path,
        beats_path=beats_path,
        output_png=args.out,
        time_window=t_win,
        model_name=args.model
    )
