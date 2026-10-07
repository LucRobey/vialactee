"""
config/room_bounds.py - Reads the physical room extent from the segments layout file.

This is the OUTSIDE-the-wall adapter: it reads project configuration and hands plain
numbers to the transition sector (InstallationSnapshot.room_bounds), so the sector
itself never touches config files.
"""
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from config.Configuration_manager import resolve_segments_file_path

logger = logging.getLogger("room_bounds")


def compute_room_bounds(infos: Optional[Dict[str, Any]] = None) -> Optional[Tuple[int, int]]:
    """
    Returns (max_x, max_y) of the installation from the active segments file,
    or None when it cannot be determined (callers keep their defaults).
    """
    try:
        seg_path = resolve_segments_file_path(infos)
        if not os.path.exists(seg_path):
            return None
        with open(seg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        segs = []
        for k, v in data.items():
            if k.startswith("segs_") and isinstance(v, list):
                segs.extend(v)
        if not segs and isinstance(data.get("segments"), list):
            segs = data["segments"]
        max_x = 0
        max_y = 0
        for s in segs:
            if isinstance(s, dict) and "start" in s and "size" in s and "step" in s:
                x0 = int(s["start"].get("x", 0))
                y0 = int(s["start"].get("y", 0))
                step_x = int(s["step"].get("x", 0))
                step_y = int(s["step"].get("y", 0))
                size = int(s.get("size", 0))
                max_x = max(max_x, x0, x0 + (size * step_x))
                max_y = max(max_y, y0, y0 + (size * step_y))
        if max_x > 0 and max_y > 0:
            return max_x, max_y
        return None
    except Exception as e:
        logger.debug(f"Could not load dynamic room bounds: {e}")
        return None
