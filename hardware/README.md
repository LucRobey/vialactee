# Hardware Abstraction (`/hardware/`)

The `hardware` directory provides an interface layer between the Python code and the physical light-emitting hardware. 

## Key Components:

- **`HardwareInterface.py`**: The base class defining what a hardware controller must be able to do (primarily `update_pixels()` and `show()`).
- **`HardwareFactory.py`**: A factory pattern script that detects the environment and returns the appropriate hardware class.
- **`Rpi_NeoPixels.py`**: The production driver. Uses the `rpi_ws281x` library to physically push data to WS2812b LEDs using the Raspberry Pi's GPIO pins.
- **`Fake_leds.py`**: The development driver. Bootstraps a Pygame window that perfectly simulates the physical dimensions and segment layout of the chandelier, allowing developers to test visual animations on a Windows or Mac PC without needing the real hardware.

## How it works:
When `Mode_master` finishes computing the colors for a frame, it passes an RGB array to the active Hardware instance. Depending on what the `HardwareFactory` instantiated, the array is either drawn to a PC screen or flushed to the Raspberry Pi's GPIO pins.
