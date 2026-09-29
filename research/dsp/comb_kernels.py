"""
research/dsp/comb_kernels.py - Vectorized Resonator Comb Kernel Generator & Toolkit.

Provides high-performance, pre-computed matrix steering banks for real-time beat tracking:
1. Complex Fourier Comb Bank (sinusoidal basis with DC leakage elimination)
2. Sparse Impulsive Comb Bank (triangular, Hann, or boxcar pulses with negative baseline & analytic Hilbert quadrature)
3. Dense Single-BPM Phase Template Bank (for sub-frame phase sweeps)
4. Fast BLAS-accelerated zero-allocation projection helpers

Authors: Vialactée Autonomous Research Team
License: Proprietary / Vialactée Project
"""

from __future__ import annotations
from typing import Optional, Tuple, Union, List
import numpy as np


def build_fourier_comb_bank(
    bpms: Union[np.ndarray, List[float]],
    fps: float = 60.0,
    buffer_len: int = 300,
    causal_decay: float = 1.5,
    num_harmonics: int = 1
) -> np.ndarray:
    """
    Builds a complex Fourier resonator steering matrix W in C^{K x M}.

    Each row k resonates with candidate tempo bpms[k].
    Row-centering ensures strictly zero DC leakage (sum of each row = 0).

    Args:
        bpms: 1D array or list of candidate BPMs (length K).
        fps: ODF sampling rate in frames per second (default: 60.0).
        buffer_len: Lookahead buffer length M in frames (default: 300 = 5.0s).
        causal_decay: Exponential decay parameter over buffer (default: 1.5).
        num_harmonics: Number of harmonic overtones to include (default: 1).

    Returns:
        Complex128 matrix W of shape (K, buffer_len).
    """
    bpms_arr = np.asarray(bpms, dtype=np.float64)
    K = len(bpms_arr)
    M = int(buffer_len)

    # Causal exponential window w[m] (decay ensures responsiveness to tempo changes)
    m = np.arange(M, dtype=np.float64)
    w = np.exp(-causal_decay * (1.0 - m / max(1.0, M - 1.0)))

    # Lookback distance: delta_m <= 0 relative to latest frame (M-1)
    delta_m = m[None, :] - (M - 1.0)

    # Fundamental frequency ratio
    freq_ratio = bpms_arr[:, None] / (60.0 * fps)
    exponent = -1j * 2.0 * np.pi * freq_ratio * delta_m
    W_raw = w[None, :] * np.exp(exponent)

    # Add harmonics if requested (e.g. 2x octave overtone with half amplitude)
    for h in range(2, num_harmonics + 1):
        h_weight = 1.0 / h
        h_exponent = -1j * 2.0 * np.pi * (h * freq_ratio) * delta_m
        W_raw += h_weight * w[None, :] * np.exp(h_exponent)

    # Annihilate DC leakage by centering each row
    W_centered = W_raw - np.mean(W_raw, axis=1, keepdims=True)
    return W_centered.astype(np.complex128)


def build_sparse_impulse_comb_bank(
    bpms: Union[np.ndarray, List[float]],
    fps: float = 60.0,
    buffer_len: int = 300,
    pulse_shape: str = "triangular",
    duty_cycle: float = 0.10,
    causal_decay: float = 1.5,
    num_harmonics: int = 8,
    method: str = "analytic_harmonics",
    include_quadrature: bool = True
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Builds a Sparse Impulsive Comb matrix bank (W_I, W_Q) in R^{K x M}.

    Unlike continuous Fourier sinusoids, sparse impulsive combs feature narrow
    percussive pulses surrounded by an active negative baseline.
    This negative baseline acts as an intrinsic non-linear noise gate that
    heavily penalizes sustained electric guitar and vocal noise, preventing
    the phase-hunting regressions observed in dense Rock music.

    When method='analytic_harmonics' (recommended default):
        The comb is synthesized from the analytical Fourier series of the pulse train:
            W_I[k, m] = w[m] * sum_{h=1}^H alpha_h * cos(h * omega_k * delta_m)
            W_Q[k, m] = w[m] * sum_{h=1}^H alpha_h * sin(h * omega_k * delta_m)
        This guarantees exact, continuous Hilbert quadrature without edge-truncation FFT
        distortions, and yields W_Q = 0 at downbeat phase alignment.

    When method='time_domain':
        Direct piecewise evaluation of pulse shape with a hard -1.0 baseline.

    Args:
        bpms: 1D array or list of candidate BPMs (length K).
        fps: ODF sampling rate in frames per second (default: 60.0).
        buffer_len: Lookahead buffer length M in frames (default: 300 = 5.0s).
        pulse_shape: 'triangular' (linear spike), 'hann' (raised cosine), or 'boxcar'.
        duty_cycle: Pulse width as fraction of period tau (default: 0.10 = 10%).
        causal_decay: Exponential window decay parameter (default: 1.5).
        num_harmonics: Number of harmonics for analytic synthesis (default: 8).
        method: 'analytic_harmonics' (default) or 'time_domain'.
        include_quadrature: Whether to compute Hilbert quadrature partner W_Q.

    Returns:
        Tuple of (W_I, W_Q) as float64 arrays of shape (K, buffer_len).
        If include_quadrature is False, W_Q is None.
    """
    bpms_arr = np.asarray(bpms, dtype=np.float64)
    K = len(bpms_arr)
    M = int(buffer_len)

    m = np.arange(M, dtype=np.float64)
    delta_m = m - (M - 1.0)  # delta_m <= 0
    w = np.exp(-causal_decay * (1.0 - m / max(1.0, M - 1.0)))

    if method == "analytic_harmonics":
        # Calculate harmonic weights based on pulse shape Fourier series
        h_arr = np.arange(1, num_harmonics + 1, dtype=np.float64)
        if pulse_shape == "triangular":
            # Triangular pulse Fourier series: sinc^2(h * duty)
            alpha_h = (np.sinc(h_arr * duty_cycle)) ** 2
        elif pulse_shape == "hann":
            # Raised cosine Hann pulse Fourier series
            s = np.sinc(h_arr * duty_cycle)
            denom = 1.0 - (2.0 * h_arr * duty_cycle) ** 2
            # Avoid division by zero when 2*h*duty == 1
            denom = np.where(np.abs(denom) < 1e-4, 1e-4, denom)
            alpha_h = np.abs(s / denom)
        elif pulse_shape == "boxcar":
            # Rectangular pulse Fourier series: sinc(h * duty)
            alpha_h = np.abs(np.sinc(h_arr * duty_cycle))
        else:
            raise ValueError(f"Unsupported pulse_shape: {pulse_shape}")

        # Normalize alpha_h so fundamental is 1.0
        if alpha_h[0] > 1e-6:
            alpha_h /= alpha_h[0]

        freq_ratio = bpms_arr[:, None] / (60.0 * fps)  # shape (K, 1)
        omega = 2.0 * np.pi * freq_ratio  # shape (K, 1)

        W_I = np.zeros((K, M), dtype=np.float64)
        W_Q = np.zeros((K, M), dtype=np.float64) if include_quadrature else None

        for h, a in zip(h_arr, alpha_h):
            angle = (h * omega) * delta_m[None, :]  # shape (K, M)
            W_I += a * np.cos(angle)
            if include_quadrature:
                # Quadrature partner: sin(angle) so positive shift yields positive phase
                W_Q += a * np.sin(angle)

        # Apply causal decay window
        W_I *= w[None, :]
        if include_quadrature:
            W_Q *= w[None, :]

        # Annihilate DC leakage
        W_I -= np.mean(W_I, axis=1, keepdims=True)
        if include_quadrature:
            W_Q -= np.mean(W_Q, axis=1, keepdims=True)

        return W_I, W_Q

    elif method == "time_domain":
        W_I = np.zeros((K, M), dtype=np.float64)
        for k in range(K):
            bpm = bpms_arr[k]
            tau = 60.0 * fps / max(1.0, bpm)

            phi = (delta_m % tau) / tau  # in [0, 1)
            dist = np.minimum(phi, 1.0 - phi)

            pulse_row = np.full(M, -1.0, dtype=np.float64)
            mask_pulse = dist < duty_cycle

            if pulse_shape == "triangular":
                pulse_row[mask_pulse] = 1.0 - (dist[mask_pulse] / duty_cycle)
            elif pulse_shape == "hann":
                norm_dist = dist[mask_pulse] / duty_cycle
                pulse_row[mask_pulse] = 0.5 * (1.0 + np.cos(np.pi * norm_dist))
            elif pulse_shape == "boxcar":
                pulse_row[mask_pulse] = 1.0
            else:
                raise ValueError(f"Unsupported pulse_shape: {pulse_shape}")

            pulse_row -= np.mean(pulse_row)
            p_std = np.std(pulse_row)
            if p_std > 1e-6:
                pulse_row /= p_std
            W_I[k, :] = pulse_row * w

        W_I -= np.mean(W_I, axis=1, keepdims=True)

        W_Q = None
        if include_quadrature:
            # Analytic finite-difference derivative quadrature for time domain
            W_Q = np.gradient(W_I, axis=1) * (tau / (2.0 * np.pi))
            W_Q -= np.mean(W_Q, axis=1, keepdims=True)

        return W_I, W_Q
    else:
        raise ValueError(f"Unknown method '{method}'. Choose 'analytic_harmonics' or 'time_domain'.")


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


def project_complex_resonators(
    W: np.ndarray,
    y: np.ndarray,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Evaluates complex matrix projection Z = W @ y with optional pre-allocated output array.
    Guarantees zero heap allocation when 'out' is provided.
    """
    return np.dot(W, y, out=out)


def project_real_resonators(
    W_I: np.ndarray,
    W_Q: Optional[np.ndarray],
    y: np.ndarray,
    out_I: Optional[np.ndarray] = None,
    out_Q: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Evaluates real in-phase and quadrature projections:
        X = W_I @ y
        Y = W_Q @ y
    Guarantees zero heap allocation when 'out_I' and 'out_Q' are provided.
    """
    res_I = np.dot(W_I, y, out=out_I)
    res_Q = np.dot(W_Q, y, out=out_Q) if W_Q is not None else None
    return res_I, res_Q
