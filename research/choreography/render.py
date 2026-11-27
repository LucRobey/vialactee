"""Render a mode on a passage of a song, as the installation would show it.

The song is played from its start through the production Listener (music.api) with the 5 s look-ahead, so the
analyzer is in the state it would be in on the installation. On every tick the chosen feed lays its signals
over listener.signals (feeds.py), the mood service is updated, and one instance of the mode per segment draws
its LEDs. Every frame inside the passage is kept (60 per second), as one array for the whole installation.

Brightness: the installation sends these values to its LEDs unchanged, and an LED's light is proportional to
the value. The eye is not: a tenth of the light looks more than a third as bright. `perceived` converts a
drive value to how bright it looks; every number the lab reports about brightness goes through it.
"""
from __future__ import annotations

import random
from typing import Any, Optional, Sequence

import numpy as np

from research.choreography.feeds import FPS, Feed
from research.choreography.layout import Layout

LOOKAHEAD_S: float = 5.0
SETTLE_S: float = 3.0          # the mode starts drawing this long before the passage, so its smoothing has settled
KEEP_EVERY: int = 1            # every tick is kept: timing is measured to 17 ms, and fast flashes are visible
CLIP_FPS: float = FPS / KEEP_EVERY


def render_clip(mode_cls: Any, mono: np.ndarray, layout: Layout, feed: Optional[Feed], start_s: float, duration_s: float,
                infos: Optional[dict] = None) -> np.ndarray:
    """Frames of `mode_cls` over [start_s, start_s + duration_s], shape (frames, total LEDs, 3), uint8."""
    from modes.Mode import Mode
    from mood.api import create_mood_service
    from music.api import Listener
    from tools.choreography_probe import HOP, OfflineClock, step_listener
    from tools.listener_config import build_listener_infos

    random.seed(42)
    np.random.seed(42)
    lead = int(round(LOOKAHEAD_S * FPS))
    first = int(round(start_s * FPS))                       # speaker-time frame where the passage starts
    count = int(round(duration_s * FPS))
    settle_from = max(0, first - int(SETTLE_S * FPS))
    out = np.zeros((count // KEEP_EVERY, layout.total, 3), dtype=np.uint8)
    cfg = build_listener_infos()
    cfg["fakeDelay"] = LOOKAHEAD_S

    with OfflineClock() as clock:
        listener = Listener(cfg)
        listener.dynamic_audio_latency = 0.0
        mood = create_mood_service(auto_scene=True)
        Mode.bind_mood_colors(mood.colors())
        Mode.bind_mood_modifiers(mood.modifiers())
        try:
            buffers, modes = [], []
            for seg in layout.segments:
                rgb = np.zeros((seg.size, 3), dtype=np.int32)
                mode_infos = {"tags": seg.tags, "orientation": seg.orientation, **(infos or {})}
                modes.append(mode_cls(mode_cls.__name__, seg.name, listener, None, list(range(seg.size)), rgb, mode_infos))
                buffers.append(rgb)
            for k in range(first + count + lead):
                step_listener(listener, mono, k * HOP, clock)
                i = k - lead                                   # the speaker-time frame this tick shows
                if feed is not None:
                    feed.apply(i, listener.signals)
                ctx = listener.context
                scene = getattr(ctx, "scene", None)
                mood.update(1.0 / FPS, str(getattr(scene, "value", scene)) if scene is not None else None)
                Mode.bind_mood_modifiers(mood.modifiers())
                if i < settle_from:
                    continue
                for mode, rgb in zip(modes, buffers):
                    mode.render(buffer=rgb)
                j = i - first
                if 0 <= j < count and j % KEEP_EVERY == 0 and j // KEEP_EVERY < len(out):
                    for seg, rgb in zip(layout.segments, buffers):
                        np.clip(rgb, 0, 255, out=rgb)
                        out[j // KEEP_EVERY, seg.offset : seg.offset + seg.size] = rgb
        finally:
            Mode.reset_mood_colors()
            Mode.reset_mood_modifiers()
    return out


def perceived(light: np.ndarray) -> np.ndarray:
    """How bright a share of full light (0..1) looks, 0..1: the CIE lightness curve."""
    x = np.clip(light, 0.0, 1.0)
    return np.where(x > 0.008856, 1.16 * np.cbrt(x) - 0.16, 9.033 * x)


def screen_values(frames: np.ndarray) -> np.ndarray:
    """LED drive values re-coded so that a screen shows them as bright as the LEDs would look (sRGB-like curve)."""
    lut = np.round(255.0 * (np.arange(256) / 255.0) ** (1.0 / 2.2)).astype(np.uint8)
    return lut[frames]


def brightness(frames: np.ndarray) -> np.ndarray:
    """How bright the whole installation looks on each frame, 0..1 (mean over LEDs of the perceived strongest channel)."""
    lut = perceived(np.arange(256) / 255.0).astype(np.float32)
    return lut[frames.max(axis=2)].mean(axis=1)


def cut_audio(mono: np.ndarray, start_s: float, duration_s: float, sr: int = 44100) -> np.ndarray:
    a = int(round(start_s * sr))
    return mono[a : a + int(round(duration_s * sr))]
