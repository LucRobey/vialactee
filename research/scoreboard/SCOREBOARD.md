# Scoreboard: the live analyzer against the source of truth

Built 2026-11-25 by `research/scoreboard/scoreboard.py`. 20 tracks, each played through the production `Listener` with the 5 s look-ahead. Every signal is read at speaker time from `listener.signals` and compared with the truth value it mirrors (`config/music_signals.json`).

How to read the numbers (all from 0 to 100, averaged over the tracks):

- a **moment** (beat, hit, drop): 100 = every one found, none invented;
- a **stretch** (silence, no beat, kick present): 100 = always right; 50 = no better than a signal stuck on one answer;
- a **level** (loudness, brightness): 100 = follows the truth exactly; 0 = unrelated;
- **tempo**: share of the time at the right tempo.

**Checked truth** counts only truth allowed to grade: timed or accepted by ear, two tools agreeing, or an exact measurement. **All truth** also counts what one tool alone says; it is indicative. A dash means there is nothing to grade against.

## DyadicMetricalAudioAnalyzer

*the model running on the installation*

### The 8 signals it produces today

| Signal | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| beat | 77 | 20 | 77 | 20 | finds 86% of them; 72% of what it reports is real; typically 17 ms early |
| bpm | 67 | 20 | 67 | 20 | double tempo 25% of the time, half tempo 1% |
| drop | - | 0 | 5 | 6 | finds 8% of them; 1% of what it reports is real; typically 350 ms early |
| section_change | - | 0 | 0 | 20 | it never fires on these tracks |
| buildup | - | 0 | - | 0 | the truth has none on these tracks; the signal is on 8% of the time |
| silence | 98 | 19 | 98 | 19 | right 99% of the time while it is on, 97% while it is off; edges 1.4 s early |
| loudness | 66 | 20 | 66 | 20 | 25 ms early |
| brightness | 20 | 20 | 20 | 20 | 100 ms early |

### The 28 empty slots

Nothing produces these yet, so there is nothing to grade: `no_beat`, `bar_position`, `beats_per_bar`, `beat_strength`, `kick`, `snare`, `hat`, `tom`, `cymbal`, `kick_present`, `kick_level`, `breakdown`, `riser`, `bass_present`, `drums_present`, `vocal_present`, `other_present`, `bass_level`, `drums_level`, `vocal_level`, `other_level`, `layers`, `band_sub`, `band_bass`, `band_mid`, `band_high`, `fullness`, `chord`.

### Existing signals tried as candidates for an empty slot

Each line takes a signal the analyzer already has and grades it as if it filled the slot on the left.

| Slot <- candidate | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| kick <- beat tag | 69 | 20 | 71 | 20 | finds 75% of them; 71% of what it reports is real; typically 5 ms early |
| snare <- beat tag | - | 0 | 24 | 20 | finds 30% of them; 24% of what it reports is real; typically 7 ms early |
| hat <- beat tag | - | 0 | 0 | 20 | finds 0% of them; 22% of what it reports is real; typically 8 ms early |
| kick <- sudden rise of the lowest band | 72 | 20 | 75 | 20 | finds 93% of them; 64% of what it reports is real; typically 17 ms late |
| section_change <- the 'song change' flag | - | 0 | 28 | 20 | finds 25% of them; 36% of what it reports is real; typically 803 ms late |
| no_beat <- not locked | 63 | 2 | 74 | 12 | right 80% of the time while it is on, 69% while it is off; edges 2.3 s late |
| no_beat <- beat trust under 0.35 | 57 | 2 | 73 | 12 | right 64% of the time while it is on, 85% while it is off; edges 1.6 s late |
| band_bass <- 1 of the 16 bands | 84 | 20 | 84 | 20 | 8 ms late |
| band_mid <- 8 of the 16 bands | 85 | 20 | 85 | 20 | 15 ms late |
| band_high <- 7 of the 16 bands | 74 | 20 | 74 | 20 | 50 ms early |
| kick_level <- lowest band | - | 0 | 63 | 20 | 58 ms late |

## MultiBandOnsetAudioAnalyzer

*its parent model, selectable*

### The 8 signals it produces today

| Signal | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| beat | 80 | 20 | 80 | 20 | finds 86% of them; 76% of what it reports is real; typically 17 ms early |
| bpm | 74 | 20 | 75 | 20 | double tempo 18% of the time, half tempo 1% |
| drop | - | 0 | 5 | 6 | finds 8% of them; 1% of what it reports is real; typically 350 ms early |
| section_change | - | 0 | 0 | 20 | it never fires on these tracks |
| buildup | - | 0 | - | 0 | the truth has none on these tracks; the signal is on 8% of the time |
| silence | 98 | 19 | 98 | 19 | right 99% of the time while it is on, 97% while it is off; edges 1.4 s early |
| loudness | 66 | 20 | 66 | 20 | 25 ms early |
| brightness | 20 | 20 | 20 | 20 | 100 ms early |

### The 28 empty slots

Nothing produces these yet, so there is nothing to grade: `no_beat`, `bar_position`, `beats_per_bar`, `beat_strength`, `kick`, `snare`, `hat`, `tom`, `cymbal`, `kick_present`, `kick_level`, `breakdown`, `riser`, `bass_present`, `drums_present`, `vocal_present`, `other_present`, `bass_level`, `drums_level`, `vocal_level`, `other_level`, `layers`, `band_sub`, `band_bass`, `band_mid`, `band_high`, `fullness`, `chord`.

### Existing signals tried as candidates for an empty slot

Each line takes a signal the analyzer already has and grades it as if it filled the slot on the left.

| Slot <- candidate | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| kick <- beat tag | 69 | 20 | 70 | 20 | finds 74% of them; 72% of what it reports is real; typically 5 ms early |
| snare <- beat tag | - | 0 | 25 | 20 | finds 30% of them; 25% of what it reports is real; typically 7 ms early |
| hat <- beat tag | - | 0 | 0 | 20 | finds 0% of them; 25% of what it reports is real; typically 8 ms early |
| kick <- sudden rise of the lowest band | 72 | 20 | 75 | 20 | finds 93% of them; 64% of what it reports is real; typically 17 ms late |
| section_change <- the 'song change' flag | - | 0 | 28 | 20 | finds 25% of them; 36% of what it reports is real; typically 803 ms late |
| no_beat <- not locked | 63 | 2 | 74 | 12 | right 80% of the time while it is on, 69% while it is off; edges 2.3 s late |
| no_beat <- beat trust under 0.35 | 57 | 2 | 73 | 12 | right 64% of the time while it is on, 85% while it is off; edges 1.6 s late |
| band_bass <- 1 of the 16 bands | 84 | 20 | 84 | 20 | 8 ms late |
| band_mid <- 8 of the 16 bands | 85 | 20 | 85 | 20 | 15 ms late |
| band_high <- 7 of the 16 bands | 74 | 20 | 74 | 20 | 50 ms early |
| kick_level <- lowest band | - | 0 | 63 | 20 | 58 ms late |

## Song by song: beats and tempo (on checked truth)

| # | Track | Group | beat DyadicMetric | tempo DyadicMetric | beat MultiBandOns | tempo MultiBandOns |
|---|---|---|---|---|---|---|
| 01 | Sweet Child O' Mine | rock | 79 | 83 | 82 | 97 |
| 02 | Hotel California - 2013 Remaster | rock | 64 | 23 | 64 | 24 |
| 03 | Come Together - Remastered | rock | 65 | 23 | 66 | 24 |
| 04 | Where Is My Mind_ | rock | 53 | 2 | 53 | 2 |
| 05 | Message In A Bottle - Remastered 2 | rock | 89 | 100 | 89 | 100 |
| 06 | Bohemian Rhapsody - Remastered 201 | rock | 67 | 59 | 67 | 59 |
| 07 | Piece of My Heart - Live at The Gr | rock | 65 | 68 | 65 | 68 |
| 08 | Pumped Up Kicks | pop | 73 | 34 | 94 | 99 |
| 09 | You Know I'm No Good | pop | 65 | 98 | 62 | 98 |
| 10 | Sugar (feat. Francesco Yates) | pop | 77 | 97 | 77 | 97 |
| 11 | Sucker for Pain (with Wiz Khalifa, | pop | 68 | 13 | 68 | 13 |
| 12 | Stayin' Alive - From _Saturday Nig | pop | 100 | 100 | 100 | 100 |
| 13 | Another One Bites The Dust - Remas | pop | 96 | 99 | 96 | 99 |
| 14 | Nightcall | electro | 73 | 29 | 98 | 100 |
| 15 | Roadgame | electro | 81 | 81 | 81 | 81 |
| 16 | Flashback | electro | 96 | 98 | 96 | 98 |
| 17 | Genesis | electro | 81 | 83 | 82 | 84 |
| 18 | Palladium | electro | 99 | 100 | 99 | 100 |
| 19 | 01-Plastic-People | electro | 60 | 46 | 60 | 46 |
| 20 | Nobody Rules the Streets | electro | 97 | 99 | 97 | 99 |

## What each signal is graded against

`beat` against `beats.t`, `bpm` against `beats.bpm`, `no_beat` against `regions.no_beat`, `bar_position` against `beats.bar_pos`, `beats_per_bar` against `meter.beats_per_bar`, `beat_strength` against `beats.strength`, `kick` against `drums.pieces.kick`, `snare` against `drums.pieces.snare`, `hat` against `drums.pieces.hat`, `tom` against `drums.pieces.tom`, `cymbal` against `drums.pieces.cymbal`, `kick_present` against `regions.kick_present`, `kick_level` against `curves.kick_db`, `drop` against `drops`, `section_change` against `sections.items`, `breakdown` against `regions.breakdown`, `buildup` against `regions.buildup`, `riser` against `regions.riser`, `silence` against `regions.silence`, `bass_present` against `regions.bass_present`, `drums_present` against `regions.drums_present`, `vocal_present` against `regions.vocal_present`, `other_present` against `regions.other_present`, `bass_level` against `curves.stem_bass_db`, `drums_level` against `curves.stem_drums_db`, `vocal_level` against `curves.stem_vocals_db`, `other_level` against `curves.stem_other_db`, `layers` against `curves.layers`, `loudness` against `curves.loud_db`, `band_sub` against `curves.sub_db`, `band_bass` against `curves.bass_db`, `band_mid` against `curves.mid_db`, `band_high` against `curves.high_db`, `brightness` against `curves.bright_oct`, `fullness` against `curves.fullness`, `chord` against `chords.items`.
