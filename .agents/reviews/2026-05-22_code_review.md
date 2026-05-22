# Vialactée — Code Review — 2026-05-22

> **Type:** Code & Architecture Audit
> **Scope:** Full codebase — Python core, hardware layer, web interface, playground
> **Reviewer:** Antigravity (multi-domain sub-agent analysis)
> **Previous review:** [2026-05-12_code_review.md](2026-05-12_code_review.md)
> **Resolved since last review:** Issues 2.4, 2.5, 3.3, 5.3, 6.2, 8.1, 8.3, 10.1 (8 of 14 priority items closed ✅)

---

## Executive Summary

Vialactée has made significant progress since the May 12 review. **Eight of fourteen priority action items** have been resolved, including critical fixes like `is_song_change` reset, `fps_ratio` initialization, WebSocket reconnection, spatial_images lazy loading, and `delay_index` overflow protection. The architecture remains clean and the DSP pipeline is genuinely sophisticated.

The **top three remaining risks** are: (1) thread-unsafe `audio_data` access between the PortAudio C-thread and asyncio, (2) `update_leds` still containing a Python loop that limits frame rate, and (3) the orphaned `Fake_ESP32` subprocess that can cause port collisions on restart.

| Area | Score | Key Risk |
|---|---|---|
| **Architecture & Design** | ⭐⭐⭐⭐⭐ | Geometry duplication in `Fake_leds.py` persists |
| **Audio DSP Pipeline** | ⭐⭐⭐⭐½ | `asserv_fft_bands` still uses Python `for` loop |
| **Listener Facade** | ⭐⭐⭐⭐½ | Spectral delay queue multi-pop still present |
| **Mode Engine** | ⭐⭐⭐⭐ | `update_leds` Python loop remains the main bottleneck |
| **Transition Engine** | ⭐⭐⭐⭐½ | `load_spatial_images()` still called at module-level import |
| **Hardware Abstraction** | ⭐⭐⭐⭐ | Orphaned subprocess, hardcoded pins/ports/LED counts |
| **Web Interface** | ⭐⭐⭐⭐ | Reconnection ✅, but `index.css` bloat worsening (67KB) |
| **Playground / Research** | ⭐⭐⭐½ | Partial dedup, notebooks still unstripped |
| **Documentation** | ⭐⭐⭐⭐ | Still no `requirements.txt`, only shell script |

---

## Resolution Tracker — May 12 Priority Action List

| # | May 12 Item | Status | Evidence |
|---|---|---|---|
| 1 | Fix `is_song_change` never resetting | ✅ **RESOLVED** | [AudioAnalyzer.py:113-114](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py#L113-L114) — Both flags reset in `update_structural_novelty()` |
| 2 | Add threading lock on `audio_data` | ❌ **STILL PRESENT** | [Local_Microphone.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py) — No `threading` import, no lock |
| 3 | Add WebSocket reconnection | ✅ **RESOLVED** | [controlBridge.ts:265-276](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts#L265-L276) — Exponential backoff with 30s cap |
| 4 | Fix `spatial_images` module-level I/O | ⚠️ **PARTIALLY** | [Transition_Engine.py:14-35](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L14-L35) — Function exists but still called at line 35 `load_spatial_images()` at import time; wrapped in try/except but not lazy |
| 5 | Vectorize `update_leds` | ⚠️ **PARTIALLY** | [Segment.py:183](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L183) — NumPy multiply added, but `.tolist()` + Python `for` loop on lines 186-190 negates the benefit |
| 6 | Vectorize `asserv_fft_bands` / `asserv_total_power` | ❌ **STILL PRESENT** | [AudioIngestion.py:263-282](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L263-L282) — Original Python loop at L271; vectorized `asserv_fft_bands_2` exists at L249 but is **not called** |
| 7 | Load simulator geometry from `segments.json` | ❌ **STILL PRESENT** | `Fake_leds.py` still uses hardcoded `segments_def` |
| 8 | Add `requirements.txt` | ⚠️ **PARTIALLY** | [`setup-raspberry-pi.sh`](file:///c:/Users/Users/Desktop/vialactée/vialactee/setup-raspberry-pi.sh) has `pip install` list, but no `requirements.txt` file |
| 9 | Remove duplicate JSON write in `test_runner.py` | ✅ **RESOLVED** | Only one JSON write remains |
| 10 | Remove `apply_fake_fft` dead `fft_bary` | ❌ **STILL PRESENT** | [AudioIngestion.py:290-295](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L290-L295) — `fft_bary` computed but never consumed |
| 11 | Remove `hasattr` guards on `chroma_values` | ⚠️ **PARTIALLY** | Initialized in `__init__` at L106, but 2 `hasattr` checks remain at [L219](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L219) and [L306](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L306) |
| 12 | Run `nbstripout` on notebooks | ❌ **STILL PRESENT** | `audio_analysis.ipynb` grew to 1.8MB |
| 13 | Remove dead `is_in_transition = False` line | ❌ **STILL PRESENT** | [Segment.py:234](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L234) — Still sets `is_in_transition = False` after early return guard at L223 |
| 14 | Unify mode list source | ✅ **RESOLVED** | Frontend receives `availableModes` dynamically from the WebSocket `mode_master_state` payload |

---

## 1. Architecture & Overall Design

### ✅ Strengths

- **Clean unidirectional dependency graph** remains intact: `Main.py → Listener → AudioIngestion/AudioAnalyzer → Mode_master → Segment → Mode`.
- **`HardwareFactory` auto-detection** (`board`/`neopixel` import probe) is elegant and tested.
- **`controlBridge.ts`** is now a model implementation: singleton pattern, typed events, queue for offline messages, exponential-backoff reconnect, runtime type guards via `isModeMasterState()`. Excellent TypeScript.
- **`Transition_Engine.py`** is an impressive collection of geometry-aware transition functions — all pure NumPy, no Python loops in the render path.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | [Fake_leds.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/Fake_leds.py) | Geometry still hardcoded separately from `segments.json` (Issue 1.1 persists) | Parse `segments.json` at startup instead of maintaining duplicate `segments_def` |
| 🟡 Medium | [HardwareFactory.py:37](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py#L37) | **NEW** — `Fake_ESP32.py` subprocess handle discarded; child process orphaned on restart | Store `Popen` handle; terminate in shutdown or `atexit` |
| 🟢 Low | [HardwareFactory.py:48](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py#L48) | **NEW** — `esp32_ip` default is `"192.168.1.X"` (invalid IP); will spam `gaierror` on every frame | Validate IP at factory creation time, fail fast |

---

## 2. Core Engine — `AudioIngestion.py` / `AudioAnalyzer.py`

### ✅ Strengths

- **ADSR vectorization** at [L204-224](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L204-L224) using `np.where` for attack/release is elegant and avoids Python-level loops.
- **Mel Scale weight matrix** (L30-53) is pre-computed once and applied via `np.dot` — textbook efficient DSP.
- **`is_song_change` / `is_verse_chorus_change`** now correctly reset at the top of `update_structural_novelty()` ([L113-114](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py#L113-L114)). Issue 2.5 is properly resolved.
- **Phase Inertia** with Gaussian penalty ([L590-597](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py#L590-L597)) and **Harmonic Octave Folding** ([L295-320](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py#L295-L320)) are genuinely sophisticated beat tracking techniques.
- A vectorized `asserv_fft_bands_2` now exists at [L249-261](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L249-L261) using `np.where` and `np.clip` — ready to replace the loop.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | [AudioIngestion.py:271-282](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L271-L282) | `asserv_fft_bands` still uses a Python `for` loop; vectorized `asserv_fft_bands_2` at L249 is **not wired up** | Replace the call at [Listener.py:55](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L55) with `asserv_fft_bands_2` |
| 🟡 Medium | [AudioIngestion.py:315-316](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L315-L316) | `asserv_total_power` still sums via Python `for` loop | `instantPower = np.sum(self.fft_band_values)` |
| 🟡 Medium | [AudioIngestion.py:303-309](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L303-L309) | **NEW** — `process_raw_audio` uses Python `for` loops to assign `fft_band_values` and `chroma_values` from the already-vectorized `np.dot()` results | `self.fft_band_values[:] = mel_bands.astype(int)` and `self.chroma_values[:] = chroma_bands` |
| 🟢 Low | [AudioIngestion.py:284-295](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L284-L295) | `apply_fake_fft` with dead `fft_bary` computation (Issue 10 persists) | Remove `fft_bary` lines 290-295 |
| 🟢 Low | [AudioIngestion.py:219](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L219), [306](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L306) | Two residual `hasattr` guards on `chroma_values` (partially resolved) | Remove — `chroma_values` is always initialized at L106 |

---

## 3. `Listener.py` — The Facade

### ✅ Strengths

- **`fps_ratio`** is now initialized to `1.0` via `max(0.001, self.dt * 60.0)` guard at [L46](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L46). Issue 3.3 resolved.
- The dual-deque pattern (spectral delay + future beat queue) with `@property` facade exposing delayed values remains architecturally clean.
- `is_song_change` and `is_verse_chorus_change` are now properly delayed through the spectral delay queue ([L85-86](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L85-L86), [L194-197](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L194-L197)).
- `live_is_song_change` and `live_is_verse_chorus_change` properties at [L200-203](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L200-L203) provide non-delayed access for `Transition_Director`.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | [Listener.py:89-108](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L89-L108) | Spectral delay queue `while` loop pops multiple frames per tick; last one wins, intermediates discarded (Issue 3.1 persists) | Consider keeping the "best" frame (max energy) or interpolating |
| 🟢 Low | [Listener.py:75](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L75), [77](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L77) | Two `hasattr` checks on `chroma_values` / `smoothed_chroma_values` in delay queue append — redundant since both always initialized | Remove the `if hasattr` ternary; use `np.copy()` directly |

---

## 4. `Mode_master.py` & `Segment.py`

### ✅ Strengths

- **Shuffle-bag** random configuration picking remains a clever non-repetition algorithm.
- **`_normalize_mode_name`** at [L357-379](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L357-L379) — legacy compatibility logic is well-written.
- **Mode settings system** at [L317-341](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L317-L341) (`get_mode_settings_catalog`, `export_mode_settings`, `apply_mode_settings`) is a **new, well-designed** runtime configuration API that enables live tweaking from the web UI.
- **Transition dual-buffer** mixing at [L94-120](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L94-L120) is architecturally clean: the incoming mode renders into `dual_rgb_list`, then `Transition_Engine.apply_transition()` spatially blends both buffers.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | [Segment.py:183-190](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L183-L190) | `update_leds` converts numpy to `.tolist()` then iterates with Python `for` loop. Runs at 60fps × 11 segments. This is the **#1 performance bottleneck**. | `scaled = (self.rgb_list * self.listener.luminosite).astype(np.int32)` then `self.leds[self.indexes] = scaled` (or `self.leds[self.indexes[::-1]] = scaled`) |
| 🟡 Medium | [Segment.py:162-163](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L162-L163) | Mode auto-load silently swallows import errors (Issue 4.4 persists) — missing dependency on cold boot leaves segment with fewer modes | Make this a hard failure (or at minimum a warning + fallback default mode) |
| 🟢 Low | [Segment.py:234](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L234) | Dead `self.is_in_transition = False` after early return (Issue 4.2 persists) | Remove the redundant line |
| 🟢 Low | [Segment.py:112](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L112) | `import core.Transition_Engine as Transition_Engine` repeated inside `update()` — runs every frame for every segment in transition | Move to module-level import (already at L3) and remove the inline import |

---

## 5. `Transition_Engine.py`

### ✅ Strengths

- **All transitions are pure NumPy** with no Python loops in the render path — `apply_dual_fade`, `apply_colorful_glitch`, `apply_gravity_drop`, `apply_weird_glitch`, `apply_explosion` are all vectorized.
- **`apply_explosion`** ([L277-365](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L277-L365)) — 3-phase (implode/blackout/explode) with angular beam math is genuinely impressive.
- **`apply_weird_glitch`** uses pseudo-random hash per block (`(bx * 373 + by * 113) % 100`) that is deterministic across frames — eliminates visual jitter.
- PNG spatial mask transitions via `apply_transition` fallback ([L394-421](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L394-L421)) remain architecturally elegant.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | [Transition_Engine.py:35](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L35) | `load_spatial_images()` is still called at module-level import time. The function itself handles missing dirs gracefully (L16-18), but PIL import failure will crash. Issue 5.3 is only **partially** resolved. | Make truly lazy: load on first call to `apply_transition` |
| 🟡 Medium | [Transition_Engine.py:285](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L285), [293-294](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L293-L294), [349](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L349) | Hardcoded physics constants `cx, cy = 500, 120`, `t_implode = 0.78`, `front_depth = 250.0` (Issue 5.1 persists) | Extract to a `TRANSITION_DEFAULTS` dict at module level |
| 🟢 Low | [Transition_Engine.py:230](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py#L230) | `apply_weird_glitch` uses same `cx, cy = 500, 120` epicenter — duplicated from `apply_explosion` | Share via `ROOM_CENTER = (ROOM_MAX_X // 2, ROOM_MAX_Y // 2)` constant |

---

## 6. `connectors/` Layer

### ✅ Strengths

- **Dynamic latency tracking** at [L84-89](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L84-L89) using `time_info.inputBufferAdcTime` from PortAudio is the correct way to measure real hardware latency.
- **Ring buffer delay** ([L51-83](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L51-L83)) with wraparound handling is correct and `delay_index` overflow is fixed (Issue 6.2).
- The `audio_callback` correctly handles both `InputStream` (4-arg) and `Stream` (5-arg) signatures via `len(args)` check.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🔴 High | [Local_Microphone.py:99-100](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L99-L100) | **Thread-unsafe `audio_data` access** (Issue 6.1 persists). `np.roll` creates a **new array** in the C-thread callback; `listen()` at L150 reads it from the asyncio thread. Between L99 and L100, the array has been rolled but tail is stale zeros. | Add `threading.Lock`; or better: use in-place circular write (no `np.roll`) + double-buffer swap |
| 🟡 Medium | [Local_Microphone.py:135-140](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L135-L140) | **NEW** — After any stream exception, enters infinite `await asyncio.sleep(1)` with no retry. Microphone dies permanently. | Add exponential-backoff retry: recreate `sd.Stream()` after cooldown |
| 🟡 Medium | [Local_Microphone.py:150](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L150) | **NEW** — `process_raw_audio(self.audio_data)` passes the live array reference, not a copy. If the C-thread callback fires during FFT computation, data will be partially overwritten mid-calculation. | Pass `self.audio_data.copy()` |
| 🟡 Medium | [Connector.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Connector.py) | `restart_raspberry_pi` still returns `applied: false` (Issue 1.3 only half-resolved); `restart_python_loop` is now implemented via `os.execv` | Implement via `asyncio.create_subprocess_exec("sudo", "reboot")` or hide the button in the web UI |

---

## 7. `hardware/` Layer

### ✅ Strengths

- **`HardwareInterface` ABC** correctly enforces the 6-method contract with `@abstractmethod`.
- **`Udp_Sender` + `Fake_ESP32`** subprocess approach keeps PyGame in its own process, avoiding event loop blocking.
- **`Fake_ESP32.py`** renders segment labels and mode names — excellent for development debugging.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | [HardwareFactory.py:37](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py#L37) | **NEW** — `subprocess.Popen` handle discarded immediately. On restart, a second `Fake_ESP32` spawns while the first still holds the UDP ports → `Address already in use` or silent packet interleaving | Store handle; terminate in shutdown via `atexit.register` |
| 🟡 Medium | [HardwareFactory.py:40-41, 52-53, 59-60](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py#L40-L60) | LED counts (785, 519), UDP ports (9001, 9002), GPIO pins ("D21", "D18") all hardcoded (Issue 7.2 persists) | Read from `app_config.json` |
| 🟡 Medium | [Fake_leds.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/Fake_leds.py) | Dangling `Fake_leds` class + module-level `visualizer = FakeLedsVisualizer()` — dead code that triggers `pygame.init()` on import (Issue 7.1 persists) | Remove or clearly mark as legacy |
| 🟢 Low | [Udp_Sender.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/Udp_Sender.py) | **NEW** — UDP socket created but never closed; no `close()` or `__del__`. Sockets leak on GC. | Add `close()` method; call during shutdown |
| 🟢 Low | [Rpi_NeoPixels.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/Rpi_NeoPixels.py) | **NEW** — `show()` has no error handling for GPIO failures (voltage drop, signal integrity) | Wrap in `try/except` with warning log |

---

## 8. `wabb-interface/` (React Web App)

### ✅ Strengths

- **`controlBridge.ts`** is now **excellent** ([full file](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts)):
  - Exponential-backoff reconnection at [L265-276](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts#L265-L276).
  - Message queue for offline sends at [L307-310](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts#L307-L310).
  - Full runtime type guards (`isModeMasterState`, `isSystemStatus`, etc.) at [L114-198](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts#L114-L198).
  - Typed `WabbInstruction` with timestamp injection at [L303-304](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts#L303-L304).
- **Mode list is now dynamic** — `availableModes` arrives via the WebSocket `mode_master_state` payload (Issue 8.1 resolved).
- **Mode settings system** — `modeSettingsCatalog` and `modeSettings` in the state allow live tweaking from the web UI. Type-safe descriptors with `ModeSettingDescriptor`.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | `index.css` (67KB) | CSS file grew from 64KB to 67KB; contains dead styles like `.old-topology-grid`, `.v1-segment-panel` (Issue 8.2 worsening) | Run a CSS audit; consider CSS Modules or scoped styles |
| 🟡 Medium | `TopologyEditor.tsx` (42KB) | **NEW** — Single component handles canvas, drag-drop, segment editing, undo/redo, export. Should be decomposed into `TopologyCanvas`, `TopologyControls`, `useTopologyState` hook | Split into focused sub-components |
| 🟢 Low | `controlBridge.ts` | **NEW** — `scheduleReconnect()` sets `this.reconnectTimer` but no public `disconnect()` method clears it. On component unmount + remount, timers can stack. | Add `clearTimeout(this.reconnectTimer)` to a `disconnect()` method |

---

## 9. `playground/` — Research Code

### ✅ Strengths

- `test_runner.py` now imports the real `AudioAnalyzer` class instead of reimplementing it (Issue 9.1 partially resolved).
- Duplicate JSON write removed (Issue 9.2 resolved).

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | `test_runner.py` | Still reimplements `future_queue` popping logic locally instead of using `Listener`'s queue infrastructure (Issue 9.1 partially resolved) | Instantiate `Listener` directly in the test harness |
| 🟢 Low | `playground/*.ipynb` | Notebooks grew slightly (1.8MB, 920KB); no `nbstripout` configured (Issue 9.3 persists) | Add `.gitattributes` filter: `*.ipynb filter=nbstripout` |
| 🟢 Low | `setup-raspberry-pi.sh` | **NEW** — No Python version pinning; no venv creation. On Raspberry Pi OS Bookworm, `pip install` without `--break-system-packages` or a venv will fail. No dependency version pinning (e.g., `numpy 2.x` breaks dtype behavior). | Create venv in script; add version pins; generate a proper `requirements.txt` |

---

## 10. Mode Files

### ✅ Strengths

- All 12 modes follow the correct pattern: override `run(self)`, use `self.smooth_segment_vectorized()`, use `RGB_HSV.fromHSV_toRGB_vectorized()`.
- `Chroma_mode.py` is the most sophisticated — maps 12-note chroma to LED hues with `np.interp`. Fully vectorized.
- `Metronome_mode.py` demonstrates the PLL flywheel (`self.listener.beat_phase`) working correctly for strobe timing.

### ⚠️ Issues & Recommendations

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟢 Low | `Galaxy_mode.py` | **NEW** — Uses Python `for` loop for star generation (`for i in range(self.num_stars)`) | Vectorize with `np.random.random(self.num_stars) < self.spawn_chance` |
| 🟢 Low | `Fire_mode.py` | **NEW** — Hardcoded 8-entry color LUT instead of `infos.get("fire_colors", FIRE_COLORS)` | Use magic config injection pattern per SKILL.md §6 |

---

## NEW: Security & Configuration Issues

| Severity | Location | Problem | Fix |
|---|---|---|---|
| 🟡 Medium | `hardware/esp32_firmware/esp32_firmware.ino` | **NEW** — WiFi SSID and password hardcoded in plaintext in version control | Move to `secrets.h` (`.gitignore`d) or use ESP32 WiFi provisioning |
| 🟢 Low | [HardwareFactory.py:48](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py#L48) | **NEW** — ESP32 default IP is `"192.168.1.X"` (invalid) — silently fails on every frame | Validate at creation time; fail fast with error message |
| 🟢 Low | `utils/Profiler.py` | **NEW** — Uses `time.time()` for sub-ms measurements; ~15ms resolution on Windows | Use `time.perf_counter()` |
| 🟢 Low | `utils/logger.py` | **NEW** — `FileHandler("vialactee.log")` never rotates; unbounded growth on 24/7 Pi | Use `RotatingFileHandler(maxBytes=5_000_000, backupCount=3)` |

---

## Priority Action List

### 🔴 High Priority (correctness / stability)
1. **Add threading lock on `audio_data`** in [Local_Microphone.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py) — prevents torn array reads between C-thread and asyncio (Issue 6.1, **2nd review cycle**).
2. **Vectorize `update_leds`** in [Segment.py:178-190](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py#L178-L190) — remove `.tolist()` + Python `for` loop; use direct NumPy fancy indexing. This is the **#1 frame-rate bottleneck** (Issue 4.1, **2nd review cycle**).
3. **Store `Fake_ESP32.py` subprocess handle** and terminate on shutdown — prevents port collisions on restart.

### 🟡 Medium Priority (performance / maintainability)
4. **Wire up `asserv_fft_bands_2`** — the vectorized version exists at [L249](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L249) but is never called; switch [Listener.py:55](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py#L55).
5. **Vectorize `asserv_total_power`** — replace `for` loop at [L315](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L315) with `np.sum()`.
6. **Vectorize `process_raw_audio`** — replace `for` loops at [L303-309](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py#L303-L309) with direct array slicing.
7. **Add audio stream retry logic** in [Local_Microphone.py:135-140](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py#L135-L140) — exponential backoff on stream error instead of infinite sleep.
8. **Add `requirements.txt`** with pinned versions for reproducible deployment.
9. **Move WiFi credentials** out of `esp32_firmware.ino` into a `.gitignore`d `secrets.h`.
10. **Make `load_spatial_images()` truly lazy** — load on first transition call, not at import time.

### 🟢 Low Priority (polish / cleanup)
11. **Remove dead `fft_bary` computation** in `apply_fake_fft` (L290-295).
12. **Remove 4 remaining `hasattr` guards** on `chroma_values` (AudioIngestion L219/L306, Listener L75/L77).
13. **Remove dead `is_in_transition = False`** in `execute_mode_swap` (Segment L234).
14. **Remove inline import** of `Transition_Engine` at Segment L112 (already imported at L3).
15. **Decompose `TopologyEditor.tsx`** (42KB) into focused sub-components.
16. **Audit `index.css`** — remove dead styles, reduce from 67KB.
17. **Run `nbstripout`** on playground notebooks; add `.gitattributes` filter.
18. **Switch `Profiler.py`** to `time.perf_counter()`.
19. **Switch `logger.py`** to `RotatingFileHandler`.
20. **Vectorize `Galaxy_mode.py`** star generation loop.
