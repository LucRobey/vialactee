from hardware.HardwareInterface import HardwareInterface

class Rpi_NeoPixels(HardwareInterface):
    """
    Physical Raspberry Pi hardware wrapper for WS2812b via adafruit-neoPixel.
    """
    def __init__(self, pin_name, nb_of_leds):
        import neopixel
        import board
        
        # Resolve the pin from the 'board' module dynamically
        pin_attr = getattr(board, pin_name)
        self.nb_of_leds = nb_of_leds
        
        # Initialize the hardware, disabling auto_write to drastically improve performance 
        # (Mode_master explicitly calls .show() once per frame)
        self.leds = neopixel.NeoPixel(pin_attr, nb_of_leds, brightness=1, auto_write=False)

    def show(self):
        self.leds.show()

    def set_pixel(self, index, color):
        self.leds[index] = color

    def clear(self):
        self.leds.fill((0, 0, 0))
        self.show()

    def __len__(self):
        return self.nb_of_leds

    def __getitem__(self, index):
        return self.leds[index]

    def __setitem__(self, index, value):
        self.leds[index] = value
