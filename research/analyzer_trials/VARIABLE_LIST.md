# Variable list: what we want, with which tool (2026-11-23)

Second version of the list, after the web survey and the owner's techno requirement. It supersedes the ranking
in `papers/P1_source_of_truth.md` section 3 (to be merged there at the next revision).

- **Local tool**: free, runs on the PC. "have" = already produced for the 20 tracks. "to install" = found by
  search, not tried.
- **Moises adds**: what a paid Moises subscription would add. Not tested by us. Stems are exported as audio
  files; whether chords, key and tempo can be exported as data is not confirmed (they may only be visible in
  the app).
- **Techno**: expected fit, from how the tools were trained. Not measured.

## A. Pulse

| # | Variable | Use for the lights | Local tool | Moises adds | Techno |
|---|---|---|---|---|---|
| 1 | Beats | pulse, step, chase | Beat This + BeatNet + librosa merged (have) | click track locked to the song: a fourth opinion, if it exports as audio | good |
| 2 | Tempo and level (normal / half / double) | speed of motion | from the merged beats (have) | BPM shown in the app | good |
| 3 | Beat present / no beat | go ambient in a break | tracker agreement (have, tuned on 2 tracks) + your ear | nothing | good |
| 4 | Downbeat, position in bar | accent the "1" | Beat This + BeatNet downbeats, to merge | nothing | medium: the "1" of a loop is ambiguous |
| 5 | Blocks of 8, 16, 32 bars | change look on the block | counting from downbeats, to build | nothing | good, and central for techno |

## B. Drums

| # | Variable | Use for the lights | Local tool | Moises adds | Techno |
|---|---|---|---|---|---|
| 6 | Kick hits | the "boom" | rule on drum stem (have, weak); DrumSep, ADTOF (to install) | kick stem (Pro plan): second opinion | good by rule; trained models doubtful |
| 7 | Snare / clap hits | backbeat flash | same | snare stem | doubtful: claps are not snares |
| 8 | Hi-hat hits | sparkle | same; today hidden behind kicks | hi-hat stem | doubtful |
| 9 | Crash, ride, toms | bursts, fills | DrumSep 6 stems (to install) | toms and cymbals stems | low: rare in techno |
| 10 | Strength of each hit (new) | brightness per hit | ADT_STR (to install) | nothing | doubtful |
| 11 | Strength of each beat | brightness per beat | drum-stem level (have) | nothing | good |
| 12 | Kick present / absent over time (new, for techno) | marks breakdown and return | direct measurement on low band and drum stem, to build | cleaner kick stem | good |
| 13 | Fills, rolls, percussion density | build-up effects | hits per bar, to build | nothing | good |

## C. Layers and big moments

| # | Variable | Use for the lights | Local tool | Moises adds | Techno |
|---|---|---|---|---|---|
| 14 | Drop, build-up, breakdown | the main moments | no tool exists: rules on 12, 15, 16 + your ear | nothing | central; depends on your labels |
| 15 | Bass present / absent (new) | low colours on and off | bass stem level (have stems) | bass stem: second opinion | good |
| 16 | Brightness rising: filter opening, riser (new) | rising fill before a drop | direct measurement, to build | nothing | good |
| 17 | Number of layers playing (new) | how full the look is | stem levels and band activity, to build | more stems: guitar, piano, strings, wind | good |
| 18 | Section change | change of scene | novelty curve (have, weak); SongFormer (to install) | not found in Moises | boundaries may work; names will not |
| 19 | Section names (verse, chorus) | one look per section type | SongFormer (to install) | not found | poor: no verse or chorus in techno |
| 20 | Silence, stop, fade-out | blackout, freeze | direct measurement | nothing | good |
| 21 | Loudness, band energies, brightness | master brightness, bass and treble colours | direct measurement | nothing | good |

## D. Voice and harmony

| # | Variable | Use for the lights | Local tool | Moises adds | Techno |
|---|---|---|---|---|---|
| 22 | Singer on / off | spotlight when the voice is in | vocal-stem level (have, wrong on instrumentals) | vocal stem: second opinion; lead and backing voices apart (Premium plan) | medium: voices are often samples |
| 23 | Level per instrument family | one strip per family | Demucs stems (have); RoFormer (to install, timing to test) | 7 stem types against our 4 | doubtful: "drums / bass / synth" overlap |
| 24 | Chords, chord changes | slow colour moves | BTC (have) | chord grid: second opinion, export not confirmed | low value |
| 25 | Key, major / minor | base palette | madmom key (to run) | key shown in the app | low value |
| 26 | Bass note | colour of the bass strip | from chords or bass stem | nothing | medium |
| 27 | Excitement curve (new) | slow intensity | MMAS (to install) | nothing | unknown |

## E. Listed, not planned

Melody and notes (MuScriptor: about half right), song description in words (Music Flamingo), swing, time
signature, stereo position, mood tags, lyrics (unimportant by owner ruling), music straight to light (parked,
see `PLAN.md`).

## What paying really buys

Moises does not add a new variable. It adds a **second, independent opinion** on drums, bass, voice and
chords. That matters under the rule in P1: one tool alone may not grade the analyzer, two that agree may.
It gives nothing for the techno-specific rows (12, 14, 16, 17), which come from direct measurement and from
the owner's ear.
