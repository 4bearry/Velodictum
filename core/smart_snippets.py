"""
Velodictum - Smart Snippets & Voice Macros Manager
Expands spoken trigger phrases into text snippets, signatures, dynamic dates, and templates.
"""
import datetime
import json
import os
import re
import threading
from typing import Dict, List, Optional


from config import get_app_dir, validate_safe_filepath, safe_atomic_json_write

SNIPPETS_FILE = os.path.join(get_app_dir(), "snippets.json")

DEFAULT_SNIPPETS_DE: List[Dict[str, str]] = [
    {
        "trigger": "meine signatur",
        "expansion": "Mit freundlichen Grüßen,\n[Ihr Name]",
        "description": "Standard E-Mail-Signatur",
    },
    {
        "trigger": "heutiges datum",
        "expansion": "{date}",
        "description": "Aktuelles Datum (TT.MM.JJJJ)",
    },
    {
        "trigger": "aktuelle uhrzeit",
        "expansion": "{time}",
        "description": "Aktuelle Uhrzeit (HH:MM Uhr)",
    },
    {
        "trigger": "meine zwischenablage",
        "expansion": "{clipboard}",
        "description": "Inhalt der Zwischenablage einfügen",
    },
]

DEFAULT_SNIPPETS_EN: List[Dict[str, str]] = [
    {
        "trigger": "my signature",
        "expansion": "Best regards,\n[Your Name]",
        "description": "Standard email signature",
    },
    {
        "trigger": "today's date",
        "expansion": "{date}",
        "description": "Current date (YYYY-MM-DD)",
    },
    {
        "trigger": "current time",
        "expansion": "{time}",
        "description": "Current time (12-hour format)",
    },
    {
        "trigger": "my clipboard",
        "expansion": "{clipboard}",
        "description": "Paste clipboard content",
    },
]

DEFAULT_SNIPPETS = DEFAULT_SNIPPETS_EN


def get_default_snippets(lang: Optional[str] = None) -> List[Dict[str, str]]:
    if not lang:
        try:
            from config import config
            lang = getattr(config.system, "ui_language", "en")
        except Exception:
            lang = "en"
    if str(lang).lower().startswith("de"):
        return list(DEFAULT_SNIPPETS_DE)
    return list(DEFAULT_SNIPPETS_EN)


class SnippetManager:
    def __init__(self, filepath: str = SNIPPETS_FILE):
        self.filepath = validate_safe_filepath(filepath)
        self._lock = threading.Lock()
        self.snippets: List[Dict[str, str]] = []
        self.enabled = True
        self.load()

    def load(self):
        with self._lock:
            defaults = get_default_snippets()
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.snippets = data.get("snippets", defaults)
                            self.enabled = data.get("enabled", True)
                            return
                except Exception as e:
                    print(f"[Snippets] Error loading snippets: {e}")

            self.snippets = list(defaults)
            self.enabled = True
            self._save_locked()

    def save(self):
        with self._lock:
            self._save_locked()

    def _save_locked(self):
        try:
            safe_atomic_json_write(
                self.filepath,
                {
                    "enabled": self.enabled,
                    "snippets": self.snippets,
                },
                indent=2,
            )
        except Exception as e:
            print(f"[Snippets] Error saving snippets: {e}")

    def add_snippet(self, trigger: str, expansion: str, description: str = "") -> bool:
        trigger = trigger.strip().lower()
        if not trigger or not expansion:
            return False
        with self._lock:
            for s in self.snippets:
                if s.get("trigger", "").lower() == trigger:
                    s["expansion"] = expansion
                    s["description"] = description
                    self._save_locked()
                    return True
            self.snippets.append({
                "trigger": trigger,
                "expansion": expansion,
                "description": description,
            })
            self._save_locked()
            return True

    def remove_snippet(self, trigger: str) -> bool:
        trigger = trigger.strip().lower()
        with self._lock:
            init_len = len(self.snippets)
            self.snippets = [s for s in self.snippets if s.get("trigger", "").lower() != trigger]
            if len(self.snippets) != init_len:
                self._save_locked()
                return True
            return False

    def get_all_snippets(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self.snippets)

    def _get_clipboard_text(self) -> str:
        """Safely retrieve text from Windows clipboard without throwing exceptions."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data or ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        return ""

    def apply_snippets(self, text: str) -> str:
        """
        Replaces voice macro triggers in text with their expanded text or dynamic variables.
        Supported Variables:
        - {date}, {{date}}, {datum}, {{datum}} -> DD.MM.YYYY
        - {time}, {{time}}, {uhrzeit}, {{uhrzeit}} -> HH:MM Uhr
        - {clipboard}, {{clipboard}}, {zwischenablage}, {{zwischenablage}} -> Text from Windows Clipboard
        - {weekday}, {{weekday}}, {wochentag}, {{wochentag}} -> Montag, Dienstag, etc.
        - {iso_date}, {{iso_date}} -> YYYY-MM-DD
        - {year}, {{year}}, {jahr}, {{jahr}} -> YYYY
        - {month}, {{month}}, {monat}, {{monat}} -> MM
        - {day}, {{day}}, {tag}, {{tag}} -> DD
        """
        if not self.enabled or not text:
            return text

        now = datetime.datetime.now()
        from i18n import get_current_language
        is_en = (get_current_language() == "en")

        date_str = now.strftime("%Y-%m-%d") if is_en else now.strftime("%d.%m.%Y")
        time_str = now.strftime("%I:%M %p") if is_en else now.strftime("%H:%M Uhr")
        iso_date_str = now.strftime("%Y-%m-%d")
        year_str = now.strftime("%Y")
        month_str = now.strftime("%m")
        day_str = now.strftime("%d")

        weekdays = (
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            if is_en
            else ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        )
        weekday_str = weekdays[now.weekday()]

        clipboard_text = None

        with self._lock:
            for item in self.snippets:
                trig = item.get("trigger", "").strip()
                exp = item.get("expansion", "")
                if not trig or not exp:
                    continue

                # Check if clipboard variable is used before fetching
                if any(k in exp for k in ("{clipboard}", "{{clipboard}}", "{zwischenablage}", "{{zwischenablage}}")):
                    if clipboard_text is None:
                        clipboard_text = self._get_clipboard_text()

                resolved_exp = exp
                # 1. Date & Time
                for d_key in ("{date}", "{{date}}", "{datum}", "{{datum}}"):
                    resolved_exp = resolved_exp.replace(d_key, date_str)
                for t_key in ("{time}", "{{time}}", "{uhrzeit}", "{{uhrzeit}}"):
                    resolved_exp = resolved_exp.replace(t_key, time_str)
                for iso_key in ("{iso_date}", "{{iso_date}}"):
                    resolved_exp = resolved_exp.replace(iso_key, iso_date_str)
                for y_key in ("{year}", "{{year}}", "{jahr}", "{{jahr}}"):
                    resolved_exp = resolved_exp.replace(y_key, year_str)
                for m_key in ("{month}", "{{month}}", "{monat}", "{{monat}}"):
                    resolved_exp = resolved_exp.replace(m_key, month_str)
                for day_key in ("{day}", "{{day}}", "{tag}", "{{tag}}"):
                    resolved_exp = resolved_exp.replace(day_key, day_str)
                for w_key in ("{weekday}", "{{weekday}}", "{wochentag}", "{{wochentag}}"):
                    resolved_exp = resolved_exp.replace(w_key, weekday_str)

                # 2. Clipboard
                if clipboard_text is not None:
                    for clip_key in ("{clipboard}", "{{clipboard}}", "{zwischenablage}", "{{zwischenablage}}"):
                        resolved_exp = resolved_exp.replace(clip_key, clipboard_text)

                # Match full or embedded trigger phrase (case-insensitive)
                pattern = r"\b" + re.escape(trig) + r"\b"
                # Use callable replacement to prevent backslash/group-reference crashes (e.g. C:\path\1 or \g<0>)
                text = re.sub(pattern, lambda m, exp=resolved_exp: exp, text, flags=re.IGNORECASE)

        return text


# Global singleton instance
snippet_manager = SnippetManager()
