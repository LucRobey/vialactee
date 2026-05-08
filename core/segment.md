# Segment Internal Architecture

The `Segment` class is the crucial bridge between the mathematical visual `modes` and the physical hardware LEDs. It acts as a local state machine that manages its own buffers, instantiates the modes, handles complex transitions, and ultimately flushes the computed colors to the hardware.

Here is a visual representation of how `Segment.py` works internally:

```mermaid

flowchart TD
    %% Define styles
    classDef init fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#dfe6e9
    classDef buffer fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff
    classDef state fill:#6c5ce7,stroke:#a29bfe,stroke-width:2px,color:#fff
    classDef engine fill:#e17055,stroke:#fab1a0,stroke-width:2px,color:#fff
    classDef hw fill:#00b894,stroke:#55efc4,stroke-width:2px,color:#fff

    subgraph Initialization
        Init[Segment.__init__]:::init
        LoadJSON[Read config/modes.json]:::init
        InitModes[Instantiate Mode Objects]:::init
  
        Init --> LoadJSON --> InitModes
        InitModes -.->|Populates| ModeDict[(self.modes Dictionary)]
    end

    subgraph Memory Buffers
        RGB1[(rgb_list\nPrimary Buffer)]:::buffer
        RGB2[(dual_rgb_list\nSecondary Buffer)]:::buffer
    end

    subgraph Mode Swapping Logic
        CmdChange[change_mode]:::state
        CmdForce[force_mode / execute_mode_swap]:::state
        State[(self.state)]:::state
  
        CmdForce -->|Instant Swap| StateNormal[NORMAL]
        CmdChange -->|Set Target & Progress| StateTrans[TRANSITION_DUAL]
  
        StateNormal -.-> State
        StateTrans -.-> State
    end

    subgraph Main Execution Loop: update
        UpdateLoop[self.update]:::engine
  
        UpdateLoop --> CheckState{Is self.state ?}
  
        CheckState -->|NORMAL| RunActive[Run self.modes\nactive_mode]
        RunActive -->|Writes to| RGB1
  
        CheckState -->|TRANSITION_DUAL| RunBoth[Run Active Mode\n&\nRun Target Mode]
  
        RunBoth -->|Active Writes to| RGB1
        RunBoth -->|Target Writes to| RGB2
  
        RunBoth --> Mix[Transition_Engine.py]:::engine
        Mix -->|Spatially mixes RGB2 into RGB1| RGB1
  
        Mix --> TransDone{Progress >= 1.0?}
        TransDone -->|Yes| FinishTrans[Swap Active Mode\nSet state NORMAL]
        FinishTrans -.-> StateNormal
    end

    subgraph Hardware Output
        UpdateLeds[self.update_leds]:::hw
        GlobalLEDs[(Global LED Array\nself.leds)]:::hw
  
        CheckState -->|End of Loop| UpdateLeds
        TransDone -->|No| UpdateLeds
  
        RGB1 -->|Flushed using self.way\nUP/DOWN direction| UpdateLeds
        UpdateLeds -->|Writes to Hardware Indexes| GlobalLEDs
    end

```

## Key Mechanisms:

1. **Dynamic Initialization**: On boot, the segment reads `modes.json` and instantiates every allowed visual pattern (e.g. `Rainbow`, `Matrix Rain`). These are stored in the `self.modes` dictionary for $O(1)$ instant lookup.
2. **Dual Buffering**: The segment owns two $N \times 3$ NumPy matrices (`rgb_list` and `dual_rgb_list`).
3. **State Machine**:
   - Under `NORMAL` state, the active mode does its math and directly mutates `rgb_list`.
   - Under `TRANSITION_DUAL` state, the *old* mode continues mutating `rgb_list`, but the *new* mode is temporarily redirected to mutate `dual_rgb_list`.
4. **Transition Engine**: During a transition, the `Transition_Engine` is called. It applies physics and spatial mapping (like a gravity drop or a fade) to smoothly overwrite `rgb_list` with the pixels from `dual_rgb_list`.
5. **Hardware Flush**: At the very end of the `update()` loop, `update_leds()` takes whatever is finalized in `rgb_list`, reverses the direction if `self.way == "DOWN"`, and writes it into the global hardware `self.leds` array to be sent to the Pi/ESP32.
