import pickle
import numpy as np
import matplotlib.pyplot as plt

with open('results_dump.pkl', 'rb') as f:
    results = pickle.load(f)

song = '01-Plastic-People.mp3'
res = results[song]

our_beats = np.array(res['our_beats'])
librosa_beats = np.array(res['librosa_beats'])

window_start = 67
window_end = 90

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

# Calculate muting spans (no our_beats emitted) to shade them gray
# A beat is muted if distance to nearest our_beats is > 0.070
muted_starts = []
muted_ends = []
in_mute = False
for b in lib_window:
    dist = np.min(np.abs(our_beats - b)) if len(our_beats) > 0 else 999
    is_muted = dist > 0.070
    if is_muted and not in_mute:
        muted_starts.append(b - 0.2)
        in_mute = True
    elif not is_muted and in_mute:
        muted_ends.append(b - 0.2)
        in_mute = False
if in_mute:
    muted_ends.append(window_end)

for s, e in zip(muted_starts, muted_ends):
    plt.axvspan(s, e, color='gray', alpha=0.2)

# Dummy lines for legend
plt.plot([], [], color='blue', linestyle='-', label='True Beats (Librosa)')
plt.plot([], [], color='red', linestyle='--', label='Our Tracker Beats')
if muted_starts:
    plt.plot([], [], color='gray', alpha=0.2, linewidth=10, label='Flywheel Muted')

plt.legend(loc='upper right')

plt.title(f"Beat Timeline: {song} (67s to 90s)")
plt.xlabel("Time (seconds)")
plt.yticks([])  # Hide y-axis
plt.xlim([window_start, window_end])

plt.tight_layout()
plt.savefig('timeline_plastic_people.png', dpi=150)
print("Saved timeline_plastic_people.png")
