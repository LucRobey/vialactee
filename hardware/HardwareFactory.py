import subprocess
import sys
import os
import json
from config.Configuration_manager import resolve_segments_file_path


def _set_runtime_flags(infos, configured_mode, resolved_mode):
    infos["hardwareModeConfigured"] = configured_mode
    infos["resolvedHardwareMode"] = resolved_mode
    infos["simulationMode"] = resolved_mode == "simulation"
    infos["onRaspberry"] = resolved_mode == "rpi"


def _get_channel_specs(infos=None):
    """
    Read active segment JSON and determine channel count and LED sizes dynamically.
    Returns list of dicts: [{'channel': 1, 'count': 785, 'port': 9001, 'pin': 'D21'}, ...]
    """
    if infos is None:
        infos = {}
    segments_path = resolve_segments_file_path(infos)
    channel_specs = []

    try:
        with open(segments_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        idx = 1
        while f"segs_{idx}" in data:
            channel_segments = data[f"segs_{idx}"]
            channel_count = sum(seg.get("size", 0) for seg in channel_segments if isinstance(seg, dict))
            port = infos.get(f"led_port{idx}", 9000 + idx)
            default_pin = "D21" if idx == 1 else "D18"
            pin = infos.get(f"led_pin{idx}", default_pin)
            channel_specs.append({
                "channel": idx,
                "count": channel_count if channel_count > 0 else infos.get(f"led_count{idx}", 100),
                "port": port,
                "pin": pin
            })
            idx += 1
    except Exception as e:
        # Fallback to default 2 channels
        count1 = infos.get("led_count1", 785)
        count2 = infos.get("led_count2", 519)
        channel_specs = [
            {"channel": 1, "count": count1, "port": infos.get("led_port1", 9001), "pin": infos.get("led_pin1", "D21")},
            {"channel": 2, "count": count2, "port": infos.get("led_port2", 9002), "pin": infos.get("led_pin2", "D18")},
        ]

    if not channel_specs:
        channel_specs = [
            {"channel": 1, "count": infos.get("led_count1", 100), "port": 9001, "pin": "D21"}
        ]

    return channel_specs


def create_hardware(infos):
    """
    Decoupled hardware instantiator.
    Reads HARDWARE_MODE and active segment profile to inject the proper hardware interfaces.
    
    Returns:
        tuple of HardwareInterface instances (e.g. (leds1,) or (leds1, leds2))
    """
    configured_mode = infos.get("HARDWARE_MODE", "auto")
    mode = configured_mode
    if mode == "auto":
        try:
            import board
            import neopixel
            mode = "rpi"
        except Exception:
            mode = "simulation"

    channel_specs = _get_channel_specs(infos)

    if mode == "simulation":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Udp_Sender as Udp_Sender
        
        import atexit
        # Launch the Fake ESP32 visualizer as a background process
        script_path = os.path.join(os.path.dirname(__file__), "Fake_ESP32.py")
        proc = subprocess.Popen([sys.executable, script_path])
        atexit.register(proc.terminate)
        
        hardware_list = []
        for spec in channel_specs:
            sender = Udp_Sender.Udp_Sender("127.0.0.1", spec["port"], spec["count"])
            hardware_list.append(sender)
        return tuple(hardware_list)
        
    elif mode == "esp32":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Udp_Sender as Udp_Sender
        
        esp32_ip = infos.get("esp32_ip", "192.168.1.X")
        if esp32_ip == "192.168.1.X":
            raise ValueError("Invalid ESP32 IP address configured: '192.168.1.X'. Please configure esp32_ip in app_config.json")
        print(f"=== INITIALIZING ESP32 HARDWARE MODE ON IP: {esp32_ip} ({len(channel_specs)} channels) ===")
        
        hardware_list = []
        for spec in channel_specs:
            sender = Udp_Sender.Udp_Sender(esp32_ip, spec["port"], spec["count"])
            hardware_list.append(sender)
        return tuple(hardware_list)
        
    elif mode == "rpi":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Rpi_NeoPixels as Rpi_NeoPixels
        hardware_list = []
        for spec in channel_specs:
            strip = Rpi_NeoPixels.Rpi_NeoPixels(spec["pin"], spec["count"])
            hardware_list.append(strip)
        return tuple(hardware_list)
        
    else:
        raise ValueError(f"Unknown HARDWARE_MODE requested in config: {mode}")
