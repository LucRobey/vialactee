# Rhythm Engine & Anticipation Flywheel ("Oracle")

> **Location:** `docs/architecture/rhythm_engine.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`core/DyadicMetricalAudioAnalyzer.py`](../../core/DyadicMetricalAudioAnalyzer.py), [`core/MultiBandOnsetAudioAnalyzer.py`](../../core/MultiBandOnsetAudioAnalyzer.py), [`core/comb_kernels.py`](../../core/comb_kernels.py), [`core/AudioAnalyzer.py`](../../core/AudioAnalyzer.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-05](../axioms/AXIOM-05_LOOKAHEAD_SYNC.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md), [AXIOM-08](../axioms/AXIOM-08_RESEARCH_REGRESSION.md)

---

## 1. Engine Overview

The **Anticipation Flywheel ("Oracle")** rhythm tracking engine is a predictive, real-time algorithmic pipeline designed to achieve zero-lag, jitter-free beat synchronization for the Vialactée chandelier. Rather than running a reactive beat tracker and delaying its triggers, it uses the 5-second look-ahead audio buffer to predict incoming tempo and phase, back-projects the phase to the physical speaker time ($T_{\text{speaker}}$), and drives a continuous mechanical flywheel with breakdown coasting, anti-phase disambiguation, and real-beat gating.

The production engine is `core/DyadicMetricalAudioAnalyzer.py` (Cycle 012), a subclass of the stable parent engine `core/MultiBandOnsetAudioAnalyzer.py` (Cycle 008, still selectable as a fallback), backed by standalone compiled `core/comb_kernels.py`. Sections A-D describe the parent engine; section E describes what the Dyadic layer adds.

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
- **Dyadic Judge:** Evaluates candidate octaves only ($\{0.5\times, 1.0\times, 2.0\times\}$; $3:2$ fifths are banned because they cause cross-metric polyrhythmic locks) with a Gaussian human prior centered at $125\text{ BPM}$.

### D. Speaker-Time Flywheel & Back-Projection
The lookahead phase $\phi_{\text{ingest}}$ is back-projected to speaker playback time $T_{\text{speaker}}$:
$$\Delta\phi = \frac{\text{BPM}}{60} \times (\text{lookahead\_seconds} - \Delta t_{\text{dynamic\_audio\_latency}} - \Delta t_{\text{hardware\_latency}})$$
$$\phi_{\text{target}} = (\phi_{\text{ingest}} - \Delta\phi) \pmod 1$$
- **Sign convention:** the lookahead is *added* to the back-shift; `dynamic_audio_latency` (age of the analysed audio, so the ingest phase is already stale by that amount) and `hardware_latency` (config `led_latency` - `audio_output_latency`, i.e. net visual lag = LED lag - audio-output lag, positive when the lights appear later than the sound) are *subtracted*. See AXIOM-05.

- **Continuous Advance:** Advanced frame-by-frame via:
  $$\text{speaker\_phase} \leftarrow \left(\text{speaker\_phase} + \frac{\text{BPM}}{60} \cdot \Delta t\right) \bmod 1.0$$
- **Adaptive Soft-Snap:** Soft-snaps toward $\phi_{\text{target}}$ with backward wrap clamp to prevent jitter.
- **Real vs. Dropped Beat Classification:** On downbeat zero-crossings (`speaker_phase >= 1.0`), local acoustic energy in the speaker window validates real downbeats vs silent breakdown coasting (`is_real_beat` vs `is_dropped_beat`).

### E. Dyadic Metrical Layer (`DyadicMetricalAudioAnalyzer`)
The flywheel tracks the nominal **tactus** in $[60, 200]\text{ BPM}$ with high inertia and emits the primary beat at phase wrap ($\phi = 0$). At the mid-cycle crossing ($\phi = 0.5$) a **causal, scale-invariant sub-pulse arbiter** decides whether a metrical sub-beat exists, using only dimensionless energy ratios against rolling baselines (invariant to mastering loudness):
- `alt_sig`: alternating snare backbeat at half-time tempo ($\text{BPM} \le 105$): kick-dominant downbeat, clean snare at the midpoint, low hi-hat sizzle, low midpoint kick leakage (e.g. *Nightcall*).
- `bal_k`: driving balanced percussion at $126.6\text{--}129.5\text{ BPM}$ (e.g. *Pumped Up Kicks*).
- An EWMA latch $L[t] = 0.95\,L[t-1] + 0.05\,(\text{alt\_sig} \lor \text{bal\_k})$ with $\text{subpulse\_active} = L > 0.30$ prevents flicker. The latch is deliberately **not** reset on a novelty-detected song change (measured to cost accuracy; it decays by itself).
- A sub-pulse beat is only emitted if physical percussive energy exists at the speaker window ($T_{\text{speaker}}$) and it is not hi-hat sizzle.

**Contract mapping.** Sub-pulses are real metrical beats: while active, `Listener.bpm` reports `effective_bpm` $= 2 \times$ tactus (range up to $\sim 260$) and `beat_phase` wraps twice per tactus cycle, so `is_beat`, `beat_count` and `beat_phase` always agree. Sub-pulse beats are tagged and validated at $T_{\text{speaker}}$ exactly like primary beats and feed the pulse-density pillar of `rhythm_salience`.

**Anti-phase indexing fix.** The kick-density lookahead offset is aligned to the observation horizon $M$ (`(M-1-idx) % step`), not to the template length.
