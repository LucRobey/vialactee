# Handoff: source of truth, corrected benchmark, and the two-labs plan

Written 2026-11-22 for an agent continuing this work. Everything below was established in one long session.
Read this file, then `PLAN.md` (same folder), then `work_history/2026-11-22_ground_truth_loader_fix_and_rescore.md`.

## 1. What the owner wants

Vialactée is a music-reactive LED installation (1,304 LEDs, 11 segments, Raspberry Pi; the repo calls it the
chandelier). The owner wants **two research environments run by agents**, built like the existing `research/`
loop (a manager that dispatches researchers, an idea tree, a leaderboard, a morning briefing):

1. **Music lab**: make the real-time analyzer approach a source of truth, signal by signal.
2. **Choreography lab**: improve the light show from music signals. No ground truth exists for it.

The two must be independent and meet only through a contract (a list of music signals). The owner will judge
the design through **four papers**:

- **P1** Source of truth: every variable we could want and the offline tool that produces it.
- **P2** Analyzer contract: the signal list (meaning, range, timing, status, rule for graduating).
- **P3** Choreography contract: what a mode may read, and how a choreography is graded.
- **P4** How research runs in both labs: roles, cycle, gates, logs, what needs the owner.

First drafts of all four were written on 2026-11-23 in `papers/` (start with `papers/README.md`). The owner has
not read them yet; each ends with the decisions asked from the owner. `FEATURE_CATALOG.md` and `feature_table.html`
were the raw material for P1/P2.

## 1b. State on 2026-11-23 (read this first)

- The owner answered P1: five levels of evidence yes; importance ranking yes; drum model (ADTOF) yes; one
  week of ear time offered, this week, if the labelling tools exist. The held-out answer ("the 20 songs") is
  unclear and still to be confirmed. P2, P3 and P4 are not answered.
- New owner rulings: paid and online tools are allowed for truth (Music.ai is business-only; Moises is the
  consumer option, not tried); everything must work for **techno**, not only rock; the music-straight-to-light
  idea is parked (`PLAN.md`).
- `VARIABLE_LIST.md`: the 27 variables wanted, local tool, what Moises would add, expected fit for techno.
- **`research/truth/` now exists**: the automatic draft of the truth for the 20 tracks (`README.md` there).
  `build_truth.py` writes one file per track and `REPORT.md`, which lists what most needs the owner's ear.
  The trained drum model is installed (`run_adtof.py`). 9 tests in `research/tests/test_truth_pipeline.py`.
- **The review tool exists**: `research/truth/review_server.py` + `review.html`, port 8766, launch name
  `truth-review` (the old `beat_viewer.py` is kept but superseded). The owner asked for: only the combined
  beats, every extracted variable visible, easy correction. Corrections are saved to `research/truth/labels/`
  and folded in by `build_truth.py` (`labels.py`). Checked in the browser by the agent; **the owner has not
  used it yet**, so expect requests for changes.
- 2026-11-24: the owner used the tool and found everything good except the section changes. They were replaced
  by `research/truth/sections.py` (measured, no model; on Plastic People the changes fall within 0.7 s of the
  owner's five timed or accepted edges). The owner has not judged the new ones yet.
- 2026-11-25: the owner declared the 20 drafts the full ground truth (variable list closed) and everything was
  committed and pushed (`7e334bc` to `f3b0ee0`). The analyzer now has a contract that mirrors the truth:
  `listener.signals` (`music/MusicSignals.py`, 36 slots, `None` until produced, 8 bridged from existing signals),
  the list in `config/music_signals.json`, section 6 of `docs/contracts/music_analyzer_contract.md`, and parity
  tests. Log: `work_history/2026-11-25_truth_mirrored_signal_contract.md`.
- **Next (agreed with the owner)**: the scoreboard. Run the production `Listener` with the 5 s look-ahead on the
  20 tracks and grade every slot of `listener.signals` against its truth value; mark provisional lines.
- **In parallel**: the owner reviews tracks in the tool. Then techno tracks to add to the 20 (the owner was asked to
  pick some), SongFormer for sections, and a rule for drops and build-ups.

## 2. Owner rulings (do not re-ask)

- **AXIOM-08 does not block truth building.** Reference files may be corrected in this work. In normal analyzer
  research the axiom still holds.
- **Audio input stays as today**: music played through the system, analyzer 5 s ahead of the speakers
  (`fakeDelay = 5.0`, `audio_preset: "spotify"`). The room-microphone case is out of scope.
- **Signal list**: a data file outside `music/`, with its status record in `research/`. The benchmark *proposes*
  status changes; only the owner makes a signal trusted by editing the contract.
- **New agent skills may be added** (update `tests/governance/test_skills_governance.py`, which pins five).
- **List every wanted signal now**, but fully define only those that have truth.
- **Importance of a signal** = value for the show x realistic chance the live analyzer can produce it. Lyrics are
  explicitly unimportant.
- Existing `research/benchmarks/` and `research/experiments/` stay in place as the music lab (the owner was asked
  whether to rename them for symmetry and did not answer; default is keep).
- These are also saved in the agent memory folder for this project.

## 3. State of the repository (nothing is committed)

Modified, tracked:
- `research/benchmarks/engine/evaluator.py`: loader fix (see section 4).
- `research/benchmarks/ground_truth/neural/`: 59 files (12 tracks' beats/downbeats/meta, 13 salience files and
  their meta block, 2 corrected durations, manifest).
- `work_history/README.md`: index row.
- `config/app_config.json`: **not ours**, modified before this session. Leave it out of any commit.

New, untracked:
- `research/tests/test_audio_loader.py`
- `work_history/2026-11-22_ground_truth_loader_fix_and_rescore.md` (status IN PROGRESS, commits "none yet")
- `research/analyzer_trials/` (this folder; its `.gitignore` excludes `.venv/` and `output/`)
- `.claude/launch.json` (starts the beat viewer)

Tests: `python -m pytest -q` gave 631 passed, 5 deselected, 275 subtests. Governance tests pass with the new log.
The owner was offered a commit and has not answered. Repo rules: Conventional Commits, one per logical step,
never `git add -A`, never force.

## 4. The benchmark problems found and what was done

**Loader bug (fixed).** `load_audio_file` returned cached `.npz` audio (stored at 44.1 kHz) labelled with the
rate the caller asked for. Callers asking 22.05 kHz got half-speed audio: `extract_neural_reference.py` and
`plot_beat_salience.compute_beat_importance`. Benchmark runs ask 44.1 kHz and were unaffected.

**References corrected.**
- 10 tracks had beats running to twice the song length: Stayin' Alive, 01-Plastic-People, Nobody Rules the
  Streets, Boogie Wonderland, Roxanne, Another One Bites The Dust, September, Feeling Good, Djon maya maï,
  Money For Nothing_1.
- Nightcall and Pumped Up Kicks (both in neural-core) had been "repaired" earlier by halving timestamps, leaving
  beats at double tempo.
- All 13 `.salience.npz` files spanned twice the song length (all 10 neural-core tracks included).
- Only those were replaced. A fresh BeatNet run here does **not** reproduce the old files on 12 healthy tracks
  (e.g. "Power" comes out at half tempo), so do not regenerate everything.
- Old references are in git history and exported at `output/neural_old/`.

**Re-score of all 10 models** (F1@50 ms macro, standard benchmark, old refs vs corrected):

| Model | neural-core | rank | neural (70) |
|---|---|---|---|
| MultiBandOnsetAudioAnalyzer | 74.5 -> 80.6 | 3 -> 1 | 61.1 -> 71.2 |
| CostasLoopAudioAnalyzer | 71.7 -> 77.5 | 4 -> 2 | 59.8 -> 70.3 |
| DyadicMetricalAudioAnalyzer (production) | 79.3 -> 75.0 | 1 -> 3 | 61.2 -> 69.7 |
| DyadicWaveletAudioAnalyzer | 79.3 -> 74.9 | 2 -> 4 | 61.2 -> 69.6 |

The "before" 79.3 reproduces the leaderboard's 79.2. The whole gap is Nightcall and Pumped Up Kicks, where the
production model doubles the tempo. Production is MultiBandOnset plus the Cycle 012 tempo-level arbiter.
Stayin' Alive: production scores 1.0% on the old reference and 98.3% on the corrected one; the research history
treats that song as a "180 degree upbeat trap".

**Look-ahead test** (models run inside the production `Listener`, corrected refs, neural-core):

| Model | no look-ahead | 5 s |
|---|---|---|
| MultiBandOnset | 83.5 | 83.2 |
| TimbreAdaptive | 82.9 | 82.6 |
| CostasLoop | 83.2 | 82.1 |
| AudioAnalyzer (legacy) | 81.1 | 81.4 |
| DyadicMetrical (production) | 78.6 | 78.1 |

Look-ahead does not change beat scores. Through the production path the legacy analyzer scores 81, against 54
in the standard benchmark (which uses `MockAudioIngestion`, 8 bands, `fakeDelay: 0.0`): the standard benchmark
distorts the ranking of older models. Cause not investigated. DualFlywheel and SparseImpulse crash in `Listener`
(they expect 8 bands).

**Not fixed, not decided:**
- `LEADERBOARD.md`, `RESEARCH_HISTORY.md`, `RESEARCH_IDEA_TREE.md` are untouched. How to record the re-score,
  and whether to change the production default, are the owner's decisions. Advice given: do not switch on this
  alone (10 tracks, machine-made references).
- `extract_neural_reference.py --out-dir` is parsed and ignored: it always writes to the official folder.
- Cache files replace apostrophes with underscores (`Sweet Child O_ Mine.mp3.npz`); the loader looks for the exact
  name, falls back to `torchaudio` / `librosa`, which the project `.venv` lacks, and crashes on those tracks.
- `run_benchmark.py` drops crashed tracks from the macro average without saying so.
- The six replaced tracks outside the 20 trial tracks have no second tracker to check them.

## 5. The trial tools in this folder

Own environment: `research/analyzer_trials/.venv` (1.3 GB: torch CPU, demucs, librosa, beat_this, BeatNet,
madmom, mir_eval). Run scripts from this folder with `.venv/Scripts/python.exe <script> [track ids]`. Outputs go
to `output/` (3.8 GB of stems, git-ignored). The 20 tracks are in `tracks.json`.

| Script | Produces |
|---|---|
| `run_beats.py`, `run_beatnet.py` | beats and downbeats from Beat This, librosa, BeatNet (correct speed) |
| `run_chords.py` | chords with times (BTC model, in `vendor/`) |
| `run_demucs.py`, `derive_from_stems.py` | stems; vocal on/off and kick/snare/hat hits |
| `build_grid.py` | combined beat grid, one vote per tracker per beat (`output/grid/`) |
| `add_salience.py` | per-beat drum salience, no-beat regions, drum hits per beat |
| `eval_grid.py` | timing of each tracker against drum onsets |
| `beat_viewer.py` + `viewer.html` | local viewer at http://127.0.0.1:8765 (lamps, waveform, clicks, regions) |
| `rescore_all.py`, `rescore_lookahead.py` | the re-scores in section 4 |

Machine quirks: no MSVC, but `gcc` from Strawberry Perl builds madmom (recipe in `README.md`). Windows app
control blocks scikit-learn's DLLs: do not import sklearn. `essentia` does not install. The benchmark must be run
with this folder's `.venv` if every track has to load.

Findings from the trials:
- Averaging the three trackers gives steadier beat times than either neural tracker alone (7.9 ms spread against
  10.5 and 10.4). Forcing the grid to be regular helps studio tracks and hurts live ones.
- "No beat" is detected where Beat This and BeatNet stop landing together for 5 s and 6 beats. Drum loudness
  cannot find it (out-of-time percussion is loud). Tuned on two tracks only.
- **Known weak**: the kick/snare/hat split (one label per hit, hats hidden behind kicks) and the vocal on/off
  rule (says 100% on instrumentals). A trained drum model (ADTOF) was proposed, not installed.
- `hand_labels.json` holds the only human labels: Plastic People (three breaks, one confirmed "beat present")
  and Bohemian Rhapsody (two regions wrongly flagged). It records which edges the owner timed and which he only
  accepted as displayed.

## 6. The plan (`PLAN.md`, draft 2, after an independent critique)

0. Owner decisions: **done**.
1. Corrected truth and full re-score: **done** (recording it in the ledgers is open).
2. Four papers, first draft, thresholds left open: **drafted 2026-11-23, waiting for the owner's reading**.
3. Thin slice: replay truth into `tools/choreography_probe.py`, one track, one clip, the owner looks; add the
   test that forbids the two labs importing each other.
4. Papers final, landed as amendments to the existing contracts.
5. Truth factory (`research/truth/`).
6. Music lab: evaluator through `Listener` with the real look-ahead; per-signal scores.
7. Choreography lab.
8. Roles, automation, pilot cycles.

Points the critique established and the plan adopted:
- The contract already half exists: `docs/contracts/music_analyzer_contract.md` lists 73 live signals with trust
  levels, behind `music/api.py`. P2 is an amendment to it, not a new document.
- Trust is, by that contract, "not encoded in Python and not enforced by a test". Keep status out of `music/`.
- Choreography grading must not be circular (truth in, sync scored against the same truth). Adopted: error
  profiles measured from the live analyzer and frozen, held-out tracks, measures only pass or fail, agents
  nominate and only the owner's choice between clips promotes.
- A mode reading a new signal also touches `DriverMuteProxy`, `SyntheticListener` and the protocols in
  `music/api.py`; tests pin 13 registered modes, so candidate modes live under `research/choreography/`.
- Draft papers outside `docs/`: `tests/governance/test_docs_parity.py` fails on paths that do not exist yet.
- Proposed layout: `research/truth/` (shared), existing folders as the music lab, new `research/choreography/`.

## 7. Repository rules that matter here

Entry point `.agents/AGENT.md`, then `.agents/CONSTITUTION.md`. Sealed sectors `music/`, `transitions/`, `mood/`
are reached only through their `api.py`. 500-line cap on production files. `docs/axioms/` changes need the owner.
Every session writes a `work_history/` log and an index row. The existing research skills
(`.agents/skills/vialactee-researcher`, `-research-manager`) are written for another tool's commands and cover
beat tracking only.

## 8. Working with the owner

- He is not a signal-processing specialist: use plain words, lead with the result, keep answers short.
- He checks things by ear in the viewer and gives timings; treat those as the only truth and save them.
- Vocabulary: he writes "bit" for beat. Call the installation the chandelier or the installation, not "the wall".
- He wants visible kick and snare punch and readable bass/treble colours in modes.
- Say plainly when a number is unverified or when something went wrong.
