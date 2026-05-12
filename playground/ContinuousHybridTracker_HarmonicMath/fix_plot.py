import json

file_path = r'c:\Users\Users\Desktop\vialactée\vialactee\playground\ContinuousHybridTracker_HarmonicMath\ContinuousHybridTracker_HarmonicMath.ipynb'
with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        # Insert end_time right after song_names
        for i, line in enumerate(source):
            if "song_names = ['Palladium" in line:
                source.insert(i+1, "    \"end_time = song_start_times[-1] + song_durations[-1]\\n\",\n")
                break
                
        for i, line in enumerate(source):
            if "plt.axhline(145, color='magenta'" in line:
                source[i] = line.replace("plt.axhline(145, color='magenta', linestyle='--', label='Target 145')", "plt.plot([song_start_times[0], song_start_times[1]], [145, 145], color='magenta', linestyle='--', label='Target 145')")
            elif "plt.axhline(128, color='yellow'" in line:
                source[i] = line.replace("plt.axhline(128, color='yellow', linestyle='--', label='Target 128')", "plt.plot([song_start_times[1], end_time], [128, 128], color='yellow', linestyle='--', label='Target 128')")

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
print('Done')
