# Band_vu_mode: notes of the cycle (work list C12, 2026-11-27)

A copy of `modes/Architectural_vu_equalizer_mode.py`. Spectral Avalanche, the other mode of C12, is not done.
Survey of the twelve Global Modes: `runs/Beat_blast_kick_mode/NOTES.md`.

## The original, through the gate

`Architectural_vu_equalizer_mode` **passes** (3.0 flashes a second at most, at the limit). Rule 4 not applicable.
Reported: average brightness 54% to 58%; kick jump 8% to 25%; flashes on a real hit 63% to 86%; flashes in breaks
0.5 to 0.8; bottom follows bass 0.19 to 0.63 (none on Plastic People); top follows treble 0.17 to 0.52.

## Where each band is

| Segments | Band | Colour |
|---|---|---|
| v1, v4 (outer pillars), h10, h31 (low bridges) | `band_bass` | red; white-tinted punch on a heard kick |
| v2, v3 (inner pillars), h11, h32 (middle bridges) | `band_mid` | amber |
| h00, h20, h30 (canopy) | `band_high` | cool white |

Each pillar is its own full meter (v1 spans 0.23 to 0.93 of the height, v3 0.0 to 0.7). A bridge or canopy
segment fills from its first LED.

## Rounds

| Round | Change | Gate | What the profile said |
|---|---|---|---|
| 1 | three meters, a thin white cap on a kick | **failed** rule 4 | every flash came from the levels, which the control does not move: 26% on a real hit on the truth and on the control. Kick jump 3% to 5% on two passages. Too bright at rest (55% to 63%) |
| 2 | a heard kick punches the whole bass meter, at most every 0.44 s; body drive 0.25 | passed | flashes on a real hit 72% to 89%; kick jump 8% to 28%; still 48% to 57% at rest |
| 3 | body drive 0.10 | passed | kick jump 12% to 29%; flashes on a real hit 82% to 92% (truth), 75% to 96% (today); 37% to 43% at rest. The bass and middle meters sat near full most of the time (time strip) |
| 4 | each meter reads its band against its own recent range (auto-ranging) | passed | the meters use their height (time strip: the bass meter rises and falls on every kick); numbers close to round 3; flashes in breaks 0.5 to 0.9 (round 3: 0.2 to 0.8) |

- Flash safety by construction: a meter falls at most 0.9 of its height a second; the full punch is rationed. 20
  runs of random levels with irregular kicks, and level jumps from silence to full at 1.5 to 15 a second, never
  go over 3.
- The flashes in breaks are the levels' own (a meter jumping with the music), not a beat tracker's pulse. On
  Plastic People today's analyzer says the kick is there during the break, so the bass meter punches there.
- Kick punch contrast on today's analyzer (from `nominate`): 0.22 to 0.25, the original 0.09 to 0.19.
