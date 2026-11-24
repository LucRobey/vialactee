# P2. Analyzer contract (first draft)

Status: DRAFT 1, 2026-11-23. Numbers marked **open** are not chosen yet.
When approved, this lands as an amendment to `docs/contracts/music_analyzer_contract.md`. It does not replace it.

## 1. In one paragraph

The contract is the list of music signals. It is the only thing the two labs share: the music lab works to
make each signal true, the choreography lab works with the signals as listed and never looks at how they are
made. The list already half exists: the current contract documents 73 live signals with a trust level. This
paper adds what is missing: where each signal stands against the source of truth, which new signals we want,
and the rule by which a signal becomes trusted.

## 2. Three places, three jobs

| What | Where | Who changes it |
|---|---|---|
| **Definitions**: name, meaning, range, timing, how it is graded | one data file outside `music/` (proposal: `config/music_signals.json`) | agents, through normal review |
| **Status record**: latest scores, truth version, proposals | `research/` (proposal: `research/truth/SIGNAL_STATUS.md`) | the benchmark writes it |
| **Trust**: how a mode is allowed to use the signal | the tables of `music_analyzer_contract.md`, as today | **you only** |

The benchmark proposes. It never changes trust. Nothing inside `music/` knows about status or trust (already
the rule today: trust is "not encoded in Python").

## 3. Timing: when a signal is known

The installation hears the music 5 seconds before the speakers play it. So each signal has one of three timings.

| Timing | Meaning | Who may use it |
|---|---|---|
| **Speaker time** | describes what is heard right now | modes |
| **Ahead** | describes what will be heard, up to 5 s from now | the context engine and transitions (prepare a drop, a scene change); modes only through a sanctioned helper |
| **Whole song** | needs the full song (key, section labels, repeats) | not available live. Listed as wanted, cannot be trusted in this setup |

Only today's setup is covered (music played through the system, 5 s look-ahead). The room-microphone case is
out of scope (your ruling).

## 4. Status of a signal: five steps

| Status | Meaning |
|---|---|
| **Wanted** | useful for the show; no usable truth yet |
| **Defined** | truth exists at level H, A or M2 (see P1) and the way to grade is written |
| **Measured** | the live analyzer outputs it and it has a score on the benchmark |
| **Candidate** | the score passes the graduation rule; the benchmark has written a proposal |
| **Trusted** | you have edited the contract |

Status and trust are two different things. Status says how far the proof has gone. Trust (HIGH, MEDIUM, LOW)
says how a mode must handle the signal. The 73 existing signals keep the trust they have today; this paper
does not change any of it.

## 5. The rule for graduating (shape only, numbers open)

A signal moves from Measured to Candidate when **all** of these hold:

1. It is graded through the real path: inside the production `Listener`, with the 5 s look-ahead, at speaker
   time. (Today's benchmark does not do this; see P4.)
2. It is graded only against truth of level H, A or M2, on a named truth version.
3. Its score on the open tracks is at least **X** (open, per signal).
4. Its score on the held-out tracks is at least **Y** (open), and no single track is below **Z** (open).
5. It also knows when it is wrong: where it has a confidence value, low confidence matches the moments it
   fails.
6. It costs no more than the frame budget allows (3 ms per tick for the whole analyzer, as today).
7. No already trusted signal gets worse because of it (the per-signal gate in P4).

Then the benchmark writes a proposal in the status record, with the numbers and the weak tracks. You decide.
A trusted signal that later falls under the rule is flagged; it is not downgraded automatically.

X, Y and Z cannot be chosen now: they depend on how good the truth itself is. If two offline tools agree with
each other only 90% of the time, asking 95% from the live analyzer means nothing. They are set in plan chapter 4.

## 6. The signals that are fully defined today

These have truth that may grade (P1 levels H, A, M2).

| Signal | Meaning | Range | Timing | Truth | How it is graded | Live today |
|---|---|---|---|---|---|---|
| Beat | the instant of each beat | event | speaker time | merged beat grid (M2, 20 tracks) | found within 50 ms, counted as hits and false alarms (F1), as today; plus longest stretch held without error | `is_beat`, `beat_phase`: MEDIUM trust, 75 to 83 depending on the model |
| Tempo | beats per minute at the level a person would tap | 60 to 260 | speaker time | from the grid, where trackers agree on the level | share of the time within a few % of truth, at the **right** level (half and double counted as wrong, and reported apart) | `bpm`: MEDIUM. Production doubles the tempo on Nightcall and Pumped Up Kicks |
| Beat present | is there a beat to follow right now | yes / no | speaker time | no-beat regions (H/A on 2 tracks) | share of the time correct; delay at each edge | no direct signal. Closest: `is_locked`, `beat_trust`, `rhythm_salience` (never graded) |
| Silence | nothing is playing | yes / no | speaker time | direct measurement | share of the time correct | `is_silent`: HIGH, never graded but simple |
| Loudness and band energies | how loud, and where in the spectrum | 0 to 1 | speaker time | direct measurement | follows the measured curve | HIGH. Graded only for delay against the speakers |

Notes:
- "Beat present" is the first new signal worth scoring end to end: it has human truth, a clear use (go ambient
  in a break), and the analyzer has three half-related outputs that have never been checked.
- The beat scores above are on machine truth. They say "agrees with three offline trackers", not "is right".

## 7. Signals partly defined (truth too weak to grade yet)

| Signal | Timing | What blocks it | Live today |
|---|---|---|---|
| Kick hit, snare hit, hat hit | speaker time | truth is level W (one label per hit, hats hidden) | `beat_tag` (MEDIUM, never graded), `band_flux` |
| Beat strength | speaker time | truth is M1 | `is_real_beat`, `is_dropped_beat` |
| Downbeat, position in bar | speaker time | the two trackers are not merged; "which beat is 1" unchecked | none |
| Section change | ahead and speaker time | truth is W | `is_verse_chorus_change`, `is_song_change`: LOW |
| Drop, build-up | ahead | no truth at all | `scene`, `drop_countdown`, `is_drop_impact`: LOW |
| Chord, chord change | speaker time | truth is M1 | chroma: LOW, uncalibrated |

## 8. Wanted signals (no definition yet)

In order of importance (see P1 section 3): singer on/off, kick drop-out and return, key and bass note, section
labels, phrases, level per instrument family, fills and risers, kick pattern type, stereo position.
Low importance and not planned: melody, notes, swing, mood tags, lyrics.

Each gets a full definition only when its truth reaches a level that may grade.

## 9. What the amendment changes in the existing contract

- Adds a "Status" column next to "Trust" in the signal tables, filled from the status record.
- Adds sections 3 to 5 of this paper (timing classes, status steps, graduation rule).
- Adds a pointer to the definitions file and the status record.
- States that trust is changed by the owner only (today: "edit its table row here and nowhere else", with no
  word on who).
- Changes no existing trust level and no code in `music/`.

## 10. Decisions asked from you

1. Agree with the three places (section 2), and with `config/music_signals.json` as the home of the definitions?
2. Agree with the five status steps and that only you make a signal trusted?
3. Agree that half and double tempo count as **wrong** for the tempo signal? (For the lights they are: the
   show runs twice too fast or too slow. The benchmark also reports a measure, AMLt, that accepts them.)
4. Agree that "beat present" is the first new signal to take through the whole chain?
