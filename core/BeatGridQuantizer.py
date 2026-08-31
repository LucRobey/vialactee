"""
core/BeatGridQuantizer.py

Decoupled Beat Grid Quantization and O(1) Motif Pattern Recognition layer.
Quantizes a continuous NoteEvent stream onto live beat tracker grid ticks
and detects repeating melodic motifs in real-time.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

@dataclass
class MotifPattern:
    notes: tuple        # tuple of note indices (e.g. (9, -1, 4, -1))
    length_beats: int   # length of motif in beats
    occurrences: int    # number of times it has repeated
    last_beat: int      # the last beat index where it ended

class BeatGridQuantizer:
    """
    Decoupled software layer that quantizes continuous NoteEvents onto the beat tracker's
    phase-aligned grid subdivisions (ticks) and monitors the resulting discrete grid
    for repeating melodic motifs.
    """

    def __init__(self, subdivisions: int = 4, grid_history_len: int = 64):
        """
        Parameters
        ----------
        subdivisions : int
            Number of ticks per beat. E.g., 4 ticks per beat = 16th note grid (in 4/4 time).
            2 ticks per beat = 8th note grid.
        grid_history_len : int
            Number of beats to keep in the rolling grid history buffer.
        """
        self.subdivisions = subdivisions
        self.grid_history_len = grid_history_len
        
        # Grid stores note events: grid[(beat_idx, tick_idx)] = NoteEvent
        self.grid: Dict[Tuple[int, int], Any] = {}
        
        # Track the active beat indices to prune old grid data
        self.active_beats: List[int] = []
        
        # Active repeating motifs
        self.detected_motifs: Dict[int, MotifPattern] = {}  # length_beats -> MotifPattern
        self.last_quantized_key: Optional[Tuple[int, int]] = None

    def quantize(self, event: Any, beat_count: int, beat_phase: float) -> Optional[Tuple[Tuple[int, int], Any]]:
        """
        Quantizes a NoteEvent onto the nearest beat grid tick.
        If multiple events fall into the same tick, aggregates them by keeping the highest confidence.

        Parameters
        ----------
        event : NoteEvent
            Continuous event from LightweightPitchDetector.
        beat_count : int
            Current continuous beat counter from the tracker.
        beat_phase : float
            Current continuous fractional beat phase [0.0 - 1.0) from the tracker.

        Returns
        -------
        tuple or None
            If a new grid cell is populated, returns ((beat_idx, tick_idx), event), otherwise None.
        """
        if beat_count < 0 or beat_phase < 0.0 or beat_phase >= 1.0:
            return None

        # Map beat phase to nearest tick index
        tick_idx = int(round(beat_phase * self.subdivisions))
        quantized_beat = beat_count

        # Handle phase wrap-around (e.g. phase of 0.98 wraps to tick 0 of the next beat)
        if tick_idx == self.subdivisions:
            tick_idx = 0
            quantized_beat += 1

        grid_key = (quantized_beat, tick_idx)

        # Skip adding silence events to keep grid clean, but we can read empty cells as silence
        if event.type == 'silence':
            return None

        # Add quantized beat to our active tracker
        if quantized_beat not in self.active_beats:
            self.active_beats.append(quantized_beat)
            self.active_beats.sort()
            self._prune_old_beats()

        # Aggregation: if the cell already contains an event, keep the loudest/highest confidence
        existing = self.grid.get(grid_key)
        if existing is None or event.confidence > existing.confidence:
            self.grid[grid_key] = event
            self.last_quantized_key = grid_key
            return grid_key, event

        return None

    def get_note_at(self, beat_idx: int, tick_idx: int) -> int:
        """Get the dominant note index (0-11) at a grid cell, or -1 if silent."""
        ev = self.grid.get((beat_idx, tick_idx))
        if ev is None:
            return -1
        return ev.note1

    def _prune_old_beats(self) -> None:
        """Remove beats older than grid_history_len to prevent memory growth."""
        if len(self.active_beats) > self.grid_history_len:
            oldest_cutoff = self.active_beats[-self.grid_history_len]
            keys_to_remove = [k for k in self.grid.keys() if k[0] < oldest_cutoff]
            for k in keys_to_remove:
                self.grid.pop(k, None)
            self.active_beats = [b for b in self.active_beats if b >= oldest_cutoff]

    def _levenshtein_distance(self, seq1: Tuple[int, ...], seq2: Tuple[int, ...]) -> int:
        if len(seq1) < len(seq2):
            return self._levenshtein_distance(seq2, seq1)
        if len(seq2) == 0:
            return len(seq1)
        
        previous_row = list(range(len(seq2) + 1))
        for i, c1 in enumerate(seq1):
            current_row = [i + 1]
            for j, c2 in enumerate(seq2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]

    def _find_best_transposed_levenshtein(self, seq1: Tuple[int, ...], seq2: Tuple[int, ...]) -> Tuple[int, int]:
        """
        Finds the minimum Levenshtein distance between seq1 and seq2 under any 12-semitone transposition.
        Returns (min_dist, best_offset).
        """
        if len(seq1) == 0 or len(seq2) == 0:
            return max(len(seq1), len(seq2)), 0
            
        min_dist = 999999
        best_offset = 0
        
        # Try all 12 semitone transpositions
        for offset in range(12):
            transposed_seq2 = tuple((n + offset) % 12 if n != -1 else -1 for n in seq2)
            dist = self._levenshtein_distance(seq1, transposed_seq2)
            if dist < min_dist:
                min_dist = dist
                best_offset = offset
                
        return min_dist, best_offset

    def _collapse_duplicates(self, seq: List[int]) -> Tuple[int, ...]:
        collapsed = []
        for n in seq:
            if not collapsed or collapsed[-1] != n:
                collapsed.append(n)
        return tuple(collapsed)

    def detect_motifs(self, current_beat: int, min_len: int = 4, max_len: int = 8) -> List[MotifPattern]:
        """
        Runs an O(1) sliding window pattern matching search over the recent beat grid
        history to detect repeating melodic motifs using transposition-aware Levenshtein distance.

        Parameters
        ----------
        current_beat : int
            The current beat index.
        min_len : int
            Minimum motif length in beats (e.g. 4 beats = 1 bar in 4/4).
            Must be a multiple of 2 or 4 for standard musical phrases.
        max_len : int
            Maximum motif length in beats (e.g. 8 beats = 2 bars in 4/4).

        Returns
        -------
        List[MotifPattern]
            List of currently active repeating MotifPatterns.
        """
        new_motifs = []
        
        # We search for repeating patterns of lengths in [min_len, max_len]
        for length in [4, 8]:  # 1-bar or 2-bar motifs are standard in music
            if current_beat < length * 2:
                continue

            # Extract notes of the most recent window: W_curr = [current_beat - length + 1, current_beat]
            curr_notes = []
            for b in range(current_beat - length + 1, current_beat + 1):
                for t in range(self.subdivisions):
                    curr_notes.append(self.get_note_at(b, t))
            curr_tuple = tuple(curr_notes)

            # Skip empty (all silence) windows
            if all(n == -1 for n in curr_tuple):
                continue

            # Compare W_curr with previous non-overlapping windows:
            # W_prev = [current_beat - 2*length + 1, current_beat - length]
            prev_notes = []
            for b in range(current_beat - 2 * length + 1, current_beat - length + 1):
                for t in range(self.subdivisions):
                    prev_notes.append(self.get_note_at(b, t))
            prev_tuple = tuple(prev_notes)

            # Extract active (non-silent) notes to allow robust rhythm-independent matching
            curr_active = [n for n in curr_tuple if n != -1]
            prev_active = [n for n in prev_tuple if n != -1]

            # We require a meaningful melody of at least 3 active notes
            if len(curr_active) < 3 or len(prev_active) < 3:
                continue

            # Collapse consecutive duplicates for rhythm-independent melodic contour matching
            curr_coll = self._collapse_duplicates(curr_active)
            prev_coll = self._collapse_duplicates(prev_active)

            # Check raw active sequences Levenshtein distance
            raw_dist, raw_offset = self._find_best_transposed_levenshtein(tuple(curr_active), tuple(prev_active))
            max_len_raw = max(len(curr_active), len(prev_active))
            raw_ratio = raw_dist / max_len_raw

            # Check collapsed sequences Levenshtein distance
            coll_dist, coll_offset = self._find_best_transposed_levenshtein(curr_coll, prev_coll)
            max_len_coll = max(len(curr_coll), len(prev_coll))
            coll_ratio = coll_dist / max_len_coll if max_len_coll > 0 else 1.0

            # Match criteria:
            # - Raw active sequences have a normalized edit distance <= 0.3 (allows up to 30% jitter/errors)
            # OR
            # - Collapsed sequences have a normalized edit distance <= 0.25 (highly similar melodic contours)
            is_match = False
            
            if raw_ratio <= 0.3:
                is_match = True
            elif len(curr_coll) >= 3 and len(prev_coll) >= 3 and coll_ratio <= 0.25:
                is_match = True

            if is_match:
                # If matched, we increment or register the motif
                existing = self.detected_motifs.get(length)
                occurrences = 2
                
                # Check if this is a continuation of an already repeating motif
                if existing is not None and existing.last_beat == current_beat - length:
                    occurrences = existing.occurrences + 1
                
                # We store the active notes list in MotifPattern
                motif = MotifPattern(
                    notes=tuple(curr_active),
                    length_beats=length,
                    occurrences=occurrences,
                    last_beat=current_beat
                )
                self.detected_motifs[length] = motif
                new_motifs.append(motif)
            else:
                # Decay occurrences if not matched in this cycle
                existing = self.detected_motifs.get(length)
                if existing is not None and current_beat - existing.last_beat > length * 2:
                    self.detected_motifs.pop(length, None)

        return new_motifs


    def get_melody_string(self, beat_idx: int) -> str:
        """Returns a string representation of notes inside a beat for easy console logging."""
        notes = []
        for t in range(self.subdivisions):
            n = self.get_note_at(beat_idx, t)
            if n == -1:
                notes.append(".")
            else:
                from LightweightPitchDetector import NOTE_NAMES
                notes.append(NOTE_NAMES[n])
        return " ".join(notes)
