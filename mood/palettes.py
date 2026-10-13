"""
mood/palettes.py - Curated master colour palettes.

Each palette consists of 4 8-bit RGB color triplets:
[Primary, Secondary, Accent, Background/Highlight]
"""
from typing import Dict, Tuple

DEFAULT_PALETTE = "Cyberpunk"

PALETTES: Dict[str, Tuple[Tuple[int, int, int], ...]] = {
    "Cyberpunk": (
        (0, 240, 255),    # Neon Cyan
        (255, 0, 128),    # Hot Magenta
        (60, 0, 180),     # Deep Indigo
        (0, 100, 255),    # Electric Blue
    ),
    "Solar Ember": (
        (255, 30, 0),     # Deep Crimson
        (255, 140, 0),    # Bright Amber
        (255, 215, 0),    # Pure Gold
        (255, 240, 200),  # Warm White
    ),
    "Deep Ocean": (
        (0, 200, 180),    # Teal
        (0, 255, 150),    # Aquamarine
        (0, 80, 200),     # Ocean Blue
        (10, 20, 80),     # Midnight Blue
    ),
    "Ethereal": (
        (180, 130, 255),  # Lavender
        (130, 255, 200),  # Mint Green
        (255, 180, 160),  # Soft Peach
        (220, 230, 255),  # Moonlight White
    ),
    "Neon Acid": (
        (57, 255, 20),    # Toxic Green
        (230, 255, 0),    # Acid Yellow
        (180, 0, 255),    # Electric Violet
        (255, 16, 240),   # Neon Pink
    ),
    "Monochrome Chrome": (
        (255, 255, 255),  # Pure White
        (180, 190, 205),  # Cool Silver
        (70, 75, 85),     # Deep Slate
        (200, 230, 255),  # Ice Blue
    ),
}
