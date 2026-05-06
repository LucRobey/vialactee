import json

with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') != 'code':
        continue
    source = cell.get('source', [])
    updated_source = []
    for line in source:
        # Patch librosa load to ensure 44100 sample rate
        if 'y_full, sr = librosa.load(AUDIO_FILE)' in line:
            line = line.replace('y_full, sr = librosa.load(AUDIO_FILE)', 'y_full, sr = librosa.load(AUDIO_FILE, sr=44100)')
            
        # Patch the coarse bpm limits
        if 'coarse_bpm = listener.bpm if (60 < listener.bpm < 180)' in line:
            line = line.replace('60 < listener.bpm < 180', '50 < listener.bpm < 220')
        if 'bpm_evals = np.arange(max(60.0, center_bpm - search_radius), min(180.0, center_bpm + search_radius + step/2), step)' in line:
            line = line.replace('max(60.0, center_bpm - search_radius)', 'max(50.0, center_bpm - search_radius)')
            line = line.replace('min(180.0, center_bpm + search_radius + step/2)', 'min(220.0, center_bpm + search_radius + step/2)')
            
        updated_source.append(line)
        
    cell['source'] = updated_source

with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook patched successfully!")
