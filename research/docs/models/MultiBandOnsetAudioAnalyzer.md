# Model Specification: `MultiBandOnsetAudioAnalyzer`

> **Model Identifier:** `MultiBandOnsetAudioAnalyzer`  
> **Author:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer  
> **Date:** 2026-09-06 (Promoted to Production: 2026-09-22)  
> **Status:** 🚀 **Promoted to Production** (`core/MultiBandOnsetAudioAnalyzer.py`)  
> **Version:** `1.1.0` (Production Hardened)  
> **Base Class:** [`core.BaseAudioAnalyzer.BaseAudioAnalyzer`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/BaseAudioAnalyzer.py)  
> **Production Implementation:** [`core/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/MultiBandOnsetAudioAnalyzer.py)  
> **Research Prototype:** [`research/experiments/models/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/experiments/models/MultiBandOnsetAudioAnalyzer.py)  
> **Research Cycle:** 008  

---

## 1. Executive Summary & Problem Statement

### 1.1 Targeted Failure Phenomena
This architecture is engineered to resolve the fundamental limitations of coarse 8-band Mel filterbanks:
- `PHASE_INVERSION_UPBEAT`: 180° anti-phase lock in high-energy electro, synthwave, and funk (*Nightcall*, *Where Is My Mind_*). In 8-band Mel, Band 0 covers $20.0\text{ Hz} \to 818.7\text{ Hz}$, merging the kick fundamental ($60\text{-}100\text{ Hz}$) with pumping 8th-note synth basslines and rhythm guitars ($150\text{-}800\text{ Hz}$). Because upbeat synth arpeggios exhibit higher positive flux than downbeats in broad bands ($0.88\times$ D/U ratio on *Nightcall*), legacy 8-band trackers are physically forced into anti-phase locks.
- `GHOST_BEAT_BURST`: Spurious triggers during guitar solos and vocal cadenzas where sustained harmonic loudness leaks into broad drum frequency bins.
- `OCTAVE_AMBIGUITY`: Half/double tempo class confusion in fast syncopated tracks.

### 1.2 Core Hypothesis
By increasing spectral resolution to $B \in \{16, 24, 32\}$ Mel bands and computing the half-wave rectified onset derivative $\Delta E_b = \max(0, E_b[t] - E_b[t-1])$ independently per band:
1. Sub-bass and kick drum attack transients ($20\text{-}180\text{ Hz}$) are isolated from synth arpeggios and guitar overdrive.
2. The downbeat-to-upbeat flux ratio on *Nightcall* is inverted from $0.88\times$ (upbeat-dominated) to $1.24\times$ (downbeat-dominated), eliminating the 180° upbeat trap.
3. Distorted guitar chord sustain is rejected because sustained harmonics produce zero onset derivative ($\Delta E \approx 0$).
4. Kick-conditioned anti-phase disambiguation actively verifies kick transient presence before accepting competing candidate phases.

---

## 2. Mathematical Formulations

### 2.1 Multi-Band Triangular Mel Filterbank Matrix ($W \in \mathbb{R}^{B \times 513}$)
For sampling rate $f_s = 44100\text{ Hz}$, buffer $N = 1024$, and $B$ bands:
$$m(f) = 2595 \log_{10}\left(1 + \frac{f}{700}\right), \quad f(m) = 700 \left(10^{m / 2595} - 1\right)$$
Triangular filter weights $W_{b, k}$ are centered at uniform Mel spacing across $[20\text{ Hz}, 20000\text{ Hz}]$, with row normalization $\sum_k W_{b, k} = 1$.

### 2.2 Per-Band Onset Derivatives & Instrument Routing
At each frame $t$, given Mel energies $E_b[t] = (W \cdot |X[t]|)_b$:
$$\Delta E_b[t] = \max\left(0, E_b[t] - E_b[t-1]\right)$$

Instrument streams are routed dynamically according to band resolution:
- **Kick Downbeat Stream ($y_{\text{kick}}$):**
  $$y_{\text{kick}}[t] = \sum_{b \in \mathcal{K}_B} w_{\text{kick}, b} \cdot \Delta E_b[t]$$
- **Snare Backbeat Stream ($y_{\text{snare}}$):**
  $$y_{\text{snare}}[t] = \sum_{b \in \mathcal{S}_B} w_{\text{snare}, b} \cdot \Delta E_b[t]$$
- **Hi-Hat Offbeat Stream ($y_{\text{hat}}$):**
  $$y_{\text{hat}}[t] = \sum_{b \in \mathcal{H}_B} w_{\text{hat}, b} \cdot \Delta E_b[t]$$
- **Mid-Melodic Squelch (Bands $\mathcal{M}_B$):**
  $$\Gamma_b[t] = \frac{\max_{\tau \in [0, 179]} \Delta E_b[t-\tau]}{\frac{1}{180}\sum_{\tau=0}^{179} \Delta E_b[t-\tau] + \epsilon}, \quad S_b[t] = \frac{1}{1 + \exp(-0.5(\Gamma_b[t] - 14.0))}$$
  $$y_{\text{mid}}[t] = 0.20 \cdot \sum_{b \in \mathcal{M}_B} S_b[t] \cdot \Delta E_b[t]$$
- **Combined Novelty Function ($y_{\text{metric}}$):**
  $$y_{\text{metric}}[t] = \max\left(0, y_{\text{kick}}[t] + y_{\text{snare}}[t] + y_{\text{mid}}[t] - 0.35 \cdot \max\left(0, y_{\text{hat}}[t] - y_{\text{kick}}[t]\right)\right)$$

### 2.3 Kick-Conditioned Anti-Phase Disambiguation
When primary phase $\phi_1$ and anti-phase $\phi_{\text{anti}} = (\phi_1 + 0.5) \bmod 1.0$ have competing Pearson correlation ($s(\phi_{\text{anti}}) \ge 0.80 s(\phi_1)$):
$$K_1 = \mathbb{E}\left[y_{\text{kick}} \mid \text{phase} \approx \phi_1\right], \quad K_{\text{anti}} = \mathbb{E}\left[y_{\text{kick}} \mid \text{phase} \approx \phi_{\text{anti}}\right]$$
If $K_{\text{anti}} > 1.25 \cdot K_1$, disambiguate in favor of $\phi_{\text{anti}}$.

---

## 3. Real-Time Embedded Safety & Memory Invariants

1. **Zero Dynamic NumPy Heap Allocations:**
   All state arrays (`diff_buffer`, `dE`, `band_flux`, `odf_buffer`, `templates`, `p_scores_buffers`, `class_neighbors`) are pre-allocated in `__init__()`.
2. **CPU Latency Budget:**
   - 32-band Mel projection: $0.23\text{ ms}$
   - Update loop: $0.44\text{ ms}$
   - Total per-frame execution: $\le 0.78\text{ ms}$ (well below the $\le 3.0\text{ms}$ budget on RPi Cortex-A72 at 60 FPS).
