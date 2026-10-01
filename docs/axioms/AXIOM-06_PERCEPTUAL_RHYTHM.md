# AXIOM-06: Perceptual Invariance & Real-Beat Gating

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/test_modes_rhythm.py`, `modes/MODE_RULES.md`, `modes/`  

---

## 1. Specification

1. **Graceful Confidence Degradation:**
   Visual modes must never abruptly freeze, black out, or glitch when beat tracking confidence drops or when entering musical breakdowns/intros/outros.
   - When `listener.beat_confidence` is high ($\ge 0.6$): Modes animate with tight percussive beat reactivity and rhythmic subdivision punches.
   - When `listener.beat_confidence` degrades ($< 0.4$): Modes must smoothly crossfade into fluid, continuous breathing driven by total acoustic volume (`listener.instant_power` or smoothed FFT bands).
2. **Real-Beat Gating for High-Energy Visuals:**
   High-energy visual effects (e.g. `Hyper_strobe_mode`, sharp flashes, explosive boundary impacts in `Impact_shockwave_mode`) must be strictly gated using `listener.is_real_beat`.
   - `is_real_beat == True`: High-confidence physical acoustic energy transient verified at speaker time.
   - `is_real_beat == False` (coasting/ghost beat from the flywheel): Flashes, strobes, and violent transitions are strictly suppressed.
3. **Ghost Beat Freedom:**
   During ambient breakdowns or vocal solos with zero percussion, the Anticipation Flywheel may coast in freewheeling mode to track the internal tempo, but high-impact visual strobes must remain dormant until real percussive energy returns.

---

## 2. Invariant Rules for Modes

```python
# MANDATORY: Strobe gating rule
if listener.is_beat and listener.is_real_beat:
    self.trigger_high_energy_flash()
elif listener.beat_confidence < 0.4:
    self.render_acoustic_power_breathing(listener.instant_power)
```

---

## 3. Violation Conditions

- Firing white-out strobes or high-energy explosive transitions on phantom/freewheeling beats during acoustic silence.
- Binary behavior (jumping instantaneously between full-power flashing and pitch-black freeze).
- Ignoring `listener.beat_confidence` in tempo-reactive modes.
