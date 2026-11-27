# 2026-11-27 `no_beat` Promoted, and a First Guess of Build-ups and Drops for the Owner to Correct

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Carry out three answers of the owner: approve `no_beat` ("yes, we need that"), "build a first version and I will use the tool to correct it" (the lanes no tool settles), and clear up "I thought we had 20" (the tracks kept aside).  
> **Status:** COMPLETED (promotion proven by identical scores; the first guess is in the truth files at level W; the owner has not corrected anything yet)  
> **Commits:** see `git log` for this date (pushed: no)  
> **Skills Used:** `vialactee-research-manager` (section 5, written the same day)  
> **Skill Friction:** `vialactee-research-manager`: step 3 of a promotion ("turn the candidate into an empty subclass") destroys the graded code when the candidate was never committed, which is the normal case since lab agents do not commit. Keep a copy in the run folder first.

---

## 1. Context & Motivation

The first run made by an agent alone ([log](2026-11-27_music_lab_cycle_no_beat.md)) proposed `no_beat`; the owner approved it. The owner also judged the three waiting clips, asked what the music lab needs, and agreed to correct by ear the lanes that hold the lab back, provided a first version is drawn for them.

## 2. Changes Made

### `no_beat` promoted (production)
* **[MODIFY]** [`music/BandKickSignals.py`](../music/BandKickSignals.py) (157 to 216 lines): `_no_beat`, next to `kick_present`, with the candidate's two settings (`NO_BEAT_KICK_GAP_S` 2.0, `NO_BEAT_UNSURE_BELOW` 0.45). `update()` takes the tempo follower's confidence as one more argument.
* **[MODIFY]** [`music/DyadicMetricalAudioAnalyzer.py`](../music/DyadicMetricalAudioAnalyzer.py): passes `confidence_score`.
* **[MODIFY]** `MusicSignals.PRODUCED` (six slots), [`config/music_signals.json`](../config/music_signals.json), section 6 of the contract, `docs/architecture/audio_pipeline.md`.
* **[MODIFY]** [`research/experiments/models/NoBeatSlotAudioAnalyzer.py`](../research/experiments/models/NoBeatSlotAudioAnalyzer.py): now an empty subclass of the production model. **[NEW]** [`runs/2026-11-27_no_beat/candidate_as_graded.py`](../research/scoreboard/runs/2026-11-27_no_beat/candidate_as_graded.py): the code as it was graded (see section 5).
* `cycle decide 2026-11-27_no_beat --decision approved`; the work list line M01 and the status record follow.

### First guess for the owner (truth building, on the owner's request)
* **[NEW]** [`research/truth/buildups.py`](../research/truth/buildups.py): release points (every kick return; every section change that gets 5 dB louder), a build-up proposed before a release point when tension rises up to it (brighter, louder, a drum roll; one sign is enough inside a break, two elsewhere), and a "possible drop" at each release point the main rule did not take. All level **W**.
* **[MODIFY]** [`research/truth/build_truth.py`](../research/truth/build_truth.py): calls it. The 20 truth files were rebuilt.
* **[NEW]** [`research/truth/review_list.py`](../research/truth/review_list.py) and `REVIEW_LIST.md`: song by song, what to check in the four lanes, most to check first.
* **[MODIFY]** [`research/truth/review.html`](../research/truth/review.html): the hints of the Build-up and Drop lanes say that a first guess is drawn and that it is weak.
* **[MODIFY]** [`research/scoreboard/scoreboard.py`](../research/scoreboard/scoreboard.py): a stretch of level W is no longer counted in the "all truth" score. The README already said weak truth is never used; for stretches it was not true.
* **[MODIFY]** `research/OWNER_QUESTIONS.md`, `research/choreography/BACKLOG.md` (the owner's three choices and what they suggest).

### Tests
* **[MODIFY]** [`tests/test_band_kick_signals.py`](../tests/test_band_kick_signals.py): two tests of `no_beat`. **[NEW]** [`research/tests/test_truth_buildups.py`](../research/tests/test_truth_buildups.py) (7 tests).

## 3. Verification & Testing

* **Promotion**: the production model scored on the 20 tracks and compared value by value with the candidate's scores (open tracks from the run folder, check tracks from the hidden file): no difference besides the timing of a tick. `no_beat` 88 on the 12 tracks graded.
* **Truth rebuild**: compared with the committed files, only `regions.buildup`, the added W drops and the build date differ, on all 20 tracks. **11 build-ups and 29 possible drops** proposed.
* **Scores after the truth change**: identical, except the "typical offset" detail of `drop` on three tracks.
* **Review tool** opened in the browser pane on Sugar: 3 build-ups and 5 drops (4 weak) loaded, no console error. Not checked: how a weak mark looks next to a strong one.
* **Automated tests**
  ```powershell
  .venv/Scripts/python.exe -m pytest -q
  ```
  * **Result**: 788 passed, 5 deselected, 412 subtests passed (779 before this work).

## 4. Architecture Decisions & Trade-offs

* **A weak guess, not truth.** Level W is never used to grade, so a wrong guess cannot hurt a score; it becomes truth only through the owner's hand (A or H in `labels.py`).
* **The climb must end at the release point.** A first rule that took the lowest point of the last 24 s proposed build-ups exactly 24 s long (the search limit); a second one accepted a step up followed by a flat stretch. The rule kept: the last unbroken climb, still rising within 3 s of the release.
* **`no_beat` and the rhythm salience.** The owner asked if they are close. Related, not the same: salience is a level of how strongly rhythmic the sound is; `no_beat` is a yes or no that looks 2.5 s both ways and uses the kick and the tempo follower's confidence. Salience was not tried as an ingredient: noted in M11.

## 5. Pitfalls & Lessons Learned

* **I overwrote the candidate with its alias before it had ever been committed.** The graded code was still in this session and was written back to the run folder (`candidate_as_graded.py`), and the promoted code scores identically, so nothing is lost; but the promotion steps must say "copy first".
* The build-up rule finds nothing on Plastic People, whose three kick returns the owner knows well: the tension there is not in brightness or loudness. Expect the guess to miss as much as it finds.
* I cannot hear. Every one of the 40 proposals is unverified by ear.

## 5b. Later the same day: the owner's corrections of the no-beat lane

The owner corrected the no-beat lane on 8 songs in the review tool and ticked each as checked (`research/truth/labels/04, 05, 06, 11, 14, 15, 19, 20.json`). Eight passages were drawn or moved by hand (level H), the other marks accepted (level A). Intros without drums were marked "no beat" (Roadgame 0 to 52 s, Sucker for Pain 0 to 24 s, Nightcall 0 to 11 s, Bohemian Rhapsody 0 to 22 s).

Truth rebuilt: against the committed files, only the no-beat lane of those 8 songs changed (and the per-beat flag that follows it). Scoreboard rebuilt on the same recordings:

| Signal | Before | After |
|---|---|---|
| `no_beat`, on truth checked by ear | 76 on 2 songs | 82 on 8 songs |
| `no_beat`, on all truth | 88 on 12 songs | 86 on 14 songs |
| `beat` | 77.4 | 78.2 |
| `bpm` | 66.7 | 66.9 |

`beat` and `bpm` move because a beat reported inside a no-beat passage is not graded. Weakest for `no_beat`: Sucker for Pain 52 (the signal covers 14% of the intro the owner marked), then Bohemian Rhapsody, Plastic People and Nobody Rules the Streets at 77 to 78. On Roadgame the owner's mark confirms what the analyzer said in the intro, which the draft had counted as a fault.

### The 12 other songs

After looking at them in the review tool, the owner said: "I validate them all, they are perfect". Nothing had been saved by the tool for those songs, so the label files of the 12 songs (01, 02, 03, 07, 08, 09, 10, 12, 13, 16, 17, 18) were written here on that word: the no-beat lane as drawn, ticked as checked. Each file says so in its `about` line. I read the sentence as covering the no-beat lane only, which is what had been asked; drops, build-ups and section changes were **not** marked as checked.

The no-beat lane is now checked on all 20 songs (28 passages: 8 by hand, 20 accepted; 6 songs have none). `no_beat`: 86 on checked truth, 14 songs graded. `beat` and `bpm` unchanged.

## 6. Open Items & Next Steps

* [x] Owner: no-beat lane corrected on 8 songs (section 5b).
* [x] Owner: no-beat lane accepted as drawn on the 12 other songs.
* [ ] Owner: drops, build-ups and section changes are not corrected yet.
* [ ] The grading still gives no score for `no_beat` on the 6 songs that have no such passage, although the owner has now checked that they have none.
* [ ] Owner: the tracks kept aside (keep the 10 / 10 split, or add new songs and keep those aside).
* [ ] Try the rhythm salience as a third ingredient of `no_beat` (M11).
* [x] "Copy the candidate into the run folder" added to the promotion steps of the manager skill.
