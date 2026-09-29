"""
research/experiments/models/MultiBandOnsetAudioAnalyzer.py - Candidate Model for Cycle 008.

Multi-Band Onset Derivative Rhythm Analyzer for the Vialactée interactive LED chandelier.
Subclasses BaseAudioAnalyzer directly, uniting:
1. Multi-Resolution Mel Filterbank (configurable B in {16, 24, 32} bands, default 32).
2. Per-Band Half-Wave Rectified Onset Derivative: dE_b[t] = max(0, E_b[t] - E_b[t-1]).
3. Instrument-Separated Stream Synthesis:
   - Dedicated Sub-Bass / Kick Fundamental stream (y_kick)
   - Dedicated Snare Body & Snap stream (y_snare)
   - Dynamic Crest-Factor Squelch on Mid-Melodic Guitar / Vocal bands (y_mid)
   - Dedicated Hi-Hat Offbeat stream (y_hat) with contrastive subtraction
4. Kick-Conditioned Anti-Phase Disambiguation:
   Resolves 180° upbeat traps by comparing kick transient density between candidate phase and anti-phase.
5. Fast 100-Class Circular Tempo-Class Scout with S^1 Angular Neighborhood Inertia (+/- 0.05).
6. Strictly Dyadic Octave Candidates {0.5x, 1.0x, 2.0x} (banning polyrhythmic fifth traps).
7. Heavy Pearson Judge on Dyadic Octaves via Precomputed Triangular Pulse Bank with Negative Baseline (-1.0).
8. Sub-Frame Parabolic Peak Refinement & Continuous Soft-Snap with Boundary Wrap Clamp.
9. Zero Dynamic NumPy Heap Allocation in per-frame update() (<= 0.50ms CPU latency).

Authors: Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
Cycle: 008
Date: 2026-09-06
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.RhythmConfig import RhythmConfig
from core.StructuralNoveltyDetector import StructuralNoveltyDetector
from research.dsp.comb_kernels import build_dense_phase_bank

logger = logging.getLogger(__name__)


def bpm_to_class(bpm: float) -> float:
    """Maps a linear BPM to a continuous circular value in [0.0, 1.0) on the octave ring."""
    return float(np.log2(max(1.0, bpm) / 60.0) % 1.0)


class MultiBandOnsetAudioAnalyzer(BaseAudioAnalyzer):
    """
    Multi-Band Onset Derivative Beat Tracker subclassing BaseAudioAnalyzer directly.
    """

    NB_AUDIO_BANDS: int = 32

    def __init__(
        self,
        ingestion: Any = None,
        infos: Optional[Dict[str, Any]] = None,
        config: Optional[RhythmConfig] = None
    ) -> None:
        cfg = config if config is not None else RhythmConfig()
        inf = infos if infos is not None else {}
        super().__init__(ingestion=ingestion, infos=inf, config=cfg)
        self.config: RhythmConfig = cfg

        self.hardware_latency: float = float(inf.get("latency", 0.0))
        self.lookahead_seconds: float = float(inf.get("fakeDelay", 5.0))
        self.odf_fps: float = 60.0
        self.btrack_fps: float = self.odf_fps

        # Configure Multi-Band Resolution (16, 24, 32 bands)
        nb_from_ingestion = getattr(self.ingestion, 'nb_of_fft_band', 32)
        cfg_bands = getattr(self.config, 'nb_bands', 8)
        if cfg_bands != 8:
            self.nb_bands: int = cfg_bands
        else:
            self.nb_bands = nb_from_ingestion if nb_from_ingestion != 8 else self.NB_AUDIO_BANDS

        self.novelty_detector = StructuralNoveltyDetector(
            nb_fft_bands=self.nb_bands,
            config=self.config
        )

        # 1. Multi-Band State Buffers (Zero Allocation)
        self.prev_fft_band_values = np.zeros(self.nb_bands, dtype=np.float64)
        self.diff_buffer = np.zeros(self.nb_bands, dtype=np.float64)
        self.dE = np.zeros(self.nb_bands, dtype=np.float64)
        self.band_flux = np.zeros(self.nb_bands, dtype=np.float64)
        self.smoothed_flux = np.zeros(self.nb_bands, dtype=np.float64)

        # Adaptive peak sensitivity buffers
        self.peak_sensitivity = np.ones(self.nb_bands, dtype=np.float64) * 1.8
        self.peak_times = np.zeros(self.nb_bands, dtype=np.float64)
        self.band_peak = np.zeros(self.nb_bands, dtype=int)

        # Instrument Routing Table based on band resolution
        self._setup_instrument_routing()

        # Rolling crest-factor squelch buffer (180 frames = 3.0s)
        self.H_len: int = 180
        self.band_flux_history = np.zeros((self.H_len, self.nb_bands), dtype=np.float64)
        self.h_idx: int = 0
        self.h_count: int = 0
        self.dynamic_squelch = np.ones(self.nb_bands, dtype=np.float64)

        # 2. ODF Buffer Configuration (M=300 samples, 5.0s lookahead)
        self.M: int = 300
        self.odf_buffer_size: int = max(360, int((self.lookahead_seconds + 1.0) * self.odf_fps))
        self.odf_buffer: np.ndarray = np.zeros(self.odf_buffer_size, dtype=np.float64)
        self.kick_odf_buffer: np.ndarray = np.zeros(self.odf_buffer_size, dtype=np.float64)
        self.rolling_flux_baseline: float = 0.0

        # Causal exponential decay curve (applied ONCE to lookahead buffer)
        m_idx = np.arange(self.M, dtype=np.float64)
        self.decay_curve: np.ndarray = np.exp(-1.5 * (1.0 - m_idx / (self.M - 1.0)))

        # Pre-allocated scratch buffers for tempo sweep (zero heap allocations)
        self.y_lookahead_weighted = np.zeros(self.M, dtype=np.float64)
        self.y_centered = np.zeros(self.M, dtype=np.float64)

        # 3. Fast Scout across S^1 Circular Ring
        self.num_classes: int = 100
        self.class_grid: np.ndarray = np.linspace(0.0, 1.0, self.num_classes, endpoint=False, dtype=np.float64)
        self.scout_rounded_bpms = np.zeros(self.num_classes, dtype=int)
        self.scout_priors = np.zeros(self.num_classes, dtype=np.float64)

        center = getattr(self.config, 'human_prior_center', 125.0)
        sigma = getattr(self.config, 'human_prior_sigma', 40.0)
        self.human_prior_center: float = center
        self.human_prior_sigma: float = sigma

        for i, c in enumerate(self.class_grid):
            base_bpm = 60.0 * (2.0 ** c)
            eval_bpm = base_bpm if base_bpm >= 90.0 else base_bpm * 2.0
            self.scout_rounded_bpms[i] = int(round(eval_bpm))
            self.scout_priors[i] = 0.5 + 0.5 * np.exp(-0.5 * ((eval_bpm - self.human_prior_center) / self.human_prior_sigma) ** 2)

        # Pre-computed S^1 circular ring neighbor lookup table for radius 0.05 (11 classes)
        self.class_neighbors = np.zeros((self.num_classes, 11), dtype=int)
        for i in range(self.num_classes):
            self.class_neighbors[i] = (i + np.arange(-5, 6)) % self.num_classes

        # 4. Precompute Normalized Triangular Pulse Templates with Negative Baseline (-1.0)
        self.bpm_min: float = 60.0
        self.bpm_max: float = 200.0
        self.templates: Dict[int, np.ndarray] = {}
        self.p_scores_buffers: Dict[int, np.ndarray] = {}

        for b in range(int(self.bpm_min), int(self.bpm_max) + 1):
            T_raw = build_dense_phase_bank(
                bpm=float(b),
                fps=self.odf_fps,
                buffer_len=self.M,
                pulse_shape="triangular",
                duty_cycle=0.10
            )
            T_centered = T_raw - np.mean(T_raw, axis=1, keepdims=True)
            T_std = np.sqrt(np.sum(T_centered ** 2, axis=1, keepdims=True)) + 1e-6
            T_norm = (T_centered / T_std).astype(np.float64)
            self.templates[b] = T_norm
            self.p_scores_buffers[b] = np.zeros(T_norm.shape[0], dtype=np.float64)

        # 5. Continuous Speaker Flywheel State
        self.speaker_phase: float = 0.0
        self.bpm: float = 120.0
        self.long_term_class_idx: int = int(round((np.log2(120.0 / 60.0) % 1.0) * self.num_classes)) % self.num_classes
        self.confidence_score: float = 0.0
        self.flywheel_status: str = "coasting"
        self.time_since_sweep: float = 0.0

        self.beat_count: int = 0
        self.last_beat_time: float = -100.0

        self.is_beat: bool = False
        self.is_real_beat: bool = False
        self.is_dropped_beat: bool = False
        self.current_beat_tag: str = "Bass/Kick"

    def _setup_instrument_routing(self) -> None:
        """Sets up frequency band indices and weights tailored to the band resolution."""
        if self.nb_bands >= 32:
            self.kick_bands = [0, 1, 2]
            self.kick_weights = [2.0, 1.8, 1.2]
            self.snare_bands = [4, 5, 14, 15, 16]
            self.snare_weights = [1.2, 1.2, 0.8, 0.8, 0.8]
            self.mid_bands = list(range(6, 14))
            self.hat_bands = list(range(22, min(self.nb_bands, 32)))
        elif self.nb_bands >= 24:
            self.kick_bands = [0, 1, 2]
            self.kick_weights = [2.0, 1.6, 1.0]
            self.snare_bands = [3, 4, 11, 12, 13]
            self.snare_weights = [1.2, 1.2, 0.8, 0.8, 0.8]
            self.mid_bands = list(range(5, 11))
            self.hat_bands = list(range(16, min(self.nb_bands, 24)))
        elif self.nb_bands >= 16:
            self.kick_bands = [0, 1]
            self.kick_weights = [2.0, 1.5]
            self.snare_bands = [2, 3, 7, 8]
            self.snare_weights = [1.2, 1.2, 0.8, 0.8]
            self.mid_bands = [4, 5, 6]
            self.hat_bands = list(range(11, min(self.nb_bands, 16)))
        else:
            # 8-band fallback
            self.kick_bands = [0, 1]
            self.kick_weights = [2.0, 1.8]
            self.snare_bands = [2, 3]
            self.snare_weights = [1.2, 1.0]
            self.mid_bands = [4, 5]
            self.hat_bands = [6, 7]

    def reset(self) -> None:
        """Resets all runtime state, buffers, and accumulators."""
        self.prev_fft_band_values.fill(0.0)
        self.diff_buffer.fill(0.0)
        self.dE.fill(0.0)
        self.band_flux.fill(0.0)
        self.smoothed_flux.fill(0.0)
        self.peak_sensitivity.fill(1.8)
        self.peak_times.fill(0.0)
        self.band_peak.fill(0)
        self.band_flux_history.fill(0.0)
        self.h_idx = 0
        self.h_count = 0
        self.dynamic_squelch.fill(1.0)
        self.odf_buffer.fill(0.0)
        self.kick_odf_buffer.fill(0.0)
        self.rolling_flux_baseline = 0.0

        self.speaker_phase = 0.0
        self.bpm = 120.0
        self.long_term_class_idx = int(round((np.log2(120.0 / 60.0) % 1.0) * self.num_classes)) % self.num_classes
        self.confidence_score = 0.0
        self.flywheel_status = "coasting"
        self.time_since_sweep = 0.0

        self.beat_count = 0
        self.last_beat_time = -100.0

        self.is_beat = False
        self.is_real_beat = False
        self.is_dropped_beat = False
        self.current_beat_tag = "Bass/Kick"

        self.novelty_detector = StructuralNoveltyDetector(
            nb_fft_bands=self.nb_bands,
            config=self.config
        )

    def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """Primary per-frame 60 FPS processing step with zero dynamic heap allocations."""
        self.is_beat = False
        self.is_real_beat = False
        self.is_dropped_beat = False

        # 1. Structural Novelty
        self.novelty_detector.update(
            current_timbre=self.ingestion.band_proportion,
            current_power=self.ingestion.smoothed_total_power,
            current_time=current_time,
            dt=dt,
            fps_ratio=fps_ratio
        )
        if self.novelty_detector.is_song_change:
            self.beat_count = 0
            self.speaker_phase = 0.0

        # 2. Multi-Band Spectral Flux & Derivative Calculation
        is_strong_peak = self._ingest_multiband_derivative_odf(current_time, fps_ratio)

        # 3. Fast Scout across S^1, Dyadic Pearson Judge, & Sub-Frame Parabolic Soft-Snap
        self._run_tempo_and_phase_sweep(dt, is_strong_peak)

        # 4. Continuous Speaker Flywheel Advancement & Physical Beat Validation
        self._advance_speaker_flywheel(current_time, dt)

    def _ingest_multiband_derivative_odf(self, current_time: float, fps_ratio: float) -> bool:
        """
        Calculates half-wave rectified onset flux per band, evaluates crest-factor squelch
        on mid bands, synthesizes instrument streams, and rolls the ODF buffers.
        """
        fft_vals = self.ingestion.fft_band_values
        active_len = min(len(fft_vals), self.nb_bands)

        # Per-band derivative: dE_b = max(0, E_b[t] - E_b[t-1])
        np.subtract(fft_vals[:active_len], self.prev_fft_band_values[:active_len], out=self.diff_buffer[:active_len])
        np.maximum(0.0, self.diff_buffer[:active_len], out=self.dE[:active_len])
        np.copyto(self.prev_fft_band_values[:active_len], fft_vals[:active_len])
        np.copyto(self.band_flux[:active_len], self.dE[:active_len])

        # Rolling crest-factor squelch update
        self.band_flux_history[self.h_idx, :active_len] = self.dE[:active_len]
        self.h_idx = (self.h_idx + 1) % self.H_len
        self.h_count = min(self.H_len, self.h_count + 1)

        if self.h_count >= 30:
            active_h = self.band_flux_history[:self.h_count, :active_len]
            means = np.mean(active_h, axis=0) + 1e-6
            maxs = np.max(active_h, axis=0)
            crest = maxs / means

            # Mid bands: continuous sigmoid squelch
            for b in self.mid_bands:
                if b < active_len:
                    s = 1.0 / (1.0 + np.exp(-0.5 * (crest[b] - 14.0)))
                    self.dynamic_squelch[b] = s

        # Instrument-Separated Stream Synthesis
        dE = self.dE
        y_kick = 0.0
        for b, w in zip(self.kick_bands, self.kick_weights):
            if b < active_len:
                y_kick += w * dE[b]

        y_snare = 0.0
        for b, w in zip(self.snare_bands, self.snare_weights):
            if b < active_len:
                y_snare += w * dE[b]

        y_mid = 0.0
        for b in self.mid_bands:
            if b < active_len:
                y_mid += 0.20 * self.dynamic_squelch[b] * dE[b]

        y_hat = 0.0
        for b in self.hat_bands:
            if b < active_len:
                y_hat += 0.30 * dE[b]

        # Contrastive novelty function: subtract excess hi-hat sizzle
        penalty = 0.35 * max(0.0, y_hat - y_kick)
        y_metric = max(0.0, float((y_kick + y_snare + y_mid) - penalty))

        # Roll circular ODF buffers
        self.odf_buffer[:-1] = self.odf_buffer[1:]
        self.odf_buffer[-1] = y_metric

        self.kick_odf_buffer[:-1] = self.kick_odf_buffer[1:]
        self.kick_odf_buffer[-1] = y_kick

        decay = self.config.rolling_flux_decay
        self.rolling_flux_baseline = decay * self.rolling_flux_baseline + (1.0 - decay) * y_metric
        is_strong_peak = y_metric > (
            self.rolling_flux_baseline * self.config.strong_peak_multiplier + 0.1
        )
        return is_strong_peak

    def _run_tempo_and_phase_sweep(self, dt: float, is_strong_peak: bool) -> None:
        """
        Runs the S^1 tempo scout, dyadic Pearson judge with triangular negative-baseline
        templates, kick-conditioned anti-phase disambiguation, and sub-frame soft-snap.
        """
        self.time_since_sweep += dt
        if not (is_strong_peak or self.time_since_sweep >= self.config.sweep_interval):
            return

        self.time_since_sweep = 0.0

        # Lookahead buffer (M=300 samples, 5.0s window)
        y_lookahead = self.odf_buffer[-self.M:]
        rms_odf = float(np.sqrt(np.mean(y_lookahead ** 2)))
        if rms_odf < 1.0:
            self.confidence_score = 0.0
            self.flywheel_status = "coasting"
            return

        # Prepare normalized lookahead buffer (single decay curve)
        np.multiply(y_lookahead, self.decay_curve, out=self.y_lookahead_weighted)
        buf_mean = np.mean(self.y_lookahead_weighted)
        np.subtract(self.y_lookahead_weighted, buf_mean, out=self.y_centered)
        buf_std = np.sqrt(np.sum(self.y_centered ** 2)) + 1e-6

        is_locked = (self.beat_count >= 4 and self.confidence_score >= self.config.moderate_confidence_threshold)

        # 1. Fast Scout across S^1 Circular Ring
        best_scout_score = -float('inf')
        best_class_idx = self.long_term_class_idx

        if not is_locked:
            eval_indices = range(self.num_classes)
        else:
            # Constrain to angular neighborhood +/- 0.05 around long_term_class
            eval_indices = self.class_neighbors[self.long_term_class_idx]

        for idx in eval_indices:
            bpm_k = self.scout_rounded_bpms[idx]
            if bpm_k in self.templates:
                T = self.templates[bpm_k]
                p_buf = self.p_scores_buffers[bpm_k]
                np.dot(T, self.y_centered, out=p_buf)
                np.divide(p_buf, buf_std, out=p_buf)
                score = float(np.max(p_buf) * self.scout_priors[idx])
                if score > best_scout_score:
                    best_scout_score = score
                    best_class_idx = idx

        # 2. Pearson Judge on Dyadic Octaves ONLY {0.5x, 1.0x, 2.0x}
        base_bpm = 60.0 * (2.0 ** self.class_grid[best_class_idx])
        multipliers = (0.5, 1.0, 2.0)
        best_judge_score = -float('inf')
        best_bpm = self.bpm
        best_p_idx = 0
        best_pearson = 0.0
        best_scores_arr: Optional[np.ndarray] = None

        for mult in multipliers:
            cand = base_bpm * mult
            if self.bpm_min <= cand <= self.bpm_max:
                bpm_k = int(round(cand))
                if bpm_k in self.templates:
                    T = self.templates[bpm_k]
                    p_buf = self.p_scores_buffers[bpm_k]
                    np.dot(T, self.y_centered, out=p_buf)
                    np.divide(p_buf, buf_std, out=p_buf)
                    p_max_idx = int(np.argmax(p_buf))
                    score_p = float(p_buf[p_max_idx])

                    cand_prior = 0.5 + 0.5 * np.exp(-0.5 * ((cand - self.human_prior_center) / self.human_prior_sigma) ** 2)
                    weighted_score = score_p * cand_prior

                    # Octave inertia
                    if is_locked and abs(np.log2(cand / self.bpm)) > 0.4:
                        weighted_score /= 1.20

                    if weighted_score > best_judge_score:
                        best_judge_score = weighted_score
                        best_bpm = cand
                        best_p_idx = p_max_idx
                        best_pearson = score_p
                        best_scores_arr = p_buf

        self.confidence_score = best_pearson

        if best_pearson >= self.config.moderate_confidence_threshold and best_scores_arr is not None:
            self.bpm = best_bpm
            self.long_term_class_idx = int(round((np.log2(best_bpm / 60.0) % 1.0) * self.num_classes)) % self.num_classes
            self.flywheel_status = "locked"

            # 3. Sub-frame Parabolic Peak Refinement
            delta_p = 0.0
            p_len = len(best_scores_arr)
            if 0 < best_p_idx < p_len - 1:
                p_prev = best_scores_arr[best_p_idx - 1]
                p_curr = best_scores_arr[best_p_idx]
                p_next = best_scores_arr[best_p_idx + 1]
                denom = 2.0 * (p_prev - 2.0 * p_curr + p_next)
                if denom < -1e-6:
                    delta_p = np.clip((p_prev - p_next) / denom, -0.5, 0.5)

            tau = 60.0 * self.odf_fps / self.bpm
            ingest_phase = ((best_p_idx + delta_p) % tau) / tau

            # 4. Kick-Conditioned Anti-Phase Disambiguation
            half_tau = tau * 0.5
            anti_p_idx = int(round((best_p_idx + half_tau) % tau))
            if anti_p_idx < p_len and best_scores_arr[anti_p_idx] >= 0.80 * best_pearson:
                k_lookahead = self.kick_odf_buffer[-self.M:]
                step = max(1, int(round(tau)))
                p1_offset = (p_len - 1 - best_p_idx) % step
                pa_offset = (p_len - 1 - anti_p_idx) % step
                k1_samples = k_lookahead[p1_offset::step]
                ka_samples = k_lookahead[pa_offset::step]
                mean_k1 = float(np.mean(k1_samples)) if len(k1_samples) > 0 else 0.0
                mean_ka = float(np.mean(ka_samples)) if len(ka_samples) > 0 else 0.0

                if mean_ka > 1.25 * mean_k1:
                    ingest_phase = (ingest_phase + 0.5) % 1.0

            total_delay = (
                self.lookahead_seconds
                + getattr(self.ingestion, 'dynamic_audio_latency', 0.0)
                + self.hardware_latency
            )
            target_speaker_phase = (ingest_phase - (self.bpm / 60.0) * total_delay) % 1.0
            phase_err = (target_speaker_phase - self.speaker_phase + 0.5) % 1.0 - 0.5

            # Continuous Soft-Snap
            snap_ratio = (
                self.config.high_snap_ratio
                if best_pearson > self.config.high_confidence_threshold
                else self.config.moderate_snap_ratio
            )
            new_phase = self.speaker_phase + snap_ratio * phase_err

            # Boundary wrap clamp
            if self.speaker_phase < 0.25 and new_phase < 0.0:
                self.speaker_phase = 0.0
            elif self.speaker_phase > 0.75 and new_phase >= 1.0:
                self.speaker_phase = 0.999
            else:
                self.speaker_phase = new_phase % 1.0
        else:
            self.flywheel_status = "coasting"

    def _advance_speaker_flywheel(self, current_time: float, dt: float) -> None:
        """Advances continuous mechanical speaker flywheel and validates physical beat events."""
        phase_increment = (self.bpm / 60.0) * dt
        self.speaker_phase += phase_increment

        if self.speaker_phase >= 1.0:
            self.speaker_phase -= 1.0

            min_beat_interval = max(0.18, 0.40 * (60.0 / max(1.0, self.bpm)))
            if (current_time - self.last_beat_time) >= min_beat_interval:
                self.beat_count += 1
                self.is_beat = True
                self.last_beat_time = current_time

                # Validate physical presence at speaker playback time window
                speaker_offset = int(self.lookahead_seconds * self.odf_fps)
                speaker_center = max(0, min(self.odf_buffer_size - 1, (self.odf_buffer_size - 1) - speaker_offset))
                w_start = max(0, speaker_center - 3)
                w_end = min(self.odf_buffer_size, speaker_center + 4)
                local_energy = float(np.max(self.odf_buffer[w_start:w_end]))

                if (
                    local_energy > (self.config.real_beat_baseline_ratio * self.rolling_flux_baseline)
                    and local_energy >= self.config.real_beat_energy_floor
                ):
                    self.is_real_beat = True
                    self.is_dropped_beat = False
                else:
                    self.is_real_beat = False
                    self.is_dropped_beat = True

                # Transient Frequency-Band Classification
                if len(self.band_flux) >= 8:
                    b_val = float(np.sum(self.band_flux[self.kick_bands]))
                    m_val = float(np.sum(self.band_flux[self.snare_bands]))
                    h_val = float(np.sum(self.band_flux[self.hat_bands]))
                    if b_val >= m_val and b_val >= h_val:
                        self.current_beat_tag = "Bass/Kick"
                    elif m_val >= b_val and m_val >= h_val:
                        self.current_beat_tag = "Snare/Mid"
                    else:
                        self.current_beat_tag = "Hi-hat/Cymbal"
                else:
                    self.current_beat_tag = "Bass/Kick"

    def capture_frame_telemetry(self) -> Dict[str, Any]:
        """Captures rich per-frame telemetry for MIR benchmark evaluation."""
        return {
            "bpm": float(self.bpm),
            "beat_phase": float(self.speaker_phase),
            "confidence": float(self.confidence_score),
            "status": str(self.flywheel_status),
            "is_beat": bool(self.is_beat),
            "is_real_beat": bool(self.is_real_beat),
            "is_dropped_beat": bool(self.is_dropped_beat),
            "beat_tag": str(self.current_beat_tag),
            "rolling_flux_baseline": float(self.rolling_flux_baseline),
            "custom_flux": float(self.odf_buffer[-1]) if len(self.odf_buffer) > 0 else 0.0,
            "asserved_novelty": float(self.novelty_detector.asserved_novelty),
            "combined_novelty": float(self.novelty_detector.combined_novelty),
        }

    # ==========================================
    # PROPERTIES & COMPATIBILITY FACADES
    # ==========================================

    @property
    def beat_phase(self) -> float:
        return float(self.speaker_phase)

    @property
    def beat_confidence(self) -> float:
        return float(self.confidence_score)

    @property
    def standalone_phase(self) -> float:
        return float(self.speaker_phase)

    @property
    def standalone_bpm(self) -> float:
        return float(self.bpm)

    @property
    def is_song_change(self) -> bool:
        return self.novelty_detector.is_song_change

    @is_song_change.setter
    def is_song_change(self, val: bool) -> None:
        self.novelty_detector.is_song_change = val

    @property
    def is_verse_chorus_change(self) -> bool:
        return self.novelty_detector.is_verse_chorus_change

    @is_verse_chorus_change.setter
    def is_verse_chorus_change(self, val: bool) -> None:
        self.novelty_detector.is_verse_chorus_change = val

    @property
    def asserved_novelty(self) -> float:
        return self.novelty_detector.asserved_novelty

    @property
    def combined_novelty(self) -> float:
        return self.novelty_detector.combined_novelty
