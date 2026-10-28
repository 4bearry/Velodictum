"""
Velodictum - AI Intelligence & Formatting Layer ("The Flow Layer")
Transforms raw STT transcripts into clean, professionally written text in realtime.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Optional, Dict

from formatting_providers import (
    BaseFormattingProvider,
    LocalRulesProvider,
    OllamaProvider,
    UniversalApiProvider,
    OpenAIProvider,
    GeminiProvider,
    GroqProvider,
    detect_provider,
    categorize_models,
)

# Automatically load .env if present
def _load_env():
    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.expanduser("~"), ".env")
    ]
    for p in env_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env()


MODES = {
    "flow": {
        "name": "Intelligenter Flow",
        "tag": "FLOW",
        "description": "Automatische App-Erkennung, KI-Grammatik, Spoken Markdown & dynamischer Satzfluss.",
    },
    "raw": {
        "name": "Rohdiktat (Bypass)",
        "tag": "RAW",
        "description": "1:1 wörtliche Whisper-Transkription ohne KI-Filter oder Transformationen (0ms Latenz).",
    },
}


def normalize_openrouter_model(name: str) -> str:
    """Normalizes shorthand model names or legacy IDs to valid model IDs."""
    if not name or not name.strip():
        return "qwen/qwen-2.5-72b-instruct"
    n = name.strip()
    low = n.lower()
    if low in ("qwen2.5:7b", "qwen2.5-7b", "qwen-7b", "qwen:7b", "qwen 7b"):
        return "qwen/qwen-2.5-7b-instruct"
    if low in ("qwen2.5:72b", "qwen2.5-72b", "qwen-72b", "qwen:72b", "qwen 72b", "qwen", "qwen2.5", "qwen 2.5"):
        return "qwen/qwen-2.5-72b-instruct"
    if low in ("gemini-2.5-flash-lite", "gemini-flash-lite", "flash-lite"):
        return "google/gemini-2.5-flash-lite"
    if low in ("gemini-2.0-flash-001", "gemini-2.0-flash", "gemini-flash", "gemini"):
        return "google/gemini-2.5-flash"
    if low in ("gemini-2.5-flash", "gemini-2.5"):
        return "google/gemini-2.5-flash"
    if low in ("gpt-4o-mini", "4o-mini"):
        return "openai/gpt-4o-mini"
    if low in ("gpt-4o", "4o"):
        return "openai/gpt-4o"
    if low in ("llama3.3:70b", "llama3.3-70b", "llama-3.3-70b", "llama3.3", "llama"):
        return "meta-llama/llama-3.3-70b-instruct"
    if low in ("claude-sonnet-4", "claude-sonnet", "sonnet"):
        return "anthropic/claude-sonnet-4"
    if low in ("claude-3-haiku", "claude-3.5-haiku", "claude-haiku", "haiku"):
        return "anthropic/claude-3-haiku"
    if low in ("mistral-small-24b-instruct-2501", "mistral-small-3", "mistral-small"):
        return "mistralai/mistral-small-24b-instruct-2501"
    if low in ("deepseek", "deepseek-chat", "deepseek-v3"):
        return "deepseek/deepseek-chat"
    return n


class AIFormatter:
    def __init__(
        self,
        mode: str = "flow",
        engine: str = "rules",
        api_key: Optional[str] = None,
        api_endpoint: str = "https://openrouter.ai/api/v1",
        model: str = "qwen/qwen-2.5-72b-instruct",
        ollama_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "qwen2.5:7b",
        openrouter_model: Optional[str] = None,
        tone: str = "default",
        custom_instructions: str = "",
    ):
        self.mode = "raw" if mode == "raw" else "flow"
        self.engine = "universal" if engine == "openrouter" else engine  # "rules", "ollama", "universal", "gemini", "openai", "groq"
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        self.model = model or openrouter_model or "qwen/qwen-2.5-72b-instruct"
        self.ollama_url = ollama_url.rstrip("/").replace("localhost", "127.0.0.1")
        self.ollama_model = ollama_model
        self.openrouter_model = self.model  # Legacy compatibility alias
        self.tone = tone
        self.custom_instructions = custom_instructions

    def get_provider(self) -> BaseFormattingProvider:
        """Returns the configured modular Formatting Provider."""
        eff_engine = "universal" if self.engine == "openrouter" else self.engine

        from config import config
        is_airgapped = getattr(config.system, "offline_privacy_mode", False)
        if is_airgapped and eff_engine not in ("ollama", "rules"):
            eff_engine = "ollama"

        if eff_engine == "ollama":
            return OllamaProvider(
                ollama_url=self.ollama_url,
                model=self.ollama_model,
            )
        elif eff_engine == "universal":
            endpoint = getattr(self, "api_endpoint", None) or getattr(config.formatting, "api_endpoint", "https://openrouter.ai/api/v1")
            model = getattr(self, "model", None) or getattr(self, "openrouter_model", None) or getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
            routing_strategy = getattr(config.formatting, "routing_strategy", "latency")
            zero_data_retention = getattr(config.formatting, "zero_data_retention", True)
            allow_fallbacks = getattr(config.formatting, "allow_fallbacks", True)
            return UniversalApiProvider(
                endpoint=endpoint,
                api_key=self._get_api_key("universal"),
                model=model,
                routing_strategy=routing_strategy,
                zero_data_retention=zero_data_retention,
                allow_fallbacks=allow_fallbacks,
            )
        elif eff_engine == "openai":
            model = getattr(config.formatting, "openai_model", "gpt-4o-mini")
            key = self._get_api_key("openai")
            return OpenAIProvider(api_key=key, model=model)
        elif eff_engine == "gemini":
            model = getattr(config.formatting, "gemini_model", "gemini-2.5-flash")
            key = self._get_api_key("gemini")
            return GeminiProvider(api_key=key, model=model)
        elif eff_engine == "groq":
            model = getattr(config.formatting, "groq_model", "llama-3.3-70b-versatile")
            key = self._get_api_key("groq")
            return GroqProvider(api_key=key, model=model)
        else:
            return LocalRulesProvider(rule_engine_callback=lambda t: self._format_with_rules(t))

    def check_ollama_status(self) -> Dict:
        """Check if local Ollama daemon is reachable and list available models."""
        provider = OllamaProvider(self.ollama_url, self.ollama_model)
        return provider.test_connection()

    def _get_api_key(self, engine: Optional[str] = None) -> Optional[str]:
        import security_credentials as sec
        from config import config

        eff_engine = engine or ("universal" if self.engine == "openrouter" else self.engine)

        # 1. Query Windows Credential Manager
        val = config.formatting.get_api_key(eff_engine)
        if val and val.strip():
            return val.strip()

        # 2. Check in-memory instance key
        if self.api_key and self.api_key.strip():
            return self.api_key.strip()

        # 3. Fallback to OS Environment Variables
        if eff_engine in ("universal", "openrouter"):
            return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("UNIVERSAL_API_KEY")
        elif eff_engine == "gemini":
            return os.environ.get("GEMINI_API_KEY")
        elif eff_engine == "groq":
            return os.environ.get("GROQ_API_KEY")
        elif eff_engine == "openai":
            return os.environ.get("OPENAI_API_KEY")
        return None

    def format_text(
        self,
        raw_text: str,
        language: Optional[str] = "de",
        window_context: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """
        Format raw transcribed text according to the selected mode, engine, and window context.
        Returns {"text": formatted_text, "latency": float, "mode": mode, "engine": engine}
        """
        if not raw_text or not raw_text.strip():
            return {"text": "", "latency": 0.0, "mode": self.mode, "engine": self.engine}

        # 1. Dynamic App-Specific Profile Auto-Detection
        effective_mode = self.mode
        effective_tone = getattr(self, "tone", "default")
        from config import config
        if getattr(config.formatting, "auto_app_profiles", True) and window_context:
            p_name = window_context.get("process_name", "")
            if p_name:
                try:
                    from app_profiles import app_profile_manager
                    matched_rule = app_profile_manager.get_profile_for_process(p_name)
                    if matched_rule:
                        effective_mode = matched_rule.get("mode", effective_mode)
                        effective_tone = matched_rule.get("tone", effective_tone)
                except Exception:
                    pass

        start_t = time.perf_counter()
        
        clean_input = raw_text.strip()

        # Check for Spoken Cancel Voice Actions (Strictly isolated or explicit trailing cancel)
        voice_cancel_enabled = getattr(config.formatting, "voice_cancel_enabled", True)
        if voice_cancel_enabled:
            # 1. Standalone / Isolated cancel
            standalone_cancel = r"^(?:abbrechen|verwerfen|diktat\s+abbrechen|aufnahme\s+verwerfen|cancel|discard|nicht\s+einfügen|stopp\s+abbrechen)[.!?]?$"
            if re.match(standalone_cancel, clean_input, flags=re.IGNORECASE):
                return {"text": "", "latency": 0.0, "mode": effective_mode, "engine": "rules", "action": "cancel"}

            # 2. Explicit trailing cancel phrase after hesitation
            trailing_cancel = r"(?:,\s*|\s+)(?:ach\s+nein\s+(?:doch\s+)?(?:abbrechen|verwerfen)|nein\s+abbrechen|nein\s+verwerfen|bitte\s+verwerfen|bitte\s+abbrechen|diktat\s+verwerfen)[.!?]?$"
            if re.search(trailing_cancel, clean_input, flags=re.IGNORECASE):
                return {"text": "", "latency": 0.0, "mode": effective_mode, "engine": "rules", "action": "cancel"}

        # 2. Check for "Send It" Voice Actions (e.g., "... und absenden", "... und abschicken", "... send it")
        action = None
        send_it_enabled = getattr(config.formatting, "send_it_enabled", True) and getattr(config.injection, "send_it_enabled", True)

        if send_it_enabled:
            send_it_patterns = [
                r"(?:,\s*|\s+)(?:und\s+absenden|absenden|bitte\s+absenden|absenden\s+bitte|nachricht\s+absenden)[.!?]?\s*$",
                r"(?:,\s*|\s+)(?:und\s+abschicken|abschicken|bitte\s+abschicken|abschicken\s+bitte|nachricht\s+abschicken)[.!?]?\s*$",
                r"(?:,\s*|\s+)(?:und\s+senden|senden|bitte\s+senden|senden\s+bitte|nachricht\s+senden)[.!?]?\s*$",
                r"(?:,\s*|\s+)(?:send\s+it|send\s+message|press\s+enter|enter)[.!?]?\s*$",
            ]
            for pat in send_it_patterns:
                if re.search(pat, clean_input, flags=re.IGNORECASE):
                    clean_input = re.sub(pat, "", clean_input, flags=re.IGNORECASE).strip()
                    action = "send_enter"
                    break

        if effective_mode == "raw":
            return {"text": clean_input, "latency": 0.0, "mode": "raw", "engine": "bypass", "action": action}

        formatted = clean_input
        used_fast_path = False

        if self.engine == "rules":
            formatted = self._format_with_rules(clean_input, language, window_context)
        elif self._can_use_fast_local_path(clean_input, window_context, effective_tone):
            formatted = self._format_with_rules(clean_input, language, window_context)
            used_fast_path = True
        else:
            system_prompt = self._build_system_prompt(language or "de", window_context)
            user_msg = self._build_user_message(clean_input)
            try:
                provider = self.get_provider()
                formatted = provider.format_text(clean_input, system_prompt, user_msg)
            except Exception as e:
                print(f"[AIFormatter] Error ({self.engine}): {e}. Falling back to rule engine...")
                formatted = self._format_with_rules(clean_input, language, window_context)

        latency = time.perf_counter() - start_t
        return {
            "text": formatted.strip(),
            "latency": latency,
            "mode": effective_mode,
            "engine": "smart_fast_path" if used_fast_path else self.engine,
            "action": action,
        }

    def prewarm_connection(self) -> bool:
        """Pre-warms the active LLM formatting provider's HTTPS connection during recording."""
        if self.mode == "raw" or self.engine == "rules":
            return True
        try:
            provider = self.get_provider()
            return provider.prewarm_connection()
        except Exception:
            return False

    def _can_use_fast_local_path(
        self,
        text: str,
        window_context: Optional[Dict[str, str]] = None,
        effective_tone: Optional[str] = None,
    ) -> bool:
        """
        Determines in <0.2ms if a short, already well-punctuated Whisper transcript
        needs zero LLM restructuring (no fillers, no self-corrections, no spoken markdown,
        no email greetings/lists, default tone) and can take the 0ms local fast-path.
        """
        from config import config
        if not getattr(config.formatting, "smart_fast_path", True):
            return False

        tone = effective_tone or getattr(self, "tone", "default")
        if tone != "default" or (self.custom_instructions and self.custom_instructions.strip()):
            return False

        if self.mode in ("email_pro", "bullet_points", "code_prompt"):
            return False

        if window_context:
            cat = window_context.get("category", "")
            style = window_context.get("style", "")
            if cat in ("code", "terminal") or style in ("code", "terminal"):
                return False

        words = text.split()
        if len(words) < 2 or len(words) > 9:
            return False

        # Must already have proper Whisper casing and terminal punctuation
        if not text[0].isupper() or text[-1] not in (".", "!", "?"):
            return False

        # Reject if ASCII umlaut replacements are present (e.g. naechste, fuer, ueber)
        if re.search(r"\b\w*(?:ae|oe|ue)\w*\b", text, flags=re.IGNORECASE):
            return False

        # Reject if fillers, self-corrections, spoken markdown, lists, or email patterns exist
        complex_triggers = (
            r"\b(?:äh+m?|ähm+|öhm+|mhm+|um+|uh+|er+|ah+|halt|quasi|sozusagen|eigentlich)\b|"
            r"\b(?:ach\s+nein|nein|warte|bzw|besser\s+gesagt|oder\s+besser|ich\s+meine|korrektur|lieber|streich(?:e|en)?|lösche|entferne|behalte\s+nur|nimm\s+nur|actually|instead|delete)\b|"
            r"\b(?:überschrift|heading|checkbox|to-?do|fett|bold|kursiv|italic|codeblock|neue\s+zeile|zeilenumbruch|new\s+line|neuer\s+absatz|absatz|new\s+paragraph|doppelpunkt|punkt\s+\w+|stichpunkt|liste|erstens|zweitens)\b|"
            r"^(?:hallo|hi|hey|dear|sehr\s+geehrte|liebe)\b|"
            r"\b(?:viele\s+grüße|liebe\s+grüße|mit\s+freundlichen\s+grüßen|best\s+regards|sincerely)\b"
        )
        if re.search(complex_triggers, text, flags=re.IGNORECASE):
            return False

        return True

    # =========================================================================
    # 1. High-Precision Local Rule-Based Engine (With Auto-Adaptive Intelligence)
    # =========================================================================
    def _format_with_rules(self, text: str, language: Optional[str] = "de", window_context: Optional[Dict[str, str]] = None) -> str:
        """Fast, offline, zero-latency hybrid post-processor."""
        cleaned = text

        # 1. Remove spoken hesitations and fillers
        fillers = [
            r"\b(äh+m?)\b", r"\b(ähm+)\b", r"\b(öhm+)\b", r"\b(mhm+)\b",
            r"\b(um+)\b", r"\b(uh+)\b", r"\b(er+)\b", r"\b(ah+)\b",
            r"\b(like,\s+you know)\b",
        ]
        for pat in fillers:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 2. Resolve Common Spoken Self-Corrections & Meta-Instructions
        correction_signals = [
            r"(?:,\s*|\s+)(?:ach\s+nein|nein\s+warte|warte\s+mal|eigentlich\s+doch|bzw\.?|besser\s+gesagt|nein\s+lieber|oder\s+besser)(?:,\s*|\s+)",
            r"(?:,\s*|\s+)(?:actually\s+no|no\s+wait|wait\s+no|I\s+mean|or\s+rather)(?:,\s*|\s+)",
        ]
        for sig in correction_signals:
            parts = re.split(sig, cleaned, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                left = parts[0]
                right = parts[1]
                words = left.split()
                if len(words) > 1:
                    left_kept = " ".join(words[:-1])
                    cleaned = f"{left_kept} {right}"
                else:
                    cleaned = right

        # 2b. Filter sentences based on spoken directive (e.g. 'A und streiche jeden Satz...', 'Behalte nur den Satz mit...')
        strike_match = re.search(r"(?:,\s*|\s+)(?:(?:a|ah|ach|oh|aber|und)\s+)*(?:streiche|lösche|entferne|nimm\s+nur|behalte\s+nur)\s+(?:jeden|alle|den)?\s*(?:sätze|satz)?\s*(?:außer|mit)?\s*(?:den|die|das)?\s*(?:mit|über|zu)?\s*(?:dem|den|der|einem|einen|des)?\s*([a-zäöüß]+)[.!?]?\s*$", cleaned, flags=re.IGNORECASE)
        if strike_match:
            kw = strike_match.group(1).lower()
            text_without_cmd = cleaned[:strike_match.start()].strip()
            # Split into sentences
            raw_sents = re.split(r"(?<=[.!?])\s+", text_without_cmd)
            matched_sents = [s for s in raw_sents if kw in s.lower()]
            if matched_sents:
                cleaned = " ".join(matched_sents)
            else:
                cleaned = text_without_cmd

        # 3. Spoken Markdown Syntax & Layout Directives
        # Headings: Überschrift 1 / 2 / 3 / Heading 1 / 2 / 3 -> # / ## / ###
        cleaned = re.sub(r"(?i)\b(?:überschrift|heading)\s*1\s*[:\.]?\s*", r"\n# ", cleaned)
        cleaned = re.sub(r"(?i)\b(?:überschrift|heading)\s*2\s*[:\.]?\s*", r"\n## ", cleaned)
        cleaned = re.sub(r"(?i)\b(?:überschrift|heading)\s*3\s*[:\.]?\s*", r"\n### ", cleaned)

        # Checkboxes: Checkbox unerledigt / pending / erledigt / done
        cleaned = re.sub(r"(?i)\b(?:checkbox\s+(?:unerledigt|offen|pending|open|unchecked)|offenes\s+to-?do|open\s+to-?do|to-?do)\s*[:\.]?\s*", r"\n- [ ] ", cleaned)
        cleaned = re.sub(r"(?i)\b(?:checkbox\s+(?:erledigt|done|completed|checked)|erledigtes\s+to-?do|completed\s+to-?do)\s*[:\.]?\s*", r"\n- [x] ", cleaned)

        # Formatting: Fett, Kursiv, Durchgestrichen, Bold, Italic
        cleaned = re.sub(r"(?i)\b(?:fettgedruckt|in\s+fett|fett|bold)\s+([^,.;\n]+)", r"**\1**", cleaned)
        cleaned = re.sub(r"(?i)\b(?:kursivgedruckt|in\s+kursiv|kursiv|italic)\s+([^,.;\n]+)", r"*\1*", cleaned)
        cleaned = re.sub(r"(?i)\b(?:durchgestrichen|strikethrough)\s+([^,.;\n]+)", r"~~\1~~", cleaned)

        # Spoken line breaks
        cleaned = re.sub(r"(?i)\b(?:neuer\s+absatz|absatz|new\s+paragraph|paragraph)\b\.?", r"\n\n", cleaned)
        cleaned = re.sub(r"(?i)\b(?:neue\s+zeile|zeilenumbruch|new\s+line|line\s+break)\b\.?", r"\n", cleaned)

        # 4. Mode Selection & Auto-Adaptive Mixed Intent Handling
        is_auto = (self.mode == "auto_adaptive")

        # Check if text contains email patterns
        email_greeting_pat = r"^(hallo\s+[\w\s]+|sehr\s+geehrte[rn]?\s+[\w\s]+|guten\s+tag\s+[\w\s]+|liebe[rn]?\s+[\w\s]+|hi\s+[\w\s]+|dear\s+[\w\s]+|hey\s+[\w\s]+)[,:]?"
        email_closing_pat = r"(viele\s+grüße|liebe\s+grüße|mit\s+freundlichen\s+grüßen|beste\s+grüße|best\s+regards|sincerely|thanks|danke)[,\s]+([\w\s]+)?$"

        # Check for list / enumeration triggers
        list_header_pat = r"^(ich\s+will\s+folgendes\s+(?:einkaufen|besorgen|erledigen|machen)|erstelle\s+eine\s+liste\s*(?:für|mit)?|mach\s+(?:mir\s+)?eine\s+liste\s*(?:für|mit)?|folgende\s+punkte|folgendes\s+ist\s+zu\s+tun|einkaufsliste|to-do-liste|meine\s+aufgaben)[:\s]*(.*)$"
        has_list_triggers = bool(re.search(r"\b(erstens|zweitens|drittens|punkt\s+\d+|1\.|2\.|außerdem)\b", cleaned, flags=re.IGNORECASE))
        has_list_header = bool(re.match(list_header_pat, cleaned, flags=re.IGNORECASE))
        has_code_triggers = bool(re.search(r"\b(function|def|variable|const|let|import|class|return)\b", cleaned, flags=re.IGNORECASE))

        if is_auto or self.mode == "email_pro":
            # Check for email greeting
            greeting_match = re.match(email_greeting_pat, cleaned, flags=re.IGNORECASE)
            closing_match = re.search(email_closing_pat, cleaned, flags=re.IGNORECASE)

            greeting_part = ""
            closing_part = ""
            body = cleaned

            if greeting_match:
                greeting_part = greeting_match.group(1).strip()
                if not greeting_part.endswith((",", ":")):
                    greeting_part += ","
                body = cleaned[greeting_match.end():].strip()

            closing_match = re.search(email_closing_pat, body, flags=re.IGNORECASE)
            if closing_match:
                closing_part = closing_match.group(0).strip()
                body = body[:closing_match.start()].strip()

            # Process body: check for inline list header or bullet triggers
            lh_match = re.match(list_header_pat, body, flags=re.IGNORECASE)
            if (is_auto and (has_list_triggers or lh_match)) or self.mode == "bullet_points":
                if lh_match and lh_match.group(2).strip():
                    intro_raw = lh_match.group(1).strip()
                    items_raw = lh_match.group(2).strip()
                    # Clean meta-command into nice header
                    if any(w in intro_raw.lower() for w in ("einkaufen", "besorgen", "einkaufsliste")):
                        intro = "Einkaufsliste:"
                    elif any(w in intro_raw.lower() for w in ("aufgaben", "to-do", "erledigen")):
                        intro = "To-Do-Liste:"
                    elif "liste" in intro_raw.lower():
                        intro = "Liste:"
                    else:
                        intro = intro_raw.rstrip(":,.") + ":"

                    raw_items = re.split(r"[,;]|\s+und\s+|\s+sowie\s+|\s+auch\s+", items_raw, flags=re.IGNORECASE)
                    clean_items = [p.strip().rstrip(".,;") for p in raw_items if len(p.strip()) > 1]
                    if clean_items:
                        bullet_lines = [f"• {it[0].upper() + it[1:]}" for it in clean_items]
                        body = intro + "\n" + "\n".join(bullet_lines)
                else:
                    # Clean trailing commas and connectors before splitting
                    body_parts = re.split(r"(?:[.;!?]|\bund\s+zwar\b|\bausserdem\b|\baußerdem\b|\bpunkt\s+\d+\b|\berstens\b|\bzweitens\b|\bdrittens\b)", body, flags=re.IGNORECASE)
                    items = [re.sub(r"(?:,\s*|\s+)(?:und|sowie|auch)\s*$", "", p.strip(), flags=re.IGNORECASE) for p in body_parts if len(p.strip()) > 2]
                    if len(items) > 1:
                        if len(items) > 2 and any(w in items[0].lower() for w in ("punkte", "folgendes", "anbei", "themen", "einkaufen", "liste")):
                            intro = items[0].rstrip(":,.") + ":"
                            bullet_lines = [f"• {it[0].upper() + it[1:].rstrip(' ,;.')}" for it in items[1:]]
                            body = intro + "\n" + "\n".join(bullet_lines)
                        else:
                            bullet_lines = [f"• {it[0].upper() + it[1:].rstrip(' ,;.')}" for it in items]
                            body = "\n".join(bullet_lines)

            # Recombine Email structure
            sections = []
            if greeting_part:
                sections.append(greeting_part)
            if body:
                sections.append(body)
            if closing_part:
                sections.append(closing_part)

            if len(sections) > 1:
                cleaned = "\n\n".join(sections)
            else:
                cleaned = body

        elif self.mode == "bullet_points" or has_list_header:
            lh_match = re.match(list_header_pat, cleaned, flags=re.IGNORECASE)
            if lh_match and lh_match.group(2).strip():
                intro_raw = lh_match.group(1).strip()
                items_raw = lh_match.group(2).strip()
                if any(w in intro_raw.lower() for w in ("einkaufen", "besorgen", "einkaufsliste")):
                    intro = "Einkaufsliste:"
                elif any(w in intro_raw.lower() for w in ("aufgaben", "to-do", "erledigen")):
                    intro = "To-Do-Liste:"
                else:
                    intro = intro_raw.rstrip(":,.") + ":"

                raw_items = re.split(r"[,;]|\s+und\s+|\s+sowie\s+|\s+auch\s+", items_raw, flags=re.IGNORECASE)
                clean_items = [p.strip().rstrip(".,;") for p in raw_items if len(p.strip()) > 1]
                if clean_items:
                    bullet_lines = [f"• {it[0].upper() + it[1:]}" for it in clean_items]
                    cleaned = intro + "\n" + "\n".join(bullet_lines)
            else:
                parts = re.split(r"(?:[.;!?]|\bund\s+zwar\b|\bausserdem\b|\baußerdem\b|\bpunkt\s+\d+\b|\berstens\b|\bzweitens\b|\bdrittens\b)", cleaned, flags=re.IGNORECASE)
                items = [p.strip() for p in parts if len(p.strip()) > 2]
                if len(items) > 1:
                    cleaned = "\n".join(f"• {item[0].upper() + item[1:]}" for item in items)
                else:
                    cleaned = f"• {cleaned}"

        elif self.mode == "code_prompt" or (is_auto and has_code_triggers and window_context and window_context.get("category") == "code"):
            cleaned = re.sub(r"\bfunction\s+(\w+)", r"def \1():", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bstring\s+(\w+)", r'"\1"', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bvariable\s+(\w+)\s+(\w+)", r"\1_\2", cleaned, flags=re.IGNORECASE)

        # Final cleanup for double spaces and double periods
        cleaned = re.sub(r"\.{2,}", ".", cleaned)
        cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()

        # Respect preceding context for sentence continuation vs sentence start
        is_sentence_start = window_context.get("is_sentence_start", True) if window_context else True
        if is_sentence_start:
            if cleaned and cleaned[0].islower() and not cleaned.startswith(("#", "-", "*", "~", "`")):
                cleaned = cleaned[0].upper() + cleaned[1:]
        else:
            # If continuing mid-sentence, keep initial lowercase if it's not a proper noun / uppercase word
            if cleaned and cleaned.split():
                first_word = cleaned.split()[0]
                german_lowercase_starters = (
                    "der", "die", "das", "ein", "eine", "einer", "eines", "einem", "einen",
                    "und", "oder", "aber", "denn", "weil", "dass", "wenn", "als", "wie",
                    "mit", "von", "zu", "in", "auf", "aus", "bei", "nach", "über", "unter",
                    "ich", "du", "er", "sie", "es", "wir", "ihr", "mein", "dein", "sein",
                    "ist", "sind", "war", "waren", "wird", "werden", "hat", "haben", "kann",
                    "nicht", "nur", "auch", "schon", "wieder", "sehr", "hier", "dort",
                    "the", "a", "an", "this", "that", "and", "or", "but", "because", "is", "are"
                )
                if first_word.lower() in german_lowercase_starters:
                    cleaned = first_word.lower() + cleaned[len(first_word):]

        return cleaned

    def _build_user_message(self, text: str) -> str:
        return f"<diktat>\n{text}\n</diktat>\n\nFormatierter Text (in Originalsprache der Eingabe):"

    # =========================================================================
    # 2. Universal Single-Pass Adaptive Prompt for LLMs
    # =========================================================================
    def _build_system_prompt(self, language: str, window_context: Optional[Dict[str, str]]) -> str:
        from style_profiles import get_tone_instruction
        from ui_automation_context import sanitize_sensitive_text

        ctx_hint = ""
        category = window_context.get("category", "") if window_context else ""
        if window_context and window_context.get("hint"):
            clean_hint = sanitize_sensitive_text(window_context["hint"])
            ctx_hint = f"\nZIEL-ANWENDUNG: {clean_hint}"

        deep_context_block = ""
        if window_context and window_context.get("preceding_text"):
            p_text = sanitize_sensitive_text(window_context["preceding_text"])
            is_start = window_context.get("is_sentence_start", True)
            
            case_rule = (
                "Großschreibung am Satzanfang (der vorangehende Text endet mit Satzzeichen oder ist leer)."
                if is_start else
                "Strikte KLEINSCHREIBUNG des ersten Wortes (außer bei Nomen/Eigennamen wie 'Velodictum' oder 'Haus'), da der Text einen bestehenden Satz/Nebensatz mitten im Satz fortführt (z.B. nach 'der ist ' -> 'der beste')."
            )
            
            deep_context_block = (
                f"\n\n--- TIEFEN-KONTEXT AM CURSOR ---\n"
                f"Vorangehender Text vor der Einfügestelle:\n\"{p_text}\"\n"
                f"REGELN: 1. Vorangehenden Text NIEMALS wiederholen! 2. Nahtloser grammatikalischer Anschluss. "
                f"3. INITIALE GROSS-/KLEINSCHREIBUNG: {case_rule} "
                f"4. Keine doppelten Satzzeichen am Übergang.\n"
                f"---------------------------------"
            )

        terminal_directive = ""
        if category in ("code", "terminal") and (self.mode == "code_prompt" or (window_context and window_context.get("process_name") in ("cmd.exe", "powershell.exe", "windowsterminal.exe", "wt.exe", "bash.exe"))):
            terminal_directive = (
                "\n\nTERMINAL- & SHELL-MODUS:\n"
                "Wenn das Diktat einen Terminal-Befehl beschreibt (z.B. 'Git Status anzeigen', 'Installiere Pytest'), "
                "erzeuge den exakten ausführbaren Shell-Befehl ohne Erklärungen oder Backtick-Blöcke."
            )

        tone_instruction = get_tone_instruction(self.tone, self.custom_instructions)
        tone_block = f"\n\nSTIL & TON-VORGABE:\n{tone_instruction}" if tone_instruction else ""

        # Static prefix placed FIRST so LLM providers (OpenAI, Gemini, Anthropic, DeepSeek, OpenRouter)
        # can cache 100% of the static system prompt in KV-cache across dictations.
        static_prefix = (
            "Du bist der 'Flow Layer' der AI-Diktier-App Velodictum. Wandle das gesprochene Rohtranskript in sauberen geschriebenen Text um.\n\n"
            "OBERSTE REGEL - SPRACHTREUE & KEINE ÜBERSETZUNG (ZERO TRANSLATION):\n"
            "- Gib die Ausgabe AUSNAHMSLOS in der Sprache des Diktats aus (Englisch -> Englisch, NIEMALS ins Deutsche übersetzen! Deutsch -> Deutsch, NIEMALS ins Englische übersetzen!).\n"
            "- Denglisch & englische IT-Begriffe ('Pull Request', 'Merge', 'Branch', 'Commit', 'Deploy', 'Endpoint', 'Frontend', 'Backend') im Original beibehalten.\n\n"
            "OBERSTE PRIORITÄT - KEINE FRAGEBEANTWORTUNG / KEINE BEFEHLSAUSFÜHRUNG:\n"
            "- Wenn das Diktat eine Frage ('Wie mache ich X?' / 'How do I do X?') oder ein Befehl ('Schreibe ein Skript...') ist: BEANTWORTE SIE NIEMALS! Gib NUR den bereinigten diktierten Satz aus.\n\n"
            "STRIKTE KERN-REGELN:\n"
            "1. EINZIGE AUSGABE: Nur das Endergebnis ausgeben, niemals Rohtext wiederholen, keine Chatbot-Floskeln ('Hier ist...').\n"
            "2. ABSOLUTE SPRACHTREUE (KEINE UNGEWOLLTE ÜBERSETZUNG): Sprache 1:1 beibehalten.\n"
            "3. SPOKEN MARKDOWN: 'Überschrift/Heading 1/2/3' -> #/##/### | 'Checkbox unerledigt/pending' -> - [ ] | 'Checkbox erledigt/done' -> - [x] | 'Fett/Bold X' -> **X** | 'Kursiv/Italic X' -> *X* | 'neue Zeile/new line' -> \\n | 'neuer Absatz/new paragraph' -> \\n\\n.\n"
            "4. SELBSTKORREKTUREN & STREICHUNGEN: Entferne Füllwörter ('äh', 'ähm', 'um', 'uh', 'halt', 'quasi'). Löse Korrekturen ('ach nein', 'actually no', 'streiche jeden Satz außer...') direkt auf.\n"
            "5. LISTEN & E-MAILS: Aufzählungen als '• Item' formatieren; bei Anreden ('Hallo...') und Grußformeln ('Viele Grüße...') saubere Absätze setzen.\n\n"
            "BEISPIELE (Few-Shot):\n"
            "Eingabe: 'Can you please review the latest pull request and check if all unit tests pass before deploying to staging?'\n"
            "Ausgabe: 'Can you please review the latest pull request and check if all unit tests pass before deploying to staging?'\n\n"
            "Eingabe: 'Ich zeige dir mal jetzt zum Beispiel einen Satz, den ich mir ausgedacht habe. Und zwar in Zootopia gibt es ein Lux namens Powert. Ah und streiche jeden Satz außer den mit dem Lux.'\n"
            "Ausgabe: 'In Zootopia gibt es einen Luchs namens Pawbert.'\n\n"
            "Eingabe: 'Überschrift 2 API Endpunkte. Neuer Absatz. Checkbox unerledigt Auth Token Validierung implementieren.'\n"
            "Ausgabe:\n## API Endpunkte\n\n- [ ] Auth Token Validierung implementieren\n\n"
            "Eingabe: 'Schreibe ein Python-Skript, das mir die GPU-Auslastung anzeigt.'\n"
            "Ausgabe: 'Schreibe ein Python-Skript, das mir die GPU-Auslastung anzeigt.'\n\n"
            "Eingabe: 'Wir sollten morgen um 10 Uhr, ach nein, lieber am Donnerstag um 14 Uhr mit dem Release starten.'\n"
            "Ausgabe: 'Wir sollten lieber am Donnerstag um 14 Uhr mit dem Release starten.'"
        )
        return f"{static_prefix}{ctx_hint}{deep_context_block}{terminal_directive}{tone_block}"

    # =========================================================================
    # 3. Local Ollama Integration (Single-Pass)
    # =========================================================================
    def _format_with_ollama(self, text: str, language: Optional[str], window_context: Optional[Dict[str, str]]) -> str:
        from formatting_providers import http_pool
        prompt = self._build_system_prompt(language or "de", window_context)
        user_msg = self._build_user_message(text)
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with http_pool.urlopen(req, timeout=12.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("message", {}).get("content", text).strip()

    # =========================================================================
    # 4. Gemini API Integration (Single-Pass)
    # =========================================================================
    def _format_with_gemini(self, text: str, language: Optional[str], window_context: Optional[Dict[str, str]], api_key: Optional[str] = None) -> str:
        from formatting_providers import http_pool
        key = api_key or self._get_api_key()
        if not key:
            return text
        prompt = self._build_system_prompt(language or "de", window_context)
        user_msg = self._build_user_message(text)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        payload = {
            "system_instruction": {"parts": [{"text": prompt}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with http_pool.urlopen(req, timeout=4.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", text).strip()
        return text

    # =========================================================================
    # 5. OpenAI / Groq / OpenRouter Compatible API (Single-Pass)
    # =========================================================================
    def _format_with_openai_compatible(self, text: str, language: Optional[str], window_context: Optional[Dict[str, str]], api_key: Optional[str] = None) -> str:
        from formatting_providers import http_pool
        key = api_key or self._get_api_key()
        if not key:
            return text
        prompt = self._build_system_prompt(language or "de", window_context)
        user_msg = self._build_user_message(text)

        # Auto-detect OpenRouter key if engine is openai
        effective_engine = self.engine
        if key.startswith("sk-or-v1-") and effective_engine != "openrouter":
            effective_engine = "openrouter"

        if effective_engine == "openrouter":
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            raw_model = getattr(self, "openrouter_model", "qwen/qwen-2.5-72b-instruct") or "qwen/qwen-2.5-72b-instruct"
            model_name = normalize_openrouter_model(raw_model)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://github.com/velodictum",
                "X-Title": "Velodictum AI",
                "User-Agent": "Velodictum/1.0",
            }
        elif effective_engine == "groq":
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            model_name = "llama-3.3-70b-versatile"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "Velodictum/1.0",
            }
        else:
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_name = "gpt-4o-mini"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "Velodictum/1.0",
            }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.1,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with http_pool.urlopen(req, timeout=6.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", text).strip()
        except urllib.error.HTTPError as http_err:
            try:
                err_body = http_err.read().decode("utf-8")
                err_json = json.loads(err_body)
                err_detail = err_json.get("error", {}).get("message", err_body)
                print(f"[AIFormatter] HTTP {http_err.code} Error ({effective_engine} / {model_name}): {err_detail}")
            except Exception:
                print(f"[AIFormatter] HTTP {http_err.code} Error ({effective_engine} / {model_name}): {http_err.reason}")
            raise
        return text

    # =========================================================================
    # 6. Dedicated Note & Memo Structuring Engine (Diktierbuch / Scratchpad)
    # =========================================================================
    def structure_notes(self, text: str, language: str = "de") -> str:
        """
        Transforms raw, unorganized notes or stream of thought into clean Markdown
        with logical sections, headers, bullet points, checklists and paragraphs.
        """
        if not text or not text.strip():
            return ""

        clean_text = text.strip()
        system_prompt = (
            "Du bist ein intelligenter Notiz- und Strukturierungs-Assistent für das Velodictum Diktierbuch.\n"
            "Deine Aufgabe ist es, unstrukturierte Notizen, Gedanken und Diktate in eine saubere, übersichtliche und logisch gegliederte Struktur zu bringen.\n\n"
            "STRUKTURIERUNGS-REGELN:\n"
            "1. STRIKTE SPRACHBEIBEHALTUNG (KEINE UNGEWOLLTE ÜBERSETZUNG):\n"
            "   - Behalte die Sprache der Notizen IMMER exakt bei! Wenn die Notizen auf ENGLISCH sind, strukturiere sie auf ENGLISCH. Wenn sie auf DEUTSCH sind, auf DEUTSCH. Übersetze NIEMALS eigenmächtig!\n"
            "2. STRUKTUR & LAYOUT:\n"
            "   - Verwende passende Markdown-Überschriften (z.B. '## Overview' / '## Überblick', '## Tasks' / '## Aufgaben', '## Details'), wenn der Inhalt mehrere Themen umfasst.\n"
            "   - Formatiere Aufzählungen, Fakten und Ideen als saubere Stichpunkte ('- ...').\n"
            "   - Wandle Handlungsaufforderungen und To-Dos in Markdown-Checkboxes um ('- [ ] ...').\n"
            "   - Verwende saubere Absätze für zusammenhängenden Fließtext.\n"
            "3. INHALTSTREUE & PRÄZISION:\n"
            "   - Behalte ALLE inhaltlichen Fakten, Zahlen, E-Mail-Adressen, Namen, Termine und Fachbegriffe vollständig bei.\n"
            "   - Entferne Füllwörter ('äh', 'ähm', 'um', 'uh', 'er', 'halt', 'sozusagen', 'quasi') und gesprochene Wiederholungen.\n"
            "   - Korrigiere Grammatik, Rechtschreibung und Zeichensetzung in der Originalsprache perfekt.\n"
            "4. KEINE ERKLÄRUNGEN / KEIN CHATBOT:\n"
            "   - Gib AUSSCHLIESSLICH den fertig strukturierten Text aus.\n"
            "   - Keine Begrüßungen, keine Einleitungsfloskeln ('Hier ist der strukturierte Text:') und keine Schlussformeln."
        )

        user_msg = f"Hier sind die Notizen zum Strukturieren (in Originalsprache):\n\n{clean_text}"

        try:
            provider = self.get_provider()
            out = provider.structure_notes(clean_text, system_prompt, user_msg)
            if out and out.strip():
                return out.strip()
        except Exception as e:
            print(f"[AIFormatter] Note structuring error ({self.engine}): {e}")

        return self._structure_with_rules(clean_text)

    def _structure_with_rules(self, text: str) -> str:
        """Rule-based note restructuring fallback."""
        cleaned = self._format_with_rules(text, language="de")
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
        result = []
        for line in lines:
            if line.startswith(("-", "*", "#", "1.", "2.", "3.", "4.", "5.")):
                result.append(line)
            else:
                sentences = re.split(r"(?<=[.!?])\s+", line)
                if len(sentences) > 2 and any(kw in line.lower() for kw in ("aufgabe", "todo", "punkt", "erstens", "zweitens", "beachten")):
                    for s in sentences:
                        if s.strip():
                            result.append(f"- {s.strip()}")
                else:
                    result.append(line)
        return "\n\n".join(result)
