import json

def patch_add_trust():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Initialize history_trust
            init_old = """history_time = []
history_bpm = []
history_bass = []
history_treble = []"""
            
            init_new = """history_time = []
history_bpm = []
history_bass = []
history_treble = []
history_trust = []"""
            if init_old in source:
                source = source.replace(init_old, init_new)

            # 2. Set default bpm_trust before loop
            trust_init_old = """# BPM Trust Variables for Song Changes
long_term_bpm = 120.0
ltm_trust = 10.0 # Arbitrary warm-up scalar
bpm_jump_threshold = 15.0 # BPM change needed to trigger song reset"""
            
            trust_init_new = """# BPM Trust Variables for Song Changes
long_term_bpm = 120.0
ltm_trust = 10.0 # Arbitrary warm-up scalar
bpm_jump_threshold = 15.0 # BPM change needed to trigger song reset
bpm_trust = 10.0 # Default starting trust"""
            if trust_init_old in source:
                source = source.replace(trust_init_old, trust_init_new)

            # 3. Append history_trust in the loop
            append_old = """    history_time.append(playhead_time)
    history_bpm.append(listener.bpm)
    history_bass.append(current_bass)
    history_treble.append(current_treble)"""
            
            append_new = """    history_time.append(playhead_time)
    history_bpm.append(listener.bpm)
    history_bass.append(current_bass)
    history_treble.append(current_treble)
    history_trust.append(bpm_trust)"""
            if append_old in source:
                source = source.replace(append_old, append_new)

            # 4. Modify Plotting Code
            plot_vars_old = """time_arr = np.array(history_time)
bpm_arr = np.array(history_bpm)
bass_arr = np.array(history_bass)
treble_arr = np.array(history_treble)"""
            
            plot_vars_new = """time_arr = np.array(history_time)
bpm_arr = np.array(history_bpm)
bass_arr = np.array(history_bass)
treble_arr = np.array(history_treble)
trust_arr = np.array(history_trust)"""
            if plot_vars_old in source:
                source = source.replace(plot_vars_old, plot_vars_new)

            plot_cmd_old = """plt.plot(time_arr, bpm_arr, color="#00bcd4", linewidth=2.5, label="BPM / Time Track")

# Plot only Song Changes"""
            
            plot_cmd_new = """plt.plot(time_arr, bpm_arr, color="#00bcd4", linewidth=2.5, label="BPM / Time Track")

# Scale the BPM trust up to fit beautifully on the same Y-axis as BPM (usually around 100-140)
# A trust of 10-15 gets scaled up: Let's multiply by 2 and add 60 as a base offset
plt.plot(time_arr, trust_arr * 2 + 60, color="#8bc34a", linewidth=1.5, alpha=0.8, label="BPM Trust (scaled)")

# Plot only Song Changes"""
            if plot_cmd_old in source:
                source = source.replace(plot_cmd_old, plot_cmd_new)

            # Assign text back
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_add_trust()
    print("Notebook ready to track and plot BPM Trust.")
