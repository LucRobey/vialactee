# Transition_Director Internal Architecture

The `Transition_Director` operates as a time-based state machine that directs the `Mode_master` on when to change visual modes. It is responsible for orchestrating the timing and type of transitions across the LED segments.

Here is a visual breakdown of how it operates internally, followed by a detailed explanation of its core mechanisms.

## 1. Flowchart & Architecture

This flowchart details how the class initializes, handles the active `update()` frame loop, and processes timers to trigger new configurations.

```mermaid
graph TD
    Init(Initialization)
    LoadSegments[Load segments config]
    Standby((Idle State))

    subgraph UpdateLoop
        CheckState{Is TRANSITION DUAL}
        IncProgress[Add step to progress]
        CheckComplete{Progress reached max}
        SetPassation[Set PASSATION state]
        CheckTimer{Is Timer expired}
        TriggerTimer[Trigger Timer]
        Command[Change configuration]
        ResetTimer[Update next change time]
        EndUpdate(Wait for next frame)
        
        CheckState -->|Yes| IncProgress
        IncProgress --> CheckComplete
        CheckComplete -->|Yes| SetPassation
        CheckComplete -->|No| CheckTimer
        SetPassation --> CheckTimer
        CheckState -->|No| CheckTimer
        
        CheckTimer -->|Yes| TriggerTimer
        TriggerTimer --> Command
        Command --> ResetTimer
        
        CheckTimer -->|No| EndUpdate
        ResetTimer --> EndUpdate
    end

    Init --> LoadSegments
    LoadSegments --> Standby
    Standby -.-> CheckState
    
    subgraph ExternalCommands
        StartTrans(Start transition)
        SetState[Set TRANSITION DUAL]
        ResetProg[Reset progress to zero]
        CalcStep[Calculate step duration]
        
        StartTrans --> SetState
        SetState --> ResetProg
        ResetProg --> CalcStep
    end
```

This diagram shows the two primary states (`PASSATION` and `TRANSITION_DUAL`) and what causes the director to switch between them.

```mermaid
stateDiagram
    [*] --> PASSATION : System start
    
    PASSATION --> TRANSITION_DUAL : start_transition called
    
    state TRANSITION_DUAL {
        [*] --> Progressing
        Progressing --> Progressing : add step to progress
        Progressing --> [*] : progress reached 1.0
    }
    
    TRANSITION_DUAL --> PASSATION : Transition complete
```

## 2. Internal Workflow Explained

### 1. Geometry Mapping
On startup, it parses `config/segments.json` to map out which segments are vertical vs horizontal, storing them for transition effects.

### 2. State Management
It switches between `PASSATION` (normal operation/standby) and `TRANSITION_DUAL` (actively crossfading or switching between modes).

### 3. Timer-Based Overrides
In its `update()` loop, it monitors `next_change_time`. When this timer expires, it proactively commands the `mode_master` to execute a global transition (currently default to an `"explosion"` effect for testing) and resets the timer.
