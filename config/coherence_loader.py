"""
config/coherence_loader.py - Declarative Coherence Policy & Metadata Loader.

Reads coherence_<profile>.json and modes.json outside the sealed transitions/ room.
Resolves paths by hardware profile ('full' vs 'small') like resolve_segments_file_path.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple, Union

CONFIG_DIR = os.path.abspath(os.path.dirname(__file__))
APP_CONFIG_PATH = os.path.join(CONFIG_DIR, "app_config.json")
MODES_CONFIG_PATH = os.path.join(CONFIG_DIR, "modes.json")
COHERENCE_FULL_PATH = os.path.join(CONFIG_DIR, "coherence_full.json")
COHERENCE_SMALL_PATH = os.path.join(CONFIG_DIR, "coherence_small.json")
COHERENCE_LEGACY_PATH = os.path.join(CONFIG_DIR, "coherence.json")
COHERENCE_SCHEMA_PATH = os.path.join(CONFIG_DIR, "coherence.schema.json")


def _read_app_config_profile() -> str:
    try:
        if os.path.exists(APP_CONFIG_PATH):
            with open(APP_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return str(cfg.get("hardware_profile", "full")).strip().lower()
    except Exception:
        pass
    return "full"


def _resolve_candidate_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not os.path.isabs(path):
        config_candidate = os.path.join(CONFIG_DIR, path)
        if os.path.exists(config_candidate) or not os.path.exists(path):
            path = config_candidate
    return os.path.abspath(path)


def resolve_coherence_file_path(infos: Optional[Union[Dict[str, Any], str]] = None) -> str:
    """Resolve the absolute path to coherence_<profile>.json matching the hardware profile."""
    if isinstance(infos, str):
        cleaned = infos.strip()
        if cleaned.lower().endswith(".json"):
            return _resolve_candidate_path(cleaned)
        profile = cleaned.lower()
    elif isinstance(infos, dict):
        explicit = infos.get("coherence_file") or infos.get("coherence_config_path")
        if isinstance(explicit, str) and explicit.strip():
            return _resolve_candidate_path(explicit)
        profile = str(infos.get("hardware_profile", "")).strip().lower() or _read_app_config_profile()
    else:
        profile = _read_app_config_profile()

    if profile == "small":
        if os.path.exists(COHERENCE_SMALL_PATH):
            return COHERENCE_SMALL_PATH
        if os.path.exists(COHERENCE_FULL_PATH):
            return COHERENCE_FULL_PATH
        return COHERENCE_SMALL_PATH

    if os.path.exists(COHERENCE_FULL_PATH):
        return COHERENCE_FULL_PATH
    if os.path.exists(COHERENCE_LEGACY_PATH):
        return COHERENCE_LEGACY_PATH
    return COHERENCE_FULL_PATH


def validate_coherence_dict(policy: Dict[str, Any]) -> None:
    """Structural pre-validation for a coherence policy dictionary."""
    if not isinstance(policy, dict):
        raise ValueError(f"Coherence policy must be a dict, got {type(policy).__name__}")
    for req_key in ("settings", "zones", "rules"):
        if req_key not in policy:
            raise ValueError(f"Coherence policy missing required top-level key: '{req_key}'")

    settings = policy["settings"]
    if not isinstance(settings, dict):
        raise ValueError("Policy 'settings' must be a dict")
    for s_key in ("maxDifferentModes", "temperature", "memoryDepth", "repeatPenalty"):
        if s_key not in settings:
            raise ValueError(f"Policy settings missing required field: '{s_key}'")

    v_max = settings["maxDifferentModes"]
    if isinstance(v_max, bool) or not isinstance(v_max, int) or v_max < 1:
        raise ValueError(f"'maxDifferentModes' must be integer >= 1, got {v_max!r}")
    v_temp = settings["temperature"]
    if isinstance(v_temp, bool) or not isinstance(v_temp, (int, float)) or not (0.05 <= float(v_temp) <= 5.0):
        raise ValueError(f"'temperature' must be in [0.05, 5.0], got {v_temp!r}")
    v_depth = settings["memoryDepth"]
    if isinstance(v_depth, bool) or not isinstance(v_depth, int) or v_depth < 0:
        raise ValueError(f"'memoryDepth' must be integer >= 0, got {v_depth!r}")
    v_rep = settings["repeatPenalty"]
    if isinstance(v_rep, bool) or not isinstance(v_rep, (int, float)) or float(v_rep) < 0.0:
        raise ValueError(f"'repeatPenalty' must be number >= 0, got {v_rep!r}")

    zones = policy["zones"]
    if not isinstance(zones, dict) or not zones:
        raise ValueError("Policy 'zones' must be a non-empty dict")
    for zone_id, zone_data in zones.items():
        if not isinstance(zone_data, dict):
            raise ValueError(f"Zone '{zone_id}' must be a dict")
        segs = zone_data.get("segments")
        if not isinstance(segs, list) or not segs:
            raise ValueError(f"Zone '{zone_id}' must contain a non-empty 'segments' list")
        groupings = zone_data.get("groupings")
        if not isinstance(groupings, list) or not groupings:
            raise ValueError(f"Zone '{zone_id}' must contain a non-empty 'groupings' list")
        for g in groupings:
            if not isinstance(g, dict) or not isinstance(g.get("id"), str) or not g["id"].strip():
                raise ValueError(f"Grouping in zone '{zone_id}' missing non-empty 'id'")
            gw = g.get("weight")
            if isinstance(gw, bool) or not isinstance(gw, (int, float)) or float(gw) <= 0.0:
                raise ValueError(f"Grouping '{g['id']}' weight must be > 0, got {gw!r}")
            groups = g.get("groups")
            if not isinstance(groups, list) or not groups or any(not isinstance(grp, list) or not grp for grp in groups):
                raise ValueError(f"Grouping '{g['id']}' must have a non-empty list of non-empty groups")

    rules = policy["rules"]
    if not isinstance(rules, list):
        raise ValueError("Policy 'rules' must be a list")
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"].strip():
            raise ValueError(f"Rule at index {idx} missing non-empty 'id'")
        rid = rule["id"].strip()
        when = rule.get("when")
        if not isinstance(when, list) or not when:
            raise ValueError(f"Rule '{rid}' 'when' must be a non-empty list of placements")
        has_w = "weight" in rule
        has_eff = "effect" in rule
        if has_w == has_eff:
            raise ValueError(f"Rule '{rid}' must specify either 'weight' or 'effect'")
        if has_w:
            rw = rule["weight"]
            if isinstance(rw, bool) or not isinstance(rw, (int, float)) or float(rw) <= 0.0:
                raise ValueError(f"Rule '{rid}' weight must be > 0, got {rw!r}")
        if has_eff and rule["effect"] != "forbid":
            raise ValueError(f"Rule '{rid}' effect must be 'forbid', got {rule['effect']!r}")


def load_coherence_config(infos: Optional[Union[Dict[str, Any], str]] = None) -> Dict[str, Any]:
    """Load, parse, and pre-validate coherence_<profile>.json."""
    file_path = resolve_coherence_file_path(infos)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Coherence configuration file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse coherence policy JSON at '{file_path}': {exc}") from exc
    validate_coherence_dict(data)
    return data
