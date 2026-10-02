# Unified 3-Tier Musical Context Engine Architecture

> **Location:** `docs/architecture/musical_context_engine.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`core/MusicalContextEngine.py`](../../core/MusicalContextEngine.py), [`core/Listener.py`](../../core/Listener.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md), [AXIOM-07](../axioms/AXIOM-07_CODE_GOVERNANCE.md)

---

## 1. Executive Summary & Architectural Overview

The **Unified 3-Tier Musical Context Engine** replaces fragmented, ad-hoc DSP threshold checks in modes with a structured, hierarchical representation of real-time musical intent. Residing inside [`core/MusicalContextEngine.py`](../../core/MusicalContextEngine.py) and exposed directly via `self.listener.context`, it provides a rock-solid, multi-signal semantic layer partitioned into three distinct abstraction tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TIER 1: CONTINUOUS DYNAMIC KINETICS                  │
│       Continuous floating-point visual modulation vectors [0.0, 1.0]   │
│  • energy          • tension          • drop_progress                  │
│  • spectral_tilt   • vertical_center  • salience/power gradients       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       TIER 2: THE 4 MACRO SCENES                       │
│        Mutually exclusive macro states with Schmitt & dwell locks      │
│  1. CHILL          2. GROOVE          3. BUILDUP       4. DROP_IMPACT  │
│  • scene_blend: Smooth 0.0 -> 1.0 crossfade (0.5s transition time)    │
│  • scene_dwell_time: Minimum 1.0s dwell lock on steady states          │
│  • DROP_IMPACT: Dedicated 1.5s post-drop shockwave dwell scene         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    TIER 3: MICRO PHYSICAL BADGES                       │
│             Deterministic boolean tags for localized triggers          │
│  • is_locked       • is_syncopated    • is_real_beat   • is_silent     │
│  • is_drop_impact  • is_drop_imminent • is_structural_cut             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline & Signal Ingestion

```
                      INCOMING AUDIO STREAM
                                │
                                ▼
                 ┌──────────────────────────────┐
                 │    MultiBandOnsetAnalyzer    │ ◄── Lookahead T_lookahead = T_spk + 5.0s
                 │   • live_rhythm_salience     │
                 │   • live_power / novelty     │
                 └──────────────┬───────────────┘
                                │
                                ▼
                 ┌──────────────────────────────┐
                 │       core/Listener.py       │ ◄── Speaker FIFO Ring Buffers
                 │   • rhythm_salience          │     (Speaker time T_speaker)
                 │   • beat_trust               │
                 │   • asserved_total_power     │
                 │   • asserved_fft_band        │
                 └──────────────┬───────────────┘
                                │
                                ▼
                 ┌──────────────────────────────┐
                 │     MusicalContextEngine     │ ◄── Evaluates 3 Tiers at 60 FPS
                 │   • Tier 1: Continuous Mod   │     Schmitt Triggers & Dwells
                 │   • Tier 2: 4 Macro Scenes   │     Zero Heap Allocation
                 │   • Tier 3: Micro Badges     │     <= 0.04 ms per frame
                 └──────────────┬───────────────┘
                                │
                                ▼
                 ┌──────────────────────────────┐
                 │   Visual Modes & Director    │ ◄── Consumes self.listener.context
                 │   • Declarative scene logic  │     Smooth crossfades & badges
                 └──────────────────────────────┘
```

---

## 3. Tier 1: Continuous Dynamic Kinetics (Floats)

Continuous kinetics eliminate manual normalization in modes, providing pre-fused, perceptual drive curves:

| Kinetic Property | Range | Mathematical Formulation & Musical Rationale |
| :--- | :--- | :--- |
| **`energy`** | $[0.0, 1.0]$ | Master visual drive: $\text{clamp}(0.50 \cdot P + 0.30 \cdot S + 0.20 \cdot (S \cdot T))$. Fuses acoustic volume, rhythmic presence, and metronomic confidence into a unified master brightness/speed parameter. |
| **`tension`** | $[0.0, 1.0]$ | Anticipation, buildup, and novelty curve: $\max(\text{drop\_progress}, \text{novelty}, 0.5 \cdot \max(\Delta R, \Delta P))$, peaking at $1.0$ on drop impact. Drives spatial contraction, chromatic warmth, and vibration. |
| **`drop_progress`** | $[0.0, 1.0]$ | Normalized countdown ramp: $1.0 - (T_{\text{countdown}} / T_{\text{duration}})$, peaking at $1.0$ at drop landing. Smoothly scales buildup intensity. |
| **`spectral_tilt`** | $[-1.0, 1.0]$ | Bass vs treble balance across 8 Mel bands: $(T - B) / (T + B)$. $-1.0 = \text{pure bass}$, $+1.0 = \text{pure treble}$, $0.0 = \text{balanced/silence}$. |
| **`vertical_center`** | $[0.0, 1.0]$ | Spectral center of gravity: $\sum_{i=0}^7 (i/7) \cdot b_i / \sum b_i$. $0.0 = \text{bottom strips (bass)}$, $1.0 = \text{top strips (treble)}$, $0.5 = \text{geometric center}$. |
| **`salience_gradient`** | $[-1.0, 1.0]$ | Differential rhythm influx: $\Delta R = S_{\text{live}} - S_{\text{speaker}}$. |
| **`power_gradient`** | $[-1.0, 1.0]$ | Differential power influx: $\Delta P = P_{\text{live}} - P_{\text{speaker}}$. |

---

## 4. Tier 2: The 4 Macro Scenes (`MusicalScene`)

Rather than maintaining ambiguous intermediate regimes, musical space is categorized into 4 canonical macro scenes:

```
                      BEAT TRUST (T)
                     Low (< 0.35)           High (>= 0.50)
                 ┌──────────────────────┬──────────────────────┐
   High          │                      │                      │
  (>= 0.45)      │   GROOVE (SYNCO)     │   GROOVE (LOCKED)    │
                 │                      │                      │
RHYTHM           ├──────────────────────┼──────────────────────┤
SALIENCE (S)     │                      │                      │
   Low           │        CHILL         │   GROOVE (PULSE)     │
  (< 0.35)       │  (Atmospheric/Rest)  │  (if P >= 0.35)      │
                 └──────────────────────┴──────────────────────┘

   MACRO EVENT SCENES:
   • BUILDUP     : Pre-drop tension ramp with armed countdown (ΔR >= 0.40 | ΔP >= 0.35 | silence cut)
   • DROP_IMPACT : Explosive 1.5s post-drop shockwave scene (entered upon drop land)
```

### Macro Scene Specification

1. **`MusicalScene.CHILL`** (`"CHILL"`):
   - **Signature:** Atmospheric drift, resting intro/outro, soft ambient pad textures, or silence ($P < 0.05$ or low $S, P$).
   - **Visual Direction:** Organic breathing, undulating slow color drift, zero strobing, relaxed dynamics.
2. **`MusicalScene.GROOVE`** (`"GROOVE"`):
   - **Signature:** Beat-driven section, steady rhythmic lock ($S \ge 0.45$ or $T \ge 0.50 \land P \ge 0.35$).
   - **Visual Direction:** Snappy rhythmic animations, locked geometric traveling waves, high-contrast pulses.
3. **`MusicalScene.BUILDUP`** (`"BUILDUP"`):
   - **Signature:** Pre-drop tension ramp armed by predictive lookahead ($\Delta R \ge 0.40 \lor \Delta P \ge 0.35 \lor \text{silence cut}$).
   - **Visual Direction:** Spatial contraction towards center, rising strobe speed, warm saturation shift, dramatic blackout on imminent landing.
4. **`MusicalScene.DROP_IMPACT`** (`"DROP_IMPACT"`):
   - **Signature:** Explosive release shockwave on drop land. Entered when countdown $\le 0.001$s or upon post-silence acoustic surge ($P \ge 0.50$ or $S \ge 0.45$).
   - **Behavior:** Fires `is_drop_impact = True` for exactly 1 frame. Locks in `DROP_IMPACT` for $1.5\text{s}$ minimum dwell before transitioning to `GROOVE` (or `CHILL` if $P < 0.20$).

### Transition Safeguards:
- **`scene_blend`:** Smooth $0.0 \to 1.0$ linear crossfade over `transition_time = 0.5s`.
- **`scene_dwell_time`:** Minimum dwell time of $1.0\text{s}$ protects `CHILL` $\leftrightarrow$ `GROOVE` steady transitions from perceptual fluttering.

---

## 5. Tier 3: Micro Physical Badges (Booleans)

Modes no longer need to parse raw thresholds; they simply inspect deterministic boolean badges:

| Badge Property | Boolean Condition & Physical Meaning | Mode Application |
| :--- | :--- | :--- |
| **`is_locked`** | $T \ge 0.50$ (release $< 0.35$, Schmitt trigger). High tempo confidence. | Engage beat-phase locked traveling waves. |
| **`is_syncopated`** | $S \ge 0.45 \land T < 0.35$. Energetic percussion without stable metric lock (drum fills, breakcore, polyrhythms). | Particle burst, aperiodic flashes, bypass strict beat phase. |
| **`is_real_beat`** | `is_beat == True` and $P \ge 0.20$. Physical confirmed acoustic transient. | Kick shockwave, bright bass hit flash. |
| **`is_silent`** | $P < 0.05$ (release $\ge 0.08$, Schmitt trigger). True acoustic silence. | Silence blackout or gentle resting glow. |
| **`is_drop_impact`** | High for **exactly 1 frame** on drop landing. | Full chandelier flash, blinding ripple expansion. |
| **`is_drop_imminent`**| Countdown $\le 0.40\text{s}$ in `BUILDUP`. | Pre-drop dramatic blackout or fast strobe freeze. |
| **`is_structural_cut`**| High for $1.2\text{s}$ dwell upon `is_song_change` or `is_verse_chorus_change`. | Macro sectional reset, dramatic palette change. |

---

## 6. Backward Compatibility Layer

To ensure seamless operation with legacy modes, visual tools, and tests, `core/MusicalContextEngine.py` provides an airtight compatibility facade:

- **Enum & String Compatibility:**
  `MusicalRegime = MusicalScene` is aliased. Legacy regime names are mapped directly to corresponding scenes:
  - `MusicalRegime.DEEP_AMBIENT` $\to$ `MusicalScene.CHILL`
  - `MusicalRegime.FLOATING_PULSE` $\to$ `MusicalScene.CHILL`
  - `MusicalRegime.THE_POCKET` $\to$ `MusicalScene.GROOVE`
  - `MusicalRegime.CHAOTIC_FILL` $\to$ `MusicalScene.GROOVE`
  - `MusicalRegime.PRE_DROP_BUILDUP` $\to$ `MusicalScene.BUILDUP`
  - `MusicalRegime.STRUCTURAL_CHANGE` $\to$ `MusicalScene.CHILL`
- **Equality Overrides:** Direct string equality `scene == "THE_POCKET"` or `scene == "DEEP_AMBIENT"` evaluates to `True`.
- **Legacy Properties:**
  - `current_regime` $\to$ `scene`
  - `previous_regime` $\to$ `previous_scene`
  - `regime_blend` $\to$ `scene_blend`
  - `regime_dwell_time` $\to$ `scene_dwell_time`
  - `is_ambient` $\to$ `scene == MusicalScene.CHILL`
  - `is_rhythmic` $\to$ `scene in (MusicalScene.GROOVE, MusicalScene.DROP_IMPACT)`
  - `is_in_pocket` $\to$ `scene == MusicalScene.GROOVE and is_locked`
  - `is_buildup` $\to$ `scene == MusicalScene.BUILDUP`
  - `is_structural_change` $\to$ `is_structural_cut`
- **Telemetry Snapshots:** `get_state_snapshot()` exports both the new 3-tier keys (`scene`, `is_locked`, `is_syncopated`, `is_real_beat`, `is_structural_cut`, etc.) and all legacy regime keys.

---

## 7. Performance & Axiom Guarantees

- **AXIOM-01 (Frame Budget):** Execution time $\le 0.04\text{ms}$ per frame (budget: $0.15\text{ms}$).
- **AXIOM-02 (Zero Dynamic Heap Allocations):** Pre-allocated scalar state variables, identity comparisons (`is`), module-level alias sets, zero tuple unpacking.
- **AXIOM-06 (Perceptual Rhythm Stability):** Dual-threshold Schmitt trigger deadbands and minimum dwell times prevent 60 FPS state chattering.
- **AXIOM-07 (Code Governance):** `core/MusicalContextEngine.py` strictly adheres to the 500-line cap (currently 477 lines).

---

## 8. Mode Authoring Pattern (Offer 4)

```python
def render(self, buffer=None, audio_ctx=None, frame_info=None):
    ctx = self.listener.context

    # 1. Micro Badges: One-frame drop impact shockwave
    if ctx.is_drop_impact:
        self.trigger_shockwave_blast()

    # Pre-drop dramatic blackout
    if ctx.is_drop_imminent:
        buffer.fill(0)
        return

    # Physical acoustic hit
    if ctx.is_real_beat:
        self.add_kick_ripple()

    # 2. Continuous Kinetics: Drive amplitude and geometry
    master_brightness = ctx.energy
    y_center = int(ctx.vertical_center * self.nb_leds)
    color_tilt = ctx.spectral_tilt  # Warm for bass, cool for treble

    # 3. Macro Scene Branching
    scene = ctx.scene
    blend = ctx.scene_blend

    if scene == MusicalScene.GROOVE:
        if ctx.is_syncopated:
            target_val = self.render_chaotic_syncopation(ctx.tension)
        else:
            target_val = self.render_locked_groove(self.listener.beat_phase) * master_brightness
    elif scene == MusicalScene.BUILDUP:
        target_val = ctx.tension * 255
    elif scene == MusicalScene.DROP_IMPACT:
        target_val = 255.0  # Climax release state
    else:  # MusicalScene.CHILL
        target_val = master_brightness * 0.4

    # Apply smooth scene crossfade
    if blend < 1.0:
        val = (1.0 - blend) * self._prev_val + blend * target_val
    else:
        val = target_val
    self._prev_val = val
```
