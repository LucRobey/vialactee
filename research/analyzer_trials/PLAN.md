# Two research labs: general plan (DRAFT 2, after independent critique)

## Goal
Two fields that agents can improve on their own, the way `research/` already improves beat tracking:

- **Music lab**: make the real-time analyzer approach a source of truth, signal by signal.
- **Choreography lab**: make the light show better, fed by music signals, graded without a ground truth.

The two never import each other. They meet only through a contract: one list of music signals.

## What the owner reviews: four papers
Drafted outside `docs/` first (the docs parity test fails on paths that do not exist yet), then landed as
amendments to the documents that already cover each subject.

| Paper | Content | Lands as |
|---|---|---|
| **P1. Source of truth** | Every variable we could want, the offline tool for each, how its quality is checked, state today. Also: truth versions, a held-out set of tracks, tool licences. | replaces `research/benchmarks/source_of_truth.md` |
| **P2. Analyzer contract** | Signal list: meaning, range, timing (speaker time, or up to 5 s ahead of it), status, and the *rule* for graduating. Numbers come later, once truth quality is measured. | amendment to `music_analyzer_contract.md` |
| **P3. Choreography contract** | What a mode may read (required, optional, fallback), where lab-only modes live, and grading: laws, measures used as pass/fail filters, the owner's choice. States how it relates to the existing 48/60 rubric. Also: the error model and real-wall validation. | amendment to `mode_contract.md` and `global_mode_contract.md` |
| **P4. How research runs** | Roles, one cycle step by step, gates, logs, what needs the owner, how independence is enforced, the per-signal regression gate. | amendment to the research skills and AXIOM-08 (owner RFC) |

## Chapters

**0. Owner decisions.** Settled: AXIOM-08's ban on modifying ground truth applies to normal research work, not to
this work, whose purpose is to build the ground truth (owner ruling, 2026-11-22). Also settled the same day:
the signal list is a data file outside `music/` with its status record in `research/`; new agent skills may be
added (the governance test that pins the current five is updated with them); the audio input stays as it is
today (music played through the system, 5 s look-ahead), so the contract is written for that case only and the
room-microphone case is out of scope.

**1. Corrected truth and full re-score.** Fix the audio loader, replace the bad references (the old ones remain
in git history), re-score every model in `research/experiments/models/`, not only the champion. This shows how
much of the research history rests on bad references.

**2. Four papers, first draft.** Everything that can be written without measurements. Thresholds stay open.
First draft written 2026-11-23 in `papers/` (index and owner decisions in `papers/README.md`); not yet read by the owner.

**3. Thin slice.** Replay truth into the existing `tools/choreography_probe.py`: one hand-labelled track, a few
signals, one clip of the wall, the owner looks. Add the test that forbids the two labs importing each other.

**4. Papers final.** Updated from what the slice showed, approved, landed as amendments.

**5. Truth factory.** `research/truth/`: per-track truth files, builders, viewer, hand labels. The 20 tracks
first; the rest of the library later.

**6. Music lab.** Rewrite the evaluator to run through `Listener` with the 5 s look-ahead the installation
really has, and re-baseline (today it measures only the no-look-ahead case). Score one new signal end to end, then the others.

**7. Choreography lab.** Renderer, clips, measures, candidate modes kept under `research/choreography/`.

**8. Roles, automation, pilot cycles.** Only after 6 and 7 work by hand.

## What changed after the critique
- Chapter 0 was "clean the base". The critic flagged that AXIOM-08 forbids modifying references. The owner ruled
  that the axiom covers normal research, not truth building, so the references are corrected in place. The
  re-score now covers all models.
- The signal list no longer sits inside `music/` with a status set by the benchmark. The existing contract says
  trust is edited by a human in one place. Now: definitions in a data file outside `music/`, a status ledger in
  `research/` that the benchmark *proposes* changes to, and "live trusted" only by the owner editing the contract.
- The critic raised that a room microphone has no look-ahead. The owner confirmed the input does not change, so
  only today's case (5 s look-ahead) is covered.
- Choreography grading was circular (truth goes in, sync is scored against the same truth, so copying kicks to
  brightness wins). Now: error profiles are measured from the live analyzer and frozen, clips come from seeded
  windows on held-out tracks, laws and measures are locked against edits, measures only pass or fail, pairs
  include a hidden reference and repeats, and agents nominate while only the owner's choice promotes.
- The registry is not the only coupling: a mode reading a new signal also touches the mute proxy, the synthetic
  listener and the protocols in `music/api.py`. Required signals are derived by the existing code scan.
- The thin slice moved before the papers are final, and the isolation test moved to the start.
- Postponed: automatic graduation, the rest of the library, song-scale grading, the pairwise page.

## Kept despite the critique
- The full list of wanted signals is written now (owner's explicit request); only signals with truth are fully defined.
- Four separate papers for the owner to read, even though each lands as an amendment.

## Parked ideas (owner will think about them later)
- **Music straight to light, learned from human lighting engineers** (noted 2026-11-23). Models such as Skip-BART
  (ICLR 2026, https://github.com/RS2002/Skip-BART, dataset RPMC-L2), SeqLight (several lights,
  https://arxiv.org/abs/2605.03660) and AuraLuxMuse (https://arxiv.org/abs/2610.11792) output colour and
  intensity from audio. Possible use: a reference of "what a human engineer would have done" for the
  choreography lab, not a truth variable. Limits: the public data is rock, punk and metal concerts, while the
  owner wants techno covered; nothing was installed or tried.

## Owner requirement added 2026-11-23
- The truth and the tools must work for **techno**, not only rock. Most trained tools found so far learned on
  acoustic drum kits and pop / rock songs. Each tool is to be tried on techno tracks before it is adopted.

## Not confirmed
- Whether the champion's gain depends on the bad references (two of its ten benchmark tracks, Nightcall and
  Pumped Up Kicks, have references at double tempo). Chapter 1 settles it.
- Whether the trained drum model and the section labeller install on this machine.
