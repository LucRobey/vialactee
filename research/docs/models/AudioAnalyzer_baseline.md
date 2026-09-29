# Model Specification: `AudioAnalyzer` (Production Baseline)

> **Model Identifier:** `AudioAnalyzer`  
> **Author:** Luc Robey / Antigravity Team  
> **Date:** 2026-09-05  
> **Version:** `1.2.0-baseline`  
> **Base Class:** [`core.BaseAudioAnalyzer.BaseAudioAnalyzer`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/BaseAudioAnalyzer.py)  
> **Implementation File:** [`core/AudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py)

---

## 1. Executive Summary & Problem Statement

`AudioAnalyzer.py` is the production beat tracking and rhythmic anticipation engine for the Vialactée interactive LED chandelier. It is designed to run in real-time at 60 FPS on resource-constrained embedded hardware (Raspberry Pi 4/5) and drive synchronized visual light shows without perceptual lag.

### 1.1 Solved Challenges
- **Zero-Latency Visual Synchronization:** Uses a 5-second look-ahead audio buffer (`fakeDelay = 5.0s`) to back-project future beat phase to speaker time ($T_{\text{speaker}}$), eliminating the 50–100ms lag inherent to purely causal trackers.
- **Double-Trigger Chatter Elimination:** Enforces a physical refractory period lockout ($T_{\min} = \max(0.18\text{s}, 0.40 \times 60/\text{BPM})$) and backward wrap clamping on phase soft-snapping.
- **Breakdown Dropout Immunity:** Employs dual-threshold gating (`real_beat_baseline_ratio` and `real_beat_energy_floor`) so the metronome coasts smoothly across breakdowns without firing false kick triggers.

### 1.2 Known Open Failure Modes
- **Upbeat Anti-Phase Lock (`PHASE_INVERSION_UPBEAT`):** Funk and disco tracks with heavy off-beat hi-hat accents (*Another One Bites The Dust*) can cause the Pearson template bank to lock 180° out of phase.
- **Dynamic Live Tempo Drift:** Rapid human accelerandos or rubato (*Bohemian Rhapsody*) require several flywheel sweeps to converge.
- **Acoustic Triple-Meter Polyrhythms:** 3/4 waltzes (*Chanson pour l'auvergnat*) experience periodic phase jitter due to binary (2/4, 4/4) template dominance.

---

## 2. Mathematical Formulations

### 2.1 Onset Detection Function ($ODF(t)$)
The Spectral Flux is computed across $B = 8$ frequency bands from Mel-filtered FFT power:
$$H_b(t) = \max\left(0, E_b(t) - E_b(t - \Delta t)\right)$$
To adapt to fluctuating signal dynamics, a rolling peak sensitivity $\gamma_b(t)$ is maintained per band:
$$\gamma_b(t) = \text{clamp}\left(\gamma_b(t - \Delta t) \cdot \lambda, \gamma_{\min}, \gamma_{\max}\right)$$
The scalar Onset Detection Function $ODF(t)$ is the weighted sum:
$$ODF(t) = \sum_{b=0}^{B-1} w_b \cdot H_b(t)$$
where bass and low-mid bands carry dominant weights ($w_{\text{bass}} = 2.5, w_{\text{low-mid}} = 1.8$).

### 2.2 Periodic & Tempo Metric

#### 2.2.1 Continuous Circular Logarithmic Tempo-Class
BPM is mapped to an octave-invariant logarithmic circle on $[0.0, 1.0)$:
$$c = \log_2\left(\frac{\text{BPM}}{60}\right) \pmod 1$$
The shortest circular distance between two tempo classes $c_1$ and $c_2$ is:
$$d(c_1, c_2) = \min\left(|c_1 - c_2|, 1.0 - |c_1 - c_2|\right)$$

#### 2.2.2 Harmonic Alignment (Octaves & Fifths)
To allow natural octave jumping while penalizing discordant shifts, harmonic alignments are evaluated against a perfect fifth shift ($\Delta_{\text{fifth}} = \log_2(1.5) \approx 0.58496$):
$$d_{\text{harmonic}} = \min\left(d(c, c_{\text{LTM}}), d(c, (c_{\text{LTM}} + \Delta_{\text{fifth}}) \bmod 1), d(c, (c_{\text{LTM}} - \Delta_{\text{fifth}}) \bmod 1)\right)$$

#### 2.2.3 Vectorized Pearson Correlation Template Bank
Precomputed normalized periodic impulse train templates $\mathbf{T}_{\text{BPM}, \phi}$ across 300 frames (5.0 seconds at 60 FPS) are correlated with the centered ODF buffer $\tilde{\mathbf{x}}$ via matrix dot-product:
$$r(\text{BPM}, \phi) = \frac{\mathbf{T}_{\text{BPM}, \phi} \cdot \tilde{\mathbf{x}}}{\|\tilde{\mathbf{x}}\|_2}$$
A Gaussian human prior centered at $\mu = 125\text{ BPM}$ ($\sigma = 40\text{ BPM}$) weights candidate BPMs:
$$P(\text{BPM}) = 0.5 + 0.5 \cdot \exp\left(-\frac{1}{2}\left(\frac{\text{BPM} - 125}{40}\right)^2\right)$$
$$\text{Score} = r(\text{BPM}, \phi) \cdot P(\text{BPM})$$

### 2.3 Continuous Phase Flywheel & Synchronization Dynamics
- **Free Inertial Evolution:**
  $$\phi(t) = \phi(t - \Delta t) + \frac{\text{BPM}(t)}{60} \Delta t \pmod 1$$
- **Phase Soft-Snapping:**
  When correlation confidence exceeds thresholds ($C \ge 0.30 \implies \alpha = 0.50$, $C \ge 0.15 \implies \alpha = 0.15$):
  $$\Delta \phi = \text{unwrap}(\phi_{\text{target}} - \phi)$$
  $$\phi \leftarrow \phi + \alpha \cdot \Delta \phi \pmod 1$$
- **Backward Wrap Clamp:**
  If $\phi < 0.25$ and $\Delta \phi < 0$, wrap-around into $[0.75, 1.0)$ is clamped to zero to prevent immediate re-triggering.
- **Refractory Lockout:**
  $$T_{\min} = \max\left(0.18\text{s}, 0.40 \times \frac{60}{\text{BPM}}\right)$$
  No beat event may fire if $(t - t_{\text{last}}) < T_{\min}$.

---

## 3. Hyperparameter Catalog

| Parameter | Type | Default | Description |
| :--- | :--- | :---: | :--- |
| `high_confidence_threshold` | `float` | `0.30` | Minimum Pearson correlation for high-gain snap |
| `moderate_confidence_threshold` | `float` | `0.15` | Minimum Pearson correlation for low-gain snap |
| `high_snap_ratio` | `float` | `0.50` | Soft-snap convergence rate for high confidence |
| `moderate_snap_ratio` | `float` | `0.15` | Soft-snap convergence rate for moderate confidence |
| `sweep_interval` | `float` | `0.20` | Seconds between Oracle template sweeps (5 Hz) |
| `human_prior_center` | `float` | `125.0` | Center BPM of human preference distribution |
| `human_prior_sigma` | `float` | `40.0` | Spread of human preference distribution |
| `real_beat_baseline_ratio` | `float` | `0.50` | Transient-to-rolling-mean ratio required for real kick |
| `real_beat_energy_floor` | `float` | `5.0` | Absolute flux energy floor required for real kick |

---

## 4. Computational Budget & Complexity

- **Algorithm Complexity:** $\mathcal{O}(K \cdot N)$ where $K$ is candidate BPMs evaluated in sweep (typically $\le 15$), and $N = 300$ samples.
- **Memory Allocations:** Zero heap allocation in per-frame `update()`. All buffers are pre-allocated 1D NumPy float32/float64 arrays.
- **Benchmark Average Execution Time:** $\approx 1.90\text{ms}$ per 60 FPS frame on standard x86 CPU, safely within the $3.0\text{ms}$ budget.

---

## 5. Official Baseline Benchmark Scores

### 5.1 Clean-Room Synthetic Suite (`--suite synthetic`)
- **F1@50ms:** **92.0%**
- **CMLt:** **91.6%**
- **AMLt:** **91.6%**
- **Upbeat Gap:** **0.00**
- **Phase Jitter:** **17.6ms**
- **CPU Time/Frame:** **1.90ms**
