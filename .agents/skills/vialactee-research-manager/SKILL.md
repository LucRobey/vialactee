---
name: vialactee-research-manager
description: How to supervise the two research labs for the owner - launch lab agents, check what they report, record the owner's decisions, promote an approved result, keep the work lists and the owner's inbox. Use when the owner asks where the labs stand, answers a proposal, or asks to launch, review or promote lab work.
---

# Supervising the two labs

Two labs improve the installation without touching it:

- the **music lab** makes the live analyzer approach the source of truth, signal by signal ([`vialactee-researcher`](../vialactee-researcher/SKILL.md));
- the **choreography lab** invents light shows, judged by the owner's eye ([`vialactee-choreographer`](../vialactee-choreographer/SKILL.md)).

They never import each other (`tests/governance/test_lab_isolation.py`). They meet through one list of signals, [`config/music_signals.json`](../../../config/music_signals.json).

You supervise. You do not write candidates or modes in this role, and **nothing reaches the installation without the owner's yes**.

`PY` stands for `research/analyzer_trials/.venv/Scripts/python.exe`; run from the repository root.

---

## 1. Where things stand

| Read | It tells you |
|---|---|
| [`research/INBOX.md`](../../../research/INBOX.md) | what is waiting for the owner: proposals, clips, standing questions |
| [`research/scoreboard/STATUS.md`](../../../research/scoreboard/STATUS.md) | every signal: empty, copied, produced; its score; every run |
| [`research/choreography/STATUS.md`](../../../research/choreography/STATUS.md) | every lab mode: its gate, its nominations, the owner's choices |
| the two `BACKLOG.md` | what is next in each lab |

Rebuild them at any time: `python -m research.inbox`, `PY -m research.scoreboard.status`, `PY -m research.choreography.status`.

When the owner asks "where are we": answer from these four, result first, in plain words.

## 2. Launching a cycle

A lab agent does one cycle and stops. In Claude Code the owner types `/music-cycle` or `/light-cycle` in a new session (project skills in `.claude/skills/`); any other agent is told: "Follow `.agents/skills/vialactee-researcher/SKILL.md` (or `vialactee-choreographer`) and run one cycle", optionally naming a line of the work list.

- **One agent per lab at a time.** They work in the same folder; two agents in one lab would overwrite each other. One in each lab at once is fine: they touch different folders.
- Lab agents do not commit. You do, after checking (section 3).
- A cycle of the music lab costs a few minutes of computer time per grade; a gate of the choreography lab about two minutes.

## 3. When an agent reports

Do not take the report as proof. Check, then commit.

1. `python -m research.guard check music` (or `choreography`): every change inside what the lab allows.
2. `.venv/Scripts/python.exe -m pytest -q`: everything passes.
3. Music: read `runs/<run>/OPEN.md` and `CHECK.md`. The score on the check tracks should be close to the open tracks; the gate must have passed; the run should have been checked once. Read `PROPOSAL.md` as the owner would: plain words, and what is not verified is said.
4. Choreography: read `output/gates/<Mode>/GATE.md` and one `PROFILE.md` with its pictures. Does the mode do what its first sentence says?
5. Commit the lab's files with a conventional message (`feat(research): ...`), one commit per cycle. Never `git add -A`; leave the owner's own changes out. Push only when the owner asks.
6. Tell the owner in a few lines what is new in the inbox.

## 4. The owner's answers

- **A music proposal**: `PY -m research.scoreboard.cycle decide <run> --decision approved|refused --note "..."`, only on the owner's own words in the conversation. Then promote (section 5) if approved.
- **Clips**: the owner chooses on the clip page (`choreography-clips` in `.claude/launch.json`, port 8768). The page writes `verdicts.jsonl` and refreshes the status and the inbox. Never write a verdict yourself.
- **A standing question** answered: remove its line from `research/OWNER_QUESTIONS.md` and write the answer where it belongs (the split file, a gate limit, a paper).

## 5. Promoting an approved music result

A separate, small piece of work, done by you, never by the lab agent. The promotion of 2026-11-27 is the model ([log](../../../work_history/2026-11-27_band_and_kick_signals_promoted.md)):

1. Move the candidate's logic into a helper file in `music/` (under 500 lines, AXIOM-07) called by the production analyzer; change nothing else it computes.
2. Update the list in its four places: `MusicSignals.PRODUCED` (or `BRIDGED`), `config/music_signals.json`, section 6 of [`docs/contracts/music_analyzer_contract.md`](../../../docs/contracts/music_analyzer_contract.md), and the governance test.
3. Copy the candidate's file into its run folder as `candidate_as_graded.py` (lab agents do not commit, so it may exist nowhere else), then turn the candidate into an empty subclass of the production model, so past runs still open.
4. Prove nothing moved: `PY -m research.scoreboard.scoreboard`, then compare with the run's scores; they must be identical for the promoted signals and unchanged for the others.
5. A memory test of the new per-tick code (AXIOM-02), and when the beat or the tempo is touched, the synthetic suite of [AXIOM-08](../../../docs/axioms/AXIOM-08_RESEARCH_REGRESSION.md): `python -m research.benchmarks.run_benchmark --model <Name> --suite synthetic`.
6. Full tests, a session log, and say what is still unmeasured (the Raspberry Pi).

## 6. Promoting a mode the owner chose

Also separate work, under [`vialactee-mode-creator`](../vialactee-mode-creator/SKILL.md): the mode moves from `research/choreography/candidates/` to `modes/` with its registration and tests. Two conditions: every signal it needs exists on the installation (or its fallback is what the owner saw), and it stays "provisional" until the owner has seen it on the real installation. The lab draws on a screen.

## 7. What only the owner decides

Which tracks are kept aside (`research/scoreboard/split.json`), the gate limits of both labs, any change to the truth, any trust level of a signal, any change to `music/`, `modes/`, `core/`, and any axiom. Research never edits the truth; correcting it is separate truth-building work (`research/truth/`), on the owner's ruling.

## 8. Keeping the lists useful

- A work list line should be doable in one cycle and say where to look. Split a line that is too big; move a line to "Blocked" with the reason when a cycle shows it cannot be done yet.
- When a lab agent stops on a locked file or a doubt about the truth, that goes to `research/OWNER_QUESTIONS.md` in plain words, with what would be unlocked.
- When the choreography lab wishes a signal existed ("this would be worth a lot if it were reliable"), add or raise the matching line in the music work list. That wish is the only thing that passes from one lab to the other.
