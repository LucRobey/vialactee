import json

def patch_notebook():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Initialization code
            if 'frames_between_sweep =' in source and 'Structural Novelty Variables' not in source:
                target_str1 = 'print("🚀 Starting Hybrid Simulation Loop...")'
                if target_str1 in source:
                    init_code = """
# Structural Novelty Variables
stm_timbre = np.zeros(8)
ltm_timbre = np.zeros(8)
stm_weight = 0.02  # ~1.5s smoothing
ltm_weight = 0.005 # ~6.0s smoothing

structural_changes = []
last_structural_change_frame = -9999
STRUCTURAL_COOLDOWN_FRAMES = int(5.0 * SIMULATED_FPS)
NOVELTY_THRESHOLD = 0.15 # Sensitivity to be tweaked later

song_changes = []
silence_frames = 0
SILENCE_THRESHOLD_FRAMES = int(1.5 * SIMULATED_FPS)

print("🚀 Starting Hybrid Simulation Loop...")"""
                    source = source.replace(target_str1, init_code)

            # 2. Main Logic code
            target_str2 = """while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()"""
            if target_str2 in source and '# 0. Feature Extraction & Novelty Detection' not in source:
                logic_code = """while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()
    
    # 0. Feature Extraction & Novelty Detection (Verse/Chorus & Song boundaries)
    current_timbre = listener.band_proportion

    # Update Short-Term and Long-Term Memory
    stm_timbre = (1 - stm_weight) * stm_timbre + stm_weight * current_timbre
    ltm_timbre = (1 - ltm_weight) * ltm_timbre + ltm_weight * current_timbre
    
    # Calculate Timbral Novelty (Euclidean distance)
    timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)
    
    # Structural Boundary (Verse / Chorus)
    if timbral_novelty > NOVELTY_THRESHOLD and (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
        structural_changes.append(playhead_time)
        last_structural_change_frame = frame
        # Pull LTM into STM to reset distance
        ltm_timbre = np.copy(stm_timbre)

    # Song Change Detection (Silence / Trust Drop)
    if listener.smoothed_total_power < 5.0:
        silence_frames += 1
    else:
        silence_frames = 0
        
    if silence_frames > SILENCE_THRESHOLD_FRAMES:
        if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
            song_changes.append(playhead_time)
            # Flush the lookahead queue
            future_queue.clear()
            standalone_beat_count = 0
            last_standalone_beat_count = 0
            standalone_sub_beat_locked = -1
            standalone_phase = 0.0
            
            # Reset Listener history
            listener.band_means.fill(0.0)
            listener.smoothed_fft_band_values.fill(0.0)
            listener.odf_buffer.fill(0.0)
"""
                source = source.replace(target_str2, logic_code)
                
            # 3. Plotting Code
            target_str3 = "plt.title(\"Rhythm Tracking Over Full Audio Duration\")"
            if target_str3 in source and 'structural_changes' not in source:
                plot_code = """
for sid, s_time in enumerate(structural_changes):
    plt.axvline(s_time, color='red', linestyle='--', linewidth=2, label='Verse/Chorus Boundary' if sid == 0 else "")

for sid, s_time in enumerate(song_changes):
    plt.axvline(s_time, color='black', linestyle='-', linewidth=4, label='Song Change' if sid == 0 else "")

plt.title("Rhythm Tracking Over Full Audio Duration")"""
                source = source.replace(target_str3, plot_code)
                
            # Convert back to ipynb lines format
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    
if __name__ == '__main__':
    patch_notebook()
    print("Notebook patched.")
