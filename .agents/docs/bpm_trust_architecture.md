# Rhythm Confidence & Flywheel Trust Architecture

This document maps out how rhythmic confidence and tempo trust are computed in the production **Anticipation Flywheel ("Oracle")** engine ([`core/AudioAnalyzer.py`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/core/AudioAnalyzer.py)), from raw audio down to the confidence-adaptive flywheel soft-snaps.

---

## 1. The Data Flow

```mermaid
flowchart TD
    %% Styling
    classDef signal fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#fff
    classDef math fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff
    classDef core fill:#d63031,stroke:#fab1a0,stroke-width:2px,color:#fff
    classDef output fill:#00b894,stroke:#55efc4,stroke-width:2px,color:#fff

    A[Raw Audio Chunk @ T_ingest]:::signal -->|FFT + Mel Bands| B[AudioIngestion.py]:::math
    B -->|Transient Flux| C[(5-Second ODF Buffer B)]:::signal

    C --> D[Standardize Buffer\nB_centered = B - mean\nB_std = std]:::math
    
    subgraph "Pearson Correlation Confidence Engine"
        D --> E[FastTemplateBank\nNormalized Triangular Templates T]:::math
        E --> F["Pearson Score Matrix\nS = (T @ B_centered) / B_std"]:::math
        F --> G[Logarithmic Class Scout\nf(BPM) = log2(BPM/60) mod 1]:::math
        G --> H["Peak Pearson Correlation\nconfidence_score ∈ [0.0, 1.0]"]:::core
    end

    subgraph "Harmonic Alignment & Gatekeeper"
        H --> I["Evaluate Harmonic Multipliers\n(Octaves & 3:2 Fifths)"]:::math
        I --> J["Candidate Scoring\nPearson + Prior - 0.5 × Dist(Current, Candidate)"]:::math
        J --> K["Winning BPM & Target Phase φ_target"]:::core
    end

    subgraph "Flywheel Adaptive Soft-Snap"
        K --> L{Confidence Level?}:::math
        L -->|Confidence > 0.30| M[High Trust:\nSnap 50% toward φ_target]:::output
        L -->|0.15 ≤ Confidence ≤ 0.30| N[Moderate Trust:\nSnap 15% toward φ_target]:::output
        L -->|Confidence < 0.15| O[Low Trust / Breakdown:\n0% Snap — Freewheel Coasting]:::output
    end
```

---

## 2. Step-by-Step Explanation

### 1. Onset Detection Function (ODF) Buffer
The `AudioIngestion` layer generates a continuous spectral flux combining low-end bass kicks and mid/high transient attacks. This is pushed into an $N$-frame sliding ring buffer ($N \approx 300$ frames for 5 seconds at 60 FPS).

### 2. $O(1)$ Pearson Template Cross-Correlation
Instead of legacy autocorrelation (which suffered from sub-harmonic bias and high CPU usage), the engine uses a pre-computed bank of zero-mean, unit-variance triangular beat pulses $\mathbf{T}_{\text{norm}}$ across all candidate BPMs and phase shifts.

The Pearson correlation coefficient is computed in a single vectorized NumPy operation:
$$\text{Score}_{\text{Pearson}} = \frac{\mathbf{T}_{\text{norm}} \cdot (\mathbf{B} - \mu_B)}{\sigma_B}$$

- **High Confidence ($> 0.30$ to $0.70+$)**: Occurs when a clear, repeating drum grid aligns strongly with the template.
- **Low Confidence ($< 0.15$)**: Occurs during ambient intros, vocal solos, drum fills, or musical breakdowns.

### 3. Circular Logarithmic Tempo-Class Trust
Tempos are evaluated in circular octave space:
$$f(\text{BPM}) = \log_2\left(\frac{\text{BPM}}{60}\right) \pmod 1$$
This ensures 60, 120, and 240 BPM all map to distance $0.0$, eliminating polyrhythmic ping-pong jumping.

Candidate tempos are scored using:
$$\text{Total Score} = \text{Score}_{\text{Pearson}} + \text{Prior}_{\text{Human}}(\text{BPM}) - 0.5 \times D_{\text{harmonic}}(\text{BPM}, \text{Current BPM})$$

The penalty term acts as a mathematical **inertia gatekeeper**, preventing erratic BPM flips unless a new tempo presents overwhelmingly strong evidence.

### 4. Confidence-Adaptive Flywheel Modulation
Rather than abruptly jumping or resetting the phase, the continuous speaker flywheel modulates its soft-snap strength based on real-time Pearson confidence:

| Confidence Range | Trust Level | Action |
| :--- | :--- | :--- |
| **$\text{Confidence} > 0.30$** | **Locked / High Trust** | Flywheel pulls $50\%$ towards $\phi_{\text{target}}$ per update for rapid, tight lock. |
| **$0.15 \le \text{Confidence} \le 0.30$** | **Moderate Trust** | Flywheel gently nudges $15\%$ towards $\phi_{\text{target}}$, filtering out noisy transients. |
| **$\text{Confidence} < 0.15$** | **Coasting / Low Trust** | Flywheel ignores phase corrections entirely ($0\%$ snap) and freewheels with perfect momentum across breakdowns or silent pauses. |

