# Proposal to the owner: `no_beat` (run `2026-11-27_no_beat`, 2026-11-27)

## What is proposed
A signal the installation does not have today: `no_beat`, which says "there is no beat to follow right now"
(a break without drums, a free ending), so that a mode can stop flashing invented beats there. The candidate
`NoBeatSlotAudioAnalyzer` (`research/experiments/models/`) is the production model plus this one signal. It
says "no beat" when two things are true around the moment the speakers play: no kick drum for more than
2 seconds, and the tempo follower is unsure of itself. It uses the 5 seconds of advance to look before and
after, so it does not arrive late. Nothing else the analyzer does is changed.

## Results (0 to 100)

| Signal | Production today | Candidate, tracks tuned on | Candidate, tracks not looked at |
|---|---|---|---|
| `no_beat` | - | 88.9 | 86.6 |

Gate: no other signal got worse, on the open tracks and on the check tracks.

To compare: the two cheap stand-ins of the scoreboard ("not locked", "beat trust under 0.35") get 69 and 72 on
the tracks tuned on, 80 and 75 on the tracks not looked at.

On the tracks tuned on:

- It says "no beat" during 85% of the no-beat time, and it stays quiet 93% of the time while there is a beat.
- It switches at the right moment (typically within a quarter of a second); the stand-ins were about 2 s late.
- On the one track whose no-beat stretches you marked by ear (Plastic People): 77, against 54 and 38 for the
  stand-ins. It finds 58% of the no-beat time there and is right 96% of the time while the beat is on.
- On the four tracks that have no no-beat stretch at all, it says "no beat" 0%, 1%, 4% and 9% of the time
  (the 9% is Sucker for Pain, in short passages without kick).

## What I ask you
Do you want this `no_beat` in the production analyzer, once you have watched a mode use it on a song you know?

## What this result does not tell you

- **Most of the truth comes from one tool.** Of the six tracks tuned on that have a no-beat stretch, only
  Plastic People was marked by ear; on the five others "no beat" means "the beat-finding tools disagree". The
  tables of the lab print "checked" for this signal, which is true for a part of it only. For the tracks not
  looked at, I only have the one number.
- **The score only counts tracks that have a no-beat stretch** (six on each half). A track without one is not
  graded for this signal, so saying "no beat" by mistake there costs nothing. I measured it myself on the
  tracks tuned on (the 0% to 9% above); it is not measured on the tracks not looked at.
- **Where it is weak** (tracks tuned on): the second half of the long breaks of Plastic People (something
  regular keeps playing, the tempo follower stays sure, and a few false kicks appear); the first 43 s of
  Roadgame, where it says "no beat" half of the time while the truth says there is one; Genesis, where it joins
  two breaks into one (186 s to 213 s). On Sweet Child O' Mine it says "no beat" from 16 s to 27 s, the guitar
  intro without drums: the truth (one tool) says there is a beat there. So what it really says is "no drums
  the analyzer can follow", which is close to "no beat" but not the same.
- **It depends on the kick.** A false kick can hide a break, a missed kick can invent one. The kick is weakest
  on electronic tracks.
- **The two settings (2 s, confidence 0.45) were chosen on six tracks.** 0.45 is a compromise: a higher value
  finds more of the breaks of Plastic People but says "no beat" 14% to 35% of the time on Sucker for Pain.
- **Cost on the Raspberry Pi: not measured.** On this PC the difference is too small to see (0.59 ms per tick
  before, 0.58 ms after). No array is created per tick by construction; not verified by a memory test.
- **Nobody has seen it drive a light.** A score of 87 says nothing about how it looks.
- The candidate reads the kicks from inside the production kick code (two private fields). If you approve, the
  rule should move next to `kick_present` in `music/BandKickSignals.py`, as a separate small change.
- The "tuned on / not looked at" split is still the provisional one.
