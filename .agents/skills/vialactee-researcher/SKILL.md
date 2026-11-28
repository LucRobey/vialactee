---
name: vialactee-researcher
description: Step-by-step procedure for an agent working alone in the music lab (research/scoreboard, research/experiments/models). Use when asked to run a cycle of the music lab, to improve or fill a signal of the analyzer, or to work on a line of the music work list.
---

# Music lab: one research cycle, alone

You make the live analyzer of the installation better at one signal, and you prove it against the source of truth. You never change the installation itself: you build a **candidate**, the lab grades it, and a proposal goes to the owner. The owner decides.

One launch = one cycle = one line of the work list. Then you stop and report.

`PY` below stands for `research/analyzer_trials/.venv/Scripts/python.exe`. Run everything from the repository root. Tests use the project environment: `.venv/Scripts/python.exe -m pytest -q`.

---

## 1. Before anything

1. `git status`, then `.venv/Scripts/python.exe -m research.guard snapshot music` (it remembers what was already changed, so it is not blamed on you).
2. Read [`research/scoreboard/STATUS.md`](../../../research/scoreboard/STATUS.md) (where every signal stands, every run made) and [`research/scoreboard/BACKLOG.md`](../../../research/scoreboard/BACKLOG.md) (the work list).
3. Take the first line whose state is `open`, unless the launch message names one. Lines under "Blocked" are not yours to take.
4. Read what the signal means and how it is graded: its entry in [`config/music_signals.json`](../../../config/music_signals.json), and [`research/scoreboard/README.md`](../../../research/scoreboard/README.md) ("Rules of the grading").

## 2. What you may change

| You may | You may not |
|---|---|
| add a candidate in `research/experiments/models/` | touch `music/`, `modes/`, `core/`, `config/`, `docs/`, `tests/` |
| write in your run folder `research/scoreboard/runs/<run>/` | edit the truth (`research/truth/`) or the track split (`split.json`) |
| update your line of `BACKLOG.md` | edit the grading tools (`research/scoreboard/*.py`) |
| add `research/tests/test_candidate_<name>.py` | edit another candidate, or the choreography lab |
| add a session log in `work_history/`, a question in `research/OWNER_QUESTIONS.md` | commit or push, unless the launch message says so |

`.venv/Scripts/python.exe -m research.guard check music` tells you if you stepped outside. If the work truly needs a locked file, **stop and say so in your report**: that is a finding, not a failure. Someone else may be working in the repository at the same time: a file the guard names that you did not touch is not yours to undo, name it in your report.

## 3. The cycle

### Step 1. Open the run

    PY -m research.scoreboard.cycle start <short_name> --signal <signal> --idea <M0x>

It creates `research/scoreboard/runs/<date>_<short_name>/` with `PLAN.md`. Fill in the plan (four short answers) **before writing the candidate**; the tool refuses to grade while it still contains `TODO`. Looking first is fine and makes the plan honest: read the scores, open the truth files, record a capture. Mark your line of `BACKLOG.md` as `taken by <run>`.

Know what the score will rest on before you plan. Open two or three truth files (`research/truth/tracks/<id>.json`) and look at the level of the values your signal is graded against: `H` and `A` are the owner's ear, `M2` two tools agreeing, `X` an exact measurement, and these may grade; `M1` is one tool alone and is only indicative ([`research/truth/README.md`](../../../research/truth/README.md)). `SCOREBOARD.md` gives production's score on every track, check tracks included: that is public. What stays hidden is how *your candidate* does on each check track.

### Step 2. Write the candidate

One file, `research/experiments/models/<ClassName>.py`, file name = class name. Start from this:

```python
from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer

class NoBeatSlotAudioAnalyzer(MultiBandOnsetAudioAnalyzer):      # the main analyzer
    """Production model plus the `no_beat` slot."""

    def detect_band_peaks(self, current_time, dt, fps_ratio):
        super().detect_band_peaks(current_time, dt, fps_ratio)   # everything production does, unchanged
        self.signals.no_beat = ...                                # your value, AT SPEAKER TIME
```

Rules that decide whether the score means anything:

- **Speaker time.** The analyzer hears the music `self.lookahead_seconds` (5 s) before the speakers play it. A slot must say what is being heard *now*. So measure when the audio arrives, keep the value in a delay line, and write it when the speakers reach it. [`music/BandKickSignals.py`](../../../music/BandKickSignals.py) is the working example (`_measure`, `_write_slots`). The 5 s of future are an advantage: a state signal may look both ways.
- **`None` until you know.** Leave the slot `None` until the first audio has reached the speakers. `None` means "does not know"; never write a guess.
- **No new array per tick.** Create arrays in `__init__`, use plain numbers in the update (AXIOM-02). The installation is a Raspberry Pi.
- **Subclass and add.** Call `super()` first and do not change what it computed, unless changing an existing signal is the idea (then say so in the plan: the gate will watch every other signal).
- **A slot the listener copies.** `beat`, `bpm`, `drop`, `section_change`, `buildup`, `silence`, `loudness`, `brightness` are copied by the `Listener` from older signals after your code runs, so writing them does nothing, unless your class says `claimed_slots = ("brightness",)`. For `beat` and `bpm` it is usually better to change what they are copied from (`is_beat`, `effective_bpm`).
- **Arrival time and speaker time.** What the analyzer computes on a tick describes the audio that just arrived, 5 s ahead of the speakers: its `confidence_score`, its streams, its kick detection. What the `Listener` and the context show (`beat_trust`, `context.is_locked`) are the same things delayed to speaker time. A stand-in that is "2 s late" in the scoreboard is often a delayed value used without the future it could have had.
- **Private fields of production code.** A candidate may read them when nothing public gives the value at arrival time (for instance the kick times inside `self._band_kick`). Say it in the proposal: at promotion that reading becomes a proper hand-over.
- What the analyzer already has to build on: the 32 bands (`self.ingestion.multiband_fft_values`), their rise this tick (`self.dE`), the kick stream (`kick_odf_buffer`; the snare and hat streams, `snare_odf_buffer` and `hat_odf_buffer`, exist only in `DyadicMetricalAudioAnalyzer`), the beat phase and trust. Read `music/MultiBandOnsetAudioAnalyzer.py` (the main analyzer; `music/DyadicMetricalAudioAnalyzer.py` is the same plus half-beats, with snare and hat streams of its own); do not edit them.

### Step 3. Grade on the open tracks, as often as you need

    PY -m research.scoreboard.cycle grade <run> --candidate <ClassName>

About a minute. Read `runs/<run>/OPEN.md`: your signal against production and against the scoreboard's stand-ins, track by track, on how many tracks it is graded and how many of those have checked truth, and the gate on every other signal. You may tune on these ten tracks. To try many settings quickly, record once and replay the rule offline, as [`runs/2026-11-27_bands_kick/tune_kick.py`](../../../research/scoreboard/runs/2026-11-27_bands_kick/tune_kick.py) does; keep such scripts in your run folder and their recordings under `research/scoreboard/output/` (not committed).

A stretch signal (no beat, kick present, silence) is graded only on tracks where the truth has such a stretch; elsewhere a wrong "on" costs nothing. Measure that yourself on the open tracks and put the numbers in the proposal.

Stop tuning when a new grade moves the score by less than a point, or after eight grades. If you tuned offline, one grade that matches your replay is enough. A candidate that fails the gate is not ready, whatever its target score.

### Step 4. Check, once

    PY -m research.scoreboard.cycle check <run> --candidate <ClassName>

It plays the ten tracks nobody tuned on and gives **one number per signal**. The run is then frozen: no more grading. If the score holds, the result is real. If it falls by much more than the spread between open tracks, you fitted the open tracks: say so. Never look for the track detail of the check set, and never start a second run with the same candidate to "check again".

### Step 5. Close

Proposal, when the check passed and the gain is worth the owner's time:

    PY -m research.scoreboard.cycle close <run> --verdict propose --summary "one sentence, plain words"

The first call only writes the skeleton of `PROPOSAL.md` with the numbers; replace every `TODO`, then call it again to close. Otherwise:

    PY -m research.scoreboard.cycle close <run> --verdict archive --summary "what was tried and why it is dropped"

A dropped idea with a clear reason is a good result. Then update your line of `BACKLOG.md` (`proposed (<run>): ...` when a proposal waits for the owner, `done (<run>): ...` when dropped, or `open` again with what was learned), and add ideas you had at the end of the list.

### Step 6. Leave the place clean

1. A test file `research/tests/test_candidate_<name>.py` for a proposed candidate: at least "the slot is `None` before the music reaches the speakers" and "values stay in range". [`research/tests/test_scoreboard_compare.py`](../../../research/tests/test_scoreboard_compare.py) shows how to run a candidate on a made-up song.
2. `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` must pass.
3. `.venv/Scripts/python.exe -m research.guard check music` must print OK, or name only files you did not touch.
4. `.venv/Scripts/python.exe -m research.inbox`, so the owner's page shows your proposal and your questions.
5. A session log in `work_history/` from [`work_history/TEMPLATE.md`](../../../work_history/TEMPLATE.md), with its row in `work_history/README.md`. Write "Commits: none (the supervisor commits)"; if you do not know your session id, write "lab agent".

## 4. Writing for the owner

The owner is not a signal-processing specialist and reads the proposal, not the code. Result first. Short sentences. Everyday words: "finds 85% of the kicks, and 79% of what it reports is a real kick", not "recall 0.85, precision 0.79". Say plainly what is **not** verified: the cost on the Raspberry Pi, truth that comes from one tool only, tracks where it is weak. Never write that something works because a score went up: nobody has seen it drive a light yet.

## 5. When to stop and ask

A doubt that touches a few seconds of one track is not a reason to stop: add a line at the end of `research/OWNER_QUESTIONS.md`, say it in the proposal, and finish the cycle. Stop the cycle, close the run as archived with the reason, and report, only when the doubt makes the result meaningless:

- the truth looks wrong on a track (say where, in seconds, and why you think so; do not correct it);
- the idea needs a locked file;
- the grading seems to punish a correct answer;
- you would need a new tool or library.

## 6. Your final report

Five lines at most before any detail: the signal, the score before and after on the open and the check tracks, gate passed or failed, proposed or dropped, and what is not verified. Then the paths of what you wrote.
