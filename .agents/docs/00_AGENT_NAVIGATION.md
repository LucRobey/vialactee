# Agent Navigation Guide

## 🤖 Directives for Future AI Agents
Welcome to the *Vialactée* lighting orchestration system! If you are an AI reading this file, you have been summoned to help build, debug, or expand the Python-based reactive lighting architecture. 

This `.agents/docs/` folder contains the canonical "Brain Trust" of the project's logic. Before proposing structural changes to the codebase, please review the relevant markdown files below to ensure your code aligns with our established mathematical frameworks.

---

## 📂 Directory Map

### 🎧 1. Musical Perception & Rhythm Tracking
These documents map out the **Audio Input Layer**. They describe how raw waveforms are processed into a stable rhythm, and how macro structure (Verses, Drops, Song Changes) are mathematically perceived through Short-Term Memory (STM) and Long-Term Memory (LTM).

- **`rhythm_tracker_architecture.md`** 
  *Read this to understand:* The **Phase Inertia Flywheel**. It explains how we track BPM using continuous non-causal phase sweeping over an ODF array, and how we smoothly snap to targets to eliminate latency jitter without fighting internal beat bounces.

- **`bpm_trust_architecture.md`**
  *Read this to understand:* The **BPM Trust Engine**. How the system decides whether to lock onto the current tempo, engage polyrhythmic jailbreaks, or fall back to recent historic tempos.
  
- **`music_events_architecture.md`**
  *Read this to understand:* **Structural Boundaries**. How Timbre (Euclidean distance) and Power (relative normalization) are combined into a "Novelty Score" to detect Verse/Chorus changes, DJ crossfades, and hard song cuts. Features the exact thresholding logic.

### 💡 2. Lighting Transitions & Director Orchestration
These documents map out the **Output Layer**. Once the Rhythm Tracker detects an event (like a drop or a song change), how does the system gracefully transition the LEDs without looking like rigid, predictable presets?

- **`transition_architecture.md`**
  *Read this to understand:* The **Transition Director** and the **Spatial Execution** of transitions. The probabilistic engine that listens to song energy and decides *what kind* of transition to trigger (Global vs Local), and how to stagger transitions physically based on physical X/Y coordinates and Aesthetic Sets.

- **`../core/precisions/transition_director.md`**
  *Read this to understand:* The internal state machine and operational flowchart of the **Transition Director**.

### 🌐 3. External Interfaces & Control
- **`../wabb-interface/README.md`**
  *Explore this document to understand:* The **React Web App** (`wabb-interface`). This web page acts as the remote controller, detailing the communication protocol used to push commands to the Raspberry Pi.

### 💻 4. Hardware Abstraction
- **`../hardware/README.md`**
  *Read this to understand:* The **Simulation and Networking Layer**. How Vialactée abstracts the Pygame simulation, physical Raspberry Pi GPIOs, and the ESP32 UDP driver logic.
---

## 📌 Agent Instructions Formatter
Whenever updating the codebase, ensure that:
1. **Math Must Be Frame-Independent:** All smoothing, decays, and timers must be driven by `self.fps_ratio` or `delta_time` (e.g., `decay_rate ** self.fps_ratio`) so physics remain stable regardless of hardware stutters. Performance intensive operations (like ODF sweeps) happen efficiently and infrequently (e.g. at 5Hz instead of 60Hz).
2. **Lighting Events Must Respect Cooldowns:** Adhere strictly to the **20s Cooldown** rules established in `music_events_architecture.md` to prevent chaotic flashing. 
3. **Do not break the Flywheel!** Keep phase-shifting logic completely decoupled from the real-time audio framerate push.
4. **Environment & Configuration:** Never hardcode configuration dictionaries (e.g., `infos`) directly in code. Always load from `config/app_config.json` and gracefully generate defaults if missing. Understand the `HARDWARE_MODE` setting (simulation vs production). Hardware dependencies (like `board` or `neopixel`) must be imported dynamically using `try/except ImportError` blocks (see `HardwareFactory.py`) to maintain seamless code portability between Windows simulation and Raspberry Pi.
5. **Asynchronous Architecture:** Main orchestration must use Python 3.10 compatible supervisors (e.g., `asyncio.wait` with `FIRST_COMPLETED`) instead of 3.11+ exclusive `TaskGroup` to guarantee graceful crashes and clean module shutdowns across legacy Pi hardware.
6. **Performance Profiling:** When adding heavy operations to the execution loop, wrap them using the existing context manager (e.g., `with mode_master.profiler.measure("feature_name"):` or `self.profiler` if inside `Mode_master`) instead of dropping unreadable procedural timing code everywhere.
