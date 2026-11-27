# Proposal to the owner: five new signals (pilot cycle of the music lab, 2026-11-27)

> **Decision, 2026-11-27: approved by the owner.** The five signals were moved into the production analyzer
> (`music/BandKickSignals.py`, called by `DyadicMetricalAudioAnalyzer`); the scores of the production model are
> now exactly those of the candidate below. Still open from this page: no mode has shown them to the owner, they
> are not rated, and the cost on the Raspberry Pi is not measured.

## What is proposed

A candidate analyzer, `BandKickSlotsAudioAnalyzer` (`research/experiments/models/`), that is the production
model plus five signals the installation does not have today:

| Signal | What it says |
|---|---|
| `band_bass`, `band_mid`, `band_high` | how much sound there is in the bass, the middle and the treble, from 0 to 1 |
| `kick` | a kick drum hits now, and how hard |
| `kick_present` | the kick is "in": there was one in the last 2 seconds and another comes in the next 2 |

Nothing the production model already does is changed: beats, tempo and the rest are computed by the same code.

## Results on the 20 truth tracks (0 to 100)

| Signal | Tracks I tuned on (10) | Tracks I did not look at (10) | All 20 | Weakest tracks |
|---|---|---|---|---|
| `kick` | 75 | 85 | 80 | Genesis 49, Roadgame 60, Sugar 62 |
| `kick_present` | 81 | 89 | 85 | Pumped Up Kicks 63, Message In A Bottle 64 |
| `band_bass` | 82 | 84 | 83 | Nightcall 36, Roadgame 48 |
| `band_mid` | 89 | 88 | 89 | Hotel California 72 |
| `band_high` | 93 | 94 | 93 | Hotel California 82 |

- The kick finds 85% of the true kicks, and 79% of what it reports is a true kick. It is about 21 ms late.
- `kick_present` is right 99% of the time while the kick is in, and 71% of the time while it is out: its
  weakness is staying on too long, because false kicks keep it alive.
- All five are graded on truth that may grade (two tools agreeing, or exact measurements).

## Checks

| Check | Result |
|---|---|
| Gate: no existing signal gets worse (margin 1 point) | passed: all seven existing signals are identical to the point |
| Old regression rule (AXIOM-08): beat score on the synthetic tracks | 96.2 for both models: no regression |
| Cost per tick on this PC | 0.49 ms to 0.53 ms for the whole listener step (+9%); 0.21 to 0.22 ms in the old benchmark |
| Cost on the Raspberry Pi | **not measured** |
| No array created per tick | by construction (fixed arrays, scalar maths); **not verified by a memory test** |
| Tests | 8 new tests, including the candidate inside the listener on a synthetic song |

## What I ask you

1. **Listen before deciding.** A score of 80 on kicks says nothing about how it looks. The honest next check is
   a mode driven by this kick, on a song you know.
2. **If you like it: may these five signals go into the production analyzer?** That is a change to the code
   running on the installation, so it is yours to decide. It would be done as a separate, small change.
3. **Do not rate them yet.** I suggest no trust level until you have seen them drive a light.

## What this result does not tell you

- The kick truth comes from a drum model trained on rock and pop. On the electronic tracks the truth itself
  is less sure, and that is where the candidate is weakest (Genesis, Roadgame).
- `band_sub` (under 60 Hz) stays empty: the audio front end has no band that low, and adding one means
  changing the front end.
- The "tuned on / not looked at" split is my own provisional one (odd and even track numbers). The held-out
  list is still your decision.
