# Musical Context Engine Architecture

> **Location:** `docs/architecture/musical_context_engine.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`core/MusicalContextEngine.py`](../../core/MusicalContextEngine.py), [`core/Listener.py`](../../core/Listener.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md), [AXIOM-07](../axioms/AXIOM-07_CODE_GOVERNANCE.md)

---

## 1. Executive Summary & Problem Statement

Prior to the Musical Context Engine, each visual animation mode in `modes/` was forced to invent its own ad-hoc interpretation of raw DSP signals (`beat_confidence`, `asserved_total_power`, `is_beat`, `rhythm_salience`). This caused four critical systemic defects:

1. **Inconsistent Mode Logic:** One mode interpreted `confidence < 0.4` as ambient breathing, while another flashed continuously, causing discordant visual styles during transitions.
2. **Epileptic Flickering at Boundaries:** Raw DSP signals naturally fluctuate across consecutive frames. Without hysteresis, modes near detection thresholds rapidly flipped states at 60 FPS.
3. **Desynchronized Confidence Lead:** Pearson correlation was evaluated on the incoming lookahead stream ($T_{\text{lookahead}} = T_{\text{speaker}} + 5.0\text{s}$), causing confidence-based visual fades to occur 5 seconds before the actual musical transition hit the speakers.
4. **Code Duplication in Modes:** Every mode had to re-implement complex ADSR smoothing, thresholding, and drop detection.

The **Musical Context Engine** solves this by centralizing all high-level musical state classification into a single, high-performance, deterministic engine residing inside [`core/MusicalContextEngine.py`](../../core/MusicalContextEngine.py) and exposed via `self.listener.context`.

---

## 2. Architectural Pipeline & System Boundary

The Musical Context Engine acts as a semantic classification layer situated between the raw/delayed DSP facade (`Listener.py`) and visual consumers (`modes/*.py`, `Transition_Director.py`):

```
                        INCOMING AUDIO STREAM
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │    MultiBandOnsetAnalyzer    │ ◄── Evaluates at T_lookahead
                   │   • live_rhythm_salience     │     (Microphone = T_speaker + 5.0s)
                   │   • confidence_score         │
                   │   • Structural Novelty       │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │       core/Listener.py       │ ◄── 5.0s Circular Ring Buffers
                   │   • rhythm_salience          │     (Speaker time T_speaker)
                   │   • beat_trust               │
                   │   • asserved_total_power     │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │     MusicalContextEngine     │ ◄── Consumes delayed + live metrics
                   │   • 6 Canonical Regimes      │     Schmitt Triggers & Dwell Logic
                   │   • Anti-flicker Hysteresis  │     regime_blend in [0.0, 1.0]
                   │   • Pre-Drop Countdown       │     Execution time <= 0.01 ms
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │   Visual Modes & Director    │ ◄── Reads self.listener.context
                   │   • Declarative regime logic │     Zero per-mode ad-hoc math
                   └──────────────────────────────┘
```

---

## 3. The 6 Canonical Musical Regimes

The engine categorizes musical context into 6 distinct, mutually exclusive regimes:

```
                      BEAT TRUST (T)
                     Low (< 0.35)           High (>= 0.50)
                 ┌──────────────────────┬──────────────────────┐
   High          │                      │                      │
  (>= 0.45)      │     CHAOTIC_FILL     │      THE_POCKET      │
                 │                      │                      │
RHYTHM           ├──────────────────────┼──────────────────────┤
SALIENCE (S)     │                      │                      │
   Low           │     DEEP_AMBIENT     │    FLOATING_PULSE    │
  (< 0.35)       │                      │                      │
                 └──────────────────────┴──────────────────────┘

   TRANSITIONAL / MACRO OVERRIDES:
   • PRE_DROP_BUILDUP  : Triggered when salience gradient ΔR >= +0.40
   • STRUCTURAL_CHANGE : Triggered on is_song_change or is_verse_chorus_change
```

### Regime Specification

| Regime Enum | Primary Acoustic Signature | Visual Mode Objective |
| :--- | :--- | :--- |
| **`DEEP_AMBIENT`** | Low Salience ($S < 0.35$), Low Trust ($T < 0.35$). Atmospheric soundscapes, soft pad chords, rubato intros, speech, or silence. | Organic slow breathing, fluid color drift, zero metronomic strobing. Energy driven strictly by `asserved_total_power`. |
| **`FLOATING_PULSE`** | Low Salience ($S < 0.35$), High Trust ($T \ge 0.50$). Rhythmic metronomic presence without heavy percussion (e.g. gentle arpeggios, fingerpicked guitar, quiet sub-bass pulse). | Smooth, undulating traveling waves locked to `beat_phase`. Soft wave ripples without hard percussive flashes. |
| **`THE_POCKET`** | High Salience ($S \ge 0.45$), High Trust ($T \ge 0.50$). Full rhythm section locked in groove (techno drops, drum loops, funk basslines, driving rock). | Maximum rhythmic punch. Quantized geometric snaps, percussive flashes on `is_real_beat`, dynamic brightness contrast. |
| **`CHAOTIC_FILL`** | High Salience ($S \ge 0.45$), Low Trust ($T < 0.35$). Energetic acoustic transients without stable metronomic periodicity (drum fills, polyrhythms, jazz solos, glitch breaks). | Organic chaotic particle bursts, raw frequency-reactive flashes driven by `band_flux`, bypassing rigid `beat_phase`. |
| **`PRE_DROP_BUILDUP`** | Lookahead salience gradient $\Delta R \ge +0.40$. A rhythmic explosion has been ingested and will hit speakers in $T_{\text{countdown}}$ seconds. | Tension building. Spatial contraction, chromatic shift towards intense warm hues, rising strobe frequency, dramatic blackout pre-drop. |
| **`STRUCTURAL_CHANGE`** | Immediate song cut, major crossfade, or verse/chorus drop (`is_song_change` or `is_verse_chorus_change`). | Sectional visual reset, shockwave ring expansion, dramatic color palette shift, or momentary flash. |

---

## 4. Mathematical Mechanics & Stability Safeguards

### 4.1 Schmitt Trigger Hysteresis
To prevent 60 FPS oscillation near boundaries, the engine utilizes dual-threshold Schmitt triggers:

$$\text{Salience State} = \begin{cases} \text{HIGH} & \text{if } S \ge 0.45 \\ \text{LOW} & \text{if } S < 0.35 \\ \text{UNCHANGED} & \text{if } 0.35 \le S < 0.45 \end{cases}$$

$$\text{Trust State} = \begin{cases} \text{HIGH} & \text{if } T \ge 0.50 \\ \text{LOW} & \text{if } T < 0.35 \\ \text{UNCHANGED} & \text{if } 0.35 \le T < 0.50 \end{cases}$$

The deadbands ($0.35 \le S < 0.45$ and $0.35 \le T < 0.50$) guarantee that noise ripples cannot flip the classification.

### 4.2 Minimum Dwell Time
Once a steady-state regime is entered, the engine enforces a minimum dwell time:
$$\tau_{\text{dwell}} \ge 1.0\text{ s}$$
Steady-state regime transitions are locked out until $\tau_{\text{dwell}}$ expires, ensuring that visual modes sustain an aesthetic state long enough to register pleasantly with human perception.

### 4.3 Lookahead Salience Gradient & Drop Countdown
The engine exploits the lookahead horizon ($T_{\text{lookahead}} - T_{\text{speaker}} = 5.0\text{s}$) to detect upcoming drops:

$$\Delta R = R_{\text{live}} - R_{\text{speaker}}$$

When $\Delta R \ge 0.40$ and the current state is not already high-salience:
1. Engine enters `PRE_DROP_BUILDUP`.
2. Initial countdown is armed: $T_{\text{countdown}} = \text{lookahead\_seconds} \approx 5.0\text{s}$.
3. Each frame: $T_{\text{countdown}} \leftarrow \max(0.0, T_{\text{countdown}} - dt)$.
4. When $T_{\text{countdown}} \le 0.0$ or when speaker salience $S$ breaches high threshold ($S \ge 0.45$), the engine immediately transitions to the active steady target regime (`THE_POCKET` if $T \ge 0.50$ or `CHAOTIC_FILL` if $T < 0.35$).

### 4.4 Smooth Regime Crossfading (`regime_blend`)
Transitions between regimes must not create jarring visual discontinuities. The engine provides `regime_blend` $\in [0.0, 1.0]$:
- At transition onset: $\text{blend} = 0.0$, `previous_regime` is preserved.
- Over transition time $\tau_{\text{trans}} = 0.5\text{s}$:
  $$\text{blend} \leftarrow \min\left(1.0, \text{blend} + \frac{dt}{\tau_{\text{trans}}}\right)$$
Modes use `regime_blend` to linearly interpolate between regime visual parameters.

### 4.5 Acoustic Power & Spectral Novelty Tracking
In addition to rhythmic salience and beat trust, the engine ingests `asserved_total_power` and `asserved_novelty` from the analyzer facade, exposing them through `context.power` and `context.novelty`. These signals drive energy scaling in ambient regimes (`DEEP_AMBIENT`) and inform telemetry snapshots. Macro structural events (`is_song_change` or `is_verse_chorus_change`) immediately trigger `STRUCTURAL_CHANGE` and re-arm dwell timing on repeated events.

---

## 5. Performance & Axiomatic Compliance

- **AXIOM-01 (Frame Budget):** Execution time is $\le 0.01\text{ms}$ per frame (budget is $0.15\text{ms}$).
- **AXIOM-02 (Zero Dynamic Allocation):** Pre-allocated scalar state variables and singleton enum comparisons. Zero allocations during hot path `update()`.
- **AXIOM-07 (Code Governance):** `core/MusicalContextEngine.py` is strictly under the 500-line limit.

---

## 6. Mode Authoring Pattern

```python
def render(self, buffer=None, audio_ctx=None, frame_info=None):
    ctx = self.listener.context
    regime = ctx.current_regime
    blend = ctx.regime_blend

    if regime == MusicalRegime.THE_POCKET:
        # Full rhythm mode: sharp beat-phase strobe
        target_val = (1.0 - self.listener.beat_phase) ** 3.0
    elif regime == MusicalRegime.PRE_DROP_BUILDUP:
        # Anticipation: build tension as drop_countdown approaches 0
        target_val = (5.0 - ctx.drop_countdown) / 5.0
    elif regime == MusicalRegime.FLOATING_PULSE:
        # Soft undulating sine wave
        target_val = 0.5 * (1.0 + np.sin(2.0 * np.pi * self.listener.beat_phase))
    else: # DEEP_AMBIENT or CHAOTIC_FILL
        # Volume breathing
        target_val = self.listener.asserved_total_power

    # Apply regime crossfade if in transition
    if blend < 1.0:
        val = (1.0 - blend) * self._prev_val + blend * target_val
    else:
        val = target_val
    self._prev_val = val
```
