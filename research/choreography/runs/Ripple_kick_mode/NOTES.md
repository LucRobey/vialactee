# Ripple_kick_mode: notes of the cycle (work list C11, 2026-11-27)

A copy of `modes/Concentric_radial_ripple_mode.py`. Survey of the twelve Global Modes:
`runs/Beat_blast_kick_mode/NOTES.md`.

## The original, through the gate

`Concentric_radial_ripple_mode` **passes** (0 large flashes: its saturated violet gives about a fifth of full
light at full drive). Rule 4 not applicable: same frames on every feed. Reported: kick jump 9% to 20%; flashes on a
real hit 53% to 77%; 2.2 to 2.4 visible pulses a second in breaks (it pumps on the beat tracker); movement in a
break 81% to 91% of normal; average brightness 42% to 46%.

## Rounds

| Round | Change | Gate | What the profile said |
|---|---|---|---|
| 1 | first version (white heart radius 0.22 in the tests, 0.40 in the gate) | passed, 3.0 flashes a second at most | too bright at rest (54% to 63%), kick jump 3% to 12%, flashes on a real hit 63% to 72% |
| 2 | everything dimmer but the white heart | passed, 3.0 | flashes on a real hit 100% (truth), 75% to 100% (today); flashes in breaks 0.0 to 0.1 (today on Plastic People 0.7); movement in a break 29% to 58%; kick jump 8% to 16% |
| 3 | ration 0.44 s instead of 0.46 s | passed, 3.0 | kicks 128 a minute that fell 27 frames apart were refused a heart; now they get one. Same numbers otherwise |

- Before round 1, the tests showed the kick lifted the seen light by only 3% to 5%: 20% of the LEDs are within 0.22
  of the core, about 57% within 0.40.
- The "most flashes in one second" stays at 3.0 on Nobody Rules the Streets (at the limit, not over), on the
  control too. 25 runs of random irregular hits (3 to 30 a second) never go over 3.
- "Bottom follows bass" is about 0: the bass glow sits at the core of the installation, which is not its bottom.
  The profile measures by height, so it cannot see whether bass and treble are read apart by distance.
- Kick punch contrast on today's analyzer (from `nominate`): 0.14 to 0.20, the original 0.15. The gain is where
  the flashes fall and the calm of the breaks, not a bigger punch.

## A finding for C07

A full-flash ration of 0.46 s (as in `Kick_bands_safe_mode`) refuses some kicks of a steady 128-a-minute track:
0.469 s between kicks lands 27 frames (0.45 s) apart now and then at 60 frames a second. 0.44 s keeps "four
cannot start within one second" (three gaps = 1.32 s).
