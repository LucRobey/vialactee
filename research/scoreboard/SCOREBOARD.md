# Scoreboard: the live analyzer against the source of truth

Built 2026-11-27 by `research/scoreboard/scoreboard.py`. 20 tracks, each played through the production `Listener` with the 5 s look-ahead. Every signal is read at speaker time from `listener.signals` and compared with the truth value it mirrors (`config/music_signals.json`).

How to read the numbers (all from 0 to 100, averaged over the tracks):

- a **moment** (beat, hit, drop): 100 = every one found, none invented;
- a **stretch** (silence, no beat, kick present): 100 = always right; 50 = no better than a signal stuck on one answer;
- a **level** (loudness, brightness): 100 = follows the truth exactly; 0 = unrelated;
- **tempo**: share of the time at the right tempo.

**Checked truth** counts only truth allowed to grade: timed or accepted by ear, two tools agreeing, or an exact measurement. **All truth** also counts what one tool alone says; it is indicative. A dash means there is nothing to grade against.

## MultiBandOnsetAudioAnalyzer

*the model running on the installation (main analyzer since 2026-11-27)*

### The 14 signals it produces today

| Signal | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| beat | 81 | 20 | 81 | 20 | finds 87% of them; 77% of what it reports is real; typically 17 ms early |
| bpm | 75 | 20 | 75 | 20 | double tempo 18% of the time, half tempo 0% |
| no_beat | 86 | 14 | 86 | 14 | right 78% of the time while it is on, 93% while it is off; edges 0.3 s late |
| kick | 80 | 20 | 81 | 20 | finds 85% of them; 79% of what it reports is real; typically 21 ms late |
| kick_present | 85 | 19 | 85 | 20 | right 99% of the time while it is on, 71% while it is off; edges 0.2 s early |
| drop | - | 0 | 5 | 6 | finds 8% of them; 1% of what it reports is real; typically 17 ms early |
| section_change | - | 0 | 0 | 20 | it never fires on these tracks |
| buildup | - | 0 | - | 0 | the truth has none on these tracks; the signal is on 8% of the time |
| silence | 98 | 19 | 98 | 19 | right 99% of the time while it is on, 97% while it is off; edges 1.4 s early |
| loudness | 66 | 20 | 66 | 20 | 25 ms early |
| band_bass | 83 | 20 | 83 | 20 | 0 ms early |
| band_mid | 89 | 20 | 89 | 20 | 0 ms early |
| band_high | 93 | 20 | 93 | 20 | 0 ms early |
| brightness | 20 | 20 | 20 | 20 | 100 ms early |

### The 22 empty slots

Nothing produces these yet, so there is nothing to grade: `bar_position`, `beats_per_bar`, `beat_strength`, `snare`, `hat`, `tom`, `cymbal`, `kick_level`, `breakdown`, `riser`, `bass_present`, `drums_present`, `vocal_present`, `other_present`, `bass_level`, `drums_level`, `vocal_level`, `other_level`, `layers`, `band_sub`, `fullness`, `chord`.

### Existing signals tried as candidates for an empty slot

Each line takes a signal the analyzer already has and grades it as if it filled the slot on the left.

| Slot <- candidate | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| kick <- beat tag | 69 | 20 | 70 | 20 | finds 74% of them; 72% of what it reports is real; typically 5 ms early |
| snare <- beat tag | - | 0 | 25 | 20 | finds 30% of them; 25% of what it reports is real; typically 7 ms early |
| hat <- beat tag | - | 0 | 0 | 20 | finds 0% of them; 25% of what it reports is real; typically 8 ms early |
| kick <- sudden rise of the lowest band | 72 | 20 | 75 | 20 | finds 93% of them; 64% of what it reports is real; typically 17 ms late |
| section_change <- the 'song change' flag | - | 0 | 28 | 20 | finds 25% of them; 36% of what it reports is real; typically 803 ms late |
| no_beat <- not locked | 71 | 14 | 71 | 14 | right 70% of the time while it is on, 70% while it is off; edges 2.5 s late |
| no_beat <- beat trust under 0.35 | 71 | 14 | 71 | 14 | right 55% of the time while it is on, 86% while it is off; edges 1.5 s late |
| band_bass <- 1 of the 16 bands | 84 | 20 | 84 | 20 | 8 ms late |
| band_mid <- 8 of the 16 bands | 85 | 20 | 85 | 20 | 15 ms late |
| band_high <- 7 of the 16 bands | 74 | 20 | 74 | 20 | 50 ms early |
| kick_level <- lowest band | - | 0 | 63 | 20 | 58 ms late |

## DyadicMetricalAudioAnalyzer

*the same model plus the half-beat sub-pulse (main until 2026-11-27), selectable*

### The 14 signals it produces today

| Signal | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| beat | 78 | 20 | 78 | 20 | finds 87% of them; 73% of what it reports is real; typically 17 ms early |
| bpm | 67 | 20 | 67 | 20 | double tempo 26% of the time, half tempo 0% |
| no_beat | 86 | 14 | 86 | 14 | right 78% of the time while it is on, 93% while it is off; edges 0.3 s late |
| kick | 80 | 20 | 81 | 20 | finds 85% of them; 79% of what it reports is real; typically 21 ms late |
| kick_present | 85 | 19 | 85 | 20 | right 99% of the time while it is on, 71% while it is off; edges 0.2 s early |
| drop | - | 0 | 5 | 6 | finds 8% of them; 1% of what it reports is real; typically 17 ms early |
| section_change | - | 0 | 0 | 20 | it never fires on these tracks |
| buildup | - | 0 | - | 0 | the truth has none on these tracks; the signal is on 8% of the time |
| silence | 98 | 19 | 98 | 19 | right 99% of the time while it is on, 97% while it is off; edges 1.4 s early |
| loudness | 66 | 20 | 66 | 20 | 25 ms early |
| band_bass | 83 | 20 | 83 | 20 | 0 ms early |
| band_mid | 89 | 20 | 89 | 20 | 0 ms early |
| band_high | 93 | 20 | 93 | 20 | 0 ms early |
| brightness | 20 | 20 | 20 | 20 | 100 ms early |

### The 22 empty slots

Nothing produces these yet, so there is nothing to grade: `bar_position`, `beats_per_bar`, `beat_strength`, `snare`, `hat`, `tom`, `cymbal`, `kick_level`, `breakdown`, `riser`, `bass_present`, `drums_present`, `vocal_present`, `other_present`, `bass_level`, `drums_level`, `vocal_level`, `other_level`, `layers`, `band_sub`, `fullness`, `chord`.

### Existing signals tried as candidates for an empty slot

Each line takes a signal the analyzer already has and grades it as if it filled the slot on the left.

| Slot <- candidate | On checked truth | tracks | On all truth | tracks | What happens |
|---|---|---|---|---|---|
| kick <- beat tag | 69 | 20 | 71 | 20 | finds 75% of them; 71% of what it reports is real; typically 5 ms early |
| snare <- beat tag | - | 0 | 24 | 20 | finds 30% of them; 24% of what it reports is real; typically 7 ms early |
| hat <- beat tag | - | 0 | 0 | 20 | finds 0% of them; 22% of what it reports is real; typically 8 ms early |
| kick <- sudden rise of the lowest band | 72 | 20 | 75 | 20 | finds 93% of them; 64% of what it reports is real; typically 17 ms late |
| section_change <- the 'song change' flag | - | 0 | 28 | 20 | finds 25% of them; 36% of what it reports is real; typically 803 ms late |
| no_beat <- not locked | 71 | 14 | 71 | 14 | right 70% of the time while it is on, 70% while it is off; edges 2.5 s late |
| no_beat <- beat trust under 0.35 | 71 | 14 | 71 | 14 | right 55% of the time while it is on, 86% while it is off; edges 1.5 s late |
| band_bass <- 1 of the 16 bands | 84 | 20 | 84 | 20 | 8 ms late |
| band_mid <- 8 of the 16 bands | 85 | 20 | 85 | 20 | 15 ms late |
| band_high <- 7 of the 16 bands | 74 | 20 | 74 | 20 | 50 ms early |
| kick_level <- lowest band | - | 0 | 63 | 20 | 58 ms late |

## Song by song: beats and tempo (on checked truth)

| # | Track | Group | beat MultiBandOns | tempo MultiBandOns | beat DyadicMetric | tempo DyadicMetric |
|---|---|---|---|---|---|---|
| 01 | Sweet Child O' Mine | rock | 82 | 97 | 79 | 83 |
| 02 | Hotel California - 2013 Remaster | rock | 64 | 24 | 64 | 23 |
| 03 | Come Together - Remastered | rock | 66 | 24 | 65 | 23 |
| 04 | Where Is My Mind_ | rock | 54 | 2 | 53 | 2 |
| 05 | Message In A Bottle - Remastered 2 | rock | 90 | 100 | 89 | 100 |
| 06 | Bohemian Rhapsody - Remastered 201 | rock | 68 | 60 | 69 | 60 |
| 07 | Piece of My Heart - Live at The Gr | rock | 65 | 68 | 65 | 68 |
| 08 | Pumped Up Kicks | pop | 94 | 99 | 73 | 34 |
| 09 | You Know I'm No Good | pop | 62 | 98 | 65 | 98 |
| 10 | Sugar (feat. Francesco Yates) | pop | 77 | 97 | 77 | 97 |
| 11 | Sucker for Pain (with Wiz Khalifa, | pop | 65 | 0 | 65 | 0 |
| 12 | Stayin' Alive - From _Saturday Nig | pop | 100 | 100 | 100 | 100 |
| 13 | Another One Bites The Dust - Remas | pop | 96 | 99 | 96 | 99 |
| 14 | Nightcall | electro | 99 | 100 | 74 | 29 |
| 15 | Roadgame | electro | 96 | 98 | 96 | 98 |
| 16 | Flashback | electro | 96 | 98 | 96 | 98 |
| 17 | Genesis | electro | 82 | 84 | 81 | 83 |
| 18 | Palladium | electro | 99 | 100 | 99 | 100 |
| 19 | 01-Plastic-People | electro | 60 | 45 | 60 | 45 |
| 20 | Nobody Rules the Streets | electro | 98 | 100 | 98 | 100 |

## What each signal is graded against

`beat` against `beats.t`, `bpm` against `beats.bpm`, `no_beat` against `regions.no_beat`, `bar_position` against `beats.bar_pos`, `beats_per_bar` against `meter.beats_per_bar`, `beat_strength` against `beats.strength`, `kick` against `drums.pieces.kick`, `snare` against `drums.pieces.snare`, `hat` against `drums.pieces.hat`, `tom` against `drums.pieces.tom`, `cymbal` against `drums.pieces.cymbal`, `kick_present` against `regions.kick_present`, `kick_level` against `curves.kick_db`, `drop` against `drops`, `section_change` against `sections.items`, `breakdown` against `regions.breakdown`, `buildup` against `regions.buildup`, `riser` against `regions.riser`, `silence` against `regions.silence`, `bass_present` against `regions.bass_present`, `drums_present` against `regions.drums_present`, `vocal_present` against `regions.vocal_present`, `other_present` against `regions.other_present`, `bass_level` against `curves.stem_bass_db`, `drums_level` against `curves.stem_drums_db`, `vocal_level` against `curves.stem_vocals_db`, `other_level` against `curves.stem_other_db`, `layers` against `curves.layers`, `loudness` against `curves.loud_db`, `band_sub` against `curves.sub_db`, `band_bass` against `curves.bass_db`, `band_mid` against `curves.mid_db`, `band_high` against `curves.high_db`, `brightness` against `curves.bright_oct`, `fullness` against `curves.fullness`, `chord` against `chords.items`.
