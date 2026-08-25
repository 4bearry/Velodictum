"""
Velodictum - Low-Latency Audio Recorder
Records microphone input stream to in-memory numpy buffer.
"""
import threading
import time
from typing import Callable, List, Optional
import numpy as np
import sounddevice as sd

from config import config


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
        on_level_update: Optional[Callable[[float], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.on_level_update = on_level_update

        self._stream: Optional[sd.InputStream] = None
        self._frames: List[np.ndarray] = []
        self._is_recording = False
        self._is_testing = False
        self._lock = threading.Lock()
        self._start_time: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_testing(self) -> bool:
        return self._is_testing

    def _ensure_stream_open(self) -> bool:
        """Ensures the background PortAudio InputStream is open and active (warm-standby)."""
        if self._stream is not None and self._stream.active:
            return True
        try:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self.device,
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * 0.05),  # 50ms blocks
            )
            self._stream.start()
            return True
        except Exception as e:
            print(f"[AudioRecorder] Error opening stream on device {self.device}: {e}. Falling back to default...")
            try:
                self.device = None
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=None,
                    callback=self._audio_callback,
                    blocksize=int(self.sample_rate * 0.05),
                )
                self._stream.start()
                from gui.signals import signals
                signals.audio_device_switched.emit("Standard-Mikrofon")
                return True
            except Exception as fallback_err:
                print(f"[AudioRecorder] Fatal: Fallback audio stream failed: {fallback_err}")
                self._stream = None
                return False

    def set_device(self, device: Optional[int]):
        """Set the active input microphone device index and restart the persistent stream."""
        with self._lock:
            if self.device == device and self._stream is not None and self._stream.active:
                return
            self.device = device
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._ensure_stream_open()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Internal callback invoked by sounddevice for each chunk of mic audio."""
        if status:
            pass

        if self._is_recording or self._is_testing:
            chunk = indata.copy()

            # Software Pre-amplification (Gain) & Anti-Clipping Limiter
            gain = getattr(config.audio, "input_gain", 1.0)
            if gain != 1.0:
                chunk = chunk * gain
                np.clip(chunk, -0.99, 0.99, out=chunk)

            if self._is_recording:
                # DoS / OOM Guard: Cap continuous recording duration at max 10 minutes (600s)
                if self._start_time == 0.0 or (time.time() - self._start_time <= 600.0):
                    with self._lock:
                        self._frames.append(chunk)

            # Calculate RMS for visual audio meter
            if self.on_level_update:
                rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                self.on_level_update(rms)

    def start_test(self) -> bool:
        """
        Start microphone test mode for live level monitoring without recording audio frames.
        """
        with self._lock:
            if self._is_recording:
                return False
            self._is_testing = True
            return self._ensure_stream_open()

    def stop_test(self) -> None:
        """
        Stop microphone test mode.
        """
        with self._lock:
            self._is_testing = False
            if self.on_level_update:
                self.on_level_update(0.0)

    def start(self) -> bool:
        """Start capturing audio for dictation instantly (<0.001ms)."""
        with self._lock:
            if self._is_recording:
                return False

            self._is_testing = False
            self._frames = []
            self._is_recording = True
            self._start_time = time.time()

            # Ensure background stream is active
            if not self._ensure_stream_open():
                self._is_recording = False
                return False

            return True

    def stop(self) -> Optional[np.ndarray]:
        """
        Stop recording and return normalized 1D float32 numpy array of audio.
        Keeps stream open in warm-standby mode for 0ms latency on next hotkey press.
        """
        with self._lock:
            if not self._is_recording:
                return None

            self._is_recording = False
            self._is_testing = False

            if not self._frames:
                return None

            # Concatenate all recorded chunks into a single 1D numpy float32 array
            audio = np.concatenate(self._frames, axis=0)
            if self.channels > 1:
                audio = np.mean(audio, axis=1)
            else:
                audio = audio.flatten()

            self._frames = []
            return audio

    def close(self):
        """Cleanly closes the background audio stream upon app exit."""
        with self._lock:
            self._is_recording = False
            self._is_testing = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    @staticmethod
    def list_devices() -> List[dict]:
        """List all available input audio devices on Windows."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append({
                    "id": i,
                    "name": dev["name"],
                    "hostapi": dev["hostapi"],
                    "channels": dev["max_input_channels"],
                    "default_samplerate": dev["default_samplerate"],
                })
        return input_devices

    @staticmethod
    def get_default_device_name() -> str:
        """Get the name of the default input device."""
        try:
            default_id = sd.default.device[0]
            if default_id is not None and default_id >= 0:
                info = sd.query_devices(default_id)
                return info["name"]
        except Exception:
            pass
        return "Default System Microphone"
