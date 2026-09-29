# Visual Mode Authoring & Rhythm Integration Rules (`MODE_RULES.md`)

This document defines the core engineering, mathematical, and artistic rules for authoring visual animation modes in the Vialactée interactive chandelier.

It codifies how modes must consume rhythmic signals from the **Anticipation Flywheel**, how to handle situations when the beat engine is lost or uncertain, and how to maintain flawless 60 FPS performance on embedded hardware.

---

## 1. The Core Philosophy: "Graceful Degradation"

Interactive lighting has a golden rule: **The spectator must never see a broken rhythm.**
Human perception detects audio-visual desync in under 50 milliseconds. If the beat tracker is confused (e.g. during a chaotic guitar solo, ambient intro, or tempo shift) and the chandelier keeps strobing out of time, spectators instantly perceive it as a technical glitch.

### The Two Modes of Operation
Every rhythm-aware mode must support two complementary visual states:

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│       LOCKED STATE (High Trust)      │     │      ACOUSTIC / AMBIENT FALLBACK     │
│       confidence >= 0.65             │     │      confidence < 0.40               │
├──────────────────────────────────────┤     ├──────────────────────────────────────┤
│ • Sharp, punchy attack & decays      │     │ • Smooth, fluid volume breathing     │
│ • High dynamic contrast              │     │ • Ambient color drift                │
│ • Phase-locked geometric kinematics  │     │ • Direct reaction to physical power  │
│ • Crisp rhythmic pulses              │     │ • Relaxed organic wave motion        │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
                   ▲                                            ▲
                   └────────── BLENDED CONTINUOUSLY ────────────┘
                              via beat_confidence
```

When the analyzer is lost, the mode does **not** fail—it smoothly dissolves into an organic, ambient, or direct volume-reactive visual. To the spectator, it feels like an artistic choice matching the music's breakdown.

---

## 2. Rhythmic Signals: What to Trust & What to Avoid

### Signals You CAN Rely On:
| Property | Type | Description | Best Used For |
| :--- | :--- | :--- | :--- |
| `self.listener.beat_phase` | `float` | Continuous phase $\theta \in [0.0, 1.0)$ in speaker time ($0.0 = \text{strike}$). | Smooth ADSR decays, sine breathing, traveling wave positions. |
| `self.listener.bpm` | `float` | Current estimated tempo (e.g. `124.0`). | Scaling particle speeds, wave travel times, and physics constants. |
| `self.listener.is_beat` | `bool` | `True` for exactly 1 frame when a beat strikes speaker time. | 1-shot events (wave injection, projectile spawn, color step). |
| `self.listener.is_real_beat` | `bool` | `True` if the beat tick matches an actual physical acoustic transient. | **Gating hard flashes** and strobes (suppresses ghost hits). |
| `self.listener.is_dropped_beat`| `bool` | `True` when flywheel is coasting through silence or a drumless breakdown. | Softening flashes or rendering phantom ghost pulses. |
| `self.listener.beat_confidence`| `float` | Pearson correlation confidence score $[0.0, 1.0]$. | Blending factor between rhythmic and acoustic fallback states. |
| `self.listener.flywheel_status`| `str` | `'locked'` vs `'coasting'`. | High-level state switching. |

### Signals to AVOID For Now:
* **`self.listener.beat_count`**: **Do not rely on `beat_count % 2` or `beat_count % 4` for strict musical meter** (downbeat vs upbeat) at this stage. Skipped beats, ghost onsets, or breakdown coasting can invert parity, turning a kick flash into an upbeat flash. Treat every verified beat equally until measure tracking is stabilized.

---

## 3. The 4 Golden Rules of Rhythm-Reactive Modes

### Rule 1: Always Blend with Confidence (Continuous Fallback)
Never write binary logic that assumes the beat is always valid. Blend the rhythmic output with the acoustic fallback using `beat_confidence`:

```python
confidence = np.clip(self.listener.beat_confidence, 0.0, 1.0)

# 1. Rhythmic component: punchy decay locked to beat phase
rhythmic_energy = (1.0 - self.listener.beat_phase) ** 2.0

# 2. Acoustic fallback component: direct smoothed volume
acoustic_energy = self.listener.asserved_total_power

# 3. Dynamic blend: locks to beat when confident, falls back to volume when lost
effective_energy = (confidence * rhythmic_energy) + ((1.0 - confidence) * acoustic_energy)
```

### Rule 2: Gate Hard Flashes (`is_real_beat` Protection)
Violent, full-strip strobes and high-brightness flashes must **never** fire on phantom / coasting beats during silent breakdowns:

```python
# GOOD: Only flashes when a real physical transient landed at speaker time
if self.listener.is_beat and self.listener.is_real_beat and self.listener.beat_confidence > 0.5:
    self.trigger_flash()

# BAD: Flashes blindly even during silent pauses
if self.listener.is_beat:
    self.trigger_flash()
```

### Rule 3: Prefer Continuous Phase ($\theta$) Over 1-Frame Impulse Spikes
* **1-Frame Impulse Spikes (`is_beat`):** If a strobe triggers 50ms late due to phase jitter, the spectator notices instantly.
* **Continuous Phase Envelopes (`beat_phase`):** Phase is smooth and continuous. Even if the tempo estimate is drifting slightly, continuous motion or exponential decays look fluid and pleasing.

#### Common Phase Envelopes:
```python
phase = self.listener.beat_phase # [0.0, 1.0)

# Punchy Percussive Attack & Decay (Kick / Snare feel)
decay_envelope = (1.0 - phase) ** 2.5

# Harmonic Sine Breathing (Ambient / Downtempo feel)
sine_breathe = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase - (np.pi / 2.0)))

# Pre-Beat Inhale / Anticipation (Pulls inward right before phase reaches 1.0/0.0)
anticipation = np.maximum(0.0, (phase - 0.8) / 0.2) ** 2.0
```

### Rule 4: Scale Motion to Tempo (BPM-Aware Kinematics)
When moving pixels, balls, or wavefronts across the chandelier, scale speed by `bpm` so animations don't feel too sluggish on fast tracks or frantic on slow tracks:

```python
# Travel time across the segment takes exactly 1 beat
# Segment length / (seconds per beat * FPS)
beat_period_seconds = 60.0 / max(60.0, min(200.0, self.listener.bpm))
frames_per_beat = beat_period_seconds * 60.0
speed_pixels_per_frame = self.nb_of_leds / max(1.0, frames_per_beat)
```

---

## 4. Hardware & Vectorization Invariants (Zero Heap Allocations)

The chandelier runs on a Raspberry Pi at **60 FPS** (16.6ms total budget). Visual rendering across all 11 segments must execute in **$\le 1.0\text{ms}$** per frame.

1. **Strictly No Python Loops Over LEDs:**
   * Never use `for i in range(self.nb_of_leds):`.
   * Use NumPy vectorization for all coordinate, HSV, and RGB math.
2. **Zero Heap Allocations in `run()` / `render()`:**
   * Pre-allocate all scratch buffers, linspaces, and coordinate arrays in `__init__()`.
   * Mutate buffers in-place (`np.copyto()`, slice assignment `[:]`, or pre-allocated targets).
3. **Use Immutable Color Constants:**
   * Colors from `utils.colors` (`red`, `green`, `blue`, `white`, etc.) and `self.white` on `Mode` are immutable tuples `(R, G, B)`. They can be safely assigned to array slices (`self.rgb_list[:] = self.white`) without risk of shared mutable state corruption across segments.
4. **Use Base Class Vectorized Blenders:**
   * `self.smooth_vectorized(ratio, target_rgb_matrix)`
   * `self.smooth_segment_vectorized(ratio, start, stop, target_color_or_array)`
   * `self.fade_to_black(ratio)` or `self.fade_to_black_segment_vectorized(ratio, start, stop)`

---

## 5. Resilient Mode Reference Template

Copy this pattern when authoring or retrofitting a rhythm-reactive mode:

```python
import numpy as np
import modes.Mode as Mode
import utils.rgb_hsv as RGB_HSV
import utils.colors as colors

class Resilient_beat_mode(Mode.Mode):
    """
    Template for a resilient rhythm-reactive mode featuring:
    1. Zero-allocation vectorized execution.
    2. Graceful confidence degradation to acoustic volume when lost.
    3. Real-beat gated kinetic transient triggers.
    4. Continuous phase-driven smooth decays.
    """

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        
        # Pre-allocated spatial arrays (ZERO runtime allocation)
        self.spatial_coords = np.linspace(0.0, 1.0, self.nb_of_leds)
        self.hues = np.full(self.nb_of_leds, 0.6) # Deep blue default
        self.sats = np.ones(self.nb_of_leds)
        self.vals = np.zeros(self.nb_of_leds)

    def run(self):
        # 1. Read rhythmic metrics
        phase = self.listener.beat_phase
        confidence = np.clip(self.listener.beat_confidence, 0.0, 1.0)
        
        # 2. Compute Rhythmic vs Acoustic energy components
        # Rhythmic: Punchy exponential decay locked to phase
        rhythmic_val = (1.0 - phase) ** 2.0
        
        # Acoustic Fallback: Smoothed total volume
        acoustic_val = self.listener.asserved_total_power
        
        # 3. Graceful Degradation Blend
        # When confidence is 1.0 -> 100% sharp beat
        # When confidence is 0.0 -> 100% smooth acoustic breathing
        blended_val = (confidence * rhythmic_val) + ((1.0 - confidence) * acoustic_val)
        
        # 4. Gated Shockwave / Flash Trigger
        # Only inject high-energy flash on VERIFIED acoustic beats (no ghost beats during silence)
        if self.listener.is_beat and self.listener.is_real_beat and confidence > 0.5:
            # Shift hue slightly on strong real beats
            self.hues[:] = (self.hues + 0.05) % 1.0
            flash_boost = 0.3
        else:
            flash_boost = 0.0

        # 5. Vectorized Color Synthesis
        self.vals[:] = np.clip(blended_val + flash_boost, 0.0, 1.0)
        target_rgb = RGB_HSV.fromHSV_toRGB_vectorized(self.hues, self.sats, self.vals)
        
        # 6. Smooth blend into LED buffer
        self.smooth_segment_vectorized(0.3, 0, self.nb_of_leds - 1, target_rgb)
```
