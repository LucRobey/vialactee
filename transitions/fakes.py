"""
transitions/fakes.py - Fake music and a fake installation for working on the sector alone.

No audio, no hardware, no project code: just the two input doors, scripted.
Used by `python -m transitions.sandbox` and by tests.
"""
from typing import Tuple

from transitions.api import InstallationSnapshot, MusicSnapshot, SegmentDescriptor
from transitions.mode_dna import MODE_DNA

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
    )


def fake_installation(vertical: int = 4, rings: int = 3) -> InstallationSnapshot:
    """A small chandelier: `vertical` pillars and `rings` horizontal rings, every mode available."""
    modes = tuple(MODE_DNA.keys())
    first = modes[0] if modes else "Rainbow"
    segments = [
        SegmentDescriptor(f"Segment v{i}", "vertical", modes, first) for i in range(1, vertical + 1)
    ] + [
        SegmentDescriptor(f"Segment h1{i}", "horizontal", modes, first) for i in range(rings)
    ]
    return InstallationSnapshot(segments=tuple(segments), room_bounds=(430, 246))
