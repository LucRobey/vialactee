# Audio Analyzer Data Contract & Variable Reference

This document serves as the authoritative contract and DSP reference for all audio analysis variables exposed through [`core/Listener.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/Listener.py) to visual modes (`self.listener.<attr>`) and orchestration engines ([`core/Transition_Director.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/Transition_Director.py)).

---

## 1. Architectural Pipeline & Timing Model

The audio analysis pipeline processes incoming audio in real time while supporting an optional lookahead buffer (`fakeDelay`, typically 5.0 seconds in Spotify / AUX playback).

```
                      INCOMING AUDIO (ADC / Stream)
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │     core/AudioIngestion.py   │
                    │   • 60 FPS Ring Buffering    │
                    │   • STFT FFT (1024 / 2048)   │
                    │   • 8-Band & 32-Band Mel Map │
                    │   • 12-TET Chromagram        │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ MultiBandOnsetAudioAnalyzer  │ ◄── Evaluates at T_lookahead
                    │   • Multi-band derivative dE │     (Microphone Time = T_speaker + 5.0s)
                    │   • Comb Filter Bank / Scouts│
                    │   • Pearson Flywheel Tracking│
                    │   • Structural Novelty (STM) │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       core/Listener.py       │ ◄── Applies FIFO Ring Buffers
                    │   • Delays features by 5.0s  │     (Synchronizes audio features to
                    │   • Exposes public facade    │      speaker playback time T_speaker)
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │        Visual Modes          │ ◄── Reads self.listener at 60 FPS
                    │   (modes/*.py on Raspberry)  │     Render loop (Axiom 1 & 2 compliant)
                    └──────────────────────────────┘
```

### The Two Timing Clocks
1. **Speaker Time ($T_{\text{speaker}}$)**:
   Synchronized exactly with the acoustic sound waves leaving the speakers and hitting spectator ears. **All visual lighting animations must synchronize with $T_{\text{speaker}}$.**
2. **Lookahead Time ($T_{\text{lookahead}} = T_{\text{speaker}} + \text{fakeDelay}$)**:
   The analysis engine processes the incoming stream ~5 seconds into the future. Variables prefixed with `live_` operate at $T_{\text{lookahead}}$ and allow predictive transitions, pre-drop blackouts, and anticipatory build-ups.

---

## 2. Complete Variable Contract

### Group A: Rhythmic & Kinematic Metronome Core

| Property on `self.listener` | Type / Range | Timing | Stability | What It Represents | How It Is Measured (DSP Mechanism) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`beat_phase`** | `float`<br>$[0.0, 1.0)$ | **$T_{\text{speaker}}$** | **Very High** | Continuous fractional position within the current beat.<br>• $0.0 =$ Downbeat hit<br>• $0.5 =$ Upbeat | An internal phase accumulator $\theta \in [0.0, 1.0)$ driven by the active tempo ($\Delta \theta = \frac{\text{BPM}}{60} \cdot dt$). Synchronized to $T_{\text{speaker}}$ using an offset reader into the 5-second ODF ring buffer. Soft-snapped backward/forward to avoid visual jumps. |
| **`bpm`** | `float`<br>$[60.0, 200.0]$ | **$T_{\text{speaker}}$** | **High** | Musical tempo in Beats Per Minute. | The onset derivative flux $dE$ is fed into a resonant IIR Comb Filter Bank spanning 60–200 BPM. Scout correlation peaks vote on candidates, filtered by a Bayesian Gaussian prior ($\mu = 125, \sigma = 40$) and constrained to dyadic octave lock ($\times 0.5, \times 1.0, \times 2.0$). |
| **`is_beat`** | `bool`<br>`True`/`False` | **$T_{\text{speaker}}$** | **High** (timing)<br>**Low** (presence) | 1-frame metronomic tick when `beat_phase` wraps around $1.0 \to 0.0$. | Raised when $\theta_t < \theta_{t-1}$ (phase wrap-around), subject to a minimum refractory lockout $\max(0.18\text{s}, 0.40 \cdot \frac{60}{\text{BPM}})$. **Note:** Ticks continuously even during silence due to flywheel momentum. |
| **`is_real_beat`** | `bool`<br>`True`/`False` | **$T_{\text{speaker}}$** | **High** | 1-frame trigger indicating an actual physical acoustic transient occurred on beat. | Evaluates whether `is_beat` is true **and** the delayed percussive flux at $T_{\text{speaker}}$ exceeds both a local baseline ($> 0.5 \times \text{baseline}$) and an absolute floor ($\ge 5.0$). **MANDATORY for hard strobes and shockwaves.** |
| **`is_dropped_beat`** | `bool`<br>`True`/`False` | **$T_{\text{speaker}}$** | **High** | 1-frame trigger indicating a metronomic beat occurred, but acoustic energy was missing. | True when `is_beat` is true but `is_real_beat` is false. Occurs during syncopation, drum rests, or breakdowns. |
| **`beat_confidence`** | `float`<br>$[-1.0, 1.0]$ | **$T_{\text{lookahead}}$**<br>(Leads by $\sim 2$–$5$s) | **High** (for 4/4)<br>**Moderate** (drift) | Correlation score measuring how clearly the music matches a periodic pulse. | Computed via Pearson correlation $r = \frac{T \cdot y}{\sigma_T \sigma_y}$ between the rolling 5.0s onset flux buffer and a synthetic triangular pulse train at current BPM, exponentially weighted toward newest audio. **Must be clipped in modes:** `np.clip(val, 0.0, 1.0)`. |
| **`flywheel_status`** | `str`<br>`'locked'`, `'coasting'` | **$T_{\text{lookahead}}$** | **High** | Operational state of the metronome flywheel. | Shifts to `'locked'` when `beat_confidence >= 0.15` and $\ge 4$ consecutive beats are verified; shifts to `'coasting'` during unmetered or low-confidence passages. |
| **`beat_count`** | `int`<br>$[0, \infty)$ | **$T_{\text{speaker}}$** | **High** (counter)<br>**Low** (measure) | Monotonic integer counter incremented on every `is_beat`. | Increments on every phase wrap. Resets to 0 on song change. **Do NOT use `beat_count % 4` for downbeats** (flywheel phase is not locked to bar boundaries). |
| **`band_flux`** | `np.ndarray (8,)`<br>$[0.0, \sim 500.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Delayed half-wave rectified onset derivative flux per frequency band. | Computed as $dE_b[t] = \max(0, E_b[t] - E_b[t-1])$ for each of the 8 Mel bands, then passed through `Listener` FIFO ring buffer to align with $T_{\text{speaker}}$. |
| ~~**`band_peak`**~~ | *None* | — | ❌ **REMOVED** | **DEPRECATED & REMOVED.** | Formerly dead feature (always 8 zeros). Removed from `Listener` ring buffers and analyzers. Modes must use `band_flux[b] > threshold` for per-band transient spike detection. |
| **`beat_tag`** | `str` | **$T_{\text{speaker}}$ via ring** | **High** | Transient classification: `'Bass/Kick'`, `'Snare/Mid'`, `'Hi-hat/Cymbal'`. | Evaluated using circular `band_flux_buffer` at the speaker playback offset ($T_{\text{speaker}}$), classifying the acoustic transient playing out of the speakers at the beat instant. |
| **`rhythm_salience`** | `float`<br>$[0.0, 1.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Normalized rhythmic prominence & groove saliency at speaker playback time. Differentiates driving percussive passages from ambient/unmetered sections. | Multi-pillar composite metric delayed by 5.0s ring buffer to align with $T_{\text{speaker}}$. Combines 4 acoustic pillars: transient ratio $\rho_{\text{trans}} = \frac{\Phi_{\text{drum}}}{\Phi_{\text{drum}} + 0.4 P_{\text{total}}}$ (0.30), percussive crest factor $C_{\text{norm}}$ (0.25), flywheel consensus $\gamma_{\text{conf}}$ (0.25), and pulse density $D_{\text{pulse}}$ (0.20), smoothed via asymmetric envelope (~50ms attack, ~1.5s release). |
| **`live_rhythm_salience`** | `float`<br>$[0.0, 1.0]$ | **$T_{\text{lookahead}}$**<br>(+5.0s future) | **High** | Anticipatory rhythmic salience evaluated on incoming microphone stream before delay buffer. Allows pre-drop visual build-up and predictive transitions. | Evaluated directly from unbuffered `MultiBandOnsetAudioAnalyzer.live_rhythm_salience` before ring buffer delay. Leads `rhythm_salience` by lookahead delay (`fakeDelay`, typically 5.0s). |
| **`standalone_phase`** / **`standalone_bpm`** | `float` | **$T_{\text{speaker}}$** | **High** | Backward-compatibility aliases for `beat_phase` and `bpm`. | Direct facade getters returning `beat_phase` and `bpm`. |

---

### Group B: Spectral Energy, Loudness & Timbre

| Property on `self.listener` | Type / Range | Timing | Stability | What It Represents | How It Is Measured (DSP Mechanism) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`asserved_total_power`** | `float`<br>$[0.0, 1.0]$ | **$T_{\text{speaker}}$ via ring** | **Very High** | Dynamic-range normalized total volume. Invariant to master volume. | Sum of all FFT power bins, smoothed via exponential filter, then divided by an adaptive Global Max envelope follower (`global_max = max(gm * 0.999, power)`). **Primary volume metric for ambient breathing & brightness.** |
| **`smoothed_total_power`** | `float`<br>$[0.0, \sim 2000.0]$ | **$T_{\text{speaker}}$ via ring** | **High** (unnormalized) | Exponentially smoothed raw total audio power. | Computed as $P_t = P_{t-1} + (1.0 - 0.5^{\text{fps\_ratio}}) \cdot (\sum \text{FFT} - P_{t-1})$. Tracks true physical loudness changes. |
| **`asserved_fft_band`** | `np.ndarray (8,)`<br>$[0.0, 1.0]$ | **$T_{\text{speaker}}$ via ring** | **Very High** | Dynamically normalized 8-band Mel spectrum. Invariant to input gain. | Each band power is mapped against running statistics ($\mu_b \pm 2\sigma_b$) and clamped to $[0.0, 1.0]$. **Primary input for graphic equalizers and spatial frequency bars.** |
| **`band_proportion`** | `np.ndarray (8,)`<br>$[0.0, 1.0]$ ($\sum=1$) | **$T_{\text{speaker}}$ via ring** | **Very High** | Normalized timbral fingerprint vector. Pure spectral distribution. | Instantaneous vector normalization: $p_b = \frac{E_b}{\sum_{j=0}^7 E_j + 10^{-6}}$. Completely invariant to total loudness. **Primary input for timbral color shifts and barycentric palettes.** |
| **`smoothed_fft_band_values`** | `np.ndarray (8,)`<br>$[0.0, \sim 500.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Asymmetric ADSR-filtered band power. | Filtered with fast attack coefficient ($0.2^{\text{ratio}}$) to catch transients instantly, and slow decay ($0.85^{\text{ratio}}$) to eliminate 60 FPS flicker. |
| **`fft_band_values`** | `np.ndarray (8,)`<br>$[0.0, \sim 500.0]$ | **$T_{\text{speaker}}$ via ring** | **Moderate** | Raw instantaneous 8-band Mel power. | Direct sum of FFT bin magnitudes within the 8 triangular Mel filters. High frame-to-frame variance; prefer `smoothed_fft_band_values`. |
| **`band_means`** | `np.ndarray (8,)`<br>$[0.0, \sim 500.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Long-term running mean power per band. | Very slow recursive single-pole IIR filter ($0.999^{\text{ratio}}$ retention). Represents the ambient acoustic noise floor. |
| **`dynamic_audio_latency`** | `float`<br>$\sim 0.05$–$0.09\text{s}$ | **ADC Instant** | **High** | Hardware ADC latency in seconds. | Dynamically measured from `sounddevice` input stream timestamps relative to system clock in `Local_Microphone.py`. |
| **`sensi`** / **`luminosite`** | `float`<br>$\sim 1.0$ / $[0.0, 1.0]$ | **Config Instant** | **High** | User sensitivity multiplier and master brightness floor. | Read directly from user configuration set via the web UI. |

---

### Group C: Macro-Structural Novelty & Form (Transitions & Drops)

| Property on `self.listener` | Type / Range | Timing | Stability | What It Represents | How It Is Measured (DSP Mechanism) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`is_song_change`** | `bool`<br>`True`/`False` | **$T_{\text{speaker}}$ via ring** | **High** (stops)<br>**Moderate** (mixes) | 1-frame trigger indicating a major song transition, crossfade, or silence drop. | Evaluated by `StructuralNoveltyDetector` when novelty distance breaches adaptive thresholds or silence exceeds 1.5s. Delayed by 5.0s ring buffer. Has 20s cooldown. |
| **`is_verse_chorus_change`** | `bool`<br>`True`/`False` | **$T_{\text{speaker}}$ via ring** | **Moderate** | 1-frame trigger indicating a sectional change (e.g. verse to chorus drop). | Triggered when novelty distance exceeds the Global Max threshold. Has 20s cooldown. Ideal for triggering dual-buffer crossfades. |
| **`live_is_song_change`** | `bool`<br>`True`/`False` | **$T_{\text{lookahead}}$**<br>(+5.0s future) | **High** | **Anticipatory trigger** firing 5.0s before a song change reaches the speakers. | Read directly from `StructuralNoveltyDetector` before the ring buffer delay. Arms `upcoming_song_change_countdown` in `Transition_Director`. |
| **`live_is_verse_chorus_change`** | `bool`<br>`True`/`False` | **$T_{\text{lookahead}}$**<br>(+5.0s future) | **Moderate** | Anticipatory trigger firing 5.0s before a section drop reaches the speakers. | Read directly from `StructuralNoveltyDetector` before delay. |
| **`asserved_novelty`** | `float`<br>$[0.0, 1.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Continuous macro-structural tension curve. | Computes Euclidean distance between Short-Term Memory (STM, ~3s) and Long-Term Memory (LTM, ~20s) timbre/power vectors, normalized against Local Max/Global Max envelopes. |
| **`combined_novelty`** | `float`<br>$[0.0, \sim 5.0]$ | **$T_{\text{speaker}}$ via ring** | **High** | Raw un-asserved structural distance metric. | Weighted combination: $0.7 \cdot \|\text{STM}_{\text{timbre}} - \text{LTM}_{\text{timbre}}\| + 0.3 \cdot |\text{STM}_{\text{power}} - \text{LTM}_{\text{power}}|$. |
| **`live_asserved_novelty`** | `float`<br>$[0.0, 1.0]$ | **$T_{\text{lookahead}}$**<br>(+5.0s future) | **High** | Lookahead structural tension curve. | Same metric evaluated on incoming microphone stream before delay buffering. Comparing `live_asserved_novelty` vs `asserved_novelty` detects builds and drops. |

---

### Group D: Tonal & Harmonic Chromagram

| Property on `self.listener` | Type / Range | Timing | Stability | What It Represents | How It Is Measured (DSP Mechanism) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`smoothed_chroma_values`** | `np.ndarray (12,)`<br>$[0.0, \sim 150.0]$ | **$T_{\text{speaker}}$ via ring** | **Moderate** | Energy distribution across 12 pitch classes (C, C#, D, ..., B). | FFT bin frequencies above 30 Hz are mapped into 12 semitone chroma bins using logarithmic frequency folding ($f \pmod{12}$), then smoothed with fast attack ($0.2$) and slow decay ($0.85$). **Primary input for harmonic color palettes.** |
| **`chroma_values`** | `np.ndarray (12,)`<br>$[0.0, \sim 150.0]$ | **$T_{\text{speaker}}$ via ring** | **Low to Moderate** | Raw instantaneous 12-pitch energy. | Direct chroma bin energy before ADSR filtering. Percussive broadband attacks bleed into all notes; prefer `smoothed_chroma_values`. |

---

## 3. Best Practices & Standard Patterns for Visual Modes

### Pattern 1: Rhythmic vs Ambient Blending (Mandatory Rule)
Never make lighting purely binary (`if self.listener.is_beat:`). Always blend rhythmic kinematics with acoustic power using `beat_confidence`:
```python
# 1. Rhythmic Confidence (clipped to valid range)
confidence = float(np.clip(self.listener.beat_confidence, 0.0, 1.0))

# 2. Continuous Phase Envelope (smooth 60 FPS decay)
rhythmic_energy = (1.0 - self.listener.beat_phase) ** 2.5

# 3. Ambient Volume Envelope (fallback for acoustic/pad passages)
ambient_energy = float(np.clip(self.listener.asserved_total_power, 0.0, 1.0))

# 4. Seamless Blended Luminance
final_brightness = (confidence * rhythmic_energy) + ((1.0 - confidence) * ambient_energy)
```

### Pattern 2: Gated Hard Strobes (Preventing Flashing on Silence)
```python
# Only detonate full-strip flashes when flywheel AND acoustic hit AND confidence agree:
if self.listener.is_beat and self.listener.is_real_beat and (self.listener.beat_confidence > 0.40):
    self.trigger_strobe()
```

### Pattern 3: Tempo-Synchronized Traveling Motion
```python
# Move a pulse across the strip so it travels exactly 1 length per beat:
dt_beat = 60.0 / max(60.0, self.listener.bpm)
speed_px_per_sec = float(self.num_leds) / dt_beat
self.position = (self.position + speed_px_per_sec * dt) % self.num_leds
```
