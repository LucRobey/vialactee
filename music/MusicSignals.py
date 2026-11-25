"""
music/MusicSignals.py - The signal record that mirrors the source of truth, field for field.

One slot per thing the offline truth knows about a song (research/truth/). Every slot describes the music
AT SPEAKER TIME: what is being heard right now. The list of slots, their meaning and the truth they are graded
against live in config/music_signals.json; docs/contracts/music_analyzer_contract.md section 6 is the
human-readable contract. A governance test keeps the three identical.

A slot holds None until something produces it. None means "the analyzer does not know": it is falsy, so a
consumer that reads an empty slot simply sees "no hit", "not present", "nothing".

Who fills what:
- `Listener` fills the slots that an existing signal already expresses (the bridge, see BRIDGED).
- A rhythm analyzer fills any other slot by writing to `self.signals.<name>` once per tick, with the value at
  speaker time (it has the look-ahead seconds of future audio to decide). `BaseAudioAnalyzer` creates the
  record, so a model only writes the slots it works on.

Writing a slot stores a reference: no allocation on the hot path (AXIOM-02).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

# Slots in the order of config/music_signals.json.
FIELDS: Tuple[str, ...] = (
    # pulse
    "beat", "bpm", "no_beat", "bar_position", "beats_per_bar", "beat_strength",
    # drums
    "kick", "snare", "hat", "tom", "cymbal", "kick_present", "kick_level",
    # moments and structure
    "drop", "section_change", "breakdown", "buildup", "riser", "silence",
    # who is playing
    "bass_present", "drums_present", "vocal_present", "other_present",
    "bass_level", "drums_level", "vocal_level", "other_level", "layers",
    # sound
    "loudness", "band_sub", "band_bass", "band_mid", "band_high", "brightness", "fullness",
    # harmony
    "chord",
)

# Slots that `Listener` fills from a signal the sector already produces.
BRIDGED: Tuple[str, ...] = (
    "beat", "bpm", "drop", "section_change", "buildup", "silence", "loudness", "brightness",
)


class MusicSignals:
    """Flat record of every truth-mirrored signal at speaker time. Empty slots are None."""

    __slots__ = FIELDS

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        """Empty every slot (track change, reset)."""
        for name in FIELDS:
            setattr(self, name, None)

    def as_dict(self) -> Dict[str, Any]:
        """Snapshot for studios, telemetry and the benchmark (allocates: not for the hot path)."""
        return {name: getattr(self, name) for name in FIELDS}
