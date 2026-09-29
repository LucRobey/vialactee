"""
core/comb_kernels.py - Vectorized Phase Template Matrix Generator.

Provides pre-computed template matrix banks for sub-frame phase sweeps in rhythm tracking engines.
Clean, zero-external-dependency, compiled NumPy implementation.
"""

from __future__ import annotations
import numpy as np


def build_dense_phase_bank(
    bpm: float,
    fps: float = 60.0,
    buffer_len: int = 300,
    pulse_shape: str = "triangular",
    duty_cycle: float = 0.10
) -> np.ndarray:
    """
    Builds a dense phase template matrix T in R^{tau x M} for a single BPM.

    Each row p corresponds to integer frame phase offset p in [0, ceil(tau)-1].
    Row p has peak at (M - 1 - p).
    Normalized with zero mean and unit variance.
    """
    tau = 60.0 * fps / max(1.0, bpm)
    p_max = max(1, int(np.ceil(tau)))
    M = int(buffer_len)

    buffer_indices = np.arange(M, dtype=np.float64)
    const_part = buffer_indices - (M - 1.0)

    p_arr = np.arange(p_max)[:, None]
    phase_float = (const_part[None, :] + p_arr) % tau
    norm_phi = phase_float / tau

    beat_dist = np.minimum(norm_phi, 1.0 - norm_phi)
    template_vals = np.full((p_max, M), -1.0, dtype=np.float64)
    mask_beat = beat_dist < duty_cycle

    if pulse_shape == "triangular":
        template_vals[mask_beat] = 1.0 - (beat_dist[mask_beat] / duty_cycle)
    elif pulse_shape == "hann":
        norm_dist = beat_dist[mask_beat] / duty_cycle
        template_vals[mask_beat] = 0.5 * (1.0 + np.cos(np.pi * norm_dist))
    elif pulse_shape == "boxcar":
        template_vals[mask_beat] = 1.0

    template_mean = np.mean(template_vals, axis=1, keepdims=True)
    template_centered = template_vals - template_mean
    template_std = np.sqrt(np.sum(template_centered ** 2, axis=1, keepdims=True)) + 1e-6
    return (template_centered / template_std).astype(np.float64)
