# Playground & Research Tracking System

This folder contains experimental notebooks and isolated research spikes. It also acts as a laboratory logbook and board to remember what was tried, what succeeded, and what failed. 

To keep things organized and context-rich, **each notebook must reside in its own folder** that shares the notebook's name.

## Directory Structure

```text
playground/
├── README.md                           ← this file
├── RESEARCH_BOARD.md                   ← the high-level kanban/progress board (always update this!)
├── template_research_session.md        ← template for logging a specific session
├── template_history.md                 ← template for the permanent notebook history
│
└── [Notebook_Name]/
    ├── [Notebook_Name].ipynb           ← the notebook itself
    ├── session.md                      ← active scratchpad for the current coding session
    └── history.md                      ← permanent knowledge base of past findings and mistakes
```

**Naming convention for logs:** Each notebook has its own `session.md` file located inside its dedicated folder.

---

## How it works

1. **The Board (`RESEARCH_BOARD.md`)**: This is the single source of truth for the *Final Objective*, the overall progress, and the To-Do list. 
2. **The Session (`session.md`)**: Whenever you iterate on a notebook, use this as a scratchpad to document exactly what you are trying right now.
3. **The History (`history.md`)**: After a session is done, summarize the permanent findings here (what worked, what failed, what changed) so future agents don't repeat the same mistakes.

### How to Log a Session

Prompt the agent with:
```text
I just finished experimenting in playground/[Notebook_Name]/[Notebook_Name].ipynb.
Please update the session log at playground/[Notebook_Name]/session.md.
Also, update the permanent playground/[Notebook_Name]/history.md to reflect any new failed approaches or successful changes.
Then, update playground/RESEARCH_BOARD.md to reflect the new progress.
```

## Reviewing Progress

When you need to understand the current state of a complex problem:
1. Check `RESEARCH_BOARD.md` to see the current active objective and what is left to do.
2. Read the latest `session.md` logs in the respective notebook folders to see the specific code, math, or parameters that were tested.
