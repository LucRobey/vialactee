import json

filepath = r"c:\Users\Users\Desktop\vialactée\vialactee\ContinuousHybridTracker.ipynb"
with open(filepath, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        if 'history_timbral_nov = []' in source:
            old_history = "history_timbral_nov = []\nhistory_power_nov = []\nhistory_combined_nov = []\nhistory_nov_threshold = []"
            new_history = "history_timbral_nov = []\nhistory_power_nov = []\nhistory_combined_nov = []\nhistory_novelty_lm = []\nhistory_novelty_gm = []\nhistory_asserved_nov = []"
            source = source.replace(old_history, new_history)
            
        if "NOVELTY_THRESHOLD_MIN = 0.15" in source:
            
            # Variables
            source = source.replace("NOVELTY_THRESHOLD_MIN = 0.15\ncurrent_novelty_threshold = NOVELTY_THRESHOLD_MIN", "novelty_lm = 0.5\nnovelty_gm = 0.5\nasserved_novelty = 0.0")
            source = source.replace("NOVELTY_DECAY_RATE = 0.997 # Reduce threshold by 0.5% every frame (faster recovery)\n", "")
            source = source.replace("SONG_NOVELTY_THRESHOLD = 0.28 # Trigger song change on massive DJ crossfades", "SONG_NOVELTY_ASSERVED_TH = 0.8\nSTRUCTURAL_NOVELTY_ASSERVED_TH = 0.6")

            # Logic
            old_logic = """    # Elevating Adaptive Threshold (Decay Phase)
    current_novelty_threshold = max(NOVELTY_THRESHOLD_MIN, current_novelty_threshold * NOVELTY_DECAY_RATE)
    
    # Structural Boundary (Verse / Chorus) OR Seamless DJ crossfade
    # We now evaluate against the dynamic `current_novelty_threshold`
    if combined_novelty > current_novelty_threshold:
        
        # If the structure disruption is astronomically high, it's a crossfade to a new track!
        if combined_novelty > SONG_NOVELTY_THRESHOLD:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
                song_changes.append(playhead_time)
                # Since these are sequential MP3s with abrupt cuts, phase is totally lost.
                # Flush the queue to instantly resync to the new track's groove and transients!
                future_queue.clear()
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.band_means.fill(0.0)
                listener.smoothed_fft_band_values.fill(0.0)
                listener.odf_buffer.fill(0.0)
                
            # Elevate threshold dynamically based on the massive novelty drop!
            current_novelty_threshold = 1.1*combined_novelty
            ltm_timbre = np.copy(stm_timbre)
            ltm_power = stm_power
            
        else:
            # Classic Verse/Chorus change. We still enforce a flat base cooldown to prevent stuttering logic
            if (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
                structural_changes.append(playhead_time)
                last_structural_change_frame = frame
                
                # Elevate threshold dynamically based on the novelty boost!
                current_novelty_threshold = combined_novelty
                # Pull LTM into STM to reset distance
                ltm_timbre = np.copy(stm_timbre)
                ltm_power = stm_power"""

            new_logic = """    # === Local & Global Max Envelope (Asserved Normalization) ===
    if combined_novelty >= novelty_lm:
        novelty_lm = combined_novelty
    else:
        novelty_lm *= 0.9995
        
    if combined_novelty >= novelty_gm:
        novelty_gm = 1.01 * combined_novelty
    else:
        # Scale GM based on how close LM is to GM.
        novelty_gm *= 1 + 0.005 * ((novelty_lm / novelty_gm) - 0.9)
        
    safe_gm = max(0.01, novelty_gm)
    
    # Smooth the target normalization
    target_asserved = combined_novelty / safe_gm
    asserved_novelty += 0.4 * (target_asserved - asserved_novelty)
    
    # === Structural Detection against Normalized Threshold ===
    if asserved_novelty > SONG_NOVELTY_ASSERVED_TH:
        if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
            song_changes.append(playhead_time)
            # Flush the queue to instantly resync to the new track's groove and transients!
            future_queue.clear()
            standalone_beat_count = 0
            last_standalone_beat_count = 0
            standalone_sub_beat_locked = -1
            standalone_phase = 0.0
            listener.band_means.fill(0.0)
            listener.smoothed_fft_band_values.fill(0.0)
            listener.odf_buffer.fill(0.0)
            
            # Reset System Envelopes to enforce an organic cooldown
            novelty_gm = combined_novelty * 1.5 
            asserved_novelty = 0.0
            ltm_timbre = np.copy(stm_timbre)
            ltm_power = stm_power
            
    elif asserved_novelty > STRUCTURAL_NOVELTY_ASSERVED_TH:
        # Classic Verse/Chorus change. We still enforce a flat base cooldown to prevent stuttering logic
        if (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
            structural_changes.append(playhead_time)
            last_structural_change_frame = frame
            
            novelty_lm = combined_novelty
            asserved_novelty = 0.0
            ltm_timbre = np.copy(stm_timbre)
            ltm_power = stm_power"""
            source = source.replace(old_logic, new_logic)

            # Append history
            old_append = "history_nov_threshold.append(current_novelty_threshold)"
            new_append = "history_novelty_lm.append(novelty_lm)\n        history_novelty_gm.append(novelty_gm)\n        history_asserved_nov.append(asserved_novelty)"
            source = source.replace(old_append, new_append)

            # Replace array definition in later cell
            source = source.replace("nov_thr_arr = np.array(history_nov_threshold)", "nov_lm_arr = np.array(history_novelty_lm)\nnov_gm_arr = np.array(history_novelty_gm)\nasserved_nov_arr = np.array(history_asserved_nov)")

        if "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)" in source:
            old_plot = """fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

# TOP PLOT: Power Comparison
ax1.plot(time_arr, stm_power_arr, color='dodgerblue', alpha=0.8, linewidth=1.5, label='Short-Term Power (STM)')
ax1.plot(time_arr, ltm_power_arr, color='darkorange', alpha=0.8, linewidth=2.0, label='Long-Term Power (LTM)')
ax1.set_title("Power Dynamics (STM vs LTM)")
ax1.set_ylabel("Total Smoothed Power")
ax1.legend(loc="upper right")
ax1.grid(alpha=0.3)

for sid, s_time in enumerate(structural_changes):
    ax1.axvline(s_time, color='red', linestyle='--', linewidth=2)
for sid, s_time in enumerate(song_changes):
    ax1.axvline(s_time, color='black', linestyle='-', linewidth=3)

# BOTTOM PLOT: Novelty & Boundaries
ax2.plot(time_arr, timbral_nov_arr, color='purple', alpha=0.5, label='Timbral Novelty')
ax2.plot(time_arr, power_nov_arr, color='orange', alpha=0.5, label='Power Novelty (relative)')
ax2.plot(time_arr, combined_nov_arr, color='red', linewidth=2.0, label='Combined Novelty Score')
ax2.plot(time_arr[:len(nov_thr_arr)],nov_thr_arr,color="grey",label = 'Threshold')

ax2.axhline(0.15, color="black", linestyle=":", label="Threshold (0.15)")
ax2.set_title("Structural Novelty & Segmentation Boundaries")
ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Novelty Score")
ax2.legend(loc="upper right")
ax2.grid(alpha=0.3)

y=0
for k in range(len(y_list)):
    y_k = y_list[k]
    y+= len(y_k)
    plt.axvline(y/sr, color='purple', linestyle='-', linewidth=2, label=f'Real song change {k}')




# Plot the Boundaries
for sid, s_time in enumerate(structural_changes):
    ax2.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else "")
for sid, s_time in enumerate(song_changes):
    ax2.axvline(s_time, color='black', linestyle='-', linewidth=2, label='Song Change' if sid == 0 else "")"""

            new_plot = """fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 13), sharex=True)

# TOP PLOT: Power Comparison
ax1.plot(time_arr, stm_power_arr, color='dodgerblue', alpha=0.8, linewidth=1.5, label='Short-Term Power (STM)')
ax1.plot(time_arr, ltm_power_arr, color='darkorange', alpha=0.8, linewidth=2.0, label='Long-Term Power (LTM)')
ax1.set_title("Power Dynamics (STM vs LTM)")
ax1.set_ylabel("Total Smoothed Power")
ax1.legend(loc="upper right")
ax1.grid(alpha=0.3)

for sid, s_time in enumerate(structural_changes):
    ax1.axvline(s_time, color='red', linestyle='--', linewidth=2)
for sid, s_time in enumerate(song_changes):
    ax1.axvline(s_time, color='black', linestyle='-', linewidth=3)

# MIDDLE PLOT: Raw Novelty vs LM & GM Envelopes
ax2.plot(time_arr, combined_nov_arr, color='red', linewidth=1.5, label='Combined Novelty Score')
ax2.plot(time_arr[:len(nov_lm_arr)], nov_lm_arr, color="grey", linestyle=":", label="Local Max Envelope")
ax2.plot(time_arr[:len(nov_gm_arr)], nov_gm_arr, color="black", linewidth=2.0, alpha=0.6, label="Global Max Envelope")

ax2.set_title("Raw Novelty vs Asserved Envelopes")
ax2.set_ylabel("Novelty Score")
ax2.legend(loc="upper right")
ax2.grid(alpha=0.3)

# BOTTOM PLOT: Asserved Normalized Novelty & Triggers
ax3.plot(time_arr[:len(asserved_nov_arr)], asserved_nov_arr, color='teal', linewidth=2.0, label='Asserved Normalized Novelty')
ax3.axhline(1.0, color="green", linestyle=":", label="Absolute Normalized Peak")
ax3.axhline(0.8, color="black", linestyle="--", linewidth=2.0, label="Song Change Threshold (0.8)")
ax3.axhline(0.6, color="red", linestyle=":", linewidth=2.0, label="Verse/Chorus Threshold (0.6)")

ax3.set_title("Fully Asserved Normalization Signal")
ax3.set_xlabel("Time (seconds)")
ax3.set_ylabel("Asserved value (0-1)")
ax3.legend(loc="upper right")
ax3.grid(alpha=0.3)

y=0
for k in range(len(y_list)):
    y_k = y_list[k]
    y+= len(y_k)
    for ax in [ax2, ax3]:
        ax.axvline(y/sr, color='purple', linestyle='-', linewidth=2, label=f'Real song change {k}' if k==0 else "")

# Plot the Boundaries on both novelty plots
for sid, s_time in enumerate(structural_changes):
    ax2.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else "")
    ax3.axvline(s_time, color='red', linestyle='--', linewidth=2)
for sid, s_time in enumerate(song_changes):
    ax2.axvline(s_time, color='black', linestyle='-', linewidth=2, label='Song Change' if sid == 0 else "")
    ax3.axvline(s_time, color='black', linestyle='-', linewidth=2)"""
            source = source.replace(old_plot, new_plot)

            
        # Repackage string back into list
        if source != "".join(cell['source']):
            lines = source.split('\n')
            cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            print("Successfully updated cell!")

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook Asserved Logic implementation applied.")
