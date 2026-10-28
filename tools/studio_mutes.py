"""
tools/studio_mutes.py
Mode Studio HUD formatter and Pygame keyboard shortcut handler for DriverMuteProxy.
"""
from typing import Any, Optional


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
    Bindings:
      - F1..F5 (or Shift+B, Shift+L, S, T, M): toggle beat, level, spectrum, transient, macro
      - 0 (K_0): clear all mutes
    Returns a status toast message if handled, else None.
    """
    import pygame

    if key == pygame.K_0:
        proxy.clear_mutes()
        return "CHOREOGRAPHY MUTES: CLEARED"

    shift = bool(mod & pygame.KMOD_SHIFT)
    channel_by_key = {
        pygame.K_F1: "beat",
        pygame.K_F2: "level",
        pygame.K_F3: "spectrum",
        pygame.K_F4: "transient",
        pygame.K_F5: "macro",
        pygame.K_s: "spectrum",
        pygame.K_t: "transient",
        pygame.K_m: "macro",
    }
    if shift and key == pygame.K_b:
        channel = "beat"
    elif shift and key == pygame.K_l:
        channel = "level"
    else:
        channel = channel_by_key.get(key)

    if channel is None:
        return None

    state = proxy.toggle_mute(channel)
    active = ", ".join(proxy.muted) if proxy.muted else "none"
    return f"MUTE [{channel.upper()}]: {'ON' if state else 'OFF'} (muted: [{active}])"
