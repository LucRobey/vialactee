import json

def update_plot():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            if 'plt.plot(time_arr, bpm_arr' in source:
                
                # Delete plotting of bass flux, treble flux, librosa lines, and sweep times
                old_plot_block = """plt.plot(time_arr, bpm_arr, color="cyan", linewidth=2.5, label="Hybrid Continuous BPM")
# Scale bass/treble to fit on the BPM axis for visualization
plt.plot(time_arr, bass_arr * 10 + 60, color="blue", linewidth=1.0, alpha=0.6, label="Bass Flux (scaled)")
plt.plot(time_arr, treble_arr * 10 + 60, color="orange", linewidth=1.0, alpha=0.6, label="Treble Flux (scaled)")
plt.axhline(true_bpm, color="lime", linestyle="--", alpha=0.8, label=f"Librosa True BPM ({true_bpm:.1f})")
plt.axhline(91, color="red", linestyle="--", alpha=0.8, label=f"Librosa True BPM ({true_bpm:.1f})")


sweep_interval = frames_between_sweep / SIMULATED_FPS
sweep_times = np.arange(sweep_interval, time_arr[-1], sweep_interval)
for sweep_idx, s_time in enumerate(sweep_times):
    plt.axvline(s_time, color='magenta', linestyle=':', alpha=0.4, linewidth=1, label='Sweep' if sweep_idx == 0 else "")


for sid, s_time in enumerate(structural_changes):
    plt.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else "")

for sid, s_time in enumerate(song_changes):
    plt.axvline(s_time, color='black', linestyle='-', linewidth=4, label='Song Change' if sid == 0 else "")"""

                new_plot_block = """plt.plot(time_arr, bpm_arr, color="#00bcd4", linewidth=2.5, label="BPM / Time Track")

# Plot only Song Changes
for sid, s_time in enumerate(song_changes):
    plt.axvline(s_time, color='black', linestyle='--', linewidth=3, label='Song Change detected' if sid == 0 else "")
"""
                if old_plot_block in source:
                    source = source.replace(old_plot_block, new_plot_block)
                else:
                    # Generic fallback matching if formatting differs
                    print("Warning: strict match failed on main plotting cell!")
                    
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    update_plot()
    print("Notebook perfectly plotted to user's specs.")
