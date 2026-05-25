import numpy as np
import time

odf_buffer_size = 512
tau_int = 40
weighted_buffer = np.random.rand(odf_buffer_size)
cycle_template = np.random.rand(tau_int)

def bench_phase_loop():
    p_scores = np.zeros(tau_int)
    buffer_indices = np.arange(odf_buffer_size)
    for p in range(tau_int):
        phase_indices = (buffer_indices - (odf_buffer_size - 1 - p)) % tau_int
        p_scores[p] = np.sum(weighted_buffer * cycle_template[phase_indices])

def bench_phase_vectorized():
    buffer_indices = np.arange(odf_buffer_size)
    p_arr = np.arange(tau_int)[:, None]
    phase_indices = (buffer_indices[None, :] - (odf_buffer_size - 1 - p_arr)) % tau_int
    p_scores = np.sum(weighted_buffer[None, :] * cycle_template[phase_indices], axis=1)

t0 = time.perf_counter()
for _ in range(100):
    bench_phase_loop()
print(f"Phase loop (100x): {(time.perf_counter()-t0)*1000:.2f} ms")

t0 = time.perf_counter()
for _ in range(100):
    bench_phase_vectorized()
print(f"Phase vectorized (100x): {(time.perf_counter()-t0)*1000:.2f} ms")
