import json
import re

file_path = r'c:\Users\Users\Desktop\vialactée\vialactee\playground\ContinuousHybridTracker_HarmonicMath\ContinuousHybridTracker_HarmonicMath.ipynb'
with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Cell 1: localized_continuous_phase_sweep
cell1_source = """# THE INITIAL SWEEP (Used once at startup to find the first class)
def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=1.5, step=0.3, expected_phase=None, tau_power=1.0):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    # Pre-compute zero-mean buffer for Pearson
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6
    
    best_overall_score = -float('inf')
    best_overall_bpm = center_bpm
    best_overall_p = 0
    
    buffer_indices = np.arange(odf_size)
    bpm_evals = np.arange(max(50.0, center_bpm - search_radius), min(220.0, center_bpm + search_radius + step/2), step)
    
    btrack_fps = 60.0
    const_part = buffer_indices - (odf_size - 1)
    
    for bpm_val in bpm_evals:
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        
        p_arr = np.arange(p_max)[:, None]
        phase_float = (const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val 
        
        # Sharp triangle pulse
        beat_dist = np.minimum(norm_phi, 1.0 - norm_phi)
        template_vals = np.full((p_max, odf_size), -0.5)
        mask_beat = beat_dist < 0.1
        template_vals[mask_beat] = 1.0 - (beat_dist[mask_beat] / 0.1)
        
        template_mean = np.mean(template_vals, axis=1, keepdims=True)
        template_centered = template_vals - template_mean
        template_std = np.sqrt(np.sum(template_centered**2, axis=1)) + 1e-6
        
        # True Pearson Correlation! No more tau_power or expected_beats!
        p_scores = np.sum(buffer_centered[None, :] * template_centered, axis=1) / (buffer_std * template_std)
        
        if expected_phase is not None:
            expected_p = (expected_phase * tau_val) % tau_val
            dist_p = np.minimum(np.abs(p_arr[:, 0] - expected_p), tau_val - np.abs(p_arr[:, 0] - expected_p))
            norm_dist = dist_p / tau_val
            phase_inertia = np.exp(-0.5 * (norm_dist / 0.35)**2)
            p_scores = p_scores * (0.5 + 0.5 * phase_inertia)
            
        tau_max_score = np.max(p_scores)
        best_p = np.argmax(p_scores)
        
        gaussian_weight = np.exp(-0.5 * ((bpm_val - center_bpm) / (search_radius * 1.5))**2)
        weighted_score = tau_max_score * (0.8 + 0.2 * gaussian_weight)
        
        if weighted_score > best_overall_score:
            best_overall_score = weighted_score
            best_overall_bpm = bpm_val
            best_overall_p = best_p
            
    optimal_tau = 60.0 * btrack_fps / best_overall_bpm
    precise_phase = best_overall_p / optimal_tau
            
    return best_overall_bpm, precise_phase, best_overall_score
"""

# Cell 2: evaluate_specific_bpms
cell2_source = """# THE CANDIDATE EVALUATOR (Options A, B, C)
def evaluate_specific_bpms(odf_buffer, candidate_bpms, expected_phase=None, tau_power=1.0):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    # Pre-compute zero-mean buffer for Pearson
    buffer_mean = np.mean(weighted_buffer)
    buffer_centered = weighted_buffer - buffer_mean
    buffer_std = np.sqrt(np.sum(buffer_centered**2)) + 1e-6
    
    btrack_fps = 60.0
    buffer_indices = np.arange(odf_size)
    const_part = buffer_indices - (odf_size - 1)
    
    best_score_pearson = -float('inf')
    best_bpm_pearson = candidate_bpms[0]
    
    best_score_ratio = -float('inf')
    best_bpm_ratio = candidate_bpms[0]
    
    best_score_density = -float('inf')
    best_bpm_density = candidate_bpms[0]
    
    for bpm_val in candidate_bpms:
        if not (40.0 <= bpm_val <= 240.0):
            continue
            
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        
        p_arr = np.arange(p_max)[:, None]
        phase_float = (const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val 
        
        # --- SHARP TRIANGLE PULSE TEMPLATE ---
        beat_dist = np.minimum(norm_phi, 1.0 - norm_phi)
        template_vals = np.full((p_max, odf_size), -0.5)
        mask_beat = beat_dist < 0.1
        template_vals[mask_beat] = 1.0 - (beat_dist[mask_beat] / 0.1)
        
        # --- OPTION A: Pearson Correlation (The Math Standard) ---
        template_mean = np.mean(template_vals, axis=1, keepdims=True)
        template_centered = template_vals - template_mean
        template_std = np.sqrt(np.sum(template_centered**2, axis=1)) + 1e-6
        
        p_scores_pearson = np.sum(buffer_centered[None, :] * template_centered, axis=1) / (buffer_std * template_std)
        
        if np.max(p_scores_pearson) > best_score_pearson:
            best_score_pearson = np.max(p_scores_pearson)
            best_bpm_pearson = bpm_val
            
        # --- OPTION B: Peak vs Valley Ratio (The Sub-Harmonic Killer) ---
        template_peaks = (beat_dist < 0.1).astype(float)
        template_valleys = (beat_dist >= 0.4).astype(float)
        
        peak_energy = np.sum(weighted_buffer[None, :] * template_peaks, axis=1)
        valley_energy = np.sum(weighted_buffer[None, :] * template_valleys, axis=1)
        
        p_scores_ratio = peak_energy / (valley_energy + 1.0)
        
        if np.max(p_scores_ratio) > best_score_ratio:
            best_score_ratio = np.max(p_scores_ratio)
            best_bpm_ratio = bpm_val
            
        # --- OPTION C: Pure Hit Density (The Simplest Approach) ---
        p_scores_density = np.sum(weighted_buffer[None, :] * template_peaks, axis=1)
        
        if np.max(p_scores_density) > best_score_density:
            best_score_density = np.max(p_scores_density)
            best_bpm_density = bpm_val

    return best_bpm_pearson, best_bpm_ratio, best_bpm_density
"""

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = "".join(cell.get('source', []))
        if "def localized_continuous_phase_sweep" in source:
            cell['source'] = [line + '\n' for line in cell1_source.split('\n')[:-1]]
        elif "def evaluate_specific_bpms" in source:
            cell['source'] = [line + '\n' for line in cell2_source.split('\n')[:-1]]

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
print("Updated successfully")
