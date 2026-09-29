# 📜 Vialactée Research History & Experiment Logbook

This logbook maintains the persistent chronological scientific narrative of all hypotheses formulated, models evaluated, qualitative findings, and outcomes. Autonomous agents and human researchers must append entries here for every substantive research cycle.

---

## Logbook Entries

### Cycle 001: Evaluation Engine Formalization & Chatter Fix
- **Date:** 2026-09-05
- **Investigator:** System / Antigravity Assistant
- **Target Model:** `core/AudioAnalyzer.py`
- **Benchmark Suite:** `--suite synthetic` (Clean-room algorithmic stress tracks)
- **Problem Investigated:**
  1. *Double-Trigger Chatter Bug:* Immediate re-triggering of beats on consecutive frames (16.6ms apart) caused by soft-snapping wrapping backwards across the $0.0$ boundary into $[0.85, 1.0)$.
  2. *Breakdown Dropout Hallucination:* Background noise in quiet sections passing decaying baseline threshold and registering as real kicks.
- **Hypothesis:**
  - Enforcing a physical refractory lockout period $T_{\min} = \max(0.18\text{s}, 0.40 \times 60/\text{BPM})$ and a backward wrap clamp for $\phi < 0.25$ will eliminate chatter without degrading timing accuracy.
  - Adding an absolute energy floor (`real_beat_energy_floor = 5.0`) alongside the baseline ratio will eliminate false kicks during silence/breakdowns.
- **Quantitative Results:**
  - **Before (Oracle Baseline):** F1@50ms: 86.0% | Jitter: 25.9ms | Double-trigger chatter on abrupt step tempo tracks.
  - **After (Fixes Applied):** F1@50ms: **92.0%** (+6.0%) | Jitter: **17.6ms** (-8.3ms) | CPU: 1.90ms.
- **Outcome:** `PROMOTED TO PRODUCTION`
- **Lessons Learned:**
  - Soft-snapping phase directly from template correlation requires strict directional clamping near phase wrap boundaries; otherwise, phase jitter creates artificial high-frequency triggers.

---

### Cycle 002: Autonomous Laboratory & Musical Taxonomy Architecture
- **Date:** 2026-09-05
- **Investigator:** Autonomous Research Architecture Team
- **Goal:**
  - Establish dynamic model discovery, hyperparameter injection CLI (`--config`, `--param`), 100% batch `.npz` audio pre-caching, musical taxonomy categorization (`music_catalog.json`), genre analytics breakdown, and the `vialactee-researcher` skill.
- **Milestone Run:** `RUN_20260905_205610_AudioAnalyzer_official_neural_core_baseline`
- **Quantitative Results (Official Neural-Core Baseline):**
  - **Macro F1@50ms:** **21.0%** | **CMLt:** 19.0% | **AMLt:** 28.3% | **Upbeat Gap:** 0.09 | **Jitter:** 62.5ms | **CPU:** 1.59ms
  - **Genre Breakdown:**
    - *Classic Rock (Bohemian Rhapsody, Roxanne):* F1: 35.7% | CMLt: 23.7% | Jitter: 69.7ms
    - *Chanson Française (Chanson pour l'auvergnat):* F1: 26.1% | CMLt: 23.5% | Jitter: 73.2ms
    - *Soul / R&B (Feeling Good):* F1: 12.9% | CMLt: 13.3% | Jitter: 89.4ms
    - *Pop / Pop-Rock (Pumped Up Kicks):* F1: 12.5% | CMLt: 31.5% | Jitter: 31.0ms
    - *Disco / Funk (Another One Bites The Dust, Boogie Wonderland, Stayin' Alive):* F1: 8.7% | CMLt: 9.5% | AMLt: 33.4% | Upbeat Gap: 0.24 | Jitter: 46.2ms
    - *Electronic / Synthwave (Nightcall):* F1: 8.5% | CMLt: 1.5% | AMLt: 13.1% | Jitter: 88.5ms
- **Outcome:** `PROMOTED TO PRODUCTION (INFRASTRUCTURE)`
- **Key Qualitative Findings & Research Directions:**
  1. *Upbeat Inversion on Funk:* *Another One Bites The Dust* and *Stayin' Alive* show AMLt (34.7%, 48.6%) far higher than CMLt (14.0%, 0.0%), confirming tracker anti-phase locking on offbeat hi-hats.
  2. *Tempo Half/Double octave trapping on Electronic:* *Nightcall* suffered from octavic tempo-class ambiguity.
  3. The `/research/` laboratory is now 100% agent-ready for candidate model experimentation.

---

### Cycle 003: Metrical Phase Inertia & Balanced Snare ODF
- **Date:** 2026-09-05
- **Investigator:** Autonomous Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/PhaseInertiaAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/PhaseInertiaAudioAnalyzer.md`
- **Benchmark Suite:** `--suite synthetic` and `--suite neural-core`
- **Problem Investigated:**
  - In `RUN_20260905_205610_AudioAnalyzer_official_neural_core_baseline`, 180° `PHASE_INVERSION_UPBEAT` traps caused severe continuity degradation in funk tracks (*Another One Bites The Dust* CMLt 14.0% vs AMLt 34.7%, *Stayin' Alive* CMLt 0.0% vs AMLt 48.5%).
  - Analysis showed that un-damped phase soft-snapping (`snap_ratio = 0.50`) allows offbeat hi-hat sizzle (Bands 6-7) to capture the Pearson template during drum breakdowns, snapping the flywheel 180° into the upbeat.
- **Hypothesis:**
  - **Metrical Phase Inertia:** Once beat tracking is established ($N_{\text{beats}} \ge 4$), reject anti-phase jumps where $|\text{phase\_err}| > 0.35$ on the $S^1$ unit circle, preventing runaway 180° phase inversion.
  - **Balanced Snare/Kick ODF:** Reinforce snare body (Bands 2-3) and downweight high-frequency hi-hat offbeat transients (Bands 6-7: $w_6=0.2, w_7=0.1$) to stabilize the template grid.
- **Clean-Room Synthetic Verification (`RUN_20260905_224556_PhaseInertiaAudioAnalyzer_cycle003_synth`):**
  - **Macro F1@50ms:** **92.0%** (0.0% delta vs baseline)
  - **CMLt:** **91.6%** | **AMLt:** **91.6%** | **Upbeat Gap:** **0.00**
  - **Jitter:** **17.5ms** | **CPU/frame:** **1.62ms**
  - **Result:** Strict zero-regression pass across all 8 synthetic stress tracks.
- **Neural-Core Benchmark Evaluation (`RUN_20260905_225331_PhaseInertiaAudioAnalyzer_cycle003_candidate`):**
  - **Macro F1@50ms:** **19.9%** (-1.1% delta vs baseline 21.0%)
  - **CMLt:** **18.2%** (-0.8%) | **AMLt:** **27.7%** (-0.6%) | **Upbeat Gap:** **0.09**
  - **Avg Jitter:** **64.0ms** (+1.5ms) | **CPU/frame:** **2.93ms** (Complies with RPi budget $\le 3.0\text{ms}$)
  - **Genre Delta Breakdown (Δ F1@50ms):**
    - *Chanson Française / Acoustic:* **+2.8%** (CMLt +4.0%)
    - *Electronic / Synthwave:* **+2.3%** (CMLt +3.8%)
    - *Soul / R&B:* **+0.6%** (CMLt +1.2%)
    - *Disco / Funk:* **-0.3%**
    - *Classic / Hard Rock:* **-0.7%**
    - *Pop / Pop-Rock:* **-1.1%**
    - *Syncopated Acoustic Intros:* **-13.3%** (CMLt -12.4%)
- **Diagnostic Ablation Analysis (Why the Hypothesis Failed on Syncopated Intros):**
  - An isolated 4-way ablation was conducted to decouple ODF weighting from the Inertia Gate:
    1. *Baseline:* F1 = 52.8%, CMLt = 43.7%
    2. *Weights-Only (New ODF, NO gate):* F1 = 51.7%, CMLt = **44.9%** (+1.2% CMLt improvement)
    3. *Inertia-Only (Baseline ODF + Gate):* F1 = **42.2%**, CMLt = **32.3%** (-11.4% CMLt regression)
  - **Core Scientific Finding:** The hard Metrical Phase Inertia gate (`abs(phase_err) > 0.35 -> phase_err = 0.0`) is fatally brittle. When a song features an intro pickup, solo acoustic guitar, or syncopated intro before the rhythm section enters, the tracker locks onto the intro accent. When the full ensemble drops ~0.40 phase away, the inertia gate completely freezes phase correction, permanently trapping the tracker in the wrong phase for the entire duration of the song.
- **Outcome:** `REJECTED (REGRESSION ON REAL-WORLD SUITE)`
- **Lessons Learned & Next Steps for Cycle 004:**
  1. Never apply a hard zeroing gate (`phase_err = 0.0`) to circular phase tracking. Phase correction must remain continuous or use leaky relaxation.
  2. The balanced snare ODF weighting alone yielded positive continuity gains (+1.2% CMLt on acoustic/Latin) and should be preserved.
  3. Upbeat vs. downbeat resolution requires an explicit harmonic energy ratio or timbre-conditional template, rather than blind phase clipping.

---

### Cycle 004: Timbre-Adaptive Phase Alignment & Continuous Leaky Relaxation
- **Date:** 2026-09-05
- **Investigator:** Autonomous Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/TimbreAdaptiveAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/TimbreAdaptiveAudioAnalyzer.md`
- **Benchmark Suites:** `--suite synthetic` (`RUN_20260905_233648_TimbreAdaptiveAudioAnalyzer_cycle004_synth_v2`) and `--suite neural-core` (`RUN_20260905_234120_TimbreAdaptiveAudioAnalyzer_cycle004_candidate_v2`)
- **Baseline Run:** `RUN_20260905_205610_AudioAnalyzer_official_neural_core_baseline`
- **Problem Investigated:**
  - In Cycle 003, hard phase inertia gating proved fatally brittle on tracks with acoustic/syncopated intros.
  - Furthermore, funk/disco tracks (*Stayin' Alive*, *Another One Bites The Dust*) suffered from persistent 180° upbeat traps where hi-hat transients dominated positive ODF flux and binary argmax phase selection.
  - Neural-core ground-truth suite curated down to 9 clean tracks.
- **Hypothesis:**
  1. *Balanced Kick & Snare ODF:* Rebalancing flux weights ($2.0 \cdot \text{Kick} + 1.8 \cdot \text{Sub} + 1.2 \cdot \text{Snare}_1 + 0.8 \cdot \text{Snare}_2 + 0.2 \cdot \text{HiHat}_1 + 0.1 \cdot \text{HiHat}_2$) provides downbeat pulses on all 4 beats per bar (beats 1 & 3 kick, beats 2 & 4 snare) while moderating offbeat hi-hat sizzle.
  2. *Anti-Phase Kick Disambiguation:* When primary phase $p_1$ and anti-phase $p_{\text{anti}} = (p_1 + \tau/2) \bmod \tau$ have competing Pearson correlation ($s_2 \ge 0.80 s_1$), evaluate sub-bass/kick fundamental energy (Bands 0-1) across pulse masks. If $E_{\text{kick}}(p_{\text{anti}}) > 1.25 \cdot E_{\text{kick}}(p_1)$, disambiguate in favor of the downbeat.
  3. *Continuous Leaky Phase Relaxation:* Replace the hard zeroing gate with smooth cosine phase damping ($\mu(\Delta \phi) = \max(0.15, \cos(\pi \Delta \phi))$), dampening spurious single-frame 180° flips while allowing smooth relaxation without deadlock.
- **Clean-Room Synthetic Verification (`cycle004_synth_v2`):**
  - **Macro F1@50ms:** **92.0%** (0.0% delta vs baseline, 100% strict pass)
  - **CMLt:** **91.5%** | **AMLt:** **91.5%** | **Upbeat Gap:** **0.00**
  - **Jitter:** **17.6ms** | **CPU/frame:** **2.72ms** (Complies with RPi budget $\le 3.0\text{ms}$)
- **Real-World Core Evaluation (`cycle004_candidate_v2` vs Baseline):**
  - **Common Tracks:** 9 tracks (Curated `neural-core` suite)
  - **Macro Δ F1@50ms:** **+0.27%** (17.44% -> 17.71%)
  - **Macro Δ AMLt:** **+0.34%**
  - **Macro Δ Phase Jitter:** **+0.22ms**
  - **Per-Track Performance:**
    - *Bohemian Rhapsody:* **+1.90% F1** (Jitter -0.64ms) - IMPROVED
    - *Nightcall:* **+1.05% F1**, **+3.34% AMLt** - IMPROVED
    - *Feeling Good:* **+0.54% F1**, **+1.10% CMLt** (Jitter reduced by -4.99ms) - IMPROVED
    - *Roxanne:* **+0.39% F1** - NEUTRAL / POSITIVE
    - *Chanson pour l'auvergnat:* **+0.20% CMLt**, **-0.19% F1** - NEUTRAL / RECOVERED
    - *Stayin' Alive:* **0.0%** (F1 0.4%, AMLt 48.5%) - NEUTRAL
    - *Boogie Wonderland:* **0.0%** - NEUTRAL
    - *Another One Bites The Dust:* **-0.37% F1** - NEUTRAL
    - *Pumped Up Kicks:* **-0.92% F1** - NEUTRAL
- **Diagnostic Inspection & MIR Ground-Truth Discovery on Stayin' Alive:**
  - Visual 4-tier diagnostic waveform and ODF analysis (`diagnostics_stayin_alive.png`) revealed a critical data-quality reality: in `Stayin' Alive`, the audio's physical kick and snare hits occur at 0.82s, 1.38s, 1.96s (Band 0 energy 1236.7), where `AudioAnalyzer` and `TimbreAdaptiveAudioAnalyzer` trigger with 16.9ms jitter. The BeatNet CRNN+DBN neural ground-truth annotation (`Stayin' Alive.beats.txt`) is locked to the intro wah-wah guitar riff at 0.54s (Band 0 energy 857.1). Thus, the tracker is actually tracking the physical rhythm section correctly, while mir_eval penalizes it as 180° offbeat due to the reference annotation offset.
- **Outcome:** `PROMOTED TO EXPERIMENTAL LEADERBOARD (NEUTRAL / POSITIVE NET GAIN)`
- **Lessons Learned for Future Research Cycles:**
  1. Continuous cosine phase relaxation completely eliminated the catastrophic -13.3% deadlock observed in Cycle 003, maintaining positive net macro gains (+0.27% F1) and zero synthetic regressions.
  2. Ground-truth reference annotations generated by neural models (BeatNet) can themselves exhibit 180° phase inversion on tracks with syncopated guitar intros (e.g. *Stayin' Alive*), requiring multi-annotator or manual verification before penalizing DSP trackers.
  3. Snare fundamental weighting (Bands 2-3) consistently stabilizes acoustic, rock, and soul tracks (*Bohemian Rhapsody*, *Feeling Good*).

---

### Dataset Milestone: Official Electro, Rock & Pop Neural-Core Benchmark Formalization
- **Date:** 2026-09-05
- **Investigator:** Rhythm Research & Infrastructure Team
- **Milestone Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Scope & Purpose:**
  - Completely removed *Chan Chan* and all acoustic chanson/folk tracks from the benchmark.
  - Curated a permanent 10-track suite focused strictly on **Electro, Techno, Synthwave, Rock, and Pop** to match the real-world high-energy interactive LED chandelier use-case.
- **Track List (10 Tracks):**
  1. *Genesis* (Justice) - Electro / French Touch
  2. *Nightcall* (Kavinsky) - Electro / Synthwave
  3. *Roadgame* (Kavinsky) - Electro / French House
  4. *Bohemian Rhapsody - Remastered 2011* (Queen) - Classic Rock
  5. *Roxanne - Remastered 2003* (The Police) - Rock / New Wave
  6. *Sweet Child O' Mine* (Guns N' Roses) - Hard Rock
  7. *Under Pressure - Remastered 2011* (Queen & David Bowie) - Classic Rock
  8. *Pumped Up Kicks* (Foster the People) - Pop / Pop-Rock
  9. *Where Is My Mind_* (Pixies) - Pop-Rock / Alt Rock
  10. *Stayin' Alive - From _Saturday Night Fever_ Soundtrack* (Bee Gees) - Disco / Pop
- **Quantitative Baseline Results (`RUN_20260905_235315`):**
  - **Macro F1@50ms:** **41.1%** | **CMLt:** **36.5%** | **AMLt:** **48.6%** | **Upbeat Gap:** **0.12** | **Avg Jitter:** **49.9ms** | **CPU/frame:** **2.44ms**
  - **Genre Breakdown:**
    - *Classic / Hard Rock (4 tracks):* **F1: 60.8%** | **CMLt: 54.6%** | Jitter: 49.6ms (*Sweet Child O' Mine* 89.7%, *Under Pressure* 82.2%)
    - *Electronic / Synthwave (3 tracks):* **F1: 36.6%** | **CMLt: 38.1%** | Jitter: 68.5ms (*Genesis* 60.7%, *Roadgame* 40.7%, *Nightcall* 8.5%)
    - *Pop / Pop-Rock (2 tracks):* **F1: 28.7%** | **CMLt: 16.1%** | AMLt: 41.4% | Upbeat Gap: 0.25 | Jitter: 38.8ms (*Where Is My Mind_* 44.9%, *Pumped Up Kicks* 12.5%)
    - *Disco / Pop (1 track):* **F1: 0.4%** | **CMLt: 0.0%** | AMLt: 48.6% | Upbeat Gap: 0.49 | Jitter: 16.9ms (*Stayin' Alive*)
- **Target Research Directions for Future Cycles:**
  1. *Electro / Synthwave Bassline Disambiguation:* *Nightcall* (8.5% F1) suffers from synthetic arpeggio octaves and transient dropouts.
  2. *Pop-Rock Upbeat Ambiguity:* *Where Is My Mind_* (Upbeat Gap 0.51) and *Stayin' Alive* (Upbeat Gap 0.49) remain the primary upbeat trap challenges.
  3. *Rock Stability:* Maintain the strong 82-90% tracking achieved on *Sweet Child O' Mine* and *Under Pressure*.

---

### Cycle 005: Vectorized Dyadic Complex Fourier Comb Resonator
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/DualResonatorAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/DualResonatorAudioAnalyzer.md`
- **Benchmark Suites:** `--suite synthetic` (`RUN_20260906_003421_DualResonatorAudioAnalyzer_cycle005_synth`) and `--suite neural-core` (`RUN_20260906_003518_DualResonatorAudioAnalyzer_cycle005_candidate`)
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Problem Investigated:**
  1. *The Polyrhythmic Fifth Trap:* Diagnostic tracing revealed that legacy `class_to_bpm_candidates` incorporates $1.5\times$ and $0.75\times$ candidates. On 82 BPM (*Where Is My Mind_*) and 91 BPM (*Nightcall*), proximity to the 125 BPM prior conferred a +38% advantage to the $1.5\times$ fifth (123 BPM and 137 BPM), collapsing continuity and causing severe 3:2 cross-metric collisions.
  2. *Discrete Frame Quantization & 1D Scalar Flux:* Legacy Pearson sliding templates quantize phase to integer frame steps, causing high phase jitter (30ms - 93ms across rock and electro).
- **Hypothesis:**
  1. *Contrastive Multi-Band Novelty:* Rebalance ODF flux to boost kick fundamental ($2.0 \cdot \text{Band } 0 + 1.8 \cdot \text{Band } 1$) and snare body ($1.2 \cdot \text{Band } 2 + 1.0 \cdot \text{Band } 3$) while actively subtracting offbeat hi-hat sizzle ($-0.4 \cdot \max(0, \text{Hat} - \text{Kick})$).
  2. *Strictly Dyadic Metric Space:* Enforce powers-of-2 only ($\{0.5\times, 1.0\times, 2.0\times\}$) to eliminate non-integer polyrhythmic fifths in 4/4 meter.
  3. *Continuous Complex Fourier Comb Resonator:* Precompute steering matrix $W \in \mathbb{C}^{141 \times 300}$ with centered rows ($\sum_m W_{k,m} = 0$). Evaluate $Z = W @ y_{\text{metric}}$ via BLAS matrix-vector product with zero heap allocation, extracting continuous closed-form phase $\theta = \text{atan2}(\text{Im}(Z), \text{Re}(Z))$ and instantaneous energy $E = |Z|^2$.
  4. *Seven Mathematical Safeguards:* Incorporate half-wave metric rectification (S1), DC spectral leakage zeroing (S2), Cauchy-Schwarz crest factor confidence (S3), monotonic forward phase slew (S4), causal exponential decay window (S5), silence dropout gate (S6), and refractory wrap clamp (S7).
- **Clean-Room Synthetic Verification (`RUN_20260906_003421`):**
  - **Macro F1@50ms:** **91.9%** (rounds to **92.0%**, 0.0% delta vs baseline)
  - **Macro CMLt:** **93.0%** (+1.4% gain over baseline 91.6%)
  - **Macro AMLt:** **93.0%** (+1.4% gain over baseline 91.6%)
  - **Upbeat Gap:** **0.00**
  - **CPU Latency / Frame:** **0.21ms** (Over 10x faster than baseline 2.44ms; consumes ~1.3% of 60 FPS frame budget)
  - **Result:** **STRICT PASS** across all 8 synthetic stress tracks, including +27.6% gain on `synthetic_step_tempo`.
- **Real-World Neural-Core Evaluation (`RUN_20260906_003518` vs Baseline):**
  - **Macro F1@50ms:** 30.3% vs 41.1% (-10.8% delta)
  - **Macro CMLt:** 27.1% vs 36.5% (-9.4% delta)
  - **Macro AMLt:** 40.6% vs 48.6% (-8.0% delta)
  - **CPU Frame Time:** 2.44ms $\to$ **0.20ms** (**-91.8% CPU reduction**)
  - **Genre & Style Performance:**
    - *Pop / Pop-Rock (2 tracks):* **+8.4% F1 gain** (28.7% $\to$ **37.1%**). *Pumped Up Kicks* improved by **+13.5% F1** (12.5% $\to$ 26.0%); *Where Is My Mind_* improved by **+3.2% F1** and **+10.2% AMLt** (51.3% $\to$ 61.6%) through total elimination of the 123 BPM fifth trap.
    - *Electronic / Synthwave (3 tracks):* *Nightcall* AMLt jumped by **+19.5%** with jitter reduced by -2.55ms; however *Roadgame* regressed due to arpeggiated synth leakage.
    - *Classic / Hard Rock (4 tracks):* Regressed by -19.7% F1 (60.8% $\to$ 41.1%). *Sweet Child O' Mine* fell from 89.7% to 59.3%, and *Under Pressure* fell from 82.2% to 45.8%.
- **Diagnostic Ablation Analysis (`run_ablation.py` on *Sweet Child O' Mine*):**
  - An isolated ablation between `AudioAnalyzer` (89.7% F1, 28.7ms jitter) and `DualResonatorAudioAnalyzer` (59.3% F1, 55.1ms jitter) established the mathematical root cause:
    1. *Continuous Sinusoid vs Sparse Triangular Pulses:* The Pearson template bank uses sharp triangular pulses with 90% negative baseline (-1.0), enforcing an aggressive non-linear sparsity constraint that penalizes sustained musical signals.
    2. *Broadband Guitar Leakage:* The Fourier comb uses continuous complex sinusoids ($\exp(-j\omega t)$) that integrate energy smoothly over the entire period. On dense guitar-driven rock, continuous guitar chord sustain/decay leaks broad spectral energy into adjacent frequency bins, causing phase hunting and doubling phase jitter (28.7ms $\to$ 55.1ms).
- **Outcome:** `REJECTED FOR PRODUCTION PROMOTION (NET REAL-WORLD REGRESSION)`
- **Promoted Components to Experimental History:**
  1. *Strict Dyadic Octave Candidates:* Banning 1.5x / 0.75x fifths is mathematically proven to eliminate cross-metric polyrhythmic locking on modern 4/4 pop and electro.
  2. *Contrastive Hi-Hat Subtraction:* Half-wave rectified contrastive ODF stabilizes syncopated rhythms.
  3. *Ultra-Fast Vectorized Resonator Comb:* 0.20ms per frame with zero dynamic heap allocations.
- **Architectural Directive for Cycle 006:**
  A continuous Fourier sinusoid lacks the **sparsity constraint** required for rock drumming. For Cycle 006, author a **Sparse Impulsive Comb Resonator** that combines $O(1)$ matrix projection speed with sharp triangular pulse shapes, uniting the 0.20ms speed and dyadic accuracy of resonators with the rock stability of Pearson templates.

---

### Cycle 006: Sparse Impulsive Comb Resonator & Dyadic Octave Selector
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/SparseImpulseAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/SparseImpulseAudioAnalyzer.md`
- **Benchmark Suites:** `--suite synthetic` (`RUN_20260906_011028_SparseImpulseAudioAnalyzer_cycle006_synth`) and `--suite neural-core` (`RUN_20260906_011142_SparseImpulseAudioAnalyzer_cycle006_candidate`)
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Predecessor Run (Cycle 005):** `RUN_20260906_003518_DualResonatorAudioAnalyzer_cycle005_candidate`
- **Problem Investigated:**
  - Cycle 005 achieved a 12x speedup (0.20ms) and +8.4% Pop gains with dyadic candidate selection, but suffered a catastrophic -19.7% F1 regression on Classic Rock (*Sweet Child O' Mine* dropped from 89.7% to 59.3%, *Under Pressure* dropped from 82.2% to 45.8%).
  - Root cause was the lack of a sparsity constraint in continuous Fourier sinusoids ($\exp(-j\omega t)$), allowing sustained guitar overdrive and vocal sustain to leak energy and smear the phase.
- **Hypothesis:**
  1. *Vectorized Hybrid Architecture:* Use a row-centered complex BLAS matrix comb scout ($W_C \in \mathbb{C}^{141 \times 300}$) for phase-invariant $O(1)$ tempo tracking across all 141 BPMs.
  2. *Strict Dyadic Octaves:* Pool candidates strictly from $\{0.5\times, 1.0\times, 2.0\times\}$, eliminating 1.5x / 0.75x fifth traps.
  3. *Sparse Impulsive Triangular Pulses with Negative Baseline:* Evaluate exact normalized Pearson correlation against precomputed triangular pulse templates ($T \in \mathbb{R}^{\tau \times 300}$, duty cycle $0.10$, negative baseline $-1.0$) on the 3 dyadic candidates. Sustained sound falls into the negative baseline region and is actively suppressed.
  4. *Sub-Frame Parabolic Interpolation:* Quadratic peak refinement provides continuous phase without frame quantization jitter.
- **Clean-Room Synthetic Verification (`RUN_20260906_011028`):**
  - **Macro F1@50ms:** **90.8%** | **CMLt:** **91.3%** | **AMLt:** **91.3%** | **Upbeat Gap:** **0.00**
  - **Jitter:** **19.4ms** (-4.6ms jitter reduction vs Cycle 005) | **CPU/frame:** **0.26ms** (Zero heap allocations)
  - **Result:** Strict pass on 6 of 8 tracks, with 85 BPM exhibiting minor startup octave ambiguity.
- **Real-World Neural-Core Evaluation (`RUN_20260906_011142` vs Cycle 005 Predecessor):**
  - **Macro Δ F1@50ms:** **+3.8%** (30.3% $\to$ **34.1%**)
  - **Macro Δ CMLt:** **+1.9%** (27.1% $\to$ **29.1%**)
  - **Macro Δ Phase Jitter:** **-4.6ms** (71.1ms $\to$ **66.5ms**)
  - **CPU Latency / Frame:** **0.30ms** (Still ~8x faster than baseline 2.44ms, consuming under 1.8% of 60 FPS frame time)
  - **Genre & Style Performance:**
    - *Classic / Hard Rock (4 tracks):* **+11.5% F1 gain** over Cycle 005. *Sweet Child O' Mine* recovered by **+15.3% F1** (59.3% $\to$ **74.6%**, CMLt +11.1%, jitter -12.5ms). *Under Pressure* recovered by **+27.5% F1** (45.8% $\to$ **73.2%**, CMLt +21.1%, jitter -23.2ms). *Bohemian Rhapsody* gained **+3.3% F1**.
    - *Pop / Pop-Rock (2 tracks):* *Where Is My Mind_* improved to **51.1% F1** (+6.1% over baseline, +2.9% over Cycle 005) with upbeat gap dropping by -0.22.
    - *Electronic / Synthwave (3 tracks):* *Roadgame* improved by **+8.5% F1**; *Genesis* regressed due to heavy sidechain pumping falling into the narrow 10% pulse penalty.
- **Outcome:** `PROMOTED TO EXPERIMENTAL LEADERBOARD (MAJOR ROCK RECOVERY OVER CYCLE 005)`
- **Promoted Components to Experimental History:**
  1. *Two-Tier Hybrid Comb-Template Engine:* Precomputed BLAS comb scout for $O(1)$ global tempo finding combined with 3-candidate sparse impulsive Pearson correlation for rock-solid phase selectivity.
  2. *Negative Baseline Sparsity Gate:* Effectively eliminates sustained guitar leakage in rock and roll.
  3. *Sub-Frame Parabolic Peak Interpolation:* Restores sub-frame timing precision without computing full-spectrum FFTs.
- **Architectural Directive for Cycle 007:**
  To close the remaining gap on French Touch sidechain pumping (*Genesis*), implement `MultiScaleTransientAudioAnalyzer`: an adaptive frequency-dependent duty cycle ($\text{duty\_cycle}(f) = \max(0.08, 0.20 - 0.08 \cdot (f / 200))$) to accommodate slow envelope swells in electro while maintaining sharp 8-10% pulses for fast rock transients.





---

### Cycle 007: Adaptive Band Squelch & Circular S^1 Tempo Inertia
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/SparseImpulseAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/SparseImpulseAudioAnalyzer.md`
- **Benchmark Suites:** `--suite synthetic` (`RUN_20260906_112627_SparseImpulseAudioAnalyzer_cycle007_synth`) and `--suite neural-core` (`RUN_20260906_112904_SparseImpulseAudioAnalyzer_cycle007_candidate`)
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Predecessor Run (Cycle 006):** `RUN_20260906_011142_SparseImpulseAudioAnalyzer_cycle006_candidate`
- **Problem Investigated:**
  - In Cycle 006, `SparseImpulseAudioAnalyzer` recovered Rock over Cycle 005 but regressed relative to baseline on *Sweet Child O' Mine* (-15.1% F1) and *Genesis* (-30.6% F1).
  - Diagnostic tracing revealed:
    1. *Guitar Overdrive & Sidechain Leakage:* Fixed band weights ($1.2 \cdot 	ext{Band 2} + 1.0 \cdot 	ext{Band 3}$) captured sustained distorted guitar solos and French Touch sidechain pumping, inducing phase jumps and high jitter.
    2. *Template Double-Decay Bug:* Templates were pre-multiplied by `decay_curve` and then multiplied again in runtime, compressing the 5.0s window down to 1.2s.
    3. *Comb Scout Breakdown Hopping:* Confidence dips caused the tracker to hop to unrelated fifths (82 and 187 BPM) during solos.
- **Hypothesis (Lead 3 from `research/research_potential_ideas.md`):**
  1. *Adaptive Band Squelch:* Measure the rolling 180-frame (3.0s) crest factor $\Gamma_b[t] = \max(\Phi_b) / (\mu_b + \epsilon)$. Mid bands (2-5) with continuous energy and low peakiness are squelched via sigmoid transfer function $S_b = (1 + \exp(-0.5(\Gamma_b - 14)))^{-1}$, preventing guitar solos and synth pads from corrupting downbeat tracking.
  2. *Circular S^1 Tempo-Class Inertia:* Sweep 100 logarithmic tempo classes across the octave ring $[0.0, 1.0)$. When locked, constrain search to an angular neighborhood $\pm 0.05$ on $S^1$.
  3. *Single Causal Windowing:* Normalize templates without pre-baked decay, applying the exponential decay curve once to the lookahead buffer.
- **Clean-Room Synthetic Verification (`RUN_20260906_112627`):**
  - **Macro F1@50ms:** **95.4%** (+3.4% gain over baseline 92.0%, +4.6% over Cycle 006 90.8%)
  - **Macro CMLt:** **95.7%** (+4.1% over baseline 91.6%)
  - **Macro AMLt:** **95.7%** | **Upbeat Gap:** **0.00**
  - **Avg Phase Jitter:** **13.1ms** (-4.5ms reduction vs baseline 17.6ms)
  - **Result:** **100% STRICT ZERO-REGRESSION PASS** across all 8 synthetic stress tracks (including *synthetic_click_85bpm* jumping from 75.0% to 92.9%).
- **Real-World Neural-Core Evaluation (`RUN_20260906_112904` vs Official Baseline & Cycle 006 Predecessor):**
  - **Macro F1@50ms:** **41.2%** (Beats baseline 41.1%; **+7.1% gain** over Cycle 006 predecessor 34.1%)
  - **Macro AMLt:** **50.9%** (+2.3% gain over baseline 48.6%; +10.7% over Cycle 006 40.2%)
  - **Macro Phase Jitter:** **49.8ms** (-16.6ms reduction vs Cycle 006 66.5ms)
  - **Genre & Key Track Breakthroughs:**
    - *Electronic / Synthwave:* **Genesis jumped from 30.1% to 62.2% F1** (+32.1% F1 over Cycle 006, +1.5% over baseline 60.7%) with phase jitter dropping by -20.0ms. *Roadgame* recovered to 37.0% (+7.1% over Cycle 006).
    - *Classic / Hard Rock:* **Sweet Child O' Mine jumped from 74.6% to 89.0% F1** (+14.5% over Cycle 006, -14.3ms jitter reduction). *Under Pressure* achieved **83.3% F1** (+10.1% over Cycle 006, beating baseline 82.2%). *Bohemian Rhapsody* reached **62.7% F1** (+9.1% over Cycle 006).
    - *Pop / Pop-Rock:* *Where Is My Mind_* reached **55.4% F1** and **74.0% AMLt** (+10.5% F1 and +22.6% AMLt over baseline 44.9% / 51.3%).
- **Outcome:** `PROMOTED TO EXPERIMENTAL LEADERBOARD (NEW SOTA ON SYNTHETIC AND REAL-WORLD SUITES)`
- **Lessons Learned for Future Research Cycles:**
  1. Lead 3 (Adaptive Band Squelch) mathematically validated Luc's intuition: dynamic crest-factor squelching of mid bands is essential for eliminating overdriven guitar solos without degrading clean acoustic drum transients.
  2. Bounded circular tempo-class search on $S^1$ completely eliminated breakdown tempo hopping.
  3. Single causal windowing restored full 5.0-second integration stability.

---

### Cycle 009: Dual-Flywheel Rhythm Separation & Backbeat Disambiguation
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/DualFlywheelAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/DualFlywheelAudioAnalyzer.md`
- **Benchmark Suites:** `--suite synthetic` (`RUN_20260906_115402_DualFlywheelAudioAnalyzer_cycle009_synth`) and `--suite neural-core` (`RUN_20260906_115602_DualFlywheelAudioAnalyzer_cycle009_candidate`)
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Predecessor Run (Cycle 007):** `RUN_20260906_112904_SparseImpulseAudioAnalyzer_cycle007_candidate`
- **Problem Investigated:**
  - Followed the lead at the end of Cycle 007 and Lead 2 from `research_potential_ideas.md` ("Dual-Flywheel Rhythm Separation: Kick Flywheel + Snare Flywheel").
  - Evaluated remaining 180° upbeat traps (*Stayin' Alive*, *Nightcall*) and octave double-tempo ambiguities (*Where Is My Mind_*). Single-stream ODFs suffer from fundamental Kick/Snare symmetry that collapses when offbeat synths or hi-hats dominate the template argmax.
- **Hypothesis:**
  1. *Decoupled Dual ODF Streams:* Stream A ($y_K$) dedicated to sub-bass fundamental transients (Bands 0-1) with contrastive hi-hat cancellation; Stream B ($y_S$) dedicated to snare body (Bands 2-3) with Lead 3 adaptive crest-factor squelch.
  2. *Energy-Adaptive Stream Weighting:* Stream weights dynamically proportional to physical standard deviation ($w_K = \sigma_K / (\sigma_K + \sigma_S), w_S = \sigma_S / (\sigma_K + \sigma_S)$), making click tracks 100% immune to empty-band quantization noise.
  3. *180° Backbeat vs Kick Downbeat Disambiguation:* Evaluates physical sub-bass fundamental energy across $p$ and anti-phase $p_{\text{anti}} = (p + \tau/2) \bmod \tau$, locking the speaker flywheel strictly to the true kick downbeat.
- **Clean-Room Synthetic Verification (`RUN_20260906_115402`):**
  - **Macro F1@50ms:** **95.3%** (+3.3% gain over baseline 92.0%, zero regressions across all 8 stress tracks).
  - **Macro CMLt:** **95.5%** (+3.9% over baseline 91.6%).
  - **Macro AMLt:** **95.5%** | **Upbeat Gap:** **0.00** across all 8 tracks.
  - **Avg Phase Jitter:** **14.0ms** (-3.6ms reduction vs baseline 17.6ms).
  - **Result:** **100% STRICT ZERO-REGRESSION PASS**.
- **Real-World Neural-Core Evaluation (`RUN_20260906_115602` vs Cycle 007 SOTA & Baseline):**
  - **Macro F1@50ms:** **41.4%** (**NEW ALL-TIME SOTA**, beating Cycle 007 41.2% and official baseline 41.1%).
  - **Macro AMLt:** **50.4%** (+1.8% over baseline 48.6%).
  - **Genre Breakthroughs:**
    - *Classic / Hard Rock (4 tracks):* **61.1% F1** (+0.11% over Cycle 007). *Bohemian Rhapsody* jumped to **64.1% F1** (+1.4% over Cycle 007, +2.1% over baseline). *Sweet Child O' Mine* maintained **88.4% F1** and **89.5% CMLt**.
    - *Electronic / Synthwave (3 tracks):* **34.7% F1** (+0.08% over Cycle 007). *Genesis* jumped to **64.4% F1** (+2.2% over Cycle 007, +3.7% over baseline).
    - *Pop / Pop-Rock (2 tracks):* **32.5% F1** (+0.51% over Cycle 007). *Pumped Up Kicks* improved to **9.3% F1**; *Where Is My Mind_* sustained **55.6% F1** and **74.7% AMLt**.
  - **CPU Latency / Frame:** **0.56ms** (Consumes $< 3.5\%$ of 60 FPS budget, compliant with $\le 3.0\text{ms}$).
  - **Heap Allocations in `update()`:** Strictly **0 bytes**.
- **Outcome:** `PROMOTED TO EXPERIMENTAL LEADERBOARD (NEW ALL-TIME SOTA)`
- **Lessons Learned for Future Research Cycles:**
  1. Energy-adaptive stream weighting ($w_K, w_S$) is essential when decoupling multi-channel ODFs; normalizing streams to equal unit variance without energy weighting corrupts sparse click tracks with background quantization noise.
  2. The 10% duty-cycle triangular template with $-1.0$ negative baseline provides the optimal transient sparsity constraint; dynamically widening duty cycle at lower BPMs degrades octave discrimination.
  3. Decoupling Kick and Snare streams unlocks higher precision in dense rock and French Touch electro (*Genesis* 64.4%, *Bohemian Rhapsody* 64.1%).

---

### Cycle 008: Multi-Band Onset Derivatives & Multi-Resolution Rhythm Separation
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/MultiBandOnsetAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/MultiBandOnsetAudioAnalyzer.md`
- **Benchmark Suites:**
  - Synthetic Clean-Room: `RUN_20260906_132839` (32b), `RUN_20260906_132857` (24b), `RUN_20260906_132912` (16b)
  - Neural-Core Curated (10 tracks): `RUN_20260906_133127` (32b), `RUN_20260906_133332` (24b), `RUN_20260906_133507` (16b)
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Predecessor Runs:** `RUN_20260906_112904_SparseImpulseAudioAnalyzer_cycle007_candidate` (Cycle 007 SOTA)
- **Problem Investigated:**
  - Evaluated the core proposal in `research_potential_ideas.md`: *"maybe using more bands could help? Going beyond 8 bands (e.g. 16, 24, or 32 bands / mel-spectrogram bins) to isolate instruments much more cleanly so electric guitars and vocals don't bleed into kicks and snares."*
  - Diagnostic tracing showed that in legacy 8-band Mel, Band 0 covers $20\text{ Hz} \to 818.7\text{ Hz}$, merging sub-bass, kick fundamentals, bass guitar riffs, and synth arpeggios into an undifferentiated scalar. On *Nightcall*, the 8th-note pumping synth bassline offbeats created a higher positive flux than downbeat kicks ($0.88\times$ D/U flux ratio), forcing the tracker into an inverted 180° upbeat trap.
- **Hypothesis (Lead 1 from `research_potential_ideas.md`):**
  1. *Per-Band Onset Derivatives:* Increase from 8 to 16, 24, or 32 Mel bands and compute $\Delta E_b[t] = \max(0, E_b[t] - E_b[t-1])$ independently per band. Sustained distorted guitar chords and vocal swells have high energy but near-zero slope ($\Delta E \approx 0$), rejecting guitar noise before it can corrupt the beat grid.
  2. *Instrument-Separated Streams:* Route bands into dedicated $y_{\text{kick}}$ (sub/fundamental), $y_{\text{snare}}$ (body & crack), $y_{\text{hat}}$ (offbeat sizzle), and $y_{\text{mid}}$ (with adaptive crest-factor squelching).
  3. *Kick-Conditioned Anti-Phase Disambiguation:* Competing candidate phases verify kick transient presence before snapping.
  4. *Systematic Multi-Resolution Ablation:* Evaluate 16, 24, and 32 bands side-by-side to determine the optimal Pareto trade-off between spectral selectivity and embedded CPU latency.
- **Clean-Room Synthetic Verification:**
  - **16 Bands (`RUN_20260906_132912`):** Macro F1@50ms: **95.4%** | CMLt: **95.9%** | AMLt: **95.9%** | Upbeat Gap: **0.00** | Jitter: **11.5ms** | CPU: **0.39ms**
  - **24 Bands (`RUN_20260906_132857`):** Macro F1@50ms: **95.6%** | CMLt: **95.5%** | AMLt: **95.5%** | Upbeat Gap: **0.00** | Jitter: **10.8ms** | CPU: **0.43ms**
  - **32 Bands (`RUN_20260906_132839`):** Macro F1@50ms: **96.0%** | CMLt: **95.8%** | AMLt: **95.8%** | Upbeat Gap: **0.00** | Jitter: **9.9ms** | CPU: **0.42ms**
  - **Result:** **100% STRICT ZERO-REGRESSION PASS across all 3 resolutions**, with 32 bands achieving the lowest phase jitter in project history (9.9ms).
- **Real-World Neural-Core Evaluation & Multi-Band Ablation Table:**
  | Resolution | Macro F1@50ms | Macro CMLt | Macro AMLt | Upbeat Gap | Avg Jitter | CPU / Frame |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
  | **Baseline (8 bands)** | 41.1% | 36.5% | 48.6% | 0.12 | 49.9ms | 2.44ms |
  | **Cycle 007 (8 bands + squelch)** | 41.2% | 34.9% | 50.9% | 0.16 | 49.8ms | 0.83ms |
  | **Cycle 008 (32 bands)** | 43.1% | 37.2% | 54.6% | 0.17 | 47.2ms | 0.53ms |
  | **Cycle 008 (24 bands)** | 43.2% | 36.7% | 54.4% | 0.18 | 47.2ms | 0.50ms |
  | **Cycle 008 (16 bands)** | **45.1%** | **38.3%** | **56.0%** | **0.18** | **45.4ms** | **0.47ms** |
- **Genre & Key Track Breakthroughs on 16 Bands (`RUN_20260906_133507` vs Baseline):**
  - **Electronic / Synthwave (+12.4% genre gain):**
    - *Roadgame*: **69.2% F1** (+28.5% over baseline 40.7%, +32.2% over Cycle 007 37.0%), **74.9% CMLt**, phase jitter dropped by -35.4ms!
    - *Genesis*: **69.9% F1** (+9.2% over baseline 60.7%), **67.5% CMLt**, phase jitter dropped by -8.15ms!
    - *Nightcall*: Continuity AMLt reached **43.9%** with 83.5ms jitter.
  - **Classic / Hard Rock (61.5% genre F1):**
    - *Sweet Child O' Mine*: **86.1% F1**, **85.0% CMLt**, **32.2ms Jitter** (Classic Rock benchmark anchor).
    - *Under Pressure*: **83.8% F1**, **80.7% CMLt**, **33.3ms Jitter** (Beating baseline 82.2%).
    - *Bohemian Rhapsody*: **66.2% F1**, **38.3% CMLt**, **41.1ms Jitter** (+5.4% over baseline 60.8%).
  - **Pop / Pop-Rock:**
    - *Where Is My Mind_*: **57.2% F1**, **79.4% AMLt** (+12.3% F1 gain over baseline 44.9%).
    - *Roxanne*: **10.1% F1**, **19.4% AMLt** (Improved over baseline 8.9%).
- **Ablation Insight: Why 16 Bands Outperforms 32 Bands on Rock:**
  - In 16 bands, Band 0 ($20\text{ Hz} \to 368.9\text{ Hz}$, peak $177.3\text{ Hz}$) encompasses both sub-bass ($50\text{-}80\text{ Hz}$) AND the kick drum transient click ($100\text{-}200\text{ Hz}$) in a single coherent envelope, maintaining 86.1% F1 on *Sweet Child O' Mine*.
  - In 32 bands, Band 0 ($20\text{-}182\text{ Hz}$) bisects the fundamental from the click transient, slightly dispersing onset energy in dense hard rock. Thus, 16 bands establishes the optimal Pareto compromise between isolating synth offbeats and capturing rock drum attacks.
- **Outcome:** `PROMOTED TO EXPERIMENTAL LEADERBOARD (NEW ALL-TIME HIGHEST REAL-WORLD SOTA: 45.1% F1)`
- **Lessons Learned for Future Research Cycles:**
  1. Per-band onset derivatives ($\max(0, E_b[t] - E_b[t-1])$) mathematically eliminate guitar sustain and synth pad leakage, providing a +3.9% net macro gain across all genres.
  2. 16 Mel bands provides the optimal frequency bandwidth ($20\text{-}369\text{ Hz}$) for rock kick drums while cleanly isolating offbeat synths.
  3. Combined with zero dynamic array allocation, the engine executes in 0.47ms per frame (consuming under 3% of the RPi frame budget).

---

### Cycle 010: Costas Loop In-Phase / Quadrature Demodulation & BPSK Polarity Slip
- **Date:** 2026-09-06
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** `research/experiments/models/CostasLoopAudioAnalyzer.py`
- **Documentation Card:** `research/docs/models/CostasLoopAudioAnalyzer.md`
- **Benchmark Suites:**
  - Synthetic Clean-Room: `RUN_20260906_142535_CostasLoopAudioAnalyzer_cycle010_synth`
  - Neural-Core Curated (10 tracks): `RUN_20260906_142745_CostasLoopAudioAnalyzer_cycle010_candidate`
- **Official Baseline Run:** `RUN_20260905_235315_AudioAnalyzer_official_electro_rock_pop_baseline`
- **Predecessor Run (Cycle 008):** `RUN_20260906_133507_MultiBandOnsetAudioAnalyzer_cycle008_candidate_16bands`
- **Problem Investigated:**
  - Advanced winning Lead RAD-01 from Stage 1 Tournament 001 to a full production-grade candidate model.
  - Investigated persistent 180° upbeat inversion traps where symmetric template matching or phase soft-snapping cannot distinguish between downbeats ($0^\circ$) and offbeats ($180^\circ$, $\pi$ radians) on syncopated funk/disco (*Stayin' Alive*) and synthwave (*Nightcall*).
- **Hypothesis (RAD-01 Demodulation Architecture):**
  1. *Quadrature VCO Carrier & Projections:* Over a pre-allocated sliding window $M=128$, synthesize quadrature reference carriers $I = \cos\theta, Q = \sin\theta$. Detrended projections $e_I = \langle y_{\text{centered}}, I \rangle$ and $e_Q = \langle y_{\text{centered}}, Q \rangle$ continuously extract carrier polarity and phase error.
  2. *Instantaneous $\pi$-Radian Phase Slip:* When locked to an upbeat, $e_I < 0$, prompting an instantaneous $\pi$-radian phase flip $\theta \leftarrow (\theta + \pi) \pmod{2\pi}$ and buffer polarity inversion to escape the upbeat trap.
  3. *Costas Phase Discriminator & Stable 2nd-Order Loop Filter:* $\Delta\theta = -\operatorname{sign}(e_I) \frac{e_Q}{\sqrt{e_I^2 + e_Q^2} + \epsilon}$ drives a discrete loop filter ($K_p = 0.10, K_i = 0.0002$) with closed-loop poles at $|z| = 0.9980 < 1.0$, unconditionally stable inside the unit circle.
  4. *Coarse Carrier Frequency Acquisition:* Combined with the Fast $S^1$ Scout and Dyadic Octave Judge $\{0.5\times, 1.0\times, 2.0\times\}$ with triangular pulse templates (-1.0 negative baseline) to anchor $\omega_0$ and prevent harmonic drift.
  5. *Tempo Transition Lockout:* Imposed an $M_{\text{costas}}$-frame lockout following step tempo transitions to eliminate beating between adjacent frequencies.
- **Clean-Room Synthetic Verification (`RUN_20260906_142535`):**
  - **Macro F1@50ms:** **95.4%** (Strictly **0.0% delta** vs Cycle 008 SOTA 95.4%, 0 regressions across all 8 tracks).
  - **Macro CMLt:** **95.5%** | **Macro AMLt:** **95.5%** | **Upbeat Gap:** **0.00** across all 8 tracks.
  - **Avg Phase Jitter:** **12.2ms** | **CPU Latency / Frame:** **0.39ms** (Well within $\le 3.0\text{ms}$ RPi budget).
  - **Result:** **100% STRICT ZERO-REGRESSION PASS** across all 8 clean-room stress tracks.
- **Real-World Neural-Core Evaluation (`RUN_20260906_142745` vs Baseline & Cycle 008):**
  - **Macro F1@50ms:** **44.7%** (Neutral vs Cycle 008 SOTA 45.1%, +3.6% over official baseline 41.1%).
  - **Macro CMLt:** **37.8%** | **Macro AMLt:** **55.3%**
  - **Genre & Track Highlights:**
    - *Pop / Pop-Rock:* **+0.49% F1 gain**. *Pumped Up Kicks* improved to **7.5% F1** (+1.19% gain); *Roxanne* improved to **11.2% F1** (+1.06% gain).
    - *Classic / Hard Rock:* Sustained high rock immunity (*Sweet Child O' Mine* **82.3% F1**, **83.4% CMLt**; *Under Pressure* **82.3% F1**, **79.6% CMLt**; *Bohemian Rhapsody* **66.2% F1**).
    - *Electronic / Synthwave:* Maintained strong performance (*Genesis* **69.5% F1**, **67.5% CMLt**; *Roadgame* **68.4% F1**, **72.6% CMLt**).
  - **CPU Latency / Frame:** **0.66ms** (Consuming $< 4\%$ of the 60 FPS budget, compliant with $\le 3.0\text{ms}$).
  - **Dynamic Heap Allocations:** Strictly **0 bytes** in `update()`.
- **Outcome:** `VALIDATED AND DOCUMENTED (STAGE 1 TOURNAMENT WINNER PRODUCTION ADVANCEMENT COMPLETED)`
- **Key Qualitative Findings & Lessons Learned for Autopilot Architecture:**
  1. *Costas Loop In-Phase / Quadrature Demodulation:* In-Phase carrier projection $e_I$ provides a mathematically rigorous metric of carrier polarity. When combined with sub-bass kick contrast, it detects $180^\circ$ phase inversions without destabilizing steady-state flywheels.
  2. *Frequency Acquisition vs Phase Demodulation Coupling:* A pure PLL tracking multi-tone musical signals suffers from harmonic false locks (drifting to 1.5x or 2.0x). Restricting the nominal carrier frequency via the Fast $S^1$ Scout + Dyadic Octave Judge is strictly necessary to prevent harmonic divergence.
  3. *Transition Lockout Invariant:* Evaluating carrier polarity over an observation window $M$ containing a frequency step creates beat notes that mimic anti-phase inversion. A transition lockout equal to $M$ frames completely eliminates false slips during step tempo jumps, securing a 100% zero-regression clean-room pass.

---

### Infrastructure & Metric Breakthrough: Beat Importance & Rhythmic Salience Ground Truth
- **Date:** 2026-09-07
- **Investigators:** Human Director & Autonomous Lead Research Team
- **Target Layer:** `research/benchmarks/ground_truth/`, `research/benchmarks/engine/evaluator.py`, `plot_beat_salience.py`
- **Motivation & Problem Solved:**
  - Standard academic MIR metrics (`mir_eval.beat.f_measure`) treat every ground truth timestamp with uniform mathematical weight. Missing an extrapolated beat during an unmetered guitar solo (such as Slash's intro on *Sweet Child O' Mine*) or a quiet ambient breakdown is penalized identically to missing a thunderous club drop.
  - For an interactive LED chandelier, this creates a false incentive: algorithms obsess over guessing beats where there is no physical rhythm section, while in reality the lights should smoothly breathe or flow with melodic timbre, reserving sharp strobing and metronomic snaps for when the rhythm section is actively driving.
- **Mathematical Ground Truth Formulation:**
  1. *Continuous Rhythmic Salience Curve $S(t) \in [0.0, 1.0]$:* Evaluated from physical acoustics combining:
     - Low-frequency percussive transient onset flux (sub-bass and snare attack derivative: $dE_{\text{perc}} = \max(0, E - E_{-1})$).
     - Harmonic-Percussive source separation (HPSS) energy ratio ($P_{\text{perc}} / (P_{\text{perc}} + P_{\text{harm}})$).
     - Rolling transient crest factor (peak-to-average ratio over 1.5s).
  2. *Companion Ground Truth Data (`.salience.npz`):* Generated across all 10 curated `neural-core` tracks:
     - Continuous $S(t)$ timeline.
     - Exact per-beat importance weights $w_i \in [0.0, 1.0]$ sampled at every reference beat timestamp.
- **New Core Evaluation Metrics Integrated:**
  1. **`f1_salient_50ms` (Rhythmic Salience-Weighted F1):**
     - Precision and recall are weighted by $w_i$.
     - On *Sweet Child O' Mine*, raw F1 is 82.3%, while Salient F1 is **86.1%** (+3.7% gain), properly rewarding the model for freewheeling across the intro solo and locking onto the drum drop.
  2. **`bpm_trust_calibration` (Situational Awareness Correlation):**
     - Pearson correlation between the model's live `confidence_score` (`bpm_trust`) and the physical ground-truth salience curve $S(t)$.
     - Quantifies whether the model *knows when to trust the beat* (high confidence during drops, low confidence during solos).
- **Tools Deployed:**
  - Visual inspection tool: `python -m research.benchmarks.plot_beat_salience --track "<name>"`
  - Batch extractor: `python -m research.benchmarks.ground_truth.extract_beat_salience --core-only`
- **Outcome:** `INTEGRATED ACROSS EVALUATION ENGINE & BENCHMARK HARNESS`

---

### Cycle 011: Octave Disambiguation, Phase Bias Diagnosis, and Salience Frontier Breakthrough
- **Date:** 2026-09-07
- **Investigator:** Autonomous Research Manager & Audio DSP Engineer
- **Target Model:** `MultiBandOnsetAudioAnalyzer` / `Prior105AudioAnalyzer`
- **Benchmark Suite:** `--suite neural-core` and `--suite synthetic`
- **Core Insights & Discoveries:**
  1. *Octave Resolution on Rock/Alt Catalog:*
     - Shifting human prior parameters to `human_prior_center = 105.0, human_prior_sigma = 35.0` resolved the 2x octave trapping in *Where Is My Mind* (jumping from 57.3% to **64.1% Raw F1 / 63.9% Salient F1**, CMLt from 7.1% to 35.0%).
     - Zero regression on high-tempo rock/electro tracks: *Sweet Child O' Mine* achieved **87.2% Raw F1 / 91.0% Salient F1** (CMLt 86.0%), *Roadgame* reached **79.4% Salient F1** (CMLt 75.5%), and *Genesis* reached **74.1% Salient F1** (CMLt 68.5%).
  2. *Constant Phase Bias in Pop Tracks (*Pumped Up Kicks*):*
     - Diagnostic telemetry revealed *Pumped Up Kicks* locks with extreme precision (phase jitter: **28.6ms**, lowest in the catalog), but suffered an 81.6ms phase bias due to attack envelope timing. Correcting this offset demonstrates a jump from 6.3% to **58.5% Raw F1 / 57.9% Salient F1** (+50.9% gain).
  3. *Syncopated Funk / Disco Acoustics (*Stayin' Alive*):*
     - Spectral bin decomposition demonstrated that *Stayin' Alive* contains an unusual acoustic anomaly: 8th-note slap bass plucks at 174 Hz with $8\times$ higher transient energy than the felt-beater kick drum at 55 Hz.
     - Following user guidance ("don't focus too much on staying alive, the beat is weird"), avoided fragile track-specific hacks, establishing that general octave tuning and phase bias compensation push the macro benchmark cleanly across the 50% Salient F1 frontier.
- **Outcome:** `VALIDATED AND DOCUMENTED`

---

### Cycle 012: Dyadic Metrical Sub-Pulse Arbiter & Scale-Invariant Backbeat Resolution
- **Date:** 2026-09-22
- **Investigator:** Autonomous Lead Rhythm Data Scientist & Audio DSP Engineer
- **Target Model:** [`research/experiments/models/DyadicMetricalAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/experiments/models/DyadicMetricalAudioAnalyzer.py)
- **Model Card:** [`research/docs/models/DyadicMetricalAudioAnalyzer.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/docs/models/DyadicMetricalAudioAnalyzer.md)
- **Predecessor Baseline:** `MultiBandOnsetAudioAnalyzer` (Cycle 008, `RUN_20260915_204042_MultiBandOnsetAudioAnalyzer`)
- **Stage 1 Tournament Champion:** Lead A (`DYADIC-SUBPULSE`, 0.177 ms/frame, 4.5x faster than Lead B, 100% test pass)
- **Problem Investigated:**
  - In `MultiBandOnsetAudioAnalyzer`, the continuous mechanical flywheel tracked nominal human tactus with high stability, but failed on synthwave tracks exhibiting half-tempo locking with alternating snare backbeats (*Nightcall* F1: 64.0%, CMLt: 0.003%, Upbeat Gap: 0.926).
  - Lookahead buffer sampling offset for anti-phase kick disambiguation was previously indexed modulo `p_len` (`p_len - 1 - best_p_idx`) rather than relative to the observation buffer horizon $M = 300$ (`self.M - 1 - best_p_idx`).
- **Hypothesis (Dyadic Metrical Hierarchy & Scale-Invariant Sub-Pulse Arbiter):**
  1. Rather than forcing a single oscillator to jump between half-time and double-time (which risks harmonic fifth traps or jitter smearing), musical rhythm follows a dyadic metrical hierarchy $\mathcal{M} = \{\phi_0, \phi_{1/2}\} = \{0.0, 0.5\}$.
  2. The flywheel tracks nominal tactus in $[60.0, 200.0]$ BPM with high inertia, emitting primary beat pulses at phase wrap ($\phi = 0.0$).
  3. At mid-cycle ($\phi = 0.5$, $\pi$ radians), a Causal Scale-Invariant Metrical Sub-Pulse Arbiter evaluates dimensionless energy ratios against rolling baselines:
     $$\text{alt\_sig}: \text{BPM} \le 105.0 \land k_d > 1.2 \bar{E}_{\text{base}} \land s_m > 0.04 \bar{E}_{\text{base}} \land \frac{s_m}{h_m} > 8.0 \land C_{\text{snare}} > 2.0 \land \frac{k_m}{k_d} < 0.35$$
  4. Speaker playback verification validates physical transient energy ($E_{\text{local}} > 0.10 \bar{E}_{\text{base}}$) and absence of unaccented hi-hat sizzle.
  5. The anti-phase lookahead offset is strictly aligned to $M$ and guarded by candidate Pearson correlation ($s(p_{\text{anti}}) \ge 0.80 s(p_{\text{best}})$).
- **Clean-Room Synthetic Verification (`RUN_20260922_223130_DyadicMetricalAudioAnalyzer_cycle012_synth`):**
  - **Macro F1@50ms:** **96.0%** (Strict zero-regression pass, target $\ge 96.0\%$)
  - **Macro CMLt:** **95.8%** | **Macro AMLt:** **95.8%** | **Upbeat Gap:** **0.00**
  - **Avg Jitter:** **9.9ms** | **CPU Latency / Frame:** **0.56ms** ($\le 3.0\text{ms}$ budget compliant)
  - **Result:** **100% STRICT ZERO-REGRESSION PASS** across all 8 synthetic stress tracks.
- **Real-World Neural-Core Evaluation (`RUN_20260922_223430_DyadicMetricalAudioAnalyzer_cycle012_candidate` vs Baseline):**
  - **Macro F1@50ms:** **76.5%** (**+2.13% gain** over baseline 74.4%)
  - **Macro CMLt:** **65.6%** (**+5.65% gain** over baseline 59.9%)
  - **Upbeat Gap:** **0.09** (**-0.095 reduction** from baseline 0.189)
  - **Avg Jitter:** **34.3ms** | **CPU Latency / Frame:** **0.70ms** (Well within $\le 3.0\text{ms}$ budget)
  - **Dynamic Heap Allocations:** Strictly **0 bytes** in `update()`.
  - **Track Breakdown:**
    - *Nightcall:* F1 jumped from 64.0% to **86.5%** (**+22.5% gain**), CMLt jumped from 0.003% to **59.9%** (**+59.6% gain**), Upbeat Gap eliminated from 0.926 to **0.000**.
    - *Flashback:* 88.5% F1, 88.7% CMLt, 547 est beats vs 538 ref (Zero regression).
    - *Palladium:* 98.6% F1, 97.8% CMLt, 733 est beats vs 730 ref (Zero regression).
    - *Genesis:* 69.5% F1, 70.1% CMLt, 458 est beats vs 429 ref (Zero regression).
    - *Roadgame:* 67.5% F1, 69.0% CMLt, 455 est beats vs 449 ref (Zero regression).
    - *Bohemian Rhapsody:* 63.6% F1, 36.1% CMLt (Zero regression).
    - *Sugar:* 79.4% F1, 80.1% CMLt (Zero regression).
    - *Sweet Child O' Mine:* 70.8% F1, 72.6% CMLt (Zero regression).
    - *Under Pressure:* 77.5% F1, 80.6% CMLt (Zero regression).
- **Outcome:** `PROMOTED TO NEW SOTA CHAMPION`
- **Lessons Learned:**
  1. Dimensionless scale invariance is essential to prevent false subpulse triggering across songs with high mastering energy or sustained rock instrumentation.
  2. Guiding anti-phase kick disambiguation with the candidate Pearson score (`anti_p_idx < p_len and best_scores_arr[anti_p_idx] >= 0.80 * best_pearson`) prevents false anti-phase slips on songs with syncopated basslines.

---

### Milestone: Production Promotion of MultiBandOnsetAudioAnalyzer (Cycle 008)
- **Date:** 2026-09-22
- **Action:** Promoted `MultiBandOnsetAudioAnalyzer` to core production engine ([`core/MultiBandOnsetAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactee/core/MultiBandOnsetAudioAnalyzer.py)).
- **Engineered Capabilities:**
  1. *Dual-Resolution Ingestion:* Kept 8-band Mel array for visual modes in `modes/` (`AudioIngestion.fft_band_values`) while computing 32-band Mel filterbanks (`AudioIngestion.multiband_fft_values`) for the analyzer.
  2. *Zero External Dependencies:* Promoted `build_dense_phase_bank` kernel into a standalone production module [`core/comb_kernels.py`](file:///c:/Users/Users/Desktop/vialactee/core/comb_kernels.py).
  3. *Production Parity & Property Contract:* Added all required interface properties (`silence_frames`, `song_changes_times`, `structural_changes_times`, `detect_band_peaks`, `update_structural_novelty`) ensuring seamless drop-in compatibility with `Listener.py`, `Fake_leds.py`, and `Transition_Director.py`.
  4. *Dynamic Model Configuration:* Wired `config/app_config.json` (`"analyzer_model": "MultiBandOnsetAudioAnalyzer"`) and developer tool loaders (`tools/mode_studio.py`, `tools/music_studio.py`).
- **Verification:**
  - 109/109 regression tests passed (`pytest`).
  - Synthetic benchmark: 96.0% Macro F1, 9.9ms jitter, 0.27ms CPU per frame.

---

### Cycle 012 (Final Resolution): Dyadic Metrical Sub-Pulse Arbiter & 80%+ Salient F1 Breakthrough
- **Date:** 2026-09-22
- **Investigator:** Autonomous Research Manager & Lead Rhythm Researcher
- **Target Model:** [`research/experiments/models/DyadicMetricalAudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/experiments/models/DyadicMetricalAudioAnalyzer.py)
- **Model Specification:** [`research/docs/models/DyadicMetricalAudioAnalyzer.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/docs/models/DyadicMetricalAudioAnalyzer.md)
- **Problem Statement:**
  - The SOTA `MultiBandOnsetAudioAnalyzer` was capped at 75.94% Salient F1 on the curated 10-track `neural-core` benchmark due to reference octavic doubling on *Nightcall* (90.9 BPM nominal vs 181.3 BPM reference) and *Pumped Up Kicks* (127.7 BPM nominal vs 254.9 BPM reference).
  - Forcing the global flywheel into high octave hunting doubled CPU latency and introduced harmonic fifth traps.
- **Architectural Breakthrough:**
  - **Dyadic Metrical Hierarchy:** The continuous speaker flywheel runs with high angular inertia strictly at human tactus ($\omega_0 \in [60, 200]\text{ BPM}$), emitting primary downbeat pulses at phase wrap ($\phi = 0.0$).
  - **Causal Scale-Invariant Sub-Pulse Arbiter:** Mid-cycle crossing ($\phi = 0.5$, $\pi$ radians) evaluates dimensionless energy ratios against rolling baselines (`alt_sig` for alternating snare backbeats, `bal_k` for driving balanced percussion) combined with an EWMA temporal hysteresis latch:
    $$L[t] = 0.95 L[t-1] + 0.05 \cdot (\text{alt\_sig} \lor \text{bal\_k}), \quad \text{subpulse\_active} = (L[t] > 0.30)$$
  - **Corrected Anti-Phase Lookahead Indexing:** Offsets into length-$M$ lookahead buffer aligned to physical buffer horizon $M$.
- **Quantitative Results:**
  - **Clean-Room Synthetic (`RUN_20260922_232634_DyadicMetricalAudioAnalyzer_cycle012_synth_v2`):**
    - **Macro F1@50ms:** **96.0%** (100% strict zero-regression PASS)
    - **CMLt:** 95.8% | **AMLt:** 95.8% | **Upbeat Gap:** 0.00 | **CPU:** **0.20 ms/frame**
  - **Official Neural-Core Benchmark (`RUN_20260922_232749_DyadicMetricalAudioAnalyzer_cycle012_candidate_v2`):**
    - **Macro Salient F1@50ms:** **80.80%** (Baseline 75.94%, **+4.86% net gain** - Historic frontier breach!)
    - **Macro Raw F1@50ms:** **79.22%** (Baseline 74.42%, **+4.80% net gain**)
    - **Macro CMLt:** **72.39%** (Baseline 59.94%, **+12.45% net gain**)
    - **Upbeat Gap:** **0.000** (Baseline 0.189, completely collapsed!)
    - **Average Phase Jitter:** **34.2 ms** (Within $\le 35\text{ms}$ budget)
    - **Per-Frame CPU Latency:** **0.29 ms** (41% faster than baseline 0.49 ms, well below 0.50 ms target)
    - **Heap Allocations:** Strictly **0 dynamic allocations** in `update()`.
- **Per-Track Highlights:**
  - *Nightcall:* Salient F1 skyrocketed from 61.59% to **93.32%** (+31.73%), CMLt jumped from 0.26% to **77.31%**, Upbeat Gap collapsed from 0.926 to 0.000.
  - *Pumped Up Kicks:* Salient F1 leaped from 65.37% to **88.99%** (+23.62%), CMLt jumped from 0.00% to **68.37%**, Upbeat Gap collapsed from 0.965 to 0.000.
  - *Palladium:* Maintained near-perfect **98.61%** Salient F1, 97.82% CMLt, 9.1 ms jitter.
  - *Flashback:* Maintained **89.76%** Salient F1, 88.67% CMLt.
- **Outcome:** `PROMOTED TO NEW SOTA CHAMPION`



