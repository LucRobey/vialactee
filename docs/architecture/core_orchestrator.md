# Core Orchestrator Architecture (`core/`)

> **Location:** `docs/architecture/core_orchestrator.md` (Tier 1 Canonical Specification)  
> **Source Directory:** [`core/`](../../core/)  
> **Related Contracts:** [`docs/contracts/transition_contract.md`](../contracts/transition_contract.md), [`docs/contracts/mood_contract.md`](../contracts/mood_contract.md), [`docs/contracts/music_analyzer_contract.md`](../contracts/music_analyzer_contract.md), [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-03](../axioms/AXIOM-03_HARDWARE_GEOMETRY.md), [AXIOM-07](../axioms/AXIOM-07_CODE_GOVERNANCE.md)

The `core/` directory is the central runtime orchestrator of Vialactée. It drives the 30 FPS asynchronous render loop, bridges the sealed `music/`, `mood/`, and `transitions/` sectors into per-segment visual rendering (`modes/`), routes WebSocket commands, and manages live configuration persistence.

---

## 1. Core Components Overview

| Module | Role & Responsibilities |
| :--- | :--- |
| [`core/Mode_master.py`](../../core/Mode_master.py) | Master orchestrator. Instantiates `Segment` objects, owns the `mood.api.MoodService` and `TransitionBridge`, runs the `asyncio` 30 FPS render loop (`run()`), pushes pixels to hardware channels, and broadcasts throttled WebSocket state updates. |
| [`core/Segment.py`](../../core/Segment.py) | Represents one physical LED segment on the chandelier. Dynamically loads all 21 modes from `config/modes.json`, pre-allocates primary and secondary RGB frame buffers, executes dual-mode transition blending via `transitions.api.TransitionService.blend()`, and writes final RGB bytes into the hardware strip. |
| [`core/TransitionBridge.py`](../../core/TransitionBridge.py) | Thin adapter between `Mode_master`/`Segment` and the sealed [`transitions/`](../../transitions/) sector (`transitions.api`). Builds `InstallationSnapshot` and `MusicSnapshot` payloads, forwards operator requests, applies `TransitionOrders` across segments, and returns `OrderAck`. |
| [`core/CommandRouter.py`](../../core/CommandRouter.py) | Declarative async dispatch table routing incoming WebSocket instruction frames (`action`) from [`connectors/Connector.py`](../../connectors/Connector.py) to `Mode_master`, `MoodService`, `TransitionBridge`, and `AppConfigStore`. |
| [`core/AppConfigStore.py`](../../core/AppConfigStore.py) | Debounced, atomic JSON persistence manager for `config/app_config.json` (`luminosity`, `sensibility`, `auto_transition_time`, and per-mode `mode_settings`). |
| [`core/Webapp_instruction_logger.py`](../../core/Webapp_instruction_logger.py) | Structured console logger that prints color-coded summaries of incoming Web UI commands and parameter updates. |

---

## 2. `Mode_master` (`core/Mode_master.py`)

### 2.1 Initialization & Boot Sequence
During `Mode_master.__init__(leds_list, infos, listener)`:
1. **Mood Binding:** Creates the mood front door via `mood.api.create_mood_service(auto_scene=True)` and binds its shared read-only `(4, 3)` `int32` color buffer (`Mode.bind_mood_colors`) and 4-float modifier buffer (`Mode.bind_mood_modifiers`) onto the `Mode` base class.
2. **Segment Construction (`create_segments()`):**
   - Resolves the active topology file (`config/segments_full.json` or `config/segments_small.json`) via `Configuration_manager.resolve_segments_file_path(infos)`.
   - Instantiates a `Segment` per strip definition, assigning it to hardware channel 1 (`leds_list[0]`) or channel 2 (`leds_list[1]`).
   - Attaches normalized 2D spatial coordinate arrays `(nb_leds, 2)` via `Configuration_manager.get_segment_coordinates(infos)` for global spatial transitions.
3. **Startup Randomization (`_randomize_initial_segment_modes()`):**
   - There are no static preset or playlist files. On boot, each segment starts from a random mode compatible with its orientation (`vertical` vs `horizontal`) and a random direction (`UP` or `DOWN`).
4. **Persisted Mode Settings:**
   - Loads any saved per-mode overrides from `infos["mode_settings"]` (validated via `Mode.normalize_setting_value()`) and applies them across all segment mode instances.
5. **Transition Bridge Setup:**
   - Instantiates `TransitionBridge(self, infos)` and registers the initial `InstallationSnapshot`.

### 2.2 The 30 FPS Main Loop (`Mode_master.run()`)
Each tick of `Mode_master.run()` executes at a target cadence of **30 FPS** (`1/30 s` frame period, governed by [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md)):

```mermaid
sequenceDiagram
    participant Loop as Mode_master.run()
    participant Listener as music/Listener
    participant Mood as mood.api.MoodService
    participant Bridge as core/TransitionBridge
    participant Seg as core/Segment (x11)
    participant HW as Hardware Driver

    Loop->>Listener: Read delayed audio & MusicalContext (T_speaker)
    Loop->>Mood: update(dt, MoodMusicSnapshot)
    Mood-->>Loop: Mutates shared Mode._mood_colors & Mode._mood_modifiers in place
    Loop->>Bridge: tick() -> TransitionService.update(dt, MusicSnapshot)
    opt Transition Triggered
        Bridge->>Mood: apply_orders(PaletteRequest)
        Bridge->>Seg: apply_orders(SegmentOrder) -> start_transition()
        Bridge-->>Bridge: acknowledge(OrderAck)
    end
    loop Every Segment
        Loop->>Seg: update() (renders active mode + blends incoming mode if transitioning)
        Loop->>Seg: update_leds() (applies direction & luminosity -> writes to HW buffer)
    end
    Loop->>HW: leds.show() (executor on RPi, main thread on Windows Pygame)
```

- **Thread-Safe Hardware Dispatch:**
  - On **Raspberry Pi** (`infos["onRaspberry"] == True`): `leds.show()` is offloaded via `loop.run_in_executor(None, leds.show)` so DMA/network I/O never stalls the `asyncio` loop.
  - On **Windows Simulation** (`infos["onRaspberry"] == False`): `leds.show()` runs synchronously on the main thread to respect Pygame's main-thread window affinity.

---

## 3. `TransitionBridge` (`core/TransitionBridge.py`)

`TransitionBridge` is the sole caller of [`transitions/api.py`](../../transitions/api.py) outside `transitions/` (see [`docs/contracts/transition_contract.md`](../contracts/transition_contract.md)):

1. **Snapshot Translation (`build_music_snapshot()` / `build_installation_snapshot()`):**
   - Reads speaker-delayed features and `MusicalContext` from `Mode_master.listener` and packs them into an immutable `MusicSnapshot`.
   - Reads each segment's orientation, available modes, active mode, and `is_blocked` lock state into an `InstallationSnapshot`.
2. **Order Execution (`apply_orders(orders)`):**
   - If `orders.palette` is present, forwards the palette request to `MoodService.select_mood()`.
   - Iterates through `orders.orders` (`SegmentOrder`):
     - Blocked segments or segments missing the target mode refuse the order.
     - Accepted segments invoke `segment.start_transition(...)` with the chosen `target_mode`, `technique`, `duration`, `direction`, `start_offset`, and `mode_handshake` flag.
   - Reports accepted and refused segment names back to `TransitionService.acknowledge(OrderAck)`.

---

## 4. `Segment` (`core/Segment.py`)

Each `Segment` manages the visual lifecycle and pixel memory for one physical strip of length `N = len(indexes)`.

### 4.1 Pre-Allocated Memory Buffers (AXIOM-02)
At `__init__`, `Segment` pre-allocates all per-strip NumPy arrays so zero heap allocations occur during rendering:
- `self.rgb_list`: shape `(N, 3)`, `dtype=np.int32` — primary render buffer mutated by the active mode.
- `self.secondary_rgb_list`: shape `(N, 3)`, `dtype=np.int32` — secondary render buffer used only during dual-mode transitions.
- `self._scaled_rgb_buffer`: shape `(N, 3)`, `dtype=np.int32` — scratch buffer for applying master luminosity scaling and `uint8` clamping before writing to hardware.

### 4.2 Dual-Buffer Transition State Machine
A segment operates in one of two states:

1. **`PASSATION` (Steady-State Single-Mode Rendering):**
   - Calls `self.active_mode.render(buffer=self.rgb_list)`.
   - Only one mode runs per frame.
2. **`TRANSITION_DUAL` (Active Mode Transition):**
   - Initiated by `start_transition(target_mode_name, technique, duration, start_offset, direction, mode_handshake)`:
     - Supports staggered segment starts via `start_offset` (remains in `is_pending` until `now >= transition_start_time`).
     - Supports mid-transition retargeting: if a new transition starts while one is already in flight, the current blended frame in `self.rgb_list` is snapshotted so the visual handover never jumps or flashes.
   - Each frame during `TRANSITION_DUAL`:
     - Computes normalized `progress` $\in [0.0, 1.0]$.
     - If `mode_handshake=True` (`MODE_COOPERATIVE`), calls `active_mode.on_transition_exit(progress)` and `next_mode.on_transition_enter(progress)` so both modes scale their internal physics envelopes (`self.transition_scale`).
     - Renders outgoing mode into `self.rgb_list` and incoming mode into `self.secondary_rgb_list`.
     - Calls `TransitionService.blend(dest_buffer=self.rgb_list, incoming_buffer=self.secondary_rgb_list, progress=progress, technique=technique, coords=self.coords)` which blends `secondary_rgb_list` over `rgb_list` **in place**.
   - On completion (`progress >= 1.0`):
     - Promotes `self.active_mode = self.next_mode`, resets transition hooks (`on_transition_reset()`), and returns to `PASSATION`.

### 4.3 Hardware Mapping & Orientation (`update_leds()`)
After `Segment.update()` populates `self.rgb_list`:
1. Multiplies `self.rgb_list` by `listener.luminosity / 100.0` into `self._scaled_rgb_buffer` and clamps to `[0, 255]`.
2. Applies logical direction (`direction == "UP"` writes `0..N-1` in reverse index order; `"DOWN"` writes in forward order).
3. Slices or assigns the RGB triplets directly into `self.leds[self.indexes]` and updates simulator sideband metadata via `leds.set_segment_mode(...)`.

---

## 5. `CommandRouter` & `AppConfigStore`

- **`CommandRouter` (`core/CommandRouter.py`):** Maps WebSocket action names (`select_mood`, `go_to_next_configuration`, `lock_current_configuration`, `manual_drop`, `select_segment_mode`, `toggle_segment_direction`, `set_luminosity`, `set_sensibility`, `set_auto_transition_time`, `set_mode_setting`, `restart_python_loop`, `restart_raspberry_pi`) to bounded handler methods on `Mode_master`. Every mutation broadcasts an updated state snapshot to connected clients and returns a standardized `{type: "instruction_ack", status, action}` response.
- **`AppConfigStore` (`core/AppConfigStore.py`):** Coalesces rapid slider/setting edits in memory and flushes `config/app_config.json` atomically via a temporary file swap so SD card wear is minimized and power loss cannot corrupt `app_config.json`.
