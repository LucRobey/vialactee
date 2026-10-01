# AXIOM-03: Physical Chandelier Geometry & The Vertical Invariant

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_03_geometry.py`, `config/Configuration_manager.py`  

---

## 1. Specification

1. **Single Source of Truth:**
   All hardware strip geometry, physical LED pixel counts, cable channels, and 2D visual layout coordinates are defined exclusively in:
   - `config/segments_full.json` (Full Profile: 1,304 LEDs, 11 segments, 2 SPI/UDP channels)
   - `config/segments_small.json` (Small Profile: 249 LEDs, 3 segments, 1 channel)
2. **Dynamic Path Resolution:**
   No code in the repository may hardcode path strings to `segments_full.json` or `configurations_full.json`. All paths must be dynamically resolved via `config/Configuration_manager.py` functions:
   - `resolve_segments_file_path(infos)`
   - `resolve_configurations_file_path(infos)`
3. **The Vertical Invariant:**
   Physical vertical chandelier strips (`v1` through `v4` in full profile, `s1` through `s3` in small profile) are physically wired **bottom-to-top**:
   - Starting point: Lowest physical altitude ($Y_{\text{start}}$).
   - Progression: `vertical_up` direction with coordinate step `step.y = -1` (moving upwards in the 2D matrix, index decrement $Y$).
   - Inverting or mirroring this invariant inverts the spatial physics of the room, corrupting wave propagation, gravity falls, and matrix rain animations.
4. **Channel Segregation:**
   - In the `full` profile:
     - Channel 1 (`segs_1`): 785 LEDs.
     - Channel 2 (`segs_2`): 519 LEDs.
     - Total: 1,304 physical LEDs.
   - In the `small` profile:
     - Channel 1 (`segs_1`): 249 LEDs (`s1`: 49, `s2`: 108, `s3`: 92).

---

## 2. Geometric Mapping Reference

```
Visual Top (Matrix Y = 0)
    ▲
    │   step.y = -1 (physical wiring ascends)
    │
Visual Bottom (Matrix Y = 246)
Physical Connector / Base
```

---

## 3. Violation Conditions

- Hardcoding file paths to configuration JSONs outside `Configuration_manager.py`.
- Declaring vertical strip mappings with positive Y-steps (`step.y > 0` or top-to-bottom indices).
- Desynchronization between `segments_*.json` and runtime `HardwareFactory` channel counts.
