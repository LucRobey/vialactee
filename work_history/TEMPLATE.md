# [YYYY-MM-DD] [Task Title]

> **Date:** YYYY-MM-DD  
> **Session ID:** `<session-id-or-hash>`  
> **Agent / Model:** Gemini 3.8 Flash / Claude 3.7 Sonnet / User  
> **Primary Goal:** Brief 1-line summary of what this session aimed to accomplish.  
> **Status:** [COMPLETED / IN PROGRESS / BLOCKED]

---

## 1. Context & Motivation

* Why was this work done?
* What user request, issue, or test failure triggered this session?
* Key references or past session logs consulted.

---

## 2. Changes Made

Group changes logically by component or feature:

### Component / Area 1
* **[NEW / MODIFY / DELETE]** [`path/to/file.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/path/to/file.py):
  * Detailed bullet point on what changed and why.

### Component / Area 2
* **[NEW / MODIFY / DELETE]** [`path/to/another_file.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/path/to/another_file.py):
  * Description of changes.

---

## 3. Verification & Testing

Record all verification steps executed during the session:

* **Command**: `python -m pytest -q`
  * **Result**: Passed X tests, Y skipped.
* **Frontend**: `npm run build`
  * **Result**: Vite build completed in Xms, 0 errors.
* **Hardware / Simulator Check**:
  * Did Pygame simulator run properly? Any frame drops or threading issues?

---

## 4. Architecture Decisions & Trade-offs

* **Decision 1**: Why did we choose approach X over approach Y?
* **Trade-off / Invariant**: Any side effects, backward compatibility constraints, or latency implications?

---

## 5. Pitfalls & Lessons Learned

* What went wrong or took longer than expected?
* Any subtle traps or bugs discovered that future agents should avoid?

---

## 6. Open Items & Next Steps

* [ ] Concrete task 1 for the next session.
* [ ] Concrete task 2.
