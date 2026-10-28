"""
utils/choreography.py
Choreography Doctrine constants (see docs/contracts/mode_contract.md Law 7: One Lead Timescale).
"""
from typing import Tuple
import numpy as np

# The four audio drivers a mode may declare as LEAD or SECONDARY.
DRIVERS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient")

# All five mute channels supported by DriverMuteProxy and Mode Studio ("macro" is a mute channel only).
MUTE_CHANNELS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient", "macro")

NEUTRAL_MOOD_MODIFIERS: np.ndarray = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
NEUTRAL_MOOD_MODIFIERS.flags.writeable = False
