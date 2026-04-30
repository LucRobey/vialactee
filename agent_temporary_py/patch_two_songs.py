import json

def patch_two_songs():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            audio_load_old = """print(f"Loading {AUDIO_FILE} full audio for Ground Truth Benchmarks...")
y_full, sr = librosa.load(AUDIO_FILE, sr=44100)

print("Running non-causal Librosa Beat Track...")
onset_env_full = librosa.onset.onset_strength(y=y_full, sr=sr)
tempo_librosa, beat_frames_true = librosa.beat.beat_track(onset_envelope=onset_env_full, sr=sr)
true_beat_times = librosa.frames_to_time(beat_frames_true, sr=sr)"""

            audio_load_new = """f1 = 'mp3_files/01-Plastic-People.mp3'
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
onset_env_full = np.concatenate([onset_1, onset_2])
tempo_librosa = t1 # Used for the first plot horizontal line"""

            if audio_load_old in source:
                source = source.replace(audio_load_old, audio_load_new)
            
            # Change the evaluation plotting window to show the entire transition
            plot_window_old = """start_time = 60
end_time = 80"""
            # We want to span across the transition! Plastic People is ~355 seconds long. Let's do 340 to 370.
            plot_window_new = """# Span across the transition boundary! Plastic People is ~354s long.
shift_sec = len(y_1) / sr
start_time = shift_sec - 15.0
end_time = shift_sec + 15.0"""
            if plot_window_old in source:
                source = source.replace(plot_window_old, plot_window_new)

            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_two_songs()
    print("Notebook updated to use 2 songs back-to-back.")
