# AXIOM-09: Scoped DSP Math & Processing Invariance

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_09_platform_invariance.py`  

---

## 1. Specification

1. **Uniform Mathematical Core:**
   The exact same audio feature analysis, Mel filtering, onset spectral flux, comb-filter tempo correlation, and beat tracking algorithms must execute identically across all execution targets:
   - Live ALSA microphone input on Raspberry Pi 4B.
   - Live WASAPI microphone input on Windows desktop.
   - Offline MP3/WAV playback via test runners.
   - Pure synthetic click benchmark evaluations.
2. **Zero Platform Branching in Math Code:**
   Code in `core/` (DSP, rhythm tracking, orchestration) and `modes/` (visual animations) is **strictly forbidden** from inspecting the host operating system or branching on environment:
   - Prohibited checks in `core/` and `modes/`: `if sys.platform == 'linux':`, `if os.name == 'posix':`, `if is_pi:`, `if "Raspberry" in ...`.
3. **Scoped Hardware Exemption:**
   Hardware- and OS-specific branches are strictly confined to:
   - `hardware/HardwareFactory.py`: Factory instantiation of drivers.
   - `hardware/Rpi_NeoPixels.py`: Low-level physical WS2812B GPIO/SPI hardware interface.
   - `hardware/Fake_leds.py`: Pygame simulator window.
   - `core/Mode_master.py:380`: The single executor thread-offload branch for physical SPI transmission.

---

## 2. Architectural Boundary Diagram

```
┌────────────────────────────────────────────────────────┐
│             MATHEMATICAL CORE (PURE & AGNOSTIC)        │
│                                                        │
│  core/AudioIngestion.py       core/Listener.py         │
│  core/MultiBandOnsetAudioAnalyzer.py                   │
│  core/comb_kernels.py         modes/*.py               │
│                                                        │
│  [ZERO OS checks, ZERO platform branching, PURE NUMPY]  │
└───────────────────────────┬────────────────────────────┘
                            │ (Emits RGB Array)
                            ▼
┌────────────────────────────────────────────────────────┐
│           SCOPED HARDWARE LAYER (PLATFORM AWARE)       │
│                                                        │
│  hardware/HardwareFactory.py  hardware/Udp_Sender.py   │
│  hardware/Rpi_NeoPixels.py    hardware/Fake_ESP32.py   │
│                                                        │
│  [Handles SPI, Windows/Linux sockets, GPIO pins]       │
└────────────────────────────────────────────────────────┘
```

---

## 3. Violation Conditions

- Any `sys.platform`, `platform.system()`, or `os.name` check found inside `core/` (except the isolated executor offload in `Mode_master.py`) or `modes/`.
- Behavior where beat tracking or visual effects produce differing mathematical outputs depending on whether run on Windows or Raspberry Pi.
