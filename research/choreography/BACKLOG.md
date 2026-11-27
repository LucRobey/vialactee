# Choreography lab: work list

What to work on, in order. Take the first line whose state is `open`. One cycle works on one line and makes
one new lab mode in `candidates/` (never edit another mode in place: copy it under a new name, so the two can
be compared). When you take a line, change its state to `taken (<Mode_name>)`; at the end, to
`done (<Mode_name>): <one-line result>`. Add new ideas at the end.

## What the owner likes (the only judge)

- A mode must **show the beat's punch**: a kick or a snare should be visible at once, not guessed.
- **Bass and treble should be readable apart**, by place or by colour.
- First blind choice (2026-11-27, Another One Bites The Dust): the owner preferred the version driven by the
  true signals over today's analyzer. Read `verdicts.jsonl` and `STATUS.md` for every later choice.
- The lights should not flash on beats that are not there (breaks, intros).
- Second set of blind choices (2026-11-27, `Kick_bands_safe_mode`, true signals against today's analyzer): the
  true signals won on Plastic People and on Another One Bites The Dust; **today's analyzer won on Nobody Rules
  the Streets**. On that passage the profile shows the true-signal version going quiet in the break (43% of
  normal movement, against 100% for today's) and being less regular from bar to bar (0.38 against 0.58). One
  choice is not a rule, but it warns against a break that goes too calm: worth testing in C03.
- These were choices between two ways of hearing the music for the same mode. The owner has not yet compared
  this mode with another mode (C06).

## What the installation can hear today

`kick`, `kick_present`, `band_bass`, `band_mid`, `band_high`, `beat`, `bpm`, `silence`, `loudness` are produced
by the installation's analyzer (see `research/scoreboard/STATUS.md` for how good each one is). Every other
signal of the contract is empty there: a mode that reads one must name a fallback, and cannot be promoted
until the signal exists.

| Id | State | The idea |
|---|---|---|
| C01 | done (Kick_bands_safe_mode): gate passed, at most 2.5 flashes in a second on the three passages (was 7.0) and never over 3.0 on 330 made-up runs of fast hits; a full flash at most every 0.46 s, the rest of the light held under 7% of full; kick jump as the eye sees it +17% to +32% on the truth (was +11% to +20%), but hits refused by the ration are barely visible and the zones are much dimmer (this also covers part of C02); nominated, waiting for the owner | **Make `Kick_bands_mode` safe.** It fails the gate on flash safety (up to 7 flashes in one second; the limit is 3). Make a new mode from it that keeps the kick punch but never exceeds the limit: for instance a full flash only on the strongest kick of each beat and a softer pulse on the others, or a punch that is a short rise in brightness rather than a flash from dark. |
| C02 | open | **A punch the eye sees.** In the profile the kick punch of `Kick_bands_mode` is weak once brightness is counted as the eye sees it (about 12%). Keep the resting light low so the punch stands out, and check `half_rise_ms` stays under 45 ms. |
| C03 | open | **Calm in a break.** Use `kick_present` (now on the installation) to change the look when the kick leaves: slow glow, no flashes; and come back hard when it returns. The profile counts flashes during breaks. |
| C04 | open | **Bass glow that survives the kick.** On Plastic People the bass glow is swamped by the kick flash. Give them different places (kick on the pillars, bass on the canopy, or the reverse) and compare. |
| C05 | open | **Three colours, three ranges.** A mode with no flash at all: bass, middle and treble as three zones whose colours and sizes follow `band_bass`, `band_mid`, `band_high`. The gate's "follows the music" rule will say "not applicable": say so in the note to the owner. |
| C06 | open | **Against a mode of the installation.** Once a lab mode passes the gate, nominate it against a registered mode the owner already uses, on the "today" feed, to learn whether the lab's ideas beat what runs now. |
| C07 | open | **A ration that follows the tempo.** `Kick_bands_safe_mode` gives a full flash at most every 0.46 s, to the first hit that comes: above 130 beats a minute every other kick only gets a soft pulse. Use `bpm` and `beat` to choose which hits get the full flash (the beats, not the first comer), or a shorter full punch. Check it on made-up fast hits too: the three standard passages have none (the first try of C01 passed the gate and went over the limit on them). |
| C08 | open | **The afterglow of a drop hides the next kicks.** In `Kick_bands_safe_mode` a drop lights everything and fades over about a second; the two or three kicks that follow jump less (Nobody Rules the Streets, 2:53). Try a shorter tail, or a tail on the canopy only. |
| C09 | open | **Soft pulses the eye can read.** In `Kick_bands_safe_mode` a hit refused by the ration gets a thin line or a sparkle that adds 1 to 2 points of brightness: about half of the true hits get no visible flash (48% to 62% do). Try another place for the soft pulse (a segment the full punch does not use), or decide it is not worth drawing. |
