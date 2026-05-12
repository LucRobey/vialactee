import time
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging
from collections import deque

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    def __init__(self, ingestion: Any, infos: Dict[str, Any]) -> None:
        self.ingestion = ingestion
        self.hardware_latency = infos.get("latency", 0.0)
        self.decay_base = infos.get("decay_base", 0.98)
        self.build_band_peaks()


    def build_band_peaks(self) -> None:
        # We start looking for peaks roughly 2.0 "standard deviations" above the exponential mean
        self.peak_sensitivity = np.ones(self.ingestion.nb_of_fft_band) * 2.0
        self.delta_time_peak = 0.15 #seconde
        self.peak_times = []
        self.band_peak = []
        self.band_flux = []
        for band_index in range(self.ingestion.nb_of_fft_band):
            self.peak_times.append(0.0)
            self.band_peak.append(0)
            self.band_flux.append(0.0)

        self.peak_times = np.array(self.peak_times)
        self.band_peak = np.array(self.band_peak)
        self.band_flux = np.array(self.band_flux)
        
        # BPM Anticipation Grid Variables
        self.bpm = 90.0
        self.bpm_trust = 0.0
        self.binary_trust = 0.0
        self.last_beat_time = time.time()
        self.last_update_time = time.time()
        self.beat_count = 0
        self.beat_phase = 0.0
        
        # New Internal Hybrid Tracker Data Arrays
        self.standalone_phase = 0.0
        self.standalone_bpm = 120.0
        self.standalone_beat_count = 0
        self.last_standalone_beat_count = 0
        self.last_standalone_phase = 0.0
        self.standalone_sub_beat_locked = -1
        self.time_since_sweep = 0.0
        self.future_queue = deque()
        self.lookahead_seconds = 5.0
        
        # --- BTrack Internal Arrays ---
        # Assuming 60 FPS update rate
        self.btrack_fps = 60.0
        self.odf_buffer_size = 512 # ~8.5 seconds of history
        self.odf_buffer = np.zeros(self.odf_buffer_size)
        
        # Tempo limits (60 BPM to 180 BPM)
        self.tau_min = int(self.btrack_fps * 60.0 / 180.0)
        self.tau_max = int(self.btrack_fps * 60.0 / 60.0)
        
        # Gaussian weighting around ideal 120 BPM in actual BPM space
        taus = np.arange(self.tau_min, self.tau_max)
        bpms = 60.0 * self.btrack_fps / taus
        self.tempo_weights = np.exp(-0.5 * ((bpms - 120.0) / 20.0)**2)
        
        self.btrack_tau = 30 # Default 120 BPM
        self.previous_best_p = 0
        
        # --- Structural Novelty & Event Trigger Variables ---
        self.stm_timbre = np.zeros(self.ingestion.nb_of_fft_band)
        self.ltm_timbre = np.zeros(self.ingestion.nb_of_fft_band)
        self.stm_power = 0.0
        self.ltm_power = 0.0
        self.stm_weight = 0.02   # ~1.5s smoothing at 60fps
        self.ltm_weight = 0.0015 # ~6.0s smoothing at 60fps
        
        self.novelty_lm = 0.5
        self.novelty_gm = 0.5
        self.asserved_novelty = 0.0
        self.combined_novelty = 0.0
        
        self.SONG_NOVELTY_ASSERVED_TH = 0.8
        
        self.song_changes_times = []
        self.structural_changes_times = []
        self.last_structural_change_time = 0.0
        self.STRUCTURAL_COOLDOWN_SECONDS = 20.0
        
        self.silence_frames = 0
        self.SILENCE_THRESHOLD_FRAMES = int(1.5 * 60) # ~90 frames
        
        self.long_term_bpm = 120.0
        self.ltm_trust = 10.0
        self.bpm_jump_threshold = 8.0
        
        # Real-time event consumption flags (True for exactly one frame!)
        self.is_verse_chorus_change = False
        self.is_song_change = False
        
        # Acapella/Vocal breakdown tracking
        self.vocals_present = False
        self.acapella_events_times = []
        self.last_acapella_time = 0.0
        self.ACAPELLA_COOLDOWN_SECONDS = 5.0
        
        
    def update_structural_novelty(self, current_time: float, dt: float, fps_ratio: float) -> None:
        # current_time from param
        
        # 1. Reset boolean triggers from last frame
        self.is_verse_chorus_change = False
        self.is_song_change = False
        
        # 2. Extract current state
        current_timbre = self.ingestion.band_proportion
        current_power = self.ingestion.smoothed_total_power
        
        # 3. Update Short-Term and Long-Term Memory (STM/LTM)
        stm_retention = 0.98 ** fps_ratio
        ltm_retention = 0.9985 ** fps_ratio
        
        self.stm_timbre = stm_retention * self.stm_timbre + (1 - stm_retention) * current_timbre
        self.ltm_timbre = ltm_retention * self.ltm_timbre + (1 - ltm_retention) * current_timbre
        
        self.stm_power = stm_retention * self.stm_power + (1 - stm_retention) * current_power
        self.ltm_power = ltm_retention * self.ltm_power + (1 - ltm_retention) * current_power
        
        # 4. Calculate Euclidean Distance (Timbral) and Relative Distance (Power)
        timbral_novelty = np.linalg.norm(self.stm_timbre - self.ltm_timbre)
        power_novelty = np.abs(self.stm_power - self.ltm_power) / (self.ltm_power + 1.0)
        
        # 5. Combined Novelty Score
        self.combined_novelty = timbral_novelty + (power_novelty * 0.2)
        
        # === Local & Global Max Envelope (Asserved Normalization) ===
        if self.combined_novelty >= self.novelty_lm:
            self.novelty_lm = self.combined_novelty
        else:
            self.novelty_lm = max(0.15, self.novelty_lm * (0.9995 ** fps_ratio))
            
        passed_gm = self.combined_novelty > self.novelty_gm
        if self.combined_novelty >= self.novelty_gm:
            self.novelty_gm = 1.01 * self.combined_novelty
        else:
            self.novelty_gm *= 1 + (0.005 * fps_ratio) * ((self.novelty_lm / max(0.001, self.novelty_gm)) - 0.9)
            
        safe_gm = max(0.01, self.novelty_gm)
        target_asserved = self.combined_novelty / safe_gm
        self.asserved_novelty += min(1.0, 0.4 * fps_ratio) * (target_asserved - self.asserved_novelty)
        
        # === A. Detect Seamless DJ Crossfade (Song Change Type I) ===
        if self.asserved_novelty > self.SONG_NOVELTY_ASSERVED_TH:
            if len(self.song_changes_times) == 0 or (current_time - self.song_changes_times[-1]) > 20.0:
                self.song_changes_times.append(current_time)
                self.is_song_change = True
                
                # We no longer clear the future_queue here to allow the remaining 5 seconds 
                # of the previous song's beats to play out accurately.
                self.standalone_beat_count = 0
                self.last_standalone_beat_count = 0
                self.standalone_sub_beat_locked = -1
                self.standalone_phase = 0.0
                self.ingestion.band_means.fill(0.0)
                self.ingestion.smoothed_fft_band_values.fill(0.0)
                self.odf_buffer.fill(0.0)
                
                # Organic Shock Absorber limit
                self.novelty_gm = self.combined_novelty * 1.5 
                self.asserved_novelty = 0.0
                self.ltm_timbre = np.copy(self.stm_timbre)
                self.ltm_power = self.stm_power
                
        # === B. Detect Verse/Chorus Boundary ===
        elif passed_gm:
            if (current_time - self.last_structural_change_time) > self.STRUCTURAL_COOLDOWN_SECONDS:
                self.structural_changes_times.append(current_time)
                self.last_structural_change_time = current_time
                self.is_verse_chorus_change = True
                
                self.asserved_novelty = 0.0
                self.ltm_timbre = np.copy(self.stm_timbre)
                self.ltm_power = self.stm_power
                
        # === C. Song Change Detection (Silence Drop) ===
        if current_power < 5.0:
            self.silence_frames += 1
        else:
            self.silence_frames = 0
            
        if self.silence_frames > self.SILENCE_THRESHOLD_FRAMES:
            if len(self.song_changes_times) == 0 or (current_time - self.song_changes_times[-1]) > 5.0:
                self.song_changes_times.append(current_time)
                self.is_song_change = True
                
                # We no longer clear the future_queue here
                self.standalone_beat_count = 0
                self.last_standalone_beat_count = 0
                self.standalone_sub_beat_locked = -1
                self.standalone_phase = 0.0
                self.ingestion.band_means.fill(0.0)
                self.ingestion.smoothed_fft_band_values.fill(0.0)
                self.odf_buffer.fill(0.0)
                
                self.silence_frames = 0
                
    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """
        Spectral Flux onset detection.
        Calculates positive energy influx to find sharp transients.
        """
        if not hasattr(self, 'prev_fft_band_values'):
            self.prev_fft_band_values = np.zeros(self.ingestion.nb_of_fft_band)
        if not hasattr(self, 'smoothed_flux'):
            self.smoothed_flux = np.zeros(self.ingestion.nb_of_fft_band)
            self.peak_sensitivity = np.ones(self.ingestion.nb_of_fft_band) * 1.8
            
        # Spectral Flux: Positive difference between current frame and previous frame
        flux = np.maximum(0, self.ingestion.fft_band_values - self.prev_fft_band_values)
        self.band_flux = flux
        self.prev_fft_band_values = np.copy(self.ingestion.fft_band_values)
        
        # current_time from param
        
        # Smooth the flux to establish a dynamic baseline of recent transients
        flux_retention = 0.95 ** fps_ratio
        self.smoothed_flux = np.where(self.smoothed_flux < 1.0, 
                                      flux, 
                                      flux_retention * self.smoothed_flux + (1 - flux_retention) * flux)
        
        # A valid transient is significantly higher than the rolling average of transients.
        # Add a minor noise_floor derived from band_means to ignore silent noise crackles.
        noise_floor = np.maximum(10.0, self.ingestion.band_means * 0.05)
        variance_threshold = (self.smoothed_flux * self.peak_sensitivity) + noise_floor
        
        # Vectorized peak detection
        is_peak = (flux > variance_threshold) & (current_time > self.peak_times + self.delta_time_peak)
        
        self.band_peak = is_peak.astype(int)
        
        # Update peak times where peak detected
        self.peak_times = np.where(is_peak, current_time, self.peak_times)
        
        # Adjust sensitivity: up heavily on beat to prevent double-hits, down slowly otherwise
        self.peak_sensitivity = np.where(is_peak, 
                                         np.minimum(self.peak_sensitivity + 1.0, 4.0),
                                         np.maximum(self.peak_sensitivity - (0.006 * fps_ratio), 1.5))
                                         
        # --- PURE PYTHON BTRACK TEMPO & PHASE TRACKING ---
        # 1. Onset Detection Function (ODF) Aggregation
        # Multi-band weighting: favor bass (indices 0,1), suppress mids (3,4,5), favor cymbals/highs (6,7)
        band_weights = np.array([1.5, 1, 0.7, 0.2, 0, 0.1, 0.2, 0.5])
        if len(self.band_flux) == len(band_weights):
            weighted_flux = self.band_flux * band_weights
            gated_flux = np.where(is_peak, weighted_flux, 0.0)
        else:
            weighted_flux = self.band_flux[0:3]
            gated_flux = np.where(is_peak[0:3], weighted_flux, 0.0) # Safe fallback

        # 1a. Hard Onset Gating & Logarithmic Compression (Volume Decoupling)
        # We strictly block volume from bands that didn't mathematically hit an onset peak,
        # and compress the energy drastically to explicitly equalise 2000-volume kicks and 50-volume cymbals.
        energy = np.log1p(np.sum(gated_flux))
        
        # 2. Update ODF Ring Buffer
        self.odf_buffer[:-1] = self.odf_buffer[1:]
        self.odf_buffer[-1] = energy
        
        # 3. Autocorrelation (Finding the Tempo/BPM)
        # Centralize to remove DC offset and improve finding rhythmic periodicities
        centered_odf = self.odf_buffer - np.mean(self.odf_buffer)
        acf = np.correlate(centered_odf, centered_odf, mode='full')
        acf = acf[len(self.odf_buffer)-1:] # Extract only positive lags
        
        # UNBIASED ESTIMATOR:
        # A finite window autocorrelation inherently slopes downwards as a triangle.
        # We divide by the overlap length at each lag to flatten the baseline.
        overlap_lengths = np.arange(self.odf_buffer_size, 0, -1)
        unbiased_acf = acf / overlap_lengths
        
        # Multiply by Tempo Preference Weights
        weighted_acf = np.maximum(0, unbiased_acf[self.tau_min:self.tau_max]) * self.tempo_weights
        
        # Strictly look for LOCAL PEAKS to avoid sliding down the edge of the tau=0 mountain
        # Use 'inf' at boundaries so the very edges (like 180BPM) can never accidentally be considered "peaks"
        left = np.r_[float('inf'), weighted_acf[:-1]]
        right = np.r_[weighted_acf[1:], float('inf')]
        peaks_mask = (weighted_acf > left) & (weighted_acf > right)
        weighted_peaks = np.where(peaks_mask, weighted_acf, 0)
        
        if np.max(weighted_peaks) > 0:
            current_tau = 60.0 * self.btrack_fps / max(1.0, self.bpm)
            
            # --- HARMONIC & POLYRHYTHMIC FOLDING ---
            # Instead of punishing multipliers, we add their energy to the primary fundamental slower tempo!
            folded_peaks = np.copy(weighted_peaks)
            for i in range(len(weighted_peaks)):
                tau = self.tau_min + i
                
                # 1. Fold half-time (double tau) back into main
                if tau * 2 <= self.tau_max:
                    idx_double = int(tau * 2) - self.tau_min
                    if idx_double < len(weighted_peaks):
                        folded_peaks[i] += 0.5 * weighted_peaks[idx_double]
                        
                # 2. Fold double-time (half tau) back into main
                if tau / 2.0 >= self.tau_min:
                    idx_half = int(tau / 2.0) - self.tau_min
                    if idx_half >= 0:
                        folded_peaks[i] += 0.5 * weighted_peaks[idx_half]
                        
                # 3. Fold 1.5x polyrhythm / dotted rhythm (tau / 1.5) back into main (fundamental lower tempo)
                if tau / 1.5 >= self.tau_min:
                    idx_15 = int(tau / 1.5) - self.tau_min
                    if idx_15 >= 0 and idx_15 < len(weighted_peaks):
                        # Strong reward: 1.5x is extremely common in EDM and pop (triplets)
                        folded_peaks[i] += 0.6 * weighted_peaks[idx_15]
                        
            weighted_peaks = folded_peaks
                
            best_tau_idx = int(np.argmax(weighted_peaks))
            global_max_val = weighted_peaks[best_tau_idx]
            
            # Store the absolute global maximum BPM before applying local stubbornness
            self.global_target_bpm = 60.0 * self.btrack_fps / max(1.0, self.tau_min + best_tau_idx)
            
            # --- Check if there are peaks that agree with current BPM ---
            expected_idx = int(round(current_tau - self.tau_min))
            
            window = 3 # Margin of error in frames
            start_idx = max(0, expected_idx - window)
            end_idx = min(len(weighted_peaks), expected_idx + window + 1)
            
            if start_idx < end_idx:
                local_max_idx = start_idx + int(np.argmax(weighted_peaks[start_idx:end_idx]))
                local_max_val = weighted_peaks[local_max_idx]
                
                # If there's a peak nearby that is not too small (e.g. >50% of the absolute max),
                # we prefer it to avoid jumping abruptly to a different BPM
                if local_max_val > 0.5 * global_max_val:
                    best_tau_idx = local_max_idx
            
            # --- Sub-frame Parabolic Interpolation for smooth Target BPM ---
            val = weighted_acf[best_tau_idx]
            left_val = weighted_acf[max(0, best_tau_idx - 1)]
            right_val = weighted_acf[min(len(weighted_acf)-1, best_tau_idx + 1)]
            
            # offset = (left - right) / (2 * (left - 2*val + right))
            offset = 0.0
            divisor = 2.0 * (left_val - 2.0*val + right_val)
            if divisor != 0:
                offset = (left_val - right_val) / divisor
                offset = max(-1.0, min(1.0, offset))
                
            self.btrack_tau = self.tau_min + best_tau_idx + offset
            
            target_bpm = 60.0 * self.btrack_fps / max(1.0, self.btrack_tau)
            
            # We must never yank the BPM so violently that it breaks the PLL!
            # High trust -> absolute inertia (0.999), meaning rock-solid tempo.
            # Low trust -> smooth but bounded drift (0.992 minimum).
            base_inertia = max(0.992, self.decay_base + 0.012)
            decay_factor = min(0.9995, base_inertia + 0.007 * self.bpm_trust)
            self.bpm = decay_factor * self.bpm + (1.0 - decay_factor) * target_bpm
            
            baseline_variance = max(1e-4, unbiased_acf[0])
            self.binary_trust = min(1.0, np.max(weighted_peaks) / baseline_variance)
            
        # 4. Phase Alignment (Bipolar Pulse Template Cross-Correlation)
        # We find the exact phase offset by rolling the hand-drawn discrete wave template 
        # (with negative-mean penalty regions) across the entire 8.5 second buffer.
        tau_int = int(self.btrack_tau)
        
        # Build the discrete template for one beat cycle of length `tau_int`
        cycle_template = np.full(tau_int, -0.2)
        
        # [0.95, 1.05] -> 1.0 (Main Beat)
        w_main = max(1, int(tau_int * 0.05))
        for i in range(w_main + 1):
            cycle_template[i] = 1.0
            cycle_template[-i] = 1.0
            
        # [0.45, 0.55] -> 0.6 (Sub Beat / 8th note)
        w_sub = max(1, int(tau_int * 0.05))
        c_sub = int(tau_int * 0.5)
        for i in range(max(0, c_sub - w_sub), min(tau_int, c_sub + w_sub + 1)):
            cycle_template[i] = 0.6
            
        # [0.22, 0.28] and [0.72, 0.78] -> 0.3 (Sub-Sub Beats / 16th notes)
        w_ss = max(1, int(tau_int * 0.03))
        c_ss1 = int(tau_int * 0.25)
        c_ss2 = int(tau_int * 0.75)
        for i in range(max(0, c_ss1 - w_ss), min(tau_int, c_ss1 + w_ss + 1)):
            cycle_template[i] = 0.3
        for i in range(max(0, c_ss2 - w_ss), min(tau_int, c_ss2 + w_ss + 1)):
            cycle_template[i] = 0.3
            
        # Apply elastic exponential decay over the buffer history
        decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, self.odf_buffer_size))
        weighted_buffer = self.odf_buffer * decay_curve
        
        # Fully vectorized cross-correlation phase evaluation
        p_scores = np.zeros(tau_int)
        buffer_indices = np.arange(self.odf_buffer_size)
        for p in range(tau_int):
            # For offset `p`, map each frame in the buffer to its phase location inside the cycle_template
            phase_indices = (buffer_indices - (self.odf_buffer_size - 1 - p)) % tau_int
            p_scores[p] = np.sum(weighted_buffer * cycle_template[phase_indices])
            
        if np.max(p_scores) > 1e-4:
            best_p_idx = int(np.argmax(p_scores))
            
            # Sub-frame phase interpolation
            val_p = p_scores[best_p_idx]
            left_p = p_scores[(best_p_idx - 1) % tau_int]
            right_p = p_scores[(best_p_idx + 1) % tau_int]
            
            offset_p = 0.0
            div_p = 2.0 * (left_p - 2.0*val_p + right_p)
            if div_p != 0:
                offset_p = (left_p - right_p) / div_p
                offset_p = max(-1.0, min(1.0, offset_p))
                
            best_p = float(best_p_idx) + offset_p
            self.previous_best_p = best_p_idx
        else:
            # Silence/Freewheel: naturally count down the phase
            best_p = (self.previous_best_p - 1) % max(1, tau_int)
            self.previous_best_p = int(best_p)
        
        # 5. Continuous Freewheeling Phase & Hybrid Tracker
        dt = dt
        self.last_update_time = current_time
        
        self.time_since_sweep += dt
        if self.time_since_sweep >= 0.2: # Sweeps every 0.2 seconds
            coarse_bpm = self.standalone_bpm if (50 < self.standalone_bpm < 220) else 120.0
            
            total_latency = self.ingestion.dynamic_audio_latency + self.hardware_latency
            latency_phase_shift = (coarse_bpm / 60.0) * total_latency
            expected_p_phase = (self.standalone_phase - latency_phase_shift + 1.0) % 1.0
            
            # Only inject phase inertia if we have already confidently tracked at least a few beats
            inertia_param = expected_p_phase if self.standalone_beat_count > 5 else None
            
            precise_bpm, precise_phase = self.localized_continuous_phase_sweep(
                center_bpm=coarse_bpm, 
                search_radius=1.5, 
                step=0.1,
                expected_phase=inertia_param
            )
            
            # --- BPM Trust Song Change Logic ---
            current_trust = self.binary_trust
            bpm_retention = 0.9 ** fps_ratio
            self.long_term_bpm = bpm_retention * self.long_term_bpm + (1 - bpm_retention) * precise_bpm
            self.ltm_trust = bpm_retention * self.ltm_trust + (1 - bpm_retention) * current_trust
            
            bpm_divergence = np.abs(precise_bpm - self.long_term_bpm)
            
            if bpm_divergence > self.bpm_jump_threshold and current_trust < (self.ltm_trust * 0.6):
                if len(self.song_changes_times) == 0 or (current_time - self.song_changes_times[-1]) > 5.0:
                    self.song_changes_times.append(current_time)
                    self.is_song_change = True
                    
                    # We no longer clear the future_queue here
                    self.standalone_beat_count = 0
                    self.last_standalone_beat_count = 0
                    self.standalone_sub_beat_locked = -1
                    self.standalone_phase = 0.0
                    self.ingestion.band_means.fill(0.0)
                    self.ingestion.smoothed_fft_band_values.fill(0.0)
                    self.odf_buffer.fill(0.0)
                    
                    # Instantly accept the new tempo reality
                    self.long_term_bpm = precise_bpm
            # -----------------------------------
            
            self.standalone_bpm = precise_bpm
            total_latency = self.ingestion.dynamic_audio_latency + self.hardware_latency # Hardware/Buffer latency
            latency_phase_shift = (precise_bpm / 60.0) * total_latency
            target_phase = (precise_phase + latency_phase_shift) % 1.0
            
            # Eliminate tug-of-war: Hard reset onto the precise sweep if within temporal sanity
            phase_diff_sweep = (target_phase - self.standalone_phase + 0.5) % 1.0 - 0.5
            if abs(phase_diff_sweep) < 0.15:
                self.standalone_phase += phase_diff_sweep
                
            self.time_since_sweep = 0.0
            
        # Free-wheel phase advance
        phase_delta = (self.standalone_bpm / 60.0) * dt
        self.standalone_phase += phase_delta
        
        while self.standalone_phase >= 1.0:
            self.standalone_phase -= 1.0
            self.standalone_beat_count += 1
        while self.standalone_phase < 0.0:
            self.standalone_phase += 1.0
            self.standalone_beat_count -= 1
            
        is_beat = False
        is_sub_beat = False
        if self.standalone_beat_count > self.last_standalone_beat_count:
            is_beat = True
            self.last_standalone_beat_count = self.standalone_beat_count
            
        if self.last_standalone_phase < 0.5 and self.standalone_phase >= 0.5:
            if self.standalone_sub_beat_locked < self.last_standalone_beat_count:
                is_sub_beat = True
                self.standalone_sub_beat_locked = self.last_standalone_beat_count
                
        self.last_standalone_phase = self.standalone_phase
        
        # High res flux analog for real-time: decouple frequency bands
        bass_flux_val = np.sum(flux[0:2])
        treble_flux_val = np.sum(flux[6:8])
        
        self.future_queue.append({
            'timestamp': current_time,
            'bpm': self.standalone_bpm,
            'bass_flux': bass_flux_val,
            'treble_flux': treble_flux_val,
            'is_beat': is_beat,
            'is_sub_beat': is_sub_beat,
            'phase': self.standalone_phase,
            'beat_count': self.standalone_beat_count
        })
        
        # RIGID BEAT POPPING
        # Pop beats precisely when they are lookahead_seconds old
        best_p = 0
        while len(self.future_queue) > 0:
            time_diff = current_time - self.future_queue[0]['timestamp']
            
            if time_diff < self.lookahead_seconds:
                break
                
            popped = self.future_queue.popleft()
            self.bpm = popped['bpm']
            self.beat_phase = popped['phase']
            
            # The beat counters & triggers 
            if popped['is_beat']:
                self.beat_count += 1
                self.last_beat_time = current_time
            elif popped['is_sub_beat']:
                pass # You can use is_sub_beat trigger if Mode_master needs it

        self.previous_best_p = best_p

    def localized_continuous_phase_sweep(self, center_bpm: float, search_radius: float = 1.5, step: float = 0.1, expected_phase: Optional[float] = None) -> Tuple[float, float]:
        odf_size = len(self.odf_buffer)
        decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
        weighted_buffer = self.odf_buffer * decay_curve
        
        best_overall_score = -float('inf')
        best_overall_bpm = center_bpm
        best_overall_p = 0
        
        buffer_indices = np.arange(odf_size)
        bpm_evals = np.arange(max(50.0, center_bpm - search_radius), min(220.0, center_bpm + search_radius + step/2), step)
        
        btrack_fps = self.btrack_fps
        const_part = buffer_indices - (odf_size - 1)
        
        for bpm_val in bpm_evals:
            tau_val = 60.0 * btrack_fps / bpm_val
            p_max = int(np.ceil(tau_val))
            
            p_arr = np.arange(p_max)[:, None]
            phase_float = (const_part[None, :] + p_arr) % tau_val
            norm_phi = phase_float / tau_val 
            
            abs_phi = np.abs(norm_phi - 0.5)
            mask_high = abs_phi >= 0.475
            mask_medium = abs_phi <= 0.025
            
            template_vals = np.full((p_max, odf_size), -0.2)
            template_vals[mask_high] = 0.9 + 0.6 * (0.025 - (0.5 - abs_phi[mask_high]))
            template_vals[abs_phi <= 0.025] = 0.6 + 0.3 * (0.025-(abs_phi[mask_medium]))
            template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0
            
            p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1)
            
            # --- NEW: PHASE INERTIA LOGIC ---
            # If we have established momentum, heavily penalize severe phase jumps
            # Eliminates 180-degree phase inversions caused by loud hi-hats during drops.
            if expected_phase is not None:
                expected_p = (expected_phase * tau_val) % tau_val
                dist_p = np.minimum(np.abs(p_arr[:, 0] - expected_p), tau_val - np.abs(p_arr[:, 0] - expected_p))
                norm_dist = dist_p / tau_val
                
                # Strict 0.20 variance prevents "tug-of-war" snapping
                phase_inertia = np.exp(-0.5 * (norm_dist / 0.20)**2)
                p_scores = p_scores * (0.1 + 0.9 * phase_inertia)
            # --------------------------------
                
            tau_max_score = np.max(p_scores)
            best_p = np.argmax(p_scores)
            
            gaussian_weight = np.exp(-0.5 * ((bpm_val - center_bpm) / (search_radius * 1.5))**2)
            weighted_score = tau_max_score * (0.8 + 0.2 * gaussian_weight)
            
            if weighted_score > best_overall_score:
                best_overall_score = weighted_score
                best_overall_bpm = bpm_val
                best_overall_p = best_p
                
        optimal_tau = 60.0 * btrack_fps / best_overall_bpm
        precise_phase = best_overall_p / optimal_tau
        return best_overall_bpm, precise_phase
            
