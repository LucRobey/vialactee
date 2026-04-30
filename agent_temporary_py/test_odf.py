import numpy as np
import librosa
import sys
import os

print("Loading audio...")
AUDIO_FILE = 'mp3_files/01-Plastic-People.mp3'

# Read audio via librosa
y, sr = librosa.load(AUDIO_FILE, duration=60)

# Simulate listener updates frame-by-frame
fps = 60
hop_length = int(sr / fps)
total_frames = int(len(y) / hop_length)

onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

print("Running librosa beat tracker...")
tempo, beat_frames_lib = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
beat_times = librosa.frames_to_time(beat_frames_lib, sr=sr, hop_length=hop_length)

beat_indices = beat_frames_lib

upbeat_indices = []
for i in range(len(beat_indices) - 1):
    upbeat_indices.append((beat_indices[i] + beat_indices[i+1]) // 2)

def get_max_flux_around(idx, window=3):
    start = max(0, idx - window)
    end = min(len(onset_env), idx + window + 1)
    if start < end:
        return np.max(onset_env[start:end])
    return 0

beat_max_flux = [get_max_flux_around(i) for i in beat_indices if i < len(onset_env)]
upbeat_max_flux = [get_max_flux_around(i) for i in upbeat_indices if i < len(onset_env)]

print(f"Average ODF at True Beats: {np.mean(beat_max_flux):.4f}")
print(f"Average ODF at Upbeats: {np.mean(upbeat_max_flux):.4f}")

offbeat_stronger = 0
total_pairs = min(len(beat_max_flux), len(upbeat_max_flux))
for i in range(total_pairs):
    if upbeat_max_flux[i] > beat_max_flux[i]:
        offbeat_stronger += 1

print(f"Upbeat was stronger than Downbeat {offbeat_stronger} out of {total_pairs} times ({(offbeat_stronger/total_pairs)*100:.1f}%)")
