import librosa
import numpy as np
import torchaudio
import torch
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# Import core infrastructure
import core.Listener as ListenerModule
from IPython.display import display, clear_output

def default_infos():
    return {
        "startServer"     : False ,
        "useGlobalMatrix" : False ,
        "useMicrophone"   : True  ,
        "HARDWARE_MODE"   : "simulation",
        "onRaspberry"     : False  ,

        "printTimeOfCalculation" : False ,
        "printModesDetails"      : True ,
        "printMicrophoneDetails" : False ,
        "printAppDetails"        : False ,
        "printAsservmentDetails" : False ,
        "printConfigurationLoads": False ,
        "printConfigChanges"     : False ,

        "modesToPrintDetails"    : ["PSG"]
    }



song_files = [
    #'mp3_files/Flashback.mp3',
    #'mp3_files/Pumped Up Kicks.mp3',
    #'mp3_files/Nobody Rules the Streets.mp3',
    'mp3_files\Sugar (feat. Francesco Yates).mp3'
    # Add as many songs as you want here!
]

print(f"Loading {len(song_files)} songs sequentially for Song Change Test...")

y_list = []
onset_list = []
true_beat_times_list = []
current_shift_time = 0.0
tempo_librosa = 120.0 # Default fallback

for i, f in enumerate(song_files):
    print(f"Running non-causal Librosa Beat Track on Song {i+1}...")
    y, sr = librosa.load(f.replace('\\', '/'), sr=44100)
    y_list.append(y)
    
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    onset_list.append(onset)
    
    t, bf = librosa.beat.beat_track(onset_envelope=onset, sr=sr)
    if i == 0:
        tempo_librosa = float(t[0]) if hasattr(t, '__len__') else float(t) # Used for first plot line
    
    bt = librosa.frames_to_time(bf, sr=sr)
    true_beat_times_list.append(bt + current_shift_time)
    
    current_shift_time += len(y) / float(sr)

import numpy as np
y_full = np.concatenate(y_list) if y_list else np.array([])
onset_env_full = np.concatenate(onset_list) if onset_list else np.array([])
true_beat_times = np.concatenate(true_beat_times_list) if true_beat_times_list else np.array([])

print(f"✅ Ground Truth Extraction Complete! Main Beats: {len(true_beat_times)}, Sub Beats: Not Extracted")
class Robust_Simulated_Microphone:
    def __init__(self, y_full_array, bandValues, infos):
        self.bandValues = bandValues
        self.nb_of_fft_band = len(self.bandValues)
        
        self.sample_rate = 44100
        self.buffer_size = 1024 
        self.audio_data = np.zeros(self.buffer_size)
        
        # Ensure array is float and flattened appropriately to avoid truncation
        self.full_audio = y_full_array
        self.total_samples = len(self.full_audio)
        self.current_pos = 0
        
        fft_size = self.buffer_size // 2 + 1
        self.weight_matrix = np.zeros((self.nb_of_fft_band, fft_size))
        
        def hz_to_mel(f): return 2595 * np.log10(1 + f / 700.0)
        def mel_to_hz(m): return 700 * (10**(m / 2595.0) - 1)
        
        lower_mel = hz_to_mel(20)
        upper_mel = hz_to_mel(20000)
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
                
        self.raw_fft_history = None
        self.bass_flux = 0.0
        self.vocal_flux = 0.0
        self.treble_flux = 0.0
        self.high_res_flux = 0.0

    def pop_chunk(self, chunk_size=1024):
        if self.current_pos + chunk_size > self.total_samples:
            return False 
        
        incoming = self.full_audio[self.current_pos : self.current_pos + chunk_size]
        self.current_pos += chunk_size
        self.audio_data = np.roll(self.audio_data, -chunk_size)
        self.audio_data[-chunk_size:] = incoming
        return True

    def calculate_fft(self):
        windowed_data = self.audio_data * np.hanning(self.buffer_size)
        fft_result = np.abs(np.fft.rfft(windowed_data))
        
        scale = 150.0 / (self.buffer_size / 1024.0)
        mel_bands = np.dot(self.weight_matrix, fft_result) * scale
        for i in range(self.nb_of_fft_band):
            self.bandValues[i] = int(mel_bands[i])

        if self.raw_fft_history is not None:
            freq_diff = np.maximum(0, fft_result - self.raw_fft_history)
            self.bass_flux = np.sum(freq_diff[1:7])
            self.vocal_flux = np.sum(freq_diff[7:70])
            self.treble_flux = np.sum(freq_diff[70:300])
            self.high_res_flux = self.treble_flux
        self.raw_fft_history = fft_result


def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=1.5, step=0.3, expected_phase=None):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    best_overall_score = -float('inf')
    best_overall_bpm = center_bpm
    best_overall_p = 0
    
    buffer_indices = np.arange(odf_size)
    
    # Tiny localized search area explicitly restricted to ± radius around the Flywheel's best guess
    bpm_evals = np.arange(max(50.0, center_bpm - search_radius), min(220.0, center_bpm + search_radius + step/2), step)
    
    btrack_fps = 60.0
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
        template_vals[abs_phi <= 0.025] = 0.6+ 0.3 * (0.025-(abs_phi[mask_medium]))
        template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0 # Sub-sub-beats get neutral weight (0.0)
        
        p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1)
        
        # --- NEW: PHASE INERTIA LOGIC ---
        # If we have an established tracker momentum, gently penalize severe phase jumps 
        # (reduces the likelihood of 180-degree phase inversions caused by loud off-beats)
        if expected_phase is not None:
            expected_p = (expected_phase * tau_val) % tau_val
            
            # Shortest circular distance from candidate p to expected_p
            dist_p = np.minimum(np.abs(p_arr[:, 0] - expected_p), tau_val - np.abs(p_arr[:, 0] - expected_p))
            norm_dist = dist_p / tau_val
            
            # Gaussian phase momentum (punishes 0.5 offsets to prevent sub-beat locks)
            phase_inertia = np.exp(-0.5 * (norm_dist / 0.35)**2)
            
            # Blend the score so sudden off-beats lose their competitive symmetry
            p_scores = p_scores * (0.5 + 0.5 * phase_inertia)
        # --------------------------------
            
        tau_max_score = np.max(p_scores)
        best_p = np.argmax(p_scores)
        
        gaussian_weight = np.exp(-0.5 * ((bpm_val - center_bpm) / (search_radius * 1.5))**2)
        weighted_score = tau_max_score * (0.8 + 0.2 * gaussian_weight)
        
        if weighted_score > best_overall_score:
            best_overall_score = weighted_score
            best_overall_bpm = bpm_val
            best_overall_p = best_p
            
    # The normalized phase (0 to 1) of the MOST RECENT frame in the buffer is derived directly from p
    optimal_tau = 60.0 * btrack_fps / best_overall_bpm
    precise_phase = best_overall_p / optimal_tau
            
    return best_overall_bpm, precise_phase, best_overall_score

infos = default_infos()
infos["printAsservmentDetails"] = False 
infos["useMicrophone"] = True

SIMULATED_FPS = 60.0
TIME_PER_FRAME = 1.0 / SIMULATED_FPS
CHUNK_SIZE_FOR_60FPS = int(44100 / SIMULATED_FPS)

class MockTime:
    def __init__(self):
        self.current_time = 0.0
    def time(self):
        return self.current_time

mock_timer = MockTime()
ListenerModule.time.time = mock_timer.time

listener = ListenerModule.Listener(infos)
listener.momentum_multiplier = 0.01
listener.dynamic_audio_latency = 0

mic = Robust_Simulated_Microphone(y_full, listener.fft_band_values, infos)
listener.hasBeenSilenceCalibrated = True
listener.hasBeenBBCalibrated = True
listener.calibrate_silence = lambda: None
listener.calibrate_bb = lambda: None

lookahead_frames = int(8.5 * SIMULATED_FPS)
future_queue = deque()

algorithmic_beats = []
algorithmic_sub_beats = []
history_time = []
history_bpm = []
history_bass = []
history_vocal = []
history_vocals_present = []
acapella_events = []
last_acapella_frame = -9999
ACAPELLA_COOLDOWN_FRAMES = int(5.0 * 86) # approximate 5 secs

history_treble = []
history_trust = []
history_stm_power = []
history_ltm_power = []
history_timbral_nov = []
history_power_nov = []
history_combined_nov = []
history_nov_threshold = []

standalone_phase = 0.0
standalone_beat_count = 0
last_standalone_beat_count = 0
last_standalone_phase = 0.0
standalone_sub_beat_locked = -1

audio_time = 0.0
playhead_time = 0.0
frame = 0

frames_since_sweep = 0
frames_between_sweep = int(2 * SIMULATED_FPS)  # Sweep every 12 frames (5 Hz)


# Structural Novelty Variables
stm_timbre = np.zeros(8)
ltm_timbre = np.zeros(8)
stm_power = 0.0
ltm_power = 0.0
stm_weight = 0.02  # ~1.5s smoothing
ltm_weight = 0.0015 # ~6.0s smoothing

structural_changes = []
last_structural_change_frame = -9999
STRUCTURAL_COOLDOWN_FRAMES = int(20.0 * SIMULATED_FPS)

# Advanced Adaptive Cooldown
NOVELTY_THRESHOLD_MIN = 0.15
current_novelty_threshold = NOVELTY_THRESHOLD_MIN
NOVELTY_DECAY_RATE = 0.998 # Reduce threshold by 0.1% every frame

power_weight = 0.2
SONG_NOVELTY_THRESHOLD = 0.28 # Trigger song change on massive DJ crossfades # Sensitivity to be tweaked later

song_changes = []
silence_frames = 0
SILENCE_THRESHOLD_FRAMES = int(1.5 * SIMULATED_FPS)

# BPM Trust Variables for Song Changes
long_term_bpm = 120.0
ltm_trust = 10.0 # Arbitrary warm-up scalar
bpm_jump_threshold = 8.0 # BPM change needed to trigger song reset
bpm_trust = 10.0 # Default starting trust

print("🚀 Starting Hybrid Simulation Loop...")

while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()
    
    # 0. Feature Extraction & Novelty Detection (Verse/Chorus & Song boundaries)
    current_timbre = listener.band_proportion

    # Update Short-Term and Long-Term Memory
    stm_timbre = (1 - stm_weight) * stm_timbre + stm_weight * current_timbre
    ltm_timbre = (1 - ltm_weight) * ltm_timbre + ltm_weight * current_timbre
    
    current_power = listener.smoothed_total_power
    stm_power = (1 - stm_weight) * stm_power + stm_weight * current_power
    ltm_power = (1 - ltm_weight) * ltm_power + ltm_weight * current_power
    
    # Calculate Timbral Novelty (Euclidean distance)
    timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)
    
    # Calculate Power Novelty (normalized by LTM to detect relative drops/surges)
    power_novelty = np.abs(stm_power - ltm_power) / (ltm_power + 1.0)
    
    # Combined Novelty Score
    combined_novelty = timbral_novelty + (power_novelty * 0.2)
    
    # Elevating Adaptive Threshold (Decay Phase)
    current_novelty_threshold = max(NOVELTY_THRESHOLD_MIN, current_novelty_threshold * NOVELTY_DECAY_RATE)
    
    # Structural Boundary (Verse / Chorus) OR Seamless DJ crossfade
    # We now evaluate against the dynamic `current_novelty_threshold`
    if combined_novelty > current_novelty_threshold:
        
        # If the structure disruption is astronomically high, it's a crossfade to a new track!
        if combined_novelty > SONG_NOVELTY_THRESHOLD:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
                song_changes.append(playhead_time)
                # Since these are sequential MP3s with abrupt cuts, phase is totally lost.
                # Flush the queue to instantly resync to the new track's groove and transients!
                future_queue.clear()
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.band_means.fill(0.0)
                listener.smoothed_fft_band_values.fill(0.0)
                listener.odf_buffer.fill(0.0)
                
            # Elevate threshold dynamically based on the massive novelty drop!
            current_novelty_threshold = 1.1*combined_novelty
            ltm_timbre = np.copy(stm_timbre)
            ltm_power = stm_power
            
        else:
            # Classic Verse/Chorus change. We still enforce a flat base cooldown to prevent stuttering logic
            if (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
                structural_changes.append(playhead_time)
                last_structural_change_frame = frame
                
                # Elevate threshold dynamically based on the novelty boost!
                current_novelty_threshold = combined_novelty
                # Pull LTM into STM to reset distance
                ltm_timbre = np.copy(stm_timbre)
                ltm_power = stm_power

    # Song Change Detection (Silence / Trust Drop)
    if listener.smoothed_total_power < 5.0:
        silence_frames += 1
    else:
        silence_frames = 0
        
    if silence_frames > SILENCE_THRESHOLD_FRAMES:
        if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
            song_changes.append(playhead_time)
            # Flush the lookahead queue
            future_queue.clear()
            standalone_beat_count = 0
            last_standalone_beat_count = 0
            standalone_sub_beat_locked = -1
            standalone_phase = 0.0
            
            # Reset Listener history
            listener.band_means.fill(0.0)
            listener.smoothed_fft_band_values.fill(0.0)
            listener.odf_buffer.fill(0.0)

    
    # 1. Periodically run the Localized Continuous Precision Sweep centered around listener.bpm
    if frames_since_sweep >= frames_between_sweep:
        # Base Flywheel BPM serves strictly as a guide to restrict search space
        coarse_bpm = listener.bpm if (50 < listener.bpm < 220) else 120.0
        
        # --- NEW: Calculate the phase we EXPECT the ODF to present as the "most recent frame"
        total_latency = listener.dynamic_audio_latency + listener.hardware_latency
        latency_phase_shift = (coarse_bpm / 60.0) * total_latency
        expected_p_phase = (standalone_phase - latency_phase_shift + 1.0) % 1.0
        
        # Only inject phase inertia if we have already confidently tracked at least a few beats
        inertia_param = expected_p_phase if standalone_beat_count > 5 else None
        
        precise_bpm, precise_phase, bpm_trust = localized_continuous_phase_sweep(
            listener.odf_buffer, 
            center_bpm=coarse_bpm, 
            search_radius=1.5, 
            step=0.5,
            expected_phase=inertia_param
        )
        
        listener.bpm = precise_bpm
        
        # --- BPM Trust Song Change Logic ---
        # 1. Update Long-Term smoothing
        if playhead_time < 5.0:
            long_term_bpm = precise_bpm
            ltm_trust = bpm_trust
        else:
            long_term_bpm = 0.9 * long_term_bpm + 0.1 * precise_bpm
            ltm_trust = 0.9 * ltm_trust + 0.1 * bpm_trust
        
        # 2. Detect Wild Departure 
        bpm_divergence = np.abs(precise_bpm - long_term_bpm)
        
        if bpm_divergence > bpm_jump_threshold and bpm_trust < (ltm_trust * 0.6):
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
                song_changes.append(playhead_time)
                # Flush queues due to Song Change (Trust Drop!)
                future_queue.clear()
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.band_means.fill(0.0)
                listener.smoothed_fft_band_values.fill(0.0)
                listener.odf_buffer.fill(0.0)
                
                # Instantly accept the new tempo reality
                long_term_bpm = precise_bpm
        # -----------------------------------

        
        # EXTRACT TARGET SETTINGS: 
        # Calculate Listener's latency-shifted target phase (from float precision)
        latency_phase_shift_precise = (precise_bpm / 60.0) * total_latency
        target_phase = (precise_phase + latency_phase_shift_precise) % 1.0
        
        # Softly align the standalone phase towards the target phase 
        # (This completely eliminates the phase tug-of-war with Listener's internal loop)
        phase_diff = (target_phase - standalone_phase + 0.5) % 1.0 - 0.5
        
        # HARD RESET onto the precise sweep, but ONLY if we maintain temporal sanity
        if abs(phase_diff) < 0.15:
            standalone_phase += phase_diff * 1.0  
        else:
            # We reject the sweep as it likely aligned onto an off-beat / subdivision
            pass
        
        frames_since_sweep = 0
        
    frames_since_sweep += 1
    
    # 2. Advance the standalone phase steadily at precisely the tracked BPM
    phase_delta = (listener.bpm / 60.0) / SIMULATED_FPS
    standalone_phase += phase_delta
    
    while standalone_phase >= 1.0:
        standalone_phase -= 1.0
        standalone_beat_count += 1
    while standalone_phase < 0.0:
        standalone_phase += 1.0
        standalone_beat_count -= 1
    
    # 3. Check for standalone beat triggers without internal Listener conflicts
    is_beat = False
    is_sub_beat = False
    
    if standalone_beat_count > last_standalone_beat_count:
        is_beat = True
        last_standalone_beat_count = standalone_beat_count
        
    if last_standalone_phase < 0.5 and standalone_phase >= 0.5:
        # ANTI-BOUNCE SAFEGUARD: Force max 1 sub-beat per beatcycle threshold
        if standalone_sub_beat_locked < last_standalone_beat_count:
            is_sub_beat = True
            standalone_sub_beat_locked = last_standalone_beat_count
            
    last_standalone_phase = standalone_phase
    
    # 4. Queue up expectations using standalone phase log
    vocals_present = mic.vocal_flux > 20.0
    if mic.bass_flux < 5.0 and mic.vocal_flux > 30.0:
        if (frame - last_acapella_frame) > ACAPELLA_COOLDOWN_FRAMES:
            acapella_events.append(playhead_time)
            last_acapella_frame = frame

    future_queue.append({
        'time': audio_time,
        'bpm': listener.bpm,
        'bass_flux': mic.bass_flux,
        'vocal_flux': mic.vocal_flux,
        'vocals_present': vocals_present,
        'treble_flux': mic.treble_flux,
        'is_beat': is_beat,
        'is_sub_beat': is_sub_beat,
    })
    
    # 4. output playhead pops the oldest frame when the buffer has 5+ seconds of footage
    if len(future_queue) >= lookahead_frames:
        window = 3 # +/- 83ms 
        target = window
        
        bass_flux_array = [f['bass_flux'] for f in future_queue]
        treble_flux_array = [f['treble_flux'] for f in future_queue]
        
        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(bass_flux_array[start_index:end_index])
            peak_power = bass_flux_array[best_idx]
            target_power = bass_flux_array[window]
            local_mean = np.mean(bass_flux_array[start_index:end_index])
            
            # Distance penalty: The further the peak is from the predicted beat (window), 
            # the higher the threshold multiplier to snap to it.
            dist_penalty = 1.0 + 0.5 * (np.abs(best_idx - window) / window)
            
            if best_idx != window and peak_power > max(2.0, (local_mean * 1.5) * dist_penalty):
                future_queue[target]['is_beat'] = False
                future_queue[best_idx]['is_beat'] = True
                future_queue[best_idx]['main_snapped'] = True
            else:
                future_queue[target]['main_snapped'] = True

        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (SUB-BEATS) ---
        if future_queue[target].get('is_sub_beat', False) and not future_queue[target].get('sub_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(treble_flux_array[start_index:end_index])
            peak_power = treble_flux_array[best_idx]
            target_power = treble_flux_array[window]
            local_mean = np.mean(treble_flux_array[start_index:end_index])
            
            dist_penalty = 1.0 + 0.5 * (np.abs(best_idx - window) / window)
            
            if best_idx != window and peak_power > max(2.0, (local_mean * 1.5) * dist_penalty):
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True

        present = future_queue.popleft()
        
        if present.get('is_beat', False):
            algorithmic_beats.append(playhead_time)
            
        if present.get('is_sub_beat', False):
            algorithmic_sub_beats.append(playhead_time)
            
        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_bass.append(present.get('bass_flux', 0.0))
        history_vocal.append(present.get('vocal_flux', 0.0))
        history_vocals_present.append(present.get('vocals_present', False))
        history_treble.append(present.get('treble_flux', 0.0))
        history_trust.append(ltm_trust)
        history_stm_power.append(stm_power)
        history_ltm_power.append(ltm_power)
        history_timbral_nov.append(timbral_novelty)
        history_power_nov.append(power_novelty)
        history_combined_nov.append(combined_novelty)
        history_nov_threshold.append(current_novelty_threshold)
        playhead_time += TIME_PER_FRAME
        
    audio_time += TIME_PER_FRAME
    mock_timer.current_time += TIME_PER_FRAME
    frame += 1
    
    if frame % 1800 == 0:
        print(f"Processed audio time {audio_time:.1f}s...")

ListenerModule.time.time = time.time 

# Final flush
while future_queue:
    present = future_queue.popleft()
    if present.get('is_beat', False):
        algorithmic_beats.append(playhead_time)
    if present.get('is_sub_beat', False):
        algorithmic_sub_beats.append(playhead_time)
    history_time.append(playhead_time)
    history_bpm.append(present['bpm'])
    history_bass.append(present.get('bass_flux', 0.0))
    history_vocal.append(present.get('vocal_flux', 0.0))
    history_vocals_present.append(present.get('vocals_present', False))
    history_treble.append(present.get('treble_flux', 0.0))
    history_trust.append(ltm_trust)
    history_stm_power.append(stm_power)
    history_ltm_power.append(ltm_power)
    history_timbral_nov.append(timbral_novelty)
    history_power_nov.append(power_novelty)
    history_combined_nov.append(combined_novelty)
    playhead_time += TIME_PER_FRAME

alg_beats_array = np.array(algorithmic_beats)
alg_sub_beats_array = np.array(algorithmic_sub_beats)
print(f"✅ Simulation Loop Complete! Extracted {len(alg_beats_array)} Hybrid Beats and {len(alg_sub_beats_array)} Hybrid Sub-beats.")


import matplotlib.pyplot as plt

time_arr = np.array(history_time)
bpm_arr = np.array(history_bpm)
bass_arr = np.array(history_bass)
vocal_arr = np.array(history_vocal)
vocals_present_arr = np.array(history_vocals_present)
vocal_arr = np.array(history_vocal)
vocals_present_arr = np.array(history_vocals_present)
treble_arr = np.array(history_treble)
trust_arr = np.array(history_trust)

plt.figure(figsize=(15, 6))

true_bpm = tempo_librosa[0] if isinstance(tempo_librosa, (list, np.ndarray)) else tempo_librosa

plt.plot(time_arr, bpm_arr, color="#00bcd4", linewidth=2.5, label="BPM / Time Track")

# Scale the BPM trust up to fit beautifully on the same Y-axis as BPM (usually around 100-140)
# A trust of 10-15 gets scaled up: Let's multiply by 2 and add 60 as a base offset
plt.plot(time_arr, trust_arr * 2 + 60, color="#8bc34a", linewidth=2, alpha=0.98, label="BPM Trust (scaled)")

# Plot only Song Changes
for sid, s_time in enumerate(song_changes):
    plt.axvline(s_time, color='black', linestyle='--', linewidth=3, label='Song Change detected' if sid == 0 else "")

y=0
for k in range(len(y_list)):
    y_k = y_list[k]
    y+= len(y_k)
    plt.axvline(y/sr, color='purple', linestyle='-', linewidth=2, label=f'Real song change {k}')


plt.fill_between(time_arr, 60, 160, where=vocals_present_arr, color="#9c27b0", alpha=0.15, label="Vocals Present")
for i, ev in enumerate(acapella_events):
    plt.axvline(x=ev, color="#ff9800", linestyle="-", linewidth=4, alpha=0.6, label="Acapella Event" if i == 0 else "")

plt.fill_between(time_arr, 60, 160, where=vocals_present_arr, color="#9c27b0", alpha=0.05, label="Vocals Present")
for i, ev in enumerate(acapella_events):
    plt.axvline(x=ev, color="#ff9800", linestyle="-", linewidth=4, alpha=0.6, label="Acapella Event" if i == 0 else "")

plt.title("Rhythm Tracking Over Full Audio Duration")
plt.xlabel("Time (seconds)")
plt.ylabel("BPM")
plt.legend(loc="upper right")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('traking_plot.png')
plt.show()


stm_power_arr = np.array(history_stm_power)
ltm_power_arr = np.array(history_ltm_power)
timbral_nov_arr = np.array(history_timbral_nov)
power_nov_arr = np.array(history_power_nov)
combined_nov_arr = np.array(history_combined_nov)
nov_thr_arr = np.array(history_nov_threshold)


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

# TOP PLOT: Power Comparison
ax1.plot(time_arr, stm_power_arr, color='dodgerblue', alpha=0.8, linewidth=1.5, label='Short-Term Power (STM)')
ax1.plot(time_arr, ltm_power_arr, color='darkorange', alpha=0.8, linewidth=2.0, label='Long-Term Power (LTM)')
ax1.set_title("Power Dynamics (STM vs LTM)")
ax1.set_ylabel("Total Smoothed Power")
ax1.legend(loc="upper right")
ax1.grid(alpha=0.3)

for sid, s_time in enumerate(structural_changes):
    ax1.axvline(s_time, color='red', linestyle='--', linewidth=2)
for sid, s_time in enumerate(song_changes):
    ax1.axvline(s_time, color='black', linestyle='-', linewidth=3)

# BOTTOM PLOT: Novelty & Boundaries
ax2.plot(time_arr, timbral_nov_arr, color='purple', alpha=0.5, label='Timbral Novelty')
ax2.plot(time_arr, power_nov_arr, color='orange', alpha=0.5, label='Power Novelty (relative)')
ax2.plot(time_arr, combined_nov_arr, color='red', linewidth=2.0, label='Combined Novelty Score')
ax2.plot(time_arr[:len(nov_thr_arr)],nov_thr_arr,color="grey",label = 'Threshold')

ax2.axhline(0.15, color="black", linestyle=":", label="Threshold (0.15)")
ax2.set_title("Structural Novelty & Segmentation Boundaries")
ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Novelty Score")
ax2.legend(loc="upper right")
ax2.grid(alpha=0.3)

y=0
for k in range(len(y_list)):
    y_k = y_list[k]
    y+= len(y_k)
    plt.axvline(y/sr, color='purple', linestyle='-', linewidth=2, label=f'Real song change {k}')




# Plot the Boundaries
for sid, s_time in enumerate(structural_changes):
    ax2.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else "")
for sid, s_time in enumerate(song_changes):
    ax2.axvline(s_time, color='black', linestyle='-', linewidth=2, label='Song Change' if sid == 0 else "")

plt.tight_layout()
plt.savefig('novelty_boundaries_plot.png')
plt.show()