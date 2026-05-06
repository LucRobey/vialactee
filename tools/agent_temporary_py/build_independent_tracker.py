import json
import os

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

add_markdown("""# 🔬 Independent 5-Second Lookahead Tracker

This notebook is an isolated sandbox. It does **not** rely on `Listener.py`, `Simulated_Microphone.py`, or any existing project files.
Instead, it simulates how a live streaming system can use a rolling **5-second buffer** of audio, extract its own onset envelope, 
and mathematically track beats exclusively inside that 5-second window.

Processing settings:
- **60 FPS** (simulated 16ms chunk updates)
- **Sub-beats** are triggered algorithmically strictly at `tempo / 2` intervals.
""")

add_code("""import librosa
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')
""")

add_markdown("### 1. Ground Truth Generation\nFirst, we generate the exact answers using Librosa on the full song to serve as our evaluation benchmark.")

add_code("""audio_file = 'resources/01.mp3'
print("Loading full audio for Librosa Ground Truth (this takes a few seconds)...")
y_full, sr = librosa.load(audio_file)

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

add_markdown("### 2. The Sandbox 5-Second Streaming Environment\nHere we pretend we only have live incoming frames. We extract Onset Envelopes (Spectral Flux) live, store 5 seconds (300 frames) in a rolling buffer, and calculate the tempo/phase strictly within that isolated buffer.")

add_code("""# Configuration
FPS = 60
CHUNK_SAMPLES = int(sr / FPS)
FRAME_DURATION = 1.0 / FPS
BUFFER_SECONDS = 5.0
BUFFER_SIZE = int(BUFFER_SECONDS * FPS)  # 300 frames

# Extract audio into simulated 'chunks'
total_chunks = len(y_full) // CHUNK_SAMPLES
print(f"Simulating streaming of {total_chunks} audio chunks at {FPS} FPS...")

# Independent Algorithm State
onset_buffer = np.zeros(BUFFER_SIZE)
playhead_time = 0.0

extracted_beats = []
extracted_sub_beats = []

# Autocorrelation variables
last_beat_time = -999.0
last_sub_beat_time = -999.0

# Pre-compute an aggressive Hanning window to weight the center 
# of our 5-second buffer heavier than the edges
window_weight = np.hanning(BUFFER_SIZE)

# We define the minimum and maximum BPM we care about to scan
MIN_BPM = 60
MAX_BPM = 180
lag_min = int(FPS * 60 / MAX_BPM)
lag_max = int(FPS * 60 / MIN_BPM)

# Keep track of previous spectra to compute flux
S_prev = None

for chunk_idx in range(total_chunks):
    # 1. Grab 16ms of audio
    start = chunk_idx * CHUNK_SAMPLES
    end = start + CHUNK_SAMPLES
    chunk = y_full[start:end]
    
    # 2. Extract Spectral Flux (Onset Strength) for this chunk
    # We do a fast STFT on just this small segment
    S_curr = np.abs(librosa.stft(chunk, n_fft=CHUNK_SAMPLES if CHUNK_SAMPLES >= 2048 else 2048))
    if S_prev is not None:
        flux = np.sum(np.maximum(0, S_curr - S_prev))  # Half-wave rectification
    else:
        flux = 0.0
    S_prev = S_curr
    
    # 3. Slide the buffer and insert the new flux
    onset_buffer = np.roll(onset_buffer, -1)
    onset_buffer[-1] = flux
    
    # Wait until buffer is initially full before popping playhead
    if chunk_idx >= BUFFER_SIZE:
        playhead_time = (chunk_idx - BUFFER_SIZE) * FRAME_DURATION
        
        # We are evaluating the frame that is popping off the BACK of the queue (index 0)
        # But we use the entire 5 seconds to decide if it's a beat!
        
        # 4. Localized Tempo Extraction (Autocorrelation on the 5s window)
        weighted_onset = onset_buffer * window_weight
        autocorr = scipy.signal.correlate(weighted_onset, weighted_onset, mode='full')
        autocorr = autocorr[len(autocorr)//2:] # Keep positive lags
        
        # Find the peak in the valid BPM range
        valid_autocorr = autocorr[lag_min:lag_max]
        if len(valid_autocorr) > 0:
            best_lag = np.argmax(valid_autocorr) + lag_min
            current_bpm = (60.0 * FPS) / best_lag
            
            # 5. Phase Alignment via mathematical comb filter
            # We want to see if a beat lands exactly on index 0 (our playhead)
            # We sum the onset strengths across the sequence: 0, best_lag, 2*best_lag...
            
            phase_score = 0
            for i in range(0, BUFFER_SIZE, best_lag):
                phase_score += onset_buffer[i]
                
            # If the onset power exactly on our output frame + harmonic multiples
            # clears an adaptive threshold, WE FIRE!
            adaptive_avg = np.mean(onset_buffer) * 2.5
            
            # BEAT TRIGGER
            if phase_score > adaptive_avg and (playhead_time - last_beat_time) > (60.0/current_bpm)*0.6:
                extracted_beats.append(playhead_time)
                last_beat_time = playhead_time
                
            # SUB BEAT TRIGGER (Tempo / 2 offset)
            sub_lag = best_lag // 2
            sub_phase_score = 0
            for i in range(sub_lag, BUFFER_SIZE, best_lag):
                sub_phase_score += onset_buffer[i]
                
            if sub_phase_score > adaptive_avg and (playhead_time - last_sub_beat_time) > (60.0/current_bpm)*0.4:
                # Make sure we aren't firing a sub beat ON TOP of a main beat
                if (playhead_time - last_beat_time) > 0.1:
                    extracted_sub_beats.append(playhead_time)
                    last_sub_beat_time = playhead_time

    if chunk_idx % 3000 == 0:
        print(f"Simulating audio chunk {chunk_idx}/{total_chunks}...")

extracted_beats = np.array(extracted_beats)
extracted_sub_beats = np.array(extracted_sub_beats)
print(f"🏁 Independent Streaming Complete! Extracted {len(extracted_beats)} beats, {len(extracted_sub_beats)} sub-beats.")
""")

add_markdown("### 3. Evaluation Metrics\nWe use the strict `TOLERANCE_WINDOW` of 150ms to judge if our independent math was accurate.")

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

m_hits, m_wrongs, m_misses, m_precision, m_recall, m_f1, m_alg_main, m_true = evaluate_single_stream(extracted_beats, true_beat_times, TOLERANCE_WINDOW)
s_hits, s_wrongs, s_misses, s_precision, s_recall, s_f1, m_alg_sub, m_true_sub = evaluate_single_stream(extracted_sub_beats, true_subbeat_times, TOLERANCE_WINDOW)

total_hits = m_hits + s_hits
total_wrongs = m_wrongs + s_wrongs
total_misses = m_misses + s_misses
total_alg = len(extracted_beats) + len(extracted_sub_beats)
total_true = len(true_beat_times) + len(true_subbeat_times)

tot_precision = total_hits / total_alg if total_alg > 0 else 0
tot_recall = total_hits / total_true if total_true > 0 else 0
tot_f1 = 2 * (tot_precision * tot_recall) / (tot_precision + tot_recall) if (tot_precision + tot_recall) > 0 else 0

print("============ 📈 EVALUATION REPORT ============")
print(f"Tolerance Window: +/- {int(TOLERANCE_WINDOW*1000)}ms")
print(f"Total True Beats: {len(true_beat_times)} | Total Sub-beats: {len(true_subbeat_times)}")
print(f"Total Independent Beats: {len(extracted_beats)} | Total Independent Sub-beats: {len(extracted_sub_beats)}")
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

output_file = 'IndependentLookaheadTracker.ipynb'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1)

print(f"Successfully generated {output_file}!")
