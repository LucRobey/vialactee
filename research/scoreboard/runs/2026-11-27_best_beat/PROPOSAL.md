# Proposal to the owner: `beat`, `bpm` (run `2026-11-27_best_beat`, 2026-11-27)

## What is proposed
The analyzer that follows the beat and the tempo best, with the six new signals added to it, as you asked.
Candidate `MultiBandSixSignalsAudioAnalyzer` (`research/experiments/models/`). It is the model the
installation's analyzer was built on, without the one thing the installation's version adds: the "sub-pulse",
which inserts half-beats and doubles the tempo when it thinks the music is felt twice as fast. The six signals
(kick, kick present, bass, middle, treble, no beat) are computed by the same code as on the installation.
There is no new rule and nothing was tuned.

## Results (0 to 100)

| Signal | Installation today | Candidate |
|---|---|---|
| `beat`, 10 tracks the lab may tune on | 76.2 | 76.4 |
| `beat`, 10 tracks kept aside | 80.2 | 85.0 |
| `beat`, all 20 | 78.2 | **80.7** |
| `bpm`, 10 tracks the lab may tune on | 69.7 | 71.3 |
| `bpm`, 10 tracks kept aside | 64.2 | 77.9 |
| `bpm`, all 20 | 67.0 | **74.6** |

Gate: no other signal got worse, on the open tracks and on the check tracks. The six signals and the five others
(silence, loudness, brightness, drop, section change) score exactly the same on every track looked at.

**The whole gain comes from three songs.** On the other seventeen the two analyzers give the same beats.

| Song | Beat, today / candidate | Tempo, today / candidate | Time at double tempo, today / candidate |
|---|---|---|---|
| Pumped Up Kicks | 73 / 94 | 34 / 99 | 65% / 0% |
| Nightcall | 74 / 99 | 29 / 100 | 71% / 0% |
| Sweet Child O' Mine | 79 / 82 | 83 / 97 | 14% / 0% |

These are the songs where the installation's sub-pulse switches on. (This table comes from the public scoreboard
of the parent model, whose beats the candidate reproduces; two of the three songs are among the tracks kept
aside, which is why the gain shows there.)

## What I ask you
Do you want this analyzer to replace the one on the installation? You can see the difference yourself before
answering: in `config/app_config.json`, set `"analyzer_model": "MultiBandOnsetAudioAnalyzer"` and play Nightcall,
Pumped Up Kicks and Sweet Child O' Mine. That model gives exactly the candidate's beats. It lacks the six
signals, so for this test use a mode that does not need them: the four modes added on 2026-11-27 (Beat Blast
Kick, Ripple Kick, Band VU, Avalanche Bands) read the kick and the bands and would fall back to older signals.
Put `"DyadicMetricalAudioAnalyzer"` back to compare.

## What this result does not tell you

- **Whether it looks better.** On those three songs the lights flash on half-beats today, for a good part of
  the song. The truth counts the beat a person would tap, so it calls that a fault. If you like the faster
  flashing on those songs, the score is measuring the wrong thing for you. Only your eye can say.
- **It does not fix the real tempo problem.** Both analyzers are at double tempo most of the time on Hotel
  California, Come Together, Where Is My Mind and Sucker for Pain, and both score 45 on the tempo of Plastic
  People. The sub-pulse is not the cause there. That is still line M08 of the work list.
- **Nothing was tuned, so the "tracks kept aside" check proves little here**: it is a comparison of two existing
  analyzers, and the difference was already visible on the public scoreboard.
- **What else the installation's version has.** It also builds a snare stream and a hi-hat stream that the
  parent model does not have. A search of the code found nothing that reads them outside the analyzer and its
  own tests: no mode and no part of the main loop does.
- **"Our best" is one of several.** I scored every analyzer we have on the real path for the first time
  (`ALL_MODELS.md`, next to this file). Five are within three points on beat; two older ones are 0.7 above
  this candidate's base on beat (81.5 and 81.4 against 80.7) and one point under on tempo. That is too close
  to call. I kept this base because the six signals are built on it.
- **How it would be promoted.** The parent model's file is over the project's 500-line limit and may not be
  edited, so the promotion would be a small new production file (this candidate) made the default, as a separate
  piece of work.
- **Cost.** On this PC a step takes 0.58 ms against 0.61 ms today (slightly less work). Not measured on the
  Raspberry Pi.
- The open / check split is still the provisional one.
