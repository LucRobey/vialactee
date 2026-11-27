# research/scoreboard: the live analyzer against the source of truth

One question per signal: how far is what the installation hears from what is really in the music?

    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.scoreboard [--model NAME] [--reuse] [track ids]

About 2 minutes for 2 models on 20 tracks (5 workers). Writes `SCOREBOARD.md` (read this one) and `scores.json`
(every number, track by track). Recordings go to `output/` (not committed). Tests:
`python -m pytest research/tests/test_scoreboard_grading.py`.

| File | Role |
|---|---|
| `record.py` | plays one song through the production `Listener` with the 5 s look-ahead and records every slot of `listener.signals` at speaker time, plus a few existing signals to try as candidates |
| `grade.py` | the grading of each kind of signal: moments (hits, misses, false alarms), stretches (right while on, right while off, delay at the edges), levels (how well the curve is followed, and how late), tempo (right level, double, half) |
| `scoreboard.py` | runs the tracks, grades each signal of `config/music_signals.json` against the truth value it mirrors, grades the candidates |
| `report.py` | writes `SCOREBOARD.md` |
| `live_path.py` | replays the road live sound takes (Spotify, aux) next to the audio-file road, and what a 30 FPS display loop sees of the one-frame flags; see `runs/live_path/LIVE_PATH.md` |
| `compare.py` | before and after of two models of one run: the gate, the new signals on open and check tracks, the cost per tick |

## A research run

A candidate is a class in `research/experiments/models/` that subclasses an analyzer and writes slots of
`self.signals`. One run, one folder:

    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.scoreboard --model DyadicMetricalAudioAnalyzer --model <Candidate> --out research/scoreboard/runs/<date>_<name>
    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.compare research/scoreboard/runs/<date>_<name> --candidate <Candidate>

`COMPARISON.md` holds the gate (no signal the baseline produces may lose more than 1 point on average), the new
signals scored apart on the open tracks (odd ids, tuning allowed) and the check tracks (even ids, not looked
at), and the cost. The split and the margin are provisional. `runs/2026-11-27_bands_kick/` is the first run
and shows the whole cycle, tuning script and proposal included.

## Rules of the grading

- Everything is compared on the song's own clock, at speaker time: frame k of the run is the music heard at
  k / 60 s minus the look-ahead.
- **Checked truth** counts only truth allowed to grade (levels H, A, M2, X of `research/truth/README.md`).
  **All truth** adds what one tool alone says (M1) and is indicative. Weak truth (W) is never used; an estimate
  that lands on a truth value that may not grade is ignored, not counted as a false alarm.
- A beat reported inside a no-beat stretch is not graded.
- A stretch signal is summarised by its balanced score: the average of "right while on" and "right while off",
  so a signal stuck on one answer gets 50.
- Levels are compared on shape only (correlation at the best lag within 1 s), because the truth is in dB and
  the live values are between 0 and 1.
- Tolerances (50 ms for a hit, 0.5 s for a drop, 2 s for a section change, 4% for tempo) are proposals, not
  owner decisions.

## Candidates

Some existing signals are close to an empty slot without meaning quite the same thing. They are graded as if
they filled it, to tell cheap wins from real research: the beat tag as kick / snare / hat, "not locked" and low
beat trust as `no_beat`, the 16 bands grouped as bass / mid / high, sudden rises of the lowest band as kicks,
the "song change" flag as `section_change`.
