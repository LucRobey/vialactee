import json

def update_bpm_trust():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])

            # 1. Update Function Return
            old_return = "return best_overall_bpm, precise_phase\n"
            new_return = "return best_overall_bpm, precise_phase, best_overall_score\n"
            if old_return in source:
                source = source.replace(old_return, new_return)
            elif "return best_overall_bpm, precise_phase" in source:
                source = source.replace("return best_overall_bpm, precise_phase", "return best_overall_bpm, precise_phase, best_overall_score")

            # 2. Update Initialization Variables
            if "SILENCE_THRESHOLD_FRAMES =" in source and "long_term_bpm =" not in source:
                init_old = """song_changes = []
silence_frames = 0
SILENCE_THRESHOLD_FRAMES = int(1.5 * SIMULATED_FPS)"""

                init_new = """song_changes = []
silence_frames = 0
SILENCE_THRESHOLD_FRAMES = int(1.5 * SIMULATED_FPS)

# BPM Trust Variables for Song Changes
long_term_bpm = 120.0
ltm_trust = 10.0 # Arbitrary warm-up scalar
bpm_jump_threshold = 15.0 # BPM change needed to trigger song reset"""
                source = source.replace(init_old, init_new)

            # 3. Update Sweep Calling and Logic
            sweep_call_old = """        precise_bpm, precise_phase = localized_continuous_phase_sweep(
            listener.odf_buffer, 
            center_bpm=coarse_bpm, 
            search_radius=1.5, 
            step=0.5,
            expected_phase=inertia_param
        )
        
        listener.bpm = precise_bpm"""

            sweep_call_new = """        precise_bpm, precise_phase, bpm_trust = localized_continuous_phase_sweep(
            listener.odf_buffer, 
            center_bpm=coarse_bpm, 
            search_radius=1.5, 
            step=0.5,
            expected_phase=inertia_param
        )
        
        listener.bpm = precise_bpm
        
        # --- BPM Trust Song Change Logic ---
        # 1. Update Long-Term smoothing
        if playhead_time < 5.0:
            long_term_bpm = precise_bpm
            ltm_trust = bpm_trust
        else:
            long_term_bpm = 0.9 * long_term_bpm + 0.1 * precise_bpm
            ltm_trust = 0.9 * ltm_trust + 0.1 * bpm_trust
        
        # 2. Detect Wild Departure 
        bpm_divergence = np.abs(precise_bpm - long_term_bpm)
        
        if bpm_divergence > bpm_jump_threshold and bpm_trust < (ltm_trust * 0.6):
            if len(song_changes) == 0 or (playhead_time - song_changes[-1]) > 5.0:
                song_changes.append(playhead_time)
                # Flush queues due to Song Change (Trust Drop!)
                future_queue.clear()
                standalone_beat_count = 0
                last_standalone_beat_count = 0
                standalone_sub_beat_locked = -1
                standalone_phase = 0.0
                listener.band_means.fill(0.0)
                listener.smoothed_fft_band_values.fill(0.0)
                listener.odf_buffer.fill(0.0)
                
                # Instantly accept the new tempo reality
                long_term_bpm = precise_bpm
        # -----------------------------------
"""
            if sweep_call_old in source:
                source = source.replace(sweep_call_old, sweep_call_new)

            if "\n" in source:
                lines = source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
            else:
                cell['source'] = [source]

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    update_bpm_trust()
    print("Notebook updated with BPM Trust logic.")
