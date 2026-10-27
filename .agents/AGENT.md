# Vialactée Agent Entry Point (AGENT.md)

Vialactée is an asynchronous Python server (Raspberry Pi 4) that drives a 1,304-LED music-reactive chandelier from live audio, with a React remote (`wabb-interface/`). **This file is a pointer, not a spec.** It deliberately duplicates nothing: if a fact lives elsewhere, link to it. Do not add changelogs here (use `work_history/` and git).

## Read order

1. [`CONSTITUTION.md`](CONSTITUTION.md): the 5 non-negotiable technical laws (30 FPS / 20 ms budget, zero hot-path allocation, 500-line ratchet, wire compatibility, fast headless tests).
2. [`skills/vialactee-project/SKILL.md`](skills/vialactee-project/SKILL.md): directory map, system invariants, session and commit protocol.
3. The domain skill for your task (table below), then the matching spec in [`docs/`](../docs/README.md).

## Where is the truth?

| Question | Source of truth |
|---|---|
| Physical/mathematical laws (frame budget, allocation, geometry, network, sync, governance) | [`docs/axioms/`](../docs/axioms/README.md) (Tier 0, human RFC required to change) |
| How a subsystem works (audio, rhythm, transitions, hardware, API) | [`docs/architecture/`](../docs/architecture/system_overview.md) |
| Schemas, catalogs, contracts (config, modes, coordinates, `music.api`, `transitions.api`, `mood.api`) | [`docs/contracts/`](../docs/contracts/README.md), [`docs/reference/`](../docs/reference/configuration_schemas.md) |
| How to author or operate something | [`docs/manuals/`](../docs/manuals/mode_authoring_guide.md) |
| Why something was changed, what was tried | [`work_history/`](../work_history/README.md) + `git log` |
| What a directory contains | [`docs/README.md`](../docs/README.md) and [`docs/architecture/`](../docs/architecture/system_overview.md) |
| Current rhythm-research SOTA | `research/experiments/LEADERBOARD.md` |
| Historical snapshots (never system truth) | [`docs/archive/`](../docs/archive/), `.agents/reviews/` |

## Domain skills

| Task | Skill |
|---|---|
| Orchestration, cross-domain work, onboarding | `vialactee-project` |
| Visual modes (`modes/`) | `vialactee-mode-creator` |
| Audio ingestion, beat tracking, Oracle flywheel | `vialactee-dsp-engine` |
| Offline MIR experiments in `research/` | `vialactee-researcher` (worker), `vialactee-research-manager` (director) |

## Session checklist

1. `git status` and `git log --oneline -n 10`. If the tree holds work that is not yours, tell the user before touching it.
2. Make the change; respect the sealed rooms (`music/` via `music.api`, `transitions/` via `transitions.api`, `mood/` via `mood.api`).
3. `python -m pytest -q` (governance tests in `tests/governance/` enforce the axioms).
4. Write the `work_history/` log, then commit per logical step (Conventional Commits) as described in the project skill.

> Previous long-form version of this file: [`docs/archive/AGENT_context_snapshot_2026-10-14.md`](../docs/archive/AGENT_context_snapshot_2026-10-14.md).
