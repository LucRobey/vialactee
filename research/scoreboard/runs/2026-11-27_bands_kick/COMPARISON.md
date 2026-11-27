# Comparison: `BandKickSlotsAudioAnalyzer` against `DyadicMetricalAudioAnalyzer`

Scoreboard run of 2026-11-27, 20 tracks, production `Listener`, 5 s look-ahead. Scores from 0 to 100.

## 1. The gate: PASSED

No signal the baseline produces may lose more than 1 point on average.

| Signal | Baseline | Candidate | Change | Truth | Verdict | Tracks losing more than 5 points |
|---|---|---|---|---|---|---|
| beat | 77.4 | 77.4 | +0.0 | checked | kept | none |
| bpm | 66.7 | 66.7 | +0.0 | checked | kept | none |
| drop | 4.8 | 4.8 | +0.0 | one tool only | kept | none |
| section_change | 0.0 | 0.0 | +0.0 | one tool only | kept | none |
| silence | 98.0 | 98.0 | +0.0 | checked | kept | none |
| loudness | 66.4 | 66.4 | +0.0 | checked | kept | none |
| brightness | 20.3 | 20.3 | +0.0 | checked | kept | none |

## 2. New signals

Open tracks (odd numbers) could be used for tuning. Check tracks (even numbers) were not looked at: a score that holds there is not an accident of the tuning.

| Signal | Open tracks | Check tracks | All | Truth | Weakest tracks |
|---|---|---|---|---|---|
| kick | 75.2 | 84.7 | 79.9 | checked | Genesis (49), Roadgame (60), Sugar (feat. Francesco Y (62) |
| kick_present | 81.0 | 89.1 | 85.0 | checked | Pumped Up Kicks (63), Message In A Bottle - Re (64), Piece of My Heart - Live (72) |
| band_bass | 81.9 | 83.8 | 82.8 | checked | Nightcall (36), Roadgame (48), Sucker for Pain (with Wi (61) |
| band_mid | 89.0 | 88.2 | 88.6 | checked | Hotel California - 2013  (72), Sugar (feat. Francesco Y (79), Sweet Child O' Mine (79) |
| band_high | 92.6 | 94.3 | 93.4 | checked | Hotel California - 2013  (82), Sweet Child O' Mine (87), Piece of My Heart - Live (88) |

## 3. Cost

Time per tick of the whole listener step (audio front end, analyzer, context) on this PC: baseline 0.491 ms, candidate 0.533 ms, difference +0.042 ms (+9%). Not measured on the Raspberry Pi.
