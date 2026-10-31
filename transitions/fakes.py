"""
transitions/fakes.py - Fake music and a fake installation for working on the sector alone.

No audio, no hardware, no project code: just the two input doors, scripted.
Used by `python -m transitions.sandbox` and by tests.
"""
from typing import Tuple

from transitions.api import InstallationSnapshot, ModeProfile, MusicSnapshot, SegmentDescriptor

FAKE_MODE_PROFILES: Tuple[ModeProfile, ...] = (
    ModeProfile("Rainbow", (0.35, 0.10, 0.20, 0.30), ("lead:spectrum", "form:field", "origin:global", "color:own-hue", "layer:bed")),
    ModeProfile("Bary Rainbow", (0.40, 0.15, 0.30, 0.35), ("lead:spectrum", "form:field", "origin:center", "color:own-hue", "layer:bed")),
    ModeProfile("Middle Bar", (0.55, 0.60, 0.50, 0.30), ("lead:beat", "axis:horizontal", "form:bar", "origin:center", "color:palette", "layer:pulse")),
    ModeProfile("Shining Stars", (0.30, 0.20, 0.25, 0.40), ("lead:transient", "form:sparkle", "origin:scatter", "color:palette", "layer:accent")),
    ModeProfile("Proportion Rainbow", (0.45, 0.25, 0.35, 0.40), ("lead:spectrum", "form:field", "origin:global", "color:own-hue", "layer:bed")),
    ModeProfile("Opposite Sides", (0.65, 0.55, 0.65, 0.45), ("lead:spectrum", "axis:horizontal", "form:bar", "origin:center", "color:palette", "layer:meter")),
    ModeProfile("Hyper Strobe", (0.95, 0.95, 0.85, 0.40), ("lead:transient", "form:flash", "origin:global", "color:palette", "layer:accent")),
    ModeProfile("Chromatic Chaser", (0.70, 0.60, 0.80, 0.50), ("lead:beat", "form:head", "origin:sweep", "color:palette", "layer:pulse")),
    ModeProfile("Metronome", (0.65, 0.85, 0.95, 0.30), ("lead:beat", "form:flash", "origin:global", "color:palette", "layer:pulse")),
    ModeProfile("Coloured Middle Wave", (0.60, 0.55, 0.60, 0.50), ("lead:spectrum", "axis:horizontal", "form:wave", "origin:center", "color:palette", "layer:meter")),
    ModeProfile("Impact Shockwave", (0.90, 0.95, 0.85, 0.60), ("lead:beat", "form:wave", "origin:center", "color:palette", "layer:accent")),
    ModeProfile("Power Bar", (0.70, 0.75, 0.60, 0.35), ("lead:level", "axis:vertical", "form:bar", "origin:bottom", "color:palette", "layer:meter")),
    ModeProfile("Extending Waves", (0.60, 0.50, 0.60, 0.50), ("lead:level", "axis:horizontal", "form:wave", "origin:center", "color:palette", "layer:meter")),
)

_CANONICAL_MODES: Tuple[str, ...] = tuple(p.name for p in FAKE_MODE_PROFILES)

# (start, end, scene, energy, salience, beat_trust, tension, rhythmic) within a 60 s loop
_SCRIPT: Tuple[Tuple[float, float, str, float, float, float, float, bool], ...] = (
    (0.0, 15.0, "CHILL", 0.20, 0.20, 0.30, 0.10, False),
    (15.0, 30.0, "GROOVE", 0.60, 0.70, 0.80, 0.20, True),
    (30.0, 35.0, "BUILDUP", 0.75, 0.80, 0.70, 0.85, True),
    (35.0, 50.0, "GROOVE", 0.85, 0.85, 0.85, 0.30, True),
    (50.0, 60.0, "CHILL", 0.25, 0.20, 0.30, 0.10, False),
)
LOOP_SECONDS = 60.0
DROP_AT = 35.0


def fake_music(t: float, bpm: float = 120.0) -> MusicSnapshot:
    """
    Scripted music at time t (seconds): CHILL -> GROOVE -> BUILDUP -> drop -> GROOVE -> CHILL, looping.
    The beat clock is a perfect metronome at `bpm`.
    """
    loop_t = t % LOOP_SECONDS
    period = 60.0 / bpm
    phase = (t % period) / period
    prev_phase = ((t - 1.0 / 30.0) % period) / period
    is_beat = phase < prev_phase  # phase wrapped since the previous 30 fps frame

    for start, end, scene, energy, salience, trust, tension, rhythmic in _SCRIPT:
        if start <= loop_t < end:
            break
    drop = DROP_AT <= loop_t < DROP_AT + 1.0 / 30.0
    drop_countdown = max(0.0, DROP_AT - loop_t) if scene == "BUILDUP" else 0.0
    return MusicSnapshot(
        beat_phase=phase,
        is_beat=is_beat,
        energy=0.95 if drop else energy,
        salience=salience,
        beat_trust=trust,
        novelty=0.4,
        tension=tension,
        power=energy,
        scene="DROP_IMPACT" if drop else scene,
        is_drop_impact=drop,
        is_locked=trust >= 0.5,
        is_rhythmic=rhythmic,
        is_silent=False,
        drop_countdown=drop_countdown,
        is_drop_imminent=bool(0.0 < drop_countdown <= 0.40),
    )


def fake_installation(vertical: int = 4, rings: int = 3) -> InstallationSnapshot:
    """A small chandelier: `vertical` pillars and `rings` horizontal rings, every mode available."""
    modes = _CANONICAL_MODES
    first = modes[0] if modes else "Rainbow"
    tiers = ("tier:canopy", "tier:mid", "tier:low")
    segments = [
        SegmentDescriptor(
            f"Segment v{i}",
            "vertical",
            modes,
            first,
            id=f"v{i}",
            tags=("half:left" if i <= max(1, vertical // 2) else "half:right", "pos:outer" if i in (1, vertical) else "pos:inner"),
        )
        for i in range(1, vertical + 1)
    ] + [
        SegmentDescriptor(
            f"Segment h1{i}",
            "horizontal",
            modes,
            first,
            id=f"h1{i}",
            tags=(tiers[i % len(tiers)], "half:left" if i % 2 == 0 else "half:right"),
        )
        for i in range(rings)
    ]
    return InstallationSnapshot(segments=tuple(segments), modes=FAKE_MODE_PROFILES, room_bounds=(430, 246))


def make_fake_installation() -> InstallationSnapshot:
    """Full 11-segment chandelier fixture matching segments_full.json tags."""
    modes = _CANONICAL_MODES
    first = modes[0] if modes else "Rainbow"
    specs = (
        ("h00", "horizontal", ("tier:canopy", "half:left", "size:long")),
        ("v1", "vertical", ("half:left", "pos:outer")),
        ("h10", "horizontal", ("tier:low", "half:left", "size:medium")),
        ("h11", "horizontal", ("tier:mid", "half:left", "size:medium")),
        ("v2", "vertical", ("half:left", "pos:inner")),
        ("h20", "horizontal", ("tier:canopy", "half:right", "size:medium")),
        ("v3", "vertical", ("half:right", "pos:inner")),
        ("h30", "horizontal", ("tier:canopy", "half:right", "size:short")),
        ("h31", "horizontal", ("tier:low", "half:right", "size:short")),
        ("h32", "horizontal", ("tier:mid", "half:right", "size:short")),
        ("v4", "vertical", ("half:right", "pos:outer")),
    )
    segs = tuple(
        SegmentDescriptor(f"Segment {sid}", ori, modes, first, id=sid, tags=tags)
        for sid, ori, tags in specs
    )
    return InstallationSnapshot(segments=segs, modes=FAKE_MODE_PROFILES, room_bounds=(430, 246))


def make_fake_small_installation() -> InstallationSnapshot:
    """Small 3-segment chandelier fixture matching segments_small.json tags."""
    modes = _CANONICAL_MODES
    first = modes[0] if modes else "Rainbow"
    specs = (
        ("s1", "vertical", ("half:left", "pos:outer")),
        ("s2", "vertical", ("half:left", "pos:inner")),
        ("s3", "vertical", ("half:right", "pos:outer")),
    )
    segs = tuple(
        SegmentDescriptor(f"Segment {sid}", ori, modes, first, id=sid, tags=tags)
        for sid, ori, tags in specs
    )
    return InstallationSnapshot(segments=segs, modes=FAKE_MODE_PROFILES, room_bounds=(430, 246))

