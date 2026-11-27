"""The guard of the research labs: did a lab agent stay inside what its role may change?

    python -m research.guard snapshot music           before starting: remember what is already changed
    python -m research.guard check music              at the end: every new change must be allowed for the role
    python -m research.guard check choreography

Works on the files git sees as changed, added or deleted (committed work is not looked at: a lab agent does not
commit). `snapshot <lab>` writes the list of paths that are already dirty to .git/lab_guard_<lab>.json, so that
the owner's own unfinished changes are not blamed on the agent. Each lab has its own snapshot, so an agent in
one lab does not erase the other's. `check` exits 1 and names every path outside the role.

What a role may change is the table below. Everything else is locked for it: the production code (music/,
modes/, core/, config/), the source of truth, the grading tools, the measures, the owner's verdicts, the
tests that keep the rules, and the other lab.
"""
from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO = Path(__file__).resolve().parents[1]


def mark(role: str) -> Path:
    return REPO / ".git" / f"lab_guard_{role}.json"

# Patterns are matched with fnmatch on the path from the repository root ('*' also crosses folders).
SHARED: Tuple[str, ...] = ("work_history/*", "research/INBOX.md", "research/OWNER_QUESTIONS.md")
ALLOWED: Dict[str, Tuple[str, ...]] = {
    "music": SHARED + (
        "research/experiments/models/*.py",            # candidates
        "research/scoreboard/runs/*",                  # the run folder: plan, scores, tuning scripts, proposal
        "research/scoreboard/BACKLOG.md",              # mark an idea as taken or done
        "research/scoreboard/STATUS.md",               # rebuilt by the cycle tool
        "research/tests/test_candidate_*.py",          # tests of a candidate
    ),
    "choreography": SHARED + (
        "research/choreography/candidates/*.py",       # lab modes
        "research/choreography/runs/*",                # an agent's own scripts and notes, one folder per mode
        "research/choreography/BACKLOG.md",
        "research/choreography/STATUS.md",             # rebuilt by the status tool
        "research/choreography/gates.json",            # written by the gate
        "research/choreography/queue.json",            # written by nominate
        "research/tests/test_choreography_candidate_*.py",
    ),
}
# Named in the report so the agent knows why, and never allowed whatever the role.
LOCKED_REASON: Tuple[Tuple[str, str], ...] = (
    ("music/*", "the production analyzer: only the owner's approval changes it, as a separate piece of work"),
    ("modes/*", "the modes of the installation: a lab mode lives in research/choreography/candidates/"),
    ("core/*", "the main loop of the installation"),
    ("config/*", "the configuration and the signal contract"),
    ("research/truth/*", "the source of truth: research never edits it"),
    ("research/scoreboard/split.json", "the open / check split: the owner's decision"),
    ("research/scoreboard/*.py", "the grading tools: a candidate may not change how it is graded"),
    ("research/choreography/verdicts.jsonl", "the owner's choices: only the clip page writes them"),
    ("research/choreography/*.py", "the measures and the gate: a mode may not change how it is judged"),
    ("tests/*", "the tests that keep the rules"),
    ("docs/*", "the contracts"),
    (".agents/*", "the agents' own instructions"),
)


def changed_paths() -> List[str]:
    """Every path git sees as modified, added, deleted or untracked, from the repository root."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    paths = []
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return sorted(set(paths))


OTHER_LAB = "the other lab's own files: fine if another agent is working there now, a fault if you changed them"


def judge(paths: List[str], role: str, already: List[str] = ()) -> List[Tuple[str, str]]:
    """The paths the role may not change, each with the reason."""
    allowed = ALLOWED[role]
    others = [pat for r, pats in ALLOWED.items() if r != role for pat in pats]
    bad = []
    for p in paths:
        if p in already or any(fnmatch.fnmatch(p, pat) for pat in allowed):
            continue
        if any(fnmatch.fnmatch(p, pat) for pat in others):
            bad.append((p, OTHER_LAB))
            continue
        reason = next((why for pat, why in LOCKED_REASON if fnmatch.fnmatch(p, pat)), "outside what this role may change")
        bad.append((p, reason))
    return bad


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "snapshot" and sys.argv[2] in ALLOWED:
        paths = changed_paths()
        mark(sys.argv[2]).write_text(json.dumps(paths), encoding="utf-8")
        print(f"guard: {len(paths)} path(s) already changed before the work started; they will not be counted")
        return
    if len(sys.argv) == 3 and sys.argv[1] == "check" and sys.argv[2] in ALLOWED:
        already = json.loads(mark(sys.argv[2]).read_text(encoding="utf-8")) if mark(sys.argv[2]).exists() else []
        found = judge(changed_paths(), sys.argv[2], already)
        bad = [b for b in found if b[1] != OTHER_LAB]
        for path, why in found:
            if why == OTHER_LAB:
                print(f"guard: note, {path} changed: {why}")
        if not bad:
            print(f"guard: OK, every change is inside what the {sys.argv[2]} lab may change")
            return
        print(f"guard: {len(bad)} change(s) outside what the {sys.argv[2]} lab may change. Undo the ones you made; "
              f"name in your report the ones you did not make (someone else may be working in the repository):")
        for path, why in bad:
            print(f"  {path}\n      {why}")
        sys.exit(1)
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
