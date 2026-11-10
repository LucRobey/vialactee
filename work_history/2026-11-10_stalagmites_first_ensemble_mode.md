# 2026-11-10 Stalagmites: First Ensemble Global Mode

> **Date:** 2026-11-10  
> **Session ID:** `18db9bd6-5abd-4710-b19f-969e52258417`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Build the first mode of the new ensemble family ("Stalagmites"), with the shared ensemble base class and the per-part mute test the contract asks for.  
> **Status:** COMPLETED (third version, approved by the user after viewing it live)  
> **Commits:** `7d9a207` (pushed: yes)  
> **Skills Used:** none (followed `.agents/skills/vialactee-mode-creator/SKILL.md` conventions by hand)  
> **Skill Friction:** `vialactee-mode-creator`: says nothing about Global Modes or their families; the global mode contract is the only guide.

---

## 1. Context & Motivation

* Follow-up to [`2026-11-10_ensemble_family_contract_amendment.md`](2026-11-10_ensemble_family_contract_amendment.md) (commit `d347f89`), which added the ensemble family to the contract without any code.
* The user asked to start on the brainstormed modes. Stalagmites is the user's own example ("pillars are power bars in different orientations, another segment shows the high frequencies") and carries the infrastructure every later ensemble mode needs.
* **User feedback on the first version** (bars following band energy, mood-palette colours): "I really like the idea, but the values represented are too simple, we don't feel the boum tchak of the beat at all, we don't realise that the bass are the red ones and the high the blue ones." The second version below answers that.
* **User feedback on the second version** (bars thrown instantly by each hit, white rung strikes): "like it but too violent. we need to smooth the bass and high values." Answered by the `smoothness` setting (default 0.5): the displayed bar rises toward the thrown height over about 0.1 s instead of jumping, the fall is slower (`fall_rate` 6 → 4.5), and the white rung strike frame only exists below smoothness 0.25. The user viewed this third version live and approved the default smoothness.

---

## 2. Changes Made

### Ensemble engine
* **[NEW]** [`modes/Ensemble_mode_base.py`](../modes/Ensemble_mode_base.py) (`ABSTRACT = True`, `FAMILY = "ensemble"`):
  * Resolves the parts one segment instance renders by reusing `utils.cast.build_fixtures` (canonical segment = 1 part; small-profile strip = its group; composite studio strip = miniature 11-segment chandelier).
  * Hooks: `part_of`, `on_bind`, `on_reset`, `on_frame(ctx, dt)`, `render_part(part, fx, out)`.
  * Shared mechanics: `draw_bar` (from either end of a part) and `draw_solid` (with optional white strike frame).
  * Silence protocol with a 0.6 s debounce; `start()` resets state so all segments agree (Law E5).
  * `part_slices()` exposes (part, start, stop) for tests and tooling.

### The mode (second version)
* **[NEW]** [`modes/Stalagmites_mode.py`](../modes/Stalagmites_mode.py) (lead `transient`, secondary `spectrum`), five parts, all driven by onset strength (`band_flux`) in their own frequency range:
  * `stalagmites` (inner pillars `v2`, `v3`): red bar thrown up from the floor by each onset in 20–400 Hz (kick, bass notes).
  * `stalactites` (outer pillars `v1`, `v4`): blue bar thrown down from the top by each onset in 1.8–5 kHz (snare crack, claps).
  * `bass_rungs` (mid rungs `h11`, `h32`): struck (white frame, then ring down in red) when a bass hit throws its bar past 75% of the pillar.
  * `treble_rungs` (low rungs `h10`, `h31`): same for the blue bar.
  * `canopy` (`h00`, `h20`, `h30`): each onset in 6.5–20 kHz (hi-hats) lights a new random handful of 8-LED cells; `drop_hit` flashes the whole canopy for one frame.
  * A thrown bar reaches a height set by the hit's strength, then falls back under gravity (full bar down in about 0.37 s).
  * A held note keeps a stub of at most 18% of the pillar lit (this is the `spectrum` secondary).
  * Colours are fixed by default: red bass, blue treble, cyan canopy. The `mood_palette` setting switches to mood slots 0 / 1 / 2.
  * Settings: `gain`, `fall_rate`, `smoothness`, `sparkle_density`, `mood_palette`. `smoothness` 0 gives the raw second version (instant jumps, white rung strikes); 1 gives a slow swell.
* **[MODIFY]** [`config/modes.json`](../config/modes.json): "Stalagmites" appended to `global_modes` (`lead:transient`, `color:own-hue`).

### Verification tooling and tests
* **[NEW]** [`tools/ensemble_matrix.py`](../tools/ensemble_matrix.py): per-part mute measurement (Law E3). `python -m tools.ensemble_matrix Stalagmites_mode` prints the table.
* **[NEW]** [`tests/test_ensemble_modes.py`](../tests/test_ensemble_modes.py): declared score, part resolution, lockstep agreement / aliveness / silence, per-part mute test, AXIOM-01/02, Law 5, real `Mode_master` part resolution, and seven rule tests for Stalagmites (kick, hit strength, snare, held note, canopy, drop, palette setting).

### Contract
* **[MODIFY]** [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md): the Law E2 example is the real mode; the base class and its hooks are documented; Law E4's debounce applies to every part; Law E3 allows a small second signal that still passes the mute test; Part C.1 names the test file and the tool.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `628 passed, 5 deselected, 275 subtests passed in 49.61s` (third version)
* **Per-part mute test** (`python -m tools.ensemble_matrix Stalagmites_mode`):

  | Part | Driver | R_std | all muted | d(beat) | d(level) | d(spectrum) | d(transient) |
  |---|---|---|---|---|---|---|---|
  | stalactites | transient | 44.82 | 0.00 | 0.00 | 0.00 | +3.01 | +41.70 |
  | stalagmites | transient | 34.42 | 0.00 | 0.00 | 0.00 | +4.78 | +29.34 |
  | treble_rungs | transient | 49.68 | 0.00 | 0.00 | 0.00 | 0.00 | +49.68 |
  | bass_rungs | transient | 40.64 | 0.00 | 0.00 | 0.00 | 0.00 | +40.64 |
  | canopy | transient | 45.38 | 0.00 | 0.00 | 0.00 | 0.00 | +45.38 |

* **Real audio, offline** (production `Listener`, 11 segments at real LED counts, 10 s from 0:45, scratch scripts, not committed):

  | Track | Bass rung strikes/min | Treble rung strikes/min | Canopy onsets/s |
  |---|---|---|---|
  | Pumped Up Kicks | 42 | 54 | 2.6 |
  | Stayin' Alive | 48 | 84 | 3.8 |
  | Another One Bites The Dust | 60 | 54 | 3.4 |
  | Les copains d'abord | 54 | 72 | 2.2 |

  On Pumped Up Kicks the time-strip image shows the blue bar reaching full length on the backbeats (about one beat in two) and the red bar spiking on the beats and bass notes in between. All 11 instances agreed on the bar heights.
* **Hardware / Simulator Check**: the user viewed all three versions live (feedback in section 1) and approved the third. The agent did not run the simulator itself.

---

## 4. Architecture Decisions & Trade-offs

* **The real geometry chose the casting.** The inner pillars stand on the floor and stop at the mid rungs (y 245 → 73); the outer pillars hang from the canopy and stop at the low rungs (y 16 → 188). So inner = stalagmites, outer = stalactites, and each rung sits exactly at the tip of one bar.
* **Onset strength, not band energy (second version).** Measured on "Another One Bites The Dust": `asserved_fft_band` is smoothed so heavily that the low bands never drop below about 0.4 during the riff, and a kick moves them by about 0.2. `band_flux` shows the same kick as a 1–3 frame spike of 1000+ against a resting value of 0. Bars following the energy cannot show a beat; bars thrown by the flux can.
* **Narrow, named frequency ranges.** Bass = Mel bands 0–1 (20–400 Hz), snare = bands 6–9 (1.8–5 kHz), hi-hat = bands 11–15 (6.5–20 kHz). The first version used the lowest and highest quarters, which mixed voices and guitars into the bass bar and showed hi-hats instead of the snare.
* **How kick and snare are told apart.** On real songs a snare produces onsets in both the low and the snare range (its body thumps), a kick only in the low range. So: the blue bar needs a strong snare-range onset (gate 0.35, curve 1.3, so hi-hat leakage stays small), and the red bar is held back by 25% when the blue one fires. A lone kick is therefore the tallest red; a snare is the tallest blue with a shorter red.
* **Per-band slow-peak scale** (decay 0.07/s, floored at 20% of a very slow peak). Flux magnitudes differ by two orders of magnitude between low and high bands, so each band is compared to its own recent maximum. The slow decay keeps hit strength readable: a hit half as strong throws the bar about half as far.
* **Gravity fall instead of exponential decay.** The bar hangs briefly at the top, then accelerates down, which reads as a thrown object.
* **Fixed warm / cold colours.** With mood-palette colours the user could not tell which bar was the bass. Red for low and blue for high is the convention `Extending_waves_mode` already uses (`color:own-hue`).
* **Canopy sparkles in cells, not a whole-canopy flash.** Hi-hats arrive up to 8 times a second; flashing 343 LEDs at that rate would be a strobe.
* **Silence debounce for continuous parts too.** On "Another One Bites The Dust" 15–20% of frames are flagged silent (gaps in a sparse riff).

---

## 5. Pitfalls & Lessons Learned

* Checking a mode with statistics and time-strip images did not reveal that the first version had no punch: the bars moved, the numbers looked healthy. Only the user's eyes caught it. For rhythm legibility, look at the raw signal around a known kick before choosing what drives a bar.
* A fast-decaying onset scale (0.35/s) saturates: every beat reads as strength 1.0 in every band, so kick and snare look identical. The slow scale is what makes them differ.
* The synthetic clip's flux burst walks through the bands slowly: with the standard 120-frame window the top bands never fire. `tools/ensemble_matrix.py` uses a 480-frame window for that reason.
* `band_flux` on real audio ranges from tens (high bands) to thousands (low bands), while some existing modes compare it to 0.30 or 0.35 in absolute terms.
* `_FALLBACK_GLOBAL_MODES` in `hardware/ShowControlPanel.py` (uncommitted, from the HUD-split session) does not list Stalagmites or the cast modes. It is only used when `config/modes.json` fails to load.

---

## 6. Open Items & Next Steps

* [ ] Further tuning by eye if wanted (`.\.venv\Scripts\python.exe Main.py --song --mode "Stalagmites" --panel`): `SNARE_DUCK`, `BASS_BOOST`, `SNAP_GATE`, rung threshold, and the canopy's one-frame white sparks.
* [ ] On four-on-the-floor tracks with a bright kick (Stayin' Alive) the snare range fires on every beat, so red and blue jump together there. A better kick/snare classifier would need more than two frequency ranges.
* [ ] The app renders at 30 FPS; the offline checks ran at 60. A one-frame onset should still be seen, but this was not verified at 30 FPS.
* [ ] Global modes are not listed in `docs/reference/modes_catalog.md` (the catalog covers the 13 standard modes only).
* [ ] Next ensemble candidates: Four Voices, Snapshot, Dashboard.
