import numpy as np

odf_buffer_size = 512
odf_buffer = np.zeros(odf_buffer_size)
btrack_fps = 60.0
true_bpm = 92.3
true_tau = 60.0 * btrack_fps / true_bpm

idx = odf_buffer_size - 1
while idx >= 0:
    odf_buffer[int(round(idx))] = 1.0
    sub = idx - true_tau/2
    if sub >= 0:
        odf_buffer[int(round(sub))] = 0.6
    idx -= true_tau

# Listener ACF calculation
tau_min = int(btrack_fps * 60.0 / 180.0)
tau_max = int(btrack_fps * 60.0 / 60.0)

taus = np.arange(tau_min, tau_max)
bpms = 60.0 * btrack_fps / taus
tempo_weights = np.exp(-0.5 * ((bpms - 120.0) / 20.0)**2)

centered_odf = odf_buffer - np.mean(odf_buffer)
acf = np.correlate(centered_odf, centered_odf, mode='full')
acf = acf[len(odf_buffer)-1:] # Extract only positive lags

overlap_lengths = np.arange(odf_buffer_size, 0, -1)
unbiased_acf = acf / overlap_lengths

weighted_acf = np.maximum(0, unbiased_acf[tau_min:tau_max]) * tempo_weights

left = np.r_[float('inf'), weighted_acf[:-1]]
right = np.r_[weighted_acf[1:], float('inf')]
peaks_mask = (weighted_acf > left) & (weighted_acf > right)
weighted_peaks = np.where(peaks_mask, weighted_acf, 0)

folded_peaks = np.copy(weighted_peaks)
for i in range(len(weighted_peaks)):
    tau = tau_min + i
    if tau * 2 <= tau_max:
        idx_double = int(tau * 2) - tau_min
        if idx_double < len(weighted_peaks):
            folded_peaks[i] += 0.5 * weighted_peaks[idx_double]
    if tau / 2.0 >= tau_min:
        idx_half = int(tau / 2.0) - tau_min
        if idx_half >= 0:
            folded_peaks[i] += 0.5 * weighted_peaks[idx_half]
    if tau / 1.5 >= tau_min:
        idx_15 = int(tau / 1.5) - tau_min
        if idx_15 >= 0 and idx_15 < len(weighted_peaks):
            folded_peaks[i] += 0.6 * weighted_peaks[idx_15]

weighted_peaks = folded_peaks
best_tau_idx = int(np.argmax(weighted_peaks))

val = weighted_acf[best_tau_idx]
left_val = weighted_acf[max(0, best_tau_idx - 1)]
right_val = weighted_acf[min(len(weighted_acf)-1, best_tau_idx + 1)]

offset = 0.0
divisor = 2.0 * (left_val - 2.0*val + right_val)
if divisor != 0:
    offset = (left_val - right_val) / divisor
    offset = max(-1.0, min(1.0, offset))

btrack_tau = tau_min + best_tau_idx + offset
target_bpm = 60.0 * btrack_fps / max(1.0, btrack_tau)

print("Listener Detected BPM:", target_bpm)
print("Listener Base Tau:", tau_min + best_tau_idx)
