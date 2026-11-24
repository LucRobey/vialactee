# P4. How research runs in both labs (first draft)

Status: DRAFT 1, 2026-11-23. Numbers marked **open** are not chosen yet.
When approved, this lands as changes to the research skills in `.agents/skills/` and as a request to amend
AXIOM-08 (an axiom changes only by your decision).

## 1. In one paragraph

Two labs, same way of working as the existing beat research: a manager picks ideas, researchers try them, a
fixed bench grades them, everything is logged, you get a short briefing. The differences from today: the
bench grades every signal and not only the beat, it grades through the real path with the 5 s look-ahead, a
separate role owns the truth, and nothing reaches the installation without you.

## 2. Roles

| Role | Does | May not |
|---|---|---|
| **You (owner)** | make a signal trusted; choose between clips; change the production analyzer; give timings by ear; approve axiom changes and thresholds | |
| **Truth keeper** | builds and corrects the source of truth, runs the offline tools, records your timings, publishes truth versions | work on the analyzer or on modes |
| **Music manager** | picks which signal and which idea to work on; approves plans; runs the held-out check; writes the briefing | write model code; change truth |
| **Music researcher** | builds one candidate analyzer change and benchmarks it on the open tracks | see held-out detail; change truth, the bench or the thresholds |
| **Choreography manager** | picks ideas; runs laws and measures; nominates candidates; prepares your clip pairs | write mode code; change measures, thresholds or the clip seed |
| **Choreography researcher** | builds one candidate mode in `research/choreography/` | touch `modes/`; change measures; see which clips you will get |

Skills: the two existing research skills are rewritten (they are written for another tool's commands and
speak only of beats). Three are added: truth keeper, choreography manager, choreography researcher. The
governance test that pins five skills is updated to eight. **Open**: one shared manager skill instead of two,
to keep the set small.

## 3. One cycle in the music lab

1. **Pick.** The manager reads the status record (P2) and picks one signal and one idea. Importance decides
   the signal: value for the show x chance to get it live.
2. **Plan.** The researcher writes what will change and what result is expected. The manager approves.
3. **Build.** One candidate, under `research/experiments/models/`. Production code is not touched.
4. **Grade on open tracks.** The bench runs the candidate inside the production `Listener` with the 5 s
   look-ahead and scores **every** signal that has truth, not only the target.
5. **Gate.** The per-signal gate (section 5). A candidate that fails is logged and archived.
6. **Held-out check.** Run by the manager. The researcher sees one number per signal, nothing else.
7. **Log.** Leaderboard, history, idea tree, status record.
8. **Propose.** If a signal now passes its graduation rule, or the candidate beats production, the manager
   writes a proposal. You decide.

## 4. One cycle in the choreography lab

1. **Pick.** The manager picks an idea: a new mode, or a new use of a signal.
2. **Plan.** The researcher states the lead driver, the signals read, and the fallback for each optional one.
3. **Build.** One candidate under `research/choreography/`.
4. **Laws.** The existing tests (layer 1 of P3).
5. **Render and measure.** Three feeds (truth, realistic, live) on open tracks; measures pass or fail.
6. **Nominate.** The manager adds passing candidates to your queue of clip pairs, on held-out passages.
7. **Your choice.** You judge the pairs when you have time. The lab does not wait: it goes on with other ideas.
8. **Log and promote.** Results are logged. A winner is promoted by a separate, normal piece of work, and stays
   provisional until you have seen it on the real installation.

## 5. Gates

| Gate | Checked by | Blocks |
|---|---|---|
| Plan approved | manager | starting to build |
| Repository tests (axioms, sealed sectors, frame budget, zero allocation) | automatic | everything |
| **Per-signal gate** | automatic | a candidate analyzer: no trusted signal may get worse by more than its noise margin (**open**), on synthetic and on real tracks |
| Held-out check | manager | a proposal to you |
| Locked files (truth, thresholds, measures, error profiles, clip seed) | automatic | any research change that edits them |
| Owner decision | you | trust, production default, promotion of a mode |

The per-signal gate replaces today's rule, which looks only at beat F1 on the synthetic tracks. With the
old rule a change could improve beats and quietly break "beat present" or the tempo.

## 6. Logs

| Log | Content |
|---|---|
| Leaderboard (music) | one line per candidate, one column per graded signal, truth version, feed used |
| Status record (music) | per signal: status, latest score, weak tracks, open proposals |
| Idea tree, history (one each per lab) | what was tried, why it failed, what is next |
| Clip verdicts (choreography) | each pair, your pick, hidden references and repeats |
| Truth change log | each truth version: what changed and why |
| `work_history/` | one log per session, as today |
| Briefing | one page for you: what moved, what is proposed, what is waiting for you |

Every score names its truth version and whether it was graded with the look-ahead. Scores from the old
bench (no look-ahead, simplified input) are kept, marked as old, and never ranked with the new ones.

## 7. What needs you, and what does not

Needs you:
- making a signal trusted, or changing any trust level
- changing the analyzer that runs on the installation
- promoting a mode
- timings by ear and "this is right / wrong" in the viewer
- thresholds, the held-out list, the list of measures
- any change to an axiom
- installing a tool whose licence is not clearly free

Does not need you: picking ideas, building candidates, running the bench, archiving failures, correcting
truth where the evidence is plain (logged; you can overrule), writing proposals.

## 8. How the two labs are kept apart

- A test fails if code under `research/choreography/` imports the music lab (`research/experiments/`,
  `research/benchmarks/`) or the inside of `music/`, and the reverse.
- Both may read `research/truth/`. Neither may write it; only the truth keeper's tools do.
- The choreography lab knows signals by their name in the contract. Which model produces them is invisible to it.
- The only things passing from the music lab to the choreography lab are the signal list and the frozen error
  profiles. The only thing passing back is a wish: "this signal would be worth a lot if it were trusted".

## 9. Request to amend AXIOM-08 (wording to be agreed)

Today the axiom says: references are immutable; promotion needs zero F1 regression on the synthetic suite and
the 3 ms budget; every candidate is logged. Proposed changes:

1. **Truth building is a separate activity.** Research may never edit a reference. Truth-building work may,
   with a new version and a logged reason. (Your ruling of 2026-11-22, written into the axiom.)
2. **The gate covers every trusted signal**, not only beat F1, and real tracks as well as synthetic ones.
3. **Grading goes through the real path**: production `Listener`, 5 s look-ahead, speaker time.
4. **A score names its truth version.**

Reason, measured on 2026-11-22: bad references reversed the ranking (production fell from first to third once
12 references were corrected), and the current bench gives the legacy analyzer 54 where the real path gives 81.

## 10. Problems of the current process this fixes, and what it does not

Fixes: grading against wrong references without noticing; a bench that does not match the installation;
tracks that crash and vanish from the average; one song treated as a trap for many cycles because of its
reference (Stayin' Alive); agents marking their own modes.

Does not fix: the truth is still mostly machine-made. Its quality grows only as fast as you label by ear.
And the choreography lab moves only as fast as you judge clips.

## 11. Decisions asked from you

1. Agree with the roles, and with a truth keeper separate from the researchers?
2. Agree with the per-signal gate replacing the beat-only gate?
3. Agree to open the AXIOM-08 amendment with the four points of section 9?
4. May the truth keeper correct plain errors without asking first (logged, reversible), or do you want to
   approve each correction?
5. Two manager skills, or one shared?
