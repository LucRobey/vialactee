# AXIOM-02: Zero Dynamic Heap Allocations in Render Hot Path

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_02_zero_allocation.py`  

---

## 1. Specification

1. **Hot-Path Heap Allocation Prohibition:**
   In the active render loop (`Mode_master.update()`, `Segment.update()`, `Mode.render()`, `Transition_Engine.apply_transition()`) and in the PortAudio audio stream callback (`Local_Microphone`), dynamic object instantiation is strictly prohibited.
2. **Prohibited Operations Inside Hot Loop:**
   - Instantiation of NumPy arrays via `np.zeros()`, `np.empty()`, `np.ones()`, `np.array()`, `np.where()`.
   - Python heap allocations: list comprehensions, dictionary creation, dynamic string formatting (`f"..."`, `str(type(...))`), set mutations.
   - Dynamic class or lambda instantiation.
3. **Approved Memory Mechanisms:**
   - Pre-allocate all buffers, lookup tables, and color matrices during `__init__()`.
   - Mutate buffers exclusively in-place via slice assignment (`self.rgb_list[:] = ...`), `np.copyto()`, or pre-allocated output targets (`out=buffer`).
   - Cache dynamic type checks (e.g. `self._is_rpi_hardware`) once at instantiation.
4. **WebSocket & Telemetry Decoupling:**
   - WebSocket serialization (`json.dumps()`, snapshot building) must never execute inline within the 30 FPS render loop.
   - `Connector.on_frame_tick()` must execute in $\mathbf{0.0\text{ ms}}$ when zero WebSockets are connected.
   - Active WebSocket clients receive updates decoupled via dirty-flag checks (`mode_master._state_dirty`), transition edge triggers, and a 1.0 Hz background heartbeat task.

---

## 2. Invariant Rules for Mode Authors

```python
# FORBIDDEN (Trips Axiom 2):
def run(self):
    self.rgb_list = np.zeros((self.nb_leds, 3), dtype=np.int32) # Allocates every frame!

# MANDATORY (Zero-Allocation Compliant):
def __init__(self, ...):
    # Pre-allocated once at initialization
    self._scratch = np.zeros((self.nb_leds, 3), dtype=np.int32)

def run(self):
    self.rgb_list.fill(0) # In-place reset
```

---

## 3. Violation Conditions

- Dynamic array creation detected via memory profiler or AST inspection within `render()`, `update()`, or PortAudio callback.
- Type string introspection (`str(type(x))`) inside per-frame methods.
- Blocking or heap-allocating WebSocket broadcasts invoked synchronously on every frame.
