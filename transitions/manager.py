"""
transitions/manager.py - Music Matchmaker, Probabilistic Cohort Allocator, & Downbeat Quantizer.
Evaluates musical context, allocates modes with weighted lotteries, and quantizes transitions.
Guarantees: AXIOM-01 (<= 0.01 ms), AXIOM-02 (zero heap alloc), AXIOM-07 (<= 500 lines).
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math
import random
import time

from transitions.mode_dna import MODE_DNA, DEFAULT_MODE_DNA, get_mode_dna
from transitions.stagger import (
    StaggerPattern,
    discover_segment_cohorts,
    generate_staggered_configs,
    select_stagger_pattern,
)


class CohortPattern(str, Enum):
    """Structural allocation pattern for segment cohorts."""
    DIVERSE = "DIVERSE"
    SYMMETRIC_PAIRS = "SYMMETRIC_PAIRS"
    UNISON = "UNISON"


TRANSITION_TECHNIQUES: Dict[str, Dict[str, Any]] = {
    "smooth_cosine_crossfade": {"type": "fade_in_out", "duration": 2.0},
    "directional_wipe": {"type": "vertical_wipe", "duration": 1.2},
    "transient_blip": {"type": "explosion", "duration": 0.4},
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely converts val to float; coalesces None and invalid types to default."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class LocalTransitionManager:
    """
    Evaluates musical intent, draws weighted lottery candidates, and quantizes
    non-rigid segment transitions to musical downbeats.
    """

    def __init__(self, mode_master: Any, listener: Any) -> None:
        """
        Initialize the LocalTransitionManager.

        Args:
            mode_master: Reference to the master Mode_master instance.
            listener: Reference to the global audio Listener.
        """
        self.mode_master = mode_master
        self.listener = listener

        self._pending_transition: Optional[Dict[str, Any]] = None
        self._downbeat_timeout: float = 1.20
        self._dwell_timer: float = 0.0

        # Cache available modes across all segments
        self._cached_available_modes: List[str] = list(MODE_DNA.keys())

    def update(self, dt: float) -> None:
        """
        Advance steady-state timers and check downbeat trigger.
        Zero dynamic heap allocations in steady-state (AXIOM-02).
        Execution <= 0.01 ms (AXIOM-01).

        Args:
            dt: Delta time in seconds since previous frame.
        """
        self._dwell_timer += dt

        # Check Downbeat Quantization for Pending Transition
        if self._pending_transition is not None:
            td = getattr(self.mode_master, "transition_director", None)
            if td is not None and getattr(td, "is_in_transition", False) is True:
                # Wait for ongoing transition to finish before starting queued transition
                return

            phase = _safe_float(getattr(self.listener, "beat_phase", 0.0), 0.0)
            is_beat = bool(getattr(self.listener, "is_beat", False))
            self._pending_transition["elapsed"] = self._pending_transition.get("elapsed", 0.0) + dt
            elapsed = self._pending_transition["elapsed"]

            is_beat_trustworthy = _safe_float(getattr(self.listener, "beat_trust", 0.0), 0.0) >= 0.20
            downbeat_hit = (phase < 0.05 and is_beat_trustworthy) or is_beat
            if downbeat_hit or elapsed >= self._downbeat_timeout:
                allocation = self._pending_transition["allocation"]
                config = self._pending_transition["config"]
                self._pending_transition = None
                self._execute_transition(allocation, config)

    # =========================================================================
    # 1. MUSIC MATCHMAKER: Live Context -> Target DNA
    # =========================================================================

    def evaluate_target_dna(self, context: Optional[Any] = None) -> Dict[str, float]:
        """
        Translates live MusicalContextEngine metrics into a target mode DNA vector.

        Returns:
            Dict[str, float] with 'energy', 'punch', 'rhythm', and 'complexity' in [0.0, 1.0].
        """
        ctx = context
        if ctx is None and hasattr(self.listener, "context"):
            ctx = getattr(self.listener, "context", None)

        if ctx is None:
            raw_power = _safe_float(getattr(self.listener, "asserved_total_power", 0.5), 0.5)
            raw_salience = _safe_float(getattr(self.listener, "rhythm_salience", 0.5), 0.5)
            raw_trust = _safe_float(getattr(self.listener, "beat_trust", 0.5), 0.5)
            return {
                "energy": max(0.0, min(1.0, raw_power)),
                "punch": max(0.0, min(1.0, raw_salience)),
                "rhythm": max(0.0, min(1.0, raw_trust)),
                "complexity": 0.50,
            }

        e = _safe_float(getattr(ctx, "energy", 0.50), 0.50)
        s = _safe_float(getattr(ctx, "salience", 0.50), 0.50)
        t = _safe_float(getattr(ctx, "beat_trust", 0.50), 0.50)
        nov = _safe_float(getattr(ctx, "novelty", 0.40), 0.40)
        tension = _safe_float(getattr(ctx, "tension", 0.30), 0.30)
        is_drop = bool(getattr(ctx, "is_drop_impact", False))
        is_sync = bool(getattr(ctx, "is_syncopated", False))

        target_energy = max(0.0, min(1.0, e))
        target_punch = 1.0 if is_drop else max(0.0, min(1.0, 0.60 * s + 0.40 * e))
        target_rhythm = max(0.0, min(1.0, 0.70 * t + 0.30 * s))
        target_complexity = max(0.0, min(1.0, 0.40 * nov + 0.30 * tension + (0.30 if is_sync else 0.10)))

        return {
            "energy": round(target_energy, 4),
            "punch": round(target_punch, 4),
            "rhythm": round(target_rhythm, 4),
            "complexity": round(target_complexity, 4),
        }

    # =========================================================================
    # 2. WEIGHTED LOTTERY: Probabilistic Mode Selection
    # =========================================================================

    def select_mode_lottery(
        self,
        candidate_pool: List[str],
        target_dna: Optional[Dict[str, float]] = None,
        current_mode: Optional[str] = None,
        spatial_orientation: Optional[str] = None,
        penalty_mode: Optional[str] = None,
    ) -> str:
        """
        Draws a mode from candidates using Euclidean DNA distance weighting.
        Never strictly zero; preserves freshness and serendipitous surprises.
        """
        if not candidate_pool:
            return "Rainbow"

        target = target_dna if isinstance(target_dna, dict) else self.evaluate_target_dna()
        et = _safe_float(target.get("energy", 0.5), 0.5)
        pt = _safe_float(target.get("punch", 0.5), 0.5)
        rt = _safe_float(target.get("rhythm", 0.5), 0.5)
        ct = _safe_float(target.get("complexity", 0.5), 0.5)

        weights: List[float] = []
        for name in candidate_pool:
            dna = get_mode_dna(name)
            de = dna["energy"] - et
            dp = dna["punch"] - pt
            dr = dna["rhythm"] - rt
            dc = dna["complexity"] - ct
            dist_sq = (de * de) + (dp * dp) + (dr * dr) + (dc * dc)

            w = 1.0 / (1.0 + 4.0 * dist_sq)

            # Spatial role filtering / soft penalty
            if spatial_orientation is not None:
                role = dna.get("spatial_role", "both")
                if role != "both" and role != spatial_orientation:
                    w *= 0.15

            # Recency penalty: discourage immediately repeating current mode
            if current_mode is not None and name.lower() == current_mode.lower():
                w *= 0.20

            # Affinity penalty: discourage mode B copying mode A in pair allocation
            if penalty_mode is not None and name.lower() == penalty_mode.lower():
                w *= 0.05

            weights.append(max(0.001, w))

        return random.choices(candidate_pool, weights=weights, k=1)[0]

    # =========================================================================
    # 3. FLEXIBLE COHORT ALLOCATION: Non-rigid Symmetries & Unison
    # =========================================================================

    def choose_cohort_pattern(self, context: Optional[Any] = None) -> CohortPattern:
        """
        Probabilistically chooses a structural allocation pattern:
        - UNISON: Boosted during high-energy drop impacts and risers.
        - SYMMETRIC_PAIRS: Boosted during rhythmic locked grooves.
        - DIVERSE: General atmospheric, ambient, or exploratory textures.
        """
        ctx = context or getattr(self.listener, "context", None)
        p_unison = 0.20
        p_sym = 0.35
        p_div = 0.45

        if ctx is not None:
            raw_scene = getattr(ctx, "scene", getattr(ctx, "current_regime", None))
            scene_str = str(getattr(raw_scene, "value", raw_scene) or "").upper()
            if getattr(ctx, "is_drop_impact", False):
                p_unison, p_sym, p_div = 0.55, 0.30, 0.15
            elif scene_str in ("BUILDUP", "PRE_DROP_BUILDUP"):
                p_unison, p_sym, p_div = 0.40, 0.40, 0.20
            elif getattr(ctx, "is_syncopated", False) or getattr(ctx, "is_locked", False):
                p_unison, p_sym, p_div = 0.15, 0.45, 0.40
            elif scene_str in ("CHILL", "DEEP_AMBIENT", "FLOATING_PULSE"):
                p_unison, p_sym, p_div = 0.10, 0.40, 0.50

        return random.choices(
            [CohortPattern.DIVERSE, CohortPattern.SYMMETRIC_PAIRS, CohortPattern.UNISON],
            weights=[p_div, p_sym, p_unison],
            k=1,
        )[0]

    def allocate_cohort_modes(
        self,
        segment_names: List[str],
        target_dna: Optional[Dict[str, float]] = None,
        pattern: Optional[CohortPattern] = None,
        spatial_orientation: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Allocates modes across a cohort of segments using the selected pattern.
        Supports symmetric pairings (ABAB, ABBA, ABA) and unison without rigidity.
        """
        if not segment_names:
            return {}

        target = target_dna or self.evaluate_target_dna()
        chosen_pattern = pattern or self.choose_cohort_pattern()
        n = len(segment_names)

        # Get pool of candidate modes available on these segments
        pool = self._get_candidate_pool_for_segments(segment_names)

        allocation: Dict[str, str] = {}

        if chosen_pattern == CohortPattern.UNISON or n == 1:
            # All segments run identical winning mode
            mode_unison = self.select_mode_lottery(pool, target, spatial_orientation=spatial_orientation)
            for seg in segment_names:
                allocation[seg] = mode_unison
            return allocation

        if chosen_pattern == CohortPattern.SYMMETRIC_PAIRS:
            # 2 distinct modes A and B mapped symmetrically
            mode_a = self.select_mode_lottery(pool, target, spatial_orientation=spatial_orientation)
            pool_b = [m for m in pool if m.lower() != mode_a.lower()] or pool
            mode_b = self.select_mode_lottery(pool_b, target, spatial_orientation=spatial_orientation, penalty_mode=mode_a)

            if n == 4:
                # For 4 pillars: flip between alternating (ABAB) and mirror (ABBA)
                if random.random() < 0.50:
                    mapping = [mode_a, mode_b, mode_a, mode_b]
                else:
                    mapping = [mode_a, mode_b, mode_b, mode_a]
                for idx, seg in enumerate(segment_names):
                    allocation[seg] = mapping[idx]
            elif n == 3:
                # 3 segments (e.g. s1, s2, s3): ABA symmetry sandwich
                mapping = [mode_a, mode_b, mode_a]
                for idx, seg in enumerate(segment_names):
                    allocation[seg] = mapping[idx]
            elif n == 2:
                allocation[segment_names[0]] = mode_a
                allocation[segment_names[1]] = mode_b
            else:
                # Arbitrary N: mirror symmetry around center
                for idx, seg in enumerate(segment_names):
                    allocation[seg] = mode_a if (idx % 2 == 0) else mode_b
            return allocation

        # DIVERSE: Every segment draws independently via weighted lottery
        for seg in segment_names:
            cur_mode = self._get_current_mode_name(seg)
            allocation[seg] = self.select_mode_lottery(
                pool, target, current_mode=cur_mode, spatial_orientation=spatial_orientation
            )

        return allocation

    def allocate_all_segments(
        self,
        target_dna: Optional[Dict[str, float]] = None,
        force_pattern: Optional[CohortPattern] = None,
    ) -> Dict[str, str]:
        """
        Partitions the physical installation into natural cohorts (verticals, horizontal rings)
        and allocates modes across all segments.
        """
        target = target_dna or self.evaluate_target_dna()
        verts, rings = self._discover_segment_cohorts()

        full_allocation: Dict[str, str] = {}

        if verts:
            vert_alloc = self.allocate_cohort_modes(
                verts, target_dna=target, pattern=force_pattern, spatial_orientation="vertical"
            )
            full_allocation.update(vert_alloc)

        for ring_cohort in rings:
            if ring_cohort:
                ring_alloc = self.allocate_cohort_modes(
                    ring_cohort, target_dna=target, pattern=force_pattern, spatial_orientation="horizontal"
                )
                full_allocation.update(ring_alloc)

        # Catch any remaining segments not caught in cohorts
        all_segs = [s.name for s in getattr(self.mode_master, "segments_list", [])]
        remainder = [s for s in all_segs if s not in full_allocation]
        if remainder:
            pool = self._get_candidate_pool_for_segments(remainder)
            for s in remainder:
                full_allocation[s] = self.select_mode_lottery(pool, target)

        return full_allocation

    # =========================================================================
    # 4. DOWNBEAT QUANTIZATION & CLEAN TECHNIQUES
    # =========================================================================

    def select_transition_technique(self, context: Optional[Any] = None) -> Dict[str, Any]:
        """
        Picks a clean transition technique based on audio kinetics:
        - Transient blip (0.4s cut/explosion) on high energy or drop impacts.
        - Directional wipe (1.2s vertical/lateral wipe) on rhythmic grooves.
        - Smooth cosine crossfade (2.0s fade_in_out) on ambient/chill sections.
        """
        ctx = context or getattr(self.listener, "context", None)
        if ctx is not None:
            is_drop = bool(getattr(ctx, "is_drop_impact", False))
            energy = _safe_float(getattr(ctx, "energy", 0.0), 0.0)
            salience = _safe_float(getattr(ctx, "salience", 0.0), 0.0)
            is_rhythmic = bool(getattr(ctx, "is_rhythmic", False))
            if is_drop or energy >= 0.85:
                return dict(TRANSITION_TECHNIQUES["transient_blip"])
            if is_rhythmic or salience >= 0.50:
                return dict(TRANSITION_TECHNIQUES["directional_wipe"])

        return dict(TRANSITION_TECHNIQUES["smooth_cosine_crossfade"])

    def generate_staggered_configs(
        self,
        allocation: Dict[str, str],
        base_config: Optional[Dict[str, Any]] = None,
        pattern: Optional[StaggerPattern] = None,
        step_delay: float = 0.15,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Builds per-segment transition configurations with staggered start offsets
        and/or cohort-specific techniques.
        """
        cfg = base_config or self.select_transition_technique()
        base_tech = cfg.get("type", "fade_in_out")
        base_dur = float(cfg.get("duration", 2.0))
        stagger_pat = pattern or select_stagger_pattern(getattr(self.listener, "context", None))
        verts, rings = self._discover_segment_cohorts()
        return generate_staggered_configs(
            allocation=allocation,
            verticals=verts,
            rings=rings,
            base_technique=base_tech,
            base_duration=base_dur,
            pattern=stagger_pat,
            step_delay=step_delay,
        )

    def schedule_transition(
        self,
        allocation: Optional[Dict[str, str]] = None,
        transition_config: Optional[Any] = None,
        quantize_downbeat: bool = True,
        staggered: bool = False,
        stagger_pattern: Optional[StaggerPattern] = None,
    ) -> None:
        """
        Queues or immediately triggers an installation mode transition.

        Args:
            allocation: Mapping of {segment_name: mode_name}. Defaults to allocate_all_segments().
            transition_config: Single transition config dict OR mapping of {seg_name: config_dict}.
            quantize_downbeat: If True, waits for listener.beat_phase < 0.05 before firing.
            staggered: If True, generates staggered timing across cohorts.
            stagger_pattern: Optional StaggerPattern override when staggered=True.
        """
        target_alloc = allocation if allocation is not None else self.allocate_all_segments()
        if staggered:
            base_cfg = transition_config if (isinstance(transition_config, dict) and "type" in transition_config) else None
            target_cfg = self.generate_staggered_configs(target_alloc, base_config=base_cfg, pattern=stagger_pattern)
        elif transition_config is not None:
            target_cfg = transition_config
        else:
            target_cfg = self.select_transition_technique()

        if not quantize_downbeat:
            self._execute_transition(target_alloc, target_cfg)
            return

        self._pending_transition = {
            "allocation": target_alloc,
            "config": target_cfg,
            "requested_time": time.time(),
            "elapsed": 0.0,
        }

    def _execute_transition(self, allocation: Dict[str, str], transition_config: Any) -> None:
        """Dispatches mode updates to physical segments and kicks Transition_Director."""
        if not allocation:
            return

        is_per_seg = isinstance(transition_config, dict) and any(k in allocation for k in transition_config)
        max_duration = 0.0
        primary_tech = "fade_in_out"

        for seg_name, mode_name in allocation.items():
            segment = getattr(self.mode_master, "_find_segment_by_name", lambda n: None)(seg_name)
            if segment is not None and getattr(segment, "isBlocked", False) is not True:
                seg_cfg = transition_config[seg_name] if (is_per_seg and seg_name in transition_config) else (transition_config or {})
                segment.change_mode(mode_name, seg_cfg)
                if hasattr(segment, "change_way") and seg_cfg.get("direction"):
                    segment.change_way(seg_cfg["direction"])

                dur = float(seg_cfg.get("duration", 2.0))
                offset = float(seg_cfg.get("start_offset", 0.0))
                if offset + dur > max_duration:
                    max_duration = offset + dur
                if primary_tech == "fade_in_out" and seg_cfg.get("type"):
                    primary_tech = seg_cfg["type"]

                if isinstance(getattr(self.mode_master, "activ_configuration", None), dict):
                    modes_dict = self.mode_master.activ_configuration.setdefault("modes", {})
                    modes_dict[seg_name] = mode_name

        if hasattr(self.mode_master, "_state_dirty"):
            self.mode_master._state_dirty = True

        td = getattr(self.mode_master, "transition_director", None)
        if td is not None and hasattr(td, "start_transition"):
            if is_per_seg:
                td.start_transition({"type": primary_tech, "duration": max_duration, "total_duration": max_duration})
            else:
                td.start_transition(transition_config)

        self._dwell_timer = 0.0

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _discover_segment_cohorts(self) -> Tuple[List[str], List[List[str]]]:
        """Discovers vertical pillars and horizontal rings from Mode_master segments."""
        return discover_segment_cohorts(getattr(self.mode_master, "segments_list", []))

    def _get_candidate_pool_for_segments(self, segment_names: List[str]) -> List[str]:
        """Aggregates mode names loaded across the given segments."""
        pool_set = set()
        for name in segment_names:
            seg = getattr(self.mode_master, "_find_segment_by_name", lambda n: None)(name)
            if seg is not None and hasattr(seg, "modes"):
                pool_set.update(seg.modes.keys())
        if pool_set:
            return sorted(pool_set)
        return list(self._cached_available_modes)

    def _get_current_mode_name(self, segment_name: str) -> Optional[str]:
        seg = getattr(self.mode_master, "_find_segment_by_name", lambda n: None)(segment_name)
        if seg is not None:
            return getattr(seg, "activ_mode", None)
        return None
