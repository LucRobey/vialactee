import json

def fix_jupyter():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source_str = "".join(cell['source'])
        
        # If this is the last cell with window plotting logic
        if "window_fn = filter_window(" in source_str and "plt.show()" in source_str:
            
            # Remove any user attempts at filtering bass/treble with filter_window
            if "bass_arr = filter_window" in source_str:
                source_str = source_str.replace("bass_arr = filter_window(bass_arr, start_time, end_time)\n", "")
            if "treble_arr = filter_window" in source_str:
                source_str = source_str.replace("treble_arr = filter_window(treble_arr, start_time, end_time)\n", "")

            # Fix the incorrect plotting if the user added it
            if "plt.plot(times_onset[mask], bass_arr * 10 + 60" in source_str:
                source_str = source_str.replace(
                    'plt.plot(times_onset[mask], bass_arr * 10 + 60, color="blue", linewidth=1.0, alpha=0.6, label="Bass Flux (scaled)")\n',
                    ''
                )
            if 'plt.plot(times_onset[mask], treble_arr * 10 + 60, color="orange"' in source_str:
                source_str = source_str.replace(
                    'plt.plot(times_onset[mask], treble_arr * 10 + 60, color="orange", linewidth=1.0, alpha=0.6, label="Treble Flux (scaled)")\n',
                    ''
                )
            
            # Now let's inject our proper filter and plot just above the scatter points
            
            replacement = """
# Filter bass and treble curves using the time_arr array mask!
mask_hist = (time_arr >= start_time) & (time_arr <= end_time)
time_arr_window = time_arr[mask_hist]
bass_arr_window = bass_arr[mask_hist]
treble_arr_window = treble_arr[mask_hist]

# Plot Bass & Treble flux correctly against time_arr_window!
# max_onset is usually 10-30. Multiply fluxes to fit chart if needed. Let's just plot them raw for now.
plt.plot(time_arr_window, bass_arr_window, color='blue', linewidth=1.5, alpha=0.6, label='Bass Flux (raw)')
plt.plot(time_arr_window, treble_arr_window, color='orange', linewidth=1.5, alpha=0.6, label='Treble Flux (raw)')

# Scatter points for detections
"""
            # Replace the generic comment header before scatter points to precisely inject this
            source_str = source_str.replace("# Scatter points for detections\n", replacement[1:]) # Drop starting newline
            
            # rebuild cell lines
            lines = []
            parts = source_str.split('\n')
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
    fix_jupyter()
    print("Notebook plot fixed!")
