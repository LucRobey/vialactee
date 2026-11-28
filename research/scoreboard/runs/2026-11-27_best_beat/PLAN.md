# Plan of run `2026-11-27_best_beat`

Target: `beat`, `bpm`. Idea from the work list: M08. Asked by the owner on 2026-11-27: "could we prepare our best
analyser by adding all the new variables to it?". Run by the supervising session, not by a lab agent. The
candidate file was written just before this plan; it has no rule of its own and nothing to tune.

## What will change
Candidate `research/experiments/models/MultiBandSixSignalsAudioAnalyzer.py`: the model production was built on
(`MultiBandOnsetAudioAnalyzer`, without the "sub-pulse" that inserts half-beats and doubles the tempo), plus the
six signals of production (`band_bass`, `band_mid`, `band_high`, `kick`, `kick_present`, `no_beat`) through the
same helper, `music/BandKickSignals.py`.

## What result is expected
On all 20 tracks the scoreboard gives the parent model beat 81 and tempo 75, against 78 and 67 for production.
The candidate computes beats and tempo with the parent's code, so on the open tracks it should show the same
gain: about +3 on `beat` and +8 on `bpm`. The six signals should keep their scores: the kick stream and the
bands are the parent's own, used unchanged by production.

## How I will know it failed
`beat` or `bpm` not above production on the open tracks, or any of the six signals losing more than a point.
`no_beat` is the one at risk: it reads the tempo follower's confidence, and the two models may not be equally
sure at the same moments.

## What it could break
`no_beat` (see above). `drop`, `section_change`, `buildup`, `silence`, `loudness`, `brightness` come from the
`Listener` and the context; the context reads the beat, so `drop` and `buildup` could move. The gate checks all.
Outside the scoreboard: modes that rely on half-beats on slow songs would look calmer. No score sees that.
