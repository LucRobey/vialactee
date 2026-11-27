# 2026-11-27 Choreography Lab: First Slice

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Start the choreography lab with a slice the owner can look at: one lab mode, three passages, each drawn three times (truth, candidate analyzer, today's analyzer), on a page where the owner chooses.  
> **Status:** COMPLETED (lab folder, feeds, renderer, first mode, first measures, clip page, isolation test; the owner has not watched the clips yet)  
> **Commits:** `09acb4a` (lab), `a71bbf8` (mode profile), `e95393b` (four fixes) (pushed: yes, except `e95393b`)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-mode-creator`: written for registered modes in `modes/`; says nothing of a lab candidate, of reading `listener.signals`, or of naming a fallback per signal.

---

## 1. Context & Motivation

* The music lab's pilot produced five new signals with scores but no picture. The owner asked to build the choreography lab. `PLAN.md` chapter 3 (thin slice) and the start of chapter 7.

---

## 2. Changes Made

### Lab (`research/choreography/`)
* **[NEW]** `layout.py`: 11 segments, 1,304 LEDs and their room coordinates from `config/segments_full.json`.
* **[NEW]** `feeds.py`: `Feed` (one row per frame at 60 fps, one column per contract slot, NaN = leave the slot alone), `truth_feed` (every slot from a truth file) and `recording_feed` (the slots an analyzer produced, from the music lab's recording).
* **[NEW]** `render.py`: plays the song from its start through the production `Listener` with the 5 s look-ahead, applies the feed to `listener.signals` after each update, updates the mood service, draws one mode instance per segment, keeps 30 frames per second for the passage.
* **[NEW]** `measures.py`: `kick_punch` (jump of brightness on true kicks against the jump halfway between kicks) and `alive`.
* **[NEW]** `build_clips.py`: a clip = audio of the passage + one frame file per feed + `meta.json`; `--defaults` builds three passages (Plastic People 3:28, Another One Bites The Dust 0:30, Nobody Rules the Streets 2:40).
* **[NEW]** `clip_server.py`, `clips.html` (port 8768, launch name `choreography-clips`): three versions side by side on a drawing of the installation, shuffled and unlabelled until the owner chooses; each choice appended to `verdicts.jsonl`.
* **[NEW]** `candidates/Kick_bands_mode.py`: first lab mode. Height is pitch (bass low, treble high, each in its own palette colour); the kick flashes the lower part and sends a front up the pillars; the snare answers from the top; a drop lights everything. Reads `kick`, `snare`, `drop`, `band_bass`, `band_mid`, `band_high` from `listener.signals`, each with a fallback on today's analyzer. Not registered.
* **[NEW]** `README.md`, `.gitignore` (clips are not committed: they contain audio).

### Mode profile (added the same day, at the owner's request: "how can an agent have an idea of what a choreography does")
* **[NEW]** `profile.py`: `passage_truth` (the truth of a passage on the clip's clock), `profile` (light, loudness, reactions around kick / snare / beat / drop / section change with size, delay and fade, kick contrast, behaviour in a break and in a no-beat stretch, light by height and by role, bottom-follows-bass and top-follows-treble, segments together, colours, flicker, bar-to-bar likeness) and `describe` (the same as sentences).
* **[NEW]** `pictures.py`: time strip, contact sheet, reaction curves, drawn with Pillow.
* **[NEW]** `profile_clip.py`: writes `output/profiles/<clip>/PROFILE.md`, `profile.json` and three pictures per version.
* **[MODIFY]** `feeds.py`: a held value (bar position, beat strength, tempo) is now read half a frame late, so the frame a beat falls on carries that beat's value; before, bars were found one beat off and irregular.
* **[NEW]** [`research/tests/test_choreography_profile.py`](../research/tests/test_choreography_profile.py): 7 tests on a made-up show.

### Four fixes after a research pass (same day)
A sub agent surveyed how lighting research and practice evaluate shows; four of its points were checked against the code and applied.
* **[MODIFY]** `render.py`: `perceived` (CIE lightness of a share of full light), `screen_values` (drive values re-coded for a screen), `brightness` now perceived; every frame is kept (`KEEP_EVERY = 1`, clips at 60 fps).
* **[MODIFY]** `profile.py`: all brightness numbers are perceived; `reaction` reports `half_rise_ms`, read between frames; `flashes_per_second` and `safety` (WCAG 2.3.1 general flash, worst of the whole installation and three height zones); `seen_flashes` and `match_flashes` (hits that get a flash, flashes that have a hit, false flashes, flashes per second in breaks).
* **[MODIFY]** `feeds.py`: `Feed.shifted` (every moment moved later); `build_clips.py` renders a fourth, hidden version `control` (truth shifted by half a beat).
* **[MODIFY]** `pictures.py` and `clips.html`: values shown as the LEDs would look; the page has a switch for raw values, hides the control, locks the buttons after a choice, and no longer adds neighbouring LEDs up to white.

### Tests
* **[NEW]** [`tests/governance/test_lab_isolation.py`](../tests/governance/test_lab_isolation.py): the choreography lab imports neither the music lab, nor the truth builders, nor the inside of `music/`; the music side does not import the choreography lab; the check is itself checked.
* **[NEW]** [`research/tests/test_choreography_lab.py`](../research/tests/test_choreography_lab.py): layout, feed semantics, measures, and a clip rendered on a made-up song (shape, light, punch on the kicks it is fed, same input gives same frames).

### Other
* **[MODIFY]** `.claude/launch.json`: `choreography-clips`.

No change to `modes/`, `music/` or `mood/`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 696 passed, 5 deselected, 406 subtests passed (682 before the profile, 689 before the four fixes).
* **Clips built** (`build_clips --defaults`), kick punch contrast (0 = the light ignores the kicks; share of full brightness):

| Passage | Truth | Candidate analyzer | Today's analyzer |
| :--- | ---: | ---: | ---: |
| Plastic People 3:28 (break, kick returns) | 0.23 | 0.19 | 0.21 |
| Another One Bites The Dust 0:30 | 0.31 | 0.25 | 0.26 |
| Nobody Rules the Streets 2:40 (break, kick returns) | 0.17 | 0.19 | 0.20 |

* **Page checked in the browser** by the agent: three clips load, the installation is drawn, playback position is shared, a choice is saved and the versions are then named. The test choice was removed. The agent cannot judge how the clips look in motion or with sound.

---

* **Profile of the three clips** (`profile_clip`), mode `Kick_bands_mode`. Plastic People from 3:28:

| | Truth | Candidate analyzer | Today's analyzer |
| :--- | ---: | ---: | ---: |
| Jump on a kick | 19% | 12% | 13% |
| Jump on a snare | 22% | 9% | 14% |
| Jump on the drop | 72% | 11% | 5% |
| Movement in the break, against normal | 11% | 60% | 92% |
| Bottom follows bass | 0.15 | -0.02 | 0.01 |

  * The pictures were read by the agent. On today's analyzer the time strip shows regular kick and snare flashes all through the break, where the truth has none, and after the kick returns the flashes are spaced at the analyzer's wrong tempo; the drop is missing. The candidate removes most of the fake kicks in the break but keeps the fake snares (it has no snare signal, so the mode falls back on today's beat tag).
  * The mode itself has a fault the profile caught: on Plastic People the bottom does not follow the bass even on truth (0.15), because the kick flash swamps the bass glow there.

* **After the four fixes**, Plastic People from 3:28 (brightness as the eye sees it):

| | Truth | Candidate | Today | Wrong on purpose |
| :--- | ---: | ---: | ---: | ---: |
| Jump on a kick | 12% | 7% | 8% | -5% |
| Light halfway up after the kick | -7 ms | 14 ms | 7 ms | - |
| Real hits that get a flash | 62% | 48% | 50% | 16% |
| Flashes that fall on a real hit | 80% | 48% | 41% | 23% |
| Flashes per second in breaks | 0.4 | 1.4 | 2.4 | 0.3 |
| Most large flashes in one second (limit 3) | 3.5 | 3.0 | 3.5 | 3.5 |

  * Seen as the eye sees it, the mode is brighter on average (59% against 31% in drive values) and its kick punch is weaker (12% against 19%): the resting glow eats the contrast.
  * The control collapses as it should (kick jump -5%, 23% of flashes on a real hit): the mode is tied to its feed.
  * `Kick_bands_mode` goes over the flash limit when fed by the truth on all three clips (3.5, 5.0 and 7.0 large flashes in the worst second).

---

## 4. Architecture Decisions & Trade-offs

* **A feed is data, not code.** The candidate version is driven by the music lab's recording of the candidate analyzer, not by importing that analyzer. This keeps the import wall intact and makes the contract's slot names the only interface.
* **Only the signals under test differ.** Energy, beat phase and mood come from the production `Listener` in all three versions.
* **The song is played from its start** for every clip (about 5 s of computing per feed), so the analyzer is in the state it would be in on the installation, drift and all.
* **A page, not a video.** Frames are raw bytes drawn on a canvas in step with the audio; no video encoder is needed.
* **Hue-preserving limit in the lab mode.** Clipping each channel turned the kick flash white and hid the bass colour; an over-bright LED is scaled down as a whole.

---

## 5. Pitfalls & Lessons Learned

* **The first measure does not separate the versions.** Today's analyzer gets about the same kick punch as the candidate, because its fallback (a beat tagged "kick") lands on most kicks of these songs. Either the measure is too coarse, or the new kick signal brings little to this mode on these passages. Only the owner's eye can tell which.
* **Truth curves and candidate levels are on different scales** (truth: 50 dB under the track's loud level; candidate: 50 dB under a falling ceiling). Versions can differ in brightness for that reason alone.
* **The curves of a truth file are not committed** (`research/truth/tracks/*.curves.npz`): `truth_feed` needs `build_truth.py` to have run on the machine.

---

* **The installation may not run the analyzer at the rate every lab tool assumes.** `core/Mode_master.py` paces its loop at `target_fps` 30 and calls `listener.update()` once per loop (unless the audio-file connector clocks the listener itself), while the analyzers hard-code `odf_fps = 60.0` and the scoreboard, the probe and this lab step the `Listener` at 60 Hz. A quick test on Stayin' Alive (scratch script, not kept): stepped at 60 Hz the production analyzer scores beat F1 99; stepped at 30 Hz it reports the right tempo and the right number of beats, but F1 falls to 10, because the beats are out of phase with the music. Not verified on the installation itself, and not fixed.

## 6. Open Items & Next Steps

* [ ] **Check the 30 against 60 updates per second question on the real installation** (see section 5). If confirmed it outweighs everything else here: every score we have was measured at 60.
* [ ] `Kick_bands_mode`: lower the resting glow (weak punch as the eye sees it) and bring its flashes under three per second.
* [ ] Owner: watch the three clips on http://127.0.0.1:8768 and choose; say what is wrong with the mode itself.
* [ ] According to the verdicts and the profile: tune the mode (bass glow swamped by the kick flash), the kick, or the measures.
* [ ] Profile: thresholds, the mute test on real music, and a check of each number against the owner's choices.
* [ ] Lab: the "realistic" feed, more measures, random passages on held-out tracks, comparing two modes, a check on the real installation.
* [ ] Owner: answers on papers P2 to P4 (P3 is this lab's rulebook).
