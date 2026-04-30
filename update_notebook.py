import json

def update_notebook():
    file_path = 'ContinuousHybridTracker.ipynb'
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb['cells']:
        if cell['cell_type'] == 'code' and any('plt.subplots(3, 1' in line for line in cell['source']):
            source = cell['source']
            i = 0
            while i < len(source):
                line = source[i]
                if 'plt.subplots(3, 1' in line:
                    source[i] = line.replace('plt.subplots(3, 1, figsize=(15, 13)', 'plt.subplots(4, 1, figsize=(15, 18)')
                elif 'ax3.set_xlabel' in line:
                    source[i] = ''
                elif 'for ax in [ax2, ax3]:' in line:
                    source[i] = line.replace('[ax2, ax3]', '[ax2, ax3, ax4]')
                elif 'ax3.axvline(s_time, color=\'black\'' in line:
                    # Add ax4 line right after
                    source.insert(i+1, '    ax4.axvline(s_time, color=\'black\', linestyle=\'-\', linewidth=2)\n')
                    i += 1 # skip iteration over inserted line
                elif 'plt.tight_layout()' in line:
                    vocal_plot = [
                        '\n',
                        '# BOTTOM PLOT: Vocal Detection\n',
                        'ax4.plot(time_arr, vocal_arr, color=\'magenta\', linewidth=1.5, label=\'Vocal Flux\')\n',
                        'vocal_max = np.max(vocal_arr) if len(vocal_arr) > 0 else 100\n',
                        'ax4.fill_between(time_arr, 0, vocal_max, where=vocals_present_arr, color=\'purple\', alpha=0.2, label=\'Vocals Present Area\')\n',
                        'for ev_i, ev in enumerate(acapella_events):\n',
                        '    ax4.axvline(x=ev, color=\'orange\', linestyle=\'-\', linewidth=3, alpha=0.8, label=\'Acapella Event\' if ev_i == 0 else "")\n',
                        'ax4.set_title("Vocal Flux & Acapella Detection")\n',
                        'ax4.set_xlabel("Time (seconds)")\n',
                        'ax4.set_ylabel("Vocal Flux Energy")\n',
                        'ax4.legend(loc="upper right")\n',
                        'ax4.grid(alpha=0.3)\n',
                        '\n'
                    ]
                    source[i:i] = vocal_plot
                    i += len(vocal_plot)  # fast forward over the inserted code
                i += 1
            break
            
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    update_notebook()
