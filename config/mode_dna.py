"""
config/mode_dna.py - Visual Mode DNA & Spatial Role Specifications.

Defines the acoustic-visual fingerprint (DNA) for every visual animation mode:
- energy [0.0, 1.0]: Overall kinetic drive and luminance activity.
- punch [0.0, 1.0]: Percussive responsiveness and transient impact sharpness.
- rhythm [0.0, 1.0]: Beat-coupling and metronomic alignment strength.
- complexity [0.0, 1.0]: Algorithmic, spatial, and chromatic entropy.
- spatial_role: Structural orientation preference ("vertical", "horizontal", "both").

Guarantees:
- AXIOM-07: Code length <= 500 lines.
"""

from typing import Dict, Any


DEFAULT_MODE_DNA: Dict[str, Any] = {
    "energy": 0.50,
    "punch": 0.50,
    "rhythm": 0.50,
    "complexity": 0.50,
    "spatial_role": "both",
}

MODE_DNA: Dict[str, Dict[str, Any]] = {
    # Smooth / Ambient / Harmonic Modes
    "Rainbow": {
        "energy": 0.35,
        "punch": 0.10,
        "rhythm": 0.20,
        "complexity": 0.30,
        "spatial_role": "both",
    },
    "Bary Rainbow": {
        "energy": 0.40,
        "punch": 0.15,
        "rhythm": 0.30,
        "complexity": 0.35,
        "spatial_role": "both",
    },
    "Shining Stars": {
        "energy": 0.30,
        "punch": 0.20,
        "rhythm": 0.25,
        "complexity": 0.40,
        "spatial_role": "both",
    },
    "Proportion Rainbow": {
        "energy": 0.45,
        "punch": 0.25,
        "rhythm": 0.35,
        "complexity": 0.40,
        "spatial_role": "both",
    },
    "Static Wave": {
        "energy": 0.35,
        "punch": 0.20,
        "rhythm": 0.40,
        "complexity": 0.30,
        "spatial_role": "both",
    },
    "Rhythm Breather": {
        "energy": 0.50,
        "punch": 0.35,
        "rhythm": 0.70,
        "complexity": 0.40,
        "spatial_role": "both",
    },

    # Grooving / Wave / Intermediate Modes
    "PSG": {
        "energy": 0.50,
        "punch": 0.40,
        "rhythm": 0.45,
        "complexity": 0.35,
        "spatial_role": "both",
    },
    "Middle Bar": {
        "energy": 0.55,
        "punch": 0.60,
        "rhythm": 0.50,
        "complexity": 0.30,
        "spatial_role": "both",
    },
    "Coloured Middle Wave": {
        "energy": 0.60,
        "punch": 0.55,
        "rhythm": 0.60,
        "complexity": 0.50,
        "spatial_role": "both",
    },
    "Extending Waves": {
        "energy": 0.60,
        "punch": 0.50,
        "rhythm": 0.60,
        "complexity": 0.50,
        "spatial_role": "both",
    },
    "Opposite Sides": {
        "energy": 0.65,
        "punch": 0.55,
        "rhythm": 0.65,
        "complexity": 0.45,
        "spatial_role": "both",
    },
    "Flying Ball": {
        "energy": 0.60,
        "punch": 0.50,
        "rhythm": 0.65,
        "complexity": 0.45,
        "spatial_role": "both",
    },
    "Magnetic Ball": {
        "energy": 0.65,
        "punch": 0.55,
        "rhythm": 0.60,
        "complexity": 0.55,
        "spatial_role": "both",
    },
    "Matrix Rain": {
        "energy": 0.55,
        "punch": 0.30,
        "rhythm": 0.45,
        "complexity": 0.65,
        "spatial_role": "vertical",
    },

    # High Dynamic / Expressive / Synesthetic Modes
    "Plasma Fire": {
        "energy": 0.75,
        "punch": 0.50,
        "rhythm": 0.55,
        "complexity": 0.75,
        "spatial_role": "both",
    },
    "Synesthesia": {
        "energy": 0.75,
        "punch": 0.65,
        "rhythm": 0.70,
        "complexity": 0.75,
        "spatial_role": "both",
    },
    "Chromatic Chaser": {
        "energy": 0.70,
        "punch": 0.60,
        "rhythm": 0.80,
        "complexity": 0.50,
        "spatial_role": "both",
    },
    "Power Bar": {
        "energy": 0.70,
        "punch": 0.75,
        "rhythm": 0.60,
        "complexity": 0.35,
        "spatial_role": "both",
    },
    "Metronome": {
        "energy": 0.65,
        "punch": 0.85,
        "rhythm": 0.95,
        "complexity": 0.30,
        "spatial_role": "both",
    },

    # High Impact / Drop / Strobe Modes
    "Beat Runner": {
        "energy": 0.85,
        "punch": 0.80,
        "rhythm": 0.90,
        "complexity": 0.55,
        "spatial_role": "both",
    },
    "Hyper Strobe": {
        "energy": 0.95,
        "punch": 0.95,
        "rhythm": 0.85,
        "complexity": 0.40,
        "spatial_role": "both",
    },
    "Impact Shockwave": {
        "energy": 0.90,
        "punch": 0.95,
        "rhythm": 0.85,
        "complexity": 0.60,
        "spatial_role": "both",
    },

    # Arcade / Special
    "Alcool Randomer": {
        "energy": 0.50,
        "punch": 0.30,
        "rhythm": 0.30,
        "complexity": 0.50,
        "spatial_role": "both",
    },
}

# Lookup map with lowercased keys and stripped whitespace/underscores for robust matching
_LOOKUP_MAP: Dict[str, Dict[str, Any]] = {}
for _mode_key, _dna_dict in MODE_DNA.items():
    _LOOKUP_MAP[_mode_key.lower()] = _dna_dict
    _LOOKUP_MAP[_mode_key.lower().replace(" ", "_")] = _dna_dict
    _LOOKUP_MAP[_mode_key.lower().replace("_", " ")] = _dna_dict
    _LOOKUP_MAP[_mode_key.lower().replace(" ", "")] = _dna_dict


def get_mode_dna(mode_name: str) -> Dict[str, Any]:
    """
    Retrieve the DNA dictionary for a given mode name.
    Performs case-insensitive, normalized lookup with fallback to DEFAULT_MODE_DNA.

    Args:
        mode_name: Name of the mode (e.g., 'Rainbow', 'beat_runner_mode', 'Impact Shockwave').

    Returns:
        Dict[str, Any] containing 'energy', 'punch', 'rhythm', 'complexity', and 'spatial_role'.
    """
    if not isinstance(mode_name, str):
        return dict(DEFAULT_MODE_DNA)

    cleaned = mode_name.strip().lower()
    # Strip optional '_mode' suffix
    if cleaned.endswith("_mode"):
        cleaned = cleaned[:-5]
    elif cleaned.endswith(" mode"):
        cleaned = cleaned[:-5]

    if cleaned in _LOOKUP_MAP:
        return dict(_LOOKUP_MAP[cleaned])

    # Strip non-alphanumeric characters
    compact = "".join(c for c in cleaned if c.isalnum())
    if compact in _LOOKUP_MAP:
        return dict(_LOOKUP_MAP[compact])

    return dict(DEFAULT_MODE_DNA)
