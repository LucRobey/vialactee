# Agent Closing Protocol for Research

When a user asks you to execute this closing protocol (e.g., "refer to close_agent.md"), you MUST perform the following steps to properly document and save the findings of the current research session.

You are expected to extract the findings, code changes, and insights from the current session and distribute them across the tracking files.

## Step 1: Update Current Objectives
Update `playground/[folder]/current_objectives.md`:
- Update "Current Progress" with what was achieved in this specific run.
- Update "What we are doing right now" if the immediate task has shifted.
- Update the "Next Steps" To-Do list.

## Step 2: Update the Comprehensive Memory (History)
Update `playground/[folder]/history.md`:
- Log **absolutely everything** you tried (code snippets, parameters, methods).
- Log all results, metrics, crashes, and bugs (even minor ones) to maintain a full trace.
- Update the "Permanent Findings" section with any new stable states or failed approaches.

## Step 3: Check the Global Objective
Check `playground/[folder]/session.md`:
- Only update this file if the overarching global objective or final vision has fundamentally shifted based on the session's findings.

## Step 4: Update the Global Board
Update `playground/RESEARCH_BOARD.md`:
- Update the progress of the current objective.
- Check off any completed tasks in the To-Do list.
- If the Final Objective has shifted or a new major blocker was discovered, log it here.

## Step 5: Final Confirmation
Once all files have been successfully updated, reply to the user confirming that the session has been securely logged and the agent is ready to be closed. Provide a very brief 1-2 sentence summary of the core finding that was saved.
