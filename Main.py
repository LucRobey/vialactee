from typing import Dict, Any, Optional
import asyncio
import logging
import json
import os
import contextlib
import shutil
import sys
import subprocess

import core.Listener as Listener
import connectors.Local_Microphone as Local_Microphone
import core.Mode_master as Mode_master
import hardware.HardwareFactory as HardwareFactory


def resolve_npm_executable() -> Optional[str]:
    # On Windows, npm is usually exposed as npm.cmd.
    npm_exec = shutil.which("npm") or shutil.which("npm.cmd")
    if npm_exec:
        return npm_exec
    return None


async def launch_webapp(infos: Dict[str, Any]) -> None:
    if not infos.get("startWebApp", True):
        logging.info("Web app autostart disabled by config.")
        return

    project_root = os.path.dirname(os.path.abspath(__file__))
    webapp_dir = os.path.join(project_root, "wabb-interface")
    package_json_path = os.path.join(webapp_dir, "package.json")
    node_modules_path = os.path.join(webapp_dir, "node_modules")
    npm_exec = resolve_npm_executable()

    if not os.path.exists(package_json_path):
        logging.warning("Web app package.json not found at %s. Skipping web app launch.", webapp_dir)
        return
    if not npm_exec:
        logging.error("`npm` command not found. Install Node.js to autostart the web app.")
        return

    webapp_process = None
    install_process = None
    try:
        if not os.path.exists(node_modules_path):
            logging.info("Installing web app dependencies (first launch)...")
            install_process = await asyncio.create_subprocess_exec(
                npm_exec, "install",
                cwd=webapp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            await install_process.communicate()
            if install_process.returncode != 0:
                raise RuntimeError(f"`npm install` failed with code {install_process.returncode}")

        logging.info("Starting web app at http://localhost:5173 ...")
        webapp_process = await asyncio.create_subprocess_exec(
            npm_exec, "run", "dev", "--", "--host", "0.0.0.0",
            cwd=webapp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        await webapp_process.wait()
        if webapp_process.returncode != 0:
            raise RuntimeError(f"Web app process exited with code {webapp_process.returncode}")
            
    except FileNotFoundError:
        logging.error("`npm` command not found. Install Node.js to autostart the web app.")
        return
    except asyncio.CancelledError:
        logging.info("Stopping web app processes...")
        if webapp_process:
            if sys.platform == "win32":
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(webapp_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webapp_process.terminate()
            with contextlib.suppress(ProcessLookupError):
                await webapp_process.wait()
        elif install_process:
            if sys.platform == "win32":
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(install_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                install_process.terminate()
            with contextlib.suppress(ProcessLookupError):
                await install_process.wait()
        raise


async def main() -> None:
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

    # Python 3.10 compatible task cancellation (since you're not on 3.11+)
    tasks = [
        asyncio.create_task(mode_master.update_forever(), name="ModeMaster"),
        asyncio.create_task(local_microphone.listen_forever(), name="Microphone")
    ]
    tasks.append(asyncio.create_task(launch_webapp(infos), name="WebApp"))

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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass