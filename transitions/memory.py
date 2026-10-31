"""
transitions/memory.py - Per-Segment & Per-Zone Recency History Ring.

Maintains in-memory history of the last `memoryDepth` transitions (most recent first,
including the boot cast from `allocate_initial`).
Computes recency penalties with fixed exponential decay (0.75^k) and checks exact repeats.
Strictly sealed: zero file I/O, zero external imports. Complies with AXIOM-07.
"""

from collections import deque
from typing import Deque, Dict, Optional, Sequence, Tuple

DECAY: float = 0.75


class TransitionMemory:
    """In-memory ring buffer tracking recent mode and grouping selections."""

    def __init__(self, depth: int = 8) -> None:
        self._depth: int = max(0, int(depth))
        self._segment_history: Dict[str, Deque[str]] = {}
        self._zone_grouping_history: Dict[str, Deque[str]] = {}
        self._cast_history: Deque[Dict[str, str]] = deque()

    @property
    def depth(self) -> int:
        return self._depth

    def __len__(self) -> int:
        return len(self._cast_history)

    def set_depth(self, depth: int) -> None:
        """Update memory depth and trim existing history rings."""
        self._depth = max(0, int(depth))
        if self._depth == 0:
            self.clear()
            return
        while len(self._cast_history) > self._depth:
            self._cast_history.pop()
        for hist in self._segment_history.values():
            while len(hist) > self._depth:
                hist.pop()
        for hist in self._zone_grouping_history.values():
            while len(hist) > self._depth:
                hist.pop()

    def clear(self) -> None:
        """Reset all history rings."""
        self._segment_history.clear()
        self._zone_grouping_history.clear()
        self._cast_history.clear()

    def record(
        self,
        cast: Dict[str, str],
        groupings_by_zone: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record an emitted segment->mode cast and zone->grouping map (most recent first)."""
        if self._depth <= 0 or not cast:
            return

        snapshot = dict(cast)
        self._cast_history.appendleft(snapshot)
        while len(self._cast_history) > self._depth:
            self._cast_history.pop()

        for seg_id, mode_name in snapshot.items():
            ring = self._segment_history.get(seg_id)
            if ring is None:
                ring = deque()
                self._segment_history[seg_id] = ring
            ring.appendleft(mode_name)
            while len(ring) > self._depth:
                ring.pop()

        if groupings_by_zone:
            for zone_name, grouping_id in groupings_by_zone.items():
                zring = self._zone_grouping_history.get(zone_name)
                if zring is None:
                    zring = deque()
                    self._zone_grouping_history[zone_name] = zring
                zring.appendleft(grouping_id)
                while len(zring) > self._depth:
                    zring.pop()

    def grouping_weight(
        self,
        zone_name: str,
        grouping_id: str,
        catalogue_weight: float,
        repeat_penalty: float,
    ) -> float:
        """
        Compute decayed grouping weight:
        w = catalogue_weight / (1 + repeatPenalty * sum_k 0.75^k * [grouping(k) == grouping_id])
        """
        if self._depth <= 0 or repeat_penalty <= 0.0:
            return float(catalogue_weight)
        zring = self._zone_grouping_history.get(zone_name)
        if not zring:
            return float(catalogue_weight)
        recency_sum = 0.0
        factor = 1.0
        for idx, past_gid in enumerate(zring):
            if idx >= self._depth:
                break
            if past_gid == grouping_id:
                recency_sum += factor
            factor *= DECAY
        return float(catalogue_weight) / (1.0 + float(repeat_penalty) * recency_sum)

    def segment_recency_sum(self, segment_id: str, mode_name: str) -> float:
        """Compute sum_{k < memoryDepth} 0.75^k * [mode(s, k) == mode_name]."""
        if self._depth <= 0:
            return 0.0
        ring = self._segment_history.get(segment_id)
        if not ring:
            return 0.0
        total = 0.0
        factor = 1.0
        for idx, past_mode in enumerate(ring):
            if idx >= self._depth:
                break
            if past_mode == mode_name:
                total += factor
            factor *= DECAY
        return total

    def variety_factor(
        self,
        group_segments: Sequence[str],
        mode_name: str,
        repeat_penalty: float,
    ) -> float:
        """
        Compute variety(m, g) = 1 / (1 + repeatPenalty * mean_{s in g} sum_{k < memoryDepth} 0.75^k * [mode(s,k) = m]).
        """
        if self._depth <= 0 or repeat_penalty <= 0.0 or not group_segments:
            return 1.0
        mean_recency = sum(self.segment_recency_sum(s, mode_name) for s in group_segments) / len(group_segments)
        return 1.0 / (1.0 + float(repeat_penalty) * mean_recency)

    def is_exact_repeat(self, cast: Dict[str, str]) -> bool:
        """Return True if `cast` equals any of the last `memoryDepth` recorded casts."""
        if self._depth <= 0 or not cast or not self._cast_history:
            return False
        for past in self._cast_history:
            if past == cast:
                return True
        return False

    def segment_history(self, segment_id: str) -> Tuple[str, ...]:
        """Return recorded modes for a segment (most recent first)."""
        ring = self._segment_history.get(segment_id)
        return tuple(ring) if ring else ()

    def zone_grouping_history(self, zone_name: str) -> Tuple[str, ...]:
        """Return recorded grouping IDs for a zone (most recent first)."""
        ring = self._zone_grouping_history.get(zone_name)
        return tuple(ring) if ring else ()
