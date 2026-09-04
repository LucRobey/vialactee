"""
AudioAnalyzer.py - Predictive Rhythm & Structural Event Analysis Engine

Implements the Anticipation Flywheel ("Oracle") architecture for the Vialactée
LED chandelier. Uses an O(1) precomputed Pearson template bank, circular logarithmic
tempo-class math, and 5-second look-ahead phase back-projection to drive a continuous
speaker-time flywheel with zero lag, breakdown coasting, and frequency-band beat tagging.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING
import time
import logging
import numpy as np

from core.RhythmConfig import RhythmConfig
from core.StructuralNoveltyDetector import StructuralNoveltyDetector

if TYPE_CHECKING:
    from core.AudioIngestion import AudioIngestion

logger = logging.getLogger(__name__)


# =====================================================================
# HARMONIC TEMPO-CLASS ARITHMETIC CORE
# =====================================================================

def bpm_to_class(bpm: float) -> float:
    """Map a linear BPM to a circular float in [0.0, 1.0) based on octave scale."""
    return float(np.log2(max(1.0, bpm) / 60.0) % 1.0)


def class_to_bpm_candidates(bpm_class: float) -> List[float]:
    """Returns the primary harmonic multipliers (octaves & fifths) for a given tempo class."""
    base_bpm = 60.0 * (2.0 ** (bpm_class % 1.0))
    return [
        base_bpm * 0.5,    # Sub-octave (e.g., 60 BPM)
        base_bpm * 0.75,   # Sub-fifth (e.g., 90 BPM)
        base_bpm * 1.0,    # Base tempo (e.g., 120 BPM)
        base_bpm * 1.5,    # Perfect fifth (e.g., 180 BPM)
        base_bpm * 2.0     # Double octave (e.g., 240 BPM -> clipped in judge)
    ]


def tempo_class_distance(f1: float, f2: float) -> float:
    """Shortest circular distance on the [0.0, 1.0) logarithmic ring."""
    d = abs(f1 - f2)
    return min(d, 1.0 - d)


def harmonic_alignment(current_class: float, long_term_class: float) -> Tuple[float, float]:
    """
    Checks straight octaves AND perfect fifths (1.5x / shift = log2(1.5))
    to safely align without polyrhythmic jumps.
    """
    shift = np.log2(1.5)  # approx 0.58496
    d_oct = tempo_class_distance(current_class, long_term_class)
    d_fifth_up = tempo_class_distance(current_class, (long_term_class + shift) % 1.0)
    d_fifth_down = tempo_class_distance(current_class, (long_term_class - shift) % 1.0)

    min_d = min(d_oct, d_fifth_up, d_fifth_down)

    if min_d == d_oct:
        aligned_class = current_class
    elif min_d == d_fifth_up:
        aligned_class = (current_class - shift) % 1.0
    else:
        aligned_class = (current_class + shift) % 1.0

    return min_d, aligned_class


# =====================================================================
# FAST TEMPLATE BANK (O(1) Precomputed Pearson Correlation)
# =====================================================================

class FastTemplateBank:
    """
    Precomputes and caches normalized triangular beat pulse templates.
    Allows Pearson cross-correlation via high-speed compiled NumPy dot products.
    """

    def __init__(self, btrack_fps: float = 60.0, odf_size: int = 300) -> None:
        self.btrack_fps = btrack_fps
        self.odf_size = odf_size
        self.templates: Dict[float, np.ndarray] = {}

        buffer_indices = np.arange(self.odf_size)
        self.const_part = buffer_indices - (self.odf_size - 1)

    def get_template(self, bpm_val: float) -> np.ndarray:
        bpm_key = round(float(bpm_val), 2)
        if bpm_key in self.templates:
            return self.templates[bpm_key]

        tau_val = 60.0 * self.btrack_fps / bpm_key
        p_max = max(1, int(np.ceil(tau_val)))

        p_arr = np.arange(p_max)[:, None]
        phase_float = (self.const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val

        # Sharp Triangle Pulse
        beat_dist = np.minimum(norm_phi, 1.0 - norm_phi)
        template_vals = np.full((p_max, self.odf_size), -1.0)
        mask_beat = beat_dist < 0.1
        template_vals[mask_beat] = 1.0 - (beat_dist[mask_beat] / 0.1)

        template_mean = np.mean(template_vals, axis=1, keepdims=True)
        template_centered = template_vals - template_mean
        template_std = np.sqrt(np.sum(template_centered ** 2, axis=1, keepdims=True)) + 1e-6

        # Pre-normalized template for rapid matrix multiplication
        normalized_template = template_centered / template_std
        self.templates[bpm_key] = normalized_template
        return normalized_template


# =====================================================================
# TEMPLATE EVALUATION FUNCTIONS
# =====================================================================

def evaluate_specific_bpms(
    odf_buffer: np.ndarray,
    candidate_bpms: List[float],
    template_bank: FastTemplateBank,
    decay_curve: np.ndarray,
    config: Optional[RhythmConfig] = None
) -> Tuple[float, float, int]:
    """Heavy Judge: Evaluates candidate BPMs and scores them with a human prior."""
    cfg = config or RhythmConfig()

    weighted_buffer = odf_buffer * decay_curve
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered ** 2)) + 1e-6

    best_score_pearson = -float('inf')
    best_bpm_pearson = candidate_bpms[0] if candidate_bpms else 120.0
    best_phase_idx_pearson = 0

    for bpm_val in candidate_bpms:
        if not (cfg.bpm_min <= bpm_val <= cfg.bpm_max):
            continue

        normalized_template = template_bank.get_template(bpm_val)

        # O(1) Vectorized Pearson Correlation via Dot Product
        p_scores_pearson = (normalized_template @ buffer_centered) / buffer_std

        # Human Prior centered around configured center BPM
        human_prior = 0.5 + 0.5 * np.exp(
            -0.5 * ((bpm_val - cfg.human_prior_center) / cfg.human_prior_sigma) ** 2
        )
        max_idx = int(np.argmax(p_scores_pearson))
        weighted_score = float(p_scores_pearson[max_idx] * human_prior)

        if weighted_score > best_score_pearson:
            best_score_pearson = weighted_score
            best_bpm_pearson = bpm_val
            best_phase_idx_pearson = max_idx

    return best_bpm_pearson, best_score_pearson, best_phase_idx_pearson


def class_based_phase_sweep(
    odf_buffer: np.ndarray,
    class_evals: np.ndarray,
    template_bank: FastTemplateBank,
    decay_curve: np.ndarray,
    config: Optional[RhythmConfig] = None
) -> Tuple[float, float, int]:
    """Fast Scout: Sweeps logarithmic tempo classes to identify dominant rhythm."""
    cfg = config or RhythmConfig()

    weighted_buffer = odf_buffer * decay_curve
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered ** 2)) + 1e-6

    best_overall_score = -float('inf')
    best_overall_class = float(class_evals[0] % 1.0) if len(class_evals) > 0 else 0.0
    best_phase_idx = 0

    for class_val in class_evals:
        c = float(class_val % 1.0)
        base_bpm = 60.0 * (2.0 ** c)
        eval_bpm = base_bpm if base_bpm >= 90.0 else base_bpm * 2.0

        normalized_template = template_bank.get_template(eval_bpm)
        p_scores = (normalized_template @ buffer_centered) / buffer_std

        human_prior = 0.5 + 0.5 * np.exp(
            -0.5 * ((eval_bpm - cfg.human_prior_center) / cfg.human_prior_sigma) ** 2
        )
        max_idx = int(np.argmax(p_scores))
        tau_max_score = float(p_scores[max_idx] * human_prior)

        if tau_max_score > best_overall_score:
            best_overall_score = tau_max_score
            best_overall_class = c
            best_phase_idx = max_idx

    return best_overall_class, best_overall_score, best_phase_idx


# =====================================================================
# AUDIO ANALYZER CORE CLASS
# =====================================================================

class AudioAnalyzer:
    """
    Core algorithmic analyzer for beat tracking and structural event detection.
    
    Maintains a 5-second look-ahead buffer, back-projects future phase estimates
    to speaker playback time, and drives a continuous mechanical flywheel.
    """

    def __init__(
        self,
        ingestion: AudioIngestion,
        infos: Dict[str, Any],
        config: Optional[RhythmConfig] = None
    ) -> None:
        self.ingestion = ingestion
        self.config = config if config is not None else RhythmConfig()

        self.hardware_latency = float(infos.get("latency", 0.0))
        self.decay_base = float(infos.get("decay_base", 0.98))
        self.lookahead_seconds = float(infos.get("fakeDelay", 5.0))
        self.btrack_fps = 60.0

        # Subsystems
        self.novelty_detector = StructuralNoveltyDetector(
            nb_fft_bands=self.ingestion.nb_of_fft_band,
            config=self.config
        )

        # 5-second ODF Look-Ahead Buffer (~300 frames at 60fps)
        self.odf_buffer_size = max(60, int(self.lookahead_seconds * self.btrack_fps))
        self.odf_buffer = np.zeros(self.odf_buffer_size)
        self.decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, self.odf_buffer_size))

        # Vectorized template bank
        self.template_bank = FastTemplateBank(btrack_fps=self.btrack_fps, odf_size=self.odf_buffer_size)

        # Flywheel & Beat State (at Speaker Time T_speaker)
        self.speaker_phase = 0.0
        self.bpm = 120.0
        self.long_term_class = bpm_to_class(120.0)
        self.confidence_score = 0.0
        self.flywheel_status = "coasting"
        self.time_since_sweep = 0.0

        self.beat_count = 0
        self.last_beat_time = time.time()

        # Per-frame event flags
        self.is_beat = False
        self.is_real_beat = False
        self.is_dropped_beat = False
        self.current_beat_tag = "Bass/Kick"

        # Onset & Peak Detection buffers
        self.peak_sensitivity = np.ones(self.ingestion.nb_of_fft_band) * 1.8
        self.peak_times = np.zeros(self.ingestion.nb_of_fft_band)
        self.band_peak = np.zeros(self.ingestion.nb_of_fft_band, dtype=int)
        self.band_flux = np.zeros(self.ingestion.nb_of_fft_band)
        self.prev_fft_band_values = np.zeros(self.ingestion.nb_of_fft_band)
        self.smoothed_flux = np.zeros(self.ingestion.nb_of_fft_band)
        self.rolling_flux_baseline = 0.0

        # Vocals tracking (stub / planned)
        self.vocals_present = False

    # ==========================================
    # PROPERTIES & FACADES
    # ==========================================

    @property
    def beat_phase(self) -> float:
        """Normalized fractional phase [0.0, 1.0) of the current beat at speaker time."""
        return float(self.speaker_phase)

    @property
    def standalone_phase(self) -> float:
        """Alias for beat_phase for backward compatibility."""
        return float(self.speaker_phase)

    @property
    def standalone_bpm(self) -> float:
        """Alias for bpm for backward compatibility."""
        return float(self.bpm)

    # --- Structural Novelty Delegation Properties ---
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

    @property
    def silence_frames(self) -> int:
        return self.novelty_detector.silence_frames

    @property
    def song_changes_times(self) -> List[float]:
        return self.novelty_detector.song_changes_times

    @property
    def structural_changes_times(self) -> List[float]:
        return self.novelty_detector.structural_changes_times

    # ==========================================
    # STRUCTURAL NOVELTY DELEGATION
    # ==========================================

    def update_structural_novelty(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """Delegates structural novelty calculation to StructuralNoveltyDetector."""
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

    # ==========================================
    # SPECTRAL ONSETS & ANTICIPATION FLYWHEEL
    # ==========================================

    def _compute_spectral_flux(self, current_time: float, fps_ratio: float) -> np.ndarray:
        """Calculates positive spectral flux, smoothed flux, and adaptive peak thresholds."""
        flux = np.maximum(0.0, self.ingestion.fft_band_values - self.prev_fft_band_values)
        self.band_flux = flux
        self.prev_fft_band_values = np.copy(self.ingestion.fft_band_values)

        flux_retention = self.config.flux_retention_base ** fps_ratio
        self.smoothed_flux = np.where(
            self.smoothed_flux < 1.0,
            flux,
            flux_retention * self.smoothed_flux + (1 - flux_retention) * flux
        )

        noise_floor = np.maximum(
            self.config.noise_floor_min,
            self.ingestion.band_means * self.config.noise_floor_ratio
        )
        variance_threshold = (self.smoothed_flux * self.peak_sensitivity) + noise_floor

        is_peak = (flux > variance_threshold) & (
            current_time > self.peak_times + self.config.delta_time_peak
        )
        self.band_peak = is_peak.astype(int)
        self.peak_times = np.where(is_peak, current_time, self.peak_times)

        self.peak_sensitivity = np.where(
            is_peak,
            np.minimum(self.peak_sensitivity + 1.0, self.config.peak_sensitivity_max),
            np.maximum(self.peak_sensitivity - (0.006 * fps_ratio), self.config.peak_sensitivity_min)
        )
        return flux

    def _ingest_odf_buffer(self, flux: np.ndarray) -> bool:
        """Ingests multi-band weighted flux into the 5-second ODF lookahead buffer."""
        if len(flux) >= 8:
            custom_flux = float(2.0 * np.sum(flux[0:2]) + 0.5 * np.sum(flux[-2:]))
        elif len(flux) >= 2:
            custom_flux = float(2.0 * np.sum(flux[0:2]))
        else:
            custom_flux = float(np.sum(flux))

        self.odf_buffer[:-1] = self.odf_buffer[1:]
        self.odf_buffer[-1] = custom_flux

        decay = self.config.rolling_flux_decay
        self.rolling_flux_baseline = decay * self.rolling_flux_baseline + (1.0 - decay) * custom_flux
        is_strong_peak = custom_flux > (
            self.rolling_flux_baseline * self.config.strong_peak_multiplier + 0.1
        )
        return is_strong_peak

    def _run_oracle_sweep(self, dt: float, is_strong_peak: bool) -> None:
        """Runs the Fast Scout and Heavy Judge to track tempo and back-project phase."""
        self.time_since_sweep += dt
        if not (is_strong_peak or self.time_since_sweep >= self.config.sweep_interval):
            return

        if self.beat_count < 4 or self.confidence_score < self.config.moderate_confidence_threshold:
            class_evals = np.arange(0.0, 1.0, self.config.coarse_class_step)
        else:
            rad = self.config.fine_class_radius
            class_evals = np.arange(
                self.long_term_class - rad,
                self.long_term_class + rad + 0.001,
                self.config.coarse_class_step
            )

        best_class, sweep_score, scout_phase_idx = class_based_phase_sweep(
            self.odf_buffer, class_evals, self.template_bank, self.decay_curve, self.config
        )
        min_d, aligned_class = harmonic_alignment(best_class, self.long_term_class)

        candidates = class_to_bpm_candidates(aligned_class)
        best_bpm, score_pearson, judge_phase_idx = evaluate_specific_bpms(
            self.odf_buffer, candidates, self.template_bank, self.decay_curve, self.config
        )

        self.confidence_score = score_pearson

        if score_pearson >= self.config.moderate_confidence_threshold:
            self.flywheel_status = "locked"
            self.long_term_class = bpm_to_class(best_bpm)
            self.bpm = best_bpm
            self.time_since_sweep = 0.0

            tau_val = 60.0 * self.btrack_fps / self.bpm
            ingest_phase = (judge_phase_idx % tau_val) / tau_val

            # Back-project to Speaker Time T_speaker
            total_delay = (
                self.lookahead_seconds
                + self.ingestion.dynamic_audio_latency
                + self.hardware_latency
            )
            latency_phase = (self.bpm / 60.0) * total_delay
            target_speaker_phase = (ingest_phase - latency_phase) % 1.0

            phase_err = (target_speaker_phase - self.speaker_phase + 0.5) % 1.0 - 0.5

            # Smart Anticipation Soft-Snap
            snap_ratio = (
                self.config.high_snap_ratio
                if score_pearson > self.config.high_confidence_threshold
                else self.config.moderate_snap_ratio
            )
            self.speaker_phase = (self.speaker_phase + snap_ratio * phase_err) % 1.0
        else:
            self.flywheel_status = "coasting"

    def _advance_flywheel(self, current_time: float, dt: float) -> None:
        """Advances continuous speaker flywheel phase and commits beat triggers & classification."""
        phase_increment = (self.bpm / 60.0) * dt
        self.speaker_phase += phase_increment

        if self.speaker_phase >= 1.0:
            self.speaker_phase -= 1.0
            self.beat_count += 1
            self.is_beat = True
            self.last_beat_time = current_time

            # Validate physical presence: Check local ODF energy at speaker time window (indices 0..6)
            local_energy = float(np.max(self.odf_buffer[0:7]))
            if (
                local_energy > (self.config.real_beat_baseline_ratio * self.rolling_flux_baseline)
                or local_energy > self.config.real_beat_energy_floor
            ):
                self.is_real_beat = True
                self.is_dropped_beat = False
            else:
                self.is_real_beat = False
                self.is_dropped_beat = True

            # Transient Frequency-Band Classification
            if len(self.band_flux) >= 8:
                b_val = float(np.sum(self.band_flux[0:2]))
                m_val = float(np.sum(self.band_flux[2:6]))
                h_val = float(np.sum(self.band_flux[6:8]))
                if b_val >= m_val and b_val >= h_val:
                    self.current_beat_tag = "Bass/Kick"
                elif m_val >= b_val and m_val >= h_val:
                    self.current_beat_tag = "Snare/Mid"
                else:
                    self.current_beat_tag = "Hi-hat/Cymbal"
            else:
                self.current_beat_tag = "Bass/Kick"

    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """
        Calculates positive spectral flux, ingests into the 5-second look-ahead buffer,
        runs the Oracle predictive phase sweep, and advances the continuous speaker flywheel.
        """
        # 1. Reset per-frame triggers
        self.is_beat = False
        self.is_real_beat = False
        self.is_dropped_beat = False

        # 2. Pipeline stages
        flux = self._compute_spectral_flux(current_time, fps_ratio)
        is_strong_peak = self._ingest_odf_buffer(flux)
        self._run_oracle_sweep(dt, is_strong_peak)
        self._advance_flywheel(current_time, dt)
