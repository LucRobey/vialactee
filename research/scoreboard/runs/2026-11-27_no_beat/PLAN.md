# Plan of run `2026-11-27_no_beat`

Target: `no_beat`. Idea from the work list: M01.

## What will change
A new candidate, `research/experiments/models/NoBeatSlotAudioAnalyzer.py`, subclass of the production model.
It adds one slot, `no_beat`, and changes nothing else. On each tick it measures, when the audio arrives, how
sure the beat tracker is of a regular pulse in the 5 s it has just received and whether kicks keep coming; it
keeps these in a delay line and, at speaker time, decides "no beat" from what is around that moment (before and
after), with a minimum length so that it does not flicker.

## What result is expected
About 80 on the open tracks. The two stand-ins of the scoreboard reach 69 ("not locked") and 72 ("beat trust
under 0.35") on the six open tracks that have a no-beat stretch, and both are 1.6 to 2.3 s late at the edges
because they look only backwards. Looking both ways should remove most of that delay, and the kick should help
on the electronic tracks (Plastic People: 54 and 38 today), where a no-beat stretch is a passage without drums.

## How I will know it failed
Dropped if the candidate stays under 77 on the open tracks (less than 5 points above the best stand-in, 72),
or if it says "no beat" more than 10% of the time on the open tracks that have no such stretch at all
(03, 05, 09, 11), which the score does not see.

## What it could break
Nothing is expected to move: the candidate calls the production code first and only writes the empty slot
`no_beat`. The gate will confirm it on every other signal. Cost: a few plain numbers per tick.
