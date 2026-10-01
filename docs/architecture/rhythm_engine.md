# Rhythm Engine & Anticipation Flywheel ("Oracle")

> **Location:** `docs/architecture/rhythm_engine.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`core/MultiBandOnsetAudioAnalyzer.py`](../../core/MultiBandOnsetAudioAnalyzer.py), [`core/comb_kernels.py`](../../core/comb_kernels.py), [`core/AudioAnalyzer.py`](../../core/AudioAnalyzer.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-05](../axioms/AXIOM-05_LOOKAHEAD_SYNC.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md), [AXIOM-08](../axioms/AXIOM-08_RESEARCH_REGRESSION.md)

---

## 1. Engine Overview

The **Anticipation Flywheel ("Oracle")** rhythm tracking engine is a predictive, real-time algorithmic pipeline designed to achieve zero-lag, jitter-free beat synchronization for the Vialactée chandelier. Rather than running a reactive beat tracker and delaying its triggers, it uses the 5-second look-ahead audio buffer to predict incoming tempo and phase, back-projects the phase to the physical speaker time ($T_{\text{speaker}}$), and drives a continuous mechanical flywheel with breakdown coasting, anti-phase disambiguation, and real-beat gating.

The production engine is implemented in `core/MultiBandOnsetAudioAnalyzer.py`, backed by standalone compiled `core/comb_kernels.py`.

---

## 2. Mathematical Pipeline

### A. 4-Stream Instrument Separation & Mid Squelch
To eliminate the 180° upbeat trap (`PHASE_INVERSION_UPBEAT`) where loud synth arpeggios overpower kick drums, `MultiBandOnsetAudioAnalyzer` separates onset derivatives into 4 distinct instrument streams:
1. **Kick Downbeat Stream ($y_{\text{kick}}$):** Sum of sub-bass and low-kick bands ($\sim 20\text{--}180\text{ Hz}$).
2. **Snare Backbeat Stream ($y_{\text{snare}}$):** Sum of snare body and crack bands ($\sim 200\text{--}4000\text{ Hz}$).
3. **Hi-Hat Offbeat Stream ($y_{\text{hat}}$):** Sum of upper-treble bands ($> 4000\text{ Hz}$).
4. **Mid-Melodic Squelch ($y_{\text{mid}}$):** Dynamically suppresses sustained synth arpeggios via a logistic squelch envelope:
   $$\Gamma_b[t] = \frac{\max_{\tau \in [0, 179]} \Delta E_b[t-\tau]}{\frac{1}{180}\sum_{\tau=0}^{179} \Delta E_b[t-\tau] + \epsilon}, \quad S_b[t] = \frac{1}{1 + \exp\left(-0.5(\Gamma_b[t] - 14.0)\right)}$$
   $$y_{\text{mid}}[t] = 0.20 \cdot \sum_{b \in \mathcal{M}_B} S_b[t] \cdot \Delta E_b[t]$$
5. **Combined Metric Function ($y_{\text{metric}}$):**
   $$y_{\text{metric}}[t] = \max\left(0, y_{\text{kick}}[t] + y_{\text{snare}}[t] + y_{\text{mid}}[t] - 0.35 \cdot \max\left(0, y_{\text{hat}}[t] - y_{\text{kick}}[t]\right)\right)$$

### B. Kick-Conditioned Anti-Phase Disambiguation
When high-energy tracks exhibit competing correlation peaks between candidate downbeat phase $\phi_1$ and 180° anti-phase $\phi_{\text{anti}} = (\phi_1 + 0.5) \bmod 1.0$:
$$K_1 = \mathbb{E}\left[y_{\text{kick}} \mid \text{phase} \approx \phi_1\right], \quad K_{\text{anti}} = \mathbb{E}\left[y_{\text{kick}} \mid \text{phase} \approx \phi_{\text{anti}}\right]$$
If $s(\phi_{\text{anti}}) \ge 0.80 s(\phi_1)$ and $K_{\text{anti}} > 1.25 \cdot K_1$, the engine forces phase alignment to the true acoustic kick downbeat, resolving upbeat inversion.

### C. Dense Pearson Template Bank & Logarithmic Octave Folding
Using standalone compiled `core/comb_kernels.py`, the engine builds dense triangular pulse template banks across continuous logarithmic tempo classes:
$$f(\text{BPM}) = \log_2\left(\frac{\text{BPM}}{60}\right) \pmod 1$$
- **Fast Scout Sweep:** Evaluates Pearson cross-correlation across tempo classes in $< 0.3\text{ ms}$ on Raspberry Pi CPU.
- **Harmonic Judge:** Evaluates candidate octaves and $3:2$ perfect fifths ($\Delta = \log_2(1.5)$) with a Gaussian human prior centered at $125\text{ BPM}$.

### D. Speaker-Time Flywheel & Back-Projection
The lookahead phase $\phi_{\text{ingest}}$ is back-projected to speaker playback time $T_{\text{speaker}}$:
$$\Delta\phi = \frac{\text{BPM}}{60} \times (\text{lookahead\_seconds} + \Delta t_{\text{dynamic\_audio\_latency}} + \Delta t_{\text{hardware\_latency}})$$
$$\phi_{\text{target}} = (\phi_{\text{ingest}} - \Delta\phi) \pmod 1$$

- **Continuous Advance:** Advanced frame-by-frame via:
  $$\text{speaker\_phase} \leftarrow \left(\text{speaker\_phase} + \frac{\text{BPM}}{60} \cdot \Delta t\right) \bmod 1.0$$
- **Adaptive Soft-Snap:** Soft-snaps toward $\phi_{\text{target}}$ with backward wrap clamp to prevent jitter.
- **Real vs. Dropped Beat Classification:** On downbeat zero-crossings (`speaker_phase >= 1.0`), local acoustic energy in the speaker window validates real downbeats vs silent breakdown coasting (`is_real_beat` vs `is_dropped_beat`).
