# Beat_blast_kick_mode: notes of the cycle (work list C10, 2026-11-27)

## What the twelve Global Modes listen to today

Read from the code of `modes/` (grep of what each `run()` reads), not from a run.

| Global Mode | Its pump / its hits | What a copy could take from the new analyzer |
|---|---|---|
| Monolithic Beat Blast | `beat_pulse()` + white flash on `is_real_beat` | done in this cycle: `kick`, `kick_present`/`no_beat`, `band_*` |
| Concentric Radial Ripple | `beat_pulse()`, a ripple on each beat phase wrap, `drop_hit` | launch a ripple on `kick`, not on the predicted beat; calm on `kick_present` false |
| Horizon Scanning Blade | beat phase drives the sweep, `beat_pulse()`, `drop_hit` | sweep on the beat (keep), blade brightness on `kick`, width on `band_bass` |
| Spectral Avalanche | raw 16 / 8 bands, `beat_pulse()` | `band_bass/mid/high` as its three main voices; `kick` for the avalanche start |
| Architectural VU Equalizer | its own level meter | `band_bass/mid/high` and `loudness` |
| Stalagmites | its own band hits (`_hit`), `drop_hit` | `kick` for the low stalagmites, `band_high` for the tips |
| Tableaux, Flip-Flop, Bar Clock, Construction, Mosaic | cast modes: the beat / bar clock of `modes/Cast_mode_base.py`, `drop_hit` | change picture on `kick` (rationed) and freeze the counter while `no_beat` |
| Negative Space | its own transient timer, `drop_hit` | `kick` for the cut-out |

No Global Mode reads `listener.signals`. On the lab's gate every one of them draws exactly the same frames on the
truth, today and control feeds, so rule 4 ("tied to the music") says "not applicable" for all of them.

## The original, through the gate (2026-11-27)

`Monolithic_beat_blast_mode` **fails** rule 3: 3.5 flashes in one second on Nobody Rules the Streets (3.0 on the
two others). It flashes 2.3 to 2.4 times a second in breaks, and 52% to 75% of its flashes fall on a real hit.

## Rounds

| Round | Change | Gate | What the profile said |
|---|---|---|---|
| 1 | first version | passed | kick jump 18% to 32% (original 10% to 19%); flashes on a real hit 88% to 100% on today's analyzer and the truth; flashes in breaks 0.1 a second (original 2.3); movement in a break only 7% to 10% of normal (original 70% to 85%) |
| 2 | the break breathes on `beat_pulse()` | passed | movement in a break 19% to 23%, but 1.3 to 1.9 visible pulses a second in breaks and only 59% of flashes on a real hit: pulses on beats that are not there. Dropped |
| 3 | the break swells with the loudness instead | passed | flashes in breaks back to 0.1 to 0.2; movement in a break 8% to 12%. Kept |

Movement in the profile is how much the light of the whole installation swings against its own half-second
average: the rings drifting in a break do not count, because the total light stays the same. A break that
"moves" by that measure has to pulse in total light, and a pulse on the beat tracker's beats is what the owner
does not want. That trade-off went to `research/OWNER_QUESTIONS.md`.
