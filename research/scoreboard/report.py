"""Write SCOREBOARD.md from the graded results: one line per signal, averaged over the tracks."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

MEANING = {
    "event": "100 = every one found, none invented",
    "state": "100 = always right; 50 = no better than a signal stuck on one answer",
    "value": "100 = follows the truth exactly; 0 = unrelated",
}
ROLE = {"MultiBandOnsetAudioAnalyzer": "the model running on the installation (main analyzer since 2026-11-27)", "DyadicMetricalAudioAnalyzer": "the same model plus the half-beat sub-pulse (main until 2026-11-27), selectable"}


def _mean(values: List[Optional[float]]) -> float:
    v = [x for x in values if x is not None and x == x]
    return float(np.mean(v)) if v else float("nan")


def _n(values: List[Optional[float]]) -> int:
    return sum(1 for x in values if x is not None and x == x)


def _pct(x: float) -> str:
    return "-" if x != x else f"{100 * x:.0f}"


def _note(kind: str, name: str, details: List[dict]) -> str:
    def avg(key: str) -> float:
        return _mean([d.get(key) for d in details])

    if name == "bpm":
        return f"double tempo {_pct(avg('double'))}% of the time, half tempo {_pct(avg('half'))}%"
    if kind == "event":
        if avg("n_est") == 0:
            return "it never fires on these tracks"
        off = avg("offset_ms")
        return (f"finds {_pct(avg('found'))}% of them; {_pct(avg('right'))}% of what it reports is real"
                + ("" if off != off else f"; typically {abs(off):.0f} ms {'late' if off > 0 else 'early'}"))
    if kind == "state":
        if avg("when_on") != avg("when_on"):
            return f"the truth has none on these tracks; the signal is on {_pct(1 - avg('when_off'))}% of the time"
        delay = avg("edge_delay_s")
        return (f"right {_pct(avg('when_on'))}% of the time while it is on, {_pct(avg('when_off'))}% while it is off"
                + ("" if delay != delay else f"; edges {abs(delay):.1f} s {'late' if delay > 0 else 'early'}"))
    lag = avg("lag_ms")
    return "" if lag != lag else f"{abs(lag):.0f} ms {'late' if lag > 0 else 'early'}"


def _rows(per_track: Dict[str, dict], section: str, names: List[str], kinds: Dict[str, str]) -> List[str]:
    rows = []
    for name in names:
        cells = [t[section][name] for t in per_track.values() if name in t[section]]
        checked, every = [c["checked"] for c in cells], [c["all"] for c in cells]
        base = name.split(" <- ")[0]
        kind = kinds[base]
        rows.append(f"| {name} | {_pct(_mean(checked))} | {_n(checked)} | {_pct(_mean(every))} | {_n(every)} | "
                    f"{_note(kind, base, [c['detail'] for c in cells])} |")
    return rows


def write_report(result: dict, spec: dict, out_path: Path) -> None:
    kinds = {s["name"]: s["kind"] for s in spec["signals"]}
    truth_of = {s["name"]: s["truth"] for s in spec["signals"]}
    lines = [
        "# Scoreboard: the live analyzer against the source of truth",
        "",
        f"Built {result['built']} by `research/scoreboard/scoreboard.py`. {len(result['tracks'])} tracks, each played through the "
        f"production `Listener` with the {result['lookahead_s']:.0f} s look-ahead. Every signal is read at speaker time from "
        "`listener.signals` and compared with the truth value it mirrors (`config/music_signals.json`).",
        "",
        "How to read the numbers (all from 0 to 100, averaged over the tracks):",
        "",
        f"- a **moment** (beat, hit, drop): {MEANING['event']};",
        f"- a **stretch** (silence, no beat, kick present): {MEANING['state']};",
        f"- a **level** (loudness, brightness): {MEANING['value']};",
        "- **tempo**: share of the time at the right tempo.",
        "",
        "**Checked truth** counts only truth allowed to grade: timed or accepted by ear, two tools agreeing, or an exact "
        "measurement. **All truth** also counts what one tool alone says; it is indicative. A dash means there is nothing to grade against.",
        "",
    ]
    for model, per_track in result["models"].items():
        first = next(iter(per_track.values()))
        produced = [n for n, c in first["signals"].items() if c["produced"]]
        empty = [n for n, c in first["signals"].items() if not c["produced"]]
        lines += [
            f"## {model}", "", f"*{ROLE.get(model, 'candidate model')}*", "",
            f"### The {len(produced)} signals it produces today", "",
            "| Signal | On checked truth | tracks | On all truth | tracks | What happens |", "|---|---|---|---|---|---|",
            *_rows(per_track, "signals", produced, kinds), "",
            f"### The {len(empty)} empty slots", "",
            "Nothing produces these yet, so there is nothing to grade: " + ", ".join(f"`{n}`" for n in empty) + ".", "",
            "### Existing signals tried as candidates for an empty slot", "",
            "Each line takes a signal the analyzer already has and grades it as if it filled the slot on the left.", "",
            "| Slot <- candidate | On checked truth | tracks | On all truth | tracks | What happens |", "|---|---|---|---|---|---|",
            *_rows(per_track, "candidates", list(first["candidates"]), kinds), "",
        ]
    models = list(result["models"])
    lines += ["## Song by song: beats and tempo (on checked truth)", "",
              "| # | Track | Group | " + " | ".join(f"beat {m[:12]} | tempo {m[:12]}" for m in models) + " |",
              "|---|---|---|" + "---|---|" * len(models)]
    for tid, info in result["tracks"].items():
        cells = []
        for m in models:
            sig = result["models"][m][tid]["signals"]
            cells += [_pct(sig["beat"]["checked"]), _pct(sig["bpm"]["checked"])]
        lines.append(f"| {tid} | {info['file'].rsplit('.', 1)[0][:34]} | {info['group']} | " + " | ".join(cells) + " |")
    lines += ["", "## What each signal is graded against", "",
              ", ".join(f"`{n}` against `{t}`" for n, t in truth_of.items()) + ".", ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
