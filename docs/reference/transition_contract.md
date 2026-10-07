# Transition Contract & Strategy Reference

> **Status: DRAFT: documents the system AS BUILT (2026-10-07).** Sections marked **[GAP]** are not implemented and are the open design work.
> Sibling of [`audio_analyzer_contract.md`](audio_analyzer_contract.md): that document defines what the audio side *provides*; this one defines how the transition system *consumes* it and what it *provides* to the rest of the installation.

Source files:
[`core/LocalTransitionManager.py`](../../core/LocalTransitionManager.py) (decision) ·
[`core/Transition_Director.py`](../../core/Transition_Director.py) (clock + trigger) ·
[`core/Transition_Engine.py`](../../core/Transition_Engine.py) (pixel blending) ·
[`core/Segment.py`](../../core/Segment.py) (per-segment dual buffer) ·
[`config/mode_dna.py`](../../config/mode_dna.py) (mode fingerprints) ·
[`core/GlobalMoodManager.py`](../../core/GlobalMoodManager.py) (palettes) ·
[`modes/Mode.py`](../../modes/Mode.py) (lifecycle hooks)

---

## 1. Pipeline: how a transition happens

```
 TRIGGER                DECIDE (LocalTransitionManager)                 EXECUTE
 ───────                ────────────────────────────────                ───────
 Director timer   ─┐    1. evaluate_target_dna(ctx)  → target DNA
 (20 s default)    │    2. choose_cohort_pattern(ctx) → DIVERSE/SYM/UNISON
 go_to_next_config ├──► 3. allocate_all_segments()    → {segment: mode}
 manual_drop      ─┘    4. select_transition_technique(ctx) → {type, duration}
                        5. schedule_transition(): queue, wait for beat
                                      │
                                      ▼
                        _execute_transition(): for each non-blocked segment
                          segment.change_mode(mode, cfg)  → dual-buffer start
                          Transition_Director.start_transition(cfg) → progress 0→1
                                      │
                                      ▼
                        Segment.update() each frame:
                          render old + new mode → Transition_Engine.apply_transition()
                          at PASSATION: terminate old mode, swap active mode
```

Timing rules in `LocalTransitionManager.update(dt)`:
- A queued transition is held while the Director is already in `TRANSITION_DUAL`.
- It fires when `listener.beat_phase < 0.05` **or** `listener.is_beat` **or** after a 1.2 s timeout. (This is "next beat", not a true bar downbeat. The analyzer contract forbids bar assumptions.)
- `quantize_downbeat=False` (used by `manual_drop`) fires immediately.

---

## 2. Inputs: what it needs (all via `listener.context`, speaker-time)

| Decision | Variables read | How |
| :--- | :--- | :--- |
| **Target DNA** (what the music wants) | `energy`, `salience`, `beat_trust`, `novelty`, `tension`, `is_drop_impact`, `is_syncopated` | `energy = energy`; `punch = 1.0 if drop else 0.6·salience + 0.4·energy`; `rhythm = 0.7·beat_trust + 0.3·salience`; `complexity = 0.4·novelty + 0.3·tension + (0.3 if syncopated else 0.1)`. Fallback without `context`: `asserved_total_power`, `rhythm_salience`, `beat_trust`. |
| **Cohort pattern** | `scene`, `is_drop_impact`, `is_syncopated`, `is_locked` | Probability table, see §3.2. |
| **Technique** | `is_drop_impact`, `energy`, `is_rhythmic`, `salience` | See §3.3. |
| **Beat alignment** | `beat_phase`, `is_beat` | See §1. |
| **Mode DNA** | `config/mode_dna.py` (`energy`, `punch`, `rhythm`, `complexity`, `spatial_role`) | Distance to target DNA. |
| **Geometry** | `segment.orientation`, segment names, `segment.modes`, `segment.isBlocked` | Cohort discovery. |

**[GAP]** No lookahead variable is consumed. `live_*`, `drop_countdown`, `is_drop_imminent`, `salience_gradient`, `power_gradient`, `is_structural_cut`, `is_song_change` and `is_verse_chorus_change` are all available (see the analyzer contract) but unused for transitions.

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

### 3.3 Which transition technique (one for the whole installation)

Evaluated top to bottom, first match wins:

| Condition | Technique | Engine `type` | Duration |
| :--- | :--- | :--- | :-: |
| `is_drop_impact` or `energy ≥ 0.85` | `transient_blip` | `explosion` | 0.4 s |
| `is_rhythmic` (GROOVE/DROP_IMPACT) or `salience ≥ 0.50` | `directional_wipe` | `vertical_wipe` | 1.2 s |
| otherwise | `smooth_cosine_crossfade` | `global_change` | 2.0 s |

Engine types available in `Transition_Engine.apply_transition`: `fade_in_out`, `global_change`, `vertical_wipe`, `wipe_left_to_right`, `wipe_right_to_left`, `box_wipe`, `spiral`, `gravity_drop`, `weird_glitch`, `explosion`, plus a PNG-mask fallback. Only 3 are ever chosen automatically.

---

## 4. Triggers: what starts one

| Source | Path | Quantized to beat | Technique |
| :--- | :--- | :-: | :--- |
| Director timer (`auto_transition_time`, default 20 s), skipped if `transition_locked` | `change_configuration(None)` | yes | auto |
| UI `go_to_next_configuration` | `schedule_transition` | yes | auto |
| UI `manual_drop` | `schedule_transition` | no | forced `explosion` 0.4 s |
| UI `select_transition` | retired | n/a | n/a |

**[GAP]** Nothing is triggered by the music itself. The commented-out block in `Transition_Director.update` was the song-change hook. The Director computes `upcoming_song_change_countdown` and `upcoming_structural_change_countdown` but nothing reads them.

---

## 5. Outputs: what it provides and what it touches

| Area | Effect |
| :--- | :--- |
| `Segment.change_mode` | Starts the target mode in a second buffer. A segment already in transition **ignores** new requests. Blocked segments are skipped. |
| `Mode_master.activ_configuration["modes"]` | Updated with the new allocation. `_state_dirty = True`. |
| `Transition_Director` | `state` (`PASSATION` or `TRANSITION_DUAL`), `transition_progress` [0..1], `transition_type`, `transition_duration`, `is_in_transition`. Published in the web state as `transitionState` / `transitionProgress`. `selectedTransition` is always `"DYNAMIC"`. |
| Modes (optional hooks) | `on_transition_exit(progress)` on the outgoing mode and `on_transition_enter(progress)` on the incoming mode, called every frame; `has_custom_transition=True` makes the Segment skip the engine blend and swap immediately. |
| `GlobalMoodManager` | Cosine palette crossfade (default 2 s), ticked by `LocalTransitionManager.update`. |

### Invariants
- One transition at a time installation-wide. The Director holds a single `type` and `progress` shared by every segment.
- Every non-blocked segment is retargeted on each transition (no partial or staggered transitions).
- The Director clock advances in `Director.update`. The Segment reads `td.transition_progress`.
- Hot path: `LocalTransitionManager.update` must satisfy AXIOM-01 (≤ 0.01 ms) and AXIOM-02 (zero allocation). It is covered by `tests/test_mood_and_transitions.py`.

---

## 6. State of implementation

| Area | State |
| :--- | :--- |
| Mode matchmaking (DNA lottery) | Done, tested. DNA entries exist for the modes. Not tuned against real music. |
| Cohort patterns | Done, tested. Cohort detection relies on name-string heuristics. |
| Technique selection | Done but coarse (3 of 10 engine types). Same technique for all segments. |
| Beat quantization | Done. |
| Music-driven triggers | **[GAP]** Timer and manual only. |
| Lookahead / pre-drop scheduling | **[GAP]** Not wired. |
| Per-mode enter/exit behavior | **[GAP]** Hooks exist, and **no mode implements them**. |
| Per-cohort or per-segment technique or staggering | **[GAP]** Not supported by the single-progress Director. |
| Automatic palette change on transitions | **[GAP]** Palette changes only via the UI `select_mood`. |
| Dwell and cooldown policy between transitions | **[GAP]** `_dwell_timer` is incremented and reset but never read. |
| Silence and standby behavior | **[GAP]** `silence_threshold`, `silence_duration_trigger` and `is_in_standby` are initialized in the Director and unused. |
| Tests | 38 transition tests pass (`test_mood_and_transitions`, `test_transition_director`, `test_transition_engine`). |

## 7. Open design questions
1. Which musical events should trigger a transition (drop, structural cut, song change, scene change) versus the timer?
2. Should pre-drop be scheduled from lookahead so the explosion lands on `is_drop_impact`?
3. Should technique vary per cohort, or by `scene`, instead of one global choice?
4. Minimum dwell time between transitions, and the policy for silence.
5. Should transitions drive palette changes?
6. Which modes get custom enter/exit behavior first?
