import board
import neopixel
import asyncio
#pixels1 = neopixel.NeoPixel(board.D18, 39, brightness=1)

import Listener
import modes.Mode as Mode
import connectors.Connector as  Connector
import connectors.ESP32_Microphone as ESP32_Microphone
import modes.Rainbow_mode as Rainbow_mode
import Segment
import Mode_master as Mode_master


async def main():
    # Create instances of necessary classes
    listener = Listener.Listener()  # Assuming Listener class is set up correctly
    mode_master = Mode_master.Mode_master(listener)  # Assuming None for now, replace as needed
   
    esp32_microphone = ESP32_Microphone.ESP32_Microphone(listener.fft_band_values , False)

    # Initialize the Connector with the mode_master
    connector = Connector.Connector(mode_master)

    # Set connector for Mode_master if needed (depending on your design)
    mode_master.set_connector(connector)

    # Start the server and update loops concurrently
    server_task = asyncio.create_task(connector.start_server())  # Start the server
    #listener_task = asyncio.create_task(listener.update_forever())  # Listener's forever update loop
    mode_master_task = asyncio.create_task(mode_master.update_forever())
    microphone_task = asyncio.create_task(esp32_microphone.listen_forever())  # Microphone listening loop
    
    # Wait for all tasks to complete (in an actual application, you might use other means)
    await asyncio.gather(server_task, mode_master_task, microphone_task)

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())