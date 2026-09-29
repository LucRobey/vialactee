"""
research/experiments/models/PhaseInertiaAudioAnalyzer.py - Candidate Model for Cycle 003.

Author: Autonomous Rhythm Data Scientist & Audio DSP Engineer
Cycle: 003
Hypothesis: 
    Phase Inversion Upbeat traps and breakdown desynchronization in AudioAnalyzer
    stem from symmetric, un-damped phase soft-snapping (snap_ratio = 0.50) during
    transient dropouts and syncopated offbeat dominance. Introducing Metrical Phase Inertia
    (suppressing anti-phase phase jumps |phase_err| > 0.35 once beat tracking is established)
    and balanced mid-band snare reinforcement prevents 180° upbeat capture while maintaining
    sub-millisecond phase alignment and zero heap allocations at 60 FPS.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

from core.AudioAnalyzer import AudioAnalyzer, class_based_phase_sweep, evaluate_specific_bpms, class_to_bpm_candidates, bpm_to_class, harmonic_alignment
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioIngestion import AudioIngestion
from core.RhythmConfig import RhythmConfig


class PhaseInertiaAudioAnalyzer(AudioAnalyzer):
    """
    PhaseInertiaAudioAnalyzer extends AudioAnalyzer with:
    1. Metrical Phase Inertia: Rejects catastrophic 180° anti-phase jumps (|phase_err| > 0.35)
       during breakdowns, syncopated offbeats, and temporary drum dropouts once locked.
    2. Balanced Snare/Kick ODF: Reinforces snare fundamental body (Bands 2-3) to maintain
       downbeat grid energy while attenuating offbeat hi-hat sizzle (Bands 6-7).
    3. Strict Zero-Allocation per-frame update loop complying with RPi 4/5 60 FPS constraints.
    """

    def __init__(
        self,
        ingestion: Optional[AudioIngestion] = None,
        infos: Optional[Dict[str, Any]] = None,
        config: Optional[RhythmConfig] = None
    ) -> None:
        cfg = config if config is not None else RhythmConfig()
        inf = infos if infos is not None else {}
        super().__init__(ingestion=ingestion, infos=inf, config=cfg)

        # Pre-allocated scratch scalar / phase buffers for zero heap allocation
        self.phase_err_threshold: float = 0.35
        self.inertia_min_beats: int = 4

    def _ingest_odf_buffer(self, flux: np.ndarray) -> bool:
        """
        Ingests balanced multi-band flux into the 5-second lookahead buffer.
        Reinforces kick (bands 0-1) and snare (bands 2-3) while moderating
        offbeat hi-hat transient energy (bands 6-7).
        """
        if len(flux) >= 8:
            # Kick (Bands 0-1) + Snare body/presence (Bands 2-3) + Low hi-hat (Bands 6-7)
            custom_flux = float(
                2.0 * flux[0] + 1.8 * flux[1] + 1.2 * flux[2] + 0.8 * flux[3] + 0.2 * flux[6] + 0.1 * flux[7]
            )
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
        """
        Runs Fast Scout and Heavy Judge with Metrical Phase Inertia.
        Prevents 180° anti-phase jumps when tracking is locked.
        """
        self.time_since_sweep += dt
        if not (is_strong_peak or self.time_since_sweep >= self.config.sweep_interval):
            return

        # Adaptive search radius
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

            tau_val = 60.0 * self.odf_fps / self.bpm
            ingest_phase = (judge_phase_idx % tau_val) / tau_val

            # Back-project to Speaker Time T_speaker
            total_delay = (
                self.lookahead_seconds
                + self.ingestion.dynamic_audio_latency
                + self.hardware_latency
            )
            latency_phase = (self.bpm / 60.0) * total_delay
            target_speaker_phase = (ingest_phase - latency_phase) % 1.0

            # Shortest angular phase distance on S1 circle [-0.5, +0.5)
            phase_err = (target_speaker_phase - self.speaker_phase + 0.5) % 1.0 - 0.5

            # METRICAL PHASE INERTIA:
            # If the flywheel has already locked beats and the target phase is in the
            # opposite half of the cycle (|phase_err| > 0.35), reject the 180° flip!
            # This protects against upbeat capture during drum breakdowns and offbeat syncopations.
            if self.beat_count >= self.inertia_min_beats and abs(phase_err) > self.phase_err_threshold:
                phase_err = 0.0

            snap_ratio = (
                self.config.high_snap_ratio
                if score_pearson > self.config.high_confidence_threshold
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
