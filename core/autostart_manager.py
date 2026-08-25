"""
Velodictum - Windows Autostart Manager
Configures Windows user startup registry entry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).
"""
import os
import sys
import winreg

APP_REG_NAME = "VelodictumAI"
RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_startup_command() -> str:
    """Returns the executable command line string for launching Velodictum minimized."""
    if getattr(sys, "frozen", False):
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}" --minimized'
    python_exe = os.path.abspath(sys.executable)
    project_root = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_root, "main.py")
    return f'"{python_exe}" "{main_script}" --minimized'


def is_autostart_enabled() -> bool:
    """Checks if Velodictum is currently registered in Windows Startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[Autostart] Read error: {e}")
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables Windows Startup for Velodictum."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_startup_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[Autostart] Enabled: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    print("[Autostart] Disabled")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Autostart] Update error: {e}")
        return False
