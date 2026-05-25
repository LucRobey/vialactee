import pickle
import numpy as np
import matplotlib.pyplot as plt

with open('results_dump.pkl', 'rb') as f:
    results = pickle.load(f)

# We will plot the timeline for Plastic People which had a massive 415 missed beat burst
song = '01-Plastic-People.mp3'
res = results[song]

our_beats = np.array(res['our_beats'])
librosa_beats = np.array(res['librosa_beats'])

# Find the start of the massive missed burst to zoom in on it
# A missed burst is where there are no 'our_beats' within 70ms of a 'librosa_beat'
is_missed = []
for b in librosa_beats:
    if len(our_beats) > 0:
        dist = np.min(np.abs(our_beats - b))
        is_missed.append(dist > 0.070)
    else:
        is_missed.append(True)

# Find the longest True sequence
max_len = 0
max_start_idx = 0
current_len = 0
current_start = 0

for i, flag in enumerate(is_missed):
    if flag:
        if current_len == 0:
            current_start = i
        current_len += 1
    else:
        if current_len > max_len:
            max_len = current_len
            max_start_idx = current_start
        current_len = 0

if current_len > max_len:
    max_len = current_len
    max_start_idx = current_start

burst_start_time = librosa_beats[max_start_idx]
# We want to show a 10 second window right around when the burst starts
window_start = max(0, burst_start_time - 5)
window_end = burst_start_time + 15

# Filter beats in window
lib_window = librosa_beats[(librosa_beats >= window_start) & (librosa_beats <= window_end)]
our_window = our_beats[(our_beats >= window_start) & (our_beats <= window_end)]

plt.figure(figsize=(15, 4))
# Plot True beats (Librosa) as blue vertical lines
for b in lib_window:
    plt.axvline(x=b, color='blue', linestyle='-', alpha=0.6, ymin=0.5, ymax=1.0)
    
# Plot Our beats as red vertical lines
for b in our_window:
    plt.axvline(x=b, color='red', linestyle='--', alpha=0.8, ymin=0.0, ymax=0.5)

plt.axvspan(burst_start_time, window_end, color='gray', alpha=0.2, label='Flywheel Muted (No beats emitted)')

# Dummy lines for legend
plt.plot([], [], color='blue', linestyle='-', label='True Beats (Librosa)')
plt.plot([], [], color='red', linestyle='--', label='Our Tracker Beats')
plt.legend(loc='upper right')

plt.title(f"Beat Timeline: {song}\nZoomed into the moment the Flywheel mutes itself")
plt.xlabel("Time (seconds)")
plt.yticks([])  # Hide y-axis

plt.tight_layout()
plt.savefig('timeline.png', dpi=150)
print("Saved timeline.png")
