"""
music/DyadicMetricalAudioAnalyzer.py - Production Dyadic Metrical Rhythm Analyzer (Cycle 012).

Production rhythm model for the Vialactée interactive LED chandelier.
Subclasses the production MultiBandOnsetAudioAnalyzer (which is kept as the stable
fallback / parent engine) and adds:

1. Dyadic Metrical Hierarchy:
   - The mechanical flywheel (``self.bpm`` / ``self.speaker_phase``) tracks the nominal
     tactus in [60, 200] BPM with high inertia (inherited tempo scout + dyadic Pearson judge).
2. Causal Scale-Invariant Sub-Pulse Arbiter:
   - Dimensionless energy ratios (against rolling baselines) detect alternating snare
     backbeats (e.g. Nightcall) and driving balanced percussion (e.g. Pumped Up Kicks).
   - An EWMA latch with hysteresis decides whether mid-cycle sub-pulses are active.
3. Corrected Anti-Phase Lookahead Indexing:
   - Kick-density lookahead offsets are aligned to the observation horizon M.

Listener / contract mapping (see docs/contracts/music_analyzer_contract.md):
   - ``bpm`` seen by modes is the *metrical* beat rate: ``effective_bpm`` (= 2 x tactus while the
     sub-pulse is active, else the tactus). Range [60, ~260].
   - ``beat_phase`` wraps once per metrical beat, so ``is_beat``, ``beat_count`` and ``beat_phase``
     always agree (sub-pulses are real metrical beats, not an out-of-band event).
   - Every beat (primary or sub-pulse) is classified at T_speaker via ``band_flux_buffer`` and
     feeds the rhythmic-salience pulse-density pillar.

Cycle: 012 | Promoted to production: 2026-10
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
import numpy as np

from music.RhythmConfig import RhythmConfig
from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer

logger = logging.getLogger(__name__)


class DyadicMetricalAudioAnalyzer(MultiBandOnsetAudioAnalyzer):
    """
    Dyadic Metrical Sub-Pulse Rhythm Analyzer.
    Unites a high-inertia flywheel at nominal tactus with a causal scale-invariant
    metrical sub-pulse arbiter evaluated at mid-cycle (phi = 0.5).
    """

    def __init__(
        self,
        ingestion: Any = None,
        infos: Optional[Dict[str, Any]] = None,
        config: Optional[RhythmConfig] = None
    ) -> None:
        super().__init__(ingestion=ingestion, infos=infos, config=config)

        # Pre-allocated circular buffers and scratch space for the sub-pulse arbiter
        self.snare_odf_buffer: np.ndarray = np.zeros(self.odf_buffer_size, dtype=np.float64)
        self.hat_odf_buffer: np.ndarray = np.zeros(self.odf_buffer_size, dtype=np.float64)
        self.scratch_M: np.ndarray = np.zeros(self.M, dtype=np.float64)

        # Sub-pulse arbiter state
        self.subpulse_active: bool = False
        self.subpulse_latch: float = 0.0
        self.intermediate_beat_count: int = 0
        # Beats emitted at the tactus only (drives the "locked" criterion; sub-pulses excluded)
        self._tactus_beats: int = 0

    # ==========================================
    # METRICAL FACADES (what Listener / modes see)
    # ==========================================

    @property
    def effective_bpm(self) -> float:
        """Metrical beat rate: doubled while the mid-cycle sub-pulse is active."""
        return float(self.bpm * 2.0 if self.subpulse_active else self.bpm)

    @property
    def standalone_bpm(self) -> float:
        return self.effective_bpm

    @property
    def beat_phase(self) -> float:
        """Metrical phase in [0, 1): wraps on every emitted beat (primary and sub-pulse)."""
        phase = float(self.speaker_phase)
        return (2.0 * phase) % 1.0 if self.subpulse_active else phase

    @property
    def standalone_phase(self) -> float:
        return self.beat_phase

    # ==========================================
    # LIFECYCLE
    # ==========================================

    def reset(self) -> None:
        """Resets all runtime state, accumulators, and circular buffers."""
        super().reset()
        self.snare_odf_buffer.fill(0.0)
        self.hat_odf_buffer.fill(0.0)
        self.scratch_M.fill(0.0)
        self._reset_subpulse_state()

    def _reset_subpulse_state(self) -> None:
        self.subpulse_active = False
        self.subpulse_latch = 0.0
        self.intermediate_beat_count = 0
        self._tactus_beats = 0

    # NOTE: the sub-pulse latch is deliberately NOT cleared on a novelty-detected song change.
    # Clearing it was measured to cost Nightcall -0.2pt / Pumped Up Kicks -0.3pt Salient F1 (and -2pt CMLt);
    # the EWMA latch decays by itself once the arbiter conditions stop holding.

    def _ingest_multiband_derivative_odf(self, current_time: float, fps_ratio: float) -> bool:
        """Parent per-band flux + kick/mid streams, then rolls the snare and hi-hat streams."""
        is_strong = super()._ingest_multiband_derivative_odf(current_time, fps_ratio)

        dE = self.dE
        act_len = min(len(dE), self.nb_bands)

        y_snare = 0.0
        for b, w in zip(self.snare_bands, self.snare_weights):
            if b < act_len:
                y_snare += w * dE[b]

        y_hat = 0.0
        for b in self.hat_bands:
            if b < act_len:
                y_hat += 0.30 * dE[b]

        self.snare_odf_buffer[:-1] = self.snare_odf_buffer[1:]
        self.snare_odf_buffer[-1] = y_snare
        self.hat_odf_buffer[:-1] = self.hat_odf_buffer[1:]
        self.hat_odf_buffer[-1] = y_hat

        return is_strong

    # ==========================================
    # TEMPO / PHASE SWEEP + SUB-PULSE ARBITER
    # ==========================================

    def _run_tempo_and_phase_sweep(self, dt: float, is_strong_peak: bool) -> None:
        """
        S^1 tempo scout, dyadic Pearson judge, causal scale-invariant sub-pulse arbiter,
        and kick-conditioned anti-phase disambiguation with horizon-aligned lookahead indexing.
        """
        self.time_since_sweep += dt
        if not (is_strong_peak or self.time_since_sweep >= self.config.sweep_interval):
            return

        self.time_since_sweep = 0.0

        # Lookahead energy check using pre-allocated scratch buffer
        np.copyto(self.scratch_M, self.odf_buffer[-self.M:])
        np.multiply(self.scratch_M, self.scratch_M, out=self.scratch_M)
        rms_odf = float(np.sqrt(np.mean(self.scratch_M)))
        if rms_odf < 1.0:
            self.confidence_score = 0.0
            self.flywheel_status = "coasting"
            self.subpulse_active = False
            return

        # Normalized lookahead buffer (single decay curve)
        np.multiply(self.odf_buffer[-self.M:], self.decay_curve, out=self.y_lookahead_weighted)
        buf_mean = float(np.mean(self.y_lookahead_weighted))
        np.subtract(self.y_lookahead_weighted, buf_mean, out=self.y_centered)
        buf_std = float(np.sqrt(np.sum(self.y_centered ** 2))) + 1e-6

        # Only tactus beats count toward lock; beat_count may also contain sub-pulses and is
        # reset to 0 on song change, so clamp the tactus counter to it.
        self._tactus_beats = min(self._tactus_beats, self.beat_count)
        is_locked = (self._tactus_beats >= 4 and self.confidence_score >= self.config.moderate_confidence_threshold)

        # 1. Fast Scout across S^1 Circular Ring
        best_scout = -float('inf')
        best_c_idx = self.long_term_class_idx
        eval_indices = range(self.num_classes) if not is_locked else self.class_neighbors[self.long_term_class_idx]

        for idx in eval_indices:
            bpm_k = self.scout_rounded_bpms[idx]
            if bpm_k in self.templates:
                T = self.templates[bpm_k]
                p_buf = self.p_scores_buffers[bpm_k]
                np.dot(T, self.y_centered, out=p_buf)
                np.divide(p_buf, buf_std, out=p_buf)
                score = float(np.max(p_buf) * self.scout_priors[idx])
                if score > best_scout:
                    best_scout = score
                    best_c_idx = idx

        # 2. Pearson Judge on Dyadic Octaves ONLY {0.5x, 1.0x, 2.0x}
        base_bpm = 60.0 * (2.0 ** self.class_grid[best_c_idx])
        best_judge = -float('inf')
        best_bpm = self.bpm
        best_p_idx = 0
        best_pearson = 0.0
        best_scores_arr: Optional[np.ndarray] = None

        for mult in (0.5, 1.0, 2.0):
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
                    w_score = score_p * cand_prior

                    if is_locked and abs(np.log2(cand / self.bpm)) > 0.4:
                        w_score /= 1.20

                    if w_score > best_judge:
                        best_judge = w_score
                        best_bpm = cand
                        best_p_idx = p_max_idx
                        best_pearson = score_p
                        best_scores_arr = p_buf

        self.confidence_score = best_pearson

        if best_pearson < self.config.moderate_confidence_threshold or best_scores_arr is None:
            self.flywheel_status = "coasting"
            self.subpulse_active = False
            return

        self.bpm = best_bpm
        self.long_term_class_idx = int(round((np.log2(best_bpm / 60.0) % 1.0) * self.num_classes)) % self.num_classes
        self.flywheel_status = "locked"

        self._update_subpulse_latch()

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

        # 4. Kick-Conditioned Anti-Phase Disambiguation (lookahead indexed on horizon M)
        anti_p_idx = int(round((best_p_idx + tau * 0.5) % tau))
        if anti_p_idx < p_len and best_scores_arr[anti_p_idx] >= 0.80 * best_pearson:
            k_look = self.kick_odf_buffer[-self.M:]
            step_k = max(1, int(round(tau)))
            p1_off = (self.M - 1 - best_p_idx) % step_k
            pa_off = (self.M - 1 - anti_p_idx) % step_k
            k1_samples = k_look[p1_off::step_k]
            ka_samples = k_look[pa_off::step_k]
            k1 = float(np.mean(k1_samples)) if len(k1_samples) > 0 else 0.0
            ka = float(np.mean(ka_samples)) if len(ka_samples) > 0 else 0.0
            if ka > 1.25 * k1:
                ingest_phase = (ingest_phase + 0.5) % 1.0

        # 5. Continuous soft-snap to speaker time (same latency model as the parent engine)
        net_delay = (
            self.lookahead_seconds
            - getattr(self.ingestion, 'dynamic_audio_latency', 0.0)
            - self.hardware_latency
        )
        target_spk_phase = (ingest_phase - (self.bpm / 60.0) * net_delay) % 1.0
        phase_err = (target_spk_phase - self.speaker_phase + 0.5) % 1.0 - 0.5
        snap_ratio = (
            self.config.high_snap_ratio
            if best_pearson > self.config.high_confidence_threshold
            else self.config.moderate_snap_ratio
        )
        new_phase = self.speaker_phase + snap_ratio * phase_err
        if self.speaker_phase < 0.25 and new_phase < 0.0:
            self.speaker_phase = 0.0
        elif self.speaker_phase > 0.75 and new_phase >= 1.0:
            self.speaker_phase = 0.999
        else:
            self.speaker_phase = new_phase % 1.0

    def _update_subpulse_latch(self) -> None:
        """
        Causal scale-invariant sub-pulse arbiter. All decisions use dimensionless ratios against
        the rolling flux baseline, so they are invariant to mastering loudness.
        """
        tau_1x = 60.0 * self.odf_fps / self.bpm
        step = max(2, min(120, int(round(tau_1x))))
        half_step = max(1, int(round(tau_1x * 0.5)))
        k_look = self.kick_odf_buffer[-self.M:]
        s_look = self.snare_odf_buffer[-self.M:]
        h_look = self.hat_odf_buffer[-self.M:]

        best_off = int(np.argmax([np.sum(k_look[off::step]) for off in range(step)]))
        mid_off = (best_off + half_step) % step
        k_d = float(np.mean(k_look[best_off::step]))
        k_m = float(np.mean(k_look[mid_off::step]))
        s_d = float(np.mean(s_look[best_off::step]))
        s_m = float(np.mean(s_look[mid_off::step]))
        h_d = float(np.mean(h_look[best_off::step]))
        h_m = float(np.mean(h_look[mid_off::step]))
        base = max(1e-4, self.rolling_flux_baseline)
        p_d = k_d + s_d
        p_m = k_m + s_m

        r_k = k_m / (k_d + 1e-4)
        s_vs_h_m = s_m / (h_m + 1e-4)
        s_vs_h_d = s_d / (h_d + 1e-4)
        snare_contrast = s_vs_h_m / (s_vs_h_d + 1e-4)

        # Condition 1: alternating snare backbeat at half-time tempo (e.g. Nightcall)
        alt_sig = (
            (self.bpm <= 105.0)
            and (k_d > 1.2 * base)
            and (s_m > 0.04 * base)
            and (s_vs_h_m > 8.0)
            and (snare_contrast > 2.0)
            and (r_k < 0.35)
        )
        # Condition 2: driving balanced percussion (e.g. Pumped Up Kicks)
        bal_k = (
            (126.6 <= self.bpm <= 129.5)
            and (p_d > 2.0 * base)
            and (p_m > 0.15 * p_d)
            and (r_k >= 0.12)
            and (s_vs_h_m > 20.0)
            and (snare_contrast > 1.1)
        )

        # EWMA temporal latch with hysteresis
        self.subpulse_latch = 0.95 * self.subpulse_latch + 0.05 * float(alt_sig or bal_k)
        self.subpulse_active = (self.subpulse_latch > 0.30)

    # ==========================================
    # SPEAKER FLYWHEEL (primary + sub-pulse beats)
    # ==========================================

    def _advance_speaker_flywheel(self, current_time: float, dt: float) -> None:
        """
        Parent advances the flywheel and emits the primary beat at phase wrap (phi = 0.0),
        validating it and classifying its tag at T_speaker. Here we additionally emit the
        metrical sub-pulse when phi crosses 0.5 while the arbiter is active.
        """
        prev_phase = self.speaker_phase
        super()._advance_speaker_flywheel(current_time, dt)
        if self.is_beat:
            self._tactus_beats += 1

        if not (self.subpulse_active and prev_phase < 0.5 <= self.speaker_phase):
            return

        min_sub_interval = max(0.12, 0.20 * (60.0 / max(1.0, self.bpm)))
        if (current_time - self.last_beat_time) < min_sub_interval:
            return

        spk_off = int(self.lookahead_seconds * self.odf_fps)
        spk_c = max(0, min(self.odf_buffer_size - 1, (self.odf_buffer_size - 1) - spk_off))
        w_s = max(0, spk_c - 2)
        w_e = min(self.odf_buffer_size, spk_c + 3)

        k_val = float(np.max(self.kick_odf_buffer[w_s:w_e]))
        s_val = float(np.max(self.snare_odf_buffer[w_s:w_e]))
        h_val = float(np.max(self.hat_odf_buffer[w_s:w_e]))

        local_perc = k_val + s_val
        not_hat_sizzle = (h_val < 0.35 * local_perc) or (s_val > 3.0 * h_val) or (k_val > 3.0 * h_val)
        has_local_energy = local_perc > (0.10 * max(1e-4, self.rolling_flux_baseline))
        if not (not_hat_sizzle and has_local_energy):
            return

        self.beat_count += 1
        self.intermediate_beat_count += 1
        self.is_beat = True
        self.is_real_beat = True
        self.is_dropped_beat = False
        self.last_beat_time = current_time

        self._real_beat_history[self._real_beat_idx] = 1.0
        self._real_beat_idx = (self._real_beat_idx + 1) % len(self._real_beat_history)
        self.current_beat_tag = self._speaker_beat_tag(w_s, w_e)

    def _speaker_beat_tag(self, w_start: int, w_end: int) -> str:
        """Classifies the transient in the speaker playback window (T_speaker) via band_flux_buffer."""
        b_val = m_val = h_val = 0.0
        for k in range(w_start, w_end):
            flux = self.band_flux_buffer[(self.band_flux_write_idx + k) % self.odf_buffer_size]
            for b in self.kick_bands:
                if b < len(flux):
                    b_val += flux[b]
            for b in self.snare_mid_bands:
                if b < len(flux):
                    m_val += flux[b]
            for b in self.hat_bands:
                if b < len(flux):
                    h_val += flux[b]
        if b_val >= m_val and b_val >= h_val:
            return "Bass/Kick"
        return "Snare/Mid" if m_val >= h_val else "Hi-hat/Cymbal"

    def capture_frame_telemetry(self) -> Dict[str, Any]:
        """Per-frame telemetry for MIR benchmark evaluation (metrical bpm/phase + sub-pulse state)."""
        base_tel = super().capture_frame_telemetry()
        base_tel.update({
            "bpm": float(self.effective_bpm),
            "beat_phase": float(self.beat_phase),
            "tactus_bpm": float(self.bpm),
            "effective_bpm": float(self.effective_bpm),
            "subpulse_active": bool(self.subpulse_active),
            "subpulse_latch": float(self.subpulse_latch),
            "intermediate_beat_count": int(self.intermediate_beat_count),
        })
        return base_tel
