import json

def patch_add_song():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            old_load = """f1 = 'mp3_files/01-Plastic-People.mp3'
f2 = 'mp3_files/Nightcall.mp3'

print(f"Loading 2 songs sequentially for Song Change Test...")
y_1, sr = librosa.load(f1, sr=44100)
y_2, sr = librosa.load(f2, sr=44100)

# Simulate DJ crossfade or direct cut (we will do a direct cut here)
y_full = np.concatenate([y_1, y_2])
shift_time = len(y_1) / sr

print("Running non-causal Librosa Beat Track on Song 1...")
onset_1 = librosa.onset.onset_strength(y=y_1, sr=sr)
t1, bf1 = librosa.beat.beat_track(onset_envelope=onset_1, sr=sr)
bt1 = librosa.frames_to_time(bf1, sr=sr)

print("Running non-causal Librosa Beat Track on Song 2...")
onset_2 = librosa.onset.onset_strength(y=y_2, sr=sr)
t2, bf2 = librosa.beat.beat_track(onset_envelope=onset_2, sr=sr)
bt2 = librosa.frames_to_time(bf2, sr=sr)

true_beat_times = np.concatenate([bt1, bt2 + shift_time])
onset_env_full = np.concatenate([onset_1, onset_2])"""

            new_load = """f1 = 'mp3_files/01-Plastic-People.mp3'
f2 = 'mp3_files/Nightcall.mp3'
f3 = 'mp3_files/Palladium.mp3'

print(f"Loading 3 songs sequentially for Song Change Test...")
y_1, sr = librosa.load(f1, sr=44100)
y_2, sr = librosa.load(f2, sr=44100)
y_3, sr = librosa.load(f3, sr=44100)

# Simulate DJ crossfade or direct cut (we will do a direct cut here)
y_full = np.concatenate([y_1, y_2, y_3])
shift_time_2 = len(y_1) / sr
shift_time_3 = shift_time_2 + (len(y_2) / sr)

print("Running non-causal Librosa Beat Track on Song 1...")
onset_1 = librosa.onset.onset_strength(y=y_1, sr=sr)
t1, bf1 = librosa.beat.beat_track(onset_envelope=onset_1, sr=sr)
bt1 = librosa.frames_to_time(bf1, sr=sr)

print("Running non-causal Librosa Beat Track on Song 2...")
onset_2 = librosa.onset.onset_strength(y=y_2, sr=sr)
t2, bf2 = librosa.beat.beat_track(onset_envelope=onset_2, sr=sr)
bt2 = librosa.frames_to_time(bf2, sr=sr)

print("Running non-causal Librosa Beat Track on Song 3...")
onset_3 = librosa.onset.onset_strength(y=y_3, sr=sr)
t3, bf3 = librosa.beat.beat_track(onset_envelope=onset_3, sr=sr)
bt3 = librosa.frames_to_time(bf3, sr=sr)

true_beat_times = np.concatenate([bt1, bt2 + shift_time_2, bt3 + shift_time_3])
onset_env_full = np.concatenate([onset_1, onset_2, onset_3])"""

            if old_load in source:
                source = source.replace(old_load, new_load)
            
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_add_song()
