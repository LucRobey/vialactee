# Transition Sector Contract

Sibling of [`audio_analyzer_contract.md`](audio_analyzer_contract.md). The transition sector lives in `transitions/` and is a **sealed room**: it talks to the rest of the project only through the doors below, defined in code in [`transitions/api.py`](../../transitions/api.py).

## Part A: The Doors (authoritative)

**Wall rules**
1. Nothing in `transitions/` imports from `core/`, `modes/`, `connectors/` or `hardware/`.
2. Nothing outside `transitions/` imports from it except `transitions.api`.
3. `api.py` uses only the standard library and numpy.
4. The front door is **synchronous**.

| # | Door | Dir | Shape (in `api.py`) | Notes |
| :-: | :--- | :-: | :--- | :--- |
| 1 | Music | in | `MusicSnapshot` | Read-only, speaker-time. Fields have defaults so it can grow. |
| 2 | Installation | in | `InstallationSnapshot`, `SegmentDescriptor` | Segments, orientation, modes available, active mode, blocked. `room_bounds` comes from the layout. |
| 3 | Requests | in | `request_next`, `request_drop`, `set_locked`, `set_auto_interval` | The UI and manual input all arrive as requests. |
| 4 | Orders | out | `TransitionOrders` containing one `SegmentOrder` per segment | Each entry has its own mode, technique, duration, direction and `start_offset`. Today all entries are identical. |
| 5 | Acknowledgement | in | `OrderAck` | The caller says which segments accepted (a segment already in transition refuses). |
| 6 | Blending | out | `blend(dest, incoming, progress, technique, coords)` | **In place**, returns nothing, zero allocation per frame. |
| 7 | Progress | out | `TransitionStatus.progress` | Used by the optional mode enter/exit hooks and the UI. |
| 8 | Status | out | `get_status()` → `TransitionStatus` | State, progress, locked, interval, current technique. |
| 9 | Palette request | out | `TransitionOrders.palette` (`PaletteRequest`) | The mood sector (`mood/`, see [mood_contract.md](mood_contract.md)) stays **outside** the room; `TransitionBridge.apply_orders` forwards the request to `mood.api`. |

**Ownership.** The room owns: when to transition, what to play where, how it looks, and timing. The outside owns: segments and their buffers, modes, the palette manager, and the UI. Modes never decide when or how they are replaced; the optional `on_transition_enter/exit` hooks stay on the mode side and receive progress from the caller.

**Change policy.** Inside the room anything may change freely. Changing a door means editing `api.py`, `tests/transitions/test_api_contracts.py` and this section together.

---

## Part B: Current internals (as built, 2026-10-13)

> This part describes the implementation inside the sealed room and its boundary glue. Sections marked **[GAP]** are not wired or not implemented yet.

Source files (all but the last four inside the room):
[`transitions/manager.py`](../../transitions/manager.py) (decision) ·
[`transitions/director.py`](../../transitions/director.py) (clock + trigger) ·
[`transitions/engine.py`](../../transitions/engine.py) (pixel blending) ·
[`transitions/stagger.py`](../../transitions/stagger.py) (staggered cohort configs) ·
[`transitions/service.py`](../../transitions/service.py) (front door) ·
[`transitions/mode_dna.py`](../../transitions/mode_dna.py) (mode fingerprints) ·
[`core/TransitionBridge.py`](../../core/TransitionBridge.py) (outside glue) ·
[`core/Segment.py`](../../core/Segment.py) (per-segment dual buffer + local timing) ·
[`mood/api.py`](../../mood/api.py) (palettes, separate sealed sector) ·
[`modes/Mode.py`](../../modes/Mode.py) (lifecycle hooks)

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
                          emit SegmentOrder(segment, mode, technique, duration, ...)
                          if at least 1 segment ordered:
                            Transition_Director.start_transition(cfg) → progress 0→1
                                      │
                                      ▼
                        TransitionBridge.apply_orders() → Segment.change_mode()
                        Segment.update() each frame:
                          render old + new mode → TransitionService.blend()
                          at passation completion: terminate old mode, swap active mode
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

Engine types available in `transitions/engine.py`: `fade_in_out` (`fade_to_black`, `smooth_cosine_crossfade`, `cosine_fade`), `global_change`, `vertical_wipe`, `wipe_left_to_right`, `wipe_right_to_left`, `box_wipe`, `spiral`, `gravity_drop`, `weird_glitch`, `explosion`, plus a PNG-mask fallback. Only 3 (`fade_in_out`, `vertical_wipe`, `explosion`) are chosen automatically; the rest are dormant unless passed via `request_next(technique=...)`.

---

## 4. Triggers: what starts one

| Source | Path | Quantized to beat | Technique |
| :--- | :--- | :-: | :--- |
| Director timer (`auto_transition_time`, default 20 s), skipped if `locked` | `update()` (reason: `timer`) | yes | auto |
| Song change countdown arrival at speakers (`upcoming_song_change_countdown <= 0.0`) | `update()` (reason: `song_change`) | no | auto |
| Structural change countdown arrival at speakers (`upcoming_structural_change_countdown <= 0.0`) | `update()` (reason: `structural_change`) | no | auto |
| Pre-drop lookahead alignment (`drop_countdown > 0` or `scene == BUILDUP`) | `update()` (reason: `pre_drop_buildup`) | no | `explosion` ($D = \text{lookahead} / 0.80$) |
| Real-time drop impact transient (`is_drop_impact = True`) | `update()` (reason: `drop_impact`) | no | `explosion` 0.4 s (snaps active explosion to $\ge 0.80$) |
| UI `go_to_next_configuration` | `request_next()` (reason: `request_next`) | yes | auto (or explicit `technique`) |
| UI `manual_drop` | `request_drop()` (reason: `request_drop`) | no | forced `explosion` 0.4 s |
| UI `select_transition` | retired | n/a | n/a |

Music-driven triggers execute immediately at the speaker boundary time without waiting for downbeat quantization, deferring the periodic fallback timer to avoid collisions.

---

## 5. Outputs: what it provides and what it touches

| Area | Effect |
| :--- | :--- |
| `Segment.change_mode` | Invoked by `TransitionBridge.apply_orders()`. Starts the target mode in a second buffer with local timing (`duration`, `start_offset`, `technique`). Blocked segments are skipped. |
| `Mode_master.activ_configuration["modes"]` | Updated by `TransitionBridge.apply_orders()` with the new allocation; sets `_state_dirty = True`. |
| `Transition_Director` | `state` (`PASSATION` or `TRANSITION_DUAL`), `transition_progress` [0..1], `transition_type`, `transition_duration`, `is_in_transition`, `cooldown_remaining`. Exposed via `TransitionService.get_status()`. |
| Modes (optional hooks) | `on_transition_exit(progress)` on the outgoing mode and `on_transition_enter(progress)` on the incoming mode, called every frame; `has_custom_transition=True` makes the Segment skip the engine blend and swap immediately. |
| `mood.api.MoodService` | Cosine palette crossfade (default 2 s), ticked by `Mode_master` (outside the room). |

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
| Technique selection | Done for the 3 core types (`fade_in_out`, `vertical_wipe`, `explosion`). **[GAP]** The other 7 engine effects in `transitions/engine.py` are not wired into automatic selection (only reachable via `request_next(technique=...)`). |
| Beat quantization | Done (`beat_phase < 0.05` gated by `beat_trust >= 0.20`, or `is_beat`, or 1.2 s timeout). |
| Music-driven triggers | Done (`song_change`, `structural_change`, `pre_drop_buildup`, `drop_impact`). |
| Lookahead / pre-drop scheduling | Done (`live_is_song_change`, `live_is_verse_chorus_change` countdowns and `pre_drop_buildup` duration scaling $D = \text{lookahead} / 0.80$). |
| Per-mode enter/exit behavior | **[GAP]** Hooks exist on `Mode`, and **no mode implements them**. |
| Per-cohort or per-segment technique or staggering | Engine/manager/segment support is built and tested (`transitions/stagger.py`, `Segment` local offsets, Director max-duration sync), but **[GAP]** `staggered=True` is not wired into automatic transitions or `CommandRouter` yet. |
| Automatic palette change on transitions | **[GAP]** `PaletteRequest` door exists on `TransitionOrders`, and `TransitionBridge.apply_orders` now forwards it to the mood sector, but transitions do not emit palette changes yet (palette changes only via UI `select_mood`). |
| Dwell and cooldown policy between transitions | Done. Minimum security cooldown of 5.0 seconds enforced post-transition across timer and musical triggers; urgent drop impacts and manual UI requests bypass and reset. |
| Silence and standby behavior | **[GAP]** `MusicSnapshot.is_silent` crosses the door, but no silence/standby policy is implemented in the transition sector yet (dead `silence_*` / `is_in_standby` fields removed from `Transition_Director`). |
| Tests | `tests/transitions/` (contracts, service, sandbox, engine, director, stagger), `test_mood_and_transitions`, `test_transition_bridge`, and the wall test `governance/test_transition_isolation`. |

## 7. Open design questions
1. Which musical events should trigger a transition (drop, structural cut, song change, scene change) versus the timer?
2. Should pre-drop be scheduled from lookahead so the explosion lands on `is_drop_impact`?
3. Should technique vary per cohort, or by `scene`, instead of one global choice?
4. Minimum dwell time between transitions, and the policy for silence.
5. Should transitions drive palette changes?
6. Which modes get custom enter/exit behavior first?
