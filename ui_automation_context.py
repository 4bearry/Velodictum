"""
Velodictum - Deep UI Automation & Caret Context Extractor
Extracts cursor (caret) screen coordinates and surrounding pre-cursor text using Win32 API and UI Automation.
Analyzes grammatical boundaries, sentence continuation, and spacing requirements.
Hardened with sensitive process isolation, password field suppression, and regex sanitization.
"""
import ctypes
from ctypes import wintypes
import os
import re
from typing import Dict, Tuple, Optional, Any

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GWL_STYLE = -16
ES_PASSWORD = 0x0020
EM_GETPASSWORDCHAR = 0x00D2
UIA_IsPasswordPropertyId = 30019

SENSITIVE_PROCESS_NAMES = {
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


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT),
    ]


def sanitize_sensitive_text(text: str) -> str:
    """
    Sanitizes and masks sensitive credentials, tokens, API keys, and passwords
    before prompt generation or external transmission.
    """
    if not text:
        return ""

    sanitized = text

    # 1. Private Key Blocks
    sanitized = re.sub(
        r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z0-9_-]+ )?PRIVATE KEY-----",
        "[REDACTED_PRIVATE_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # 2. OpenAI / OpenRouter / Anthropic Keys (e.g. sk-..., sk-proj-..., sk-or-v1-...)
    sanitized = re.sub(
        r"\b(?:sk-(?:proj-|ant-|or-v1-)?[a-zA-Z0-9_\-]{16,})\b",
        "[REDACTED_API_KEY]",
        sanitized,
    )

    # 3. Google Gemini / Cloud API Keys (AIzaSy...)
    sanitized = re.sub(
        r"\bAIza[0-9A-Za-z\-_]{35}\b",
        "[REDACTED_GEMINI_KEY]",
        sanitized,
    )

    # 4. GitHub Personal Access Tokens (ghp_, gho_, ghu_, ghs_, ghr_, github_pat_)
    sanitized = re.sub(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b|\bgithub_pat_[a-zA-Z0-9_]{50,}\b",
        "[REDACTED_GITHUB_TOKEN]",
        sanitized,
    )

    # 5. Slack Tokens (xoxb-, xoxp-, xoxa-, xoxr-)
    sanitized = re.sub(
        r"\bxox[baprs]-[0-9]{10,}-[a-zA-Z0-9-]+\b",
        "[REDACTED_SLACK_TOKEN]",
        sanitized,
    )

    # 6. AWS Access Key IDs
    sanitized = re.sub(
        r"\bAKIA[0-9A-Z]{16}\b",
        "[REDACTED_AWS_KEY]",
        sanitized,
    )

    # 7. Bearer / JWT Tokens
    sanitized = re.sub(
        r"\bBearer\s+[a-zA-Z0-9_\-\.]{20,}\b",
        "Bearer [REDACTED_TOKEN]",
        sanitized,
    )

    # 8. Generic Key-Value Password / Token Assignments in Code or Config
    sanitized = re.sub(
        r"(?i)\b(password|passwd|pwd|secret|api_key|apikey|auth_token|token|access_token|private_key)\s*([:=])\s*([\"']?)([^\"'\s&,;]{4,})\3",
        r"\1\2\3[REDACTED_SECRET]\3",
        sanitized,
    )

    # 9. URL Query Parameters containing sensitive auth data
    sanitized = re.sub(
        r"(?i)([?&](?:token|key|api_key|apikey|secret|password|auth|access_token)=)([^&\s]{4,})",
        r"\1[REDACTED]",
        sanitized,
    )


    return sanitized


def is_sensitive_process(hwnd: int) -> bool:
    """Returns True if the HWND belongs to a sensitive security app or password manager."""
    if not hwnd:
        return False
    try:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return False

        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not h_proc:
            return False
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                proc_name = os.path.basename(buf.value).lower()
                return proc_name in SENSITIVE_PROCESS_NAMES
        finally:
            kernel32.CloseHandle(h_proc)
    except Exception:
        pass
    return False


def is_password_field(hwnd: int, uia_elem: Optional[Any] = None) -> bool:
    """Checks whether the target Win32 control or UI Automation element is a masked password field."""
    # 1. Win32 Edit Control Check
    if hwnd:
        try:
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style & ES_PASSWORD:
                return True
            pw_char = user32.SendMessageW(hwnd, EM_GETPASSWORDCHAR, 0, 0)
            if pw_char != 0:
                return True
        except Exception:
            pass

    # 2. UI Automation Element Check
    if uia_elem is not None:
        try:
            if getattr(uia_elem, "CurrentIsPassword", False):
                return True
        except Exception:
            pass
        try:
            if uia_elem.GetCurrentPropertyValue(UIA_IsPasswordPropertyId):
                return True
        except Exception:
            pass

    return False


def is_sensitive_or_password_focused(hwnd: Optional[int] = None) -> Tuple[bool, str]:
    """
    Comprehensive multi-layer security guard:
    Checks if the active foreground window belongs to a sensitive password/security process,
    or if the currently focused control/element (Win32 or Web/UIA) is a password field.
    Returns: (is_blocked: bool, reason: str)
    """
    target_hwnd = hwnd or user32.GetForegroundWindow()
    if not target_hwnd:
        return False, ""

    # 1. Check if foreground process is a sensitive password manager or security tool
    if is_sensitive_process(target_hwnd):
        return True, "Passwort-Manager oder Sicherheitsfenster erkannt"

    # 2. Check Win32 Edit control password attributes (ES_PASSWORD / EM_GETPASSWORDCHAR)
    try:
        thread_id = user32.GetWindowThreadProcessId(target_hwnd, None)
        if thread_id:
            gti = GUITHREADINFO()
            gti.cbSize = ctypes.sizeof(GUITHREADINFO)
            if user32.GetGUIThreadInfo(thread_id, ctypes.byref(gti)):
                focus_hwnd = gti.hwndFocus or gti.hwndCaret or target_hwnd
                if is_password_field(focus_hwnd):
                    return True, "Maskiertes Win32-Passwortfeld erkannt"
    except Exception:
        pass

    # 3. Check Windows UI Automation focused element (Web browsers, Electron, modern apps)
    try:
        import comtypes
        import comtypes.client
        from comtypes.gen import UIAutomationClient

        ctypes.windll.ole32.CoInitialize(None)
        uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation)
        elem = uia.GetFocusedElement()
        if elem:
            # Check UIA CurrentIsPassword / Property 30019
            if is_password_field(0, elem):
                return True, "Web-/App-Passwortfeld erkannt"

            # Check accessible properties for password hints in web browsers
            try:
                elem_class = (getattr(elem, "CurrentClassName", "") or "").lower()
                elem_help = (getattr(elem, "CurrentHelpText", "") or "").lower()
                if any(kw in elem_class for kw in ("password", "passwd", "kennwort", "passwort")) or \
                   any(kw in elem_help for kw in ("password", "passwd", "kennwort", "passwort")):
                    return True, "Passwort-Eingabeelement erkannt"
            except Exception:
                pass
    except Exception:
        pass

    return False, ""


def get_caret_screen_position() -> Optional[Tuple[int, int]]:
    """
    Returns (x, y) screen coordinates of the active text cursor/caret or focused input control.
    Hierarchical resolution:
    1. Active Win32 Caret (Notepad, Word, editors with true caret)
    2. Focused child input control bounding rect center (Explorer search/address bar, dialogs, web inputs)
    3. Mouse cursor within the active foreground window
    4. Global mouse cursor position
    """
    try:
        hwnd_fg = user32.GetForegroundWindow()
        if not hwnd_fg:
            # Fallback to mouse cursor
            pt_cursor = POINT()
            if user32.GetCursorPos(ctypes.byref(pt_cursor)):
                if pt_cursor.x > 0 or pt_cursor.y > 0:
                    return (pt_cursor.x, pt_cursor.y)
            return None

        thread_id = user32.GetWindowThreadProcessId(hwnd_fg, None)
        if not thread_id:
            pt_cursor = POINT()
            if user32.GetCursorPos(ctypes.byref(pt_cursor)):
                return (pt_cursor.x, pt_cursor.y)
            return None

        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(GUITHREADINFO)

        if user32.GetGUIThreadInfo(thread_id, ctypes.byref(gti)):
            # 1. Active Win32 Caret (Strict check: MUST have valid non-empty caret rectangle and hwndCaret)
            if gti.hwndCaret:
                rc = gti.rcCaret
                has_dimensions = (rc.right > rc.left) or (rc.bottom > rc.top)
                has_offset = (rc.left != 0 or rc.top != 0)
                if has_dimensions or has_offset:
                    caret_mid_x = (rc.left + rc.right) // 2 if rc.right > rc.left else rc.left
                    pt = POINT(caret_mid_x, rc.bottom)
                    if user32.ClientToScreen(gti.hwndCaret, ctypes.byref(pt)):
                        if pt.x > 0 or pt.y > 0:
                            return (pt.x, pt.y)

            # 2. Focused child input control (Explorer search bar, address bar, edit fields)
            if gti.hwndFocus and gti.hwndFocus != hwnd_fg:
                r_focus = RECT()
                if user32.GetWindowRect(gti.hwndFocus, ctypes.byref(r_focus)):
                    w = r_focus.right - r_focus.left
                    h = r_focus.bottom - r_focus.top
                    # Sensible input field dimensions (not the entire window or screen)
                    if 15 < w < 2200 and 12 < h < 1200:
                        ctrl_mid_x = (r_focus.left + r_focus.right) // 2
                        ctrl_bot_y = r_focus.bottom
                        if ctrl_mid_x > 0 and ctrl_bot_y > 0:
                            return (ctrl_mid_x, ctrl_bot_y)

        # 3. Mouse cursor if located within active foreground window
        pt_cursor = POINT()
        if user32.GetCursorPos(ctypes.byref(pt_cursor)):
            r_fg = RECT()
            if user32.GetWindowRect(hwnd_fg, ctypes.byref(r_fg)):
                if (r_fg.left <= pt_cursor.x <= r_fg.right) and (r_fg.top <= pt_cursor.y <= r_fg.bottom):
                    return (pt_cursor.x, pt_cursor.y)

            # 4. Fallback to global mouse position
            if pt_cursor.x > 0 or pt_cursor.y > 0:
                return (pt_cursor.x, pt_cursor.y)

    except Exception:
        pass
    return None


def get_preceding_text_context() -> Dict[str, any]:
    """
    Reads and analyzes preceding text before cursor to assist the LLM Flow Layer with:
    - Grammatical sentence continuation
    - Case sensitivity (uppercase vs lowercase initial word)
    - Automatic leading space insertion
    - Contextual coherence
    Uses Win32 EM_GETSEL first, and falls back to Windows UI Automation TextPattern/ValuePattern.
    Completely passive, non-intrusive, privacy-hardened, and sanitized.
    """
    result = {
        "preceding_text": "",
        "is_sentence_start": True,
        "is_clause_continuation": False,
        "needs_leading_space": False,
    }

    try:
        hwnd_fg = user32.GetForegroundWindow()
        if not hwnd_fg:
            return result

        # 0. Sensitive Process Isolation (Never extract text from password managers)
        if is_sensitive_process(hwnd_fg):
            return result

        fg_thread = user32.GetWindowThreadProcessId(hwnd_fg, None)
        if not fg_thread:
            return result

        full_preceding = ""

        # ---------------------------------------------------------------------
        # 1. Win32 Standard Edit Control / Caret Check (Notepad, standard inputs)
        # ---------------------------------------------------------------------
        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(GUITHREADINFO)

        if user32.GetGUIThreadInfo(fg_thread, ctypes.byref(gti)):
            target_hwnd = gti.hwndFocus or gti.hwndCaret or hwnd_fg
            if target_hwnd:
                # Password field check
                if is_password_field(target_hwnd):
                    return result

                start = wintypes.DWORD()
                end = wintypes.DWORD()
                res_ptr = ctypes.c_size_t()

                success = user32.SendMessageTimeoutW(
                    target_hwnd, 0x00B0, ctypes.byref(start), ctypes.byref(end), 0x0002, 10, ctypes.byref(res_ptr)
                )
                if success != 0:
                    cursor_pos = start.value
                    if cursor_pos > 0:
                        text_len_res = ctypes.c_size_t()
                        user32.SendMessageTimeoutW(target_hwnd, 0x000E, 0, 0, 0x0002, 10, ctypes.byref(text_len_res))
                        text_len = text_len_res.value
                        if text_len > 0:
                            buf_size = min(text_len + 1, 1024)
                            buf = ctypes.create_unicode_buffer(buf_size)
                            user32.SendMessageTimeoutW(target_hwnd, 0x000D, buf_size, buf, 0x0002, 10, ctypes.byref(res_ptr))
                            full_text = buf.value
                            full_preceding = full_text[:cursor_pos]

        # ---------------------------------------------------------------------
        # 2. Windows UI Automation (Chromium, Edge, Electron, VS Code, Word, Web)
        # ---------------------------------------------------------------------
        if not full_preceding:
            try:
                import comtypes
                import comtypes.client
                from comtypes.gen import UIAutomationClient

                ctypes.windll.ole32.CoInitialize(None)
                uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation)
                elem = uia.GetFocusedElement()
                if elem:
                    # Password property check on UIA element
                    if is_password_field(0, elem):
                        return result

                    # Try TextPattern (Supports selection endpoint range in rich editors)
                    try:
                        tp = elem.GetCurrentPattern(10014)  # UIA_TextPatternId
                        if tp:
                            t_pat = tp.QueryInterface(UIAutomationClient.IUIAutomationTextPattern)
                            sel = t_pat.GetSelection()
                            if sel and sel.Length > 0:
                                first_range = sel.GetElement(0)
                                doc_range = t_pat.DocumentRange
                                doc_range.MoveEndpointByRange(
                                    UIAutomationClient.TextPatternRangeEndpoint_End,
                                    first_range,
                                    UIAutomationClient.TextPatternRangeEndpoint_Start
                                )
                                prec_txt = doc_range.GetText(-1)
                                if prec_txt:
                                    full_preceding = prec_txt
                    except Exception:
                        pass

                    # Fallback to ValuePattern (Input textboxes, search bars)
                    if not full_preceding:
                        try:
                            vp = elem.GetCurrentPattern(10002)  # UIA_ValuePatternId
                            if vp:
                                v_pat = vp.QueryInterface(UIAutomationClient.IUIAutomationValuePattern)
                                val = v_pat.CurrentValue
                                if val:
                                    full_preceding = val
                        except Exception:
                            pass
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 3. Privacy Sanitization & Grammar Boundary Analysis
        # ---------------------------------------------------------------------
        if full_preceding:
            # Mask any secrets/tokens before grammatical analysis or LLM usage
            sanitized_preceding = sanitize_sensitive_text(full_preceding)
            preceding_tail = sanitized_preceding[-140:]
            stripped_tail = preceding_tail.rstrip()

            # Sentence boundary detection
            is_start = len(stripped_tail) == 0 or stripped_tail[-1] in (".", "!", "?", "\n", "\r")

            clause_connectors = (
                ",", ":", ";", "-", "—", "dass", "weil", "wenn", "ob", "und", "oder",
                "aber", "denn", "sondern", "sowie", "bzw.", "während", "obwohl", "da",
                "ist", "sind", "war", "waren", "wird", "werden", "hat", "haben",
                "that", "which", "because", "if", "and", "or", "but", "so", "as", "is", "are"
            )
            last_word = stripped_tail.split()[-1].lower().rstrip(",:;-") if stripped_tail.split() else ""
            is_clause = (not is_start) and (stripped_tail.endswith((",", ":", ";", "-")) or last_word in clause_connectors)

            # Spacing check: Needs a leading space if the cursor immediately follows non-whitespace characters
            needs_space = len(preceding_tail) > 0 and not preceding_tail[-1].isspace()

            result["preceding_text"] = preceding_tail
            result["is_sentence_start"] = is_start
            result["is_clause_continuation"] = is_clause
            result["needs_leading_space"] = needs_space

    except Exception:
        pass

    return result

