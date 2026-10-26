# Visual Mode Sector Contract & Authoring Rules (`MODE_RULES.md`)

Sibling of [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md), [`docs/contracts/mood_contract.md`](../docs/contracts/mood_contract.md), and [`docs/contracts/transition_contract.md`](../docs/contracts/transition_contract.md).

This document defines **Part A: The Mode Sector Contract** (doors, signal-handling guidance, and sanctioned base-class helpers) and **Part B: Authoring & Vectorization Rules** for all 21 concrete modes in `modes/`.

---

## Part A: Mode Sector Contract (authoritative)

### 1. The Doors (`modes/Mode.py`)

`modes/Mode.py` is the **sanctioned base class and front door** of the `modes/` sector. Every concrete mode (`modes/*_mode.py`) subclasses `Mode.Mode` and interacts with the rest of the chandelier through the doors below:

| # | Door | Dir | Shape (on `Mode`) | Notes |
| :-: | :--- | :-: | :--- | :--- |
| 1 | Construction | in | `__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)` | Called once per segment on startup. Pre-allocates all scratch arrays here. |
| 2 | Rendering | in/out | `render(buffer=None, audio_ctx=None, frame_info=None)` / `run()` | Mutates the target `(N, 3)` `int32` RGB buffer in place at 30 FPS with zero heap allocations. |
| 3 | Settings | in/out | `get_settings_schema()`, `apply_settings(settings)` | Declares live UI sliders and binds runtime updates. Every declared setting must be read in `run()`/`render()`. |
| 4 | Transition Handshake | in | `on_transition_enter(progress)`, `on_transition_exit(progress)` | Optional 3-layer cooperative transition hooks exposing `self.transition_scale` (`0.0 .. 1.0`). |
| 5 | Mood Views | in | `Mode.bind_mood_colors(colors)`, `Mode.bind_mood_modifiers(modifiers)` | Bound once by `Mode_master` from `mood.api`. Concrete modes read `self.mood_colors`, `self.palette_lut`, `self.highlight_color`, `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, and `self.mood_accent`. |
| 6 | Music Injection | in | `self.listener` (`music.api.ListenerProtocol`) | Speaker-aligned ($T_{\text{speaker}}$) audio facade and `self.listener.context` (`MusicalContextProtocol`). |

### 2. Handling Signals by Trust

Because `self.listener` is injected into every mode, modes see every public signal of `Listener` and `listener.context`. How much we trust each one is stated **only** by its producer in [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md); this file does not repeat per-signal ratings. Trust is engineering guidance, not a hard rule, and it is not enforced by a test. General authoring guidance:

| Tier | What it means | How to use it in a concrete mode (`modes/*_mode.py`) |
| :--- | :--- | :--- |
| **🟢 HIGH** *(physical / pre-gated)* | Direct spectral measurement, or already debounced and smoothed inside its own sealed room (including `mood_colors` and `mood_modifiers` as consumed). | Safe to drive brightness, extent, or colour directly on every frame. |
| **🟡 MEDIUM** *(confidence-gated)* | Probabilistic tempo/phase or rhythm badges that can drift on beatless intros, breakdowns, or polyrhythms. | Gate or blend by a confidence signal (`rhythm_lock`, `beat_trust`, `rhythm_salience`, `is_locked`, `beat_confidence`, or `beat_pulse`) and keep a continuous fallback when confidence is `0.0`. |
| **🟠 LOW** *(heuristic / predictive / uncalibrated)* | Scene, drop, boundary, novelty, or pitch signals prone to false positives and jitter. | Avoid reading directly in concrete modes. Scene adaptation goes through `mood_modifiers` (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`), and drop/impact envelopes go through the sanctioned `Mode.py` helpers below. Never use for hard branches, velocity flips, or 1.5 s whiteouts. |

### 3. Sanctioned Gated Helpers on `Mode.py`

`modes/Mode.py` is the sanctioned place that reads the noisy signals directly, because it encapsulates the 🟡 MEDIUM and 🟠 LOW signals behind safe, bounded helpers:

| Sanctioned Helper (`Mode.py`) | Internal Signals Read | What It Guarantees to Concrete Modes |
| :--- | :--- | :--- |
| `self.rhythm_lock` | `ctx.salience` (or `listener.rhythm_salience`), `ctx.beat_trust` (or `listener.beat_trust`) | Continuous confidence weight in $[0.0, 1.0]$ ($\sqrt{\text{trust} \cdot \text{salience}}$). |
| `self.beat_pulse(sharpness=2.0)` | `listener.beat_phase`, `self.rhythm_lock`, `self.mood_sharpness`, `ctx.energy` | Blends a sharp phase-locked $(1 - \theta)^{\text{sharpness} \cdot \text{mood\_sharpness}}$ pulse with a smooth acoustic breathing fallback when `rhythm_lock -> 0.0`. |
| `self.drop_hit` | `ctx.is_drop_impact` | **1-frame** boolean trigger on drop arrival (`False` on all other frames), preventing 1.5 s solid whiteouts. |
| `self.drop_decay` | `ctx.scene`, `ctx.is_drop_impact`, `ctx.drop_progress` | Smooth $1.0 \to 0.0$ envelope across the 1.5 s `DROP_IMPACT` dwell (`0.0` outside a drop). |
| `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent` | `Mode._shared_mood_modifiers` (bound from `mood.api.modifiers()`) | Debounced (`0.30 s`) and cosine-smoothed (`2.5 s`) scene modifiers (`🟢 HIGH` trust as consumed). |

---

## Part B: Visual Mode Authoring & Rhythm Integration Rules

### 1. The Core Philosophy: "Graceful Degradation & Subtle Mood Governance"

Interactive lighting has a golden rule: **The spectator must never see a broken rhythm or a violent state-machine snap.**
Human perception detects audio-visual desync in under 50 milliseconds. If the beat tracker is confused (e.g. during a chaotic guitar solo, ambient intro, or tempo shift) and the chandelier keeps strobing out of time, or if a false `DROP_IMPACT` / `BUILDUP` classification causes a 1.5 s full-strip whiteout, spectators instantly perceive it as a technical glitch.

Therefore, every visual mode should follow **three architectural laws**:
1. **Always Alive Without the Flywheel (`self.rhythm_lock == 0.0`):** Every mode must produce a smooth, musical animation driven by continuous audio energy, 8-band spectrum, or pitch even when the beat tracker is completely lost (`beat_trust == 0.0`).
2. **Rhythm-Locked When Confident (`self.rhythm_lock -> 1.0`):** As `rhythm_salience` and `beat_trust` rise, the *same* visual smoothly couples its pulse and speed to `beat_phase`, `bpm`, and `is_real_beat` without switching to a different visual algorithm.
3. **Avoid `if scene == ...` Branching in Modes:** Because macro scene detection (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) is a heuristic that can jitter, **modes should avoid reading or branching on `ctx.scene`**. Prefer the sealed [`mood/`](../mood/api.py) sector, which absorbs scene changes with a `0.30 s` debounce and a `2.5 s` cosine crossfade, exposing bounded modifiers (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`) on `Mode`.

---

### 2. Rhythmic & Mood Signals Reference

| Property | Trust | Type | Description | Best Used For |
| :--- | :-: | :--- | :--- | :--- |
| `self.rhythm_lock` | 🟢 Helper | `float` | Combined lock confidence $[0.0, 1.0]$ from `beat_trust` and `salience`. | Blending between continuous spectral/energy drive (`0.0`) and beat-locked motion (`1.0`). |
| `self.beat_pulse(sharpness)` | 🟢 Helper | `float` | Confidence-blended beat envelope $[0.0, 1.0]$ scaled by `mood_sharpness`. | Primary rhythmic brightness/size pump with built-in acoustic breathing fallback. |
| `self.mood_pace` | 🟢 HIGH | `float` | Cosine-smoothed scene speed multiplier $[0.82, 1.22]$. | Gently nudging wave, ball, or hue drift speed ($\pm 20\%$ max). |
| `self.mood_sharpness` | 🟢 HIGH | `float` | Cosine-smoothed envelope exponent multiplier $[0.78, 1.22]$. | Softening pulses in `CHILL` and sharpening them in `BUILDUP`/`DROP_IMPACT`. |
| `self.mood_trail` | 🟢 HIGH | `float` | Cosine-smoothed trail persistence multiplier $[0.88, 1.18]$. | Scaling trail length (`fade_ratio / self.mood_trail`). |
| `self.mood_accent` | 🟢 HIGH | `float` | Cosine-smoothed highlight warmth blend $[0.00, 0.28]$. | Warming primary colors up to 28% toward `self.highlight_color`. |
| `self.listener.context.energy` | see contract | `float` | Continuous fused visual energy drive $[0.0, 1.0]$. | Master brightness, bar height, and continuous motion drive. |
| `self.listener.context.spectral_tilt` | see contract | `float` | Treble vs Bass balance $[-1.0, 1.0]$ across 8 Mel bands. | Warm/cool color shifts, horizontal balance point. |
| `self.listener.context.vertical_center` | see contract | `float` | Spectral center of mass $[0.0, 1.0]$. | Target position for gliding balls and bar color balance. |
| `self.drop_hit` | 🟢 Helper | `bool` | True for **1 frame** on drop impact arrival (`ctx.is_drop_impact`). | Triggering a single shockwave or kick without a 1.5 s lock. |
| `self.drop_decay` | 🟢 Helper | `float` | Smooth $1.0 \to 0.0$ envelope across the drop dwell. | Gradual post-drop boost without reading `ctx.scene` or `ctx.is_drop_impact`. |
| `self.listener.context.is_real_beat` | see contract | `bool` | True if beat tick matches verified acoustic transient ($P \ge 0.20$). | Gating hard strobes, physical kicks, and boundary sparks (with `rhythm_lock`). |
| `self.listener.beat_phase` | see contract | `float` | Continuous phase $\theta \in [0.0, 1.0)$ in speaker time ($0.0 = \text{strike}$). | Smooth ADSR decays, sine breathing, traveling waves (blended via `rhythm_lock`). |
| `self.listener.bpm` | see contract | `float` | Current estimated tempo (e.g. `124.0`). | Scaling particle speeds, wave travel times, and physics (blended via `rhythm_lock`). |

---

### 3. The 4 Golden Rules of Rhythm-Reactive Modes

#### Rule 1: Always Blend with `rhythm_lock` or Use `self.beat_pulse()`
Never write binary logic that assumes the beat tracker is always locked. Use `self.beat_pulse()` for envelope modulation, and blend kinematic positions/forces with `self.rhythm_lock`:

```python
lock = self.rhythm_lock  # [0.0, 1.0]
pulse = self.beat_pulse(2.2)  # Punchy when locked, smooth acoustic breathing when lost
```

#### Rule 2: Gate Hard Flashes (`is_real_beat` & `self.drop_hit` Protection)
Violent strobes and high-brightness kicks must **never** fire on phantom coasting beats during silent breakdowns, and must **never** lock on for the 1.5 s `DROP_IMPACT` scene dwell:

```python
# GOOD: 1-frame verified transient or 1-frame drop_hit
if (self.listener.is_beat and ctx.is_real_beat and self.rhythm_lock > 0.35) or self.drop_hit:
    self.trigger_spark()
```

#### Rule 3: Prefer Continuous Phase ($\theta$) Over 1-Frame Impulse Spikes
Continuous motion and exponential decays driven by `beat_phase` (blended with a free-running phase when `self.rhythm_lock` is low) look fluid even if the tempo estimate drifts slightly.

#### Rule 4: Scale Motion to Tempo & `mood_pace` (BPM-Aware Kinematics)
Scale speeds by `bpm` and `self.mood_pace`:

```python
frames_per_beat = max(1.0, (60.0 / bpm) * 60.0)
speed = (float(self.half_len) / frames_per_beat) * self.fps_ratio * self.mood_pace
```

---

### 4. Hardware & Vectorization Invariants (Zero Heap Allocations)

The chandelier renders on a Raspberry Pi at **30 FPS** (33.33 ms frame period, $\le 20.0\text{ ms}$ total compute budget per AXIOM-01; audio DSP ticks at 60 Hz). Visual rendering across all 11 segments must execute in **$\le 1.0\text{ ms}$** per frame ($\le 0.20\text{ ms}$ per mode).

1. **Strictly No Python Loops Over LEDs:** Never use `for i in range(self.nb_of_leds):`. Use NumPy vectorization for all coordinate, HSV, and RGB math.
2. **Zero Heap Allocations in `run()` / `render()`:** Pre-allocate all scratch buffers, linspaces, and coordinate arrays in `__init__()`. Mutate buffers in-place (`np.copyto()`, slice assignment `[:]`, or pre-allocated targets).
3. **Use Base Class Vectorized Blenders:** `self.smooth_vectorized(ratio, target_rgb_matrix)`, `self.smooth_segment_vectorized(ratio, start, stop, target_color_or_array)`, `self.fade_to_black(ratio)`, or `self.fade_to_black_segment_vectorized(ratio, start, stop)`.
4. **Support Mode-Cooperative Transitions (`self.transition_scale`):** Scale physical extent/height/radius/kick forces by `self.transition_scale`.

---

### 5. Shared Authoring Helpers (`Mode` base class)

| Helper | Use it for |
| :--- | :--- |
| `self.rhythm_lock` | Continuous confidence weight in $[0.0, 1.0]$ combining `beat_trust` and `salience`. |
| `self.beat_pulse(sharpness)` | Confidence-blended beat envelope (Rule 1 in one call), automatically scaled by `self.mood_sharpness`. |
| `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent` | Cosine-smoothed scene modifiers from `mood/` (`(4,)` `float32`). |
| `self.drop_hit` | **One-frame** trigger when a drop lands (`ctx.is_drop_impact`). |
| `self.drop_decay` | Envelope $1 \to 0$ across the drop dwell (`0.0` outside a drop). |
| `self.dt`, `self.fps_ratio`, `self.alpha(rate_hz)` | Frame time in seconds, ratio relative to 60 Hz reference, and frame-rate independent smoothing $1 - e^{-dt \cdot rate}$. |
| `self.palette_lut`, `self.palette_sample(t, out)` | `(256, 3)` gradient `primary -> secondary -> accent`, refreshed in place on mood change, and allocation-free sampler. |
| `self.highlight_color` | Luminance-safe flash/warmth colour (brightest palette slot pushed 40% toward white). **Use instead of `mood_colors[3]` for flashes and `mood_accent` blends.** |
| `self.segment_phase_offset` | Stable per-segment offset in $[0, 1)$ to stagger identical modes across the chandelier. |

**Never cache views of `self.rgb_list` in `__init__`.** During transitions `Mode.render(buffer=...)` redirects `self.rgb_list` to a different buffer; a cached view keeps writing to the old one. Either slice inside `run()`/`render()`, or cache the views keyed by buffer identity (`if self._view_buf is not self.rgb_list: rebuild`).

**Settings must be read.** Every entry returned by `get_settings_schema()` must be used by the mode outside `__init__`. `tests/test_mode_helpers.py::TestDeadSettingsRatchet` fails on new dead sliders; fix an old one and remove it from `KNOWN_DEAD`.
