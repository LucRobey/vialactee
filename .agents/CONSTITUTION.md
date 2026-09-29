# The Constitution of Project Vialactée 🌟
*Location: .agents/CONSTITUTION.md*

### Article I: Core Mission
Drive a 1,304-LED physical chandelier with musically coherent, visually breathtaking, 
fully autonomous lighting at 30 FPS on Raspberry Pi 4 hardware with zero live human intervention.

### Article II: The 5 Non-Negotiable Technical Laws
1. **The 33.33ms Frame Budget (Raspberry Pi 4 Safety)**:
   - Target framerate is **30 FPS** (33.33 ms frame period).
   - Total compute (DSP + 11 modes + spatial blend + UDP packing) must complete in **≤ 20.0 ms** on ARM Cortex-A72.
   - A minimum **13.33 ms (40%)** safety margin is reserved for OS scheduling jitter.
2. **Zero Heap Allocations in the LED Render Hot Path**:
   - No Python object instantiation, dynamic NumPy allocations (`np.where`, `np.zeros`), or coroutine task creation inside the 30 FPS LED rendering loop (Modes, Math, DSP, Blending).
   - Pre-allocated buffers and in-place operations (`out=`, `np.putmask`, `memoryview`) are mandatory.
   - WebSocket state telemetry serialization is decoupled from the 30 FPS render loop and capped at 10 Hz.
3. **Agent-Native Navigability (The 500-Line Rule & Ratchet)**:
   - No new or modified production file may exceed **500 lines** (early warning triggers at 450 lines).
   - The 4 legacy core files (`MultiBandOnsetAudioAnalyzer.py`, `Mode_master.py`, `AudioAnalyzer.py`, `Transition_Engine.py`) are grandfathered under a strict ratchet: they may shrink, but never expand.
   - No loose untyped `Dict[str, Any]` contracts in hot frame paths.
4. **Wire & UI Compatibility (Zero Frontend Regressions)**:
   - `connectors/Connector.py` maintains `{ "segments": [...], "cables": [...] }` formatting for the React Topology Editor.
   - All WebSocket instructions receive immediate acknowledgments (`{"ok": true, ...}`).
5. **Fast Headless Unit Test Loop**:
   - Pure unit tests (`pytest -m "not benchmark"`) must execute headlessly with `SDL_VIDEODRIVER=dummy`.
   - Test execution time (excluding Python import overhead) must remain under **2.0 seconds**.
