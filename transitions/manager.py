"""
transitions/manager.py - Music Matchmaker, Mode Coherence Orchestrator, & Downbeat Quantizer.

Evaluates musical context, delegates segment mode allocation to transitions/casting.py,
records transition history in transitions/memory.py on order emission, and quantizes transitions.
Guarantees: AXIOM-01 (<= 0.01 ms), AXIOM-02 (zero heap alloc in steady-state), AXIOM-07 (<= 500 lines).
"""

from dataclasses import replace
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from transitions.api import ModeProfile, MusicSnapshot, SegmentDescriptor, SegmentOrder
from transitions.casting import CastResult, cast_transition
from transitions.director import Transition_Director
from transitions.effects import set_transition_params
from transitions.families import (
    get_allowed_stagger_patterns,
    is_mode_cooperative,
    is_staggerable,
    roll_transition_params,
)
from transitions.memory import TransitionMemory
from transitions.policy import CompiledPolicy, compile_policy, get_default_policy
from transitions.stagger import (
    StaggerPattern,
    discover_segment_cohorts,
    generate_staggered_configs,
    select_stagger_pattern,
)

TRANSITION_TECHNIQUES: Dict[str, Dict[str, Any]] = {
    k: {"type": t, "duration": d}
    for k, (t, d) in {
        "smooth_cosine_crossfade": ("fade_in_out", 2.0),
        "directional_wipe": ("vertical_wipe", 1.2),
        "transient_blip": ("explosion", 0.4),
        "ember_dissolve": ("ember_dissolve", 1.8),
        "luma_melt": ("luma_melt", 1.6),
        "breath_dip": ("breath_dip", 2.0),
        "silk_wipe": ("silk_wipe", 1.2),
        "silk_wipe_reverse": ("silk_wipe_reverse", 1.2),
        "iris_open": ("iris_open", 1.2),
        "iris_close": ("iris_close", 1.2),
        "zipper_merge": ("zipper_merge", 1.2),
        "collider": ("collider", 1.0),
        "prism_sweep": ("prism_sweep", 1.4),
        "flash_cut": ("flash_cut", 0.5),
        "staccato_shutter": ("staccato_shutter", 0.8),
        "transformer_cut": ("transformer_cut", 1.0),
    }.items()
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely converts val to float; coalesces None and invalid types to default."""
    try:
        return default if val is None else float(val)
    except (TypeError, ValueError):
        return default


class LocalTransitionManager:
    """Evaluates musical intent, delegates mode casting to the coherence engine, and quantizes transitions."""

    def __init__(
        self,
        director: Optional[Transition_Director] = None,
        segments: Sequence[SegmentDescriptor] = (),
        music: Optional[MusicSnapshot] = None,
        policy_raw: Optional[Dict[str, Any]] = None,
        modes: Sequence[ModeProfile] = (),
    ) -> None:
        self.director = director
        self.music: MusicSnapshot = music if music is not None else MusicSnapshot()
        self.segments: List[SegmentDescriptor] = []
        self.modes: Tuple[ModeProfile, ...] = tuple(modes)
        self._segments_by_name: Dict[str, SegmentDescriptor] = {}
        self._policy_raw: Optional[Dict[str, Any]] = policy_raw
        self._compiled_policy: Optional[CompiledPolicy] = None
        self.memory: TransitionMemory = TransitionMemory(depth=8)
        self.last_cast_result: Optional[CastResult] = None

        self._pending_transition: Optional[Dict[str, Any]] = None
        self._downbeat_timeout: float = 1.20
        self._dwell_timer: float = 0.0
        self._orders: List[SegmentOrder] = []
        if segments:
            self.set_installation(segments, modes)

    def configure(self, policy_raw: Optional[Dict[str, Any]]) -> None:
        """Store raw coherence policy dict and compile immediately if installation is set."""
        self._policy_raw = policy_raw
        self._compiled_policy = None
        if self._policy_raw is not None and self.segments:
            self._compile_active_policy()

    def _compile_active_policy(self) -> CompiledPolicy:
        """Compile active or default policy and sync memory depth."""
        raw = self._policy_raw if self._policy_raw is not None else get_default_policy(self.segments)
        self._compiled_policy = compile_policy(raw, tuple(self.segments), self.modes)
        self.memory.set_depth(self._compiled_policy.settings.memory_depth)
        return self._compiled_policy

    @property
    def compiled_policy(self) -> CompiledPolicy:
        """Return the compiled coherence policy, compiling on demand if needed."""
        if self._compiled_policy is None:
            return self._compile_active_policy()
        return self._compiled_policy

    @property
    def policy(self) -> Dict[str, Any]:
        """Return active raw policy or built-in default policy."""
        return self._policy_raw if self._policy_raw is not None else get_default_policy(self.segments)

    def set_installation(
        self,
        segments: Sequence[SegmentDescriptor],
        modes: Sequence[ModeProfile] = (),
    ) -> None:
        """Update installation segment descriptors and mode profiles, recompiling policy."""
        self.segments = list(segments)
        self._segments_by_name = {s.name: s for s in self.segments}
        if modes:
            self.modes = tuple(modes)
        self._compiled_policy = None
        if self.segments:
            self._compile_active_policy()

    def allocate_initial(self, music: Optional[MusicSnapshot] = None) -> Dict[str, str]:
        """
        Run the coherence allocator once at boot, record the boot cast in history,
        and return Dict[segment_name, mode_name].
        """
        if not self.segments:
            return {}
        ctx = music if music is not None else self.music
        target_dna = self.evaluate_target_dna(ctx)
        cp = self.compiled_policy
        res = cast_transition(cp, target_dna, self.segments, self.memory)
        self.last_cast_result = res
        self.memory.record(res.full_cast_by_id, res.groupings_by_zone)

        boot_map: Dict[str, str] = {}
        for sid, mode_name in res.full_cast_by_id.items():
            seg_name = cp.segment_id_to_name.get(sid, sid)
            boot_map[seg_name] = mode_name
            self.set_active_mode(seg_name, mode_name)
        return boot_map

    def set_active_mode(self, segment_name: str, mode_name: str) -> None:
        """Record that a segment accepted its target mode."""
        seg = self._segments_by_name.get(segment_name)
        if seg is not None:
            updated = replace(seg, active_mode=mode_name)
            self._segments_by_name[segment_name] = updated
            self.segments = [updated if s.name == segment_name else s for s in self.segments]

    def pop_orders(self) -> Tuple[SegmentOrder, ...]:
        """Drain and return emitted segment orders since the last check."""
        orders, self._orders = tuple(self._orders), []
        return orders

    def update(self, dt: float, music: Optional[MusicSnapshot] = None) -> None:
        """Advance steady-state timers and check downbeat trigger (AXIOM-01/02)."""
        if music is not None:
            self.music = music
        self._dwell_timer += dt

        if self._pending_transition is not None:
            if self.director is not None and self.director.is_in_transition:
                return

            phase = _safe_float(getattr(self.music, "beat_phase", 0.0))
            is_beat = bool(getattr(self.music, "is_beat", False))
            self._pending_transition["elapsed"] = self._pending_transition.get("elapsed", 0.0) + dt
            is_beat_trustworthy = _safe_float(getattr(self.music, "beat_trust", 0.0)) >= 0.20
            if ((phase < 0.05 and is_beat_trustworthy) or is_beat) or self._pending_transition["elapsed"] >= self._downbeat_timeout:
                pending, self._pending_transition = self._pending_transition, None
                self._execute_transition(
                    pending["allocation"],
                    pending["config"],
                    pending.get("cast_result"),
                )

    # 1. MUSIC MATCHMAKER: Live Context -> Target DNA

    def evaluate_target_dna(self, context: Optional[Any] = None) -> Dict[str, float]:
        """Translates live music snapshot metrics into a target mode DNA vector in [0.0, 1.0]."""
        ctx = context if context is not None else self.music
        e = _safe_float(getattr(ctx, "energy", 0.5), 0.5)
        s = _safe_float(getattr(ctx, "salience", 0.5), 0.5)
        t = _safe_float(getattr(ctx, "beat_trust", 0.5), 0.5)
        nov = _safe_float(getattr(ctx, "novelty", 0.4), 0.4)
        tension = _safe_float(getattr(ctx, "tension", 0.3), 0.3)
        is_drop = bool(getattr(ctx, "is_drop_impact", False))
        is_sync = bool(getattr(ctx, "is_syncopated", False))
        return {
            "energy": round(max(0.0, min(1.0, e)), 4),
            "punch": round(1.0 if is_drop else max(0.0, min(1.0, 0.60 * s + 0.40 * e)), 4),
            "rhythm": round(max(0.0, min(1.0, 0.70 * t + 0.30 * s)), 4),
            "complexity": round(max(0.0, min(1.0, 0.40 * nov + 0.30 * tension + (0.30 if is_sync else 0.10))), 4),
        }

    # 2. COHERENCE CASTING DELEGATION

    def allocate_all_segments(
        self,
        target_dna: Optional[Dict[str, float]] = None,
    ) -> Dict[str, str]:
        """Delegates installation mode allocation to the Mode Coherence casting engine."""
        if not self.segments:
            return {}
        target = target_dna if isinstance(target_dna, dict) else self.evaluate_target_dna()
        cp = self.compiled_policy
        res = cast_transition(cp, target, self.segments, self.memory)
        self.last_cast_result = res
        return dict(res.orders_by_segment_name)

    # 3. DOWNBEAT QUANTIZATION & CLEAN TECHNIQUES

    def select_transition_technique(self, context: Optional[Any] = None) -> Dict[str, Any]:
        """Picks a transition technique based on audio kinetics (drop -> explosion, rhythmic -> wipe, chill -> fade)."""
        ctx = context if context is not None else self.music
        if ctx is not None:
            if bool(getattr(ctx, "is_drop_impact", False)) or _safe_float(getattr(ctx, "energy", 0.0)) >= 0.85:
                return dict(TRANSITION_TECHNIQUES["transient_blip"])
            if bool(getattr(ctx, "is_rhythmic", False)) or _safe_float(getattr(ctx, "salience", 0.0)) >= 0.50:
                return dict(TRANSITION_TECHNIQUES["directional_wipe"])
        return dict(TRANSITION_TECHNIQUES["smooth_cosine_crossfade"])

    def generate_staggered_configs(
        self,
        allocation: Dict[str, str],
        base_config: Optional[Dict[str, Any]] = None,
        pattern: Optional[StaggerPattern] = None,
        step_delay: float = 0.15,
    ) -> Dict[str, Dict[str, Any]]:
        """Builds per-segment transition configurations respecting TransitionFamily stagger contracts."""
        cfg = base_config or self.select_transition_technique()
        base_tech, base_dur = str(cfg.get("type", "fade_in_out")), float(cfg.get("duration", 2.0))
        if not is_staggerable(base_tech):
            stagger_pat = StaggerPattern.SIMULTANEOUS
        elif pattern is not None:
            allowed = get_allowed_stagger_patterns(base_tech)
            stagger_pat = pattern if pattern in allowed else StaggerPattern.SIMULTANEOUS
        else:
            stagger_pat = select_stagger_pattern(self.music)
            allowed = get_allowed_stagger_patterns(base_tech)
            if stagger_pat not in allowed:
                stagger_pat = random.choice(allowed)
        verts, rings = self._discover_segment_cohorts()
        return generate_staggered_configs(
            allocation=allocation,
            verticals=verts,
            rings=rings,
            base_technique=base_tech,
            base_duration=base_dur,
            pattern=stagger_pat,
            step_delay=step_delay,
            segments=self.segments,
        )

    def schedule_transition(
        self,
        allocation: Optional[Dict[str, str]] = None,
        transition_config: Optional[Any] = None,
        quantize_downbeat: bool = True,
        staggered: bool = False,
        stagger_pattern: Optional[StaggerPattern] = None,
    ) -> None:
        """Queues or immediately triggers an installation mode transition."""
        if allocation is not None:
            target_alloc = allocation
            cast_res = None
        else:
            target_alloc = self.allocate_all_segments()
            cast_res = self.last_cast_result

        if staggered:
            base_cfg = transition_config if (isinstance(transition_config, dict) and "type" in transition_config) else None
            target_cfg = self.generate_staggered_configs(target_alloc, base_config=base_cfg, pattern=stagger_pattern)
        elif transition_config is not None:
            target_cfg = transition_config
        else:
            target_cfg = self.select_transition_technique()

        if not quantize_downbeat:
            self._pending_transition = None
            self._execute_transition(target_alloc, target_cfg, cast_res)
            return

        self._pending_transition = {
            "allocation": target_alloc,
            "config": target_cfg,
            "cast_result": cast_res,
            "elapsed": 0.0,
        }

    def _execute_transition(
        self,
        allocation: Dict[str, str],
        transition_config: Any,
        cast_result: Optional[CastResult] = None,
    ) -> None:
        """Builds SegmentOrders for non-blocked segments, records history, and starts Transition_Director."""
        self._orders.clear()
        if not allocation:
            if self.director is not None:
                self.director.is_pending = False
            return

        is_per_seg = isinstance(transition_config, dict) and any(k in allocation for k in transition_config)
        max_duration = 0.0
        primary_tech = (
            str(transition_config.get("type", "fade_in_out"))
            if (isinstance(transition_config, dict) and not is_per_seg)
            else "fade_in_out"
        )
        emitted = 0

        for seg_name, mode_name in allocation.items():
            segment = self._segments_by_name.get(seg_name)
            if segment is not None and not segment.is_blocked:
                seg_cfg = transition_config[seg_name] if (is_per_seg and seg_name in transition_config) else (transition_config or {})
                tech = str(seg_cfg.get("type", "fade_in_out"))
                dur = float(seg_cfg.get("duration", 2.0))
                offset = float(seg_cfg.get("start_offset", 0.0))
                self._orders.append(
                    SegmentOrder(
                        segment=seg_name,
                        target_mode=mode_name,
                        technique=tech,
                        duration=dur,
                        direction=seg_cfg.get("direction"),
                        start_offset=offset,
                        mode_handshake=is_mode_cooperative(tech),
                    )
                )
                emitted += 1
                max_duration = max(max_duration, offset + dur)
                if primary_tech == "fade_in_out" and seg_cfg.get("type"):
                    primary_tech = str(seg_cfg["type"])

        if emitted > 0:
            # Record cast and groupings in history ONLY when orders are emitted (§4 Step 7)
            if cast_result is not None:
                self.memory.record(cast_result.full_cast_by_id, cast_result.groupings_by_zone)
            elif self.segments:
                cp = self.compiled_policy
                manual_cast: Dict[str, str] = {}
                for s in self.segments:
                    sid = cp.segment_name_to_id.get(s.name, s.name)
                    if not s.is_blocked and s.name in allocation:
                        manual_cast[sid] = allocation[s.name]
                    elif s.active_mode:
                        manual_cast[sid] = s.active_mode
                self.memory.record(manual_cast)

            set_transition_params(roll_transition_params(primary_tech))
            if self.director is not None:
                cfg = (
                    {"type": primary_tech, "duration": max_duration, "total_duration": max_duration}
                    if is_per_seg
                    else (
                        dict(transition_config)
                        if isinstance(transition_config, dict)
                        else {"type": primary_tech, "duration": max_duration}
                    )
                )
                if not is_per_seg and max_duration > float(cfg.get("duration", 0.0)):
                    cfg["total_duration"] = max_duration
                self.director.start_transition(cfg)
            self._dwell_timer = 0.0
        elif self.director is not None:
            self.director.is_pending = False

    def _discover_segment_cohorts(self) -> Tuple[List[str], List[List[str]]]:
        """Discovers vertical pillars and horizontal rings from installation segments."""
        return discover_segment_cohorts(self.segments)


TransitionManager = LocalTransitionManager
