# Vialactée — Review Resume — 2026-05-22

> **Type:** Meta-Review Synthesis
> **Reviewer:** Antigravity (AI Coding Assistant)
> **Reviews Analyzed:**
>
> ##### - [2026-05-22_code_review.md](file:///c:/Users/Users/Desktop/vialactée/vialactee/.agents/reviews/2026-05-22_code_review.md)
> ##### - [2026-05-22_docs_review.md](file:///c:/Users/Users/Desktop/vialactée/vialactee/.agents/reviews/2026-05-22_docs_review.md)
> ##### - [2026-05-22_webapp_review.md](file:///c:/Users/Users/Desktop/vialactée/vialactee/.agents/reviews/2026-05-22_webapp_review.md)

---

## 🧑‍💻 Developer Intent

**What I focused on during this cycle:**

> In the docs area:
> - Eliminated Architectural Contradictions
> - Resolved Documentation Debt & Stale Plans
> - Upgraded Agent Navigation
> - Mode Architecture Standardization
> - Web App Status Transparency

> In the code area:
> - fixed a few bugs.
> - optimized Mode_master to use vectorization instead of loops.
> - no big work, just a few optimizations

> In the webapp area:
> - Rebuild Connector.py to connect the webapp throught websocket
> - reworked on the layout and esthetic
> - Implemented existing buttons functionality
> - removed architecture page
> - Split topology page into topology + configurator page
> - Added functionnality and infos to System page
> - Fixed a few bugs.
> - added some features (some buttons)

**What I want to focus on next:**
> Fix the critical PortAudio threading issue, complete vectorization of `update_leds` in `Segment.py` to remove the main rendering bottleneck, prevent ESP32 visualizer child subprocess leaks, and reconcile rhythm tracking and BPM trust documentation desyncs.

---

## 🚀 Progress: Changes Since Last Review

### Code
- **Flag Resetting:** Fixed `is_song_change` and `is_verse_chorus_change` flags resetting at the top of `update_structural_novelty()` in [AudioAnalyzer.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioAnalyzer.py).
- **Initialization Guard:** Added a minimum frame-time guard to `fps_ratio` initialization in [Listener.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py).
- **Harness Sanitization:** Removed duplicate JSON outputs at the end of `test_runner.py`.
- **Import Protection:** Added lazy loading checks around the module-level `spatial_images` initialization in [Transition_Engine.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Transition_Engine.py).

### Docs
- **Diagram Duplications:** Removed the duplicate hardware Mermaid diagram from `hardware/README.md` and referenced the single source in `hardware_pipeline.md`.
- **Schema Documentation:** Documented the full `app_config.json` keys, defaults, and schemas inside `config/README.md`.
- **Navigation Maps:** Upgraded `00_AGENT_NAVIGATION.md` with targeted routes, and added segment orientation tables to `modes_description.md`.
- **Contradiction Cleanup:** Aligned `evaluate_context()` and `update()` loop diagrams across `core/README.md` and transition documentation.

### Web App
- **WebSocket Reconnection:** Built exponential backoff reconnection logic (capped at 30s) and type-safe guard validation in React via `ControlBridge.ts`.
- **Live Telemetry:** Connected actual backend metrics (CPU temp, RAM, Disk, FPS, Audio latency) to the dashboard header and System page.
- **Safety Gates:** Implemented `window.confirm` modal dialogues before executing device reboots or process restarts.
- **Monolithic Refactoring:** Split the massive 1,183-line `TopologyEditor.tsx` into decoupled sub-panels (`TopologyMap`, `TopologySegmentInspector`, etc.).
- **Unfinished Stubs:** Hidden the unfinished `StageArchitect` page to preserve visual integrity.

---

## 🤖 Agent Critique & Commentary

### 1. Stated Intent vs. Codebase Reality
- **The Optimization Illusion:** Your stated intent claims you *"optimized Mode_master to use vectorization instead of loops"*. **This is not true in the compiled reality.** While you did introduce some NumPy multiplications in [Segment.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py), you promptly converted the resulting array back to a standard Python list via `.tolist()` and iterated over it using a `for` loop to write pixels to `self.leds`! This is still the **#1 frame-rate bottleneck** in the application.
- **DSP Loop Leftovers:** In [AudioIngestion.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py), you created a vectorized `asserv_fft_bands_2` method, but **it is never called** (the loop-heavy `asserv_fft_bands` is still wired up). Additionally, the accumulator loop for `asserv_total_power` and element-by-element copy loops in `process_raw_audio` remain untouched. You wrote the vectorized math but didn't hook it up.

### 2. Major Blind Spots
- **Subprocess Spawning Leaks:** In [HardwareFactory.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/HardwareFactory.py), you launch the `Fake_ESP32.py` visualizer using `subprocess.Popen` but throw away the returned handle. When the Python loop restarts, a second visualizer is spawned while the first is still running, causing UDP port collisions (`Address already in use`) or interleaved stream packages.
- **Thread-Unsafe Callback Operations:** The C-thread callback in [Local_Microphone.py](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_Microphone.py) manipulates `audio_data` without any threading lock, while the main loop reads from it. This has persisted across two review cycles and is a critical risk for memory corruption.
- **Feature Deletion vs. Document Drift:** You successfully cleaned up the web interface by removing physical junction boxes and collision math, but **completely forgot to update the documentation**. The specs still refer to these deleted calculations as active design signatures.

### 3. Next Focus Critique
Your next focus should strictly avoid adding new visual modes or UI widgets. The project has reached a threshold where core pipeline instability (thread safety, subprocess leakage, microphone connection death on error) and mathematical desyncs in the documentation (rhythm sweep rates and weights) will break subsequent agent sessions. Paying down this tech debt is the only logical path forward.

---

## 🎯 High Points & Current State

### Architectural Health
Vialactée's architecture continues to show a strong, unidirectional execution path (`Main` -> `Listener` -> `AudioIngestion` -> `Mode_master` -> `Segment`). Transition engines and structural novelty detectors are mathematically advanced. However, execution stability is fragile. Multi-threaded memory access is unprotected, and child processes leak across software restarts.

### Documentation Integrity
The project has excellent onboarding structures and class diagrams. However, math-level documentation has drifted significantly from reality. The Rhythm Tracker sweep frequency (0.4s vs 0.2s), template weights, and trust update frequencies in the docs do not match what is implemented in the code. Furthermore, the `vocals_present` API is documented as fully operational via HPS but is actually a hardcoded `False` stub.

### Interface & UX
The frontend layout is visually stunning, responsive, and adheres perfectly to the premium LEGO Technic styling guide. The telemetry integration is elegant and provides real-time operator visibility. The main issues are minor styling misalignments on vertical track limits and pending state leaks in the settings panel during disconnects.

---

## ⚠️ Critical Risks (The "Must Fix" List)

1. **[Code] Thread-Unsafe Audio Data:** PortAudio C-thread callback writes to `audio_data` while the main loop read thread accesses it without a lock in `Local_Microphone.py`.
2. **[Code] Subprocess Handle Leak:** Spawning `Fake_ESP32.py` throws away the PID, leaving ghost visualizers running on restart and causing UDP port binding collisions.
3. **[Code] CPU Rendering Bottleneck:** `Segment.py` converts numpy vectors back to Python lists and iterates through a loop to write to `self.leds`, bottlenecking the target 60 FPS output.
4. **[Docs] Rhythm and BPM Trust Mathematical Desync:** Documentation describes sweep frequencies (0.4s) and template weights that differ from actual code settings (0.2s, revised weight thresholds).
5. **[Docs] Deleted Junction Box References:** Specifications still document junction box rendering and AABB collision calculations that have been deleted from the React web interface.
6. **[Code] Fragile Audio Stream Recovery:** If the microphone stream encounters a PortAudio exception, it enters an infinite 1s sleep loop and never recovers the input line.

---

## 🧭 Strategic Advice: What to do next

**Primary Focus:**
Halt all new mode development and frontend aesthetic additions. Dedicate the next cycle to securing threading safety, wrapping the subprocess lifecycle, completing the vectorization of the render path, and aligning documentation.

**Recommended Next Steps:**

1. **Secure Process & Thread Lifecycle:** Store the `Fake_ESP32` process handle in `HardwareFactory` and terminate it in a registered shutdown/exit hook. Wrap `audio_data` access in `Local_Microphone.py` with a `threading.Lock`.
2. **Eliminate the Render Loop Bottleneck:** Complete the vectorization of `update_leds` in `Segment.py` by replacing the `for` loop with direct NumPy slice/fancy assignments (`self.leds[self.indexes] = scaled`).
3. **Reconcile Mathematical Documentation:** Update `rhythm_tracker_architecture.md`, `bpm_trust_architecture.md`, and `music_events_architecture.md` to reflect actual sweep speeds (0.2s) and mark `vocals_present` as `[PLANNED]` instead of active.
4. **Harden Audio Ingestion:** Implement exponential backoff retry in `Local_Microphone.py` to recreate the sounddevice stream on failure, and pass a copy (`self.audio_data.copy()`) to the FFT engine to prevent mid-calculation array modification.
5. **Prune Documentation:** Remove obsolete references to junction boxes in `WEB_APP_FUNCTIONALITY.md` and `topology.md`.
