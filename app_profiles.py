"""
Velodictum - App-Specific Smart Profiles Manager
Automatically switches dictation modes and tone profiles based on the active target window.
(e.g., Code & Syntax in VS Code, Business E-Mail in Outlook, Casual Chat in Slack).
"""
import json
import os
import threading
from typing import Dict, Optional, List


from config import get_app_dir

PROFILES_FILE = os.path.join(get_app_dir(), "app_profiles.json")

DEFAULT_APP_RULES: List[Dict[str, str]] = [
    {
        "process": "code.exe",
        "name": "VS Code",
        "mode": "code_prompt",
        "tone": "default",
        "enabled": True,
    },
    {
        "process": "cursor.exe",
        "name": "Cursor IDE",
        "mode": "code_prompt",
        "tone": "default",
        "enabled": True,
    },
    {
        "process": "windowsterminal.exe",
        "name": "Windows Terminal",
        "mode": "code_prompt",
        "tone": "default",
        "enabled": True,
    },
    {
        "process": "outlook.exe",
        "name": "Microsoft Outlook",
        "mode": "email_pro",
        "tone": "formal_sie",
        "enabled": True,
    },
    {
        "process": "thunderbird.exe",
        "name": "Mozilla Thunderbird",
        "mode": "email_pro",
        "tone": "formal_sie",
        "enabled": True,
    },
    {
        "process": "slack.exe",
        "name": "Slack",
        "mode": "smart_clean",
        "tone": "informal_du",
        "enabled": True,
    },
    {
        "process": "discord.exe",
        "name": "Discord",
        "mode": "smart_clean",
        "tone": "informal_du",
        "enabled": True,
    },
    {
        "process": "whatsapp.exe",
        "name": "WhatsApp",
        "mode": "smart_clean",
        "tone": "informal_du",
        "enabled": True,
    },
    {
        "process": "notion.exe",
        "name": "Notion",
        "mode": "bullet_points",
        "tone": "default",
        "enabled": True,
    },
    {
        "process": "obsidian.exe",
        "name": "Obsidian",
        "mode": "bullet_points",
        "tone": "default",
        "enabled": True,
    },
]


class AppProfileManager:
    def __init__(self, filepath: str = PROFILES_FILE):
        self.filepath = filepath
        self._lock = threading.Lock()
        self.rules: List[Dict[str, str]] = []
        self.auto_switch_enabled = True
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.rules = data.get("rules", list(DEFAULT_APP_RULES))
                        self.auto_switch_enabled = data.get("auto_switch_enabled", True)
                        return
                except Exception as e:
                    print(f"[AppProfiles] Error loading rules: {e}")

            self.rules = list(DEFAULT_APP_RULES)
            self.auto_switch_enabled = True
            self._save_locked()

    def save(self):
        with self._lock:
            self._save_locked()

    def _save_locked(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "auto_switch_enabled": self.auto_switch_enabled,
                        "rules": self.rules,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print(f"[AppProfiles] Error saving rules: {e}")

    def get_profile_for_process(self, process_name: str) -> Optional[Dict[str, str]]:
        """
        Returns rule dict if a rule matches the active process_name and is enabled.
        """
        if not self.auto_switch_enabled or not process_name:
            return None

        p_low = process_name.lower().strip()
        with self._lock:
            for rule in self.rules:
                if not rule.get("enabled", True):
                    continue
                r_proc = rule.get("process", "").lower().strip()
                if r_proc and (r_proc == p_low or r_proc.replace(".exe", "") == p_low.replace(".exe", "")):
                    return rule
        return None

    def add_rule(self, process: str, name: str, mode: str, tone: str = "default") -> bool:
        process = process.strip().lower()
        if not process:
            return False
        with self._lock:
            for r in self.rules:
                if r.get("process", "").lower() == process:
                    r["name"] = name
                    r["mode"] = mode
                    r["tone"] = tone
                    r["enabled"] = True
                    self._save_locked()
                    return True
            self.rules.append({
                "process": process,
                "name": name,
                "mode": mode,
                "tone": tone,
                "enabled": True,
            })
            self._save_locked()
            return True

    def remove_rule(self, process: str) -> bool:
        process = process.strip().lower()
        with self._lock:
            init_len = len(self.rules)
            self.rules = [r for r in self.rules if r.get("process", "").lower() != process]
            if len(self.rules) != init_len:
                self._save_locked()
                return True
            return False

    def toggle_rule(self, process: str, enabled: bool):
        process = process.strip().lower()
        with self._lock:
            for r in self.rules:
                if r.get("process", "").lower() == process:
                    r["enabled"] = enabled
                    self._save_locked()
                    break

    def get_all_rules(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self.rules)


# Global singleton instance
app_profile_manager = AppProfileManager()
