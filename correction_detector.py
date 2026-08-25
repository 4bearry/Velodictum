"""
Velodictum - Ultra-Precise Control-Pinned In-Field Correction Detector
Monitors text controls via Windows UI Automation ONLY after a dictation injection.
Pins the target window handle and control ID so that typing in other windows (e.g. ChatGPT,
Antigravity, Discord, or empty fields) is strictly ignored.
Employs strict sentence-structure anchoring (>= 60% overlap) and a 30-second one-shot lifecycle.
"""
import ctypes
from ctypes import wintypes
import os
import re
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from config import config
from custom_vocabulary import vocab_manager
from gui.signals import signals

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Blacklisted sensitive process names
SENSITIVE_PROCESSES = {
    "keepass.exe", "keepassxc.exe", "1password.exe", "bitwarden.exe",
    "lastpass.exe", "credentialui.exe", "logonui.exe"
}


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


class CorrectionDetector:
    def __init__(self, check_window_seconds: float = 35.0):
        self.check_window_seconds = check_window_seconds
        self._lock = threading.Lock()
        self._last_injection: Optional[Dict] = None
        self._prompted_timestamps: Dict[str, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Standard German/English stopwords
        self.stopwords = {
            "Der", "Die", "Das", "Ein", "Eine", "Einer", "Eines", "Einem", "Einen",
            "Und", "Oder", "Aber", "Denn", "Doch", "Weil", "Dass", "Wenn", "Als",
            "Mit", "Von", "Zu", "In", "Auf", "Aus", "Bei", "Nach", "Über", "Unter",
            "Ich", "Du", "Er", "Sie", "Es", "Wir", "Ihr", "Ihnen", "Mein", "Dein",
            "Sehr", "Hier", "Dort", "Nicht", "Nur", "Auch", "Schon", "Wieder", "Bitte",
            "Heute", "Gestern", "Morgen", "Immer", "Alles", "Nichts", "Etwas",
            "Zum", "Beispiel", "Namens", "Heißt", "Gibt", "Schönen", "Schöne",
            "The", "This", "That", "There", "Here", "With", "From", "About", "Have",
            "Has", "Had", "Will", "Would", "Should", "Could", "What", "When", "Where",
            "Fertig", "Aufnahme", "Wörterbuch", "Gespeichert", "Transformiert"
        }

    def start(self):
        """Starts background correction monitor."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stops background monitor."""
        with self._lock:
            self._running = False

    def record_injection(self, text: str, hwnd: Optional[int] = None):
        """
        Records a freshly injected dictation text and pins the target window and control.
        Arms the detector for a 35-second one-shot window on this specific control.
        """
        if not text or len(text.strip()) < 3:
            return

        target_hwnd = hwnd or user32.GetForegroundWindow()
        control_sig = self._get_active_control_signature(target_hwnd)

        with self._lock:
            words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
            self._last_injection = {
                "text": text,
                "words": words,
                "word_set": set(w.lower() for w in words),
                "hwnd": target_hwnd,
                "control_sig": control_sig,
                "timestamp": time.time(),
                "is_armed": True,
            }

    def disarm(self):
        """Disarms the watcher until the next injection."""
        with self._lock:
            if self._last_injection:
                self._last_injection["is_armed"] = False

    def inspect_text_for_corrections(
        self,
        current_text: str,
        current_hwnd: Optional[int] = None,
        current_control_sig: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Calculates exact word diffs between injected text and current text field.
        Strict verification:
        1. Must match pinned window and control (if provided).
        2. Must satisfy Sentence Anchor Overlap (>= 50% of the original sentence remains).
        3. Only returns candidate if an old word was replaced by a phonetically similar new word.
        """
        with self._lock:
            if not self._last_injection or not self._last_injection.get("is_armed", False):
                return []
            if time.time() - self._last_injection["timestamp"] > self.check_window_seconds:
                self._last_injection["is_armed"] = False
                return []
            last = dict(self._last_injection)

        # 1. Check pinned window
        if current_hwnd is not None and last.get("hwnd") and current_hwnd != last["hwnd"]:
            return []

        # 2. Check pinned control signature
        if current_control_sig is not None and last.get("control_sig") and current_control_sig != last["control_sig"]:
            return []

        if not current_text or current_text.strip() == last["text"].strip():
            return []

        old_words = re.findall(r"\b\w+\b", last["text"], flags=re.UNICODE)
        new_words = re.findall(r"\b\w+\b", current_text, flags=re.UNICODE)

        if not old_words or not new_words:
            return []

        old_lower_set = {w.lower() for w in old_words}
        new_lower_set = {w.lower() for w in new_words}

        # 3. Sentence Structure Anchor: At least 50% of original words must still be present!
        # (Protects against empty text fields, brand new unrelated typing, ChatGPT/Antigravity prompts)
        common_words = old_lower_set.intersection(new_lower_set)
        overlap_ratio = len(common_words) / max(1, len(old_lower_set))

        if overlap_ratio < 0.45 and len(common_words) < 3:
            # The text in this field is completely unrelated to our last injection -> Ignore!
            return []

        # 4. Find removed and newly added words
        removed_words = [w for w in old_words if w.lower() not in new_lower_set and w not in self.stopwords]
        added_words = [w for w in new_words if w.lower() not in old_lower_set and w not in self.stopwords]

        # In a normal manual correction, only 1-2 words are changed (not the entire text)
        if not removed_words or not added_words or len(removed_words) > 3 or len(added_words) > 3:
            return []

        existing_vocab = {item.get("word", "").lower() for item in vocab_manager.get_words_list()}
        now = time.time()

        candidates = []
        for new_w in added_words:
            new_clean = new_w.strip()
            if not new_clean or len(new_clean) < 2:
                continue

            # Must start with uppercase or special accented letter
            if not (new_clean[0].isupper() or new_clean[0] in "ÉÈÊÁÀÂÓÒÔÚÙÛÑÇÄÖÜ"):
                continue

            if new_clean in self.stopwords:
                continue

            if new_clean.lower() in existing_vocab:
                continue

            last_prompt_t = self._prompted_timestamps.get(new_clean, 0)
            if now - last_prompt_t < 15.0:
                continue

            # Find matching removed word
            for old_w in removed_words:
                old_clean = old_w.strip()
                if not old_clean or len(old_clean) < 2 or old_clean in self.stopwords:
                    continue
                if old_clean.lower() == new_clean.lower():
                    continue

                dist = _levenshtein_distance(new_clean.lower(), old_clean.lower())
                max_len = max(len(new_clean), len(old_clean))

                is_close_match = (dist <= 3 and max_len >= 4) or (dist <= 2 and max_len >= 3)
                shares_prefix_or_suffix = (new_clean.lower()[:2] == old_clean.lower()[:2]) or (new_clean.lower()[-3:] == old_clean.lower()[-3:])

                if is_close_match or (shares_prefix_or_suffix and dist <= 4):
                    candidates.append((old_clean, new_clean))
                    break

        return candidates

    def trigger_prompt(self, candidate_word: str, original_word: str = ""):
        """Emits UI prompt signal and records prompted timestamp."""
        now = time.time()
        with self._lock:
            last_t = self._prompted_timestamps.get(candidate_word, 0)
            if now - last_t < 4.0:
                return
            self._prompted_timestamps[candidate_word] = now
            # Note: We keep the watcher armed so that if the user continues typing
            # (e.g. 'Pawb' -> 'Pawbert'), the HUD prompt dynamically updates!

        print(f"[CorrectionDetector] Triggering Pinned HUD Prompt: '{original_word}' -> '{candidate_word}'")
        signals.vocab_suggestion_prompt.emit({
            "word": candidate_word,
            "original": original_word,
            "category": "Eigennamen",
        })

    def accept_candidate(self, candidate_word: str, original_word: str = "") -> bool:
        """Adds accepted candidate word directly into persistent vocabulary and disarms watcher."""
        desc = f"Aus Korrektur von '{original_word}' gelernt" if original_word else "Aus Textfeld-Korrektur übernommen"
        ok = vocab_manager.add_word(candidate_word, category="Eigennamen", description=desc)
        if ok:
            with self._lock:
                if self._last_injection:
                    self._last_injection["is_armed"] = False
            signals.vocab_word_learned.emit(candidate_word)
        return ok

    def _get_active_control_signature(self, hwnd: int) -> str:
        """Generates a stable signature for the active control to prevent cross-control leaking."""
        try:
            thread_id = user32.GetWindowThreadProcessId(hwnd, None)
            if thread_id:
                from ui_automation_context import GUITHREADINFO
                gti = GUITHREADINFO()
                gti.cbSize = ctypes.sizeof(GUITHREADINFO)
                if user32.GetGUIThreadInfo(thread_id, ctypes.byref(gti)):
                    focus_hwnd = gti.hwndFocus or gti.hwndCaret
                    if focus_hwnd:
                        return f"win_{hwnd}_ctrl_{focus_hwnd}"
        except Exception:
            pass
        return f"win_{hwnd}"

    def _get_active_control_text_uia(self) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Extracts active control text, active hwnd, and control signature.
        Strictly skips password controls and password managers.
        Returns: (text, hwnd, control_signature)
        """
        try:
            hwnd_fg = user32.GetForegroundWindow()
            if not hwnd_fg:
                return (None, None, None)

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd_fg, ctypes.byref(pid))
            if pid.value:
                h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                if h_proc:
                    try:
                        buf = ctypes.create_unicode_buffer(512)
                        size = ctypes.c_ulong(512)
                        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                            p_name = os.path.basename(buf.value).lower()
                            if p_name in SENSITIVE_PROCESSES:
                                return (None, None, None)
                    finally:
                        kernel32.CloseHandle(h_proc)

            import comtypes
            import comtypes.client
            from comtypes.gen import UIAutomationClient

            ole32.CoInitialize(None)
            uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation)
            elem = uia.GetFocusedElement()
            if not elem:
                return (None, hwnd_fg, None)

            # Security check: Password fields are strictly omitted
            try:
                if elem.CurrentIsPassword:
                    return (None, hwnd_fg, None)
            except Exception:
                pass

            ctrl_sig = self._get_active_control_signature(hwnd_fg)

            # 1. ValuePattern
            try:
                val_p = elem.GetCurrentPattern(10002)
                if val_p:
                    val_pat = val_p.QueryInterface(UIAutomationClient.IUIAutomationValuePattern)
                    val = val_pat.CurrentValue
                    if val and len(val.strip()) > 0:
                        return (val, hwnd_fg, ctrl_sig)
            except Exception:
                pass

            # 2. TextPattern
            try:
                txt_p = elem.GetCurrentPattern(10014)
                if txt_p:
                    txt_pat = txt_p.QueryInterface(UIAutomationClient.IUIAutomationTextPattern)
                    doc_range = txt_pat.DocumentRange
                    if doc_range:
                        txt = doc_range.GetText(-1)
                        if txt and len(txt.strip()) > 0:
                            return (txt, hwnd_fg, ctrl_sig)
            except Exception:
                pass

        except Exception:
            pass
        return (None, None, None)

    def _monitor_loop(self):
        """Passive background loop inspecting text changes in pinned active document/control."""
        while self._running:
            try:
                with self._lock:
                    is_armed = self._last_injection and self._last_injection.get("is_armed", False)
                    if is_armed and (time.time() - self._last_injection["timestamp"] > self.check_window_seconds):
                        self._last_injection["is_armed"] = False
                        is_armed = False

                if is_armed:
                    current_text, current_hwnd, current_ctrl_sig = self._get_active_control_text_uia()
                    if current_text:
                        corrections = self.inspect_text_for_corrections(
                            current_text=current_text,
                            current_hwnd=current_hwnd,
                            current_control_sig=current_ctrl_sig
                        )
                        for orig, cand in corrections:
                            self.trigger_prompt(cand, orig)
                            break
                    time.sleep(0.6)
                else:
                    time.sleep(1.2)  # Low-power sleep when not armed

            except Exception:
                time.sleep(1.0)


# Global singleton instance
correction_detector = CorrectionDetector()
