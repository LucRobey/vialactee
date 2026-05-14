import os

with open('run_nb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace `localized_continuous_phase_sweep` with `class_based_phase_sweep`
old_sweep_func = """# THE INITIAL SWEEP (FAST SCOUT)
def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=1.5, step=0.3, expected_phase=None, tau_power=1.0):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    best_overall_score = -float('inf')
    best_overall_bpm = center_bpm
    best_overall_p = 0
    
    buffer_indices = np.arange(odf_size)
    bpm_evals = np.arange(max(40.0, center_bpm - search_radius), min(190.0, center_bpm + search_radius + step/2), step)
    
    btrack_fps = 60.0
    const_part = buffer_indices - (odf_size - 1)
    
    for bpm_val in bpm_evals:
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        
        p_arr = np.arange(p_max)[:, None]
        phase_float = (const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val 
        
        template_vals = (norm_phi < 0.1).astype(float)
        
        p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1) / tau_val**tau_power
        
        # --- HUMAN PERCEPTION PRIOR (Gaussian weighting) ---
        human_prior = 0.5 + 0.5 * np.exp(-0.5 * ((bpm_val - 125.0) / 40.0)**2)
        
        tau_max_score = np.max(p_scores) * human_prior
        best_p = np.argmax(p_scores)
        
        if tau_max_score > best_overall_score:
            best_overall_score = tau_max_score
            best_overall_bpm = bpm_val
            best_overall_p = best_p
            
    optimal_tau = 60.0 * btrack_fps / best_overall_bpm
    precise_phase = best_overall_p / optimal_tau
            
    return best_overall_bpm, precise_phase, best_overall_score"""

new_sweep_func = """# THE INITIAL SWEEP (FAST SCOUT)
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
            
    return best_overall_class, best_overall_score"""

content = content.replace(old_sweep_func, new_sweep_func)

# Replace the sweep logic in run_simulation
old_sweep_call = """        if frames_since_sweep >= frames_between_sweep:
            # 1. RAW SWEEP (The Fast Scout) on CUSTOM PRISTINE ODF
            raw_bpm, raw_phase, raw_score = localized_continuous_phase_sweep(
                custom_odf_buffer, center_bpm=120.0, search_radius=40.0, step=0.5, expected_phase=None, tau_power=0.5)
            
            # 2. CLASS MATH
            current_class = bpm_to_class(raw_bpm)
            
            # 3. ALIGN & SMOOTH
            min_d, aligned_class = harmonic_alignment(current_class, long_term_class)"""

new_sweep_call = """        if frames_since_sweep >= frames_between_sweep:
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

content = content.replace(old_sweep_call, new_sweep_call)

# Add sweep_count var
old_var = """    frames_since_sweep = 0
    frames_between_sweep = int(1.0 * SIMULATED_FPS)"""

new_var = """    frames_since_sweep = 0
    frames_between_sweep = int(1.0 * SIMULATED_FPS)
    sweep_count = 0"""

content = content.replace(old_var, new_var)

# Add sweep_count increment
old_inc = """            listener.analyzer.bpm = bpm_pearson
            frames_since_sweep = 0
            
        frames_since_sweep += 1"""

new_inc = """            listener.analyzer.bpm = bpm_pearson
            frames_since_sweep = 0
            sweep_count += 1
            
        frames_since_sweep += 1"""

content = content.replace(old_inc, new_inc)

# Replace history append
old_hist_bpm = "history_raw_bpm.append(raw_bpm if 'raw_bpm' in locals() else 120)"
new_hist_bpm = "history_raw_bpm.append(60.0 * (2 ** best_class) if 'best_class' in locals() else 120)"
content = content.replace(old_hist_bpm, new_hist_bpm)

old_hist_class = "history_class.append(current_class if 'current_class' in locals() else 0)"
new_hist_class = "history_class.append(best_class if 'best_class' in locals() else 0)"
content = content.replace(old_hist_class, new_hist_class)

with open('run_nb.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated run_nb.py")
