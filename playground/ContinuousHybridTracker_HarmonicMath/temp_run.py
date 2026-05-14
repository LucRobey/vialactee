import librosa
import numpy as np
import torchaudio
import torch
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.abspath('../..'))
import core.Listener as ListenerModule
from IPython.display import display, clear_output

def default_infos():
    return {
        "startServer"     : False ,
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

root = '../../assets/musics/mp3_files/'
song_files = [
    'Palladium',
    'Pumped Up Kicks',
    'Nobody Rules the Streets',
]
real_bpms = [145, 128, 128]

for song_id in range(len(song_files)):
    song_files[song_id] = root + song_files[song_id] + ".mp3"

y_list = []
onset_list = []
librosa_dir = os.path.join(root, 'librosa')
os.makedirs(librosa_dir, exist_ok=True)

for i, f in enumerate(song_files):
    basename = os.path.basename(f)
    save_path = os.path.join(librosa_dir, f"{basename}.npz")
    
    if os.path.exists(save_path):
        data = np.load(save_path, allow_pickle=True)
        y = data['y']
        sr = int(data['sr'])
        onset = data['onset']
    else:
        y, sr = librosa.load(f, sr=44100)
        onset = librosa.onset.onset_strength(y=y, sr=sr)
        np.savez(save_path, y=y, sr=sr, onset=onset)
        
    y_list.append(y)
    onset_list.append(onset)

class Robust_Simulated_Microphone:
    def __init__(self, y_full_array, bandValues, infos):
        self.bandValues = bandValues
        self.nb_of_fft_band = len(self.bandValues)
        self.sample_rate = 44100
        self.buffer_size = 1024 
        self.audio_data = np.zeros(self.buffer_size)
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
        self.raw_fft_history = fft_result

# THE HARMONIC MATH CORE (SIMPLIFIED)
def bpm_to_class(bpm):
    '''Map BPM to a float in [0, 1) based on octave'''
    return np.log2(bpm / 60.0) % 1.0

def class_to_bpm_candidates(bpm_class):
    '''Returns the most common harmonic multipliers for a given class'''
    base_bpm = 60.0 * (2 ** bpm_class)
    return [
        base_bpm * 0.5,    # e.g., 50
        base_bpm * 0.75,   # e.g., 75
        base_bpm * 1.0,    # e.g., 100
        base_bpm * 1.5,    # e.g., 150
        base_bpm * 2.0     # e.g., 200
    ]

def tempo_class_distance(f1, f2):
    '''Shortest circular distance on [0, 1)'''
    d = abs(f1 - f2)
    return min(d, 1.0 - d)

def harmonic_alignment(current_class, long_term_class):
    '''Checks straight octaves AND perfect fifths (1.5x) to safely align and find distance'''
    shift = np.log2(1.5) # approx 0.58496
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

# THE TEMPLATE BANK (O(1) Precomputed Pearson Correlation)
class FastTemplateBank:
    def __init__(self, btrack_fps=60.0, odf_size=300):
        self.btrack_fps = btrack_fps
        self.odf_size = odf_size
        self.templates = {}
        
        buffer_indices = np.arange(self.odf_size)
        self.const_part = buffer_indices - (self.odf_size - 1)
        
    def get_template(self, bpm_val):
        if bpm_val in self.templates:
            return self.templates[bpm_val]
            
        tau_val = 60.0 * self.btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        
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
        template_std = np.sqrt(np.sum(template_centered**2, axis=1)) + 1e-6
        
        # Pre-normalized template for rapid matrix multiplication
        normalized_template = template_centered / template_std[:, None]
        self.templates[bpm_val] = normalized_template
        return normalized_template

# Global Bank Instance
template_bank = FastTemplateBank()

# THE CANDIDATE EVALUATOR (HEAVY JUDGE)
def evaluate_specific_bpms(odf_buffer, candidate_bpms, **kwargs):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    # Pre-compute zero-mean buffer for Pearson
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6
    
    best_score_pearson = -float('inf')
    best_bpm_pearson = candidate_bpms[0]
    
    for bpm_val in candidate_bpms:
        if not (40.0 <= bpm_val <= 190.0):
            continue
            
        normalized_template = template_bank.get_template(bpm_val)
        
        # O(1) Vectorized Pearson Correlation via Dot Product
        p_scores_pearson = (normalized_template @ buffer_centered) / buffer_std
        
        # --- HUMAN PERCEPTION PRIOR (Gaussian weighting) ---
        human_prior = 0.5 + 0.5 * np.exp(-0.5 * ((bpm_val - 125.0) / 40.0)**2)
        weighted_score = np.max(p_scores_pearson) * human_prior
        
        if weighted_score > best_score_pearson:
            best_score_pearson = weighted_score
            best_bpm_pearson = bpm_val
            
    return best_bpm_pearson, best_score_pearson
# THE INITIAL SWEEP (FAST SCOUT) - TRUE PEARSON O(1)
def class_based_phase_sweep(odf_buffer, class_evals, **kwargs):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6
    
    best_overall_score = -float('inf')
    best_overall_class = class_evals[0] % 1.0
    
    for class_val in class_evals:
        c = class_val % 1.0
        base_bpm = 60.0 * (2 ** c)
        eval_bpm = base_bpm if base_bpm >= 90.0 else base_bpm * 2.0
        
        normalized_template = template_bank.get_template(eval_bpm)
        p_scores = (normalized_template @ buffer_centered) / buffer_std
        
        # Human Prior injected into Fast Scout to fix Song 3 polyrhythms!
        human_prior = 0.5 + 0.5 * np.exp(-0.5 * ((eval_bpm - 125.0) / 40.0)**2)
        tau_max_score = np.max(p_scores) * human_prior
        
        if tau_max_score > best_overall_score:
            best_overall_score = tau_max_score
            best_overall_class = c
            
    return best_overall_class, best_overall_score
import time
def run_simulation(y_list):
    print(f"\n🚀 Starting Fast-Scout/Heavy-Judge Simulation with Bass+High Filter (ONSET DRIVEN)...\n")
    infos = default_infos()
    infos["printAsservmentDetails"] = False 
    infos["useMicrophone"] = True

    SIMULATED_FPS = 60.0
    TIME_PER_FRAME = 1.0 / SIMULATED_FPS
    CHUNK_SIZE_FOR_60FPS = int(44100 / SIMULATED_FPS)

    class MockTime:
        def __init__(self): self.current_time = 0.0
        def time(self): return self.current_time

    mock_timer = MockTime()
    ListenerModule.time.time = mock_timer.time

    listener = ListenerModule.Listener(infos)
    listener.ingestion.momentum_multiplier = 0.01
    listener.dynamic_audio_latency = 0

    y_full = np.concatenate(y_list)
    mic = Robust_Simulated_Microphone(y_full, listener.ingestion.fft_band_values, infos)
    listener.hasBeenSilenceCalibrated = True
    listener.hasBeenBBCalibrated = True
    listener.ingestion.calibrate_silence = lambda fps_ratio: None
    listener.ingestion.calibrate_bb = lambda fps_ratio: None

    # Metrics
    history_time = []
    history_raw_bpm = []
    history_pearson = []
    history_class = []
    history_ltm_class = []

    audio_time = 0.0
    playhead_time = 0.0
    frame = 0

    last_strong_sweep_time = -8.0
    smoothed_flux = 0.0
    long_term_class = 0.0
    
    # CUSTOM BASS + HIGH ODF BUFFER
    custom_odf_buffer = np.zeros(300)
    prev_bands = np.zeros(len(listener.ingestion.fft_band_values))

    # Profiling Accumulators
    profile_time = {
        'mic_and_fft': 0.0,
        'listener_update': 0.0,
        'flux_calc': 0.0,
        'class_based_phase_sweep': 0.0,
        'harmonic_alignment': 0.0,
        'evaluate_specific_bpms': 0.0,
    }

    # Use the real time to profile execution
    real_time_func = time.perf_counter

    while True:
        t_start = real_time_func()
        if not mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
            break
        mic.calculate_fft()
        profile_time['mic_and_fft'] += real_time_func() - t_start
        
        t_start = real_time_func()
        listener.update()
        profile_time['listener_update'] += real_time_func() - t_start
        
        t_start = real_time_func()
        current_bands = np.array(listener.ingestion.fft_band_values)
        flux_bands = np.maximum(0, current_bands - prev_bands)
        prev_bands = current_bands
        
        custom_flux = np.sum(flux_bands[0:2]) + np.sum(flux_bands[-2:])
        custom_odf_buffer = np.roll(custom_odf_buffer, -1)
        custom_odf_buffer[-1] = custom_flux
        
        # SIMULATE BTRACK PEAK DETECTION
        smoothed_flux = 0.95 * smoothed_flux + 0.05 * custom_flux
        is_peak = custom_flux > (smoothed_flux * 1.8 + 0.1)
        profile_time['flux_calc'] += real_time_func() - t_start
        
        # ONLY RUN MATH ON BEATS (TRANSIENTS)
        if is_peak:
            if playhead_time - last_strong_sweep_time >= 8.0:
                # STRONG SWEEP: Full [0.0, 1.0) range every 8 seconds
                class_evals = np.arange(0.0, 1.0, 0.01)
                last_strong_sweep_time = playhead_time
            else:
                # LOCAL SWEEP: Window around long_term_class
                class_evals = np.arange(long_term_class - 0.05, long_term_class + 0.05 + 0.001, 0.01)

            t_start = real_time_func()
            best_class, raw_score = class_based_phase_sweep(
                custom_odf_buffer, class_evals=class_evals)
            profile_time['class_based_phase_sweep'] += real_time_func() - t_start
            
            t_start = real_time_func()
            min_d, aligned_class = harmonic_alignment(best_class, long_term_class)
            
            if playhead_time < 5.0:
                long_term_class = aligned_class
            else:
                diff = (aligned_class - long_term_class + 0.5) % 1.0 - 0.5
                long_term_class = (long_term_class + 0.1 * diff) % 1.0
                
            candidates = class_to_bpm_candidates(long_term_class)
            profile_time['harmonic_alignment'] += real_time_func() - t_start
            
            t_start = real_time_func()
            bpm_pearson, score_pearson = evaluate_specific_bpms(custom_odf_buffer, candidates)
            profile_time['evaluate_specific_bpms'] += real_time_func() - t_start

            winning_class = bpm_to_class(bpm_pearson)
            min_d_win, aligned_winning_class = harmonic_alignment(winning_class, long_term_class)
            diff_win = (aligned_winning_class - long_term_class + 0.5) % 1.0 - 0.5
            long_term_class = (long_term_class + 0.5 * diff_win) % 1.0 
            
            listener.analyzer.bpm = bpm_pearson
            
        if frame % int(SIMULATED_FPS) == 0:
            history_time.append(playhead_time)
            history_raw_bpm.append(60.0 * (2 ** best_class) if 'best_class' in locals() else 120)
            history_pearson.append(bpm_pearson if 'bpm_pearson' in locals() else 120)
            history_class.append(best_class if 'best_class' in locals() else 0)
            history_ltm_class.append(long_term_class)

        audio_time += TIME_PER_FRAME
        mock_timer.current_time += TIME_PER_FRAME
        playhead_time += TIME_PER_FRAME
        frame += 1

    ListenerModule.time.time = time.time 
    
    print("Simulation Complete!")
    print("\n=== PROFILING RESULTS ===")
    for k, v in profile_time.items():
        print(f"{k}: {v:.3f} seconds")
    return history_time, history_raw_bpm, history_pearson, history_class, history_ltm_class

h_time, h_raw_bpm, h_pearson, h_class, h_ltm_class = run_simulation(y_list)

song_durations = [len(y)/44100.0 for y in y_list]
song_start_times = [0.0]
for d in song_durations[:-1]:
    song_start_times.append(song_start_times[-1] + d)

song_names = ['Palladium (117)', 'Pumped Up Kicks (128)', 'Nobody Rules the Streets (128)']
end_time = song_start_times[-1] + song_durations[-1]


# --- PLOT 1 ---

for i in range(len(song_names)):
    t_start = song_start_times[i]
    t_end = song_start_times[i+1] if i+1 < len(song_start_times) else end_time
    target_bpm = 117 if i == 0 else 128
    color = 'magenta' if i == 0 else 'yellow'
    


# --- PLOT 2 ---

for i in range(len(song_names)):
    t_start = song_start_times[i]


