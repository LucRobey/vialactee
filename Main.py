from typing import Dict, Any, Optional, List
import asyncio
import atexit
import logging
import json
import os
import contextlib
import shutil
import sys
import subprocess
import argparse

import core.Listener as Listener
import connectors.Local_Microphone as Local_Microphone
import connectors.Local_AudioFile as Local_AudioFile
import connectors.Connector as Connector
import core.Mode_master as Mode_master
import hardware.HardwareFactory as HardwareFactory
import config.Configuration_manager as Configuration_manager


RESTART_REQUESTED = "restart_requested"


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


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vialactée - Interactive Music-Reactive LED Chandelier Controller"
    )
    parser.add_argument(
        "--song", "-s",
        nargs="?",
        const="",
        default=None,
        help="Path or name of local MP3/WAV file to stream and analyze (defaults to Palladium.mp3 if flag passed without value)"
    )
    parser.add_argument(
        "song_pos",
        nargs="?",
        default=None,
        help="Optional positional path or name of local MP3/WAV file"
    )
    parser.add_argument(
        "--mic", "--microphone",
        dest="use_microphone",
        action="store_true",
        default=False,
        help="Force physical microphone input mode"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=False,
        help="Loop the selected audio track instead of advancing through playlist"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        default=None,
        help="Initial lighting mode to activate across all segments"
    )
    parser.add_argument(
        "--profile", "-p",
        type=str,
        choices=["full", "small"],
        default=None,
        help="Hardware profile override ('full' or 'small')"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Rhythm analyzer model class override (e.g. MultiBandOnsetAudioAnalyzer, AudioAnalyzer)"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        default=False,
        help="Enable web connector server on 0.0.0.0:8080"
    )
    parser.add_argument(
        "--panel",
        action="store_true",
        default=False,
        help="Enable real-time music analyzer HUD overlay in the simulator"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/app_config.json",
        help="Path to app configuration file"
    )
    return parser.parse_args(args)


async def main(cli_args: Optional[argparse.Namespace] = None) -> Optional[str]:
    if cli_args is None:
        cli_args = parse_arguments()
    
    config_path = cli_args.config if (cli_args and cli_args.config) else "config/app_config.json"
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        default_config = {
            "startServer"     : False,
            "useMicrophone"   : True,
            "printCpuFpsInfo" : False,
            "HARDWARE_MODE"   : "simulation", # 'auto', 'rpi', or 'simulation'
            "log_level"       : "INFO",
            "show_music_analyser_panel" : True,
            "profiler": {
                "interval_seconds": 5.0,
                "format": "compact",
                "target_fps": 30,
                "alert_threshold_ms": 35.0,
                "track_slowest_mode": True
            }
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)

    with open(config_path, 'r') as f:
        infos = json.load(f)

    if cli_args.profile:
        infos["hardware_profile"] = cli_args.profile
    if cli_args.model:
        infos["analyzer_model"] = cli_args.model
    if cli_args.server:
        infos["startServer"] = True
    if cli_args.panel:
        infos["show_music_analyser_panel"] = True
    if cli_args.loop:
        infos["loop"] = True
        
    from logging.handlers import RotatingFileHandler
    log_level_str = infos.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    file_handler = RotatingFileHandler(
        "vialactee.log", maxBytes=5*1024*1024, backupCount=2, encoding="utf-8"
    )
    console_handler = logging.StreamHandler()
    
    logging.basicConfig(
        level=log_level, 
        format='%(levelname)s - [%(name)s] - %(message)s', 
        force=True,
        handlers=[file_handler, console_handler]
    )
    
    infos = Configuration_manager.resolve_audio_config(infos)

    # Determine audio source (Local_AudioFile vs Local_Microphone)
    target_song = cli_args.song if cli_args.song is not None else cli_args.song_pos
    use_audio_file = False
    song_path = None

    if cli_args.use_microphone:
        use_audio_file = False
        infos["useMicrophone"] = True
    elif target_song is not None:
        use_audio_file = True
        song_path = target_song
    elif infos.get("song") or infos.get("audio_file"):
        use_audio_file = True
        song_path = infos.get("song") or infos.get("audio_file")
    
    listener = Listener.Listener(infos)
    
    hardware_leds = HardwareFactory.create_hardware(infos)

    # Wire the analyzer to the simulator so the HUD panel can render live state
    if infos.get("show_music_analyser_panel", False) and len(hardware_leds) > 0:
        if hasattr(hardware_leds[0], 'set_analyzer'):
            hardware_leds[0].set_analyzer(listener.analyzer)

    mode_master = Mode_master.Mode_master(listener, infos, *hardware_leds)                                 
    atexit.register(mode_master.flush_sync)

    if cli_args.mode:
        for seg in mode_master.segments_list:
            seg.force_mode(cli_args.mode)
   
    if use_audio_file:
        infos["useMicrophone"] = False
        audio_connector = Local_AudioFile.Local_AudioFile(listener, infos, song_path=song_path)
        logging.info(f"(Main) Streaming local audio file: {audio_connector.file_path}")
        if len(hardware_leds) > 0 and hasattr(hardware_leds[0], 'set_audio_player'):
            hardware_leds[0].set_audio_player(audio_connector)
        audio_task = asyncio.create_task(audio_connector.play_forever(), name="AudioPlayer")
    else:
        local_microphone = Local_Microphone.Local_Microphone(listener, infos)
        audio_task = asyncio.create_task(local_microphone.listen_forever(), name="Microphone")

    connector = Connector.Connector(mode_master, infos)
    mode_master.set_connector(connector)

    restart_task = asyncio.create_task(mode_master.wait_for_restart_request(), name="RestartRequest")

    # Python 3.10 compatible task cancellation (since you're not on 3.11+)
    tasks = [
        restart_task,
        asyncio.create_task(mode_master.update_forever(), name="ModeMaster"),
        audio_task
    ]
    if infos.get("startServer", False):
        tasks.append(asyncio.create_task(connector.start_server(), name="Connector"))
        tasks.append(asyncio.create_task(launch_webapp(infos), name="WebApp"))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        should_restart = (
            restart_task in done
            and not restart_task.cancelled()
            and restart_task.exception() is None
        )
        
        # If any task completed or crashed, gracefully cancel the remaining ones
        for task in pending:
            task.cancel()
            
        # Wait for the cancelled tasks to finish cleaning up
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
            
        # Re-raise exceptions from the crashed task(s)
        for task in done:
            if task is restart_task:
                if task.cancelled():
                    continue
                if task.exception():
                    raise task.exception()
                continue
            if task.exception():
                raise task.exception()
        
        return RESTART_REQUESTED if should_restart else None
                
    except Exception as e:
        logging.error(f"Critical error in main task group: {e}")
        return None
    finally:
        mode_master.flush_sync()
        atexit.unregister(mode_master.flush_sync)

def run_forever() -> None:
    is_win = (sys.platform == "win32")
    if is_win:
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    cli_args = parse_arguments()
    try:
        while True:
            try:
                result = asyncio.run(main(cli_args))
            except KeyboardInterrupt:
                break

            if result != RESTART_REQUESTED:
                break

            # Keep the controller attached to the same terminal so Ctrl+C / stop still works after a web-triggered restart.
            logging.info("Restart requested from the web app. Relaunching the controller...")
    finally:
        if is_win:
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass


if __name__ == "__main__":
    run_forever()