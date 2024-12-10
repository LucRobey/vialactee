import asyncio

import Listener
import connectors.Connector as  Connector
import connectors.ESP32_Microphone as ESP32_Microphone
import Mode_master as Mode_master


async def main():
    
    infos = {
        "useGlobalMatrix" : False ,
        "useMicrophone"   : False ,
        "onRaspberry"     : True  ,    #si tu veux compiler sur ton ordi, met en commentaire plus haut import neopixel et import board dans Mode_master, et met aussi en commentaire import Serial dans ESP32_microphone, et l'initialisation des leds dans mode_master

        "printTimeOfCalculation" : False ,
        "printModesDetails"      : True  ,
        "printMicrophoneDetails" : False ,
        "printAppDetails"        : False ,
        "printAsservmentDetails" : False ,
        "printConfigurationLoads": False ,
        "printConfigChanges"     : True  ,

        "modesToPrintDetails"    : ["Christmas_mode_2"]
    }
    
    listener = Listener.Listener(infos)
    mode_master = Mode_master.Mode_master(listener, infos)                                 
   
    esp32_microphone = ESP32_Microphone.ESP32_Microphone(listener.fft_band_values , infos)

    # Initialize the Connector with the mode_master
    connector = Connector.Connector(mode_master , infos)

    # Set connector
    mode_master.set_connector(connector)

    # Start the server and update loops concurrently
    server_task = asyncio.create_task(connector.start_server())  # Start the server
    mode_master_task = asyncio.create_task(mode_master.update_forever())
    microphone_task = asyncio.create_task(esp32_microphone.listen_forever())  # Microphone listening loop
    
    # Wait for all tasks to complete
    await asyncio.gather(server_task, mode_master_task, microphone_task)

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())