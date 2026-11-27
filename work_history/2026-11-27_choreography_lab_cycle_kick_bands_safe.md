# 2026-11-27 Choreography Lab Cycle: Kick_bands_mode Made Safe (C01)

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388` (sub-agent)  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** First cycle of the choreography lab run by an agent alone: take line C01 of the work list and make a flash-safe lab mode from `Kick_bands_mode`.  
> **Status:** COMPLETED (mode written, gate passed on round 5 of 6, nominated for the owner; nothing promoted, nothing committed)  
> **Commits:** none (pushed: no)  
> **Skills Used:** `light-cycle`, `vialactee-choreographer`, `vialactee-mode-creator`  
> **Skill Friction:** `vialactee-choreographer`: see section 5 (the guard fails on another agent's file; nominating against the mode one improves is refused; the gate cannot show that a mode is safe on fast music).

---

## 1. Context & Motivation

* Launched with `/light-cycle`, no argument: the first `open` line of [`research/choreography/BACKLOG.md`](../research/choreography/BACKLOG.md) is C01, "Make `Kick_bands_mode` safe" (it fails the gate on flash safety: up to 7 flashes in one second, the limit is 3).
* Read first: the work list, [`research/choreography/STATUS.md`](../research/choreography/STATUS.md), [`research/choreography/README.md`](../research/choreography/README.md), the gate report and the profiles of `Kick_bands_mode`.

---

## 2. Changes Made

### Lab mode
* **[NEW]** [`research/choreography/candidates/Kick_bands_safe_mode.py`](../research/choreography/candidates/Kick_bands_safe_mode.py): a copy of `Kick_bands_mode` (three coloured zones by height, the kick punches from the floor, the snare from the top, a drop everywhere) with the light split in two layers.
  * **Resting layer** (the zones and the soft pulses): its light is measured on every frame on each third of the height of the segment and scaled down when it goes over 7% of full light. A flash needs a swing of 10%: this layer alone cannot make one.
  * **Flash layer** (the full punches): rationed. A hit starts a full punch only if the last one is at least 0.46 s old. A hit that comes sooner gets a soft pulse in the resting layer (a thin line climbing the pillars for a kick, one LED in ten sparkling up high for a snare).
  * A full punch is held three frames at its top; a hit that falls inside joins it (in the truth files a drop falls one or two frames after its kick).
  * The zones are much dimmer than in `Kick_bands_mode` (drive 0.012 to 0.12 instead of 0.10 to 0.65) and follow the level to the power 3.
  * Same signals and fallbacks as `Kick_bands_mode`: `kick`, `snare`, `drop`, `band_bass`, `band_mid`, `band_high`.

### Test
* **[NEW]** [`research/tests/test_choreography_candidate_Kick_bands_safe_mode.py`](../research/tests/test_choreography_candidate_Kick_bands_safe_mode.py): 8 tests on made-up signals, flashes counted with the lab's own counter: the resting layer never goes over its limit and never flashes (also on an all-white palette); hits ten times a second stay within three flashes a second; a steady kick every 0.5 s gets a full punch every time; a kick that comes too soon gets a soft pulse; a drop two frames after its kick still lights everything; a second kick that joins a punch does not make a second flash; empty slots fall back; same input, same frames.

### Lab records (written by the tools)
* **[MODIFY]** `research/choreography/gates.json`, `research/choreography/queue.json`, `research/choreography/STATUS.md`, `research/INBOX.md`.
* **[MODIFY]** [`research/choreography/BACKLOG.md`](../research/choreography/BACKLOG.md): C01 done; C07 to C09 added.
* **[MODIFY]** [`research/OWNER_QUESTIONS.md`](../research/OWNER_QUESTIONS.md): two questions (the 0.46 s ration; the gate's flash rule is tried on three passages only).

No change to `modes/`, `music/`, `core/`, `config/`, `docs/`, `tests/`, nor to the gate, the measures or the profile.

---

## 3. Verification & Testing

* **Gate**: `research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.check_mode Kick_bands_safe_mode`
  * **Result**: PASSED (exit 0). 12 of 12 versions drawn; today: dark 0% of the time, the light travels 55%; flash safety: at most 2.5 flashes in one second on every passage, truth and today (`Kick_bands_mode`: 7.0); tied to the music: 100% of the flashes on a real hit on the truth, 25% on the control; 0.77 ms a frame on this PC.
* **Profile, truth feed** (Plastic People / Another One Bites The Dust / Nobody Rules the Streets), `Kick_bands_mode` in brackets:
  * jump on a kick, as the eye sees it: +25% / +32% / +17% (+12% / +20% / +11%); halfway up 3 to 6 ms before the sound;
  * jump on a drop: +77% / - / +76% (+51% / - / +48%);
  * average brightness 34% / 37% / 34% (59% / 60% / 64%);
  * real hits that get a visible flash: 48% / 62% / 53% (62% / 62% / 59%): the hits refused by the ration;
  * bottom follows bass 0.04 / 0.60 / 0.53 (0.16 / 0.78 / 0.61); top follows treble 0.54 / 0.56 / 0.35 (0.74 / 0.73 / 0.38);
  * movement in a break against normal: 10% / - / 43%.
* **Profile, today feed**: jump on a kick +10% / +19% / +10%, halfway up 28 / 20 / 18 ms after the sound; flashes in breaks 0.9 and 1.5 a second and movement in a break 75% and 100% of normal (the false kicks and the snare fallback of today's analyzer: line C03).
* **Made-up fast hits** (scratch scripts outside the repository, the lab's own flash counter, 30 s runs, 5 palettes, random kicks and snares at 1.5 to 12 a second each, random drops and levels), final code: 0 of 160 random runs over 3.0 flashes in a second (worst 3.0); 0 of 90 runs of steady kicks (every 0.33 to 0.6 s) and of hits ten times a second (worst 3.0); 0 of 80 random runs drawn at 30 frames a second (worst 3.0). Earlier rounds on the same hits: 0.40 s ration, 4 of 170 runs at 3.5; rounds 2 and 3 (the front bug of section 5), 9 of 160 runs over, worst 4.0. This is evidence, not a proof: the scripts are not in the repository and the hits are made up.
* **Tests**: `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance`
  * **Result**: 187 passed, 140 subtests passed (8 of them are the new file).
* **Guard**: `python -m research.guard check choreography`
  * **Result**: exit 1, one path: `research/scoreboard/README.md`, changed during this cycle by someone else (a music-lab cycle was running in the same folder; its own files are listed as notes). Every change of this cycle is inside what the choreography lab may change.
* **Nomination**: `nominate Kick_bands_safe_mode --note "..."`: 3 clips in the owner's queue (`19_0208_Kick_bands_safe_mode_n1`, `13_0030_Kick_bands_safe_mode_n1`, `20_0160_Kick_bands_safe_mode_n1`), each showing the mode on the truth and on today's analyzer. `--against Kick_bands_mode` was refused (that mode failed its gate).
* **Rounds**: 5 of the 6 allowed. 1: ration 0.40 s (gate passed at 3.0, not safe on made-up hits). 2: ration 0.46 s and the three-frame hold. 3: dimmer, steeper zones. 4: one front per full punch. 5: soft pulses drawn thin and bright. The gate passed on every round.

---

## 4. Architecture Decisions & Trade-offs

* **A ration on events, not a brake on the light.** Every copy of the mode (one per segment) hears the same hits on the same frame, so a ration counted in time is the same everywhere without any shared state. A brake that watches the light itself would need the light of the whole installation, which a segment's copy does not have.
* **0.46 s and not 0.40 s.** Round 1 used 0.40 s and passed the gate at exactly 3.0. On made-up fast hits it reached 3.5 flashes in a second in 4 of 170 runs: when one punch fades late (a weak one, or the long tail of a drop) and three more follow at the shortest spacing, seven turns of the light fit in one second. With 0.46 s that needs a punch fading 0.38 s later than another. Price: a steady kick keeps its full punch on every beat up to 130 beats a minute (150 with 0.40 s); faster, every other kick is soft. Asked to the owner.
* **The limit on the resting layer is counted per third of each segment**, with the same cut as the profile (altitude under 1/3, over 2/3). The mean of a third of the installation is a mix of these means, so the limit holds for the zones the gate counts.
* **Dim zones.** With the zones of `Kick_bands_mode` scaled to 28% (round 2) the limit was acting on the pillars 56 to 64% of the time: the bass zone was flattened and the other zones of the same pillar dimmed with it. With the dimmer, steeper zones it acts 1% of the time on the truth feed and 17% on today, during soft pulses (measured at round 3, on Another One Bites The Dust).

---

## 5. Pitfalls & Lessons Learned

* **The gate can pass a mode that is not safe.** The three standard passages have no kick faster than about 128 beats a minute and no fast irregular hits. Round 1 passed and was over the limit on made-up hits. A lab agent cannot change the gate: reported to the owner.
* **A second kick joining a held punch called the kick front back to the floor**: the light low down fell and rose again, one more flash (up to 4.0 a second on made-up hits, round 2 and 3). The three standard passages did not show it; the made-up hits did. Fixed (one front per full punch) and kept as a test.
* **A drop one or two frames after its kick was refused by the ration** in round 1 (jump on a drop 20% instead of 51%). Hence the three-frame hold.
* **Soft pulses can only be small.** Under 10% of full light on a third, and on top of the fading punch before them, they add 1 to 2 points to the brightness of the whole installation. They are drawn thin and bright (a line, a sparkle) so that they can be seen where they are. Whether they are seen on the real installation is not known.
* **`python -m research.guard check choreography` exits 1** because `research/scoreboard/README.md` was changed during this cycle by someone else (a music-lab cycle was running in the same folder). Not undone, named in the report.
* **`nominate --against Kick_bands_mode` is refused** (that mode failed its gate), so the owner cannot compare the safe mode with the mode it comes from. Nominated without `--against`.

---

## 6. Open Items & Next Steps

* [ ] The owner watches the three clips of `Kick_bands_safe_mode` (truth against today's analyzer) and answers the two questions in `research/OWNER_QUESTIONS.md`.
* [ ] C07: a ration that follows the tempo, for music faster than 130 beats a minute.
* [ ] C08: the afterglow of a drop hides the next two kicks.
* [ ] C09: make the soft pulses readable, or drop them.
* [ ] Not verified: the real installation (brightness, colours, the room), the cost on the Raspberry Pi, 30 frames a second (the lab draws 60), saturated red flashes (not checked by the gate).
