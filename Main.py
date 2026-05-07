import asyncio
import logging
import json
import os

import core.Listener as Listener
import connectors.Connector as Connector
import connectors.Local_Microphone as Local_Microphone
import core.Mode_master as Mode_master
import hardware.HardwareFactory as HardwareFactory


async def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - [%(name)s] - %(message)s')
    
    config_path = "config/app_config.json"
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        default_config = {
            "startServer"     : False,
            "useMicrophone"   : True,
            "HARDWARE_MODE"   : "auto", # 'auto', 'rpi', or 'simulation'
            "printTimeOfCalculation" : False,
            "printModesDetails"      : True,
            "printMicrophoneDetails" : False,
            "printAppDetails"        : False,
            "printAsservmentDetails" : False,
            "printConfigurationLoads": False,
            "printConfigChanges"     : False,
            
            "modesToPrintDetails"    : ["PSG"]
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)

    with open(config_path, 'r') as f:
        infos = json.load(f)
    
    listener = Listener.Listener(infos)
    
    leds1, leds2 = HardwareFactory.create_hardware(infos)
    mode_master = Mode_master.Mode_master(listener, infos, leds1, leds2)                                 
   
    local_microphone = Local_Microphone.Local_Microphone(listener, infos)

    # Initialize the Connector with the mode_master
    connector = Connector.Connector(mode_master , infos)

    # Set connector
    mode_master.set_connector(connector)

    # Python 3.10 compatible task cancellation (since you're not on 3.11+)
    tasks = [
        asyncio.create_task(mode_master.update_forever(), name="ModeMaster"),
        asyncio.create_task(local_microphone.listen_forever(), name="Microphone")
    ]
    if infos.get("startServer", False):
        tasks.append(asyncio.create_task(connector.start_server(), name="Server"))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # If any task completed or crashed, gracefully cancel the remaining ones
        for task in pending:
            task.cancel()
            
        # Wait for the cancelled tasks to finish cleaning up
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
            
        # Re-raise exceptions from the crashed task(s)
        for task in done:
            if task.exception():
                raise task.exception()
                
    except Exception as e:
        logging.error(f"Critical error in main task group: {e}")

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())