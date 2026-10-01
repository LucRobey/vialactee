# AXIOM-04: Network Transport Protocols & UDP MTU Bounds

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_04_network_limits.py`, `hardware/Udp_Sender.py`, `connectors/Connector.py`  

---

## 1. Specification

1. **UDP Packet MTU Safety:**
   Pixel packets streamed over UDP (Port 9001 for Channel 1, Port 9002 for Channel 2) to physical ESP32 or simulation visualizers must never exceed the 1,472-byte unfragmented Ethernet/Wi-Fi MTU limit.
2. **Chunking Bounds:**
   - Maximum LEDs per UDP datagram: **400 LEDs**.
   - Maximum Payload: $400 \times 3\text{ bytes (RGB)} = 1,200\text{ bytes}$.
   - Protocol Header: 2 bytes (`chunk_index`, `total_chunks`).
   - Total Datagram Size: $\mathbf{1,202\text{ bytes}} \le 1,472\text{ bytes}$ (leaves 270 bytes safety margin against network fragmentation).
3. **Telemetry Throttling on Port 9003 / WebSocket:**
   - Active transition telemetry broadcasts must be rate-limited to $\le \mathbf{10.0\text{ Hz}}$ (minimum interval $\Delta t \ge 100\text{ ms}$).
   - Steady-state telemetry heartbeat runs at **1.0 Hz** to preserve client connection state.
   - Zero-client bypass: When `len(active_websockets) == 0`, telemetry processing overhead must be **0.0 ms**.
4. **WebSocket Control Acknowledgments:**
   - Incoming control instructions from web clients must receive immediate structured JSON acknowledgments (`{"status": "ok", "action": ...}`) without blocking the visual loop.

---

## 2. Packet Structure Definition

```
UDP Datagram (Port 9001/9002):
[Byte 0: Chunk Index (uint8)]
[Byte 1: Total Chunks (uint8)]
[Bytes 2..1201: Raw RGB Bytes (3 bytes per LED, up to 400 LEDs)]
Total <= 1,202 Bytes
```

---

## 3. Violation Conditions

- Any UDP payload transmission exceeding 1,472 bytes.
- Streaming telemetry over WebSocket faster than 10 Hz during transitions or unthrottled on steady-state.
- Dropped frames caused by network socket write blocking on the main asyncio loop.
