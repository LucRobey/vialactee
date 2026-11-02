"""
transitions/catalog/gravity_drop.py - Architectural Marble-Run Cascade.
"""

import numpy as np

from transitions.catalog._common import ROOM_MAX_X, ROOM_MAX_Y, TransitionFamily as F, TransitionSpec


def apply_gravity_drop(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
) -> None:
    """
    Architectural Marble-Run Cascade:
    Luminous spheres travel left-to-right (nx: 0 -> 1) along the horizontal bars and
    plunge downward with gravity (ny: 0 -> 1) whenever they reach a vertical pillar
    (v1 at nx=0.48, v2 at nx=0.68, v3 at nx=0.89, v4 at nx=1.00), unveiling `rgb_list_new`.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    nx = np.clip(coords[:, 0] / max(1.0, float(ROOM_MAX_X)), 0.0, 1.0)
    ny = np.clip(coords[:, 1] / max(1.0, float(ROOM_MAX_Y)), 0.0, 1.0)

    cascade_t = 0.56 * nx + 0.32 * (ny ** 0.78)
    lead_p = progress * 0.98

    ahead_d = cascade_t - lead_p
    trench = (ahead_d > 0.0) & (ahead_d < 0.18)
    if np.any(trench):
        t_fade = (ahead_d[trench] / 0.18) ** 1.5
        rgb_list_old[trench] = (rgb_list_old[trench] * (0.08 + 0.92 * t_fade[:, np.newaxis])).astype(np.int32)

    np.copyto(rgb_list_old, rgb_list_new, where=(cascade_t <= lead_p)[:, np.newaxis])

    tail_fade = 1.0 if progress < 0.84 else max(0.0, (1.0 - progress) / 0.16) ** 1.4
    if tail_fade <= 1e-3:
        return

    marbles = (
        (0.00, np.array([255.0, 215.0, 60.0])),
        (0.07, np.array([0.0, 235.0, 255.0])),
        (0.14, np.array([255.0, 60.0, 200.0])),
        (0.21, np.array([180.0, 255.0, 120.0])),
    )
    pillar_xs = (205.0 / 430.0, 292.0 / 430.0, 383.0 / 430.0, 1.0)
    glow = np.zeros((len(rgb_list_old), 3), dtype=np.float64)

    for delay, color in marbles:
        mp = progress - delay
        if mp <= 0.0:
            continue
        roll_nx = (mp - 0.32 * (ny ** 0.78)) / 0.56
        h_orb = np.clip(1.0 - np.abs(nx - roll_nx) / 0.09, 0.0, 1.0) ** 1.8
        glow += h_orb[:, np.newaxis] * color

        for px in pillar_xs:
            t_pillar = mp - 0.56 * px
            if 0.0 < t_pillar < 0.42:
                drop_ny = min(1.05, 0.05 + 1.85 * ((t_pillar / 0.34) ** 1.65))
                on_pillar = np.clip(1.0 - np.abs(nx - px) / 0.04, 0.0, 1.0)
                v_orb = on_pillar * (np.clip(1.0 - np.abs(ny - drop_ny) / 0.16, 0.0, 1.0) ** 1.6)
                glow += v_orb[:, np.newaxis] * (color * 0.7 + np.array([255.0, 255.0, 255.0]) * 0.5)

    np.clip(rgb_list_old + glow * tail_fade, 0, 255, out=rgb_list_old, casting="unsafe")


SPEC = TransitionSpec(
    name="gravity_drop",
    families=frozenset({F.ROOM_SWEEP_2D}),
    duration=2.8,
    kind="spatial_room",
    handler=apply_gravity_drop,
)
