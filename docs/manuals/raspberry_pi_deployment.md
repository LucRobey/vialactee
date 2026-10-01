# Raspberry Pi 4 Deployment & Operations Manual

> **Location:** `docs/manuals/raspberry_pi_deployment.md` (Tier 2 Operational Manual)  
> **Target Device:** Raspberry Pi 4B (Raspberry Pi OS 64-bit Lite)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-04](../axioms/AXIOM-04_NETWORK_PROTOCOLS.md)

---

## 1. System Requirements & Hardware Setup

1. **Host:** Raspberry Pi 4 Model B (4GB or 8GB recommended).
2. **Audio Interface:** USB Sound Card (e.g. Behringer U-Control UCA202 or USB Audio DAC) for clean line-out to speakers and line-in from aux sources.
3. **Network:** Connected to local Wi-Fi router or Ethernet (assigned static IP, e.g. `192.168.1.40`).
4. **ESP32 LED Receiver:** Configured on the same subnet (`192.168.1.41`) listening on UDP ports 9001 and 9002.

---

## 2. Audio Routing & Bluetooth A2DP Sink

To stream music directly from a smartphone to the Raspberry Pi:
1. Install `bluez-alsa` or `pulseaudio-module-bluetooth`:
   ```bash
   sudo apt-get install -y bluez-tools pulseaudio-module-bluetooth
   ```
2. Pair smartphone via `bluetoothctl`.
3. In `config/app_config.json`, configure:
   ```json
   {
     "audio_preset": "spotify_aux",
     "HARDWARE_MODE": "esp32",
     "hardware_profile": "full",
     "esp32_ip": "192.168.1.41"
   }
   ```

---

## 3. Systemd Service Deployment

To run Vialactée automatically at system boot as an unprivileged service:

1. Create `/etc/systemd/system/vialactee.service`:
   ```ini
   [Unit]
   Description=Vialactee LED Chandelier Orchestrator
   After=network.target sound.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/vialactee
   ExecStart=/home/pi/vialactee/venv/bin/python Main.py
   Restart=on-failure
   RestartSec=5s
   Environment=PYTHONUNBUFFERED=1
   Environment=SDL_VIDEODRIVER=dummy

   [Install]
   WantedBy=multi-user.target
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vialactee.service
   sudo systemctl start vialactee.service
   ```
3. Check logs:
   ```bash
   journalctl -u vialactee.service -f
   ```
