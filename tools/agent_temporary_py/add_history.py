import json

def modify():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source = "".join(cell['source'])
        
        changed = False
        
        # 1. Initialize history_bass and history_treble near history_bpm
        if "history_bpm = []" in source and "history_bass = []" not in source:
            source = source.replace("history_bpm = []", "history_bpm = []\n    history_bass = []\n    history_treble = []")
            changed = True
            
        # 2. Append in the main loop
        if "history_bpm.append(present['bpm'])" in source:
            source = source.replace(
                "history_bpm.append(present['bpm'])", 
                "history_bpm.append(present['bpm'])\n        history_bass.append(present.get('bass_flux', 0.0))\n        history_treble.append(present.get('treble_flux', 0.0))"
            )
            changed = True
            
        # 3. Add to charting logic
        if "bpm_arr = np.array(history_bpm)" in source and "bass_arr =" not in source:
            source = source.replace(
                "bpm_arr = np.array(history_bpm)",
                "bpm_arr = np.array(history_bpm)\n    bass_arr = np.array(history_bass)\n    treble_arr = np.array(history_treble)"
            )
            
            # The user wants to plot them on the last plot (or create a new plot)
            source = source.replace(
                'plt.plot(time_arr, bpm_arr, color="cyan", linewidth=2.5, label="Hybrid Continuous BPM")',
                'plt.plot(time_arr, bpm_arr, color="cyan", linewidth=2.5, label="Hybrid Continuous BPM")\n    # Scale bass/treble to fit on the BPM axis for visualization\n    plt.plot(time_arr, bass_arr * 10 + 60, color="blue", linewidth=1.0, alpha=0.6, label="Bass Flux (scaled)")\n    plt.plot(time_arr, treble_arr * 10 + 60, color="orange", linewidth=1.0, alpha=0.6, label="Treble Flux (scaled)")'
            )
            changed = True
            
        if changed:
            lines = []
            parts = source.split('\n')
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    lines.append(part + '\n')
                else:
                    if part:
                        lines.append(part)
            cell['source'] = lines

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    modify()
    print("Notebook modified successfully.")
