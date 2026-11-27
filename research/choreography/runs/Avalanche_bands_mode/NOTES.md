# Avalanche_bands_mode: notes of the cycle (work list C12, second half, 2026-11-27)

A copy of `modes/Spectral_avalanche_mode.py`. Survey of the twelve Global Modes: `runs/Beat_blast_kick_mode/NOTES.md`.

## The original, through the gate

`Spectral_avalanche_mode` **fails** rule 3: 6.5 (Plastic People), 19.5 (Another One Bites The Dust) and 19.0
(Nobody Rules the Streets) flashes in one second, on every feed. Its stripes move by the mean frame-to-frame change
of the 16 raw bands times 45: on busy music they jump by a large part of their length every frame. Reported: kick
jump 5% to 30%; flashes on a real hit 30% to 72%; 2.0 to 3.5 flashes a second in breaks.

## Before the gate

The first version of the tests failed: 3.5 to 4.5 flashes in a second on fast kicks. The white front of a full
flare, falling from the canopy, made a second bump in each third of the height after the flare. The fronts were
moved to the resting layer (held under 7% of full light per third). Then 10 tests pass, among them 20 runs of
random kicks and levels.

## Round 1 (kept)

Gate passed: 3.0 flashes in one second at most (Nobody Rules the Streets, at the limit), 57% to 100% of flashes on
a real hit on the truth against 9% to 28% on the control, 0.58 ms a frame on this PC.

| | Plastic People | Another One Bites The Dust | Nobody Rules the Streets |
|---|---|---|---|
| kick jump, truth / today | 17% / 18% | 26% / 25% | 19% / 19% |
| flashes on a real hit, truth / today | 57% / 51% | 97% / 91% | 100% / 100% |
| flashes in breaks, truth / today | 0.6 / 0.8 | - | 0.0 / 0.1 |
| movement in a break, truth / today | 21% / 43% | - | 10% / 10% |
| top follows treble, truth | 0.72 | 0.67 | 0.09 |

- On the time strip of Plastic People the canopy (single height, no flow) shimmers with the treble level: the
  likely source of the flashes off the hits there. Not changed.
- Nobody Rules the Streets: the break is calm (10% of the normal movement), as in `Beat_blast_kick_mode`; see the
  owner question on how much a break should move.
- Kick contrast on today's analyzer (from `nominate`): 0.22 to 0.36, the original -0.08 to 0.32.
