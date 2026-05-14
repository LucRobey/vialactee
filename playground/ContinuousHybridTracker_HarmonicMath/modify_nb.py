import json
import re

with open('ContinuousHybridTracker_HarmonicMath.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cell 6 and replace `localized_continuous_phase_sweep`
for cell in nb['cells']:
    if 'localized_continuous_phase_sweep' in "".join(cell.get('source', [])):
        new_source = """# THE INITIAL SWEEP (FAST SCOUT)
def class_based_phase_sweep(odf_buffer, class_evals, tau_power=1.0):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    best_overall_score = -float('inf')
    best_overall_class = class_evals[0] % 1.0
    
    buffer_indices = np.arange(odf_size)
    btrack_fps = 60.0
    const_part = buffer_indices - (odf_size - 1)
    
    for class_val in class_evals:
        # Map class to representative BPM in [90, 180)
        c = class_val % 1.0
        base_bpm = 60.0 * (2 ** c)
        eval_bpm = base_bpm if base_bpm >= 90.0 else base_bpm * 2.0
        
        tau_val = 60.0 * btrack_fps / eval_bpm
        p_max = int(np.ceil(tau_val))
        
        p_arr = np.arange(p_max)[:, None]
        phase_float = (const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val 
        
        template_vals = (norm_phi < 0.1).astype(float)
        
        p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1) / tau_val**tau_power
        
        tau_max_score = np.max(p_scores)
        
        if tau_max_score > best_overall_score:
            best_overall_score = tau_max_score
            best_overall_class = c
            
    return best_overall_class, best_overall_score
"""
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        break

# Find the run_simulation cell and update it
for cell in nb['cells']:
    if 'def run_simulation(' in "".join(cell.get('source', [])):
        source = "".join(cell['source'])
        
        # update frames_between_sweep
        source = source.replace("frames_between_sweep = int(5 * SIMULATED_FPS)", "frames_between_sweep = int(1.0 * SIMULATED_FPS)\n    sweep_count = 0")
        
        # update the sweep logic block
        old_block = """        if frames_since_sweep >= frames_between_sweep:
            # 1. RAW SWEEP (The Fast Scout) on CUSTOM PRISTINE ODF
            raw_bpm, raw_phase, raw_score = localized_continuous_phase_sweep(
                custom_odf_buffer, center_bpm=120.0, search_radius=40.0, step=0.5, expected_phase=None, tau_power=0.5)
            
            # 2. CLASS MATH
            current_class = bpm_to_class(raw_bpm)
            
            # 3. ALIGN & SMOOTH
            min_d, aligned_class = harmonic_alignment(current_class, long_term_class)"""
            
        new_block = """        if frames_since_sweep >= frames_between_sweep:
            if sweep_count % 10 == 0:
                # STRONG SWEEP: Full [0.0, 1.0) range
                class_evals = np.arange(0.0, 1.0, 0.01)
            else:
                # LOCAL SWEEP: Window around long_term_class
                class_evals = np.arange(long_term_class - 0.05, long_term_class + 0.05 + 0.001, 0.01)

            # 1. RAW SWEEP (The Fast Scout)
            best_class, raw_score = class_based_phase_sweep(
                custom_odf_buffer, class_evals=class_evals, tau_power=0.5)
            
            # 2. ALIGN & SMOOTH
            min_d, aligned_class = harmonic_alignment(best_class, long_term_class)"""
            
        source = source.replace(old_block, new_block)
        
        # update the history variables
        source = source.replace("history_raw_bpm.append(raw_bpm if 'raw_bpm' in locals() else 120)", "history_raw_bpm.append(60.0 * (2 ** best_class) if 'best_class' in locals() else 120)")
        source = source.replace("history_class.append(current_class if 'current_class' in locals() else 0)", "history_class.append(best_class if 'best_class' in locals() else 0)")
        
        # add sweep_count += 1
        source = source.replace("frames_since_sweep = 0", "frames_since_sweep = 0\n            sweep_count += 1")
        
        cell['source'] = [line + ('\n' if i < len(source.split('\n')) - 1 else '') for i, line in enumerate(source.split('\n'))]
        break

with open('ContinuousHybridTracker_HarmonicMath.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook updated.")
