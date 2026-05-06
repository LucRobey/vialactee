import json

def update_notebook():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            if 'stm_timbre = np.zeros(8)' in source and 'stm_power' not in source:
                # Update Initialization
                init_old = '''# Structural Novelty Variables
stm_timbre = np.zeros(8)
ltm_timbre = np.zeros(8)
stm_weight = 0.02  # ~1.5s smoothing
ltm_weight = 0.005 # ~6.0s smoothing'''

                init_new = '''# Structural Novelty Variables
stm_timbre = np.zeros(8)
ltm_timbre = np.zeros(8)
stm_power = 0.0
ltm_power = 0.0
stm_weight = 0.02  # ~1.5s smoothing
ltm_weight = 0.005 # ~6.0s smoothing'''
                source = source.replace(init_old, init_new)

            if 'timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)' in source and 'power_novelty' not in source:
                # Update Logic
                block_old = '''    # Update Short-Term and Long-Term Memory
    stm_timbre = (1 - stm_weight) * stm_timbre + stm_weight * current_timbre
    ltm_timbre = (1 - ltm_weight) * ltm_timbre + ltm_weight * current_timbre
    
    # Calculate Timbral Novelty (Euclidean distance)
    timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)
    
    # Structural Boundary (Verse / Chorus)
    if timbral_novelty > NOVELTY_THRESHOLD and (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
        structural_changes.append(playhead_time)
        last_structural_change_frame = frame
        # Pull LTM into STM to reset distance
        ltm_timbre = np.copy(stm_timbre)'''

                block_new = '''    # Update Short-Term and Long-Term Memory
    stm_timbre = (1 - stm_weight) * stm_timbre + stm_weight * current_timbre
    ltm_timbre = (1 - ltm_weight) * ltm_timbre + ltm_weight * current_timbre
    
    current_power = listener.smoothed_total_power
    stm_power = (1 - stm_weight) * stm_power + stm_weight * current_power
    ltm_power = (1 - ltm_weight) * ltm_power + ltm_weight * current_power
    
    # Calculate Timbral Novelty (Euclidean distance)
    timbral_novelty = np.linalg.norm(stm_timbre - ltm_timbre)
    
    # Calculate Power Novelty (normalized by LTM to detect relative drops/surges)
    power_novelty = np.abs(stm_power - ltm_power) / (ltm_power + 1.0)
    
    # Combined Novelty Score
    combined_novelty = timbral_novelty + (power_novelty * 0.2)
    
    # Structural Boundary (Verse / Chorus)
    if combined_novelty > NOVELTY_THRESHOLD and (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
        structural_changes.append(playhead_time)
        last_structural_change_frame = frame
        # Pull LTM into STM to reset distance
        ltm_timbre = np.copy(stm_timbre)
        ltm_power = stm_power'''
        
                source = source.replace(block_old, block_new)
                
            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    update_notebook()
    print("Notebook optimized with Power Novelty.")
