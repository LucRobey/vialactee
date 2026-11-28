# Open tracks: `MultiBandSixSignalsAudioAnalyzer` against production (run `2026-11-27_best_beat`, grade 1)

10 open tracks, production `Listener`, 5 s look-ahead. Scores from 0 to 100. You may tune on these tracks and grade again as often as you need.

## Target

| Signal | Production today | Candidate | Change | Truth |
|---|---|---|---|---|
| beat | 76.2 | 76.4 | +0.2 | 10 of 10 tracks graded, 10 of them on checked truth |
| bpm | 69.7 | 71.3 | +1.6 | 10 of 10 tracks graded, 10 of them on checked truth |

`beat`, track by track (open tracks only):

| Track | Production today | Candidate |
|---|---|---|
| 01 Sweet Child O' Mine | 79.5 | 82.3 |
| 03 Come Together - Remastered | 65.1 | 65.5 |
| 05 Message In A Bottle - Remast | 89.3 | 89.6 |
| 07 Piece of My Heart - Live at  | 65.3 | 65.3 |
| 09 You Know I'm No Good | 65.0 | 62.1 |
| 11 Sucker for Pain (with Wiz Kh | 64.8 | 64.8 |
| 13 Another One Bites The Dust - | 96.5 | 96.5 |
| 15 Roadgame | 96.2 | 96.2 |
| 17 Genesis | 81.2 | 82.3 |
| 19 01-Plastic-People | 59.6 | 59.6 |

`bpm`, track by track (open tracks only):

| Track | Production today | Candidate |
|---|---|---|
| 01 Sweet Child O' Mine | 82.8 | 96.6 |
| 03 Come Together - Remastered | 22.6 | 24.2 |
| 05 Message In A Bottle - Remast | 100.0 | 100.0 |
| 07 Piece of My Heart - Live at  | 67.9 | 67.9 |
| 09 You Know I'm No Good | 98.4 | 98.4 |
| 11 Sucker for Pain (with Wiz Kh | 0.0 | 0.0 |
| 13 Another One Bites The Dust - | 99.5 | 99.5 |
| 15 Roadgame | 97.5 | 97.5 |
| 17 Genesis | 83.0 | 83.9 |
| 19 01-Plastic-People | 45.4 | 45.4 |

A dash means the truth has nothing to grade on that track (for a stretch signal: no such stretch in the song). A wrong answer there costs nothing in the score: measure it yourself and say it in the proposal.

## Gate on the other signals: PASSED

No signal production already has may lose more than 1 point on average.

| Signal | Production today | Candidate | Verdict | Tracks losing more than 5 points |
|---|---|---|---|---|
| no_beat | 84.0 | 84.0 | kept | none |
| kick | 75.2 | 75.2 | kept | none |
| kick_present | 81.0 | 81.0 | kept | none |
| drop | 0.0 | 0.0 | kept | none |
| section_change | 0.0 | 0.0 | kept | none |
| silence | 97.7 | 97.7 | kept | none |
| loudness | 63.3 | 63.3 | kept | none |
| band_bass | 81.9 | 81.9 | kept | none |
| band_mid | 89.0 | 89.0 | kept | none |
| band_high | 92.6 | 92.6 | kept | none |
| brightness | 23.3 | 23.3 | kept | none |

## Cost

Whole listener step on this PC: production 0.605 ms, candidate 0.580 ms (-4%). Not measured on the Raspberry Pi.
