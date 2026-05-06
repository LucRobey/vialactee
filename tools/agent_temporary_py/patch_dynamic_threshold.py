import json

def patch_dynamic_threshold():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Variables
            old_init = """structural_changes = []
last_structural_change_frame = -9999
STRUCTURAL_COOLDOWN_FRAMES = int(20.0 * SIMULATED_FPS)
NOVELTY_THRESHOLD = 0.2
power_weight = 0.2
SONG_NOVELTY_THRESHOLD = 0.40 # Trigger song change on massive DJ crossfades # Sensitivity to be tweaked later"""

            new_init = """structural_changes = []
last_structural_change_frame = -9999
STRUCTURAL_COOLDOWN_FRAMES = int(20.0 * SIMULATED_FPS)

# Advanced Adaptive Cooldown
NOVELTY_THRESHOLD_MIN = 0.15
current_novelty_threshold = NOVELTY_THRESHOLD_MIN
NOVELTY_DECAY_RATE = 0.999 # Reduce threshold by 0.1% every frame

power_weight = 0.2
SONG_NOVELTY_THRESHOLD = 0.40 # Trigger song change on massive DJ crossfades # Sensitivity to be tweaked later"""

            if old_init in source:
                source = source.replace(old_init, new_init)

            # 2. History Arrays
            if "history_combined_nov = []" in source:
                source = source.replace("history_combined_nov = []", "history_combined_nov = []\nhistory_nov_threshold = []")

            # 3. Main Logic Loop Update
            old_logic = """    # Calculate Power Novelty (normalized by LTM to detect relative drops/surges)
    power_novelty = np.abs(stm_power - ltm_power) / (ltm_power + 1.0)
    
    # Combined Novelty Score
    combined_novelty = timbral_novelty + (power_novelty * 0.2)
    
    # Structural Boundary (Verse / Chorus) OR Seamless DJ crossfade
    if combined_novelty > NOVELTY_THRESHOLD and (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
        
        # If the structure disruption is astronomically high, it's a crossfade to a new track!
        if combined_novelty > SONG_NOVELTY_THRESHOLD:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
                song_changes.append(playhead_time)
                # Note: We DO NOT flush the lookahead phase queue here!
                # Because if the DJ seamlessly beatmatched the crossfade, we want the rhythmic flywheel
                # to stay perfectly locked into the groove without interruption!
        else:
            structural_changes.append(playhead_time)
            
        last_structural_change_frame = frame
        # Pull LTM into STM to reset distance
        ltm_timbre = np.copy(stm_timbre)
        ltm_power = stm_power"""

            new_logic = """    # Calculate Power Novelty (normalized by LTM to detect relative drops/surges)
    power_novelty = np.abs(stm_power - ltm_power) / (ltm_power + 1.0)
    
    # Combined Novelty Score
    combined_novelty = timbral_novelty + (power_novelty * 0.2)
    
    # Elevating Adaptive Threshold (Decay Phase)
    current_novelty_threshold = max(NOVELTY_THRESHOLD_MIN, current_novelty_threshold * NOVELTY_DECAY_RATE)
    
    # Structural Boundary (Verse / Chorus) OR Seamless DJ crossfade
    # We now evaluate against the dynamic `current_novelty_threshold`
    if combined_novelty > current_novelty_threshold:
        
        # If the structure disruption is astronomically high, it's a crossfade to a new track!
        if combined_novelty > SONG_NOVELTY_THRESHOLD:
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 20.0:
                song_changes.append(playhead_time)
                # Note: We DO NOT flush the lookahead phase queue here!
                # Because if the DJ seamlessly beatmatched the crossfade, we want the rhythmic flywheel
                # to stay perfectly locked into the groove without interruption!
                
            # Elevate threshold dynamically based on the massive novelty drop!
            current_novelty_threshold = combined_novelty
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

            if old_logic in source:
                source = source.replace(old_logic, new_logic)

            # 4. History Appending Wait, "if frame % (int(SIMULATED_FPS / 60)) == 0:"
            old_history = """        history_power_nov.append(power_novelty)
        history_combined_nov.append(combined_novelty)
        playhead_time += TIME_PER_FRAME"""
            new_history = """        history_power_nov.append(power_novelty)
        history_combined_nov.append(combined_novelty)
        history_nov_threshold.append(current_novelty_threshold)
        playhead_time += TIME_PER_FRAME"""

            if old_history in source:
                source = source.replace(old_history, new_history)

            # 5. Plotting Update
            old_plot = "ax2.axhline(y=0.15, color='gray', linestyle='--', alpha=0.5, label='Threshold (0.15)')"
            new_plot = """# Plot our new beautiful decaying dynamic threshold
    history_threshold_arr = np.array(history_nov_threshold)
    ax2.plot(time_arr, history_threshold_arr, color='magenta', linestyle='--', linewidth=2.0, alpha=0.7, label='Dynamic Adaptive Threshold')"""

            if old_plot in source:
                source = source.replace(old_plot, new_plot)

            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_dynamic_threshold()
