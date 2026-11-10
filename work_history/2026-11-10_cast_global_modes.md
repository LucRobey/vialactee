# 2026-11-10 Cast Global Modes (Segment-as-Fixture Family)

> **Date:** 2026-11-10  
> **Session ID:** `77890469-62c9-4a94-94aa-e2936c2a1993`  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Add a second Global Mode family ("cast") that treats each of the 11 segments as a light fixture with an architectural identity and changes state only on musical steps, plus 6 first cast modes and the matching contract update.  
> **Status:** COMPLETED  
> **Commits:** `53e06a9` (pushed: yes)  
> **Skills Used:** none (followed `.agents/skills/vialactee-mode-creator/SKILL.md` conventions by hand)  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The user found the 5 global modes from `115558e` "too smooth, moving too much, simulating something real as if the chandelier was a screen".
* Diagnosis: all 5 are **field** modes. They sample a continuous function of room coordinates at every LED, so segment boundaries are invisible and the result always glides. The contract itself (Law 8.1 "a ripple expands from a single shared origin", Law 10.3 continuity) pushed toward this.
* Decisions taken with the user:
  * keep both families;
  * first batch = Tableaux, Bar Clock, Construction, Flip-Flop, Negative Space;
  * the fixture look is a per-mode `look` setting.

---

## 2. Changes Made

### Cast engine
* **[NEW]** [`utils/cast.py`](../utils/cast.py):
  * `CAST_TOPOLOGY`: group, colour slot, mirror partner and build order for every canonical segment.
  * `build_fixtures`, which handles all three cases:
    * a canonical segment renders 1 fixture;
    * small-profile and tag-only strips render one sub-fixture per group member;
    * composite studio/test strips render a miniature 11-fixture chandelier.
  * `TABLEAUX_POSES` (sparse / medium / full).
  * `CastClock`: beat-locked steps, plus a bass-onset/timer fallback with hysteresis.
  * Shared looks via `render_fixture`: `snap`, `neon`, `rise`, `flash`.
  * `look_setting`.
* **[NEW]** [`modes/Cast_mode_base.py`](../modes/Cast_mode_base.py) (`ABSTRACT = True`, `FAMILY = "cast"`):
  * Owns the clock, fixtures, look rendering, the silence protocol and the `start()` reset.
  * Concrete modes implement only `on_step` / `on_frame` / `segment_slot`.

### Five cast modes
* **[NEW]** [`modes/Tableaux_mode.py`](../modes/Tableaux_mode.py) (beat / level): held poses, cut every N bars; energy picks the density; never repeats a pose.
* **[NEW]** [`modes/Bar_clock_mode.py`](../modes/Bar_clock_mode.py) (beat / transient): pillars = beat in bar, rungs = bars in phrase, canopy = phrase start.
* **[NEW]** [`modes/Construction_mode.py`](../modes/Construction_mode.py) (beat / transient): one segment per step in build order, hold, blackout, rebuild.
* **[NEW]** [`modes/Flip_flop_mode.py`](../modes/Flip_flop_mode.py) (beat / transient): mirror pairs show one side; checkerboard flips each step; crown on each bar start.
* **[NEW]** [`modes/Negative_space_mode.py`](../modes/Negative_space_mode.py) (transient / level): all lit; hits cut a group by `beat_tag` (kick → pillars, snare → rungs, hat → canopy); `band_flux` onset fallback.
* **[NEW]** [`modes/Mosaic_mode.py`](../modes/Mosaic_mode.py) (beat only, default look `steady`), added after two user follow-ups asking for a simpler mode with no other music reaction:
  * Segments that are on stay on.
  * Each beat exactly one deterministic-random segment changes: it switches on if dark, otherwise it takes a new mood colour.
  * There are no flashes and no drop effect.
  * A first draft, "Spotlight" (one segment lit at a time, jumping each beat), was replaced by this version.
* **[MODIFY]** [`utils/cast.py`](../utils/cast.py): added the `steady` fixture look (plain on/off colour, no white strike frame). It is available to every cast mode.

### Registration, tooling, contract
* **[MODIFY]** [`config/modes.json`](../config/modes.json): 6 entries appended to `global_modes`, using existing vocabulary tags only.
* **[MODIFY]** [`tools/mode_studio.py`](../tools/mode_studio.py): discovery prefers the class named after its module and skips `ABSTRACT` classes. Otherwise the imported `Cast_mode_base` could win the alphabetical `dir()` scan.
* **[MODIFY]** [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md):
  * a two-family table (`FAMILY`);
  * a Door 5 cast topology/clock/looks section;
  * **Part B2 — Cast Mode Laws C1–C6**;
  * scope notes on Laws 1, 8 and 10.3;
  * a D2 rubric note;
  * the cast template.

### Tests
* **[NEW]** [`tests/test_cast_modes.py`](../tests/test_cast_modes.py) covers:
  * helper and clock unit tests;
  * a lockstep 11-segment and 3-segment small-profile run: instances agree, the chandelier changes state, it keeps stepping when beat trust is 0, and silence decays to pure black;
  * per-mode rule invariants;
  * every look renders, with pure-black off pixels;
  * AXIOM-01/02 on `studio_preview` (60 LEDs) and `h00` (205 LEDs);
  * Law 7 dominance;
  * Law 5 honesty (across the MRO) and geometry rebind.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/test_cast_modes.py -q`
  * **Result**: `12 passed, 61 subtests passed`
* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `612 passed, 5 deselected, 248 subtests passed` (baseline 600 + 12 new).
  * Later reruns under machine load: `tests/test_all_modes_musical_context.py::test_axiom_01_frame_execution_time` (standard `Extending_waves_mode`, not touched here) is flaky, measuring 0.21–0.23 ms against a 0.20 ms cap. It fails about 1 in 3 runs even in isolation.
* **Law 7 (synthetic `high_lock`, 40-LED composite)**, lead share / secondary retained:

  | Mode | Lead share | Secondary retained |
  |---|---|---|
  | Tableaux | 0.78 | 1.00 |
  | Bar Clock | 0.71 | 0.95 |
  | Construction | 0.89 | 0.81 |
  | Flip-Flop | 0.88 | 0.98 |
  | Negative Space | 1.00 | 0.91 |

* **Frame cost:** about 0.01–0.03 ms per instance on the dev machine (budget 0.20 ms).
* **Simulator:** not run this session (see Open Items).

---

## 4. Architecture Decisions & Trade-offs

* **Agreement by determinism, not shared state (C5).** Each segment instance computes the same decisions from the same listener inputs, and clocks reset in `start()` and in silence. If a single segment is switched to a cast mode alone, its clock restarts and drifts out of phase with nothing, which is acceptable.
* **One fixture = one segment.** The first version had group "zones" lit when any member was lit. That hid the beat count on composite/small strips: Bar Clock failed Law 7 (transient dominated). Splitting zones into per-member sub-fixtures fixed it, and turned the Studio strip into a miniature chandelier.
* **Drop handling is restrike-only** in Bar Clock and Construction. Structural drop reactions (canopy for a beat, jump to full) out-weighed the beat driver in the Law 7 matrix. Tableaux only biases the *next* cut to a full pose.
* **No `family:` registry tag.** `transitions/policy.py` rejects unknown vocabulary tags and `tests/test_mode_helpers.py` pins the vocabulary, so `FAMILY` lives only as a class attribute.
* **No downbeat in `music/`.** Bar and phrase alignment is arbitrary (relative to mode start), which is acceptable for perception of the 4-cycle.

---

### Live-run fixes (after the user reported Mosaic "not working")
A headless real-app run (`Main.py --song --mode "Mosaic"`, with a silent fake `sounddevice` output stream so playback timing still advances) showed three problems:
* **[MODIFY]** [`Main.py`](../Main.py): `--mode` only forced each segment while the transition sector stayed in local scope, so the startup re-cast replaced Mosaic with local modes after about 1.5 s. This affected every mode passed to `--mode`. `--mode` now:
  * routes a Global Mode through the panel's `set_global_mode` (global scope);
  * starts in HOLD (`set_locked`); LIVE in the panel resumes automatic transitions.
* **[MODIFY]** [`modes/Cast_mode_base.py`](../modes/Cast_mode_base.py):
  * **The problem:** in sparse passages `ctx.is_silent` fires in the gaps between kicks, in 0.03–0.12 s bursts covering 161 of 903 frames on Palladium. Each burst used to reset the cast state, so Mosaic restarted from empty every beat, and faded the chandelier, so it pumped on the beat.
  * **The fix:** cast fixtures now hold through silence shorter than `SILENCE_FADE_S` = 0.6 s, fade only after that, and drain the clock and state only after `SILENCE_RESET_S` = 3 s.
  * **Verified live:** Mosaic fills all 11 segments in about 13 s, then changes one segment per beat, with no dark or dimmed frames.

## 5. Pitfalls & Lessons Learned

* The silence detector (`music/`, Schmitt enter ≤ 0.05) fires between kicks in sparse intros. This also makes field modes flicker. It is a music-sector calibration issue, worth its own look.

* `tests/test_global_modes.py` hardcodes its spec list, and its Mode_master test assumes "Spectral Avalanche" is the last spec. That is why cast modes have their own test file.
* `Mode.py` sits at 498/500 lines (AXIOM-07), so shared cast logic had to live in `utils/cast.py` and `modes/Cast_mode_base.py`.
* A parallel session (HUD split, [`2026-11-10_hud_split_and_dead_prototype_cleanup.md`](2026-11-10_hud_split_and_dead_prototype_cleanup.md)) created `hardware/ShowControlPanel.py` at the same time. Its `_FALLBACK_GLOBAL_MODES` list was deliberately left untouched; it is only used when `config/modes.json` fails to load.

---

## 6. Open Items & Next Steps

* [ ] Live playtest in the simulator (`.\.venv\Scripts\python.exe Main.py --song --mode "Tableaux" --panel`), cycling the 5 cast modes and the 4 looks; tune pose tables, the neon strike and the fallback timer by eye.
* [ ] Add the 5 cast names to `_FALLBACK_GLOBAL_MODES` in `hardware/ShowControlPanel.py` once the HUD-split work is committed.
* [ ] Consider a downbeat estimate in `music/` so Bar Clock / Construction phrases align with real bars.
* [ ] Next cast ideas from the brainstorm: Elevator (quantized floors), Call & Response (left vs right ladder).
