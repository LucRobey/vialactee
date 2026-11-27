# Music lab: work list

What to work on, in order. Take the first line whose state is `open`, unless `STATUS.md` shows a better reason.
One run works on one line. When you take a line, change its state to `taken by <run>`; when the run is closed,
to `proposed (<run>): <one-line result>` when a proposal waits for the owner, `done (<run>): <one-line result>` when the idea is
finished or dropped, or back to `open` with a note on what was learned. Add new ideas at the end.

Scores are those of `SCOREBOARD.md` (production, 20 tracks, 0 to 100). "Truth" says whether the result can be
trusted: **checked** = two tools agree, the owner's ear, or an exact measurement; **one tool only** = a single
model's opinion, good to explore, not enough to propose.

| Id | Signal | Today | Truth | State | The idea, and where to look |
|---|---|---|---|---|---|
| M01 | `no_beat` | 86 (in production since 2026-11-27) | checked by the owner on all 20 songs | done (2026-11-27_no_beat): approved by the owner and promoted. "No kick for 2 s and the tempo follower unsure", looking both ways: 89 on the open tracks, 87 on the check tracks. See M11 for what it misses. | Say when there is no beat to follow (intro, break, free passage), so the lights stop flashing invented beats there. |
| M02 | `brightness` | 20 | checked (exact measurement) | open | The slot is copied from `context.vertical_center`, which is not a brightness measure. Truth is the spectral centre in octaves (`research/truth/measures.py`). Compute it from the 32 bands in a candidate and claim the slot (`claimed_slots = ("brightness",)`, see the skill). |
| M03 | `loudness` | 66 | checked (exact measurement) | open | The slot is copied from a level that follows its own automatic gain. Truth is the loudness curve in dB. A plain level in dB from the bands, through the same delay line as the band levels (`music/BandKickSignals.py` shows how), claimed the same way. |
| M04 | `fullness` | empty | checked (exact measurement) | open | How much of the spectrum is filled. Read its definition in `research/truth/measures.py` and compute the same thing from the 32 bands. |
| M05 | `kick_present` | 85 | checked | open | It stays on too long after the kick stops (right 71% of the time while the kick is out), because false kicks keep it alive. Ideas: ask for two kicks on each side, or ignore weak kicks. Change only this signal: `kick` itself must not move. |
| M06 | `kick_level` | empty | read the truth file to see | open | How loud the kick drum is, as a level. `SCOREBOARD.md` grades "lowest band" as a stand-in. |
| M07 | `beat_strength` | empty | checked where two beat trackers agree | open | How hard the drums mark the latest beat. Truth: `beats[].strength`. A first try: the kick stream at the beat, held until the next beat. |
| M08 | `bpm` (and `beat`) | 67 (beat 77) | checked | open | The hard one. The analyzer is at double tempo 25% of the time, and 28% of the beats it reports are not real: most are the half-beats it adds when its "sub-pulse" is active (`DyadicMetricalAudioAnalyzer.effective_bpm`, `subpulse_active`). A candidate overrides that decision. Look track by track in `SCOREBOARD.md` first: the fault is concentrated on a few songs. Any change here moves `beat`: the gate will tell. |
| M09 | `bar_position`, `beats_per_bar` | empty | checked per beat where two trackers agree | open | Where we are in the bar. Needs the first beat of the bar: hard. Only after M08. |
| M10 | `kick` | 80 | checked | open | Weakest on electronic tracks (Genesis 49, Roadgame 60), where the truth itself is less sure. Look at what is missed and what is invented there before changing anything. |
| M11 | `no_beat` (second pass) | 86, all of it on truth checked by ear (in production since 2026-11-27) | **checked by the owner on all 20 songs since 2026-11-27** (corrected by hand on 8; accepted as drawn on 12) | open | **New since the owner's corrections of 2026-11-27:** the owner counts an intro without drums as "no beat" (Roadgame 0 s to 52 s, Sucker for Pain 0 s to 24 s), so saying "no beat" there is right, not a fault. The big miss is now Sucker for Pain: the signal covers only 14% of its intro (score 52). Plastic People 57% and Roadgame 72% of the no-beat time. On Sweet Child O' Mine the owner accepted the lane as drawn, so the guitar intro (16 s to 27 s) has a beat and saying "no beat" there is a fault. Earlier notes, written before those corrections: What the first candidate misses: a break where something regular keeps playing without drums (Plastic People 207 s to 218 s: the tempo judge stays sure, a few false kicks appear), and it says "no beat" on intros with a pulse but no kick (Roadgame 0 s to 43 s, Sweet Child O' Mine 16 s to 27 s). The tempo confidence is the weak half of the rule: on Plastic People it is lower while the kick is steady than during the breaks. Tried and not worth it: "onsets fell under half their usual level" as a third condition (under 1 point). Worth trying: a regularity measure of the kick itself (steady spacing) instead of the tempo confidence. Only after the owner has answered the `no_beat` questions of `research/OWNER_QUESTIONS.md`: with one track checked by ear per half, a second pass would fit the one tool. |

## Blocked: do not take these

| Signal | Why |
|---|---|
| `band_sub` | The audio front end has no band under 60 Hz. Needs a change to `music/AudioIngestion.py`, which is the owner's to approve. |
| `snare`, `hat`, `tom`, `cymbal` | Truth from one tool only. A run may explore, but cannot be proposed. Listed in `research/OWNER_QUESTIONS.md`. |
| `drop`, `section_change`, `breakdown`, `riser`, `buildup` | Truth from one tool only, or weak. `section_change` never fires because the verse / chorus branch of `music/StructuralNoveltyDetector.py` cannot be reached: worth a run once the owner has marked a few by ear. |
| `bass_present`, `drums_present`, `vocal_present`, `other_present`, the four `*_level`, `layers`, `chord` | Truth from one separation model; live separation costs too much for the Raspberry Pi. Open research, not a cycle. |
