import numpy as np

def localized_continuous_phase_sweep(odf_buffer, center_bpm, search_radius=3.0, step=0.1):
    odf_size = len(odf_buffer)
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_size))
    weighted_buffer = odf_buffer * decay_curve
    
    best_overall_score = -float('inf')
    best_overall_bpm = center_bpm
    best_overall_p = 0
    
    buffer_indices = np.arange(odf_size)
    bpm_evals = np.arange(max(60.0, center_bpm - search_radius), min(180.0, center_bpm + search_radius + step/2), step)
    btrack_fps = 60.0
    
    for bpm_val in bpm_evals:
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        p_scores = np.zeros(p_max)
        
        for p in range(p_max):
            phase_float = (buffer_indices - (odf_size - 1 - p)) % tau_val
            norm_phi = phase_float / tau_val 
            
            template_vals = np.full(odf_size, -0.2)
            template_vals[(norm_phi <= 0.05) | (norm_phi >= 0.95)] = 1.0
            template_vals[(norm_phi >= 0.45) & (norm_phi <= 0.55)] = 0.6
            template_vals[(norm_phi >= 0.22) & (norm_phi <= 0.28)] = 0.3
            template_vals[(norm_phi >= 0.72) & (norm_phi <= 0.78)] = 0.3
            
            p_scores[p] = np.sum(weighted_buffer * template_vals)
            
        tau_max_score = np.max(p_scores)
        best_p = np.argmax(p_scores)
        
        gaussian_weight = np.exp(-0.5 * ((bpm_val - center_bpm) / (search_radius * 1.5))**2)
        weighted_score = tau_max_score * (0.8 + 0.2 * gaussian_weight)
        
        if weighted_score > best_overall_score:
            best_overall_score = weighted_score
            best_overall_bpm = bpm_val
            best_overall_p = best_p
            
    return best_overall_bpm, best_overall_p

# Simulate a perfect 92.3 BPM peak signal
odf_size = 512
odf = np.zeros(odf_size)
btrack_fps = 60.0
true_bpm = 92.3
true_tau = 60.0 * btrack_fps / true_bpm

idx = odf_size - 1
while idx >= 0:
    odf[int(round(idx))] = 1.0
    sub = idx - true_tau/2
    if sub >= 0:
        odf[int(round(sub))] = 0.6
    idx -= true_tau

print("True BPM:", true_bpm)
res_bpm, _ = localized_continuous_phase_sweep(odf, center_bpm=92.3, search_radius=3.0, step=0.1)
print("Swept BPM (centered at 92.3):", res_bpm)

res_bpm_90, _ = localized_continuous_phase_sweep(odf, center_bpm=90.0, search_radius=3.0, step=0.1)
print("Swept BPM (centered at 90.0):", res_bpm_90)
