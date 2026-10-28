"""
tools/studio_mutes.py
Mode Studio HUD formatter and Pygame keyboard shortcut handler for DriverMuteProxy.
"""
from typing import Any, Dict, Optional

# Single table of Pygame key names resolved via getattr(pygame, name) at call time.
CTRL_KEY_MAP: Dict[str, str] = {
    "K_b": "beat",
    "K_l": "level",
    "K_s": "spectrum",
    "K_t": "transient",
    "K_m": "macro",
}
CLEAR_MUTES_KEY: str = "K_0"


def format_hud_line(proxy: Any, mode: Any) -> str:
    """Format the compact choreography status line for Mode Studio HUD."""
    lead = getattr(mode, "LEAD", "") or "undeclared"
    sec_tuple = getattr(mode, "SECONDARY", ())
    sec = sec_tuple[0] if sec_tuple else "none"
    muted_list = ", ".join(proxy.muted) if proxy.muted else "none"
    return f"LEAD: {lead} · SECONDARY: {sec} · muted: [{muted_list}]"


def handle_studio_key(proxy: Any, key: int, mod: int = 0) -> Optional[str]:
    """
    Handle Pygame KEYDOWN events for Mode Studio choreography mute toggles.
    Bindings (plain Ctrl only; Shift/Alt/Meta combinations are ignored):
      - Ctrl+B, Ctrl+L, Ctrl+S, Ctrl+T, Ctrl+M: toggle beat, level, spectrum, transient, macro
      - Ctrl+0: clear all mutes
    Returns a status toast message if handled, else None.
    """
    import pygame

    if not (mod & pygame.KMOD_CTRL):
        return None
    if mod & (pygame.KMOD_SHIFT | pygame.KMOD_ALT | getattr(pygame, "KMOD_META", 0)):
        return None

    if key == getattr(pygame, CLEAR_MUTES_KEY, None):
        proxy.clear_mutes()
        return "CHOREOGRAPHY MUTES: CLEARED"

    channel: Optional[str] = None
    for key_name, ch_name in CTRL_KEY_MAP.items():
        if key == getattr(pygame, key_name, None):
            channel = ch_name
            break

    if channel is None:
        return None

    state = proxy.toggle_mute(channel)
    active = ", ".join(proxy.muted) if proxy.muted else "none"
    return f"MUTE [{channel.upper()}]: {'ON' if state else 'OFF'} (muted: [{active}])"
