# The four papers (first draft, 2026-11-23)

Plan chapter 2. Drafts kept here, outside `docs/`, until approved. Thresholds are left open on purpose:
they are set after the thin slice (chapter 3) and the first truth-quality measurements.

| Paper | Question it answers | Lands as |
|---|---|---|
| [P1 Source of truth](P1_source_of_truth.md) | What do we know about each song, and how sure are we? | replaces `research/benchmarks/source_of_truth.md` |
| [P2 Analyzer contract](P2_analyzer_contract.md) | Which signals exist, and how does one become trusted? | amendment to `docs/contracts/music_analyzer_contract.md` |
| [P3 Choreography contract](P3_choreography_contract.md) | What may a mode read, and how is a show graded? | amendment to `mode_contract.md` and `global_mode_contract.md` |
| [P4 How research runs](P4_how_research_runs.md) | Who does what, in which order, and what needs the owner? | research skills, AXIOM-08 amendment |

Read in this order. Each paper ends with the decisions asked from the owner.

## The decisions that shape everything else

1. **What may grade the analyzer** (P1 section 2): human labels and agreement of two tools, never one tool alone.
2. **Only the owner makes a signal trusted** and **only the owner's choice promotes a mode** (P2, P3).
3. **Half and double tempo count as wrong** (P2 section 10).
4. **Measures only filter** in the choreography lab; they are never maximised (P3 section 5).
5. **The per-signal gate and the real-path bench** replace the beat-only gate (P4 sections 5 and 9).
6. **Your time**: ear time per track (P1) and clip pairs per week (P3) set the speed of both labs.

## Not verified in these drafts

- Tool licences (P1 section 7) are written from memory.
- The importance ranking of signals is a judgement, not a measurement.
- "Live today" scores in P2 are graded against machine-made truth.
- Folder and file names for things that do not exist yet (`research/truth/`, `research/choreography/`,
  `config/music_signals.json`) are proposals.
