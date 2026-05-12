import ctypes
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


class SystemStatus:
    def __init__(self, infos: Dict[str, Any], listener: Any, leds_list: Any) -> None:
        self.infos = infos
        self.listener = listener
        self.leds_list = leds_list
        self.started_monotonic = time.monotonic()
        self.last_loop_tick_monotonic: Optional[float] = None
        self.loop_fps: Optional[float] = None
        self.last_action: Optional[Dict[str, Any]] = None

        self._last_host_probe = 0.0
        self._last_esp32_probe = 0.0
        self._last_bluetooth_probe = 0.0

        self._cached_host_probe: Dict[str, Any] = {
            "cpuTempC": None,
            "ramUsagePercent": None,
            "diskUsagePercent": None,
        }
        self._cached_esp32_probe: Dict[str, Any] = {
            "status": "unknown",
            "target": None,
        }
        self._cached_bluetooth_probe: Dict[str, Any] = {
            "status": "unknown",
            "deviceName": None,
        }

    def note_loop_tick(self, dt_seconds: Optional[float]) -> None:
        now = time.monotonic()
        self.last_loop_tick_monotonic = now
        if dt_seconds is None or dt_seconds <= 0:
            return

        instantaneous_fps = 1.0 / dt_seconds
        if self.loop_fps is None:
            self.loop_fps = instantaneous_fps
            return

        self.loop_fps = (self.loop_fps * 0.85) + (instantaneous_fps * 0.15)

    def set_last_action(self, action: str, state: str, message: str) -> None:
        self.last_action = {
            "action": action,
            "state": state,
            "message": message,
            "timestampMs": int(time.time() * 1000),
        }

    def get_restart_python_capability(self) -> Dict[str, Any]:
        executable = getattr(sys, "executable", "")
        if not executable or not os.path.exists(executable):
            return {
                "available": False,
                "reason": "Python executable unavailable for self-restart.",
            }

        if len(sys.argv) == 0:
            return {
                "available": False,
                "reason": "Current Python entrypoint is unavailable for self-restart.",
            }

        return {
            "available": True,
            "reason": None,
        }

    def get_reboot_raspberry_capability(self) -> Dict[str, Any]:
        if not self._is_linux():
            return {
                "available": False,
                "reason": "Raspberry reboot is only available on Linux hosts.",
            }

        if not self._is_raspberry_runtime():
            return {
                "available": False,
                "reason": "Reboot is only enabled when the app runs on the Raspberry.",
            }

        if self.resolve_reboot_command() is None:
            return {
                "available": False,
                "reason": "No reboot command is available on this host.",
            }

        return {
            "available": True,
            "reason": None,
        }

    def get_snapshot(self, websocket_count: int) -> Dict[str, Any]:
        now = time.monotonic()

        if now - self._last_host_probe >= 1.5:
            self._cached_host_probe = self._probe_host_metrics()
            self._last_host_probe = now

        if now - self._last_esp32_probe >= 3.0:
            self._cached_esp32_probe = self._probe_esp32_status()
            self._last_esp32_probe = now

        if now - self._last_bluetooth_probe >= 5.0:
            self._cached_bluetooth_probe = self._probe_bluetooth_status()
            self._last_bluetooth_probe = now

        last_loop_tick_ms = None
        python_loop_healthy = False
        if self.last_loop_tick_monotonic is not None:
            last_loop_tick_ms = int(max(0.0, now - self.last_loop_tick_monotonic) * 1000)
            python_loop_healthy = last_loop_tick_ms < 2000

        last_audio_sample_age_ms = self._last_audio_sample_age_ms()
        audio_stream_state = str(getattr(self.listener, "audio_stream_state", "unknown") or "unknown")
        use_microphone = bool(self.infos.get("useMicrophone", True))
        audio_stream_healthy = (
            (not use_microphone)
            or (
                audio_stream_state == "running"
                and last_audio_sample_age_ms is not None
                and last_audio_sample_age_ms < 3000
            )
        )

        dynamic_audio_latency = getattr(self.listener, "dynamic_audio_latency", None)
        dynamic_audio_latency_ms = None
        if isinstance(dynamic_audio_latency, (int, float)):
            dynamic_audio_latency_ms = int(max(0.0, float(dynamic_audio_latency)) * 1000)

        restart_python = self.get_restart_python_capability()
        reboot_raspberry = self.get_reboot_raspberry_capability()

        return {
            "cpuTempC": self._cached_host_probe.get("cpuTempC"),
            "ramUsagePercent": self._cached_host_probe.get("ramUsagePercent"),
            "diskUsagePercent": self._cached_host_probe.get("diskUsagePercent"),
            "pythonLoopFps": None if self.loop_fps is None else round(float(self.loop_fps), 1),
            "pythonLoopHealthy": python_loop_healthy,
            "pythonLoopLastTickMs": last_loop_tick_ms,
            "simulationMode": self._is_simulation_mode(),
            "hardwareModeConfigured": str(self.infos.get("hardwareModeConfigured", self.infos.get("HARDWARE_MODE", "auto"))),
            "hardwareModeResolved": str(self.infos.get("resolvedHardwareMode", self.infos.get("HARDWARE_MODE", "unknown"))),
            "esp32Status": self._cached_esp32_probe.get("status"),
            "esp32Target": self._cached_esp32_probe.get("target"),
            "phoneBluetoothStatus": self._cached_bluetooth_probe.get("status"),
            "phoneBluetoothDeviceName": self._cached_bluetooth_probe.get("deviceName"),
            "webClientCount": int(max(0, websocket_count)),
            "useMicrophone": use_microphone,
            "audioStreamHealthy": audio_stream_healthy,
            "audioStreamState": audio_stream_state,
            "lastAudioSampleAgeMs": last_audio_sample_age_ms,
            "dynamicAudioLatencyMs": dynamic_audio_latency_ms,
            "uptimeSeconds": int(max(0.0, now - self.started_monotonic)),
            "hostname": platform.node() or "unknown-host",
            "platform": f"{platform.system()} {platform.release()}".strip(),
            "actions": {
                "restartPython": restart_python,
                "rebootRaspberry": reboot_raspberry,
                "lastAction": self.last_action,
            },
        }

    def _is_linux(self) -> bool:
        return sys.platform.startswith("linux")

    def _is_raspberry_runtime(self) -> bool:
        resolved_mode = str(self.infos.get("resolvedHardwareMode", self.infos.get("HARDWARE_MODE", "")))
        return bool(self.infos.get("onRaspberry", False)) or resolved_mode == "rpi"

    def _is_simulation_mode(self) -> bool:
        resolved_mode = str(self.infos.get("resolvedHardwareMode", self.infos.get("HARDWARE_MODE", "")))
        return resolved_mode == "simulation"

    def resolve_reboot_command(self) -> Optional[List[str]]:
        if shutil.which("systemctl"):
            return ["systemctl", "reboot"]
        if shutil.which("reboot"):
            return ["reboot"]
        return None

    def _last_audio_sample_age_ms(self) -> Optional[int]:
        last_audio_callback_time = getattr(self.listener, "last_audio_callback_time", None)
        if not isinstance(last_audio_callback_time, (int, float)):
            return None
        return int(max(0.0, time.time() - float(last_audio_callback_time)) * 1000)

    def _probe_host_metrics(self) -> Dict[str, Any]:
        return {
            "cpuTempC": self._read_cpu_temperature(),
            "ramUsagePercent": self._read_ram_usage_percent(),
            "diskUsagePercent": self._read_disk_usage_percent(),
        }

    def _read_cpu_temperature(self) -> Optional[float]:
        if not self._is_linux():
            return None

        thermal_zone_path = "/sys/class/thermal/thermal_zone0/temp"
        try:
            with open(thermal_zone_path, "r", encoding="utf-8") as file_obj:
                raw_value = file_obj.read().strip()
            return round(float(raw_value) / 1000.0, 1)
        except Exception:
            pass

        if shutil.which("vcgencmd"):
            try:
                result = subprocess.run(
                    ["vcgencmd", "measure_temp"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                    check=False,
                )
                output = result.stdout.strip()
                if "=" in output and "'" in output:
                    value = output.split("=", 1)[1].split("'", 1)[0]
                    return round(float(value), 1)
            except Exception:
                pass

        return None

    def _read_ram_usage_percent(self) -> Optional[float]:
        if self._is_linux():
            try:
                meminfo: Dict[str, int] = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as file_obj:
                    for line in file_obj:
                        if ":" not in line:
                            continue
                        key, value = line.split(":", 1)
                        meminfo[key] = int(value.strip().split()[0])

                total_kb = meminfo.get("MemTotal")
                available_kb = meminfo.get("MemAvailable")
                if total_kb and available_kb is not None and total_kb > 0:
                    used_ratio = 100.0 * float(total_kb - available_kb) / float(total_kb)
                    return round(used_ratio, 1)
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
                return round(float(memory_status.dwMemoryLoad), 1)
            except Exception:
                pass

        return None

    def _read_disk_usage_percent(self) -> Optional[float]:
        try:
            usage = shutil.disk_usage(os.getcwd())
            if usage.total <= 0:
                return None
            used_ratio = 100.0 * float(usage.used) / float(usage.total)
            return round(used_ratio, 1)
        except Exception:
            return None

    def _probe_esp32_status(self) -> Dict[str, Any]:
        targets = []
        for led_strip in self.leds_list:
            ip_addr = getattr(led_strip, "ip", None)
            if isinstance(ip_addr, str) and len(ip_addr) > 0 and ip_addr not in targets:
                targets.append(ip_addr)

        if self._is_simulation_mode():
            target = ", ".join(targets) if len(targets) > 0 else "127.0.0.1"
            return {
                "status": "simulation",
                "target": target,
            }

        if len(targets) == 0:
            if any("Rpi_NeoPixels" in str(type(led_strip)) for led_strip in self.leds_list):
                return {
                    "status": "direct_gpio",
                    "target": None,
                }
            return {
                "status": "unknown",
                "target": None,
            }

        if shutil.which("ping") is None:
            return {
                "status": "unknown",
                "target": ", ".join(targets),
            }

        reachability = [self._ping_host(target) for target in targets]
        status = "reachable" if all(reachability) else "unreachable"
        return {
            "status": status,
            "target": ", ".join(targets),
        }

    def _ping_host(self, host: str) -> bool:
        try:
            if sys.platform == "win32":
                command = ["ping", "-n", "1", "-w", "800", host]
            else:
                command = ["ping", "-c", "1", "-W", "1", host]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _probe_bluetooth_status(self) -> Dict[str, Any]:
        if not self._is_linux() or shutil.which("bluetoothctl") is None:
            return {
                "status": "unknown",
                "deviceName": None,
            }

        try:
            result = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except Exception:
            return {
                "status": "unknown",
                "deviceName": None,
            }

        if result.returncode != 0:
            return {
                "status": "unknown",
                "deviceName": None,
            }

        connected_lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("Device ")
        ]
        if len(connected_lines) == 0:
            return {
                "status": "disconnected",
                "deviceName": None,
            }

        first_device = connected_lines[0].split(maxsplit=2)
        device_name = first_device[2] if len(first_device) >= 3 else "Connected device"
        return {
            "status": "connected",
            "deviceName": device_name,
        }
