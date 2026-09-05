"""
benchmarks/engine/evaluator.py - Standardized, immutable evaluation engine for beat trackers.

Runs any model implementing BaseAudioAnalyzer over benchmark audio tracks at 60 FPS,
captures emitted beats, computes standard MIR metrics via mir_eval, logs per-frame telemetry,
and returns an objective scorecard.
"""

from __future__ import annotations
import os
import time
import wave
from typing import Dict, Any, List, Optional, Tuple, Type
import numpy as np
import mir_eval

from core.BaseAudioAnalyzer import BaseAudioAnalyzer


class MockAudioIngestion:
    """Lightweight, vectorized audio feature provider for simulation benchmark runs."""

    def __init__(self, nb_of_fft_band: int = 8, sample_rate: int = 44100, buffer_size: int = 1024) -> None:
        self.nb_of_fft_band = nb_of_fft_band
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.fft_band_values = np.zeros(self.nb_of_fft_band)
        self.band_means = np.zeros(self.nb_of_fft_band)
        self.smoothed_total_power = 0.0
        self.asserved_total_power = 0.0
        self.band_proportion = np.zeros(self.nb_of_fft_band)
        self.dynamic_audio_latency = 0.0

        # Build pre-computed Mel filterbank matrix
        fft_size = self.buffer_size // 2 + 1
        self.weight_matrix = np.zeros((self.nb_of_fft_band, fft_size))

        def hz_to_mel(f: float) -> float:
            return 2595.0 * np.log10(1.0 + f / 700.0)

        def mel_to_hz(m: float) -> float:
            return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

        lower_mel = hz_to_mel(20.0)
        upper_mel = hz_to_mel(20000.0)
        mel_points = np.linspace(lower_mel, upper_mel, self.nb_of_fft_band + 2)
        hz_points = mel_to_hz(mel_points)
        bin_points = np.floor((self.buffer_size + 1) * hz_points / self.sample_rate).astype(int)

        for i in range(self.nb_of_fft_band):
            start = min(bin_points[i], fft_size - 1)
            mid = min(bin_points[i + 1], fft_size - 1)
            end = min(bin_points[i + 2], fft_size - 1)
            if mid > start:
                self.weight_matrix[i, start:mid] = np.linspace(0, 1, mid - start, endpoint=False)
            if end > mid:
                self.weight_matrix[i, mid:end] = np.linspace(1, 0, end - mid, endpoint=False)
            band_sum = np.sum(self.weight_matrix[i, :])
            if band_sum > 0:
                self.weight_matrix[i, :] /= band_sum

        self.hanning_window = np.hanning(self.buffer_size)

    def process_frame(self, audio_chunk: np.ndarray) -> None:
        """Processes a 1024-sample audio chunk into Mel filterbank values."""
        if len(audio_chunk) < self.buffer_size:
            padded = np.zeros(self.buffer_size)
            padded[: len(audio_chunk)] = audio_chunk
            audio_chunk = padded

        windowed = audio_chunk * self.hanning_window
        fft_res = np.abs(np.fft.rfft(windowed))
        scale = 150.0 / (self.buffer_size / 1024.0)
        mel_bands = np.dot(self.weight_matrix, fft_res) * scale
        self.fft_band_values = mel_bands

        total_p = float(np.sum(mel_bands))
        self.smoothed_total_power = total_p
        if total_p > 1e-6:
            self.band_proportion = mel_bands / total_p
        else:
            self.band_proportion.fill(0.0)


def load_audio_file(audio_path: str, target_sr: int = 44100) -> Tuple[np.ndarray, int]:
    """Loads WAV, MP3, or M4A audio into a 1D float numpy array."""
    ext = os.path.splitext(audio_path)[1].lower()

    if ext == ".wav":
        with wave.open(audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

            if sampwidth == 2:
                samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            elif sampwidth == 1:
                samples = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            if n_channels > 1:
                samples = samples.reshape(-1, n_channels).mean(axis=1)

            if framerate != target_sr:
                # Basic linear resample for WAV if rate differs
                num_target = int(len(samples) * target_sr / framerate)
                samples = np.interp(
                    np.linspace(0, len(samples), num_target, endpoint=False),
                    np.arange(len(samples)),
                    samples
                ).astype(np.float32)

            return samples, target_sr

    # 1. Check for pre-cached .npz audio array (fastest, avoids MP3 codec overhead)
    basename = os.path.basename(audio_path)
    parent_dir = os.path.dirname(audio_path)
    npz_candidates = [
        os.path.join(parent_dir, "librosa", f"{basename}.npz"),
        f"{audio_path}.npz",
    ]
    for npz_path in npz_candidates:
        if os.path.exists(npz_path):
            try:
                data = np.load(npz_path, allow_pickle=True)
                if "y" in data:
                    return data["y"].astype(np.float32), target_sr
            except Exception:
                pass

    # Fallback to torchaudio or librosa for MP3/M4A
    try:
        import torchaudio
        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
            waveform = resampler(waveform)
        return waveform.numpy().flatten().astype(np.float32), target_sr
    except Exception:
        pass

    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
        return y.astype(np.float32), target_sr
    except Exception as e:
        raise RuntimeError(f"Could not load audio file {audio_path}: {e}")


def load_beats_file(beats_path: str) -> np.ndarray:
    """Loads a .beats.txt or .npz ground truth beat list into a numpy array."""
    if beats_path.endswith(".npz"):
        data = np.load(beats_path)
        if "beats" in data:
            return np.array(data["beats"], dtype=np.float64)
        elif "beat_times" in data:
            return np.array(data["beat_times"], dtype=np.float64)
        else:
            first_key = list(data.keys())[0]
            return np.array(data[first_key], dtype=np.float64)

    timestamps = []
    with open(beats_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            try:
                timestamps.append(float(parts[0]))
            except ValueError:
                continue
    return np.array(timestamps, dtype=np.float64)


def run_benchmark_on_track(
    analyzer_class: Type[BaseAudioAnalyzer],
    audio_path: str,
    beats_path: str,
    config: Optional[Any] = None,
    fps: float = 60.0
) -> Dict[str, Any]:
    """
    Executes a complete simulation of a single track and returns its evaluation metrics and telemetry.
    """
    y, sr = load_audio_file(audio_path, target_sr=44100)
    true_beats = load_beats_file(beats_path)

    # Initialize simulated environment
    infos = {
        "startServer": False,
        "useMicrophone": False,
        "HARDWARE_MODE": "simulation",
        "onRaspberry": False,
        "fakeDelay": 0.0,
        "latency": 0.0,
    }
    ingestion = MockAudioIngestion(nb_of_fft_band=8, sample_rate=sr, buffer_size=1024)
    analyzer = analyzer_class(ingestion, infos, config=config)
    analyzer.reset()

    # Step-by-step simulation loop
    chunk_samples = int(sr / fps)  # 735 samples per frame at 60 FPS
    total_samples = len(y)
    total_frames = total_samples // chunk_samples

    current_pos = 0
    current_time = 0.0
    dt = 1.0 / fps

    rolling_audio_buffer = np.zeros(1024, dtype=np.float32)
    emitted_beats: List[float] = []
    telemetry_records: List[Dict[str, Any]] = []

    frame_durations: List[float] = []
    last_logged_beat_count = 0

    for frame_idx in range(total_frames):
        incoming = y[current_pos : current_pos + chunk_samples]
        current_pos += chunk_samples
        if len(incoming) < chunk_samples:
            break

        rolling_audio_buffer[:-chunk_samples] = rolling_audio_buffer[chunk_samples:]
        rolling_audio_buffer[-chunk_samples:] = incoming

        # Vectorized FFT
        ingestion.process_frame(rolling_audio_buffer)

        # Time the model update
        t0 = time.perf_counter()
        analyzer.update(current_time, dt, fps_ratio=1.0)
        t_elapsed = time.perf_counter() - t0
        frame_durations.append(t_elapsed)

        # Detect beat emission (either is_beat flag or beat_count increment)
        if analyzer.is_beat or (analyzer.beat_count > last_logged_beat_count):
            emitted_beats.append(current_time)
            last_logged_beat_count = analyzer.beat_count

        # Capture telemetry at 10 FPS to save memory (every 6th frame at 60 FPS)
        if frame_idx % 6 == 0:
            telem = analyzer.capture_frame_telemetry()
            telem["time"] = current_time
            telem["is_beat_emitted"] = bool(analyzer.is_beat)
            telemetry_records.append(telem)

        if frame_idx % 1800 == 0 and frame_idx > 0:
            print(f"       [{current_time:.0f}s / {total_frames * dt:.0f}s]", flush=True)

        current_time += dt

    est_beats = np.array(emitted_beats, dtype=np.float64)

    # Compute MIR metrics
    scorecard = compute_scorecard(true_beats, est_beats, frame_durations)
    scorecard["audio_path"] = audio_path
    scorecard["beats_path"] = beats_path
    scorecard["total_frames"] = total_frames
    scorecard["duration_sec"] = current_time

    return {
        "scorecard": scorecard,
        "true_beats": true_beats,
        "est_beats": est_beats,
        "telemetry": telemetry_records,
        "model_metadata": analyzer.get_model_metadata(),
    }


def compute_scorecard(
    reference_beats: np.ndarray,
    estimated_beats: np.ndarray,
    frame_durations: List[float]
) -> Dict[str, Any]:
    """Computes standardized MIR beat tracking metrics with mir_eval."""
    avg_frame_ms = float(np.mean(frame_durations) * 1000.0) if frame_durations else 0.0

    if len(reference_beats) < 2 or len(estimated_beats) < 2:
        return {
            "f1_50ms": 0.0,
            "f1_70ms": 0.0,
            "cmlt": 0.0,
            "amlt": 0.0,
            "cmlc": 0.0,
            "amlc": 0.0,
            "upbeat_gap": 0.0,
            "mean_phase_bias_ms": 0.0,
            "phase_jitter_ms": 0.0,
            "avg_frame_time_ms": avg_frame_ms,
            "total_ref_beats": len(reference_beats),
            "total_est_beats": len(estimated_beats),
        }

    # Standard mir_eval evaluations
    f1_70ms = float(mir_eval.beat.f_measure(reference_beats, estimated_beats, f_measure_threshold=0.070))
    f1_50ms = float(mir_eval.beat.f_measure(reference_beats, estimated_beats, f_measure_threshold=0.050))
    cmlc, cmlt, amlc, amlt = mir_eval.beat.continuity(reference_beats, estimated_beats)

    cmlt = float(cmlt)
    amlt = float(amlt)
    upbeat_gap = float(max(0.0, amlt - cmlt))

    # Phase Bias and Jitter calculation (for matched beats within 150ms)
    time_diffs = []
    for est in estimated_beats:
        dists = np.abs(reference_beats - est)
        min_idx = int(np.argmin(dists))
        if dists[min_idx] <= 0.150:
            time_diffs.append((est - reference_beats[min_idx]) * 1000.0)

    if time_diffs:
        bias_ms = float(np.mean(time_diffs))
        jitter_ms = float(np.std(time_diffs))
    else:
        bias_ms = 0.0
        jitter_ms = 0.0

    return {
        "f1_50ms": round(f1_50ms, 4),
        "f1_70ms": round(f1_70ms, 4),
        "cmlt": round(cmlt, 4),
        "amlt": round(amlt, 4),
        "cmlc": round(float(cmlc), 4),
        "amlc": round(float(amlc), 4),
        "upbeat_gap": round(upbeat_gap, 4),
        "mean_phase_bias_ms": round(bias_ms, 2),
        "phase_jitter_ms": round(jitter_ms, 2),
        "avg_frame_time_ms": round(avg_frame_ms, 3),
        "total_ref_beats": len(reference_beats),
        "total_est_beats": len(estimated_beats),
    }
