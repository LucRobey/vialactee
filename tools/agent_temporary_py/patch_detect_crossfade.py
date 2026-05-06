import json

def patch_detect_crossfade():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Add the constant
            if "NOVELTY_THRESHOLD = 0.2" in source or "NOVELTY_THRESHOLD = 0.15" in source:
                # First let's standardize to 0.15 just in case it was 0.2 
                source = source.replace("NOVELTY_THRESHOLD = 0.2", "NOVELTY_THRESHOLD = 0.15")
                
                old_const = "NOVELTY_THRESHOLD = 0.15"
                new_const = "NOVELTY_THRESHOLD = 0.15\npower_weight = 0.2\nSONG_NOVELTY_THRESHOLD = 0.40 # Trigger song change on massive DJ crossfades"
                if "SONG_NOVELTY_THRESHOLD" not in source:
                    source = source.replace(old_const, new_const)

            # 2. Update the structural logic
            old_logic = """    # Structural Boundary (Verse / Chorus)
    if combined_novelty > NOVELTY_THRESHOLD and (frame - last_structural_change_frame) > STRUCTURAL_COOLDOWN_FRAMES:
        structural_changes.append(playhead_time)
        last_structural_change_frame = frame
        # Pull LTM into STM to reset distance
        ltm_timbre = np.copy(stm_timbre)
        ltm_power = stm_power"""
            
            new_logic = """    # Structural Boundary (Verse / Chorus) OR Seamless DJ crossfade
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
            
            if old_logic in source:
                source = source.replace(old_logic, new_logic)

            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_detect_crossfade()
