"""
core/GlobalMoodManager.py - Master Color Harmony & Smooth Palette Transitions.

Curates master color palettes and orchestrates continuous cosine cross-fades
so visual modes running simultaneously maintain aesthetic color harmony.

Guarantees:
- AXIOM-01: Execution time <= 0.01 ms per frame (DSP frame budget).
- AXIOM-02: Zero dynamic heap allocations in hot-path update().
- AXIOM-07: Code length <= 500 lines.
"""

from typing import Dict, List, Tuple, Optional, Any
import math
import numpy as np


# Curated Master Color Palettes
# Each palette consists of 4 8-bit RGB color triplets:
# [Primary, Secondary, Accent, Background/Highlight]
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


class GlobalMoodManager:
    """
    Central manager for global lighting moods and palette crossfades.
    Provides singleton access and guaranteed zero-allocation runtime performance.
    """

    _instance: Optional["GlobalMoodManager"] = None

    @classmethod
    def get_instance(cls, initial_palette: str = "Cyberpunk") -> "GlobalMoodManager":
        """Singleton accessor for modes and orchestrators."""
        if cls._instance is None:
            cls._instance = cls(initial_palette=initial_palette)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Testing utility to reset singleton state."""
        cls._instance = None

    def __init__(self, initial_palette: str = "Cyberpunk", transition_duration: float = 2.0) -> None:
        """
        Initialize the Global Mood Manager. Pre-allocates all buffers.

        Args:
            initial_palette: Name of starting curated palette.
            transition_duration: Default crossfade duration in seconds (2.0s standard).
        """
        GlobalMoodManager._instance = self

        self._palette_names: List[str] = list(PALETTES.keys())
        self._current_palette_name: str = initial_palette if initial_palette in PALETTES else "Cyberpunk"
        self._target_palette_name: str = self._current_palette_name
        self._default_duration: float = max(0.01, float(transition_duration))
        self._transition_duration: float = self._default_duration
        self._timer: float = self._transition_duration
        self._blend_progress: float = 1.0
        self._is_transitioning: bool = False

        # Pre-cache all palettes as static float32 arrays
        self._cached_palettes: Dict[str, np.ndarray] = {
            name: np.array(colors, dtype=np.float32)
            for name, colors in PALETTES.items()
        }

        # Pre-allocated zero-allocation buffers (AXIOM-02)
        self._from_colors: np.ndarray = np.array(self._cached_palettes[self._current_palette_name], copy=True)
        self._to_colors: np.ndarray = np.array(self._cached_palettes[self._current_palette_name], copy=True)
        self._diff_colors: np.ndarray = np.zeros((4, 3), dtype=np.float32)
        self._blend_scratch: np.ndarray = np.zeros((4, 3), dtype=np.float32)
        self._term2_scratch: np.ndarray = np.zeros((4, 3), dtype=np.float32)
        self._mood_colors: np.ndarray = np.array(PALETTES[self._current_palette_name], dtype=np.int32)

    def set_palette(self, palette_name: str, duration: Optional[float] = None) -> bool:
        """
        Initiate a smooth cosine cross-fade to the designated palette.

        Args:
            palette_name: Target palette name.
            duration: Duration of crossfade in seconds. Defaults to 2.0s.

        Returns:
            True if palette transition was queued/started, False if palette unknown.
        """
        if palette_name not in self._cached_palettes:
            return False

        if palette_name == self._target_palette_name:
            return True

        # Snapshot current blended colors as starting point
        self._from_colors[:] = self._mood_colors
        self._to_colors[:] = self._cached_palettes[palette_name]
        np.subtract(self._to_colors, self._from_colors, out=self._diff_colors)
        self._target_palette_name = palette_name
        self._transition_duration = max(0.01, float(duration if duration is not None else self._default_duration))
        self._timer = 0.0
        self._blend_progress = 0.0
        self._is_transitioning = True
        return True

    def next_palette(self, duration: Optional[float] = None) -> str:
        """Cycle to the next curated palette in order."""
        try:
            cur_idx = self._palette_names.index(self._target_palette_name)
            next_idx = (cur_idx + 1) % len(self._palette_names)
        except ValueError:
            next_idx = 0
        target = self._palette_names[next_idx]
        self.set_palette(target, duration=duration)
        return target

    def set_palette_for_scene(self, scene: Any, duration: Optional[float] = None) -> bool:
        """
        Align color mood with MusicalContextEngine macro scenes.
        """
        scene_str = getattr(scene, "value", str(scene)).upper()
        if scene_str in ("CHILL", "DEEP_AMBIENT", "FLOATING_PULSE"):
            return self.set_palette("Deep Ocean", duration=duration)
        elif scene_str in ("GROOVE", "THE_POCKET", "CHAOTIC_FILL"):
            return self.set_palette("Cyberpunk", duration=duration)
        elif scene_str in ("BUILDUP", "PRE_DROP_BUILDUP"):
            return self.set_palette("Solar Ember", duration=duration)
        elif scene_str in ("DROP_IMPACT",):
            return self.set_palette("Neon Acid", duration=duration)
        return False

    def update(self, dt: float) -> None:
        """
        Advance the smooth cosine crossfade timer and interpolate colors in-place.
        Strictly zero dynamic heap allocations (AXIOM-02).
        Execution time <= 0.01 ms (AXIOM-01).

        Args:
            dt: Delta time in seconds since previous frame.
        """
        if not self._is_transitioning:
            return

        self._timer += dt
        if self._timer >= self._transition_duration:
            self._timer = self._transition_duration
            self._blend_progress = 1.0
            self._is_transitioning = False
            self._current_palette_name = self._target_palette_name
            self._mood_colors[:] = self._cached_palettes[self._target_palette_name]
            return

        progress = self._timer / self._transition_duration
        self._blend_progress = progress

        # Cosine crossfade weighting: 0.5 * (1.0 - cos(pi * progress))
        w = np.float32(0.5 * (1.0 - math.cos(math.pi * progress)))

        # Zero-allocation arithmetic: mood = from + diff * w
        np.multiply(self._diff_colors, w, out=self._blend_scratch)
        np.add(self._from_colors, self._blend_scratch, out=self._mood_colors, casting='unsafe')

    @property
    def mood_colors(self) -> np.ndarray:
        """Current blended RGB color array (shape: (4, 3), dtype: np.int32)."""
        return self._mood_colors

    @property
    def current_palette(self) -> str:
        """Active palette name (or outgoing palette during transition)."""
        return self._current_palette_name

    @property
    def target_palette(self) -> str:
        """Target palette name being blended into."""
        return self._target_palette_name

    @property
    def blend_progress(self) -> float:
        """Progress of active crossfade in [0.0, 1.0]."""
        return self._blend_progress

    @property
    def is_transitioning(self) -> bool:
        """True if a palette crossfade is currently active."""
        return self._is_transitioning

    @property
    def palette_names(self) -> List[str]:
        """List of available palette names."""
        return list(self._palette_names)

    @property
    def primary_color(self) -> np.ndarray:
        """Primary theme color (RGB)."""
        return self._mood_colors[0]

    @property
    def secondary_color(self) -> np.ndarray:
        """Secondary complementary theme color (RGB)."""
        return self._mood_colors[1]

    @property
    def accent_color(self) -> np.ndarray:
        """Accent highlight theme color (RGB)."""
        return self._mood_colors[2]

    @property
    def background_color(self) -> np.ndarray:
        """Subtle/background theme color (RGB)."""
        return self._mood_colors[3]
