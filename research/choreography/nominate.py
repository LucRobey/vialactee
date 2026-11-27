"""Nominate a mode: put clips of it in the owner's queue.

Only a mode whose latest gate passed (check_mode.py) on its current code can be nominated. Nominating builds one
clip per standard passage and appends one entry per clip to queue.json (committed, small, no audio):

    without --against    the feeds of the mode side by side (truth, candidate analyzer, today's analyzer)
    with --against B     the mode against mode B, both hearing the same feed (default: today's analyzer)

An entry is "waiting" exactly when no line of verdicts.jsonl names its clip. Every nomination gets fresh clip ids
(they end in _n1, _n2...), so a mode can be nominated again after the owner has judged an earlier version.

Clips hold audio and are not committed. After a fresh checkout, --rebuild draws again the waiting clips that are
missing from output/clips/ (add --all for the ones already judged too).

Run from the repository root with the trial environment:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.nominate Kick_bands_mode --against Rainbow_mode --note "why"
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.nominate --rebuild

Exit code: 0 done, 1 refused (the reason is printed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from research.choreography import records

FEEDS = ("truth", "today", "candidate")      # what both modes can hear in a mode-against-mode clip


class Refused(ValueError):
    """The nomination is not allowed; the message says why in plain words."""


def _builders() -> tuple:
    from research.choreography import build_clips

    return build_clips.build_clip, build_clips.build_versus_clip, build_clips.DEFAULT_CLIPS


def _build(entry: dict, clips_dir: Path, build_feeds: Callable[..., Path], build_versus: Callable[..., Path]) -> Path:
    """Draw the clip of one queue entry, under the entry's own clip id."""
    if entry["against"]:
        return build_versus(entry["mode"], entry["against"], entry["track"], entry["start_s"], entry["duration_s"],
                            feed=entry["feed"], clip_id=entry["clip"], clips_dir=clips_dir)
    return build_feeds(entry["mode"], entry["track"], entry["start_s"], entry["duration_s"], clip_id=entry["clip"], clips_dir=clips_dir)


def nominate(mode: str, against: Optional[str] = None, feed: str = "today", note: str = "", *,
             passages: Optional[Sequence[tuple]] = None, queue_path: Path = records.QUEUE, verdicts_path: Path = records.VERDICTS,
             gates_path: Path = records.GATES, candidates: Path = records.CANDIDATES, production: Path = records.PRODUCTION_MODES,
             clips_dir: Path = records.CLIPS, build_feeds: Optional[Callable[..., Path]] = None,
             build_versus: Optional[Callable[..., Path]] = None) -> List[dict]:
    """Check the gates, build the clips, append the entries to the queue. Returns the new entries. Raises Refused."""
    if records.mode_file(mode, candidates, production) is None:
        raise Refused(f"no mode '{mode}' in research/choreography/candidates/ or modes/")
    gates = records.read_gates(gates_path)
    problem = records.gate_problem(mode, gates, candidates, production)
    if problem:
        raise Refused(problem)
    if against is not None:
        if against == mode:
            raise Refused("a mode cannot be nominated against itself")
        if records.mode_file(against, candidates, production) is None:
            raise Refused(f"no mode '{against}' in research/choreography/candidates/ or modes/")
        if feed not in FEEDS:
            raise Refused(f"feed must be one of {', '.join(FEEDS)}")
        if records.is_candidate(against, candidates):          # a registered mode already runs on the installation: no gate asked
            problem = records.gate_problem(against, gates, candidates, production)
            if problem:
                raise Refused(problem)
    if build_feeds is None or build_versus is None or passages is None:
        real_feeds, real_versus, real_passages = _builders()
        build_feeds, build_versus, passages = build_feeds or real_feeds, build_versus or real_versus, passages or real_passages

    queue = records.read_queue(queue_path)
    taken = {e.get("clip") for e in queue} | records.judged_clips(records.read_verdicts(verdicts_path))
    feed_of_entry = feed if against else None                  # a feeds clip shows every feed: no single feed to name
    n = 1
    while any(records.clip_name(t, s, mode, against, feed_of_entry, f"n{n}") in taken for t, s, _ in passages):
        n += 1
    entries = [{"clip": records.clip_name(track, start, mode, against, feed_of_entry, f"n{n}"), "mode": mode, "against": against,
                "feed": feed_of_entry, "track": track, "start_s": float(start), "duration_s": float(duration),
                "nominated": records.today(), "note": str(note)[:500]} for track, start, duration in passages]
    for entry in entries:                                      # build everything first: a failed build queues nothing
        print(f"wrote {_build(entry, clips_dir, build_feeds, build_versus)}", flush=True)
    records.write_queue(queue + entries, queue_path)
    return entries


def rebuild(everything: bool = False, *, queue_path: Path = records.QUEUE, verdicts_path: Path = records.VERDICTS,
            gates_path: Path = records.GATES, clips_dir: Path = records.CLIPS, build_feeds: Optional[Callable[..., Path]] = None,
            build_versus: Optional[Callable[..., Path]] = None) -> List[str]:
    """Draw again the queued clips missing from output/clips/: the waiting ones, or all of them. Returns their ids."""
    queue = records.read_queue(queue_path)
    wanted = queue if everything else records.waiting(queue, records.read_verdicts(verdicts_path))
    missing = [e for e in wanted if not (clips_dir / e["clip"] / "meta.json").is_file()]
    if missing and (build_feeds is None or build_versus is None):
        real_feeds, real_versus, _ = _builders()
        build_feeds, build_versus = build_feeds or real_feeds, build_versus or real_versus
    gates = records.read_gates(gates_path)
    for entry in missing:
        for name in (entry["mode"], entry["against"]):
            now, then = records.source_sha(records.mode_file(name or "")), (gates.get(name) or {}).get("source_sha")
            if name and now and then and now != then:
                print(f"warning: {name} has changed since its gate; clip {entry['clip']} shows the code as it is now", flush=True)
        print(f"wrote {_build(entry, clips_dir, build_feeds, build_versus)}", flush=True)
    return [e["clip"] for e in missing]


def main() -> int:
    p = argparse.ArgumentParser(description="Put clips of a gated mode in the owner's queue, or rebuild queued clips.")
    p.add_argument("mode", nargs="?")
    p.add_argument("--against", help="another mode to compare with (a lab candidate or a registered mode)")
    p.add_argument("--feed", default="today", choices=FEEDS, help="with --against: what both modes hear (default: today)")
    p.add_argument("--note", default="", help="a line for the owner: what to look at, why this comparison")
    p.add_argument("--rebuild", action="store_true", help="draw again the waiting clips that are missing from output/clips/")
    p.add_argument("--all", action="store_true", help="with --rebuild: also the clips the owner has already judged")
    args = p.parse_args()
    if args.rebuild:
        done = rebuild(args.all)
        print(f"{len(done)} clip(s) rebuilt." if done else "Nothing to rebuild: every queued clip is there.")
        return 0
    if not args.mode:
        p.error("give a mode to nominate, or --rebuild")
    try:
        entries = nominate(args.mode, args.against, args.feed, args.note)
    except Refused as why:
        print(f"Refused: {why}.")
        return 1
    print(f"{len(entries)} clip(s) added to the owner's queue: " + ", ".join(e["clip"] for e in entries))
    from research import inbox                   # the owner's one page (research/INBOX.md)
    from research.choreography import status

    status.write()
    inbox.write()
    return 0


if __name__ == "__main__":
    sys.exit(main())
