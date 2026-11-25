# research/truth: the source of truth, automatic draft

One file per track saying what is in the music and when. This folder holds the **machine pass**, built before
the owner's review by ear. Design: `research/analyzer_trials/papers/P1_source_of_truth.md`. Variables wanted:
`research/analyzer_trials/VARIABLE_LIST.md`.

## Build

The heavy tools (beat trackers, stems, chords, drum model) are run first by the scripts in
`research/analyzer_trials/` and leave their results in `research/analyzer_trials/output/`. Then, from the
repository root:

    research/analyzer_trials/.venv/Scripts/python.exe -m research.truth.build_truth [track ids...]

About 8 s per track. It writes `tracks/<id>.json`, `tracks/<id>.curves.npz` (not committed, rebuilt on demand)
and `REPORT.md`. Tests: `python -m pytest research/tests/test_truth_pipeline.py`.

| File | Role |
|---|---|
| `build_truth.py` | gathers every source, lays the owner's timings on top, writes the truth files |
| `measures.py` | direct measurements on the mix and the stems: levels, bands, brightness, silence, kick stretches, breakdowns, risers, layers |
| `meter.py` | main beats against half-beats, tempo, position in the bar from two trackers' downbeats |
| `sections.py` | section changes: bar lines where the music after differs from the music before (a family of instruments in or out, a step in loudness or brightness), put on the exact beat, with the reason in words |
| `labels.py` | lays the owner's corrections (`labels/<id>.json`) over the draft: owner-placed items become H, a lane ticked "checked whole" becomes A |
| `review_server.py`, `review.html` | the review tool (below) |
| `report.py` | `REPORT.md`: one line per track and the list of what most needs a human ear |

## Review tool

    research/analyzer_trials/.venv/Scripts/python.exe -m research.truth.review_server

then open http://127.0.0.1:8766 (or start `truth-review` from `.claude/launch.json`). One page per track: the
sound, one combined beat lane, one lane per drum piece, per kind of stretch and per curve. Marks and stretches
can be dragged, added, deleted; a beat can be made the "1" of the bar. Every change is saved at once to
`labels/<id>.json`. Those files are the owner's word and are committed; `build_truth.py` reads them and never
writes them. Run `build_truth.py` again to fold the corrections into `tracks/<id>.json`.

## The live mirror

Every value of a truth file that describes the music has a matching slot in the analyzer, at
`listener.signals` (`music/MusicSignals.py`). The list is `config/music_signals.json`; the contract is
section 6 of `docs/contracts/music_analyzer_contract.md`. `research/tests/test_truth_contract_parity.py` fails
if a value is added to the truth without a slot, or the reverse.

## Levels of evidence

Every value carries one: **H** timed by ear, **A** accepted by ear, **M2** two tools agree, **M1** one tool,
**W** known weak, **X** exact by construction (a direct measurement of the mix). Only H, A, M2 and X may grade
the analyzer.

## What a truth file holds

| Key | Content | Level today |
|---|---|---|
| `beats` | time, main beat or half-beat, votes of the three trackers, tempo, position in the bar, strength, drum pieces on the beat | M2 where two trackers agree |
| `meter` | beats per bar, and whether the two trackers count bars the same way | M2 / M1 per beat (`bar_pos_level`) |
| `regions.no_beat`, `regions.beat_confirmed` | no beat to follow; stretches the owner confirmed have a beat | H / A on 2 tracks, M1 elsewhere |
| `regions.kick_present`, `regions.breakdown`, `moments` | where the kick keeps coming; where it leaves and returns, with the loudness jump | M2 where the trained model agrees with the measurement |
| `drums.pieces` | kick, snare, tom, hat, cymbal hits from the trained model (ADTOF), each `[time, strength, level]` | kick M2 when a measured low-band peak matches; others M1 / W |
| `regions.bass_present`, `drums_present`, `vocal_present`, `other_present` | a stem is loud in itself and not far under the mix | M1 |
| `regions.silence` | mix under -50 dB | X |
| `regions.riser` | brightness rising for seconds | W |
| `sections` | section changes from `sections.py`, each with a strength and what changed | M1 |
| `chords`, `sections_old_rule` | BTC chords; the first novelty boundaries, kept for comparison | M1; W |
| `curves` | 20 values per second: loudness, four bands, brightness, fullness, layers, level of each stem, kick band | X for the mix, M1 for stems |

The owner's first timings (2026-11-22) live in `research/analyzer_trials/hand_labels.json`; everything corrected
since lives in `labels/`. The pipeline never overwrites either: where the owner has spoken, the machine's
value is dropped.

## Known limits

- Kick stretches matched the owner's three timed edges on Plastic People within 0.7 s. That is one track.
- The drum model was trained on rock, metal and pop with acoustic kits. Its hits on electronic tracks are unchecked.
- "M2" for a drum piece other than the kick does not exist yet: mix and stem are two runs of one model.
- Risers are a first guess. Drops and build-ups are not detected at all; only "the kick returns" is.
- Bars are counted in blocks of 16 beats; a block where the two trackers disagree follows one of them and is
  marked M1.
