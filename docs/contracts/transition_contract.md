# Transition Sector Contract (`transition_contract.md`)

Sibling of [`music_analyzer_contract.md`](music_analyzer_contract.md) and [`mood_contract.md`](mood_contract.md). The transition sector lives in [`transitions/`](../../transitions/) and is a **sealed room**: it talks to the rest of the project only through the doors below, defined in code in [`transitions/api.py`](../../transitions/api.py).

## Part A: The Doors (authoritative)

**Wall rules** (enforced by [`tests/governance/test_transition_isolation.py`](../../tests/governance/test_transition_isolation.py))
1. Nothing in `transitions/` imports from `core/`, `music/`, `modes/`, `mood/`, `connectors/` or `hardware/`.
2. Nothing outside `transitions/` imports from it except `transitions.api`.
3. `api.py` uses only the standard library and `numpy`.
4. The front door is **synchronous**.

| # | Door | Dir | Shape (in `api.py`) | Notes |
| :-: | :--- | :-: | :--- | :--- |
| 1 | Music | in | `MusicSnapshot` | Read-only, speaker-time + lookahead triggers. Fields have defaults; the trust of each `music/` signal is stated only in [`music_analyzer_contract.md`](music_analyzer_contract.md). |
| 2 | Installation | in | `InstallationSnapshot`, `SegmentDescriptor` | Segments, orientation, modes available, active mode, blocked. `room_bounds` comes from the layout. |
| 3 | Requests | in | `request_next`, `request_drop`, `set_locked`, `set_auto_interval` | The UI and manual input all arrive as requests. |
| 4 | Orders | out | `TransitionOrders` containing one `SegmentOrder` per segment | Each entry has its own mode, technique, duration, direction, `start_offset`, and `mode_handshake`. |
| 5 | Acknowledgement | in | `OrderAck` | The caller says which segments accepted (a segment already in transition refuses). |
| 6 | Blending | out | `blend(dest, incoming, progress, technique, coords)` | **In place**, returns nothing, zero allocation per frame. |
| 7 | Progress | out | `TransitionStatus.progress` | Used by the optional mode enter/exit hooks and the UI. |
| 8 | Status | out | `get_status()` → `TransitionStatus` | State, progress, locked, interval, current technique, `is_pending`. |
| 9 | Palette request | out | `TransitionOrders.palette` (`PaletteRequest`) | The mood sector (`mood/`, see [`mood_contract.md`](mood_contract.md)) stays **outside** the room; `TransitionBridge.apply_orders` forwards the request to `mood.api`. |

**Ownership.** The room owns: when to transition, what to play where, how it looks, and timing. The outside owns: segments and their buffers, modes, the palette manager, and the UI. Modes never decide when or how they are replaced; the `on_transition_enter/exit` hooks stay on the mode side and receive progress from the caller.

**Change policy.** Inside the room anything may change freely. Changing a door means editing `api.py`, `tests/transitions/test_api_contracts.py` and this section together.

### `MusicSnapshot` Field Table

`core/TransitionBridge.build_music_snapshot(listener)` freezes 21 fields from `Listener` and `listener.context` into `MusicSnapshot`. The trust rating of each source signal is defined by its producer in [`music_analyzer_contract.md`](music_analyzer_contract.md) (this table does not repeat it). Because several of these signals are only moderately or weakly trusted there, `transitions/` enforces internal **beat-quantization timeouts (`1.2 s`)** and **post-transition security cooldowns (`5.0 s`)** so noisy boundary flags cannot machine-gun mode changes:

| `MusicSnapshot` Field | Source | How `transitions/` Safeguards Consumption |
| :--- | :--- | :--- |
| `energy` | `context.energy` | Continuous weight in target DNA and technique selection. |
| `power` | `context.power` | Continuous acoustic power metric. |
| `is_silent` | `context.is_silent` | Schmitt-triggered silence state. |
| `beat_phase` | `listener.beat_phase` | Used for beat alignment (`beat_phase < 0.05`) only when `beat_trust >= 0.20`, with a `1.2 s` fallback timeout. |
| `is_beat` | `listener.is_beat` | Beat quantization trigger with `1.2 s` timeout fallback if the flywheel stalls. |
| `salience` | `context.salience` | Soft weight in target DNA (`punch`, `rhythm`) and technique selection. |
| `beat_trust` | `context.beat_trust` | Gates `beat_phase` quantization (`>= 0.20`) and weights `rhythm` DNA. |
| `is_locked` | `context.is_locked` | Soft probability weight in cohort pattern lottery. |
| `is_syncopated` | `context.is_syncopated` | Soft probability weight in complexity DNA and cohort lottery. |
| `novelty` | `context.novelty` | Soft weight (`0.4 * novelty`) in target `complexity` DNA. |
| `tension` | `context.tension` | Soft weight (`0.3 * tension`) in target `complexity` DNA. |
| `scene` | `context.scene.value` | Soft probability bias in cohort lottery (`CHILL` vs `BUILDUP`); pre-drop trigger gated by cooldown. |
| `is_rhythmic` | `context.is_rhythmic` | Selects `directional_wipe` vs `smooth_cosine_crossfade` when transition fires. |
| `is_drop_impact` | `context.is_drop_impact` | Triggers `drop_impact` transition (`explosion` `0.4 s`), resetting cooldown timer. |
| `is_drop_imminent` | `context.is_drop_imminent` | Pre-drop indicator from lookahead countdown. |
| `drop_countdown` | `context.drop_countdown` | Schedules `pre_drop_buildup` transition gated by `5.0 s` security cooldown. |
| `is_song_change` | `listener.is_song_change` | Speaker-time song boundary trigger, gated by `5.0 s` security cooldown and `TRANSITION_DUAL` lock. |
| `is_verse_chorus_change` | `listener.is_verse_chorus_change` | Speaker-time structural trigger, gated by `5.0 s` security cooldown and `TRANSITION_DUAL` lock. |
| `live_is_song_change` | `listener.live_is_song_change` | Starts `lookahead_seconds` countdown timer in `Transition_Director`, gated by security cooldown. |
| `live_is_verse_chorus_change` | `listener.live_is_verse_chorus_change` | Starts `lookahead_seconds` structural countdown timer in `Transition_Director`, gated by security cooldown. |
| `lookahead_seconds` | `analyzer.lookahead_seconds` | Lookahead horizon (`5.0 s`) used to initialize boundary countdowns. |

---

## Part B: Current internals (as built, 2026-10-15)

> This part describes the implementation inside the sealed room and its boundary glue. Sections marked **[GAP]** are not wired or not implemented yet.

Source files (all but the last four inside the room):
[`transitions/manager.py`](../../transitions/manager.py) (decision & parameter rolling) ·
[`transitions/director.py`](../../transitions/director.py) (clock + trigger) ·
[`transitions/engine.py`](../../transitions/engine.py) (2D spatial blending & dispatcher) ·
[`transitions/effects.py`](../../transitions/effects.py) (1D strip-intrinsic & organic shaders) ·
[`transitions/families.py`](../../transitions/families.py) (multi-family contracts & generative parameters) ·
[`transitions/stagger.py`](../../transitions/stagger.py) (staggered cohort configs) ·
[`transitions/service.py`](../../transitions/service.py) (front door) ·
[`transitions/mode_dna.py`](../../transitions/mode_dna.py) (mode fingerprints) ·
[`core/TransitionBridge.py`](../../core/TransitionBridge.py) (outside glue) ·
[`core/Segment.py`](../../core/Segment.py) (per-segment dual buffer + 3-layer mode handshake) ·
[`mood/api.py`](../../mood/api.py) (palettes, separate sealed sector) ·
[`modes/Mode.py`](../../modes/Mode.py) (lifecycle hooks & `transition_scale`)

---

## 1. Pipeline: how a transition happens

```
 TRIGGER                DECIDE (LocalTransitionManager)                 EXECUTE
 ───────                ────────────────────────────────                ───────
 Director timer   ─┐    1. evaluate_target_dna(music) → target DNA
 (20 s default)    │    2. choose_cohort_pattern(music) → DIVERSE/SYM/UNISON
 Music triggers    ├──► 3. allocate_all_segments()    → {segment: mode}
 request_next      │    4. select_transition_technique(music) → {type, duration}
 request_drop     ─┘    5. schedule_transition(): queue, wait for beat
                                      │
                                      ▼
                        _execute_transition(): for each non-blocked segment
                          emit SegmentOrder(segment, mode, technique, duration, mode_handshake, ...)
                          if at least 1 segment ordered:
                            set_transition_params(roll_transition_params(primary_tech))
                            Transition_Director.start_transition(cfg) → progress 0→1
                                      │
                                      ▼
                        TransitionBridge.apply_orders() → Segment.change_mode()
                        Segment.update() each frame:
                          if mode_handshake: call on_transition_exit(prog) / on_transition_enter(prog)
                          render old + new mode → TransitionService.blend()
                          at passation completion: copy dual_rgb_list → rgb_list, terminate old mode
```

Timing rules in `LocalTransitionManager.update(dt, music)`:
- A queued transition is held while the Director is already in `TRANSITION_DUAL`.
- It fires when `music.beat_phase < 0.05` (with `beat_trust >= 0.20`) **or** `music.is_beat` **or** after a 1.2 s timeout. (This is "next beat", not a true bar downbeat. The analyzer contract forbids bar assumptions.)
- `quantize_downbeat=False` (used by `request_drop` and music-driven boundary triggers) fires immediately.
- If all segments are blocked (`is_blocked=True`) or no segments are installed, no `SegmentOrder` is emitted and `Transition_Director.start_transition()` is not called (`state` remains `PASSATION`).

---

## 2. Inputs: what it needs (via `MusicSnapshot` and `InstallationSnapshot`)

| Decision | Variables read | How |
| :--- | :--- | :--- |
| **Target DNA** (what the music wants) | `energy`, `salience`, `beat_trust`, `novelty`, `tension`, `is_drop_impact`, `is_syncopated` | `energy = energy`; `punch = 1.0 if drop else 0.6·salience + 0.4·energy`; `rhythm = 0.7·beat_trust + 0.3·salience`; `complexity = 0.4·novelty + 0.3·tension + (0.3 if syncopated else 0.1)`. |
| **Cohort pattern** | `scene`, `is_drop_impact`, `is_syncopated`, `is_locked` | Probability table, see §3.2. |
| **Technique** | `is_drop_impact`, `energy`, `is_rhythmic`, `salience` | See §3.3. |
| **Beat alignment** | `beat_phase`, `beat_trust`, `is_beat` | See §1. |
| **Musical triggers & lookahead** | `live_is_song_change`, `live_is_verse_chorus_change`, `is_song_change`, `is_verse_chorus_change`, `lookahead_seconds`, `drop_countdown`, `is_drop_imminent`, `scene`, `is_drop_impact` | Tracked by `Transition_Director.update(dt, music)`, see §4. |
| **Mode DNA** | `transitions/mode_dna.py` (`energy`, `punch`, `rhythm`, `complexity`, `spatial_role`) | Distance to target DNA. |
| **Geometry** | `SegmentDescriptor` (`name`, `orientation`, `available_modes`, `active_mode`, `is_blocked`) | Cohort discovery and candidate pools. |

**[GAP]** Analyzer gradients (`salience_gradient`, `power_gradient`, `is_structural_cut`) and `is_silent` are not consumed by the transition sector yet.

---

## 3. Decisions: what is chosen

### 3.1 Which modes (weighted lottery)
Per candidate: `w = 1 / (1 + 4·d²)`, where `d²` is the squared Euclidean distance between mode DNA and target DNA over 4 axes. Multipliers:
- `×0.15` if the mode's `spatial_role` conflicts with the cohort orientation.
- `×0.20` if it is the segment's current mode (recency).
- `×0.05` if it equals mode A while drawing mode B (pair contrast).
- Floor `0.001`, so no mode is ever impossible.

### 3.2 Which segments get which pattern
Cohorts are **vertical pillars** (orientation `vertical`, or name containing ` v` / ` s`) and **horizontal rings** (grouped by the first 2 characters of the segment id). Each cohort draws a pattern independently:

| Context | UNISON | SYMMETRIC_PAIRS | DIVERSE |
| :--- | :-: | :-: | :-: |
| default | 0.20 | 0.35 | 0.45 |
| `is_drop_impact` | 0.55 | 0.30 | 0.15 |
| scene `BUILDUP` | 0.40 | 0.40 | 0.20 |
| `is_syncopated` or `is_locked` | 0.15 | 0.45 | 0.40 |
| scene `CHILL` | 0.10 | 0.40 | 0.50 |

SYMMETRIC_PAIRS: n=4 gives ABAB or ABBA (50/50); n=3 gives ABA; n=2 gives AB; otherwise alternating.

### 3.3 Which transition technique (one for the whole installation by default)

Evaluated top to bottom, first match wins:

| Condition | Technique | Engine `type` | Duration |
| :--- | :--- | :--- | :-: |
| `is_drop_impact` or `energy ≥ 0.85` | `transient_blip` | `explosion` | 0.4 s |
| `is_rhythmic` (GROOVE/DROP_IMPACT) or `salience ≥ 0.50` | `directional_wipe` | `vertical_wipe` | 1.2 s |
| otherwise | `smooth_cosine_crossfade` | `fade_in_out` | 2.0 s |

Engine types available in `transitions/engine.py` and `transitions/effects.py`:
- **Classic & Spatial 2D:** `fade_in_out` (`fade_to_black`, `smooth_cosine_crossfade`, `cosine_fade`), `global_change`, `vertical_wipe`, `wipe_left_to_right`, `wipe_right_to_left`, `box_wipe`, `spiral`, `gravity_drop`, `weird_glitch`, `explosion`, plus PNG-mask fallback.
- **Photonic & Organic Dissolves:** `ember_dissolve` (per-LED spatial noise threshold + blackbody gold/amber spark edge), `luma_melt` (luminance-keyed takeover where bright pixels breakthrough first), `breath_dip` (parabolic breath valley with 20% floor glow).
- **1D Strip-Intrinsic Sweeps:** `silk_wipe`, `silk_wipe_reverse` (1D smoothstep wipe along index $u \in [0, 1]$ with specular leading crest), `iris_open`, `iris_close` (symmetric center-out / edges-in aperture along each strip), `zipper_merge` (even/odd LED interleave sliding from opposite ends).
- **Kinetic & Physics:** `collider` (twin cyan/magenta energy packets accelerating from opposite ends and detonating at strip focal point $u$), `prism_sweep` (chromatic RGB phase-split wave), `flash_cut` (instant mode swap at $p=0.12$ masked by an exponential photographic flash).
- **Rhythmic & DJ Cuts:** `staccato_shutter` (accelerating rhythmic square-wave gate between old and new modes), `transformer_cut` (turntablist chop stutter cut).

All selectable names are exported in `transitions.api.AVAILABLE_TRANSITIONS`.

### 3.4 Multi-Family Transition Contracts & Generative Parameters (`transitions/families.py`)

Each transition in `TRANSITION_FAMILIES` belongs to a `frozenset` of one or more abstract `TransitionFamily` contracts. Family memberships govern both **generative parameter rolling** (`roll_transition_params(technique)`) and **choreography compatibility** (`is_staggerable(technique)`, `get_allowed_stagger_patterns(technique)`):

| Family (`TransitionFamily`) | Contract Meaning & Rolled Parameters | Member Transitions |
| :--- | :--- | :--- |
| `ROOM_EPI_2D` | 2D room-space radial/angular transition around an architectural epicenter inside the chandelier core (`epicenter_x ∈ [0.46, 0.78]`, `epicenter_y ∈ [0.38, 0.64]`, `spiral_sign ∈ {-1, +1}`). Always `SIMULTANEOUS` across segments. | `explosion`, `transient_blip`, `spiral`, `box_wipe`, `weird_glitch` |
| `ROOM_SWEEP_2D` | 2D room-space plane or gravity sweep (`beam_thickness ∈ [0.08, 0.22]`). Non-staggerable except `vertical_wipe` / `directional_wipe`. | `vertical_wipe`, `directional_wipe`, `wipe_left_to_right`, `wipe_right_to_left`, `gravity_drop` |
| `STRIP_SWEEP_1D` | 1D strip-intrinsic directional wipe (`edge_width ∈ [0.10, 0.22]`, `reverse`). | `silk_wipe`, `silk_wipe_reverse`, `prism_sweep`, `zipper_merge` |
| `STRIP_FOCAL_1D` | 1D strip-intrinsic focal/aperture transition around a dynamic strip coordinate (`focal_u ∈ [0.28, 0.72]`). | `iris_open`, `iris_close`, `collider` |
| `STAGGERABLE` | Eligible for per-segment stagger offsets (`CASCADE_DOWN/UP`, `CENTER_OUT`, `ALTITUDE_CASCADE_DOWN/UP`, `BAY_WAVE_LR/RL`, `COHORT_COMPLEMENTARY`). | All 1D strip, organic, and rhythmic cut transitions + `vertical_wipe` |
| `STOCHASTIC_ORGANIC` | Per-LED spatial hash permutation (`seed ∈ [0, 99.9]`, `spark_intensity ∈ [0.85, 1.25]`). | `ember_dissolve`, `luma_melt`, `weird_glitch`, `global_change` |
| `RHYTHMIC_CHOP` | Beat/sub-beat stutter & flash parameters (`chop_count ∈ {3, 4, 5}`, `flash_decay ∈ [4.5, 7.5]`). | `flash_cut`, `staccato_shutter`, `transformer_cut`, `explosion` |
| `MODE_COOPERATIVE` | Activates `SegmentOrder.mode_handshake = True` so outgoing/incoming modes physically wind down and bloom in via `on_transition_exit` / `on_transition_enter`. | All organic, 1D sweep/focal, and 2D wipe transitions (disabled on hard rhythmic cuts `flash_cut`, `staccato_shutter`, `transformer_cut`, `explosion`, `weird_glitch`) |

---

## 4. Triggers: what starts one

| Source | Path | Quantized to beat | Technique |
| :--- | :--- | :-: | :--- |
| Director timer (`auto_transition_time`, default 20 s), skipped if `locked` | `update()` (reason: `timer`) | yes | auto |
| Song change countdown arrival at speakers (`upcoming_song_change_countdown <= 0.0`) | `update()` (reason: `song_change`) | no | auto |
| Structural change countdown arrival at speakers (`upcoming_structural_change_countdown <= 0.0`) | `update()` (reason: `structural_change`) | no | auto |
| Pre-drop lookahead alignment (`drop_countdown > 0` or `scene == BUILDUP`) | `update()` (reason: `pre_drop_buildup`) | no | `explosion` ($D = \text{lookahead} / 0.80$) |
| Real-time drop impact transient (`is_drop_impact = True`) | `update()` (reason: `drop_impact`) | no | `explosion` 0.4 s (snaps active explosion to $\ge 0.80$) |
| UI `go_to_next_configuration` / Simulator Transition Tester | `request_next(technique=..., duration=...)` (reason: `request_next`) | yes (1.2 s beat window) | auto or explicit `technique` & optional `duration` ($N$ s) |
| UI `manual_drop` | `request_drop()` (reason: `request_drop`) | no | forced `explosion` 0.4 s |
| UI `select_transition` | retired | n/a | n/a |

Music-driven triggers execute immediately at the speaker boundary time without waiting for downbeat quantization, deferring the periodic fallback timer to avoid collisions.

---

## 5. Outputs: what it provides and what it touches

| Area | Effect |
| :--- | :--- |
| `Segment.change_mode` | Invoked by `TransitionBridge.apply_orders()`. Zero-fills `dual_rgb_list` (preventing stale buffer ghosting), starts the target mode in the secondary buffer with local timing (`duration`, `start_offset`, `technique`, `mode_handshake`), and on completion copies `dual_rgb_list → rgb_list` so stateful trails survive handoff. |
| `Transition_Director` | `state` (`PASSATION` or `TRANSITION_DUAL`), `transition_progress` [0..1], `transition_type`, `transition_duration`, `is_in_transition`, `cooldown_remaining`. Exposed via `TransitionService.get_status()` (which also exposes `is_pending`). |
| Modes (3-Layer Cooperative Handshake) | When `mode_handshake=True`, `Segment.update()` calls `activ_mode_obj.on_transition_exit(prog)` before updating the outgoing mode and `target_mode.on_transition_enter(prog)` before rendering the incoming mode. `Mode` exposes `transition_scale` (combining quadratic exit wind-down with ease-out enter bloom) and accelerates `fade_to_black` during exit. |
| `mood.api.MoodService` | Cosine palette crossfade (default 2 s) and scene modifier smoothing (`create_mood_service(auto_scene=True)`, bound via `Mode.bind_mood_colors` and `Mode.bind_mood_modifiers`), ticked by `Mode_master` (outside the room). |

### Invariants
- One transition at a time installation-wide. The Director holds a single `state` and `transition_progress` spanning the maximum `(start_offset + duration)` of the emitted orders.
- Every non-blocked segment is retargeted on each transition. If all segments are blocked, no transition starts.
- The Director clock advances by `dt` in `Director.update(dt, music)`.
- Hot path: `transitions/manager.py` `update` must satisfy AXIOM-01 (≤ 0.01 ms) and AXIOM-02 (zero allocation). It is covered by `tests/test_mood_and_transitions.py`.

---

## 6. State of implementation

| Area | State |
| :--- | :--- |
| Mode matchmaking (DNA lottery) | Done, tested. DNA entries exist for the modes. Not tuned against real music. |
| Cohort patterns | Done, tested. Cohort detection relies on `orientation` and name-string heuristics. |
| Technique selection, Families & Effects | Done. 23 transition effects mapped across 8 `TransitionFamily` contracts (`transitions/families.py`) with dynamic generative parameter rolling (`roll_transition_params`) and the `Fake_leds.py` / `VisualizerHud.py` Transition Tester UI + left-side `SEGMENT MODES` table. |
| Beat quantization | Done (`beat_phase < 0.05` gated by `beat_trust >= 0.20`, or `is_beat`, or 1.2 s timeout). |
| Music-driven triggers | Done (`song_change`, `structural_change`, `pre_drop_buildup`, `drop_impact`). |
| Lookahead / pre-drop scheduling | Done (`live_is_song_change`, `live_is_verse_chorus_change` countdowns and `pre_drop_buildup` duration scaling $D = \text{lookahead} / 0.80$). |
| Per-mode enter/exit behavior | Done. `Mode.py` implements `_exit_progress`, `_enter_progress`, `transition_scale`, and accelerated exit trail decay; wired into `Plasma_fire_mode`, `Power_bar_mode`, `Middle_bar_mode`, `Extending_waves_mode`, `Shining_stars_mode`, `Flying_ball_mode`, and `Magnetic_ball_mode`. |
| Per-cohort or per-segment technique or staggering | Done. Includes `SIMULTANEOUS`, `CASCADE_DOWN`, `CASCADE_UP`, `CENTER_OUT`, `COHORT_COMPLEMENTARY`, physical $Y$-altitude cascades (`ALTITUDE_CASCADE_DOWN`, `ALTITUDE_CASCADE_UP`), and horizontal bay waves (`BAY_WAVE_LR`, `BAY_WAVE_RL`), gated by `is_staggerable(technique)`. |
| Automatic palette change on transitions | **[GAP]** `PaletteRequest` door exists on `TransitionOrders`, and `TransitionBridge.apply_orders` forwards it to the mood sector, but transitions do not emit palette changes yet. Outside the transition room, `Mode_master` instantiates `create_mood_service(auto_scene=True)` and binds `Mode.bind_mood_colors` and `Mode.bind_mood_modifiers` (plus manual UI `select_mood`). |
| Dwell and cooldown policy between transitions | Done. Minimum security cooldown of 5.0 seconds enforced post-transition across timer and musical triggers; urgent drop impacts and manual UI requests bypass and reset. |
| Silence and standby behavior | **[GAP]** `MusicSnapshot.is_silent` crosses the door, but no silence/standby policy is implemented in the transition sector yet (dead `silence_*` / `is_in_standby` fields removed from `Transition_Director`). |
| Tests | `tests/transitions/` (`test_api_contracts`, `test_families_and_handshake`, `test_transition_engine`, `test_transition_director`, `test_stagger`, `test_sandbox`), `test_mood_and_transitions`, `test_transition_bridge`, and `governance/test_transition_isolation`. |

## 7. Open design questions
1. Which musical events should trigger a transition (drop, structural cut, song change, scene change) versus the timer?
2. Should technique vary per cohort, or by `scene`, instead of one global choice?
3. Minimum dwell time between transitions, and the policy for silence.
4. Should transitions drive palette changes?
