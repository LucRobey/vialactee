# P3. Choreography contract (first draft)

Status: DRAFT 1, 2026-11-23. Numbers marked **open** are not chosen yet.
When approved, this lands as an amendment to `docs/contracts/mode_contract.md` and
`docs/contracts/global_mode_contract.md`. It does not replace them.

## 1. In one paragraph

The choreography lab improves the light show. It has no ground truth: nobody can compute whether a show is
beautiful. So a choreography is graded in three layers: laws it must obey (checked by tests), measures it
must pass (checked by numbers, pass or fail only), and your choice between two clips. Agents can do the first
two alone. Only your choice promotes a mode to the installation.

## 2. What a mode may read

The signals are those of the analyzer contract (P2), and nothing else. Three classes:

| Class | Which signals | Rule |
|---|---|---|
| **Required** | HIGH trust: loudness, band energies, spectrum shape, silence | always there; a mode may depend on them |
| **Optional** | every other **trusted** signal (beat, tempo, and later: beat present, kick, ...) | allowed, but the mode must name a **fallback**: what it does when the signal is absent or unsure. This is today's Law 1 ("always alive without the flywheel"), extended to every optional signal |
| **Lab-only** | signals not trusted yet (status Defined, Measured or Candidate) | only in candidate modes inside the lab. Never in `modes/` |

- The list of signals a mode reads is found by the existing code scan, not declared by hand, so it cannot lie.
- Signals with timing "ahead" stay out of modes, as today, except through sanctioned helpers on `Mode`
  (like `drop_hit`).
- A registered mode whose optional signal loses its trust keeps working: its fallback takes over. That is
  the point of the fallback.

## 3. Where lab modes live

- Candidate modes live under `research/choreography/`. They are not registered and not visible in the web
  interface. The tests that pin the 13 registered modes are untouched.
- A candidate may read a new signal without touching the production plumbing. In the lab the signals come from
  a replay (section 4), so the mute proxy, the synthetic listener and the protocols in `music/api.py` are not
  changed for an experiment.
- Promotion is a separate, normal piece of work: move the mode into `modes/`, register it, write its catalogue
  entry, extend the plumbing if it reads a newly trusted signal. It happens only after your choice (section 5).
- A candidate that reads a lab-only signal **cannot** be promoted until that signal is trusted. It can still
  be shown to you: it tells us what the signal would be worth, which helps decide what the music lab should
  work on next.

## 4. What feeds a candidate in the lab

Each candidate is rendered three times on the same passage of music:

| Feed | What it is | What it shows |
|---|---|---|
| **Truth** | signals replayed from the source of truth | the best the idea can look |
| **Realistic** | truth degraded by an **error profile**: misses, false alarms, timing error and delay, at the rates measured on the live analyzer | what it would look like once the signal is live |
| **Live** | the production analyzer of today (existing signals only) | what it looks like now |

A candidate must stay acceptable on the realistic feed, not only on the truth feed. An idea that is
wonderful with perfect kicks and ugly with 10% of them missing is not ready.

The error profiles are measured once by the music lab, then **frozen** with a version number. The
choreography lab cannot edit them.

## 5. Grading, in three layers

### Layer 1: laws (pass or fail, automatic)

The existing ones, unchanged: alive without the beat tracker, smooth fade in silence, no scene branching,
one lead driver and the mute test (Law 7), zero allocation, frame budget. They are already tests.

### Layer 2: measures (pass or fail, automatic)

Numbers computed from the rendered frames against the truth of the passage. Each one is a **filter with a
threshold**, never a score to push up. First list (thresholds **open**, to be set by looking at the 13
existing modes and at clips you like and dislike):

| Measure | Question it answers |
|---|---|
| Punch on kick and snare | does the light visibly change on the hit, more than between hits? (your stated wish) |
| Bass and treble readable | do low and high sounds give clearly different colours or places? (your stated wish) |
| Break behaviour | in a no-beat region, does the mode stop pulsing on a fake beat? |
| Never dark, never stuck | outside silence, is there light, and does it move? |
| Calm | no flicker faster than the eye can take, no full white held for seconds |
| Change over the song | does a loud chorus look different from a quiet verse? |
| Stable under error | does the realistic feed look close to the truth feed? |

Why pass or fail only: if agents were rewarded for a higher "punch" number, the winner would be a mode that
copies the kick straight to brightness. It would top the measure and be a poor show. A threshold only removes
the clearly bad; it does not choose the best.

### Layer 3: your choice

- Candidates that pass layers 1 and 2 are **nominated** by the agents.
- You are shown pairs of short clips of the installation (simulator render), same music, two modes, and you
  pick one or say "no difference".
- The passages come from **held-out tracks**, at positions drawn by a fixed random seed, so agents cannot
  tune a mode for the clip you will see.
- Without telling you, some pairs contain the current best mode (a hidden reference), and some pairs come
  back a second time. This tells us whether a win is real or a coin toss.
- Only a mode that wins your choices is promoted. Agents never promote.

### What keeps this honest

- Truth goes in, and the look is judged by you, not by the same truth: the grading is not circular.
- Laws, measures, thresholds, error profiles and the clip seed are locked: a research agent that edits one
  fails a test. Changing them is a decision for you, logged.
- The measures are checked once against your taste: if a mode you clearly like fails a measure, the measure
  is wrong, not the mode.

## 6. Relation to the existing 48/60 rubric

The rubric in `global_mode_contract.md` (six dimensions, 0 to 10 each, accepted at 48/60) stays as the
**authoring checklist**. What changes is who gives the marks:

| Dimension | Today | Proposed |
|---|---|---|
| D4 zero allocation, D5 frame budget | marked by the agent | measured by the existing tests (layer 1) |
| D6 resilience and fallback | marked by the agent | tests (layer 1) plus "stable under error" and "break behaviour" (layer 2) |
| D1 legibility, D2 simplicity, D3 colour | marked by the agent who wrote the mode | your choice between clips (layer 3). An agent's own marks are advice, not proof |

So a mode is no longer accepted because its author gave it 55/60.

## 7. From the screen to the real installation

Clips are rendered by the simulator. The real chandelier differs: LED brightness curve, colour of the
diffusers, the room, and the delay between sound and light. So:

- A promotion is **provisional** until you have seen the mode on the real installation with music.
- The light-to-sound delay is checked on the installation before a clip verdict is trusted (a late flash
  looks like a bad choreography).
- If screen and installation disagree often, the clip renderer is corrected first; the lab does not go on
  optimising for the screen. How often we check on the real thing: **open**.

## 8. Decisions asked from you

1. Agree with required / optional with fallback / lab-only (section 2)?
2. Agree that measures only filter, and that only your choice promotes?
3. Agree that an agent's own rubric marks stop counting as proof for D1 to D3?
4. How many clip pairs are you willing to judge per week, and how long may a clip be? (It sets the speed of
   the whole choreography lab. Suggestion: 10 pairs of 20 seconds.)
5. The first list of measures (section 5): anything missing that you look for in a show?
