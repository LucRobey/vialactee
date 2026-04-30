import librosa
import numpy as np
import scipy.signal

y, sr = librosa.load('mp3_files/Nightcall.mp3', sr=22050)
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
print("Librosa tempo:", tempo)

# Let's do a simple autocorrelation of the onset envelope
acf = np.correlate(onset_env - np.mean(onset_env), onset_env - np.mean(onset_env), mode='full')
acf = acf[len(onset_env)-1:]

# Find peaks in ACF corresponding to 60-180 BPM
hop_time = 512 / sr
bpms = np.arange(60, 180, 0.1)
corrs = []
for bpm in bpms:
    period_sec = 60.0 / bpm
    period_frames = period_sec / hop_time
    
    # We can just sum the ACF at multiples of this period
    corr = sum(acf[int(round(k * period_frames))] for k in range(1, 10))
    corrs.append(corr)

best_bpm = bpms[np.argmax(corrs)]
print("Simple ACF max BPM:", best_bpm)

# What if we explicitly print the top 5 BPMs?
top_indices = np.argsort(corrs)[-5:]
for i in reversed(top_indices):
    print(f"Acf peak at: {bpms[i]:.2f}")

