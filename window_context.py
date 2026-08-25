"""
Velodictum - Active Windows Context Detector
Detects the active focused window, process name, and category in <0.1ms using Win32 API.
"""
import ctypes
import os
from typing import Dict

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def get_active_window_context(include_deep_text: bool = False) -> Dict[str, any]:
    """
    Returns the active window context:
    {
        "title": str,
        "process_name": str,
        "category": str,  # "email", "code", "chat", "document", "browser", "general"
        "hint": str
    }
    If include_deep_text is True (only during dictation injection), also extracts pre-cursor text context.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {
            "title": "",
            "process_name": "",
            "category": "general",
            "hint": "General Application",
            "preceding_text": "",
            "is_sentence_start": True,
            "is_clause_continuation": False,
            "needs_leading_space": False,
        }

    # 1. Window Title (Safe passive query)
    length = user32.GetWindowTextLengthW(hwnd)
    title = ""
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value

    # 2. Process Name (Safe passive query)
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process_name = ""

    if pid.value:
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if h_process:
            try:
                exe_buf = ctypes.create_unicode_buffer(1024)
                size = ctypes.c_ulong(1024)
                if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(size)):
                    process_name = os.path.basename(exe_buf.value).lower()
            finally:
                kernel32.CloseHandle(h_process)

    # 3. Categorize Application & Extract Workspace Details
    category = "general"
    category_label = "Allgemeines Programm"
    workspace_project = ""
    workspace_file = ""
    git_branch = ""

    if process_name in ("windowsterminal.exe", "cmd.exe", "powershell.exe", "wt.exe", "bash.exe", "wsl.exe"):
        category = "terminal"
        category_label = "Terminal / Kommandozeile"
    elif process_name in ("code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe"):
        category = "code"
        category_label = "Entwicklung / Code-Editor"

        # Parse VS Code / IDE title (e.g. "● main.py - Velodictum [main] - Visual Studio Code")
        if title and ("Visual Studio Code" in title or "VSCodium" in title):
            parts = [p.strip() for p in title.split(" - ") if p.strip()]
            if len(parts) >= 3:
                workspace_file = parts[0].lstrip("● ").strip()
                proj_part = parts[1].strip()
                if "[" in proj_part and "]" in proj_part:
                    p_name, b_name = proj_part.split("[", 1)
                    workspace_project = p_name.strip()
                    git_branch = b_name.rstrip("]").strip()
                else:
                    workspace_project = proj_part
            elif len(parts) == 2 and parts[1] in ("Visual Studio Code", "VSCodium"):
                workspace_project = parts[0]

    elif process_name in ("outlook.exe", "thunderbird.exe", "mail.exe"):
        category = "email"
        category_label = "E-Mail Programm"
    elif process_name in ("slack.exe", "teams.exe", "discord.exe", "telegram.exe", "whatsapp.exe"):
        category = "chat"
        category_label = "Messenger / Chat"
    elif process_name in ("winword.exe", "notion.exe", "obsidian.exe", "onenote.exe", "notepad.exe", "notepad++.exe"):
        category = "document"
        category_label = "Dokument / Notizen"
    elif process_name in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"):
        category = "browser"
        category_label = "Web-Browser"

    hint = f"{category_label} ({process_name or 'Unbekannt'})"
    if title:
        short_title = title[:40] + "..." if len(title) > 40 else title
        hint += f" — '{short_title}'"

    # 4. Deep UI Automation Context (ONLY when actively processing dictation)
    preceding_text = ""
    is_sentence_start = True
    is_clause_continuation = False
    needs_leading_space = False

    if include_deep_text:
        try:
            from ui_automation_context import get_preceding_text_context
            ui_ctx = get_preceding_text_context()
            preceding_text = ui_ctx.get("preceding_text", "")
            is_sentence_start = ui_ctx.get("is_sentence_start", True)
            is_clause_continuation = ui_ctx.get("is_clause_continuation", False)
            needs_leading_space = ui_ctx.get("needs_leading_space", False)
        except Exception:
            pass

    from ui_automation_context import sanitize_sensitive_text
    safe_title = sanitize_sensitive_text(title)
    safe_project = sanitize_sensitive_text(workspace_project)
    safe_file = sanitize_sensitive_text(workspace_file)
    safe_hint = sanitize_sensitive_text(hint)
    safe_preceding = sanitize_sensitive_text(preceding_text)

    return {
        "title": safe_title,
        "process_name": process_name,
        "category": category,
        "hint": safe_hint,
        "workspace_project": safe_project,
        "workspace_file": safe_file,
        "git_branch": git_branch,
        "preceding_text": safe_preceding,
        "is_sentence_start": is_sentence_start,
        "is_clause_continuation": is_clause_continuation,
        "needs_leading_space": needs_leading_space,
    }


