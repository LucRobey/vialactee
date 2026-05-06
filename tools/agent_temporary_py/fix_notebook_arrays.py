import json

def fix_notebook_arrays():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # -- Fix Array Appending Block 1 (Inside Loop, Snapping Match) --
            block1_old = """                history_time.append(playhead_time)
                history_bpm.append(present['bpm'])
                history_bass.append(present.get('bass_flux', 0.0))
                history_treble.append(present.get('treble_flux', 0.0))
                history_trust.append(ltm_trust)"""
                
            block1_new = """                history_time.append(playhead_time)
                history_bpm.append(present['bpm'])
                history_bass.append(present.get('bass_flux', 0.0))
                history_treble.append(present.get('treble_flux', 0.0))
                history_trust.append(ltm_trust)
                history_stm_power.append(stm_power)
                history_ltm_power.append(ltm_power)
                history_timbral_nov.append(timbral_novelty)
                history_power_nov.append(power_novelty)
                history_combined_nov.append(combined_novelty)"""
            
            if block1_old in source:
                source = source.replace(block1_old, block1_new)


            # -- Fix Array Appending Block 2 (Inside Loop, No Snapping Fallback) --
            block2_old = """            history_time.append(playhead_time)
            history_bpm.append(present['bpm'])
            history_bass.append(present.get('bass_flux', 0.0))
            history_treble.append(present.get('treble_flux', 0.0))
            history_trust.append(ltm_trust)"""
            
            # Wait, my previous broken patch might have inserted it here already?
            # Let's clean up any broken insertions first by searching broadly
            if "history_stm_power.append(stm_power)" in source:
                source = source.replace("    history_stm_power.append(stm_power)\n", "")
                source = source.replace("    history_ltm_power.append(ltm_power)\n", "")
                source = source.replace("    history_timbral_nov.append(timbral_novelty)\n", "")
                source = source.replace("    history_power_nov.append(power_novelty)\n", "")
                source = source.replace("    history_combined_nov.append(combined_novelty)\n", "")
            
            block2_new = """            history_time.append(playhead_time)
            history_bpm.append(present['bpm'])
            history_bass.append(present.get('bass_flux', 0.0))
            history_treble.append(present.get('treble_flux', 0.0))
            history_trust.append(ltm_trust)
            history_stm_power.append(stm_power)
            history_ltm_power.append(ltm_power)
            history_timbral_nov.append(timbral_novelty)
            history_power_nov.append(power_novelty)
            history_combined_nov.append(combined_novelty)"""

            if block2_old in source:
                source = source.replace(block2_old, block2_new)


            # -- Fix NameError for sweep_times in Evaluation Cell --
            if "sweep_times = filter_window(sweep_times,start_time,end_time)" in source:
                missing_var_inject = """sweep_interval = 1.5 
sweep_times = np.arange(sweep_interval, time_arr[-1], sweep_interval)
sweep_times = filter_window(sweep_times,start_time,end_time)"""
                source = source.replace("sweep_times = filter_window(sweep_times,start_time,end_time)", missing_var_inject)


            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    fix_notebook_arrays()
    print("Fixed Array append length logic & sweep_times logic!")
