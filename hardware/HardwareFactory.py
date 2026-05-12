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
        
        # Launch the Fake ESP32 visualizer as a background process
        # This allows PyGame to run in its own process without blocking the main event loop
        script_path = os.path.join(os.path.dirname(__file__), "Fake_ESP32.py")
        subprocess.Popen([sys.executable, script_path])
        
        # Send UDP packets to localhost where the Fake_ESP32 is listening
        leds1 = Udp_Sender.Udp_Sender("127.0.0.1", 9001, 785)
        leds2 = Udp_Sender.Udp_Sender("127.0.0.1", 9002, 519)
        return leds1, leds2
        
    elif mode == "rpi":
        _set_runtime_flags(infos, configured_mode, mode)
        import hardware.Rpi_NeoPixels as Rpi_NeoPixels
        leds1 = Rpi_NeoPixels.Rpi_NeoPixels("D21", 785)
        leds2 = Rpi_NeoPixels.Rpi_NeoPixels("D18", 519)
        return leds1, leds2
        
    else:
        raise ValueError(f"Unknown HARDWARE_MODE requested in config: {mode}")

