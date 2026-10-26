# Music Analyzer & DSP Sector (`/music/`)

The `music` directory is a sealed sector containing Vialactée's real-time audio ingestion, multi-band spectral processing, predictive Anticipation Flywheel ("Oracle") beat tracking, structural novelty detection, and the 3-tier Musical Context Engine.

> **Sealed Sector Boundary:**
> - Production code outside `music/` may import **only** [`music.api`](api.py) (enforced by `tests/governance/test_music_isolation.py`).
> - Nothing inside `music/` may import project code outside `music/`.
> - Canonical contract and trust-tier ratings: [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md).

## Front Door (`music/api.py`)

- **`Listener`**: Speaker-time-aligned facade and zero-allocation circular delay ring buffer synchronizing real-time spectral features (`AudioIngestion`) with 5-second lookahead rhythm and structural predictions (`BaseAudioAnalyzer`, `MusicalContextEngine`).
- **`MusicalContextEngine`** & **`MusicalScene`**: Unified 3-tier visual conductor (`listener.context`) exposing Tier 1 continuous kinetics (`energy`, `tension`, `drop_progress`, `spectral_tilt`, `vertical_center`), Tier 2 macro scenes (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`), and Tier 3 micro badges (`is_locked`, `is_real_beat`, `is_syncopated`, `is_silent`, `is_drop_impact`, `is_drop_imminent`, `is_structural_cut`).
- **`ANALYZER_REGISTRY`**, **`DEFAULT_ANALYZER_MODEL`**, **`resolve_analyzer_class`**: Registry and resolver for selecting the rhythm analyzer engine (`DyadicMetricalAudioAnalyzer` default, `MultiBandOnsetAudioAnalyzer` fallback, `AudioAnalyzer` baseline).

## Internal Modules

- **`AudioIngestion.py`**: Dual-resolution vectorized DSP front-end. Computes 4096-sample Hanning-windowed RFFTs, an 8-band Mel filterbank for visual modes (`fft_band_values`), a 32-band Mel filterbank for rhythm analyzers (`multiband_fft_values`), a 12-bin chromagram (`chroma_values`), and local/global ADSR envelopes (`asserved_fft_band`, `asserved_total_power`, `band_proportion`).
- **`BaseAudioAnalyzer.py`**: Abstract base contract for all rhythm and structural analyzers used across production and the `research/` benchmark harness.
- **`DyadicMetricalAudioAnalyzer.py`**: Production default rhythm analyzer (Cycle 012). Extends `MultiBandOnsetAudioAnalyzer` with a causal scale-invariant sub-pulse arbiter and dyadic metrical hierarchy.
- **`MultiBandOnsetAudioAnalyzer.py`**: Stable parent rhythm analyzer (Cycle 008). Separates 32-band half-wave rectified onset derivatives into 4 instrument streams ($y_{\text{kick}}, y_{\text{snare}}, y_{\text{hat}}, y_{\text{mid}}$) with kick-conditioned anti-phase disambiguation and a dense triangular pulse template bank.
- **`AudioAnalyzer.py`**: Legacy single-ODF Anticipation Flywheel ("Oracle") baseline preserved for fallback and benchmark ablations.
- **`comb_kernels.py`**: Standalone compiled NumPy kernel (`build_dense_phase_bank`) generating dense triangular pulse template matrices with zero external dependencies.
- **`StructuralNoveltyDetector.py`**: Detects verse/chorus boundaries, seamless crossfades, and silence drops using Short-Term Memory (STM) vs Long-Term Memory (LTM) Euclidean novelty envelopes.
- **`RhythmConfig.py`**: Strongly-typed configuration dataclass centralizing thresholds, cooldowns, and constants for beat tracking and structural novelty detection.
