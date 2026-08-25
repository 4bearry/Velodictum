"""
Velodictum - Audio Device Monitor & Hot-Plug Fallback Engine
Periodically inspects connected audio input devices.
If the active microphone is disconnected or becomes invalid, it automatically
falls back to the Windows default input device and triggers an instant HUD notification pill.
Also detects hot-plugging of new audio devices.
"""
import threading
import time
from typing import List, Dict, Optional, Set
import sounddevice as sd

from config import config
from gui.signals import signals


class AudioDeviceMonitor:
    def __init__(self, check_interval: float = 2.0):
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_device_ids: Set[int] = set()
        self._last_device_names: List[str] = []
        self._lock = threading.Lock()
        self._recorder_ref = None

    def set_recorder(self, recorder):
        """Set reference to the active AudioRecorder instance."""
        with self._lock:
            self._recorder_ref = recorder

    def start(self):
        """Start background device monitoring thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            init_devs = self.get_input_devices()
            self._last_device_ids = {d["id"] for d in init_devs}
            self._last_device_names = [d["name"] for d in init_devs]
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            print("[DeviceMonitor] Audio device hot-plug monitor started.")

    def stop(self):
        """Stop background device monitoring thread."""
        with self._lock:
            self._running = False

    def get_input_devices(self) -> List[Dict]:
        """Returns all currently available input devices."""
        try:
            raw_devices = sd.query_devices()
            valid = []
            for i, d in enumerate(raw_devices):
                if d.get("max_input_channels", 0) > 0:
                    valid.append({
                        "id": i,
                        "name": d.get("name", f"Gerät {i}"),
                        "hostapi": d.get("hostapi", 0),
                        "channels": d.get("max_input_channels", 1),
                    })
            return valid
        except Exception as e:
            print(f"[DeviceMonitor] Query devices error: {e}")
            return []

    def get_default_input_device(self) -> Optional[Dict]:
        """Returns the system default input device."""
        try:
            def_idx = sd.default.device[0]
            raw_devices = sd.query_devices()
            if 0 <= def_idx < len(raw_devices):
                d = raw_devices[def_idx]
                return {
                    "id": def_idx,
                    "name": d.get("name", "Standard-Mikrofon"),
                    "hostapi": d.get("hostapi", 0),
                    "channels": d.get("max_input_channels", 1),
                }
        except Exception:
            pass

        avail = self.get_input_devices()
        return avail[0] if avail else None

    def _monitor_loop(self):
        while self._running:
            try:
                current_devices = self.get_input_devices()
                current_ids = {d["id"] for d in current_devices}
                current_names = [d["name"] for d in current_devices]

                target_id = getattr(config.audio, "input_device", None)

                # Case 1: Specific configured device was unplugged
                if target_id is not None and target_id not in current_ids:
                    default_dev = self.get_default_input_device()
                    if default_dev:
                        fallback_id = default_dev["id"]
                        fallback_name = default_dev["name"]
                        print(f"[DeviceMonitor] Active device {target_id} lost! Auto-switching to default '{fallback_name}' ({fallback_id})...")

                        config.audio.input_device = fallback_id
                        config.save()

                        if self._recorder_ref:
                            self._recorder_ref.set_device(fallback_id)

                        signals.audio_device_switched.emit(fallback_name)

                # Case 2: Topology change (unplugged or newly connected device when using system default or any device)
                elif self._last_device_ids and current_ids != self._last_device_ids:
                    lost_names = set(self._last_device_names) - set(current_names)
                    added_names = set(current_names) - set(self._last_device_names)

                    if lost_names:
                        default_dev = self.get_default_input_device()
                        new_name = default_dev["name"] if default_dev else "Standard-Mikrofon"
                        print(f"[DeviceMonitor] Audio device disconnected: {lost_names}! Active fallback: '{new_name}'")
                        if self._recorder_ref and default_dev:
                            self._recorder_ref.set_device(default_dev["id"])
                        signals.audio_device_switched.emit(new_name)

                    elif added_names:
                        connected_name = list(added_names)[0]
                        print(f"[DeviceMonitor] New audio device detected: '{connected_name}'")
                        signals.audio_device_switched.emit(connected_name)

                self._last_device_ids = current_ids
                self._last_device_names = current_names

            except Exception as e:
                print(f"[DeviceMonitor] Loop error: {e}")

            time.sleep(self.check_interval)


# Global singleton instance
audio_device_monitor = AudioDeviceMonitor()
