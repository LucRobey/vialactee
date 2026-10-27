# Unified 3-Tier Musical Context Engine Architecture

> **Location:** `docs/architecture/musical_context_engine.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`music/MusicalContextEngine.py`](../../music/MusicalContextEngine.py), [`music/Listener.py`](../../music/Listener.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md), [AXIOM-07](../axioms/AXIOM-07_CODE_GOVERNANCE.md)

---

## 1. Executive Summary & Architectural Overview

The **Unified 3-Tier Musical Context Engine** replaces fragmented, ad-hoc DSP threshold checks in modes with a structured, hierarchical representation of real-time musical intent. Residing inside [`music/MusicalContextEngine.py`](../../music/MusicalContextEngine.py) and exposed directly via `self.listener.context`, it provides a rock-solid, multi-signal semantic layer partitioned into three distinct abstraction tiers:

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
                 │       music/Listener.py       │ ◄── Speaker FIFO Ring Buffers
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

Deterministic boolean badges encapsulate threshold and Schmitt-trigger logic for downstream consumers (`mood/`, `transitions/`, and `Mode.py` helpers):

| Badge Property | Boolean Condition & Physical Meaning | Consumer & Mode Application |
| :--- | :--- | :--- |
| **`is_locked`** | $T \ge 0.50$ (release $< 0.35$, Schmitt trigger). High tempo confidence. | Cohort lottery in `transitions/`; concrete modes prefer continuous `self.rhythm_lock`. |
| **`is_syncopated`** | $S \ge 0.45 \land T < 0.35$. Energetic percussion without stable metric lock (drum fills, breakcore, polyrhythms). | Complexity DNA and cohort lottery in `transitions/`. |
| **`is_real_beat`** | `is_beat == True` and $P \ge 0.20$. Physical confirmed acoustic transient. | Gate hard kicks/sparks in modes (paired with `self.rhythm_lock` or `ctx.beat_trust`). |
| **`is_silent`** | $P < 0.05$ (release $\ge 0.08$, Schmitt trigger). True acoustic silence. | Silence fade-to-black in modes and `self.beat_pulse()`. |
| **`is_drop_impact`** | High for **exactly 1 frame** on drop landing. | Exposed to concrete modes via `self.drop_hit` (1-frame trigger) and `self.drop_decay` ($1.0 \to 0.0$ envelope). |
| **`is_drop_imminent`**| Countdown $\le 0.40\text{s}$ in `BUILDUP`. | Consumed by `transitions/` (`MusicSnapshot`); **never** used in concrete modes for pre-drop blackouts. |
| **`is_structural_cut`**| High for $1.2\text{s}$ dwell upon `is_song_change` or `is_verse_chorus_change`. | Telemetry and macro sectional tracking. |

---

## 6. Semantic Helpers & Snapshot

The legacy 6-regime compatibility layer (`MusicalRegime`, `current_regime`, `previous_regime`, `regime_blend`, `regime_dwell_time`, `is_structural_change`, the legacy regime names and the `STRUCTURAL_CHANGE` pseudo-scene) has been **removed**. `MusicalScene` is a plain `str` enum with exactly 4 members (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) and compares equal to its string value (`scene == "GROOVE"`). A sectional cut is reported only by the `is_structural_cut` badge; it never replaces the scene.

Convenience properties derived from the scene:
  - `is_ambient` $\to$ `scene == MusicalScene.CHILL`
  - `is_rhythmic` $\to$ `scene in (MusicalScene.GROOVE, MusicalScene.DROP_IMPACT)`
  - `is_in_pocket` $\to$ `scene == MusicalScene.GROOVE and is_locked`
  - `is_buildup` $\to$ `scene == MusicalScene.BUILDUP`

**Telemetry Snapshots:** `get_state_snapshot()` exports the 3-tier keys (`scene`, `previous_scene`, `scene_blend`, `scene_dwell_time`, `is_locked`, `is_syncopated`, `is_real_beat`, `is_structural_cut`, etc.) and the semantic helpers.

---

## 7. Performance & Axiom Guarantees

- **AXIOM-01 (Frame Budget):** Execution time $\le 0.04\text{ms}$ per frame (budget: $0.15\text{ms}$).
- **AXIOM-02 (Zero Dynamic Heap Allocations):** Pre-allocated scalar state variables, identity comparisons (`is`), module-level alias sets, zero tuple unpacking.
- **AXIOM-06 (Perceptual Rhythm Stability):** Dual-threshold Schmitt trigger deadbands and minimum dwell times prevent 60 FPS state chattering.
- **AXIOM-07 (Code Governance):** `music/MusicalContextEngine.py` strictly adheres to the 500-line cap (currently 477 lines).

---

## 8. Mode Consumption Pattern (Sanctioned Helpers & Subtle Mood Modifiers)

Concrete modes (`modes/*_mode.py`) **do not branch on `ctx.scene` or `ctx.is_drop_imminent`**, as heuristic scene classifications and pre-drop blackouts cause jarring visual snaps on false positives. Instead, `Mode_master` feeds `ctx.scene` into `mood.api.MoodService(auto_scene=True)`, which debounces (`0.30 s`) and cosine-smooths (`2.5 s`) scene transitions into four continuous modifiers bound on `Mode` (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`), while `Mode.py` provides bounded rhythm and drop helpers:

```python
def run(self) -> None:
    ctx = self.listener.context
    if ctx is not None and ctx.is_silent:
        self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
        return

    # 1. Confidence-blended beat envelope & continuous lock weight
    lock = self.rhythm_lock          # [0.0, 1.0]: trust * (0.4 + 0.6 * salience)
    pulse = self.beat_pulse(2.2)     # Punchy when locked, smooth breathing when lost

    # 2. One-frame drop trigger & smooth 1.5s post-drop decay envelope
    if (self.listener.is_beat and ctx.is_real_beat and lock > 0.35) or self.drop_hit:
        self.trigger_kick_ripple()
    boost = 1.0 + 0.35 * self.drop_decay

    # 3. Continuous kinetics + cosine-smoothed mood_* modifiers (no ctx.scene branching)
    drive = min(1.0, (0.55 * ctx.energy + 0.45 * pulse) * boost)
    speed = self.base_speed * (1.0 + lock * ((self.listener.bpm / 120.0) - 1.0)) * self.mood_pace * self.fps_ratio
    fade_ratio = self.base_fade / max(0.5, self.mood_trail)
```
