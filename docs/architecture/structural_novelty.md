# Structural Novelty & Music Event Detection

> **Location:** `docs/architecture/structural_novelty.md` (Tier 1 Canonical Specification)  
> **Source Files:** [`core/StructuralNoveltyDetector.py`](../../core/StructuralNoveltyDetector.py), [`core/RhythmConfig.py`](../../core/RhythmConfig.py)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)

---

## 1. Overview

The `StructuralNoveltyDetector` module analyzes audio streams to understand musical macro-structures in real time. It autonomously identifies **Verse/Chorus transitions**, **Song Changes** (both sharp cuts and seamless DJ crossfades), and **Acoustic Silence Drops**.

It achieves this by continuously tracking the mathematical tension between Short-Term Memory (STM) and Long-Term Memory (LTM) across both **timbral texture** and **instantaneous power**.

---

## 2. Core Novelty Metrics

### Timbre Novelty
Calculated across the 8 Mel frequency bands (`AudioIngestion.band_proportion`):
- **STM (`stm_retention_base = 0.98`):** Represents immediate sonic texture (~0.5s half-life).
- **LTM (`ltm_retention_base = 0.9985`):** Represents recent baseline texture (~8.0s half-life).
- **Novelty:** Euclidean distance between normalized STM and LTM vectors.

### Power Novelty
Calculated from smoothed total volume (`AudioIngestion.smoothed_total_power`):
- Percentage difference between STM energy and LTM energy. Detects both sudden explosive energy bursts and dramatic breakdowns.

### Combined Novelty Function
$$\text{Novelty}_{\text{combined}} = \text{Novelty}_{\text{timbre}} + 0.20 \times \text{Novelty}_{\text{power}}$$

---

## 3. Dynamic Asserved Envelopes & Event Classification

To guarantee robust event detection across varying genres and production volumes without hardcoded thresholds, the engine normalizes the combined novelty inside **Local Max (LM)** and **Global Max (GM)** tracking envelopes:

1. **Verse / Chorus Boundary (`is_verse_chorus_change = True`):**
   - Fires when raw novelty punches vertically through the Global Max envelope ceiling.
   - Enforces a 20.0-second cooldown (`structural_cooldown_seconds`) to prevent rapid chatter during chaotic sections.
2. **Seamless DJ Crossfade (`is_song_change = True`):**
   - Fires when the normalized asserved novelty breaches `song_novelty_asserved_th` (0.80).
   - Multiplies Global Max by 1.5x (`gm_shock_multiplier`) to absorb subsequent drop shocks.
3. **Silence Drop (`is_song_change = True`):**
   - Fires when audio power remains below `silence_power_threshold` (5.0) for $> 1.5\text{ s}$.
   - Triggers ambient/chill preset selection and resets beat phase.
