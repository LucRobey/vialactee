"""
tools/build_coherence_helper.py - Authoritative check for coherence policies.

The editor itself (tools/coherence_helper.html) is standalone: open it in Chrome/Edge and pick config/.
This script runs the real `transitions.policy.compile_policy` (incl. the feasibility probe).

Usage (from the repo root):
    python -m tools.build_coherence_helper --check full    # check config/coherence_full.json
    python -m tools.build_coherence_helper --check small path/to/other_policy.json
"""

import argparse
import json
import os
import sys
import warnings
from typing import Any, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(REPO_ROOT, "config")
PROFILES = ("full", "small")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_segments(profile: str) -> List[Dict[str, Any]]:
    """Flatten every `segs_*` block of segments_<profile>.json into [{id, orientation, tags}]."""
    raw = _read_json(os.path.join(CONFIG_DIR, f"segments_{profile}.json"))
    out: List[Dict[str, Any]] = []
    for key, block in raw.items():
        if key.startswith("segs") and isinstance(block, list):
            for seg in block:
                out.append({
                    "id": str(seg["id"]),
                    "orientation": str(seg.get("orientation", "vertical")),
                    "tags": [str(t) for t in seg.get("tags", [])],
                })
    return out


def check(profile: str, policy_path: str = "") -> bool:
    """Run the authoritative compile_policy (incl. feasibility probe) on a policy file."""
    sys.path.insert(0, REPO_ROOT)
    from transitions.api import ModeProfile, PolicyError, SegmentDescriptor
    from transitions.policy import compile_policy

    path = policy_path or os.path.join(CONFIG_DIR, f"coherence_{profile}.json")
    policy = _read_json(path)
    segments = tuple(SegmentDescriptor(name=f"Segment {s['id']}", orientation=s["orientation"], id=s["id"], tags=tuple(s["tags"]))
                     for s in load_segments(profile))
    modes_raw = _read_json(os.path.join(CONFIG_DIR, "modes.json"))
    modes = tuple(
        ModeProfile(m["name"], tuple(float(m["dna"][k]) for k in ("energy", "punch", "rhythm", "complexity")), tuple(m.get("tags", [])))
        for m in modes_raw.get("standard_modes", [])
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile_policy(policy, segments, modes)
        except PolicyError as exc:
            print(f"ERROR: {exc}")
            return False
    for w in caught:
        print(f"WARNING: {w.message}")
    print(f"OK: {os.path.relpath(path, REPO_ROOT)} compiles for profile '{profile}'")
    return True


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", nargs="+", metavar=("PROFILE", "FILE"), help="validate a policy with transitions.policy.compile_policy")
    args = ap.parse_args(argv)
    if not args.check:
        ap.error("--check PROFILE [FILE] is required (the HTML editor is standalone, no build step)")
    return 0 if check(args.check[0], args.check[1] if len(args.check) > 1 else "") else 1


if __name__ == "__main__":
    sys.exit(main())
