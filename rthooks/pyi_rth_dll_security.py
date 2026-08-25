"""
Velodictum PyInstaller Early Runtime Hook - DLL Search Order Hardening.
Mitigates DLLPreloading / Binary Hijacking on Windows 10/11.
"""
import ctypes
import os
import sys

if sys.platform == 'win32':
    try:
        kernel32 = ctypes.windll.kernel32
        # 1. Remove Current Working Directory (CWD) from DLL search path
        kernel32.SetDllDirectoryW('')

        # 2. Enforce Safe DLL search mode
        LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000
        LOAD_LIBRARY_SEARCH_APPLICATION_DIR = 0x00000200
        LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800
        flags = (
            LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
            | LOAD_LIBRARY_SEARCH_APPLICATION_DIR
            | LOAD_LIBRARY_SEARCH_SYSTEM32
        )
        try:
            kernel32.SetDefaultDllDirectories(flags)
        except Exception:
            pass
    except Exception:
        pass