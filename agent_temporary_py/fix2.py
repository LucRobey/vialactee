import json

def apply_fixes():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # -- 1. Fix 8-space indent block (Middle of loop) --
            block_8_old = """        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_bass.append(present.get('bass_flux', 0.0))
        history_treble.append(present.get('treble_flux', 0.0))
        history_trust.append(ltm_trust)"""
                
            block_8_new = """        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_bass.append(present.get('bass_flux', 0.0))
        history_treble.append(present.get('treble_flux', 0.0))
        history_trust.append(ltm_trust)
        history_stm_power.append(stm_power)
        history_ltm_power.append(ltm_power)
        history_timbral_nov.append(timbral_novelty)
        history_power_nov.append(power_novelty)
        history_combined_nov.append(combined_novelty)"""
            
            if block_8_old in source:
                source = source.replace(block_8_old, block_8_new)
                print("Replaced 8-space block")

            # -- 2. Fix 4-space indent block (End of loop flush) --
            block_4_old = """    history_time.append(playhead_time)
    history_bpm.append(present['bpm'])
    history_bass.append(present.get('bass_flux', 0.0))
    history_treble.append(present.get('treble_flux', 0.0))
    history_trust.append(ltm_trust)"""
            
            block_4_new = """    history_time.append(playhead_time)
    history_bpm.append(present['bpm'])
    history_bass.append(present.get('bass_flux', 0.0))
    history_treble.append(present.get('treble_flux', 0.0))
    history_trust.append(ltm_trust)
    history_stm_power.append(stm_power)
    history_ltm_power.append(ltm_power)
    history_timbral_nov.append(timbral_novelty)
    history_power_nov.append(power_novelty)
    history_combined_nov.append(combined_novelty)"""

            if block_4_old in source:
                source = source.replace(block_4_old, block_4_new)
                print("Replaced 4-space block")

            # -- 3. Fix NameError for sweep_times in Evaluation Cell --
            if "sweep_times = filter_window(sweep_times,start_time,end_time)" in source:
                missing_var_inject = """sweep_interval = frames_between_sweep / SIMULATED_FPS
sweep_times = np.arange(sweep_interval, time_arr[-1], sweep_interval)
sweep_times = filter_window(sweep_times,start_time,end_time)"""
                source = source.replace("sweep_times = filter_window(sweep_times,start_time,end_time)", missing_var_inject)
                print("Replaced sweep_times")

            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    apply_fixes()
