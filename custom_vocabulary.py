"""
Velodictum - Custom Vocabulary & Personal Dictionary Manager
Injects user-defined terms, acronyms, and proper nouns directly into Whisper's acoustic decoding prompt.
"""
import json
import os
import threading
from typing import List, Dict, Optional

from config import get_app_dir, validate_safe_filepath, safe_atomic_json_write

VOCAB_FILE = os.path.join(get_app_dir(), "vocabulary.json")

DEFAULT_VOCABULARY = [
    {"word": "Velodictum", "category": "App", "description": "AI Diktier-App"},
    {"word": "Antigravity", "category": "Dev", "description": "Google AI Tool"},
    {"word": "PyQt6", "category": "Dev", "description": "GUI Framework"},
    {"word": "CUDA", "category": "Tech", "description": "NVIDIA GPU Beschleunigung"},
    {"word": "RTX 4080", "category": "Hardware", "description": "Grafikkarte"},
    {"word": "Ollama", "category": "AI", "description": "Lokaler LLM Server"},
    {"word": "OpenRouter", "category": "AI", "description": "Universal LLM API"},
    {"word": "GitHub", "category": "Dev", "description": "Code Repository"},
]


MAX_VOCAB_WORDS = 500
MAX_WORD_LENGTH = 35


class VocabularyManager:
    def __init__(self, filepath: str = VOCAB_FILE):
        self.filepath = validate_safe_filepath(filepath)
        self._lock = threading.Lock()
        self.words: List[Dict[str, str]] = []
        self._transient_terms: List[str] = []
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.words = data
                            return
                except Exception as e:
                    print(f"[Vocab] Error loading vocabulary file: {e}")

            # Use defaults if file does not exist or corrupted
            self.words = list(DEFAULT_VOCABULARY)
            self._save_locked()

    def save(self):
        with self._lock:
            self._save_locked()

    def _save_locked(self):
        try:
            safe_atomic_json_write(self.filepath, self.words, indent=2)
        except Exception as e:
            print(f"[Vocab] Error saving vocabulary: {e}")

    def add_word(self, word: str, category: str = "Allgemein", description: str = "") -> bool:
        import re
        if not word or not isinstance(word, str):
            return False
        word = word.strip()
        
        # 1. Bounds: Word length check (max 35 chars, min 2 chars)
        if len(word) < 2 or len(word) > MAX_WORD_LENGTH:
            return False

        # 2. Sanitization: Block control characters, newlines, and null bytes
        if any(ord(c) < 32 or ord(c) == 127 for c in word):
            return False

        # 3. Filtering: Block purely numeric sequences or symbol-only strings
        if word.isdigit() or not any(c.isalpha() for c in word):
            return False

        with self._lock:
            # 4. Storage Cap: Prevent vocabulary inflation / unbounded growth
            if len(self.words) >= MAX_VOCAB_WORDS:
                return False

            # Check if already exists (case-insensitive)
            for item in self.words:
                if item.get("word", "").lower() == word.lower():
                    return False
            self.words.append({"word": word, "category": category, "description": description})
            self._save_locked()
            return True

    def remove_word(self, word: str) -> bool:
        with self._lock:
            initial_len = len(self.words)
            self.words = [item for item in self.words if item.get("word", "").lower() != word.lower()]
            if len(self.words) != initial_len:
                self._save_locked()
                return True
            return False

    def get_words_list(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self.words)

    def set_transient_workspace_terms(self, terms: List[str]):
        """Dynamically seed project and file names without permanently saving to disk."""
        with self._lock:
            cleaned = []
            for t in terms:
                t_str = t.strip()
                if t_str and len(t_str) > 1 and t_str not in cleaned:
                    cleaned.append(t_str)
            self._transient_terms = cleaned

    def get_prompt_injection(self, language: str = "de") -> Optional[str]:
        """
        Generate a clean list of proper nouns and terminology for Whisper.
        Merges persistent vocabulary with transient workspace context terms.
        """
        with self._lock:
            valid_words = [item["word"].strip() for item in self.words if item.get("word") and item.get("word").strip()]
            for t in self._transient_terms:
                if t not in valid_words:
                    valid_words.append(t)

            if not valid_words:
                return None
            return ", ".join(valid_words) + "."

    def suggest_words_from_text(self, text: str) -> List[str]:
        """
        Scans text for PascalCase, camelCase, UPPERCASE, or code terms
        that are not yet present in vocabulary.json.
        """
        import re
        if not text:
            return []
        
        words = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", text)
        existing = {item.get("word", "").lower() for item in self.get_words_list()}
        
        suggestions = []
        for w in words:
            low = w.lower()
            if low not in existing and w not in suggestions and len(w) > 2:
                # Filter out standard German capitalized common nouns
                if any(char.isupper() for char in w[1:]) or "_" in w or "-" in w or w.isupper():
                    suggestions.append(w)
        return suggestions

    def learn_correction(self, original_phrase: str, corrected_phrase: str) -> List[str]:
        """
        Detects corrected proper nouns, names, and special terms between the original
        transcription/selection and the corrected version (e.g. 'Leon' -> 'Léon', 'Muller' -> 'Müller').
        Automatically saves valid learned proper nouns to vocabulary.json.
        """
        import re
        if not original_phrase or not corrected_phrase:
            return []
        if original_phrase.strip() == corrected_phrase.strip():
            return []

        orig_words = set(re.findall(r"\b\w+\b", original_phrase, flags=re.UNICODE))
        corr_words = re.findall(r"\b\w+\b", corrected_phrase, flags=re.UNICODE)

        # Standard German stopwords that should not be learned as proper nouns by accident
        stopwords = {
            "Der", "Die", "Das", "Ein", "Eine", "Einer", "Eines", "Einem", "Einen",
            "Und", "Oder", "Aber", "Denn", "Doch", "Weil", "Dass", "Wenn", "Als",
            "Mit", "Von", "Zu", "In", "Auf", "Aus", "Bei", "Nach", "Über", "Unter",
            "Ich", "Du", "Er", "Sie", "Es", "Wir", "Ihr", "Sie", "Ihnen", "Mein", "Dein",
            "Sehr", "Hier", "Dort", "Nicht", "Nur", "Auch", "Schon", "Wieder", "Bitte"
        }

        learned = []
        for w in corr_words:
            w_clean = w.strip()
            if not w_clean or len(w_clean) < 2 or len(w_clean) > MAX_WORD_LENGTH:
                continue

            # Must start with uppercase or special accented letter
            if not (w_clean[0].isupper() or w_clean[0] in "ÉÈÊÁÀÂÓÒÔÚÙÛÑÇÄÖÜ"):
                continue

            # Must not be a common stopword
            if w_clean in stopwords:
                continue

            # Must be a new or modified token compared to the original
            if w_clean not in orig_words:
                # Check for proper noun characteristics:
                # Accented chars, umlauts, camelCase, UPPERCASE, or direct replacement of a similar word
                has_accent = bool(re.search(r"[éèêëáàâäóòôöúùûüñçÉÈÊËÁÀÂÄÓÒÔÖÚÙÛÜÑÇ]", w_clean))
                has_mixed_case = any(c.isupper() for c in w_clean[1:]) or w_clean.isupper()
                is_replacement = any(w_clean.lower() != ow.lower() and (w_clean.lower().startswith(ow.lower()[:3]) or ow.lower().startswith(w_clean.lower()[:3])) for ow in orig_words)

                if has_accent or has_mixed_case or is_replacement:
                    if self.add_word(w_clean, category="Eigennamen", description="Automatisch aus Korrektur gelernt"):
                        learned.append(w_clean)
                        try:
                            from gui.signals import signals
                            signals.vocab_word_learned.emit(w_clean)
                        except Exception:
                            pass

        return learned


# Global singleton instance
vocab_manager = VocabularyManager()
