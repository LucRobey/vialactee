import board
import neopixel
#pixels1 = neopixel.NeoPixel(board.D18, 39, brightness=1)

import Listener
import modes.Mode as Mode
import modes.Rainbow_mode as Rainbow_mode
import Segment
import Mode_master as Mode_master

#listener = Listener.Listener()
#segment1 = Segment.Segment(listener , pixels1)

#pixels1.fill((100, 0, 0))

mm = Mode_master.Mode_master()

while True :
    mm.update()
    