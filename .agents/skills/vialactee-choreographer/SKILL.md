---
name: vialactee-choreographer
description: Step-by-step procedure for an agent working alone in the choreography lab (research/choreography). Use when asked to run a cycle of the choreography lab, to invent or improve a light show as a lab mode, or to work on a line of the choreography work list.
---

# Choreography lab: one cycle, alone

You invent one light show for the installation (1,304 LEDs, 11 segments), as a **lab mode**. There is no right answer to grade against: a gate removes what clearly fails, and then **the owner chooses by eye**. Only the owner's choice makes a mode better than another. You never touch the modes that run on the installation.

One launch = one cycle = one line of the work list = one new mode. Then you stop and report.

`PY` below stands for `research/analyzer_trials/.venv/Scripts/python.exe`. Run everything from the repository root. Tests use the project environment: `.venv/Scripts/python.exe -m pytest -q`.

---

## 1. Before anything

1. `git status`, then `.venv/Scripts/python.exe -m research.guard snapshot choreography`.
2. Read [`research/choreography/BACKLOG.md`](../../../research/choreography/BACKLOG.md): what the owner likes, what the installation can hear today, and the work list. Read [`research/choreography/STATUS.md`](../../../research/choreography/STATUS.md): every lab mode, its gate, the owner's choices.
3. Take the first line whose state is `open`, unless the launch message names one.
4. Read [`research/choreography/README.md`](../../../research/choreography/README.md) once: the feeds, how an agent "sees" a mode, the gate's five rules.

## 2. What you may change

| You may | You may not |
|---|---|
| add a mode in `research/choreography/candidates/` | touch `modes/`, `music/`, `core/`, `config/`, `docs/`, `tests/` |
| update your line of `BACKLOG.md` | edit the gate, the measures or the profile (`research/choreography/*.py`) |
| let the tools write `gates.json`, `queue.json`, `STATUS.md` | write `verdicts.jsonl` (the owner's word), or change a gate limit |
| add `research/tests/test_choreography_candidate_<name>.py` | edit another lab mode in place: copy it under a new name |
| keep your own scripts and notes in `research/choreography/runs/<Mode_name>/` | leave scripts that matter outside the repository |
| add a session log in `work_history/`, a question in `research/OWNER_QUESTIONS.md` | commit or push, unless the launch message says so |

`.venv/Scripts/python.exe -m research.guard check choreography` tells you if you stepped outside. Someone else may be working in the repository at the same time: a file the guard names that you did not touch is not yours to undo, name it in your report.

## 3. The cycle

### Step 1. Write the mode

One file, `research/choreography/candidates/<Mode_name>.py`, file name = class name. [`candidates/Kick_bands_mode.py`](../../../research/choreography/candidates/Kick_bands_mode.py) is the working example: copy its shape (constructor, `run()`, how it reads signals with a fallback). Mark your line of `BACKLOG.md` as `taken (<Mode_name>)`. To improve an existing lab mode, copy it under a new name so both can be compared.

Rules:

- **Say the idea in one sentence** at the top of the file. If you cannot, the mode is not ready.
- **Read signals from `listener.signals`** (the list is `config/music_signals.json`), and give **a fallback for every one**: a slot can be `None` on the installation. A mode that only works on perfect signals is worth nothing.
- **Fast.** The installation draws 30 frames a second on a Raspberry Pi. Create arrays in the constructor; no new array in `run()`; NumPy on whole segments, no loop over LEDs. Only the speed rules of [`vialactee-mode-creator`](../vialactee-mode-creator/SKILL.md) apply to a lab mode: no registration, no settings schema, no catalog entry.
- **Safe by construction.** Never more than three flashes in any one second. The gate only tries three passages, none faster than about 128 beats a minute, so passing it does not prove safety: build the limit into the mode (a minimum time between two full flashes), and try it on made-up fast hits. A punch can also be a quick rise in brightness without going through dark.
- **Brightness is what the eye sees.** A tenth of the value already looks a third as bright. A "small" resting light eats the punch.

### Step 2. Look at what it does

    PY -m research.choreography.check_mode <Mode_name>

About two minutes. It draws the mode on three standard passages and on every feed, profiles it and applies the gate. Then **look**, you cannot watch a clip but you can read:

- `research/choreography/output/gates/<Mode_name>/GATE.md`: the five rules, pass or fail, with numbers;
- `research/choreography/output/profiles/<clip>/PROFILE.md`: what the light does, in numbers and in sentences, version by version;
- the pictures next to it. Open them. The time strip (time left to right, LEDs top to bottom, the true hits marked above) shows in one look whether the flashes fall on the kicks, whether a break is calm, whether anything travels.

Compare what you see with the sentence at the top of your file. If the mode does not do what the sentence says, fix the mode, not the sentence.

### Step 3. Improve, and pass the gate

Change the mode and run the gate again (`--reuse` is only for an unchanged mode). One round = one gate run on changed code. The five rules: it runs on every feed; it works on today's analyzer; flash safety; it follows the music (it must come out clearly worse when every hit is moved half a beat late); cost. **Never change a limit to make a mode pass.** If you believe a limit is wrong, say so in your report and in `research/OWNER_QUESTIONS.md`.

Passing the gate does not mean the mode is good. Before nominating, check the profile against what the owner likes: is the kick visible at once (`half_rise_ms` under 45, a clear contrast as the eye sees it)? Are bass and treble readable apart? Is a break calmer than a chorus? Does it still do something on the "today" feed?

Stop when the gate passes and the profile matches your sentence, or after six rounds. If the idea does not work, drop it and say why.

### Step 4. Put it in front of the owner

    PY -m research.choreography.nominate <Mode_name> --note "what to look at, in one line"
    PY -m research.choreography.nominate <Mode_name> --against <Other_mode> --note "..."

Without `--against` the owner compares your mode on perfect signals and on today's analyzer. With `--against` the owner compares your mode with another one, a lab mode or a mode of the installation, both hearing the same thing (`--feed today` by default). The tool refuses a mode that has not passed its gate, and refuses `--against` a lab mode that failed its own: the owner is not shown a mode that breaks the flash limit. Compare with a mode that passed, or with a mode of the installation. One nomination puts three clips in the queue (the three standard passages), and one nomination per cycle is enough: the owner's time is the scarce thing.

The owner chooses when they have time. **Do not wait**: finish and report.

### Step 5. Leave the place clean

1. A test file `research/tests/test_choreography_candidate_<name>.py` for a nominated mode: at least "it draws with every signal empty" and your flash limit on made-up fast hits.
2. `PY -m research.choreography.status` (rewrites `STATUS.md`) and `.venv/Scripts/python.exe -m research.inbox` (the owner's page).
3. Update your line of `BACKLOG.md` (if your mode also covered part of another line, say so in the result); add ideas you had at the end.
4. `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` must pass.
5. `.venv/Scripts/python.exe -m research.guard check choreography` must print OK, or name only files you did not touch.
6. A session log in `work_history/` from [`work_history/TEMPLATE.md`](../../../work_history/TEMPLATE.md), with its row in `work_history/README.md`. Write "Commits: none (the supervisor commits)"; if you do not know your session id, write "lab agent".

## 4. What the first cycle learned the hard way

- **What counts as a flash.** `profile.py` looks at the average light of the whole installation and of each third of its height. A flash is a swing of 10% of full light up and back; three in one second is the limit. A change kept under that size is not a flash.
- **Two brightness scales.** The flash rule weighs colours as light (a saturated blue at full drive is about 7%), while "brightness as the eye sees it" in the profile uses the strongest colour channel (the same blue is 100%). Check which one a number uses before designing around it.
- **Hits of one musical moment are not on the same frame.** A drop lands a frame or two after its kick in the truth feed. Do not merge "same-frame" hits into one event.
- **The profile cannot see a small local pulse.** Every number is an average over the installation or a third of it. To know whether a small detail draws anything, print the frames yourself.
- **Your own scripts** run from the repository root with `PYTHONPATH=.` so they can import `modes` and `research`. Keep the ones that support a claim in `research/choreography/runs/<Mode_name>/`.

## 4b. What you must not claim

You have not seen the show. The profile says what the light does, never whether it is beautiful. Write "the kick lights the lower third in 30 ms, on 95% of the kicks", not "the kick looks great". The lab draws on a screen: brightness, colour and the room differ on the real installation.

## 5. When to stop and ask

A trade-off only the owner's eye can judge ("is a soft pulse on every other kick acceptable?"), or a hole you found in the gate, goes at the end of `research/OWNER_QUESTIONS.md` in plain words; then finish the cycle. Stop the cycle and report when the idea needs a signal the installation does not have and no fallback makes sense, when a gate rule seems to punish a good show, or when the work needs a locked file.

## 6. Your final report

Five lines at most before any detail: the idea in one sentence, the gate result, what the profile says about the kick, the bands and the breaks, whether it is nominated (and against what), and what is not verified. Then the paths of what you wrote.
