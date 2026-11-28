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
- The production analyzer writes the slots listed in PRODUCED.

Writing a slot stores a reference: no allocation on the hot path (AXIOM-02).

One-frame signals and the display loop: the analyzer ticks 60 times a second and the display draws 30 times a
second. A signal that is true for one tick and cleared on the next is missed by a reader that looks every other
tick. `DisplayHold` keeps every one-frame signal up until the display has collected it once
(`Listener.begin_display_frame`).
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

# Slots that the production analyzer writes itself (music/BandKickSignals.py, called by
# MultiBandOnsetAudioAnalyzer and every model built on it). They stay None until the first audio has reached the speakers.
PRODUCED: Tuple[str, ...] = ("no_beat", "kick", "kick_present", "band_bass", "band_mid", "band_high")


# Event slots: true (or a strength above 0) on one tick only. Same list as kind == "event" in the signal list.
EVENTS: Tuple[str, ...] = ("beat", "kick", "snare", "hat", "tom", "cymbal", "drop", "section_change")

# One-frame flags of `Listener` that the display must not miss.
FLAGS: Tuple[str, ...] = (
    "is_beat", "is_real_beat", "is_dropped_beat", "is_song_change", "is_verse_chorus_change",
    "live_is_song_change", "live_is_verse_chorus_change",
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


class DisplayHold:
    """One-frame signals held between two frames of the display loop.

    After every analyzer tick, `hold` remembers which one-frame signals fired. Once per display frame, `publish`
    makes what fired since the previous frame visible and starts again. Each event is therefore seen for exactly
    one display frame, whatever the two rates. Until the display declares itself by publishing once, `active` is
    False and readers get the tick values, as benchmarks and studios that read every tick expect.
    """

    __slots__ = ("active", "pending", "shown", "signals", "pending_events")

    def __init__(self) -> None:
        self.active: bool = False
        self.pending: Dict[str, bool] = dict.fromkeys(FLAGS, False)
        self.shown: Dict[str, bool] = dict.fromkeys(FLAGS, False)
        self.signals: MusicSignals = MusicSignals()          # the record as the display sees it
        self.pending_events: Dict[str, Any] = dict.fromkeys(EVENTS)

    def reset(self) -> None:
        for name in FLAGS:
            self.pending[name] = self.shown[name] = False
        for name in EVENTS:
            self.pending_events[name] = None
        self.signals.clear()

    def hold(self, listener: Any, tick_signals: MusicSignals) -> None:
        """Called after each analyzer tick: remember what fired on it."""
        pending = self.pending
        for name in FLAGS:
            if listener._tick(name):
                pending[name] = True
        events = self.pending_events
        for name in EVENTS:
            v = getattr(tick_signals, name)
            if v:
                cur = events[name]
                if cur is None or v > cur:
                    events[name] = v

    def publish(self, tick_signals: MusicSignals) -> None:
        """Called once per display frame: show what fired since the previous frame, and start again."""
        self.active = True
        pending, shown = self.pending, self.shown
        for name in FLAGS:
            shown[name] = pending[name]
            pending[name] = False
        out, events = self.signals, self.pending_events
        for name in FIELDS:
            setattr(out, name, getattr(tick_signals, name))
        for name in EVENTS:
            if events[name] is not None:
                setattr(out, name, events[name])
                events[name] = None
