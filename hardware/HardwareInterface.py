from abc import ABC, abstractmethod

class HardwareInterface(ABC):
    """
    Strict hardware interface decoupling physical layout from the logic engine.
    Ensures that any custom pixel pusher correctly exposes the expected methods.
    """

    @abstractmethod
    def show(self):
        """Push the current array state to the hardware buffer."""
        pass

    @abstractmethod
    def set_pixel(self, index, color):
        """Set a single pixel's color."""
        pass

    @abstractmethod
    def clear(self):
        """Turn off all pixels."""
        pass

    @abstractmethod
    def __len__(self):
        """Return the total number of LEDs."""
        pass

    @abstractmethod
    def __getitem__(self, index):
        """Get the color of a specific pixel or slice."""
        pass

    @abstractmethod
    def __setitem__(self, index, value):
        """Map assignments (like array slices or single indexes) directly to hardware."""
        pass
