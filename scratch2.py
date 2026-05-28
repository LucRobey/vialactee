import numpy as np
import time

btrack_fps = 60.0
odf_buffer_size = 512
odf_buffer = np.random.rand(odf_buffer_size)

def bench_sweep_fast():
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
        norm_phi = ((const_part[None, :] + p_arr) % tau_val) / tau_val
        abs_phi = np.abs(norm_phi - 0.5)
        
        # Vectorized Math without boolean arrays
        # Base value: -0.2
        # If abs_phi >= 0.475: 0.9 + 0.6 * (abs_phi - 0.475)
        # If abs_phi <= 0.025: 0.6 + 0.3 * (0.025 - abs_phi)
        # If 0.22 <= abs_phi <= 0.28: 0.0
        
        template_vals = np.full((p_max, odf_buffer_size), -0.2)
        
        # Optimization: use np.where instead of boolean indexing assignment
        # which creates a ton of temporary arrays and masks
        template_vals = np.where(abs_phi >= 0.475, 0.9 + 0.6 * (abs_phi - 0.475), template_vals)
        template_vals = np.where(abs_phi <= 0.025, 0.6 + 0.3 * (0.025 - abs_phi), template_vals)
        template_vals = np.where((abs_phi >= 0.22) & (abs_phi <= 0.28), 0.0, template_vals)
        
        p_scores = np.sum(weighted_buffer * template_vals, axis=1)

t0 = time.perf_counter()
bench_sweep_fast()
print(f"Sweep time fast 1: {(time.perf_counter()-t0)*1000:.2f} ms")

def bench_sweep_faster():
    center_bpm = 120.0
    search_radius = 1.5
    step = 0.1
    
    decay_curve = np.exp(-1.5 * np.linspace(1.0, 0.0, odf_buffer_size))
    weighted_buffer = odf_buffer * decay_curve
    
    bpm_evals = np.arange(max(50.0, center_bpm - search_radius), min(220.0, center_bpm + search_radius + step/2), step)
    buffer_indices = np.arange(odf_buffer_size)
    const_part = buffer_indices - (odf_buffer_size - 1)
    
    # Completely vectorize over BPMs as well!
    # bpm_evals is ~30 items
    num_bpms = len(bpm_evals)
    tau_vals = 60.0 * btrack_fps / bpm_evals
    p_max = int(np.ceil(np.max(tau_vals))) # ~40
    
    p_arr = np.arange(p_max)[:, None, None] # shape (p_max, 1, 1)
    tau_vals = tau_vals[None, :, None] # shape (1, num_bpms, 1)
    
    # const_part: (1, 1, 512)
    # phase_float: (p_max, num_bpms, 512)
    phase_float = (const_part[None, None, :] + p_arr) % tau_vals
    norm_phi = phase_float / tau_vals
    abs_phi = np.abs(norm_phi - 0.5)
    
    template_vals = np.full((p_max, num_bpms, odf_buffer_size), -0.2)
    template_vals = np.where(abs_phi >= 0.475, 0.9 + 0.6 * (abs_phi - 0.475), template_vals)
    template_vals = np.where(abs_phi <= 0.025, 0.6 + 0.3 * (0.025 - abs_phi), template_vals)
    template_vals = np.where((abs_phi >= 0.22) & (abs_phi <= 0.28), 0.0, template_vals)
    
    # Invalid p entries (where p >= tau_val) should be zeroed so they don't affect max
    valid_p = p_arr < tau_vals # (p_max, num_bpms, 1)
    template_vals = np.where(valid_p, template_vals, 0.0)
    
    p_scores = np.sum(weighted_buffer[None, None, :] * template_vals, axis=2) # shape (p_max, num_bpms)

t0 = time.perf_counter()
bench_sweep_faster()
print(f"Sweep time faster: {(time.perf_counter()-t0)*1000:.2f} ms")
