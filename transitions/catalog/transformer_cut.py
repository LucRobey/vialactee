"""
transitions/catalog/transformer_cut.py - DJ Crossfader 'Transformer' Stutter with Smooth Lock-In.
"""

import math
import numpy as np

from transitions.catalog._common import ACTIVE_PARAMS, TransitionFamily as F, TransitionSpec


def apply_transformer_cut(rgb_old: np.ndarray, rgb_new: np.ndarray, progress: float) -> None:
    """
    DJ crossfader 'transformer' stutter: gates rapidly between old and new modes
    across rhythmic subdivisions with increasing duty cycle and a smooth final lock-in.
    """
    progress = max(0.0, min(1.0, float(progress)))
    if progress <= 0.0:
        return
    if progress >= 1.0:
        np.copyto(rgb_old, rgb_new)
        return

    gates = float(max(4, int(ACTIVE_PARAMS.get("chop_count", 4)) * 2))
    g = progress * gates
    gate_idx = int(g)
    phase = g - gate_idx
    duty_new = min(1.0, 0.15 + 0.85 * (progress ** 0.85))

    tail = max(0.0, min(1.0, (progress - 0.72) / 0.28))
    smooth_tail = tail * tail * (3.0 - 2.0 * tail)
    gate_mix = 1.0 if phase < duty_new else smooth_tail
    edge_punch = 1.0 + 0.22 * math.exp(-abs(phase - duty_new) * 10.0) * (1.0 - smooth_tail)

    blended = (rgb_old * (1.0 - gate_mix) + rgb_new * gate_mix) * edge_punch
    np.clip(blended, 0, 255, out=rgb_old, casting="unsafe")


SPEC = TransitionSpec(
    name="transformer_cut",
    families=frozenset({F.RHYTHMIC_CHOP, F.STAGGERABLE}),
    duration=1.4,
    kind="strip_1d",
    handler=apply_transformer_cut,
)
