import asyncio

import core.Listener as Listener
import connectors.Connector as Connector
import connectors.Local_Microphone as Local_Microphone
import core.Mode_master as Mode_master
import hardware.HardwareFactory as HardwareFactory


async def main():
    
    infos = {
        "startServer"     : False ,
        "useGlobalMatrix" : False ,
        "useMicrophone"   : True  ,
        "HARDWARE_MODE"   : "simulation",
        "onRaspberry"     : False  ,    #si tu veux compiler sur ton ordi, met en commentaire plus haut import neopixel et import board dans Mode_master, et met aussi en commentaire import Serial dans ESP32_microphone, et l'initialisation des leds dans mode_master

        "printTimeOfCalculation" : False ,
        "printModesDetails"      : True ,
        "printMicrophoneDetails" : False ,
        "printAppDetails"        : False ,
        "printAsservmentDetails" : False ,
        "printConfigurationLoads": False ,
        "printConfigChanges"     : False ,

        "modesToPrintDetails"    : ["PSG"]
    }
    
    listener = Listener.Listener(infos)
    
    leds1, leds2 = HardwareFactory.create_hardware(infos)
    mode_master = Mode_master.Mode_master(listener, infos, leds1, leds2)                                 
   
    local_microphone = Local_Microphone.Local_Microphone(listener.fft_band_values , infos, chromaValues=listener.chroma_values)

    # Initialize the Connector with the mode_master
    connector = Connector.Connector(mode_master , infos)

    # Set connector
    mode_master.set_connector(connector)

    mode_master_task = asyncio.create_task(mode_master.update_forever())
    microphone_task = asyncio.create_task(local_microphone.listen_forever())  # Microphone listening loop
    
    tasks_to_run = [mode_master_task, microphone_task]
    if infos.get("startServer", False):
        server_task = asyncio.create_task(connector.start_server())  # Start the server
        tasks_to_run.append(server_task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks_to_run)

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())