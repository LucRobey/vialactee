# Agent Closing Protocol for Research

When a user asks you to execute this closing protocol (e.g., "refer to close_agent.md"), you MUST perform the following steps to properly document and save the findings of the current research session.

You are expected to extract the findings, code changes, and insights from the current session and distribute them across three tracking files.

## Step 1: Update the Session Log
Update `playground/[folder]/session.md`:
- Summarize exactly what was tried during this session (methods, parameter tweaks).
- Document the results and observations (what crashed, what improved).
- Log any strategy changes or thoughts.
- Update the "Next Steps" checklist based on what is left to do.

## Step 2: Update the Permanent History
Update `playground/[folder]/history.md`:
- Distill the session down to its permanent lessons.
- Add any newly discovered "failed approaches" to the "What was tested (and didn't work)" section so future agents don't repeat the mistake.
- If a new stable state was reached, update the "What is currently working" section.
- Summarize any major architectural or mathematical changes.

## Step 3: Update the Global Board
Update `playground/RESEARCH_BOARD.md`:
- Update the progress of the current objective.
- Check off any completed tasks in the To-Do list.
- If the Final Objective has shifted or a new major blocker was discovered, log it here.

## Step 4: Final Confirmation
Once all three files have been successfully updated, reply to the user confirming that the session has been securely logged and the agent is ready to be closed. Provide a very brief 1-2 sentence summary of the core finding that was saved.
