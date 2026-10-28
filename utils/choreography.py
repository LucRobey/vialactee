"""
utils/choreography.py
Choreography Doctrine constants, driver-mute proxy, and response metrics
(see docs/contracts/mode_contract.md Law 7: One Lead Timescale).
"""
from typing import Tuple

# The four audio drivers a mode may declare as LEAD or SECONDARY.
DRIVERS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient")

# All five mute channels supported by DriverMuteProxy and Mode Studio ("macro" is a mute channel only).
MUTE_CHANNELS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient", "macro")
