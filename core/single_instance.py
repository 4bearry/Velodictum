"""
Velodictum - Single Instance Guard & Inter-Process Mutex
Ensures only one instance of Velodictum runs at any time on Windows.
Prevents duplicate hotkey hooks, double text paste, and duplicate floating HUDs.
"""
import ctypes
import os
import sys

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\Velodictum_SingleInstance_Mutex_Secure"

_mutex_handle = None


def ensure_single_instance(app_title: str = "Velodictum") -> bool:
    """
    Acquires a Win32 system-wide named mutex.
    Returns True if this is the primary/only instance.
    Returns False if another instance is already running.
    """
    global _mutex_handle

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    # Create / open named mutex
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:
        # Another instance is already active!
        # Try to bring the existing window to the front
        hwnd = user32.FindWindowW(None, app_title)
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        return False

    return True


def release_single_instance():
    """Release the mutex on clean application exit."""
    global _mutex_handle
    if _mutex_handle:
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None
