# Music Analyzer & DSP Sector Contract (`music_analyzer_contract.md`)

Sibling of [`mood_contract.md`](mood_contract.md) and [`transition_contract.md`](transition_contract.md). The music analysis and DSP sector lives in [`music/`](../../music/) and is a **sealed room**: production code outside `music/` reaches it only through [`music/api.py`](../../music/api.py).

---

## Part A: The Doors (authoritative)

**Wall rules** (enforced by [`tests/governance/test_music_isolation.py`](../../tests/governance/test_music_isolation.py) and [`tests/governance/test_docs_parity.py`](../../tests/governance/test_docs_parity.py))
1. Nothing in `music/` imports project code outside `music/` (`core/`, `modes/`, `connectors/`, `hardware/`, `transitions/`, `mood/`, ...). Only the Python standard library, `numpy`, and `music/` itself.
2. Production code outside `music/` imports **only** `music.api`. (Tests, `research/`, and developer studios in `tools/` / `scripts/` may import internal modules directly for benchmarking and diagnostics.)
3. None of the 10 music modules (`AudioIngestion.py`, `BaseAudioAnalyzer.py`, `AudioAnalyzer.py`, `MultiBandOnsetAudioAnalyzer.py`, `DyadicMetricalAudioAnalyzer.py`, `comb_kernels.py`, `StructuralNoveltyDetector.py`, `RhythmConfig.py`, `MusicalContextEngine.py`, `Listener.py`) may exist as shims in `core/`.
4. Every public attribute on `Listener` and `listener.context` (`MusicalContextEngine`) is documented in §2 and §3 below (`TestDocsParity.test_music_contract_parity`). **This file is the only place that states our trust (🟢 HIGH / 🟡 MEDIUM / 🟠 LOW) in each of these signals.** Trust is engineering guidance for people and agents writing or reviewing consumers; it is not encoded in Python and not enforced by a test. To change a signal's trust, edit its table row here and nowhere else.

### Doors Across the Wall

| # | Door | Dir | Trust | Shape (in `music/api.py`) | Notes |
| :-: | :--- | :-: | :-: | :--- | :--- |
| 1 | Construction | in | ⚙️ CONFIG | `Listener(infos, analyzer_class=None)` | Reads `useMicrophone`, `fakeDelay` (`5.0 s`), `analyzer_model`, `luminosity`, `sensibility`, `led_latency`, `audio_output_latency`, and `musical_context`. |
| 2 | PCM Audio Stream | in | 🟢 Physical | `listener.process_raw_audio(audio_data)` | Accepts a 4096-sample `float64`/`float32` PCM chunk (`44.1 kHz`) and updates 8-band Mel, 32-band Mel, and 12-bin chroma arrays in place. |
| 3 | Driving Clock & Reset | in | ⚙️ Lifecycle | `listener.update(fixed_dt=None)`, `listener.reset()` | Ticks ingestion envelopes, rhythm analyzer, 5.0 s ring buffer, and `listener.context`. |
| 4 | Runtime Gain & Latency | in/out | ⚙️ CONFIG / 🟢 HIGH | `listener.luminosite`, `listener.sensi`, `listener.dynamic_audio_latency` | Live UI brightness/sensitivity sliders and PortAudio latency calibration setter. |
| 5 | `Listener` Signals | out | 🟢 / 🟡 / 🟠 / ⚙️ | `ListenerProtocol` (42 `@property` attributes) | Speaker-aligned ($T_{\text{speaker}}$) and lookahead ($T_{\text{lookahead}}$) signals (§2). |
| 6 | `MusicalContextEngine` | out | 🟢 / 🟡 / 🟠 | `listener.context` (`MusicalContextProtocol`, 31 `@property` attributes) | Unified 3-tier kinetics, macro scenes, and micro badges (§3). |

### Exported Symbols in `music/api.py`

| Symbol | Kind | Role |
| :--- | :--- | :--- |
| `Listener` | Class | Primary facade & zero-allocation circular delay ring buffer synchronizing `AudioIngestion`, `BaseAudioAnalyzer`, and `MusicalContextEngine` at speaker time ($T_{\text{speaker}}$). |
| `MusicalContextEngine` | Class | Unified 3-tier visual conductor exposed at `listener.context` (also used via `isinstance(ctx, MusicalContextEngine)`). |
| `MusicalScene` | `str, Enum` | 4 canonical macro scenes: `CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`. |
| `ANALYZER_REGISTRY` | `Dict[str, Type]` | Maps `"DyadicMetricalAudioAnalyzer"`, `"MultiBandOnsetAudioAnalyzer"`, and `"AudioAnalyzer"` to their classes. |
| `DEFAULT_ANALYZER_MODEL` | `str` | `"DyadicMetricalAudioAnalyzer"` (Cycle 012 production default). |
| `resolve_analyzer_class(spec)` | Function | Resolves a model name or class to a `BaseAudioAnalyzer` subclass; warns and falls back to default on unknown names. |
| `ListenerProtocol`, `MusicalContextProtocol` | `typing.Protocol` | Static type protocols documenting the consumer-facing surface injected into `modes/` and `core/TransitionBridge.py`. |

---

## 1. Dual Time-Horizon Invariant: $T_{\text{speaker}}$ vs $T_{\text{lookahead}}$

Because the Anticipation Flywheel ("Oracle") inspects a 5.0-second lookahead window (`fakeDelay = 5.0 s`) to lock onto tempo and phase without causal lag, `Listener` maintains **two distinct time horizons**:

```
Audio Stream (T_lookahead = t) ──► AudioIngestion + Rhythm Analyzer (live_*)
                                           │
                          Pre-allocated Circular Ring Buffer (5.0 s)
                                           │
                                           ▼
Speaker Output (T_speaker = t - 5.0s) ──► Listener delayed properties + MusicalContextEngine
```

1. **Speaker-Aligned Properties ($T_{\text{speaker}}$, no prefix):**
   * Synchronized with the physical sound waves leaving the speakers (`current_time - lookahead_seconds`).
   * **Visual modes (`modes/`) must only consume $T_{\text{speaker}}$ signals** so light impacts land within $< 50\text{ ms}$ of the audible transient (AXIOM-05).
2. **Lookahead Properties ($T_{\text{lookahead}}$, `live_*` prefix & gradients):**
   * Reflect the audio stream 5.0 seconds *ahead* of the speakers (`live_asserved_total_power`, `live_rhythm_salience`, `live_beat_trust`, `live_asserved_novelty`, `live_combined_novelty`, `live_is_song_change`, `live_is_verse_chorus_change`, plus `salience_gradient` $\Delta R$ and `power_gradient` $\Delta P$).
   * Consumed internally by `MusicalContextEngine` (to compute `BUILDUP` ramps and `drop_countdown`) and by `transitions/` (to pre-schedule transitions before a song boundary or drop reaches the speakers).

---

## 2. `Listener` Public Contract (42 Properties + 6 Internal Attributes)

### 2.1 🟢 HIGH Trust (10 Physical / Spectral Signals)

Direct spectral measurements, ADSR-normalized envelopes, and hardware calibration values. Safe for modes to consume directly every frame without confidence gating.

| Signal | Type & Shape | Range / Units | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `fft_band_values` | `np.ndarray (8,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | Raw 8-band Mel filterbank magnitudes. |
| `smoothed_fft_band_values` | `np.ndarray (8,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | ADSR-smoothed (fast attack, slow release) 8-band Mel magnitudes. |
| `asserved_fft_band` | `np.ndarray (8,) float64` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | ADSR-normalized (local/global max) 8-band Mel spectrum; primary per-band drive for visual modes. |
| `band_proportion` | `np.ndarray (8,) float64` | $[0.0, 1.0]$, $\sum \le 1$ | $T_{\text{speaker}}$ | Relative energy share of each of the 8 Mel bands. |
| `band_means` | `np.ndarray (8,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | Rolling mean energy per Mel band. |
| `band_flux` | `np.ndarray (8,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | Half-wave rectified spectral onset flux $\max(0, E_b[t] - E_b[t-1])$ across the 8 Mel bands. |
| `smoothed_total_power` | `float` | $\ge 0.0$ | $T_{\text{speaker}}$ | Exponentially smoothed total acoustic power. |
| `asserved_total_power` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | ADSR-normalized total acoustic power at speaker time. |
| `live_asserved_total_power` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | ADSR-normalized total acoustic power at the live lookahead horizon. |
| `dynamic_audio_latency` | `float` | seconds ($\ge 0.0$) | Hardware | Dynamic PortAudio capture-to-Hanning-window-center latency calibration. |

### 2.2 🟡 MEDIUM Trust (15 Tempo, Phase & Confidence Signals)

Probabilistic estimates from the Anticipation Flywheel. **Guidance:** Consumers reading `beat_phase`, `is_beat`, `bpm`, `is_real_beat`, or `beat_count` should gate or blend by a confidence signal (`rhythm_lock`, `beat_trust`, `rhythm_salience`, `is_locked`, `beat_confidence`, or `Mode.beat_pulse()`) and stay smoothly animated when confidence is `0.0`.

| Signal | Type | Range / Values | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `bpm` | `float` | $[60.0, \sim 260.0]$ | $T_{\text{speaker}}$ | Effective metrical tempo in BPM (`effective_bpm` when sub-pulses are active, else nominal tactus). |
| `beat_phase` | `float` | $[0.0, 1.0)$ | $T_{\text{speaker}}$ | Continuous sawtooth metrical beat phase ($0.0$ = beat strike). |
| `beat_count` | `int` | $\ge 0$ | $T_{\text{speaker}}$ | Cumulative metrical beat counter since startup/reset. |
| `is_beat` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | 1-frame impulse true on the frame `beat_phase` wraps across `0.0`. |
| `is_real_beat` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | 1-frame beat tick validated by physical acoustic transient energy. |
| `is_dropped_beat` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | 1-frame beat tick where the flywheel coasted without a physical transient. |
| `beat_tag` | `str` | `"Bass/Kick"`, `"Snare/Mid"`, `"Hi-hat/Cymbal"` | $T_{\text{speaker}}$ | Dominant frequency-band instrument classification for the most recent beat at $T_{\text{speaker}}$. |
| `beat_confidence` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Raw Pearson template correlation confidence score (`analyzer.confidence_score`). |
| `beat_trust` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-delayed beat tracking trust score. |
| `live_beat_trust` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Lookahead beat tracking trust score. |
| `rhythm_salience` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-delayed rhythmic salience (pulse clarity + crest factor + periodicity). |
| `live_rhythm_salience` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Lookahead rhythmic salience score. |
| `standalone_bpm` | `float` | $[60.0, \sim 260.0]$ | $T_{\text{speaker}}$ | Backward-compatibility alias for `bpm` (`effective_bpm` in `DyadicMetricalAudioAnalyzer`). |
| `standalone_phase` | `float` | $[0.0, 1.0)$ | $T_{\text{speaker}}$ | Backward-compatibility alias for `beat_phase`. |
| `flywheel_status` | `str` | `"locked"`, `"coasting"`, ... | $T_{\text{speaker}}$ | Diagnostic status label of the Anticipation Flywheel. |

### 2.3 🟠 LOW Trust (14 Heuristic Novelty, Boundary, Gradient & Uncalibrated Pitch Signals)

Structural boundary heuristics, lookahead-minus-speaker gradients, and uncalibrated chromagram pitch bins. Prone to false positives and broadband harmonic pollution. **Guidance:** Prefer not to drive visuals directly from `is_song_change`, `is_verse_chorus_change`, `chroma_values`, or `smoothed_chroma_values` in concrete modes (the chromagram is currently uncalibrated); boundary flags are meant for `transitions/` (behind cooldowns) and `MusicalContextEngine`.

| Signal | Type | Range / Values | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `chroma_values` | `np.ndarray (12,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | Raw 12-pitch-class chromagram magnitudes (`C, C#, D, ..., B`); uncalibrated against broadband percussion/harmonics. |
| `smoothed_chroma_values` | `np.ndarray (12,) float64` | $\ge 0.0$ | $T_{\text{speaker}}$ | ADSR-smoothed 12-pitch-class chromagram magnitudes; uncalibrated against broadband percussion/harmonics. |
| `is_song_change` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Speaker-delayed song change boundary flag. |
| `is_verse_chorus_change` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Speaker-delayed structural section boundary flag. |
| `live_is_song_change` | `bool` | `True` / `False` | $T_{\text{lookahead}}$ | Lookahead song change boundary flag (5.0 s ahead of speakers). |
| `live_is_verse_chorus_change` | `bool` | `True` / `False` | $T_{\text{lookahead}}$ | Lookahead structural section boundary flag (5.0 s ahead of speakers). |
| `asserved_novelty` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-delayed ADSR-normalized structural novelty score. |
| `combined_novelty` | `float` | $\ge 0.0$ | $T_{\text{speaker}}$ | Speaker-delayed raw STM-vs-LTM Euclidean novelty score. |
| `live_asserved_novelty` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Lookahead ADSR-normalized structural novelty score. |
| `live_combined_novelty` | `float` | $\ge 0.0$ | $T_{\text{lookahead}}$ | Lookahead raw STM-vs-LTM structural novelty score. |
| `novelty_lm` | `float` | $\ge 0.0$ | $T_{\text{speaker}}$ | Speaker-delayed local-maximum envelope of structural novelty. |
| `novelty_gm` | `float` | $\ge 0.0$ | $T_{\text{speaker}}$ | Speaker-delayed global-maximum envelope of structural novelty. |
| `salience_gradient` | `float` | $[-1.0, 1.0]$ | $\Delta(T_{\text{lookahead}}, T_{\text{speaker}})$ | Forward rhythmic salience gradient $\Delta R = R_{\text{live}} - R_{\text{speaker}}$ (delegated to `context.salience_gradient`). |
| `power_gradient` | `float` | $[-1.0, 1.0]$ | $\Delta(T_{\text{lookahead}}, T_{\text{speaker}})$ | Forward acoustic power gradient $\Delta P = P_{\text{live}} - P_{\text{speaker}}$ (delegated to `context.power_gradient`). |

### 2.4 ⚙️ CONFIG (3 Configuration Properties)

User-configurable runtime settings and static filterbank dimensions proxied from `AudioIngestion`.

| Property | Type | Range / Default | Description |
| :--- | :--- | :--- | :--- |
| `luminosite` | `float` | $[0.0, 1.0]$ (default `1.0`) | Master chandelier brightness scalar controlled from the Live Deck UI. |
| `sensi` | `float` | $> 0.0$ (default `1.0`) | Global audio input sensitivity multiplier controlled from the Live Deck UI. |
| `nb_of_fft_band` | `int` | `8` | Number of coarse Mel frequency bands exposed to visual modes. |

### 2.5 `Listener` Internal Attributes (6 Non-Signals)

Orchestrator lifecycle methods and internal component references (not visual signals):

| Attribute | Kind | Purpose |
| :--- | :--- | :--- |
| `analyzer` | `BaseAudioAnalyzer` | Active rhythm analyzer instance (used by simulator HUD and tests). |
| `context` | `MusicalContextEngine` | Unified 3-tier musical context engine (§3). |
| `ingestion` | `AudioIngestion` | Vectorized DSP front-end instance. |
| `reset` | Method (`reset()`) | Resets ingestion, analyzer, ring buffers, and `context` on track change. |
| `update` | Method (`update()`) | Advances one 60 Hz / 30 FPS tick of ingestion, analyzer, ring buffer, and `context`. |
| `process_raw_audio` | Method (`process_raw_audio(audio_data)`) | Feeds a raw PCM audio chunk into `AudioIngestion`. |

---

## 3. `MusicalContextEngine` (`listener.context`) Contract (31 Signals + 19 Internal Attributes)

### 3.1 🟢 HIGH Trust (7 Physical & Kinetic Signals)

Continuous physical kinetics and Schmitt-stabilized acoustic power/silence states at $T_{\text{speaker}}$. Safe to drive visual modes directly every frame.

| Signal | Type | Range | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `energy` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Composite continuous visual energy drive ($\text{clamp}(0.50 \cdot P + 0.30 \cdot S + 0.20 \cdot (S \cdot T), 0.0, 1.0)$). |
| `power` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-aligned `asserved_total_power`. |
| `live_power` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Lookahead `live_asserved_total_power`. |
| `spectral_tilt` | `float` | $[-1.0, 1.0]$ | $T_{\text{speaker}}$ | High-frequency vs low-frequency balance across the 8 Mel bands ($-1$ = bass-heavy, $+1$ = treble-heavy). |
| `vertical_center` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Normalized spectral center of mass across the 8 Mel bands. |
| `is_power_high` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Schmitt-triggered high acoustic power state (`power_low = 0.35`, `power_high = 0.50`). |
| `is_silent` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Schmitt-triggered acoustic silence guard (`silence_threshold = 0.05`, `silence_exit_threshold = 0.08`). |

### 3.2 🟡 MEDIUM Trust (6 Rhythm Confidence Signals & Badges)

Confidence scores and Schmitt-gated micro badges derived from the rhythm flywheel.

| Signal | Type | Range / Values | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `salience` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-aligned rhythmic salience (`listener.rhythm_salience`). |
| `live_salience` | `float` | $[0.0, 1.0]$ | $T_{\text{lookahead}}$ | Lookahead rhythmic salience (`listener.live_rhythm_salience`). |
| `beat_trust` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Speaker-aligned beat tracking trust (`listener.beat_trust`). |
| `is_locked` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Schmitt-triggered beat trust lock (`_is_trust_high`, entering at `beat_trust >= 0.50`, exiting at `< 0.35`). |
| `is_real_beat` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Speaker-time beat tick verified by acoustic power (`listener.is_beat and power >= 0.20`). |
| `is_syncopated` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | High rhythmic salience while 4/4 flywheel trust is low (`_is_salience_high and beat_trust < trust_low`). |

### 3.3 🟠 LOW Trust (18 Scene, Drop & Structural Heuristics)

Macro scene states, lookahead drop predictors, and structural boundary badges. **Guidance:** Concrete modes (`modes/*_mode.py`) should not read `scene`, `is_drop_impact`, `is_drop_imminent`, or `is_structural_cut` directly. Instead, `mood/` smooths `scene` into 🟢 `mood_modifiers`, and `Mode.py` provides the gated `self.drop_hit` and `self.drop_decay` helpers.

| Signal | Type | Range / Values | Time Horizon | Description |
| :--- | :--- | :--- | :-: | :--- |
| `scene` | `MusicalScene` | `CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT` | $T_{\text{speaker}}$ | Active macro musical scene governed by Schmitt hysteresis and dwell locks. |
| `previous_scene` | `MusicalScene` | `CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT` | $T_{\text{speaker}}$ | Previous macro musical scene prior to the latest scene transition. |
| `scene_blend` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Linear blend progress from `previous_scene` to `scene` over `transition_time`. |
| `scene_dwell_time` | `float` | seconds ($\ge 0.0$) | $T_{\text{speaker}}$ | Time elapsed in the current `scene`. |
| `is_ambient` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Scene helper (`scene == MusicalScene.CHILL`). |
| `is_rhythmic` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Scene helper (`scene in (MusicalScene.GROOVE, MusicalScene.DROP_IMPACT)`). |
| `is_in_pocket` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Scene + lock helper (`scene == MusicalScene.GROOVE and is_locked`). |
| `is_buildup` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Scene helper (`scene == MusicalScene.BUILDUP`). |
| `drop_countdown` | `float` | seconds ($[-2.0, 5.0]$) | $T_{\text{lookahead}} \to T_{\text{speaker}}$ | Estimated seconds remaining until the predicted drop reaches the speakers. |
| `drop_progress` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Ramps $0 \to 1$ across `BUILDUP` and decays $1 \to 0$ across the 1.5 s `DROP_IMPACT` dwell. |
| `pre_drop_cooldown` | `float` | seconds ($\ge 0.0$) | $T_{\text{speaker}}$ | Cooldown timer preventing repeated back-to-back `BUILDUP` detections. |
| `is_drop_imminent` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | True during `BUILDUP` when `drop_countdown <= 0.40 s`. |
| `is_drop_impact` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | 1-frame arrival pulse on the frame `scene` transitions into `DROP_IMPACT`. |
| `is_structural_cut` | `bool` | `True` / `False` | $T_{\text{speaker}}$ | Sustained for `structural_dwell_time` (`1.2 s`) after a song or verse/chorus boundary at $T_{\text{speaker}}$. |
| `novelty` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Clamped speaker-aligned `asserved_novelty`. |
| `tension` | `float` | $[0.0, 1.0]$ | $T_{\text{speaker}}$ | Macro tension curve combining `drop_progress`, `novelty`, and positive lookahead gradients. |
| `salience_gradient` | `float` | $[-1.0, 1.0]$ | $\Delta(T_{\text{lookahead}}, T_{\text{speaker}})$ | Clamped forward salience delta $\Delta R = \text{live\_salience} - \text{salience}$. |
| `power_gradient` | `float` | $[-1.0, 1.0]$ | $\Delta(T_{\text{lookahead}}, T_{\text{speaker}})$ | Clamped forward power delta $\Delta P = \text{live\_power} - \text{power}$. |

### 3.4 `MusicalContextEngine` Internal Attributes (19 Non-Signals)

Lifecycle methods, parent back-reference, and Schmitt / dwell configuration constants:

| Attribute | Kind | Default / Purpose |
| :--- | :--- | :--- |
| `listener` | `Listener` | Back-reference to the owning `Listener` facade. |
| `reset` | Method (`reset()`) | Resets all scene, Schmitt, and countdown states. |
| `update` | Method (`update(dt)`) | Advances scene evaluation, Schmitt triggers, and modulation envelopes by `dt` seconds. |
| `get_state_snapshot` | Method (`get_state_snapshot()`) | Returns a JSON-serializable dict for studio/telemetry inspection (not hot-path). |
| `salience_high`, `salience_low` | `float` | `0.45`, `0.35` — Schmitt hysteresis thresholds for rhythmic salience. |
| `trust_high`, `trust_low` | `float` | `0.50`, `0.35` — Schmitt hysteresis thresholds for beat trust. |
| `power_high`, `power_low` | `float` | `0.50`, `0.35` — Schmitt hysteresis thresholds for total power. |
| `silence_threshold`, `silence_exit_threshold` | `float` | `0.05`, `0.08` — Schmitt hysteresis thresholds for `is_silent`. |
| `drop_buildup_threshold` | `float` | `0.40` — Forward salience gradient threshold ($\Delta R$) for `BUILDUP`. |
| `drop_buildup_power_threshold` | `float` | `0.40` — Forward power gradient threshold ($\Delta P$) for `BUILDUP`. |
| `min_dwell_time` | `float` | `1.0 s` — Minimum scene dwell time before a non-drop transition is allowed. |
| `transition_time` | `float` | `0.5 s` — Duration over which `scene_blend` ramps from `0.0` to `1.0`. |
| `structural_dwell_time` | `float` | `1.2 s` — Duration `is_structural_cut` stays active after a boundary. |
| `pre_drop_cooldown_time` | `float` | `16.0 s` — Minimum cooldown between consecutive `BUILDUP` detections. |
| `drop_impact_dwell_time` | `float` | `1.5 s` — Duration of the `DROP_IMPACT` scene dwell before returning to `GROOVE`. |

---

## 4. `BaseAudioAnalyzer` Subclass Contract & 4-Step Lifecycle

Every rhythm and structural analyzer in `music/` and `research/` subclasses [`music/BaseAudioAnalyzer.py`](../../music/BaseAudioAnalyzer.py) (verified by `tests/test_base_analyzer_contract.py` and `tests/test_analyzer_contract_compliance.py`):

1. **Step 1 — Multi-Band ODF Ingestion (`_ingest_multiband_derivative_odf`):** Computes half-wave rectified onset derivatives across the 32 Mel bands (`ingestion.multiband_fft_values`), separates instrument streams ($y_{\text{kick}}, y_{\text{snare}}, y_{\text{hat}}, y_{\text{mid}}$), and appends to the 5.0 s circular ODF ring buffer.
2. **Step 2 — Periodic Tempo & Phase Sweep (`_run_tempo_and_phase_sweep`):** Evaluates the dense Pearson pulse template bank (`music/comb_kernels.py`), performs kick-conditioned anti-phase disambiguation ($K_{\text{anti}} > 1.25 \cdot K_1$), and updates `bpm`, `confidence_score`, `live_rhythm_salience`, and `live_beat_trust`.
3. **Step 3 — Speaker Back-Projection & Continuous Flywheel (`_advance_speaker_flywheel`):** Back-projects lookahead phase $\phi_{\text{ingest}}$ to $T_{\text{speaker}}$ accounting for `lookahead_seconds`, `dynamic_audio_latency`, and `hardware_latency = led_latency - audio_output_latency`. Advances `speaker_phase`, soft-snaps with backward-wrap clamping, enforces the physical refractory lockout ($T_{\min} = \max(0.18\text{ s}, 0.40 \times 60/\text{BPM})$), and emits `is_beat`, `is_real_beat`, `is_dropped_beat`, `beat_count`, and `current_beat_tag` (`"Bass/Kick"`, `"Snare/Mid"`, `"Hi-hat/Cymbal"`).
4. **Step 4 — Structural Novelty & Telemetry (`update_structural_novelty` / `capture_frame_telemetry`):** Updates `StructuralNoveltyDetector` (`is_song_change`, `is_verse_chorus_change`, `asserved_novelty`, `combined_novelty`) and provides per-frame telemetry dicts for the offline benchmark harness.

---

## 5. Real-Time Performance & Safety Guarantees

* **AXIOM-01 (Frame Budget):** Full `Listener.update()` (ingestion + 32-band analyzer + novelty + ring buffer + context) executes in $\le 3.0\text{ ms}$ per 60 Hz tick on Raspberry Pi ARM Cortex-A72 (`< 0.50 ms` typical).
* **AXIOM-02 (Zero Heap Allocations):** All FFT windows, Mel matrices, ring buffers, and context states are pre-allocated in `__init__()`. `update()` mutates arrays in place with zero dynamic heap allocations.
* **AXIOM-05 (Lookahead Sync):** All unprefixed properties on `Listener` and `MusicalContextEngine` are delayed by `lookahead_seconds` so visual events align with speaker output within $< 50\text{ ms}$.
* **AXIOM-07 (Code Governance):** Every file in `music/` obeys the 500-line cap (or the one-way ratchet in `test_axiom_07_code_governance.py`).
