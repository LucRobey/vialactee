"""
research/tests/test_comb_kernels.py - Unit tests for research/dsp/comb_kernels.py.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import unittest
import time
import numpy as np

from research.dsp.comb_kernels import (
    build_fourier_comb_bank,
    build_sparse_impulse_comb_bank,
    build_dense_phase_bank,
    project_complex_resonators,
    project_real_resonators
)


class TestCombKernels(unittest.TestCase):

    def setUp(self):
        self.bpms = np.linspace(60.0, 200.0, 141)  # 1 BPM resolution
        self.fps = 60.0
        self.M = 300  # 5.0 seconds lookahead

    def test_fourier_comb_bank_shape_and_dc_leakage(self):
        W = build_fourier_comb_bank(self.bpms, fps=self.fps, buffer_len=self.M)
        self.assertEqual(W.shape, (141, 300))
        self.assertEqual(W.dtype, np.complex128)

        # DC Annihilation check: row sums must be ~0
        row_means = np.abs(np.mean(W, axis=1))
        self.assertTrue(np.all(row_means < 1e-12), f"DC leakage detected: max mean={np.max(row_means)}")

    def test_sparse_impulse_comb_bank_shapes_and_dc(self):
        for method in ["analytic_harmonics", "time_domain"]:
            for shape in ["triangular", "hann", "boxcar"]:
                W_I, W_Q = build_sparse_impulse_comb_bank(
                    self.bpms, fps=self.fps, buffer_len=self.M, pulse_shape=shape, duty_cycle=0.10, method=method
                )
                self.assertEqual(W_I.shape, (141, 300))
                self.assertEqual(W_Q.shape, (141, 300))
                self.assertEqual(W_I.dtype, np.float64)
                self.assertEqual(W_Q.dtype, np.float64)

                # Row centering check
                row_means_I = np.abs(np.mean(W_I, axis=1))
                self.assertTrue(np.all(row_means_I < 1e-12), f"DC leakage in W_I ({method}, {shape}): max mean={np.max(row_means_I)}")

                row_means_Q = np.abs(np.mean(W_Q, axis=1))
                self.assertTrue(np.all(row_means_Q < 1e-12), f"DC leakage in W_Q ({method}, {shape}): max mean={np.max(row_means_Q)}")

    def test_synthetic_pulse_resonance_and_dc_noise_rejection(self):
        target_bpm = 120.0
        tau = 60.0 * self.fps / target_bpm  # 30 frames
        y = np.zeros(self.M, dtype=np.float64)

        # Place pulses at phase 0 relative to latest frame (index 299)
        # index 299, 269, 239, ...
        pulse_indices = np.arange(self.M - 1, -1, -int(tau))
        y[pulse_indices] = 1.0

        W_I, W_Q = build_sparse_impulse_comb_bank(self.bpms, fps=self.fps, buffer_len=self.M, method="analytic_harmonics")

        # Project
        scores_I, scores_Q = project_real_resonators(W_I, W_Q, y)

        # The maximum in-phase response MUST peak at 120 BPM
        peak_idx = int(np.argmax(scores_I))
        detected_bpm = self.bpms[peak_idx]
        self.assertEqual(detected_bpm, target_bpm, f"Expected peak at {target_bpm} BPM, got {detected_bpm}")

        # At phase 0 downbeat, quadrature response must be close to zero relative to in-phase peak
        self.assertLess(abs(scores_Q[peak_idx]), 0.10 * scores_I[peak_idx])

        # Test continuous sustain (guitar feedback / noise): constant signal
        y_sustained = np.ones(self.M, dtype=np.float64)
        scores_sustain, _ = project_real_resonators(W_I, W_Q, y_sustained)
        # All sustain responses must be ~0 due to negative baseline and DC centering
        self.assertTrue(np.all(np.abs(scores_sustain) < 1e-10))

    def test_analytic_quadrature_phase_tracking(self):
        target_bpm = 120.0
        tau = 60.0 * self.fps / target_bpm  # 30 frames
        W_I, W_Q = build_sparse_impulse_comb_bank(self.bpms, fps=self.fps, buffer_len=self.M, method="analytic_harmonics")
        k_target = int(np.argmin(np.abs(self.bpms - target_bpm)))

        # Test phase response for pulses shifted around nominal positions
        for shift in [-2, 0, 2]:
            y = np.zeros(self.M, dtype=np.float64)
            # Nominal downbeat pulse at 209 (299 - 3 * 30 = 209 is exact integer period)
            for idx in np.arange(209 + shift, -1, -int(tau)):
                if 0 <= idx < self.M:
                    y[idx] = 1.0

            I = float(np.dot(W_I[k_target, :], y))
            Q = float(np.dot(W_Q[k_target, :], y))

            if shift == 0:
                self.assertLess(abs(Q), 0.10 * abs(I))
            elif shift > 0:
                # Pulse shifted forward in buffer index (later in time) -> positive phase
                self.assertGreater(Q, 0.0)
            elif shift < 0:
                # Pulse shifted backward in buffer index (earlier in time) -> negative phase
                self.assertLess(Q, 0.0)

    def test_dense_phase_bank(self):
        T = build_dense_phase_bank(120.0, fps=self.fps, buffer_len=self.M)
        tau = int(np.ceil(60.0 * self.fps / 120.0))  # 30
        self.assertEqual(T.shape, (tau, self.M))
        self.assertEqual(T.dtype, np.float64)

    def test_zero_allocation_and_latency_budget(self):
        W_I, W_Q = build_sparse_impulse_comb_bank(self.bpms, fps=self.fps, buffer_len=self.M)
        y = np.random.randn(self.M)

        out_I = np.zeros(141, dtype=np.float64)
        out_Q = np.zeros(141, dtype=np.float64)

        # Warmup
        for _ in range(50):
            project_real_resonators(W_I, W_Q, y, out_I=out_I, out_Q=out_Q)

        # Benchmark 1,000 iterations
        t0 = time.perf_counter()
        for _ in range(1000):
            project_real_resonators(W_I, W_Q, y, out_I=out_I, out_Q=out_Q)
        t1 = time.perf_counter()

        avg_latency_ms = (t1 - t0) / 1000.0 * 1000.0
        print(f"\n[BENCHMARK] Sparse Comb Projection Latency: {avg_latency_ms:.4f} ms / frame (RPi Budget: <= 3.0 ms)")
        self.assertLess(avg_latency_ms, 1.5, f"Latency {avg_latency_ms} ms exceeds budget")


if __name__ == "__main__":
    unittest.main()
