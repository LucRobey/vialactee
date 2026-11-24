# P1. Source of truth (first draft)

Status: DRAFT 1, 2026-11-23. Thresholds and numbers marked **open** are not chosen yet.
When approved, this replaces `research/benchmarks/source_of_truth.md`.

## 1. In one paragraph

The source of truth is, for each song, a file that says what is in the music and when: where the beats are,
where there is no beat, which drum hits, which chord, which section. It is built offline, with tools far too
heavy for the Raspberry Pi and with your ears. It is used for two things: to grade the live analyzer (music
lab), and to feed the light show with reliable signals while a choreography is being designed (choreography
lab). Today it holds beats for 70 songs and a richer description for 20 of them. Only a small part of it has
been checked by a human.

## 2. How sure we are: five levels of evidence

Every value in a truth file carries one of these levels. The level decides what the value may be used for.

| Level | Meaning | May grade the analyzer? |
|---|---|---|
| **H** timed by ear | You gave the time yourself in the viewer | yes |
| **A** accepted by ear | A tool proposed it, you looked and said it is right | yes |
| **M2** machines agree | Two or more independent tools give the same answer | yes, flagged as machine-made |
| **M1** one machine | A single tool, no cross-check | no: shown in reports, not counted |
| **W** known weak | We already know the tool is often wrong | no |

Rules that follow:
- A score is always reported with the level it was graded against ("F1 on M2 beats", "accuracy on H regions").
- Where the tools disagree, the moment is marked "undecided" and is left out of the score. It is not guessed.
- H and A outrank everything. A human label is never overwritten by a tool.
- Exact truth exists for the 8 synthetic test tracks only (we generate the audio, so we know the beats).

## 3. Every variable we could want

**Importance** = value for the show x realistic chance that the live analyzer can produce it
(your rule). **State** is the best level we have today on the 20 trial tracks.

### 3.1 Top importance

| Variable | Use for the lights | Offline tool | How its quality is checked | State |
|---|---|---|---|---|
| Beats | pulse, step, chase | Beat This + BeatNet + librosa, merged (`build_grid.py`) | agreement between trackers; timing against drum hits; your ear in the viewer | M2 on 20 tracks; M1 (BeatNet alone) on the other 50 |
| Beat present / no beat | go ambient in a break instead of faking beats | the two neural trackers stop agreeing for 5 s and 6 beats (`add_salience.py`) | your timings | H/A on 2 tracks, M1 on 18. Rule tuned on those 2 tracks only |
| Tempo and tempo level (normal, half, double) | speed of motion; avoids the double-tempo error | from the merged beats | trackers agree on the level; your ear when they do not | M2 where trackers agree, undecided elsewhere |
| Kick hits | the "boom" | rule on the drum stem today; trained drum model (ADTOF) proposed | compare two methods; your ear on a few bars | W |
| Snare / clap hits | backbeat flash | same | same | W |
| Strength of each beat | brightness per beat | level of the drum stem at the beat (`add_salience.py`) | only sanity checks so far | M1 |
| Loudness, band energies, brightness of sound | master brightness, bass and treble colours | direct measurement, no model | exact by construction | computed on demand; the live analyzer already has these |
| Silence, stop, fade-out | blackout, freeze, slow fade | level per stem | direct measurement | computed on demand |

### 3.2 High importance

| Variable | Use for the lights | Offline tool | How its quality is checked | State |
|---|---|---|---|---|
| Downbeat and position in the bar (1-2-3-4) | accent the "1", patterns per bar | Beat This and BeatNet downbeats, not merged yet | the two agree; your ear ("is this the 1?") | M1, partly |
| Drop, build-up, breakdown | the main moments in electro | rules on kick presence, energy and risers; no ready tool | your ear, track by track | none |
| Section change | change of scene | simple novelty curve today; section models (allin1, SongFormer) not tried | two methods agree; your ear | W |
| Hi-hat hits | sparkle, fine pulse | same as kick; today hats are hidden behind kicks | same | W |
| Singer on / off | spotlight when the voice is in | level of the vocal stem (says 100% on instrumentals) | your ear | W |
| Kick drops out / comes back | marks breakdown and return | kick presence over time | follows from kick quality | none (derivable once kicks are good) |

### 3.3 Medium importance

| Variable | Offline tool | State |
|---|---|---|
| Chords and chord changes (slow colour moves) | BTC model (`run_chords.py`) | M1 |
| Key, major or minor (base palette) | madmom key model, not run | none |
| Bass note | chords, or pitch of the bass stem | none |
| Section labels (verse, chorus, ...) and repeats | allin1 / SongFormer, not tried | none |
| Phrases of 4, 8, 16 bars | needs downbeats and sections first | none |
| Level per instrument family (drums, bass, voice, other) | Demucs stems | M1 (stems exist) |
| Fills and rolls, risers, percussion density | rules on hits and on the "other" stem | none |
| Kick pattern type (four-on-the-floor, breakbeat, half-time) | pattern of kicks per bar | none |
| Stereo position | channel level difference | none (cheap) |

### 3.4 Low importance (listed, not planned)

Melody and bass-line notes, melody direction, arpeggios, long held notes, swing, time signature, toms and
cymbals, tension, sung or spoken, lead or backing voice, mood and genre tags, instrument presence, guitar and
piano stems, key changes. **Lyrics** are explicitly unimportant (your ruling) and are not pursued.

The full raw list with sources is in `../FEATURE_CATALOG.md`.

## 4. What truth we really have today

| Set | Tracks | Content | Level |
|---|---|---|---|
| Synthetic | 8 generated tracks | beats | exact |
| Library beats (`ground_truth/neural/`) | 70 | beats, downbeats from BeatNet; 12 tracks corrected on 2026-11-22 | M1 (M2 on the 20 trial tracks, by comparison with two other trackers) |
| Trial set (`analyzer_trials/output/`) | 20 | merged beat grid with votes, no-beat regions, beat strength, drum hits, chords, stems, vocal on/off, section boundaries | M2 down to W, see section 3 |
| Hand labels (`hand_labels.json`) | 2 (Plastic People, Bohemian Rhapsody) | 9 no-beat regions, 3 "the beat is there" regions | 3 edges H, the rest A |
| Ballroom (academic) | 698 | beats annotated by experts | human, but dance music outside our styles; audio not downloaded |

Honest summary: beats are in decent shape. Everything else is machine opinion, and the kick / snare / hat
split and the singer on/off rule are known to be wrong often.

Known defects of the current tools (not fixed yet):
- `extract_neural_reference.py --out-dir` is ignored: the tool always writes into the official folder.
- Some songs fail to load in the project environment (apostrophe in the file name), and the benchmark then
  leaves them out of the average without saying so.
- Six of the 12 corrected tracks are outside the trial set: nothing cross-checks their new beats.

## 5. Truth versions

- One truth file per track, with a version number, the date, the tool versions and a fingerprint of the audio.
- Every change makes a new version and a line in a change log: what changed, why, who (tool or you).
- Every score ever published names the truth version it was graded against. Scores on different versions are
  never put in the same ranking.
- Old versions stay available (git history), so a past result can be re-checked.
- Only the truth-building work may change truth (your ruling on AXIOM-08). A researcher who wants a reference
  changed files a request with the evidence and does not edit it.

## 6. Held-out tracks

A held-out track is one the research agents never look at in detail. They get one global score on it, not the
per-beat view. It is how we notice that a model has learned the test songs instead of the music.

- The 10 `neural-core` tracks have been tuned on for 12 cycles: they stay open, they cannot be held out.
- Proposal: hold out 6 of the 11 trial tracks that are not in `neural-core`, two per style:
  Hotel California, Message In A Bottle, You Know I'm No Good, Another One Bites The Dust,
  Nobody Rules the Streets, and one more electro track to be added to the trial set.
- Plastic People stays open: it carries most of the hand labels, and agents need to study it.
- The choreography lab takes its test clips from held-out tracks as well (see P3).
- **Open**: the exact list and the size (6 is a suggestion).

## 7. Tool licences

Written from memory, **not verified**. To be checked before the truth factory is built (plan chapter 5).

| Tool | Licence as I recall it | Remark |
|---|---|---|
| Beat This, Demucs, BTC | MIT | free use |
| librosa | ISC | free use |
| BeatNet | CC BY 4.0 | free use with credit |
| madmom | code BSD, trained models non-commercial | fine for a private installation |
| ADTOF, LarsNet (not installed) | non-commercial, I believe | same remark |

None of these tools runs on the installation. They only produce reference files on the PC. If the project is
ever sold or published with the truth files, the non-commercial ones must be looked at again.

## 8. Decisions asked from you

**Owner answers, 2026-11-23:** 1 yes. 2 yes. 3 "the 20 songs that we chose earlier" (to be clarified: if all
20 are held out, no richly described track stays open for the agents). 4 yes. 5 one week of the owner's time,
this week, to make the truth as good as possible, provided the tools to label are there. Added by the owner:
paid and online tools are allowed if they give a better truth.

1. Agree with the five levels, and with "M2 may grade, M1 may not"?
2. Agree with the importance ranking in section 3? Move anything up or down.
3. Held-out list (section 6).
4. May I install the trained drum model (ADTOF) to repair kick / snare / hat? It is the largest gap.
5. How much ear time are you willing to give per track? It decides how many variables can reach level H or A.
