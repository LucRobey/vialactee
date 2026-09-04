# Anticipation Flywheel ("Oracle") Architecture & Math Reference

The Vialactée rhythm tracking engine operates non-causally via an Anticipation Flywheel ("Oracle") architecture implemented across `core/AudioIngestion.py`, `core/AudioAnalyzer.py`, and `core/Listener.py`.

---

## 1. Vectorized DSP Front-End

### Mel Scale & Chromagram Matrix Projection
Instead of iterative band-pass filters, raw audio buffers (4096 samples with a Hanning window) are transformed via `np.fft.rfft()`.
- **Mel Scale Transformation**: Pre-computed matrix $M_{\text{mel}} \in \mathbb{R}^{8 \times 2049}$ maps FFT bins into 8 psychoacoustic bands via compiled dot-product:
  $$\mathbf{B}_{\text{mel}} = \mathbf{M}_{\text{mel}} \cdot |\mathbf{X}_{\text{fft}}|$$
- **Chromagram Matrix**: Pre-computed matrix $M_{\text{chroma}} \in \mathbb{R}^{12 \times 2049}$ maps bins directly into 12 musical pitch classes (C through B).
- **ADSR Smoothing**: Applied frame-by-frame with distinct attack (`attack = 0.2 ** fps_ratio`, effective $\alpha = 0.8$) and release (`release = 0.85 ** fps_ratio`, effective $\alpha = 0.15$) coefficients:
  $$\text{smoothed} \leftarrow \text{factor} \cdot \text{smoothed} + (1 - \text{factor}) \cdot \text{new}$$

---

## 2. Anticipation Flywheel ("Oracle") Engine

### Lookahead Onset Buffer
`AudioAnalyzer` maintains a 5-second future look-ahead Onset Detection Function (ODF) buffer ($\mathbf{y}_{\text{future}}$). An exponential recency weight $w[i] = \exp(-1.5 \cdot (1 - i/N))$ is applied prior to template matching to prioritize the most recent transients.

### $O(1)$ Pearson Correlation Template Bank (`FastTemplateBank`)
To estimate tempo candidates across the full range (40–220 BPM), normalized periodic triangular pulse trains $\mathbf{T}_{\text{BPM}, \phi}$ are evaluated against the ODF buffer using vectorized Pearson correlation:
$$r(\text{BPM}, \phi) = \frac{\sum (\mathbf{y} - \bar{y})(\mathbf{T} - \bar{T})}{\sigma_y \sigma_T}$$

### Logarithmic Base-Tempo (LBT) Classes
To completely prevent sub-harmonic and polyrhythmic octave-jumping traps, tempos are mapped into circular logarithmic octave space:
$$f(\text{BPM}) = \log_2\left(\frac{\text{BPM}}{60}\right) \pmod 1$$
Harmonic checks test $1:2$, $2:1$, and $3:2$ (perfect fifth) ratios before committing to a tempo change.

---

## 3. Dynamic Latency & Phase Back-Projection

### Total System Latency
Audio delay is dynamically computed per frame:
$$\Delta t_{\text{total}} = t_{\text{lookahead}} + \Delta t_{\text{dynamic\_audio\_latency}} + \Delta t_{\text{hardware\_latency}}$$
where:
- $t_{\text{lookahead}} = 5.0\text{ s}$
- $\Delta t_{\text{dynamic\_audio\_latency}} = \Delta t_{\text{adc}} + \Delta t_{\text{algorithmic}}$ (queried from PortAudio C-level `time_info.inputBufferAdcTime` plus the Hanning window algorithmic center $\frac{N_{\text{fft}}}{2 \cdot f_s} \approx 46.4\text{ ms}$).
- $\Delta t_{\text{hardware\_latency}}$ is the configured speaker/DAC output delay (default 0.0s).

### Phase Back-Projection to Speaker Time ($T_{\text{speaker}}$)
When the lookahead estimate yields future phase $\phi_{\text{ingest}}$, the phase at the physical speaker boundary is:
$$\phi_{\text{speaker}} = \left(\phi_{\text{ingest}} - \frac{\text{BPM}}{60} \cdot \Delta t_{\text{total}}\right) \pmod{1.0}$$

---

## 4. Continuous Adaptive Flywheel & Dropout Immunity

* **Continuous Freewheeling**: The internal `beat_phase` continuously advances in speaker time at rate $\frac{\text{BPM}}{60} \cdot dt$.
* **Adaptive Soft-Snapping**: 
  - If Pearson confidence $r \ge 0.30$ (high confidence): Snap phase by $50\%$ toward target $\phi_{\text{speaker}}$.
  - If $0.15 \le r < 0.30$ (moderate confidence): Gentle nudge ($15\%$).
  - If $r < 0.15$ (breakdowns / silence): Zero nudge ($0\%$), freewheel smoothly on inertia.
* **Real vs. Dropped Beat Validation**:
  When `beat_phase` wraps around $0.0$, local delayed ODF energy is validated:
  - If local transient energy $> \text{threshold}$: `is_real_beat = True`, tagged as `'Bass/Kick'`, `'Snare/Mid'`, or `'Hi-hat/Cymbal'`.
  - If transient is missing (breakdown): `is_real_beat = False`, `is_dropped_beat = True` (visual modes can choose to ignore or soften effects).
