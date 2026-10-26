# Researcher Reference: First-Principles Redesign Playbook

> Loaded on demand from [`SKILL.md`](../SKILL.md). Cycle results quoted below are historical snapshots; `research/experiments/LEADERBOARD.md` is the authority for current SOTA numbers.

## 4. First-Principles Mathematical Redesign & Architectural Freedom

### 4.1 Beyond Incremental Tweaks
Researchers are **not** restricted to tweaking hyperparameters or adding minor `if` statements to the legacy `AudioAnalyzer.py` logic. If incremental tuning encounters diminishing returns or plateauing failure modes (e.g. persistent upbeat traps on funk/disco, octave ambiguity on synthwave arpeggios), **take a step back and redesign the mathematical foundation from first principles**.

You have full authority to propose and implement fundamentally new mathematical paradigms, provided you mathematically justify the choice and respect the real-time embedded safety invariants.

### 4.2 Candidate Mathematical Paradigms
Instead of legacy 1D Pearson correlation over a 5-second static template buffer, consider alternative well-founded MIR / DSP architectures:
- **Resonator Filterbanks (Comb Filter / IIR Oscillators):**
  Maintain a parallel bank of $K$ tuned second-order complex IIR resonators across the tempo grid ($60 \le \text{BPM}_k \le 180$). Compute instantaneous energy $E_k(t) = |z_k(t)|^2$ and phase $\phi_k(t) = \text{atan2}(\text{Im}(z_k), \text{Re}(z_k))$ continuously with zero lookahead latency.
- **State-Space & Extended Kalman Filters (EKF):**
  Model rhythm as a continuous dynamic state vector $x_t = [\theta_t, \omega_t, \alpha_t]^T$ (instantaneous phase, tempo velocity, acceleration) driven by multi-band measurement novelty vectors $[y_{\text{kick}}, y_{\text{snare}}, y_{\text{hat}}]^T$. Tracks covariance $P_t$, handling dropouts via Kalman prediction without ad-hoc heuristic thresholds.
- **Dual-Tier Phase-Locked Loops (Costas Loop Demodulators):**
  Treat beat tracking as carrier phase recovery. A Voltage-Controlled Oscillator (VCO) driven by a loop filter comparing incoming multi-band novelty with the oscillator phase, using a quadrature phase detector to cleanly resolve $90^\circ$ and $180^\circ$ offbeat ambiguities.
- **Online Circular Autocorrelation & Tempogram Analysis:**
  Compute an incremental sliding circular lag-domain autocorrelation matrix ($R_{xx}(\tau, t)$) directly in pre-allocated buffers, eliminating template bank bias.
- **Harmonic Energy Ratio & Timbre-Conditional Pulse Generators:**
  Multi-channel novelty where downbeat energy is conditioned on low-frequency transient dominance ($E_{\text{sub}} / E_{\text{high}}$) rather than a single collapsed scalar flux.

### 4.3 The 4 Non-Negotiable Invariants
Any clean-sheet mathematical redesign must satisfy:
1. **Contract Inheritance:** Subclass [`music.BaseAudioAnalyzer.BaseAudioAnalyzer`](../../../../music/BaseAudioAnalyzer.py) directly (implementing `__init__`, `reset()`, `update()`, and `beat_phase`). Do not inherit from `AudioAnalyzer` if you are replacing its paradigm.
2. **Real-Time Safety:** Per-tick `update()` execution must remain $\le 3.0\text{ms}$ on ARM Cortex-A72 (60 Hz analyzer tick; LEDs render at 30 FPS, AXIOM-01).
3. **Zero Heap Allocation:** All state arrays, filter coefficients, and history matrices must be pre-allocated in `__init__()`. No dynamic allocations or array reshaping inside `update()`.
4. **Zero Clean-Room Regression:** Must pass the synthetic suite (`--suite synthetic`) with $\Delta \text{F1@50ms} \ge 0.0\%$.

### 4.4 Documentation & Justification Requirements
When introducing a first-principles mathematical redesign, you must explicitly document in your model card (`research/docs/models/<CandidateName>.md`) and your living artifact (`research_log.md`):
1. **The Structural Flaw of the Legacy Math:** What mathematical assumption broke (e.g. *"A 1D Pearson correlation over a single scalar flux collapses timbre information, making a 130 BPM hi-hat offbeat transient indistinguishable from a kick downbeat"*).
2. **The New Mathematical Equations:** State the governing difference equations, transfer functions, state transitions, or loss/energy functions in rigorous $\LaTeX$.
3. **Complexity & Memory Proof:** Prove that the per-frame operation is $O(N)$ or $O(1)$ and runs within the pre-allocated footprint.

### 4.5 The Lesson of Cycle 005 & The Sparse Impulsive Comb Resonator
In Cycle 005, `DualResonatorAudioAnalyzer` demonstrated that replacing the 1D loop with a vectorized complex resonator matrix ($W \cdot y$) achieved a **12x CPU speedup (0.20ms per frame)** and a **+8.4% Pop gain** (*Pumped Up Kicks* +13.5%, *Nightcall* AMLt +19.5%).
However, using pure continuous Fourier sinusoids ($\exp(-j\omega t)$) caused a severe regression on Rock (-19.7% F1 on *Sweet Child O' Mine*).
- **The Root Cause:** Continuous sinusoids integrate energy across the entire period. In dense Rock, sustained distorted guitar chords leak continuous harmonic energy across all Fourier frequency bins, smearing the phase and causing phase hunting.
- **The Solution (The Sparse Impulsive Comb Resonator):**
  The baseline `AudioAnalyzer` succeeded on Rock because its template has a **sparse triangular pulse surrounded by a negative baseline (-1.0)**. The negative baseline penalizes sustain and only rewards sharp attack transients.
  Use `research.dsp.comb_kernels.build_sparse_impulse_comb_bank(...)` to get precomputed matrix banks ($W_I, W_Q$) featuring sparse triangular/Hann pulses with zero-mean negative baselines and closed-form Hilbert quadrature. This preserves the 0.20ms BLAS evaluation speed while eliminating broadband guitar leakage.

### 4.6 The Breakthrough of Cycle 008 & Multi-Band Onset Derivatives (Current SOTA)
In Cycle 008, `MultiBandOnsetAudioAnalyzer` established a new all-time benchmark record:
- **Macro F1@50ms:** **45.1%** on `neural-core` (up from baseline 41.1%).
- **Clean-Room Synthetic:** **95.4%** F1 / 95.9% CMLt.
- **Per-Frame Latency:** **0.47ms** (well within the $\le 3.0\text{ms}$ ARM budget).
- **Core Mechanism:** Replaces single-channel collapsed flux with 16-band half-wave rectified onset slopes ($\Delta E_b[t] = \max(0, E_b[t] - E_b[t-1])$) and kick-conditioned anti-phase disambiguation.
- **Research Directive:** Any radical new paradigm should build on top of multi-band onset separation (or equivalent timbre-selective representation) rather than collapsing raw audio into a single scalar flux.
