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

AUDIO_FILE = 'mp3_files/Palladium.mp3'
AUDIO_FILE = 'mp3_files/01-Plastic-People.mp3'



print(f"Loading {AUDIO_FILE} full audio for Ground Truth Benchmarks...")
y_full, sr = librosa.load(AUDIO_FILE, sr=44100)

print("Running non-causal Librosa Beat Track...")
onset_env_full = librosa.onset.onset_strength(y=y_full, sr=sr)
tempo_librosa, beat_frames_true = librosa.beat.beat_track(onset_envelope=onset_env_full, sr=sr)
true_beat_times = librosa.frames_to_time(beat_frames_true, sr=sr)

# Basic Librosa sub-beats estimation (tempo / 2 shift)
true_subbeat_times = []
for i in range(len(true_beat_times) - 1):
    midpoint = (true_beat_times[i] + true_beat_times[i+1]) / 2.0
    true_subbeat_times.append(midpoint)
true_subbeat_times = np.array(true_subbeat_times)

print(f"✅ Ground Truth Extraction Complete! Main Beats: {len(true_beat_times)}, Sub Beats: {len(true_subbeat_times)}")


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
            freq_diff = np.maximum(0, fft_result[5:300] - self.raw_fft_history[5:300])
            self.high_res_flux = np.sum(freq_diff)
        self.raw_fft_history = fft_result


def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=1.5, step=0.1):
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
        template_vals = np.full((p_max, odf_size), -0.2)
        template_vals[abs_phi >= 0.45] = 1.5
        template_vals[abs_phi <= 0.04] = 0.6
        template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0 # Sub-sub-beats get neutral weight (0.0)
        
        p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1)
            
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
            
    return best_overall_bpm, precise_phase

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

standalone_phase = 0.0
standalone_beat_count = 0
last_standalone_beat_count = 0
last_standalone_phase = 0.0
standalone_sub_beat_locked = -1

audio_time = 0.0
playhead_time = 0.0
frame = 0

frames_since_sweep = 0
frames_between_sweep = int(0.4 * SIMULATED_FPS)  # Sweep every 12 frames (5 Hz)

print("🚀 Starting Hybrid Simulation Loop...")

while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()
    
    # 1. Periodically run the Localized Continuous Precision Sweep centered around listener.bpm
    if frames_since_sweep >= frames_between_sweep:
        # Base Flywheel BPM serves strictly as a guide to restrict search space
        coarse_bpm = listener.bpm if (50 < listener.bpm < 220) else 120.0
        precise_bpm, precise_phase = localized_continuous_phase_sweep(
            listener.odf_buffer, 
            center_bpm=coarse_bpm, 
            search_radius=1.5, 
            step=0.5
        )
        
        listener.bpm = precise_bpm
        
        # EXTRACT TARGET SETTINGS: 
        # Calculate Listener's latency-shifted target phase (from float precision)
        total_latency = listener.dynamic_audio_latency + listener.hardware_latency
        latency_phase_shift = (precise_bpm / 60.0) * total_latency
        target_phase = (precise_phase + latency_phase_shift) % 1.0
        
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
    future_queue.append({
        'time': audio_time,
        'bpm': listener.bpm,
        'raw_flux': mic.high_res_flux,
        'is_beat': is_beat,
        'is_sub_beat': is_sub_beat,
    })
    
    # 4. output playhead pops the oldest frame when the buffer has 5+ seconds of footage
    if len(future_queue) >= lookahead_frames:
        window = 5 # +/- 83ms 
        target = window
        
        flux_array = [f['raw_flux'] for f in future_queue]
        
        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            local_mean = np.mean(flux_array[start_index:end_index])
            
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
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            local_mean = np.mean(flux_array[start_index:end_index])
            
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
    playhead_time += TIME_PER_FRAME

alg_beats_array = np.array(algorithmic_beats)
alg_sub_beats_array = np.array(algorithmic_sub_beats)
print(f"✅ Simulation Loop Complete! Extracted {len(alg_beats_array)} Hybrid Beats and {len(alg_sub_beats_array)} Hybrid Sub-beats.")


TOLERANCE_WINDOW = 0.075

def evaluate_single_stream(alg_stream, true_stream, tolerance=0.150):
    matched_true = set()
    matched_alg = set()
    for i, a_beat in enumerate(alg_stream):
        closest_dist = float('inf')
        closest_j = -1
        for j, t_beat in enumerate(true_stream):
            if j in matched_true: continue
            dist = abs(a_beat - t_beat)
            if dist < closest_dist and dist <= tolerance:
                closest_dist = dist
                closest_j = j
                
        if closest_j != -1:
            matched_true.add(closest_j)
            matched_alg.add(i)
            
    hits = len(matched_alg)
    false_positives = len(alg_stream) - hits
    false_negatives = len(true_stream) - hits
    precision = hits / len(alg_stream) if len(alg_stream) > 0 else 0
    recall = hits / len(true_stream) if len(true_stream) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return hits, false_positives, false_negatives, precision, recall, f1_score, matched_alg, matched_true

# Validate output sync quality!
m_hits, m_wrongs, m_misses, m_precision, m_recall, m_f1, m_alg_main, m_true = evaluate_single_stream(alg_beats_array, true_beat_times, TOLERANCE_WINDOW)
s_hits, s_wrongs, s_misses, s_precision, s_recall, s_f1, m_alg_sub, m_true_sub = evaluate_single_stream(alg_sub_beats_array, true_subbeat_times, TOLERANCE_WINDOW)

total_hits = m_hits + s_hits
total_wrongs = m_wrongs + s_wrongs
total_misses = m_misses + s_misses
total_alg = len(alg_beats_array) + len(alg_sub_beats_array)
total_true = len(true_beat_times) + len(true_subbeat_times)

tot_precision = total_hits / total_alg if total_alg > 0 else 0
tot_recall = total_hits / total_true if total_true > 0 else 0
tot_f1 = 2 * (tot_precision * tot_recall) / (tot_precision + tot_recall) if (tot_precision + tot_recall) > 0 else 0

print("============ 📈 EVALUATION REPORT ============")
print(f"Tolerance Window: +/- {int(TOLERANCE_WINDOW*1000)}ms")
print(f"Total True Beats: {len(true_beat_times)} | Total Sub-beats: {len(true_subbeat_times)}")
print(f"Total Hybrid Beats: {len(alg_beats_array)} | Total Hybrid Sub-beats: {len(alg_sub_beats_array)}")
print("----------------------------------------------")
print(f"✅ RIGHT (Main Beats): {m_hits} perfectly synced.")
print(f"☑️ RIGHT (Sub-Beats): {s_hits} perfectly synced.")
print(f"❌ WRONG (False Positives): {total_wrongs} extra/ghost commands.")
print(f"👻 MISSED (True commands): {total_misses} true beats slipped through.")
print("----------------------------------------------")
print(f"🎯 Precision: {tot_precision*100:.1f}%")
print(f"🏅 Recall: {tot_recall*100:.1f}%")
print(f"🏆 F1-SCORE (Overall Sync Quality): {tot_f1*100:.1f}%")
print("==============================================")


import matplotlib.pyplot as plt

time_arr = np.array(history_time)
bpm_arr = np.array(history_bpm)

plt.figure(figsize=(15, 6))

true_bpm = tempo_librosa[0] if isinstance(tempo_librosa, (list, np.ndarray)) else tempo_librosa

plt.plot(time_arr, bpm_arr, color="cyan", linewidth=2.5, label="Hybrid Continuous BPM")
plt.axhline(true_bpm, color="lime", linestyle="--", alpha=0.8, label=f"Librosa True BPM ({true_bpm:.1f})")
plt.axhline(91, color="red", linestyle="--", alpha=0.8, label=f"Librosa True BPM ({true_bpm:.1f})")


sweep_interval = frames_between_sweep / SIMULATED_FPS
sweep_times = np.arange(sweep_interval, time_arr[-1], sweep_interval)
for sweep_idx, s_time in enumerate(sweep_times):
    plt.axvline(s_time, color='magenta', linestyle=':', alpha=0.4, linewidth=1, label='Sweep' if sweep_idx == 0 else "")

plt.title("Rhythm Tracking Over Full Audio Duration")
plt.xlabel("Time (seconds)")
plt.ylabel("BPM")
plt.legend(loc="upper right")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


# Define 15-second window in the middle
total_duration = len(y_full) / sr
mid_time = total_duration / 2.0
start_time = 60
end_time = 80


# Filter arrays for the time window
def filter_window(arr, start, end):
    return [t for t in arr if start <= t <= end]

sweep_times = filter_window(sweep_times,start_time,end_time)
tp_alg_times = [alg_beats_array[i] for i in m_alg_main] + [alg_sub_beats_array[i] for i in m_alg_sub]
fp_alg_times = [alg_beats_array[i] for i in range(len(alg_beats_array)) if i not in m_alg_main] + [alg_sub_beats_array[i] for i in range(len(alg_sub_beats_array)) if i not in m_alg_sub]
fn_true_times = [true_beat_times[i] for i in range(len(true_beat_times)) if i not in m_true] + [true_subbeat_times[i] for i in range(len(true_subbeat_times)) if i not in m_true_sub]



window_tp = filter_window(tp_alg_times, start_time, end_time)
window_fp = filter_window(fp_alg_times, start_time, end_time)
window_fn = filter_window(fn_true_times, start_time, end_time)
window_true = filter_window(true_beat_times, start_time, end_time)

# Get onset envelope time axis
times_onset = librosa.frames_to_time(np.arange(len(onset_env_full)), sr=sr)
mask = (times_onset >= start_time) & (times_onset <= end_time)
max_onset = max(onset_env_full[mask]) if sum(mask) > 0 else 1.0

plt.figure(figsize=(30, 6))
plt.plot(times_onset[mask], onset_env_full[mask], label='Onset Strength', color='gray', alpha=0.4)

# V-lines for Ground Truth Beats
#plt.vlines(window_true, ymin=0, ymax=max_onset*1.1, color='lime', linestyle='-', alpha=0.3, label='Ground Truth Beats', linewidth=3)

# Scatter points for detections
plt.scatter(window_tp, [max_onset * 0.9]*len(window_tp), color='green', s=120, label='True Positives (Found)', zorder=5)
plt.scatter(window_fp, [max_onset * 0.8]*len(window_fp), color='red', s=120, label='False Positives (Ghost)', zorder=5)
plt.scatter(window_fn, [max_onset * 0.7]*len(window_fn), color='orange', s=120, label='False Negatives (Missed)', zorder=5)

for sweep_idx, s_time in enumerate(sweep_times):
    plt.axvline(s_time, color='magenta', linestyle='--', alpha=0.6, linewidth=1, label='Sweep' if sweep_idx == 0 else "")


plt.title(f"Beat Detection Sync Evaluation ({start_time:.1f}s to {end_time:.1f}s)")
plt.xlabel("Time (seconds)")
plt.ylabel("Onset Strength")
plt.xlim(start_time, end_time)
plt.ylim(0, max_onset*1.15)
plt.legend(loc="upper right")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
