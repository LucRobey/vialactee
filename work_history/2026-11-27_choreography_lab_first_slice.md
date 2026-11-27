# 2026-11-27 Choreography Lab: First Slice

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Start the choreography lab with a slice the owner can look at: one lab mode, three passages, each drawn three times (truth, candidate analyzer, today's analyzer), on a page where the owner chooses.  
> **Status:** COMPLETED (lab folder, feeds, renderer, first mode, first measures, clip page, isolation test; the owner has not watched the clips yet)  
> **Commits:** `09acb4a` (lab), `a71bbf8` (mode profile) (pushed: yes)  
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

### Tests
* **[NEW]** [`tests/governance/test_lab_isolation.py`](../tests/governance/test_lab_isolation.py): the choreography lab imports neither the music lab, nor the truth builders, nor the inside of `music/`; the music side does not import the choreography lab; the check is itself checked.
* **[NEW]** [`research/tests/test_choreography_lab.py`](../research/tests/test_choreography_lab.py): layout, feed semantics, measures, and a clip rendered on a made-up song (shape, light, punch on the kicks it is fed, same input gives same frames).

### Other
* **[MODIFY]** `.claude/launch.json`: `choreography-clips`.

No change to `modes/`, `music/` or `mood/`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 689 passed, 5 deselected, 406 subtests passed (682 before the profile was added).
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

## 6. Open Items & Next Steps

* [ ] Owner: watch the three clips on http://127.0.0.1:8768 and choose; say what is wrong with the mode itself.
* [ ] According to the verdicts and the profile: tune the mode (bass glow swamped by the kick flash), the kick, or the measures.
* [ ] Profile: thresholds, the mute test on real music, and a check of each number against the owner's choices.
* [ ] Lab: the "realistic" feed, more measures, random passages on held-out tracks, comparing two modes, a check on the real installation.
* [ ] Owner: answers on papers P2 to P4 (P3 is this lab's rulebook).
