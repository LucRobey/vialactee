# Segment Internal Architecture

The `Segment` class is the crucial bridge between the mathematical visual modes and the physical hardware LEDs. It acts as a local state machine that manages its own buffers, instantiates the modes, handles complex transitions, and ultimately flushes the computed colors to the hardware.

Here is a visual breakdown of how it operates internally, followed by a detailed explanation of its core mechanisms.

## 1. Flowchart & Architecture

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
        State[(self.is_in_transition)]:::state
  
        CmdForce -->|Instant Swap| StateNormal[False]
        CmdChange -->|Set Target| StateTrans[True]
  
        StateNormal -.-> State
        StateTrans -.-> State
    end

    subgraph Main Execution Loop: update
        UpdateLoop[self.update_td]:::engine
  
        UpdateLoop --> CheckState{self.is_in_transition?}
  
        CheckState -->|False| RunActive[Run self.modes\nactive_mode]
        RunActive -->|Writes to| RGB1
  
        CheckState -->|True| CheckTD{td.state?}
        CheckTD -->|TRANSITION_DUAL| RunBoth[Run Active Mode\n&\nRun Target Mode]
  
        RunBoth -->|Active Writes to| RGB1
        RunBoth -->|Target Writes to| RGB2
  
        RunBoth --> Mix[Transition_Engine.py]:::engine
        Mix -->|Spatially mixes RGB2 into RGB1\nusing td.transition_progress| RGB1
  
        CheckTD -->|PASSATION| FinishTrans[Swap Active Mode\nis_in_transition = False]
        FinishTrans -.-> StateNormal
    end

    subgraph Hardware Output
        UpdateLeds[self.update_leds]:::hw
        GlobalLEDs[(Global LED Array\nself.leds)]:::hw
  
        CheckState -->|End of Loop| UpdateLeds
        CheckTD -->|End of Loop| UpdateLeds
  
        RGB1 -->|Flushed using self.way\nUP/DOWN direction| UpdateLeds
        UpdateLeds -->|Writes to Hardware Indexes| GlobalLEDs
    end
```

## 2. Internal Workflow Explained

### 1. Dynamic Initialization
On boot, the segment reads `modes.json` and instantiates every allowed visual pattern (e.g. `Rainbow`, `Matrix Rain`). These are stored in the `self.modes` dictionary for $O(1)$ instant lookup.

### 2. Dual Buffering
The segment owns two $N \times 3$ NumPy matrices (`rgb_list` and `dual_rgb_list`).

### 3. State Machine
*   When `self.is_in_transition` is false, the active mode does its math and directly mutates `rgb_list`.
*   When `self.is_in_transition` is true, it queries the `Transition_Director` (`td`). If `td.state == "TRANSITION_DUAL"`, the *old* mode continues mutating `rgb_list`, but the *new* mode is temporarily redirected to mutate `dual_rgb_list`.
*   If `td.state == "PASSATION"`, the segment finalizes the swap and turns off `is_in_transition`.

### 4. Transition Engine
During a transition, the `Transition_Engine` is called. It applies physics and spatial mapping (like a gravity drop or a fade) to smoothly overwrite `rgb_list` with the pixels from `dual_rgb_list` based on the synchronized global `td.transition_progress`.

### 5. Hardware Flush
At the very end of the `update()` loop, `update_leds()` takes whatever is finalized in `rgb_list`, reverses the direction if `self.way == "DOWN"`, and writes it into the global hardware `self.leds` array to be sent to the Pi/ESP32.
