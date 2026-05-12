# Vialactée — Complete Project Review

> **Scope:** Full codebase audit of `c:\Users\Users\Desktop\vialactée\vialactee`  
> **Date:** 2026-05-12  
> **Reviewer:** Antigravity (multi-domain sub-agent analysis)

---

## Executive Summary

Vialactée is a technically ambitious, well-conceived audio-reactive LED orchestration system. The architecture is **clean and layered**, the DSP pipeline is **genuinely sophisticated**, and the hardware abstraction is **production-quality**. The main risks are concentrated in: a few concurrency sharp edges, some growing code duplication between the playground and core, hardcoded geometry in the simulator, and a web interface that has outgrown its prototype state. The project is in very good shape overall — the findings below are refinements, not structural problems.

---

## 1. Architecture & Overall Design

### ✅ Strengths

- **Layered and clean separation of concerns.** `Main.py → Listener → AudioIngestion / AudioAnalyzer → Mode_master → Segment → Mode` is a textbook unidirectional dependency graph.
- **HardwareFactory abstraction** is excellent. The `auto` detection (trying `board`/`neopixel` imports) means the same codebase genuinely runs on Pi and Windows without any branch in application logic.
- **The 5-second non-causal delay pipeline** is the project's most elegant design. Buffering spectral state and beat predictions in parallel deques (`spectral_delay_queue`, `future_queue`) and popping them in sync is mathematically sound and beautifully implemented.
- **`AGENT.md` and `project_overview.md`** as machine-readable onboarding guides is a great practice for AI-assisted development.
- **`modes.json`** for runtime mode registration via `importlib` means adding a new visual mode requires zero changes to core engine files.

### ⚠️ Issues & Recommendations

#### 1.1 Geometry duplication between `segments.json` and `Fake_leds.py`

The physical LED geometry is **defined twice**: once in `config/segments.json` (the authoritative source) and once hardcoded inside `Fake_leds.py`'s `segments_def` list. These two sources can silently diverge.

```diff
- # In Fake_leds.py
- cls._instance.segments_def = [
-     (173, "vertical", 962, 164, "segment_v4", (50, 100, 255)),
-     ...
- ]
+ # Load geometry from segments.json at startup instead
+ with open("config/segments.json") as f:
+     seg_data = json.load(f)
+ cls._instance.segments_def = _parse_segments_json(seg_data)
```

**Impact:** Medium — any geometry change to `segments.json` won't be reflected in the visual simulator.

#### 1.2 `startServer` defaults differ between the fallback generator and the live config

In `Main.py`, the auto-generated default config sets `"startServer": false`, but `config/app_config.json` currently has `"startServer": true`. This is a latent bug: on a fresh install, the TCP server won't start even if a user expects it to.

#### 1.3 The `Connector` action `restart_raspberry_pi` returns `applied: false` with no implementation path

```python
if action in {"restart_python_loop", "restart_raspberry_pi"}:
    return {"applied": False, "reason": "system_action_not_implemented"}
```

The web interface exposes this button to the user. A system command (`sudo reboot`) wrapped in `asyncio.create_subprocess_exec` could implement this properly, or the button should be hidden in the web UI. Right now the user clicks it and nothing happens silently.

---

## 2. Core Engine — `AudioIngestion.py` / `AudioAnalyzer.py`

### ✅ Strengths

- **ADSR vectorization** using `np.where` for attack/release is elegant and avoids any Python-level loops over bands.
- **`asserv_fft_bands`** (the dual local_max/global_max servo) is a smart auto-gain approach that adapts to any room energy level without clipping.
- **Phase Inertia Flywheel** with a Gaussian penalty function (`0.20` variance) on phase jumps is a genuinely good technique — it eliminates "ping-pong" between harmonics.
- **ODF (Onset Detection Function) buffer** with exponential recency decay prevents old rhythmic patterns from contaminating the beat estimate.

### ⚠️ Issues & Recommendations

#### 2.1 `asserv_fft_bands` uses a Python `for` loop — inconsistent with the vectorized philosophy

```python
# In AudioIngestion.py — this is O(n) in Python
def asserv_fft_bands(self, fps_ratio: float) -> None:
    for band_index in range(self.nb_of_fft_band):
        if self.smoothed_fft_band_values[band_index] >= self.band_lm[band_index]:
            ...
```

The rest of the pipeline is fully vectorized. This loop can be rewritten:

```python
def asserv_fft_bands(self, fps_ratio: float) -> None:
    peak_mask = self.smoothed_fft_band_values >= self.band_lm
    self.band_lm = np.where(peak_mask, self.smoothed_fft_band_values, self.band_lm * (0.9995 ** fps_ratio))

    gm_peak_mask = self.smoothed_fft_band_values >= self.band_gm
    self.band_gm = np.where(gm_peak_mask,
        1.01 * self.smoothed_fft_band_values,
        self.band_gm * (1 + (0.005 * fps_ratio) * (self.band_lm / np.maximum(0.001, self.band_gm) - 0.9))
    )
    self.asserved_fft_band += np.minimum(1.0, 0.4 * fps_ratio) * (
        self.smoothed_fft_band_values / self.band_gm - self.asserved_fft_band
    )
```

**Impact:** Low at 8 bands; would matter if `nb_of_fft_band` is increased.

#### 2.2 `asserv_total_power` uses a Python `for` loop for the sum

```python
for band_index in range(self.nb_of_fft_band):
    instantPower += self.fft_band_values[band_index]
```

Should be `instantPower = np.sum(self.fft_band_values)`.

#### 2.3 `apply_fake_fft` is a pure Python loop used only in simulation

```python
def apply_fake_fft(self, fps_ratio: float) -> None:
    for band_index in range(self.nb_of_fft_band):
        self.fft_band_values[band_index] += random.randint(-10, 10)
```

Also uses `num`/`denom` accumulator loops for `fft_bary`. Neither this computed `fft_bary` nor the fake FFT is consumed anywhere visible in the codebase (no mode reads `fft_bary`). This is dead code in the simulation path.

#### 2.4 `hasattr` guards on `chroma_values` are scattered everywhere

The `Listener.py` has 6+ `hasattr(self.ingestion, 'chroma_values')` checks. This suggests Chromagram was added incrementally without updating the `__init__` to always initialize the attribute. Adding `self.chroma_values = np.zeros(12)` unconditionally in `AudioIngestion.__init__` would remove all these guards.

#### 2.5 `is_song_change` flag is never reset to `False`

In `AudioAnalyzer.py`:
```python
self.is_song_change = True  # Set on detection
# ... but never reset to False in the same method
```

This means the `is_song_change` flag stays `True` forever after the first song change. `Mode_master` and the delay queue must defensively never see this flag clear. A proper event pattern would reset the flag on the next frame:
```python
# At the top of detect_band_peaks:
self.is_song_change = False
self.is_verse_chorus_change = False
```

---

## 3. `Listener.py` — The Facade

### ✅ Strengths

- The dual-deque pattern (one for spectral data, one for beat events) with independent popping is architecturally clean.
- The `@property` facade exposing delayed values transparently is the right abstraction — modes never need to know about the buffering.

### ⚠️ Issues & Recommendations

#### 3.1 The spectral delay queue pops multiple frames per tick with `while` — can cause jitter

```python
while len(self.spectral_delay_queue) > 0:
    if current_time - self.spectral_delay_queue[0]['time'] >= self.analyzer.lookahead_seconds:
        popped = self.spectral_delay_queue.popleft()
        # overwrite all delayed values
    else:
        break
```

If the system hiccups (e.g., GC pause, blocking I/O), multiple frames get popped in a single tick, and the last one wins. All intermediate frames are silently discarded. Consider storing the "best" (most recent valid) frame rather than overwriting blindly.

#### 3.2 `beat_count` and `beat_phase` are direct pass-throughs, bypassing the delay

```python
@property
def beat_count(self): return self.analyzer.beat_count
@property
def beat_phase(self): return self.analyzer.beat_phase
```

These expose **live (non-delayed)** values. However, the BPM/phase values are already correctly delayed via `future_queue` inside `AudioAnalyzer`. This is actually correct behavior — but it's confusing because most other properties are wrapped with `_delayed_*`. A docstring clarifying that `beat_phase` is already correctly delayed by `future_queue` internally would prevent future regressions.

#### 3.3 `fps_ratio` is initialized as `0.0`

```python
self.fps_ratio: float = 0.0
```

On the very first frame, `fps_ratio = 0.0`. Any mode doing `(0.9) ** fps_ratio` will get `1.0` (safe), but any mode dividing by `fps_ratio` will get a `ZeroDivisionError`. The `update` method has a guard (`max(0.001, self.dt * 60.0)`) but only after the first frame.

---

## 4. `Mode_master.py` & `Segment.py`

### ✅ Strengths

- **Shuffle-bag** random configuration picking is a clever non-repetition algorithm.
- **`_normalize_mode_name`** providing legacy compatibility for old underscore-style names is good defensive coding.
- **`execute_mode_swap` vs `change_mode` vs `force_mode`** — three distinct swap semantics with clear contracts.
- **Transition blocking logic** (`is_in_transition`, `isBlocked`) cleanly prevents race conditions at the segment level.

### ⚠️ Issues & Recommendations

#### 4.1 `update_leds` uses a Python loop — the slowest part of the render pipeline

```python
def update_leds(self) -> None:
    for led_index in range(self.nb_of_leds):
        if self.way == "UP":
            self.leds[self.indexes[led_index]] = [int(luminosite * x) for x in self.rgb_list[led_index]]
```

This is a pure Python loop over potentially 205 LEDs per segment × 11 segments = 2255 iterations per frame. With `rgb_list` already being a numpy array, this should be:

```python
def update_leds(self) -> None:
    scaled = (self.rgb_list * self.listener.luminosite).astype(np.int32)
    if self.way == "UP":
        self.leds[self.indexes] = scaled
    else:
        self.leds[self.indexes[::-1]] = scaled
```

**Impact:** High. This loop runs at 60fps across all segments. It's likely the bottleneck for frame rate.

#### 4.2 `execute_mode_swap` sets `is_in_transition = False` redundantly

```python
def execute_mode_swap(self, mode_name: str) -> None:
    if self.is_in_transition:
        return  # exits early
    ...
    self.is_in_transition = False  # unreachable if it was True
```

The `self.is_in_transition = False` line is dead code — if the flag was `True`, the method already returned.

#### 4.3 `change_mode` ignores the `transition_config` parameter after storing `target_mode_name`

When `transition_config` is provided to `change_mode`, the segment stores `target_mode_name` and sets `is_in_transition = True`, but `transition_config` itself is never stored. The `Transition_Engine` is applied externally (in `Mode_master`), so this works — but the segment has no memory of *which* transition was requested. If `Mode_master` later queries the segment for its transition type, it won't know.

#### 4.4 Mode auto-load silently swallows import errors

```python
except Exception as e:
    self.logger.error(f"Failed to load mode {mode_info.get('name', 'Unknown')}: {e}")
```

On a Raspberry Pi cold boot, a missing dependency (e.g., `pygame` not installed) would fail silently here, leaving the segment with fewer modes than expected. Consider making this a hard failure during initialization, not a soft warning.

---

## 5. `Transition_Engine.py`

### ✅ Strengths

- **Geometry-aware transitions** using PNG spatial masks is architecturally beautiful. Transitions can be authored visually (paint a grayscale image) and the engine reads thresholds per-LED automatically.
- **`apply_explosion`** is a standout visual achievement — 3-phase (implode / blackout / explode) with angular beam math is genuinely impressive.
- All transitions are **pure numpy functions** with no Python loops. This is correct and efficient.

### ⚠️ Issues & Recommendations

#### 5.1 Hardcoded physics constants in `apply_explosion` (750+ lines total in engine)

Magic numbers like `t_implode = 0.78`, `t_blackout = 0.80`, `front_depth = 250.0`, `cx, cy = 500, 120` are scattered in transition functions with no configuration path. If the chandelier geometry changes, all these need manual updates.

#### 5.2 `apply_weird_glitch` has an index-mismatch bug

```python
new_colors_subset = rgb_list_new[mask_glitching]
glitch_colors[mask_peek] = new_colors_subset[mask_peek]
```

`new_colors_subset` is indexed by `mask_glitching` (shape: `N_glitching × 3`), then sub-indexed by `mask_peek` (shape: `N_glitching`). This is correct if `mask_peek` was generated from `glitch_colors` (same shape as `new_colors_subset`). However, `mask_peek` was generated from `flicker_noise[mask_glitching]`, so shapes match — but this dependency chain is fragile and should be documented.

#### 5.3 `spatial_images` loaded at module import time

```python
# At module level
spatial_images = {}
for img_name in TRANSITION_IMAGES:
    ...
    spatial_images[img_name] = np.array(img)
```

Module-level I/O runs at import time. If the image directory doesn't exist or images are missing, import will fail with an unhandled exception. This should be lazy-loaded or wrapped in try/except.

---

## 6. `connectors/Local_Microphone.py`

### ✅ Strengths

- The `audio_callback` correctly handles both `InputStream` and `Stream` signatures (4-arg and 5-arg) via `len(args)`.
- The **5-second physical delay buffer** (circular ring buffer played back through speakers) is a clever hardware trick for the non-causal lookahead.
- **Dynamic latency computation** using `time_info.inputBufferAdcTime` is the right way to measure real hardware latency.

### ⚠️ Issues & Recommendations

#### 6.1 `audio_callback` is called from a C thread — it mutates shared Python state without a lock

```python
def audio_callback(self, *args):
    ...
    self.audio_data = np.roll(self.audio_data, -m)  # mutates self.audio_data
    self.audio_data[-m:] = incoming
```

Meanwhile, `listen()` reads `self.audio_data` from the asyncio thread. On CPython, the GIL makes this *mostly* safe for numpy array assignments, but `np.roll` creates a new array and rebinds `self.audio_data` — this is a reference swap, not an in-place operation. A `threading.Lock` around the read/write of `self.audio_data` is the correct fix:

```python
# In __init__:
self._audio_lock = threading.Lock()

# In audio_callback:
with self._audio_lock:
    self.audio_data = np.roll(self.audio_data, -m)
    self.audio_data[-m:] = incoming

# In listen:
with self.local_microphone._audio_lock:
    audio_snapshot = self.audio_data.copy()
self.listener.process_raw_audio(audio_snapshot)
```

#### 6.2 `delay_index` arithmetic can overflow on very long sessions

```python
self.delay_index = self.delay_index + m  # keeps growing
if self.delay_index >= self.delay_frames:
    self.delay_index %= self.delay_frames
```

The `%=` only fires at the wrap point. The intermediate value can grow to `delay_frames + chunk_size` safely, but over weeks of continuous operation it approaches `sys.maxsize`. A simple `self.delay_index = (self.delay_index + m) % self.delay_frames` on every frame is safer.

---

## 7. `hardware/` Layer

### ✅ Strengths

- **`HardwareInterface` ABC** correctly enforces the contract with `@abstractmethod` for all 6 operators.
- **`Udp_Sender` + `Fake_ESP32`** subprocess approach is architecturally clean — Pygame runs in its own process, no event loop blocking.

### ⚠️ Issues & Recommendations

#### 7.1 `Fake_leds.py` is imported in simulation mode but the live code path uses `Udp_Sender`

When `HARDWARE_MODE = "simulation"`, `HardwareFactory` imports `Udp_Sender` (not `Fake_leds`). But `Fake_leds.py` still contains the `FakeLedsVisualizer` singleton which is imported if `Fake_leds` is directly imported anywhere. Currently the two codepaths are independent, which is correct — but the `Fake_leds.py` file has a dangling Singleton class that is never used in production. The file should either be marked clearly as legacy/unused or removed.

#### 7.2 `HardwareFactory.create_hardware` hardcodes pin names and UDP ports

```python
leds1 = Rpi_NeoPixels.Rpi_NeoPixels("D21", 785)
leds2 = Rpi_NeoPixels.Rpi_NeoPixels("D18", 519)
leds1 = Udp_Sender.Udp_Sender("127.0.0.1", 9001, 785)
leds2 = Udp_Sender.Udp_Sender("127.0.0.1", 9002, 519)
```

GPIO pins, UDP ports, and LED counts should come from `app_config.json`. A hardware change (e.g., moving to a different GPIO pin) requires source code modification.

---

## 8. `wabb-interface/` (React Web App)

### ✅ Strengths

- **`controlBridge.ts`** cleanly separates the WebSocket connection from the React state layer.
- The `TopologyEditor.tsx` (38KB) is the most complex component and handles the chandelier segment editor — it's appropriately large for what it does.
- TypeScript throughout with a proper `tsconfig`.

### ⚠️ Issues & Recommendations

#### 8.1 `constants/modes.ts` and `config/modes.json` are duplicate sources of truth

The available modes are defined in both:
- `wabb-interface/src/constants/modes.ts` (frontend)
- `config/modes.json` (backend)

Adding a new mode requires updating both files. The frontend should fetch the mode list from the backend on connect (it can be added as a WebSocket message type `get_modes` → `modes_list`).

#### 8.2 `index.css` is 64KB — likely contains dead styles

At 64KB, this CSS file has grown far beyond what a 5-page app needs. It likely contains utility classes, unused components, or scaffolding from earlier prototypes. A CSS audit is recommended.

#### 8.3 No reconnection logic in `controlBridge.ts`

If the Raspberry Pi WebSocket server restarts (e.g., after a code update), the web app will silently lose its connection. A standard exponential-backoff reconnection loop would make the interface resilient to server restarts during live shows.

```typescript
// Suggested reconnection pattern
function connectWithRetry(url: string, delay = 1000) {
    const ws = new WebSocket(url);
    ws.onclose = () => setTimeout(() => connectWithRetry(url, Math.min(delay * 2, 30000)), delay);
    return ws;
}
```

---

## 9. `playground/` — Research Code

### ✅ Strengths

- `test_runner.py` is a well-structured simulation harness — it patches `time.time`, loads real audio, and runs the full tracker pipeline offline. This is excellent engineering practice.
- The 4-option jailbreak comparison framework is a proper A/B test structure with JSON result export and matplotlib visualization.

### ⚠️ Issues & Recommendations

#### 9.1 `test_runner.py` duplicates large sections of `AudioAnalyzer.py` logic

The standalone phase sweep, the `future_queue` logic, and the BPM trust calculation are all copy-pasted from `AudioAnalyzer.py` into `test_runner.py`. When `AudioAnalyzer` is updated, `test_runner` will silently run old code. The test harness should instantiate the real `AudioAnalyzer` class rather than reimplementing it.

#### 9.2 `test_runner.py` has duplicate JSON write at the end

```python
with open('...jailbreak_options_results.json', 'w') as f:
    json.dump(results_dict, f)

print("Results successfully saved...")

with open('...jailbreak_options_results.json', 'w') as f:  # duplicate!
    json.dump(results_dict, f)
```

The second write is identical to the first and should be removed.

#### 9.3 The `playground/` contains very large notebook files (1.7MB, 900KB)

These notebooks contain embedded output data (probably matplotlib plots and audio arrays). They should be run with `nbstripout` before committing to keep git history clean.

---

## 10. Documentation (`.agents/`)

### ✅ Strengths

- `AGENT.md` is a well-maintained living document with 14 numbered upgrade notes.
- The task-based navigation map in `project_overview.md` is excellent for onboarding.

### ⚠️ Issues & Recommendations

#### 10.1 `AGENT.md` mentions `asserved_fft_band` uses a "future_queue" but the queue is actually in `AudioAnalyzer`

Small inconsistency — the `future_queue` is an `AudioAnalyzer` concept but `AGENT.md` attributes it to `Listener`. Should reference `AudioAnalyzer.detect_band_peaks()` directly.

#### 10.2 No `requirements.txt` or `pyproject.toml`

There is no dependency specification file. A fresh Pi deployment requires manual `pip install` guessing. A minimal `requirements.txt` listing `numpy`, `sounddevice`, `python-btrack` (or whatever is used), `aiohttp`/`websockets`, `pygame` would make deployment reproducible.

---

## Summary Table

| Area | Score | Key Risk |
|---|---|---|
| **Architecture & Design** | ⭐⭐⭐⭐⭐ | Geometry duplication in simulator |
| **Audio DSP Pipeline** | ⭐⭐⭐⭐½ | Python loops in hot path, `is_song_change` never reset |
| **Listener Facade** | ⭐⭐⭐⭐ | Thread-safety on `audio_data`, multi-frame skip |
| **Mode Engine** | ⭐⭐⭐⭐ | `update_leds` Python loop is bottleneck |
| **Transition Engine** | ⭐⭐⭐⭐½ | Module-level I/O, magic geometry constants |
| **Hardware Abstraction** | ⭐⭐⭐⭐ | Hardcoded pins/ports, dead `Fake_leds` class |
| **Web Interface** | ⭐⭐⭐½ | No reconnection logic, dual source of truth for modes |
| **Playground / Research** | ⭐⭐⭐ | Logic duplication with core, large notebooks |
| **Documentation** | ⭐⭐⭐⭐ | Missing `requirements.txt` |

---

## Priority Action List

### 🔴 High Priority (correctness / stability)
1. **Fix `is_song_change` never resetting** — add `self.is_song_change = False` at the top of `detect_band_peaks()`.
2. **Add threading lock on `audio_data`** in `Local_Microphone` — prevents rare race-condition corruption.
3. **Add WebSocket reconnection** in `controlBridge.ts` — critical for live-show robustness.
4. **Fix spatial_images module-level I/O** in `Transition_Engine.py` — wrap in try/except to prevent import failures.

### 🟡 Medium Priority (performance / maintainability)
5. **Vectorize `update_leds`** in `Segment.py` — biggest frame-rate improvement available.
6. **Vectorize `asserv_fft_bands` and `asserv_total_power`** in `AudioIngestion.py`.
7. **Load simulator geometry from `segments.json`** instead of hardcoding in `Fake_leds.py`.
8. **Add `requirements.txt`** with all Python dependencies.

### 🟢 Low Priority (polish / cleanup)
9. **Remove duplicate JSON write** in `test_runner.py`.
10. **Remove `apply_fake_fft`'s `fft_bary`** computation — dead code.
11. **Remove `hasattr` guards** on `chroma_values` — initialize unconditionally in `__init__`.
12. **Run `nbstripout`** on playground notebooks before committing.
13. **Remove dead `execute_mode_swap` line** `self.is_in_transition = False`.
14. **Unify mode list source** between `constants/modes.ts` and `config/modes.json`.
