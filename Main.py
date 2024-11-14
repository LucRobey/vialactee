import board
import neopixel
pixels1 = neopixel.NeoPixel(board.D18, 2, brightness=1)

import Listener
import Modes.Mode as Mode
import Modes.Rainbow_mode as Rainbow_mode
import Segment

listener = Listener.Listener()
segment = Segment.Segment(pixels1)
rb = Rainbow_mode.Rainbow_mode(listener)


pixels1.fill((100, 0, 0))






while True :
    pass