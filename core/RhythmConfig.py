"""
RhythmConfig.py - Centralized configuration dataclass for the Oracle Rhythm & Structural Event Engine.
"""

from dataclasses import dataclass


@dataclass
class RhythmConfig:
    # --- Flywheel Confidence & Soft-Snap Thresholds ---
    high_confidence_threshold: float = 0.30
    moderate_confidence_threshold: float = 0.15
    high_snap_ratio: float = 0.50
    moderate_snap_ratio: float = 0.15

    # --- Oracle Sweep & Tempo Judge ---
    sweep_interval: float = 0.2                 # seconds between phase sweeps
    bpm_min: float = 40.0
    bpm_max: float = 220.0
    human_prior_center: float = 125.0
    human_prior_sigma: float = 40.0
    coarse_class_step: float = 0.01
    fine_class_radius: float = 0.05

    # --- Structural Novelty & Song Change ---
    song_novelty_asserved_th: float = 0.8
    structural_cooldown_seconds: float = 20.0
    gm_shock_multiplier: float = 1.5
    stm_retention_base: float = 0.98
    ltm_retention_base: float = 0.9985
    novelty_lm_floor: float = 0.15
    novelty_lm_decay: float = 0.9995
    power_novelty_weight: float = 0.2

    # --- Silence Detection ---
    silence_power_threshold: float = 5.0
    silence_threshold_seconds: float = 1.5
    silence_cooldown_seconds: float = 5.0

    # --- Onset & Flux Detection ---
    flux_retention_base: float = 0.95
    rolling_flux_decay: float = 0.95
    strong_peak_multiplier: float = 1.8
    peak_sensitivity_min: float = 1.5
    peak_sensitivity_max: float = 4.0
    delta_time_peak: float = 0.15
    noise_floor_min: float = 10.0
    noise_floor_ratio: float = 0.05

    # --- Beat Validation & Dropped Beat ---
    real_beat_baseline_ratio: float = 0.5
    real_beat_energy_floor: float = 5.0
