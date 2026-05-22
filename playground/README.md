# Playground & Research Tracking System

This folder contains experimental notebooks and isolated research spikes. It also acts as a laboratory logbook and board to remember what was tried, what succeeded, and what failed. 

To keep things organized and context-rich, **each notebook must reside in its own folder** that shares the notebook's name.

## Directory Structure

```text
playground/
├── README.md                           ← this file
├── RESEARCH_BOARD.md                   ← the high-level kanban/progress board (always update this!)
├── template_research_session.md        ← template for logging the global objective
├── template_history.md                 ← template for the permanent notebook history & comprehensive memory
├── template_current_objectives.md      ← template for the active progress and what the agent is currently doing
│
└── [Notebook_Name]/
    ├── [Notebook_Name].ipynb           ← the notebook itself
    ├── session.md                      ← represents the global objective of this notebook
    ├── history.md                      ← comprehensive memory, keeps track of absolutely everything (results, bugs, etc.) to revert if needed
    └── current_objectives.md           ← current progresses and immediate tasks (what we are doing right now)
```

**Naming convention for logs:** Each notebook has its own `session.md`, `history.md`, and `current_objectives.md` located inside its dedicated folder.

---

## How it works

1. **The Board (`RESEARCH_BOARD.md`)**: This is the single source of truth for the *Final Objective*, the overall progress, and the To-Do list. 
2. **The Session (`session.md`)**: This represents the overarching global objective of the specific research notebook.
3. **The History (`history.md`)**: A detailed memory bank. Keep track of absolutely everything here (what worked, what failed, parameters, results, bugs) so we can go back if something goes wrong.
4. **Current Objectives (`current_objectives.md`)**: This file represents the current progresses and the specific tasks the agent is actively doing right now. It makes it easier to initiate a new agent.

### How to Log a Session

Prompt the agent with:
```text
I just finished experimenting in playground/[Notebook_Name]/[Notebook_Name].ipynb.
Please update playground/[Notebook_Name]/current_objectives.md with what was completed and what to do next.
Also, update the comprehensive memory in playground/[Notebook_Name]/history.md with all detailed findings, results, and observations.
Only update playground/[Notebook_Name]/session.md if the global objective has shifted.
Then, update playground/RESEARCH_BOARD.md to reflect the new progress.
```

## Reviewing Progress

When you need to understand the current state of a complex problem:
1. Check `RESEARCH_BOARD.md` to see the current active objective and what is left to do.
2. Read the latest `current_objectives.md` to see what is currently being worked on.
3. Dive into the `history.md` logs in the respective notebook folders to see the specific code, math, or parameters that were tested previously.
