import json

notebook = {
 "cells": [],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}

def add_markdown(source):
    notebook["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [s + "\n" for s in source.split("\n")]
    })

def add_code(source):
    notebook["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [s + "\n" for s in source.split("\n")]
    })

add_markdown("""# 🔬 Continuous Hybrid Tracker
This notebook combines our high-resolution `numpy` FFT Transient Extractor with the powerful Localized Continuous Phase Sweep.

Here, `Listener` acts simply to **initialize a search radius**. We sweep a continuous phase float array at high resolution (0.1 BPM) in a tiny local region around what the classic Flywheel suspects the BPM is. This gives sub-BPM float precision. We then throw those projected phase beats into our Magnetic 5-Second Lookahead Buffer to snap onto the exact physical transients.""")

add_code("""import librosa
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

AUDIO_FILE = 'mp3_files/Nightcall.mp3'
""")

add_markdown("""### 1. The Ground Truth Evaluation Benchmark""")

add_code("""print(f"Loading {AUDIO_FILE} full audio for Ground Truth Benchmarks...")
y_full, sr = librosa.load(AUDIO_FILE)

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
""")

add_markdown("""### 2. High Resolution FFT Microphones""")

add_code("""class Robust_Simulated_Microphone:
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
""")

add_markdown("""### 3. Localized Continuous Phase Sweep & Float Flywheel
This cuts computation by ~95% by only exploring around a center BPM given by the Listener.py guide.""")

add_code("""def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=3.0, step=0.1):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    best_overall_score = -float('inf')
    best_overall_bpm = center_bpm
    best_overall_p = 0
    
    buffer_indices = np.arange(odf_size)
    
    # Tiny localized search area explicitly restricted to ± radius around the Flywheel's best guess
    bpm_evals = np.arange(max(60.0, center_bpm - search_radius), min(180.0, center_bpm + search_radius + step/2), step)
    
    btrack_fps = 60.0
    
    for bpm_val in bpm_evals:
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        p_scores = np.zeros(p_max)
        
        for p in range(p_max):
            phase_float = (buffer_indices - (odf_size - 1 - p)) % tau_val
            norm_phi = phase_float / tau_val 
            
            template_vals = np.full(odf_size, -0.2)
            template_vals[(norm_phi <= 0.05) | (norm_phi >= 0.95)] = 1.0
            template_vals[(norm_phi >= 0.45) & (norm_phi <= 0.55)] = 0.6
            template_vals[(norm_phi >= 0.22) & (norm_phi <= 0.28)] = 0.3
            template_vals[(norm_phi >= 0.72) & (norm_phi <= 0.78)] = 0.3
            
            p_scores[p] = np.sum(weighted_buffer * template_vals)
            
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

""")

add_markdown("""### 4. The 5-Second Magnetic Snap Execution Engine""")

add_code("""infos = default_infos()
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

last_logged_beat_count = getattr(listener, 'beat_count', 0)
last_logged_beat_phase = getattr(listener, 'beat_phase', 0.0)

audio_time = 0.0
playhead_time = 0.0
frame = 0

frames_since_sweep = 0
frames_between_sweep = int(0.2 * SIMULATED_FPS)  # Sweep every 12 frames (5 Hz)

print("🚀 Starting Hybrid Simulation Loop...")

while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()
    
    # 1. Periodically run the Localized Continuous Precision Sweep centered around listener.bpm
    if frames_since_sweep >= frames_between_sweep:
        # Base Flywheel BPM serves strictly as a guide to restrict search space
        coarse_bpm = listener.bpm if (60 < listener.bpm < 180) else 120.0
        precise_bpm, precise_phase = localized_continuous_phase_sweep(
            listener.odf_buffer, 
            center_bpm=coarse_bpm, 
            search_radius=3.0, 
            step=0.1
        )
        # Periodically explicitly "fix the bpm" of Listener while retaining its exact phase engine!
        listener.bpm = precise_bpm
        listener.btrack_tau = 60.0 * listener.btrack_fps / max(1.0, precise_bpm)
        frames_since_sweep = 0
        
    frames_since_sweep += 1
    
    # 2. Check what the Flywheel guide asks for, using same technique as RobustGuidedTracker
    is_beat = False
    is_sub_beat = False
    
    current_beat_count = getattr(listener, 'beat_count', 0)
    if current_beat_count > last_logged_beat_count:
        is_beat = True
        last_logged_beat_count = current_beat_count
        
    current_phase = getattr(listener, 'beat_phase', 0.0)
    if last_logged_beat_phase < 0.5 and current_phase >= 0.5:
        is_sub_beat = True
    last_logged_beat_phase = current_phase
    
    # 3. Queue up expectations using Listener's phase log
    future_queue.append({
        'time': audio_time,
        'bpm': listener.bpm,
        'raw_flux': mic.high_res_flux,
        'is_beat': is_beat,
        'is_sub_beat': is_sub_beat,
    })
    
    # 4. output playhead pops the oldest frame when the buffer has 5+ seconds of footage
    if len(future_queue) >= lookahead_frames:
        window = 9 # +/- 150ms 
        target = window
        
        flux_array = [f['raw_flux'] for f in future_queue]
        
        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            
            # Snap safely onto the exact acoustic peak!
            if peak_power > 10.0:
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
            
            if peak_power > 10.0:
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
""")

add_markdown("### 5. Metrics & Evaluation")

add_code("""TOLERANCE_WINDOW = 0.150

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
""")

add_markdown("### 6. Visualizing Rhythm & Target Synchronization")

add_code("""import matplotlib.pyplot as plt

time_arr = np.array(history_time)
bpm_arr = np.array(history_bpm)

plt.figure(figsize=(15, 6))

true_bpm = tempo_librosa[0] if isinstance(tempo_librosa, (list, np.ndarray)) else tempo_librosa

plt.plot(time_arr, bpm_arr, color="cyan", linewidth=2.5, label="Hybrid Continuous BPM")
plt.axhline(true_bpm, color="lime", linestyle="--", alpha=0.8, label=f"Librosa True BPM ({true_bpm:.1f})")

plt.title("Rhythm Tracking Over Full Audio Duration")
plt.xlabel("Time (seconds)")
plt.ylabel("BPM")
plt.legend(loc="upper right")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
""")

output_file = 'ContinuousHybridTracker.ipynb'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1)

print(f"Dumping Continuous Hybrid Tracking to {output_file}...")
