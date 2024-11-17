import board
import neopixel
pixels1 = neopixel.NeoPixel(board.D18, 40, brightness=1)

import Listener
import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import Segment

listener = Listener.Listener()
segment1 = Segment.Segment(listener , pixels1)

pixels1.fill((100, 0, 0))



while True :
    listener.update()
    segment1.update()