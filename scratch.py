import numpy as np
import time

btrack_fps = 60.0
odf_buffer_size = 512
odf_buffer = np.random.rand(odf_buffer_size)

def bench_sweep():
    center_bpm = 120.0
    search_radius = 1.5
    step = 0.1
    
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_buffer_size))
    weighted_buffer = odf_buffer * decay_curve
    
    bpm_evals = np.arange(max(50.0, center_bpm - search_radius), min(220.0, center_bpm + search_radius + step/2), step)
    buffer_indices = np.arange(odf_buffer_size)
    const_part = buffer_indices - (odf_buffer_size - 1)
    
    for bpm_val in bpm_evals:
        tau_val = 60.0 * btrack_fps / bpm_val
        p_max = int(np.ceil(tau_val))
        
        p_arr = np.arange(p_max)[:, None]
        phase_float = (const_part[None, :] + p_arr) % tau_val
        norm_phi = phase_float / tau_val 
        
        abs_phi = np.abs(norm_phi - 0.5)
        mask_high = abs_phi >= 0.475
        mask_medium = abs_phi <= 0.025
        
        template_vals = np.full((p_max, odf_buffer_size), -0.2)
        template_vals[mask_high] = 0.9 + 0.6 * (0.025 - (0.5 - abs_phi[mask_high]))
        template_vals[abs_phi <= 0.025] = 0.6 + 0.3 * (0.025-(abs_phi[mask_medium]))
        template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.0
        
        p_scores = np.sum(weighted_buffer[None, :] * template_vals, axis=1)

t0 = time.perf_counter()
bench_sweep()
print(f"Sweep time: {(time.perf_counter()-t0)*1000:.2f} ms")
