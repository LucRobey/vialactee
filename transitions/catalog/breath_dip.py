"""
transitions/catalog/breath_dip.py - Two-Stage Theatrical Exhale/Inhale Reset.
"""

import math
import numpy as np

from transitions.catalog._common import TransitionFamily as F, TransitionSpec, get_u


def apply_breath_dip(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    Two-stage theatrical reset (Exhale to center darkness -> suspense pause -> Inhale bloom).
    Ideal for song changes and ambient breakdowns.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    n = len(rgb_old)
    if n == 0:
        return
    u = get_u(n)
    dist_center = np.abs(2.0 * u - 1.0)

    if progress < 0.45:
        p1 = progress / 0.45
        edge_envelope = np.clip((1.0 - p1 * 1.15 - dist_center * p1) / max(0.05, 1.0 - p1 * 0.5), 0.0, 1.0)
        gain = (edge_envelope * (1.0 - p1 * p1))[:, np.newaxis]
        np.multiply(rgb_old, gain, out=rgb_old, casting="unsafe")
    elif progress < 0.55:
        rgb_old.fill(0)
    else:
        p2 = (progress - 0.55) / 0.45
        win = 0.25
        reveal = np.clip((p2 * (1.0 + win) - dist_center) / win, 0.0, 1.0)
        envelope = (reveal * reveal * (3.0 - 2.0 * reveal) * math.sin(p2 * math.pi * 0.5))[:, np.newaxis]
        np.multiply(rgb_new, envelope, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="breath_dip",
    families=frozenset({F.STAGGERABLE, F.MODE_COOPERATIVE}),
    duration=2.4,
    kind="strip_1d",
    handler=apply_breath_dip,
)
