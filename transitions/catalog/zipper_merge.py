"""
transitions/catalog/zipper_merge.py - 3-Act Mechanical Interlock Zipper Transition.
"""

import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec, get_u


def apply_zipper_merge(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    3-Act Mechanical Interlock:
    - Act I (0.00..0.28): Slider spark rips down the strip, splitting old mode into pitch-black tooth sockets.
    - Act II (0.28..0.80): Bold full-brightness teeth of incoming mode slide from opposite ends to interlock.
    - Act III (0.80..1.00): Teeth slam shut at the zone seams with a crisp metallic lock flash.
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
    teeth = float(max(2, int(ACTIVE_PARAMS.get("teeth_count", 4))))
    scaled = u * teeth
    zone = np.minimum(np.floor(scaled).astype(np.int32), int(teeth) - 1)
    local_u = scaled - zone
    is_even = (zone % 2) == 0

    if progress < 0.28:
        p1 = progress / 0.28
        unzipped_odd = (~is_even) & (u <= p1)
        rgb_old[unzipped_odd] = (rgb_old[unzipped_odd] * 0.04).astype(np.int32)
        slider_glow = np.clip(1.0 - np.abs(u - p1) / 0.09, 0.0, 1.0) ** 2
        if np.any(slider_glow > 0.0):
            g = slider_glow[:, np.newaxis]
            rgb_old[:] = np.clip(rgb_old * (1.0 - g * 0.5) + g * np.array([255, 235, 160]), 0, 255).astype(np.int32)
    elif progress < 0.80:
        p2 = (progress - 0.28) / 0.52
        tooth_pos = np.where(is_even, local_u, 1.0 - local_u)
        edge_w = max(0.06, float(ACTIVE_PARAMS.get("edge_width", 0.14)) * 0.6)
        rgb_old[:] = (rgb_old * 0.04).astype(np.int32)
        mask_in = tooth_pos <= p2
        np.copyto(rgb_old, rgb_new, where=mask_in[:, np.newaxis])
        stud = np.clip(1.0 - np.abs(tooth_pos - p2) / edge_w, 0.0, 1.0) ** 2
        if np.any(stud > 0.0):
            s = stud[:, np.newaxis]
            rgb_old[:] = np.clip(rgb_old + s * np.array([255, 240, 190]), 0, 255).astype(np.int32)
    else:
        p3 = (progress - 0.80) / 0.20
        np.copyto(rgb_old, rgb_new)
        seam_dist = np.minimum(local_u, 1.0 - local_u)
        seam_flash = (np.clip(1.0 - seam_dist / 0.14, 0.0, 1.0) * ((1.0 - p3) ** 2) * 210.0)[:, np.newaxis]
        np.clip(rgb_old + seam_flash, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="zipper_merge",
    families=frozenset({F.STRIP_SWEEP_1D, F.STAGGERABLE}),
    duration=2.8,
    kind="strip_1d",
    handler=apply_zipper_merge,
)
