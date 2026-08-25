"""
Velodictum - Windows Core Audio Auto-Ducking Engine
Automatically lowers the master volume scalar of background applications (Spotify, YouTube, Games)
during active dictation and smoothly restores it upon completion.

Native Win32 COM implementation (IMMDeviceEnumerator / IAudioEndpointVolume) via ctypes.
Zero external dependencies.
"""
import ctypes
from ctypes import wintypes, POINTER, c_void_p, c_float, Structure, HRESULT, byref
import threading
import time
from typing import Optional


class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
        super().__init__(l, w1, w2, (wintypes.BYTE * 8)(b1, b2, b3, b4, b5, b6, b7, b8))


CLSID_MMDeviceEnumerator = GUID(0xBCDE0395, 0xE52F, 0x467C, 0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E)
IID_IMMDeviceEnumerator = GUID(0xA95664D2, 0x9614, 0x4F35, 0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6)
IID_IAudioEndpointVolume = GUID(0x5CDF2C82, 0x841E, 0x4546, 0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A)

CLSCTX_ALL = 23
eRender = 0
eMultimedia = 1


class AudioDucker:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_ducked = False
        self._prev_volume: Optional[float] = None
        self._ole32 = None
        try:
            self._ole32 = ctypes.windll.ole32
        except Exception:
            pass

    def _get_endpoint_volume(self):
        if not self._ole32:
            return None, None

        self._ole32.CoInitialize(None)

        p_enum = c_void_p()
        hr = self._ole32.CoCreateInstance(
            byref(CLSID_MMDeviceEnumerator),
            None,
            CLSCTX_ALL,
            byref(IID_IMMDeviceEnumerator),
            byref(p_enum),
        )
        if hr != 0 or not p_enum.value:
            return None, None

        # IMMDeviceEnumerator vtbl: GetDefaultAudioEndpoint is at index 4
        vtbl = ctypes.cast(p_enum.value, POINTER(POINTER(ctypes.c_void_p))).contents
        GetDefaultAudioEndpoint_proto = ctypes.WINFUNCTYPE(
            HRESULT, c_void_p, wintypes.DWORD, wintypes.DWORD, POINTER(c_void_p)
        )
        GetDefaultAudioEndpoint = GetDefaultAudioEndpoint_proto(vtbl[4])

        p_device = c_void_p()
        hr = GetDefaultAudioEndpoint(p_enum.value, eRender, eMultimedia, byref(p_device))
        if hr != 0 or not p_device.value:
            return None, None

        # IMMDevice vtbl: Activate is at index 3
        dev_vtbl = ctypes.cast(p_device.value, POINTER(POINTER(ctypes.c_void_p))).contents
        Activate_proto = ctypes.WINFUNCTYPE(
            HRESULT, c_void_p, POINTER(GUID), wintypes.DWORD, c_void_p, POINTER(c_void_p)
        )
        Activate = Activate_proto(dev_vtbl[3])

        p_endpoint_vol = c_void_p()
        hr = Activate(p_device.value, byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None, byref(p_endpoint_vol))
        if hr != 0 or not p_endpoint_vol.value:
            return None, None

        return p_endpoint_vol, p_endpoint_vol.value

    def get_master_volume(self) -> Optional[float]:
        """Returns current master output volume as a scalar between 0.0 and 1.0."""
        try:
            _, vol_ptr = self._get_endpoint_volume()
            if not vol_ptr:
                return None

            vol_vtbl = ctypes.cast(vol_ptr, POINTER(POINTER(ctypes.c_void_p))).contents
            GetMasterVolumeLevelScalar_proto = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))
            GetMasterVolumeLevelScalar = GetMasterVolumeLevelScalar_proto(vol_vtbl[9])

            current_vol = c_float()
            hr = GetMasterVolumeLevelScalar(vol_ptr, byref(current_vol))
            if hr == 0:
                return float(current_vol.value)
        except Exception as e:
            print(f"[AudioDucker] Get volume error: {e}")
        return None

    def set_master_volume(self, scalar: float) -> bool:
        """Sets master output volume as a scalar between 0.0 and 1.0."""
        try:
            _, vol_ptr = self._get_endpoint_volume()
            if not vol_ptr:
                return False

            vol_vtbl = ctypes.cast(vol_ptr, POINTER(POINTER(ctypes.c_void_p))).contents
            SetMasterVolumeLevelScalar_proto = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)
            SetMasterVolumeLevelScalar = SetMasterVolumeLevelScalar_proto(vol_vtbl[7])

            val = max(0.0, min(1.0, float(scalar)))
            hr = SetMasterVolumeLevelScalar(vol_ptr, c_float(val), None)
            return hr == 0
        except Exception as e:
            print(f"[AudioDucker] Set volume error: {e}")
            return False

    def duck(self, target_fraction: float = 0.25) -> bool:
        """
        Lowers the master volume to target_fraction (e.g. 0.25 = 25% of current volume or absolute 0.25).
        Remembers previous volume for unducking.
        """
        with self._lock:
            if self._is_ducked:
                return True

            cur_vol = self.get_master_volume()
            if cur_vol is None or cur_vol <= 0.01:
                return False

            self._prev_volume = cur_vol
            # Calculate ducked level: proportional to current volume
            ducked_level = max(0.05, min(cur_vol, cur_vol * float(target_fraction)))
            ok = self.set_master_volume(ducked_level)
            if ok:
                self._is_ducked = True
            return ok

    def unduck(self) -> bool:
        """Restores the master volume back to the pre-duck level."""
        with self._lock:
            if not self._is_ducked or self._prev_volume is None:
                self._is_ducked = False
                self._prev_volume = None
                return False

            target = self._prev_volume
            ok = self.set_master_volume(target)
            self._is_ducked = False
            self._prev_volume = None
            return ok

    @property
    def is_ducked(self) -> bool:
        with self._lock:
            return self._is_ducked


# Singleton audio ducker instance
audio_ducker = AudioDucker()
