"""
benchmarks/ground_truth/synthetic/generator.py - Generates 8 exact synthetic stress tracks & ground truth.

Covers:
1. synthetic_click_120bpm: Standard 120.0 BPM 4/4 metronome kick.
2. synthetic_click_85bpm: Slow 85.0 BPM ballad/hip-hop tempo.
3. synthetic_click_140bpm: Fast 140.0 BPM techno/EDM tempo.
4. synthetic_step_tempo: Instant jump 120 BPM -> 140 BPM (measures re-lock latency).
5. synthetic_breakdown_dropout: 16 bars drums -> 8 bars silent breakdown -> drums return (measures coasting).
6. synthetic_tempo_drift_accel: Gradual ramp 100 -> 130 BPM over 30s (measures drummer drift tracking).
7. synthetic_syncopated_reggae: Kicks on downbeats, loud hats on upbeats (tests upbeat inversion resistance).
8. synthetic_polyrhythm_3_against_2: 3-against-2 cross-rhythms (tests sub-harmonic trap immunity).
"""

from __future__ import annotations
import os
import wave
import numpy as np
from typing import List, Tuple


def _synthesize_kick(sr: int = 44100, duration: float = 0.08) -> np.ndarray:
    """Synthesizes an acoustic/electronic kick drum transient (decaying pitch sine)."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freq_env = 150.0 * np.exp(-t * 50.0) + 45.0
    phase = 2.0 * np.pi * np.cumsum(freq_env) / sr
    amp_env = np.exp(-t * 35.0)
    kick = np.sin(phase) * amp_env
    click_len = min(len(kick), int(sr * 0.005))
    kick[:click_len] += np.random.uniform(-0.3, 0.3, click_len) * np.linspace(1, 0, click_len)
    return np.clip(kick, -1.0, 1.0)


def _synthesize_snare(sr: int = 44100, duration: float = 0.12) -> np.ndarray:
    """Synthesizes a mid-range snare drum transient with noise body."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = np.sin(2.0 * np.pi * 180.0 * t) * np.exp(-t * 30.0)
    noise = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 20.0)
    snare = 0.4 * tone + 0.6 * noise
    return np.clip(snare, -1.0, 1.0)


def _synthesize_hihat(sr: int = 44100, duration: float = 0.04) -> np.ndarray:
    """Synthesizes a high-frequency percussive hi-hat transient."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    amp_env = np.exp(-t * 80.0)
    return noise * amp_env * 0.3


def _save_wav_and_beats(
    audio: np.ndarray,
    beat_timestamps: List[float],
    wav_path: str,
    beats_path: str,
    sr: int = 44100
) -> None:
    """Saves a 16-bit mono WAV file and an immutable .beats.txt timestamp file."""
    os.makedirs(os.path.dirname(wav_path), exist_ok=True)
    os.makedirs(os.path.dirname(beats_path), exist_ok=True)

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        norm_audio = (audio / max_val) * 0.95
    else:
        norm_audio = audio
    int_samples = (norm_audio * 32767.0).astype(np.int16)

    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())

    with open(beats_path, "w", encoding="utf-8") as bf:
        for b in beat_timestamps:
            bf.write(f"{b:.4f}\n")


def generate_click_track(bpm: float, output_dir: str, duration: float = 30.0, sr: int = 44100) -> Tuple[str, str]:
    """Generates a steady metronome track at a fixed BPM."""
    total_samples = int(sr * duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)

    interval = 60.0 / bpm
    beat_times = []
    current_time = 0.5

    while current_time < duration - 0.5:
        idx = int(current_time * sr)
        end_idx = min(total_samples, idx + len(kick))
        audio[idx:end_idx] += kick[: end_idx - idx]
        beat_times.append(current_time)
        current_time += interval

    name = f"synthetic_click_{int(bpm)}bpm"
    wav_path = os.path.join(output_dir, f"{name}.wav")
    beats_path = os.path.join(output_dir, f"{name}.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_click_120bpm(output_dir: str, duration: float = 30.0, sr: int = 44100) -> Tuple[str, str]:
    """Convenience alias for standard 120bpm synthetic test track."""
    return generate_click_track(120.0, output_dir, duration, sr)


def generate_step_tempo(output_dir: str, sr: int = 44100) -> Tuple[str, str]:
    """120.0 BPM for 15s -> Instant step to 140.0 BPM for 15s."""
    total_duration = 30.0
    total_samples = int(sr * total_duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)

    beat_times = []
    current_time = 0.5

    while current_time < total_duration - 0.5:
        idx = int(current_time * sr)
        end_idx = min(total_samples, idx + len(kick))
        audio[idx:end_idx] += kick[: end_idx - idx]
        beat_times.append(current_time)

        bpm = 120.0 if current_time < 15.0 else 140.0
        current_time += 60.0 / bpm

    wav_path = os.path.join(output_dir, "synthetic_step_tempo.wav")
    beats_path = os.path.join(output_dir, "synthetic_step_tempo.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_breakdown_dropout(output_dir: str, sr: int = 44100) -> Tuple[str, str]:
    """120.0 BPM drums for 12s -> 8s silent breakdown -> 12s drums return."""
    total_duration = 32.0
    total_samples = int(sr * total_duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)

    beat_times = []
    current_time = 0.5
    interval = 60.0 / 120.0

    while current_time < total_duration - 0.5:
        beat_times.append(current_time)
        if current_time < 12.0 or current_time >= 20.0:
            idx = int(current_time * sr)
            end_idx = min(total_samples, idx + len(kick))
            audio[idx:end_idx] += kick[: end_idx - idx]

        current_time += interval

    wav_path = os.path.join(output_dir, "synthetic_breakdown_dropout.wav")
    beats_path = os.path.join(output_dir, "synthetic_breakdown_dropout.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_tempo_drift_accel(output_dir: str, duration: float = 30.0, sr: int = 44100) -> Tuple[str, str]:
    """Continuous accelerando: tempo drifts smoothly from 100.0 BPM to 135.0 BPM."""
    total_samples = int(sr * duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)

    beat_times = []
    current_time = 0.5

    while current_time < duration - 0.5:
        # Linear tempo interpolation
        progress = current_time / duration
        bpm = 100.0 + progress * 35.0  # 100 -> 135 BPM
        interval = 60.0 / bpm

        idx = int(current_time * sr)
        end_idx = min(total_samples, idx + len(kick))
        audio[idx:end_idx] += kick[: end_idx - idx]
        beat_times.append(current_time)

        current_time += interval

    wav_path = os.path.join(output_dir, "synthetic_tempo_drift_accel.wav")
    beats_path = os.path.join(output_dir, "synthetic_tempo_drift_accel.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_syncopated_reggae(output_dir: str, duration: float = 30.0, sr: int = 44100) -> Tuple[str, str]:
    """120.0 BPM with kicks on downbeats and loud hi-hats on upbeats (inversion test)."""
    total_samples = int(sr * duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)
    hat = _synthesize_hihat(sr)

    beat_times = []
    current_time = 0.5
    quarter = 60.0 / 120.0

    while current_time < duration - 0.5:
        beat_times.append(current_time)
        idx_kick = int(current_time * sr)
        end_k = min(total_samples, idx_kick + len(kick))
        audio[idx_kick:end_k] += kick[: end_k - idx_kick]

        upbeat_time = current_time + (quarter / 2.0)
        idx_hat = int(upbeat_time * sr)
        end_h = min(total_samples, idx_hat + len(hat))
        audio[idx_hat:end_h] += hat[: end_h - idx_hat] * 1.5

        current_time += quarter

    wav_path = os.path.join(output_dir, "synthetic_syncopated_reggae.wav")
    beats_path = os.path.join(output_dir, "synthetic_syncopated_reggae.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_polyrhythm_3_against_2(output_dir: str, duration: float = 30.0, sr: int = 44100) -> Tuple[str, str]:
    """
    4/4 Beat grid at 120 BPM (kicks), overlaid with a 3-against-2 cross-rhythm snare pattern.
    Tests if the tracker stays locked on the main pulse or gets pulled into triplets.
    """
    total_samples = int(sr * duration)
    audio = np.zeros(total_samples, dtype=np.float32)
    kick = _synthesize_kick(sr)
    snare = _synthesize_snare(sr)

    beat_times = []
    current_time = 0.5
    beat_interval = 60.0 / 120.0  # 0.5s

    # 1. Main 4/4 kicks (Ground Truth)
    while current_time < duration - 0.5:
        beat_times.append(current_time)
        idx = int(current_time * sr)
        end_idx = min(total_samples, idx + len(kick))
        audio[idx:end_idx] += kick[: end_idx - idx]
        current_time += beat_interval

    # 2. Overlaid 3:2 cross-rhythm snares (3 hits per 2 beats = 1.5x speed)
    triplet_interval = (beat_interval * 2.0) / 3.0  # 0.333s
    t_snare = 0.5
    while t_snare < duration - 0.5:
        idx = int(t_snare * sr)
        end_idx = min(total_samples, idx + len(snare))
        audio[idx:end_idx] += snare[: end_idx - idx] * 0.7
        t_snare += triplet_interval

    wav_path = os.path.join(output_dir, "synthetic_polyrhythm_3_against_2.wav")
    beats_path = os.path.join(output_dir, "synthetic_polyrhythm_3_against_2.beats.txt")
    _save_wav_and_beats(audio, beat_times, wav_path, beats_path, sr)
    return wav_path, beats_path


def generate_all_synthetic_tracks(output_dir: str) -> List[Tuple[str, str]]:
    """Generates the full 8-track synthetic benchmark suite."""
    tracks = [
        generate_click_track(120.0, output_dir),
        generate_click_track(85.0, output_dir),
        generate_click_track(140.0, output_dir),
        generate_step_tempo(output_dir),
        generate_breakdown_dropout(output_dir),
        generate_tempo_drift_accel(output_dir),
        generate_syncopated_reggae(output_dir),
        generate_polyrhythm_3_against_2(output_dir),
    ]
    return tracks


if __name__ == "__main__":
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "synthetic_cache"))
    generated = generate_all_synthetic_tracks(out)
    print(f"Generated {len(generated)} synthetic stress tracks in {out}")
