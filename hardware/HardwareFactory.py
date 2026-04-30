def create_hardware(infos):
    """
    Decoupled hardware instantiator.
    Reads HARDWARE_MODE from the infos config to inject the proper hardware interface.
    
    Returns:
        leds1, leds2 (HardwareInterface instances)
    """
    mode = infos.get("HARDWARE_MODE", "auto")

    if mode == "auto":
        try:
            import board
            import neopixel
            mode = "rpi"
        except ImportError:
            mode = "simulation"

    if mode == "simulation":
        import hardware.Fake_leds as Fake_leds
        leds1 = Fake_leds.Fake_leds(785)
        leds2 = Fake_leds.Fake_leds(519)
        return leds1, leds2
        
    elif mode == "rpi":
        import hardware.Rpi_NeoPixels as Rpi_NeoPixels
        leds1 = Rpi_NeoPixels.Rpi_NeoPixels("D21", 785)
        leds2 = Rpi_NeoPixels.Rpi_NeoPixels("D18", 519)
        return leds1, leds2
        
    else:
        raise ValueError(f"Unknown HARDWARE_MODE requested in config: {mode}")
