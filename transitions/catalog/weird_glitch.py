"""
transitions/catalog/weird_glitch.py - 3-Act Cyberpunk Sector Corruption & Matrix Reboot.
"""

import math
import numpy as np

from transitions.catalog._common import (
    ACTIVE_PARAMS,
    ROOM_MAX_X,
    ROOM_MAX_Y,
    TransitionFamily as F,
    TransitionSpec,
)


def apply_weird_glitch(
    rgb_list_old: np.ndarray,
    rgb_list_new: np.ndarray,
    coords: np.ndarray,
    progress: float,
) -> None:
    """
    3-Act Cyberpunk Sector Corruption & Matrix Reboot:
    - Act I (0.00..0.32): Quantized sector freeze, RGB channel tear & scanline blackouts.
    - Act II (0.32..0.72): High-contrast pitch-black void with teleporting neon cyber-blocks.
    - Act III (0.72..1.00): Progressive digital scanline resync locking smoothly into `rgb_list_new`.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_list_old, rgb_list_new)
        return

    nx = np.clip(coords[:, 0] / max(1.0, float(ROOM_MAX_X)), 0.0, 1.0)
    ny = np.clip(coords[:, 1] / max(1.0, float(ROOM_MAX_Y)), 0.0, 1.0)
    seed = float(ACTIVE_PARAMS.get("seed", 0.0))

    bx = np.floor(nx * 7.0)
    by = np.floor(ny * 5.0)
    step = math.floor(progress * 22.0)
    b_hash = np.mod(np.sin(bx * 127.1 + by * 311.7 + step * 19.3 + seed) * 43758.5453, 1.0)
    static_h = np.mod(np.sin(bx * 73.1 + by * 157.3 + seed) * 19731.3, 1.0)

    if progress < 0.32:
        p1 = progress / 0.32
        infected = static_h < (0.25 + 0.75 * p1)
        dropout = infected & (b_hash < 0.42)
        tear_c = infected & (b_hash >= 0.42) & (b_hash < 0.72)
        tear_m = infected & (b_hash >= 0.72)
        rgb_list_old[dropout] = 0
        if np.any(tear_c):
            rgb_list_old[tear_c, 0] = 0
            rgb_list_old[tear_c, 1] = np.clip(rgb_list_old[tear_c, 1] + 150, 0, 255)
            rgb_list_old[tear_c, 2] = 255
        if np.any(tear_m):
            rgb_list_old[tear_m, 0] = 255
            rgb_list_old[tear_m, 1] = 0
            rgb_list_old[tear_m, 2] = np.clip(rgb_list_old[tear_m, 2] + 150, 0, 255)
    elif progress < 0.72:
        p2 = (progress - 0.32) / 0.40
        rgb_list_old.fill(0)
        m_new = (b_hash >= 0.28) & (b_hash < (0.55 + 0.25 * p2))
        m_cyan = (b_hash >= 0.80) & (b_hash < 0.87)
        m_mag = (b_hash >= 0.87) & (b_hash < 0.94)
        m_yel = b_hash >= 0.94
        np.copyto(rgb_list_old, rgb_list_new, where=m_new[:, np.newaxis])
        rgb_list_old[m_cyan] = [0, 250, 255]
        rgb_list_old[m_mag] = [255, 0, 210]
        rgb_list_old[m_yel] = [255, 235, 0]
    else:
        p3 = (progress - 0.72) / 0.28
        scan_lock = 0.65 * ny + 0.35 * static_h
        locked = scan_lock <= (p3 * 1.15)
        rgb_list_old.fill(0)
        np.copyto(rgb_list_old, rgb_list_new, where=locked[:, np.newaxis])
        if np.any(~locked):
            rgb_list_old[~locked] = (rgb_list_new[~locked] * p3).astype(np.int32)
        sync_bar = np.clip(1.0 - np.abs(ny - p3) / 0.14, 0.0, 1.0) * ((1.0 - p3) ** 1.4)
        out = rgb_list_old + sync_bar[:, np.newaxis] * np.array([0.0, 240.0, 255.0])
        np.clip(out, 0, 255, out=rgb_list_old, casting="unsafe")


SPEC = TransitionSpec(
    name="weird_glitch",
    families=frozenset({F.ROOM_EPI_2D, F.STOCHASTIC_ORGANIC, F.RHYTHMIC_CHOP}),
    duration=2.2,
    kind="spatial_room",
    handler=apply_weird_glitch,
)
