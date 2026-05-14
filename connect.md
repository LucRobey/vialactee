# Connecting to the Vialactée Web App

This guide explains how to access the interactive control interface from another computer or mobile device, especially when the Vialactée controller is running on a Raspberry Pi.

## 1. Ensure Network Connectivity

Both the Raspberry Pi and your control device (PC, Tablet, or Smartphone) **must be connected to the same local network** (Wi-Fi or Ethernet).

## 2. Find the Raspberry Pi's IP Address

On the Raspberry Pi terminal, run the following command to find its local IP address:

```bash
hostname -I
```

This will return one or more IP addresses (e.g., `192.168.1.45`). Take note of the first one.

## 3. Access the Web Interface

Open a web browser on your other device and enter the following URL, replacing `<IP_ADDRESS>` with the one you found in the previous step:

```text
http://<IP_ADDRESS>:5173
```

### Example:
If your Raspberry Pi's IP is `192.168.1.45`, go to:
`http://192.168.1.45:5173`

---

## Technical Details

- **Web App Port (`5173`)**: The React frontend is served by Vite. When launched via `Main.py`, it uses the `--host 0.0.0.0` flag, making it accessible to the entire network.
- **Backend Port (`8080`)**: The Python orchestration server handles API requests and WebSockets on port `8080`. The web app automatically detects the host IP and connects to the backend at `ws://<IP_ADDRESS>:8080/ws`.

## Troubleshooting

- **Page not loading**: 
    - Verify that `Main.py` is running and the log shows `Starting web app at http://localhost:5173 ...`.
    - Check if the Raspberry Pi firewall (if any) allows traffic on ports `5173` and `8080`.
- **Controls not working**:
    - If the page loads but sliders/buttons don't respond, check the "LIVE DATA STATUS" banner in the UI. It might indicate a failure to connect to the WebSocket on port `8080`.
