import subprocess
import sys
import os


def _set_runtime_flags(infos, configured_mode, resolved_mode):
    infos["hardwareModeConfigured"] = configured_mode
    infos["resolvedHardwareMode"] = resolved_mode
    infos["simulationMode"] = resolved_mode == "simulation"
    infos["onRaspberry"] = resolved_mode == "rpi"

def create_hardware(infos):
    """
    Decoupled hardware instantiator.
    Reads HARDWARE_MODE from the infos config to inject the proper hardware interface.
    
    Returns:
        leds1, leds2 (HardwareInterface instances)
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

    if mode == "simulation":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Udp_Sender as Udp_Sender
        
        import atexit
        # Launch the Fake ESP32 visualizer as a background process
        # This allows PyGame to run in its own process without blocking the main event loop
        script_path = os.path.join(os.path.dirname(__file__), "Fake_ESP32.py")
        proc = subprocess.Popen([sys.executable, script_path])
        atexit.register(proc.terminate)
        
        port1 = infos.get("led_port1", 9001)
        port2 = infos.get("led_port2", 9002)
        count1 = infos.get("led_count1", 785)
        count2 = infos.get("led_count2", 519)
        # Send UDP packets to localhost where the Fake_ESP32 is listening
        leds1 = Udp_Sender.Udp_Sender("127.0.0.1", port1, count1)
        leds2 = Udp_Sender.Udp_Sender("127.0.0.1", port2, count2)
        return leds1, leds2
        
    elif mode == "esp32":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Udp_Sender as Udp_Sender
        
        esp32_ip = infos.get("esp32_ip", "192.168.1.X")
        if esp32_ip == "192.168.1.X":
            raise ValueError("Invalid ESP32 IP address configured: '192.168.1.X'. Please configure esp32_ip in app_config.json")
        print(f"=== INITIALIZING ESP32 HARDWARE MODE ON IP: {esp32_ip} ===")
        
        port1 = infos.get("led_port1", 9001)
        port2 = infos.get("led_port2", 9002)
        count1 = infos.get("led_count1", 785)
        count2 = infos.get("led_count2", 519)
        # Send UDP packets to the real ESP32 IP
        leds1 = Udp_Sender.Udp_Sender(esp32_ip, port1, count1)
        leds2 = Udp_Sender.Udp_Sender(esp32_ip, port2, count2)
        return leds1, leds2
        
    elif mode == "rpi":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Rpi_NeoPixels as Rpi_NeoPixels
        pin1 = infos.get("led_pin1", "D21")
        pin2 = infos.get("led_pin2", "D18")
        count1 = infos.get("led_count1", 785)
        count2 = infos.get("led_count2", 519)
        leds1 = Rpi_NeoPixels.Rpi_NeoPixels(pin1, count1)
        leds2 = Rpi_NeoPixels.Rpi_NeoPixels(pin2, count2)
        return leds1, leds2
        
    else:
        raise ValueError(f"Unknown HARDWARE_MODE requested in config: {mode}")

