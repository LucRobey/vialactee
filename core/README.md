# Core Engine (`/core/`)

The `core` directory is the engine room of Vialactée. It contains the primary modules responsible for asynchronous orchestration, audio DSP processing, beat tracking, and structural event mapping.

## Key Components:

- **`CommandRouter.py`**: Modular instruction router. Extracts WebSocket action handling out of `Mode_master` using a clean decorator-based dispatch table (`@router.register(page, action)`) across `live_deck`, `topology`, `mode_settings`, and `system`.
- **`PresetRepository.py`**: Dedicated configuration repository. Encapsulates configuration persistence, playlist querying, and shuffle bag selection. Automatically offloads synchronous disk writes (`json.dump`) to background threads via `loop.run_in_executor()` to prevent frame stalls in the 30 FPS render loop.
- **`AudioIngestion.py`**: Leaf DSP filterbank engine. Receives raw PCM audio, initializes persisted luminosity/sensibility from `config/app_config.json`, and applies pure `numpy` vectorization to compute FFTs, Mel-band weights (8 bands), Chromagrams (12 pitch classes), and ADSR envelopes with explicit zero-division guards.
- **`AudioAnalyzer.py`**: Executes the **Anticipation Flywheel ("Oracle")** engine with an $O(1)$ Pearson template bank, logarithmic tempo-class arithmetic, look-ahead phase back-projection to speaker time, real/dropped beat validation, and frequency-band tagging. Fully decomposed into cohesive pipeline stages (`_compute_spectral_flux`, `_ingest_odf_buffer`, `_run_oracle_sweep`, `_advance_flywheel`).
- **`StructuralNoveltyDetector.py`**: Dedicated structural novelty engine. Autonomously identifies Verse/Chorus boundaries, Seamless Crossfades, and Silence Drops using Short-Term Memory (STM) vs Long-Term Memory (LTM) tension wrapped in dynamic asserved mathematical envelopes.
- **`RhythmConfig.py`**: Centralized, strongly-typed configuration dataclass holding all thresholds, cooldowns, and constants for beat tracking, flywheel trust levels, and structural novelty detection.
- **`Listener.py`**: The transparent facade orchestrator. Instantiates Ingestion and Analysis layers and provides a fully backward-compatible API (`beat_phase`, `beat_count`, `bpm`, `is_real_beat`, `is_dropped_beat`, `beat_tag`, `beat_confidence`, `is_song_change`, `is_verse_chorus_change`) to feed data into the visual modes and transition engine. Manages a zero-allocation, pre-allocated 2D/1D NumPy circular ring buffer to synchronize real-time spectral arrays with the predictive lookahead of the beat tracker.
- **`Mode_master.py`**: The 30FPS rendering engine. Polls the `Listener` for audio features, resolves the active hardware profile (`"full"` vs `"small"`), delegates configuration queries and shuffle bag rotation to `PresetRepository`, dispatches WebSocket instructions to `CommandRouter`, routes state to active visual modes, and exposes JSON-safe state snapshots for the web app.
- **`Transition_Director.py` & `Transition_Engine.py`**: Orchestrates lighting transitions across presets based on configurable timer intervals (`auto_transition_time`) respecting user-selected transition configs. `Transition_Engine.py` uses `init_room_bounds()` to dynamically compute spatial room bounds from active segment geometry and provides 10 spatial/alpha blending routines.
- **`Segment.py`**: A logical abstraction of the physical LED strips, mapping mathematical vectors to physical addresses using the resolved segment configuration. Features zero-allocation pre-allocated output buffers (`_scaled_buffer`), cached index reversal, and dual-buffer rendering via `Mode.render(buffer)`.
- **`BeatGridQuantizer.py`**: Decoupled beat grid quantization and O(1) motif pattern recognition layer. Quantizes continuous note events onto beat tracker phase-aligned grid subdivisions (16th/8th notes) and detects repeating melodic motifs in real-time.
- **`Webapp_instruction_logger.py`**: Instruction logger sink instantiated by `connectors/Connector.py` to parse, format, and log incoming WebSocket commands from the web interface.

## How it works:

The `Mode_master` runs an asynchronous loop, asking the `Listener` for the current state of the music. Based on rules handled by the `Transition_Director`, it updates the LED `Segment`s using the algorithms defined in the `modes/` directory. When a `Connector` is attached, it also broadcasts changed state snapshots so Live Deck and Topology mirror automatic backend transitions.

## Core Architecture Diagram

The following diagram visualizes the interaction and structural relationship between `Listener`, `Mode_master`, `Transition_Director`, `AudioAnalyzer`, and `StructuralNoveltyDetector`:

```mermaid
classDiagram
    %% Core Orchestration
    class Mode_master {
        -listener : Listener
        -transition_director : Transition_Director
        -segments_list : list
        -activ_configuration : dict
        +update()
        +change_configuration(transition_config)
        +update_segments_modes(transition_config)
    }

    %% Spatial & Transition Logic Filter
    class Transition_Director {
        -listener : Listener
        -state : str
        -next_change_time : float
        -transition_progress : float
        -transition_type : str
        -all_segments : list
        -verticals : list
        -horizontals : list
        +start_transition(transition_config) : None
        +update(current_time) : None
    }

    %% Audio Facade & Analyzers
    class Listener {
        +bpm : float
        +beat_phase : float
        +beat_count : int
        +is_real_beat : bool
        +is_dropped_beat : bool
        +beat_tag : str
        +beat_confidence : float
        +is_song_change : bool
        +is_verse_chorus_change : bool
        +smoothed_total_power : float
        +update()
        +start_silence_calibration()
    }

    class AudioIngestion {
        +smoothed_total_power
        +band_proportion
        +process_raw_audio(audio_data)
    }

    class RhythmConfig {
        +high_confidence_threshold : float
        +moderate_confidence_threshold : float
        +song_novelty_asserved_th : float
        +structural_cooldown_seconds : float
    }

    class StructuralNoveltyDetector {
        +is_song_change : bool
        +is_verse_chorus_change : bool
        +asserved_novelty : float
        +combined_novelty : float
        +update(current_timbre, current_power, current_time, dt, fps_ratio)
    }
  
    class AudioAnalyzer {
        -config : RhythmConfig
        -novelty_detector : StructuralNoveltyDetector
        +bpm : float
        +speaker_phase : float
        +confidence_score : float
        +is_real_beat : bool
        +is_dropped_beat : bool
        +current_beat_tag : str
        +is_song_change : bool
        +is_verse_chorus_change : bool
        +detect_band_peaks(current_time, dt, fps_ratio)
        +update_structural_novelty(current_time, dt, fps_ratio)
    }

    %% Hardware & Visual Outputs
    class Segment {
        +change_mode(new_mode, transition_config)
    }

    %% Subsystem Collaborators
    class CommandRouter {
        +dispatch(mode_master, instruction) : dict
        +register(page, action) : decorator
    }

    class PresetRepository {
        +load_configurations()
        +pick_a_random_conf()
        +persist_configurations_store()
    }

    %% --- Relationships and Interactions ---

    %% Composition / Ownership
    Mode_master *-- Transition_Director : Instantiates
    Mode_master *-- Listener : Instantiates / Owns
    Mode_master *-- PresetRepository : Owns
    Mode_master ..> CommandRouter : Dispatches via
    Mode_master "1" *-- "*" Segment : Orchestrates
    Listener *-- AudioIngestion : Facades
    Listener *-- AudioAnalyzer : Facades
    AudioAnalyzer *-- StructuralNoveltyDetector : Owns
    AudioAnalyzer *-- RhythmConfig : Uses

    %% Logic Flow
    Transition_Director ..> Listener : Polls audio state \n(Power, Drops, Events)
    Transition_Director ..> Mode_master : Commands action via\nchange_configuration()
    Mode_master ..> Segment : Pushes global\ntransition states
```

### Interaction within the Execution Loop (`update()`):

1. **Audio Ingestion & Calculation:**
   `Mode_master` fires `listener.update()` every frame. The `Listener` (acting as a facade) processes raw audio through `AudioIngestion`, updates `StructuralNoveltyDetector` for macro-structure, and runs the predictive beat tracking pipeline in `AudioAnalyzer`.
2. **Context Evaluation:**
   `Mode_master` asks the `Transition_Director` to update its state and progress transitions by passing the time state: `transition_director.update(current_time)`.
3. **Interval Evaluation:**
   `Transition_Director.update(current_time)` checks whether the automated transition interval (`auto_transition_time`) has elapsed or a manual trigger has fired. When an update is required, it directly commands `await self.mode_master.change_configuration(transition_config)`.
4. **Execution:**
   `Mode_master.change_configuration()` loads the new preset from the active configuration store, initializes the transition configuration matrix via `transition_director.start_transition(transition_config)`, and pushes the dual-buffer blend state to all underlying physical `Segment` objects.
