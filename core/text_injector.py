"""
Velodictum - Smart Text Injector & Revert Engine
Safely injects text into the focused Windows application via clipboard & keystroke simulation.
Supports instant Undo/Revert (Ctrl+Alt+Z) and auto-send Enter actions.
Preserves user's original clipboard content.
"""
import ctypes
import threading
import time
from typing import Dict, Optional
import pyperclip

# Win32 Virtual-Key Codes and Constants
VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_C = 0x43
VK_V = 0x56
VK_Z = 0x5A
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
KEYEVENTF_KEYUP = 0x0002

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Blacklisted sensitive process names
SENSITIVE_PROCESSES = {
    "keepass.exe",
    "keepassxc.exe",
    "1password.exe",
    "bitwarden.exe",
    "lastpass.exe",
    "dashlane.exe",
    "enpass.exe",
    "nordpass.exe",
    "credentialui.exe",
    "logonui.exe",
    "consent.exe",
    "securityhealthsystray.exe",
}


def _release_modifiers_win32():
    """Releases physical modifier keys (Alt, Shift, Ctrl, Win) to avoid key combination desync."""
    user32 = ctypes.windll.user32
    for vk in (VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN, VK_CONTROL):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def safe_clipboard_copy(text: str, retries: int = 4, delay: float = 0.015) -> bool:
    """Copy text to clipboard with exponential retry for handling Win32 OpenClipboard contention."""
    for attempt in range(retries):
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            time.sleep(delay * (2 ** attempt))
    return False


def safe_clipboard_paste(retries: int = 4, delay: float = 0.015) -> str:
    """Paste text from clipboard with retry for handling Win32 OpenClipboard contention."""
    for attempt in range(retries):
        try:
            return pyperclip.paste() or ""
        except Exception:
            time.sleep(delay * (2 ** attempt))
    return ""


def get_process_name_for_hwnd(hwnd: int) -> str:
    """Safely retrieves the executable name for a given window handle."""
    if not hwnd:
        return ""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if h_process:
                try:
                    import os
                    exe_buf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.c_ulong(1024)
                    if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(size)):
                        return os.path.basename(exe_buf.value).lower()
                finally:
                    kernel32.CloseHandle(h_process)
    except Exception:
        pass
    return ""


class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [("TokenIsElevated", ctypes.c_ulong)]


def is_current_process_elevated() -> bool:
    """Checks if the current Velodictum process is running with Administrator/Elevated rights."""
    try:
        shell32 = getattr(ctypes.windll, "shell32", None)
        if shell32 and hasattr(shell32, "IsUserAnAdmin"):
            return bool(shell32.IsUserAnAdmin())
    except Exception:
        pass
    return False


def is_elevated_hwnd(hwnd: int) -> bool:
    """
    Checks if target window process is elevated (RunAsAdmin / High Integrity).
    Returns True if target process is elevated or protected by Windows UIPI.
    """
    if not hwnd:
        return False
    user32 = getattr(ctypes.windll, "user32", None)
    kernel32 = getattr(ctypes.windll, "kernel32", None)
    advapi32 = getattr(ctypes.windll, "advapi32", None)
    if not user32 or not kernel32 or not advapi32:
        return False

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return False

    # Skip elevation check if targeting our own process
    try:
        if pid.value == kernel32.GetCurrentProcessId():
            return False
    except Exception:
        pass

    h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h_process:
        err = kernel32.GetLastError()
        # ERROR_ACCESS_DENIED (5) happens when standard user inspects elevated process
        if err == 5 and not is_current_process_elevated():
            return True
        return False

    h_token = ctypes.c_void_p()
    try:
        TOKEN_QUERY = 0x0008
        if not advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            err = kernel32.GetLastError()
            if err == 5 and not is_current_process_elevated():
                return True
            return False

        elevation = TOKEN_ELEVATION()
        ret_len = ctypes.c_ulong()
        TokenElevation = 20
        if advapi32.GetTokenInformation(
            h_token,
            TokenElevation,
            ctypes.byref(elevation),
            ctypes.sizeof(elevation),
            ctypes.byref(ret_len),
        ):
            return bool(elevation.TokenIsElevated)
    except Exception:
        pass
    finally:
        if h_token:
            kernel32.CloseHandle(h_token)
        if h_process:
            kernel32.CloseHandle(h_process)

    return False


def check_uipi_boundary(hwnd: int) -> bool:
    """
    Returns True if targeting `hwnd` would violate Windows UIPI
    (Velodictum runs as standard user and target window runs as Elevated/Admin).
    """
    if not hwnd:
        return False
    if is_current_process_elevated():
        return False  # Elevated injector can send inputs to any window
    return is_elevated_hwnd(hwnd)


def is_sensitive_hwnd(hwnd: int) -> bool:
    """Checks if a window handle belongs to a credential/password manager or logon dialog."""
    proc = get_process_name_for_hwnd(hwnd)
    return proc in SENSITIVE_PROCESSES


def grab_selected_text_win32() -> str:
    """
    Robustly grabs currently highlighted/selected text from the active window by:
    1. Releasing any physical modifier keys (Alt, Shift, Ctrl, Win) held down during hotkey press.
    2. Simulating clean Win32 Ctrl+C.
    3. Polling clipboard with timeout to ensure target app processes the copy.
    """
    try:
        from ui_automation_context import is_sensitive_or_password_focused
        is_blocked, _ = is_sensitive_or_password_focused()
        if is_blocked:
            return ""
    except Exception:
        pass

    user32 = ctypes.windll.user32

    # 1. Release modifier keys that may be held down by user hotkey (e.g. Ctrl+Alt+Space)
    _release_modifiers_win32()
    time.sleep(0.02)

    # 2. Set temporary sentinel on clipboard
    sentinel = f"__VELODICTUM_GRAB_{time.time()}__"
    safe_clipboard_copy(sentinel)

    # 3. Simulate clean Ctrl+C
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    # 4. Poll clipboard for up to 140ms
    start_t = time.time()
    grabbed = ""
    while time.time() - start_t < 0.14:
        curr = safe_clipboard_paste()
        if curr and curr != sentinel:
            grabbed = curr
            break
        time.sleep(0.015)

    return grabbed


def _send_ctrl_v_win32():
    """Simulate Ctrl+V keypress using low-level Win32 keybd_event API."""
    _release_modifiers_win32()
    time.sleep(0.005)
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _send_ctrl_z_win32():
    """Simulate Ctrl+Z keypress using low-level Win32 keybd_event API."""
    _release_modifiers_win32()
    time.sleep(0.005)
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_Z, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(VK_Z, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _send_enter_win32():
    """Simulate Enter/Return keypress using Win32 keybd_event API."""
    _release_modifiers_win32()
    time.sleep(0.005)
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.025)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)


class TextInjector:
    def __init__(self, auto_paste: bool = True, restore_clipboard: bool = True, restore_delay: float = 0.35):
        self.auto_paste = auto_paste
        self.restore_clipboard = restore_clipboard
        self.restore_delay = restore_delay
        self._lock = threading.Lock()
        self.last_injection: Optional[Dict] = None

    def inject(
        self,
        text: str,
        raw_text: str = "",
        send_enter: bool = False,
        target_hwnd: Optional[int] = None,
        enforce_target_window: bool = False,
    ) -> bool:
        """
        Inject text into the active focused window.
        1. Expand Smart Snippets & Voice Macros
        2. Validate target window and sensitive process isolation
        3. Back up clipboard
        4. Set text to clipboard
        5. Send Ctrl+V
        6. Send Enter (if send_enter is True)
        7. Restore previous clipboard asynchronously with non-destructive integrity check
        8. Record last injection state for Revert (Ctrl+Alt+Z)
        """
        if not text:
            return False

        try:
            from smart_snippets import snippet_manager
            text = snippet_manager.apply_snippets(text)
        except Exception:
            pass

        with self._lock:
            user32 = ctypes.windll.user32
            current_hwnd = user32.GetForegroundWindow()

            # Window Swap / TOCTOU Protection
            if target_hwnd and current_hwnd != target_hwnd:
                if enforce_target_window:
                    # Attempt safe focus restore
                    user32.SetForegroundWindow(target_hwnd)
                    time.sleep(0.03)
                    current_hwnd = user32.GetForegroundWindow()
                    if current_hwnd != target_hwnd:
                        print(f"[Injector] Window swap race detected! Focus switched from {target_hwnd} to {current_hwnd}. Aborting injection.")
                        return False
                else:
                    # Log window change for diagnostics
                    pass

            # Sensitive / Password Field Guard: Prevent automated injection into password managers & masked password inputs
            is_blocked = is_sensitive_hwnd(current_hwnd)
            reason = "Sensibles Passwort-/Sicherheitsfenster erkannt" if is_blocked else ""

            if not is_blocked:
                try:
                    from ui_automation_context import is_sensitive_or_password_focused
                    is_blocked, reason = is_sensitive_or_password_focused(current_hwnd)
                except Exception:
                    pass

            if is_blocked:
                msg = f"Injektion blockiert: {reason or 'Sensibles Passwortfeld'} (HWND {current_hwnd})."
                print(f"[Injector] {msg}")
                try:
                    from gui.signals import signals
                    signals.injection_blocked.emit(msg)
                except Exception:
                    pass
                return False

            # UIPI & Elevation Boundary Detection: Prevent silent input drops and clipboard corruption in Admin windows
            if check_uipi_boundary(current_hwnd):
                msg = "Injection blocked: Target window runs with administrator privileges (Windows UIPI protection)."
                print(f"[Injector] {msg}")
                try:
                    from gui.signals import signals
                    signals.injection_blocked.emit(msg)
                except Exception:
                    pass
                return False

            # 1. Backup existing clipboard content safely
            previous_clip = safe_clipboard_paste()

            # Record state for undo/revert
            self.last_injection = {
                "injected_text": text,
                "raw_text": raw_text or text,
                "previous_clip": previous_clip,
                "hwnd": current_hwnd,
                "timestamp": time.time(),
                "send_enter": send_enter,
            }

            try:
                from correction_detector import correction_detector
                correction_detector.record_injection(text, current_hwnd)
            except Exception:
                pass

            # 2. Put new text in clipboard with retry
            if not safe_clipboard_copy(text):
                print("[Injector] Clipboard write error after retries.")
                return False

            # 3. Simulate Ctrl+V to paste into active window
            if self.auto_paste:
                time.sleep(0.02)  # Tiny pause to ensure clipboard is ready
                _send_ctrl_v_win32()

                if send_enter:
                    time.sleep(0.12)  # Wait for paste to register in chat before submitting
                    _send_enter_win32()

            # 4. Restore original clipboard content non-destructively in background thread
            if self.restore_clipboard and previous_clip is not None:
                def _restore(injected_sentinel: str, orig_clip: str):
                    time.sleep(self.restore_delay)
                    try:
                        # Non-destructive check: Only restore if the clipboard still has the text we injected!
                        # If the user copied something else in the meantime, preserve their new clipboard data!
                        current_clip = safe_clipboard_paste()
                        if current_clip == injected_sentinel:
                            safe_clipboard_copy(orig_clip)
                    except Exception:
                        pass

                threading.Thread(target=_restore, args=(text, previous_clip), daemon=True).start()

            return True

    def revert_last_injection(self, mode: str = "undo", verify_hwnd: bool = True) -> Dict:
        """
        Reverts the last text injection in the active window.
        - 'undo': Simulates Ctrl+Z to remove injected text and restores clipboard.
        - 'raw': Undoes formatted text and injects the raw verbatim transcript instead.
        """
        with self._lock:
            if not self.last_injection:
                return {"success": False, "reason": "Kein vorheriges Diktat vorhanden"}

            last = dict(self.last_injection)
            user32 = ctypes.windll.user32
            current_hwnd = user32.GetForegroundWindow()

            if verify_hwnd and last.get("hwnd") and current_hwnd != last["hwnd"]:
                # Attempt to bring original target window to foreground
                user32.SetForegroundWindow(last["hwnd"])
                time.sleep(0.03)

            # 1. Simulate Ctrl+Z in the active window
            time.sleep(0.02)
            _send_ctrl_z_win32()

            # 2. Restore previous clipboard immediately
            if last.get("previous_clip") is not None:
                safe_clipboard_copy(last["previous_clip"])

            if mode == "raw" and last.get("raw_text"):
                time.sleep(0.05)
                try:
                    safe_clipboard_copy(last["raw_text"])
                    _send_ctrl_v_win32()
                    return {"success": True, "action": "raw_restored", "text": last["raw_text"]}
                except Exception as e:
                    return {"success": False, "reason": str(e)}

            # Clear state after successful undo
            self.last_injection = None
            return {"success": True, "action": "undone", "text": last.get("injected_text", "")}

    def send_enter_keystroke(self):
        """Manually trigger an Enter keypress."""
        _send_enter_win32()

