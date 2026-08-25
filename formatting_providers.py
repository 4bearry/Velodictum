"""
Velodictum - Modular Provider-Agnostic Formatting Architecture
Provides a unified interface for Local Rules, Ollama, Universal API (OpenAI-compatible),
OpenAI, Google Gemini, and Groq.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import json
import os
import re
import time
import urllib.request
import urllib.error


from i18n import tr


def detect_provider(endpoint: str, api_key: Optional[str] = None) -> str:
    """
    Detects known provider platforms based on endpoint URL or API key prefix
    as secondary metadata. Returns 'Custom Endpoint' / 'Benutzerdefinierter Endpunkt' by default.
    """
    ep_low = (endpoint or "").lower().strip()
    key = (api_key or "").strip()

    if "openrouter.ai" in ep_low or key.startswith("sk-or-v1-"):
        return "OpenRouter"
    if "together.xyz" in ep_low or "together.ai" in ep_low:
        return "Together AI"
    if "deepseek.com" in ep_low:
        return "DeepSeek"
    if "fireworks.ai" in ep_low:
        return "Fireworks AI"
    if "groq.com" in ep_low or key.startswith("gsk_"):
        return "Groq"
    if "api.openai.com" in ep_low:
        return "OpenAI"
    if "googleapis.com" in ep_low:
        return "Google Gemini"
    if "localhost" in ep_low or "127.0.0.1" in ep_low:
        if "11434" in ep_low:
            return tr("prov_det_ollama")
        if "8000" in ep_low:
            return tr("prov_det_vllm")
        return tr("prov_det_local_server")
    if ep_low:
        return tr("prov_det_custom")
    return tr("prov_det_unconfigured")


def categorize_models(raw_models: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Intelligently categorizes available models into standard provider-agnostic categories:
    - recommended: Best allrounders for structuring and formatting
    - value: High quality / cost ratio
    - fast: Lightweight, fast and low latency
    - quality: Top parameter / flagship reasoning models
    - other: All other models
    """
    categories: Dict[str, List[Dict[str, Any]]] = {
        "recommended": [],
        "value": [],
        "fast": [],
        "quality": [],
        "other": [],
    }

    seen_ids = set()

    for item in raw_models:
        m_id = item.get("id", "")
        if not m_id or m_id in seen_ids:
            continue
        seen_ids.add(m_id)

        name = item.get("name", m_id)
        low_id = m_id.lower()
        low_name = name.lower()

        # Classification heuristics based on architecture & size
        is_flagship_allrounder = any(k in low_id for k in ("qwen/qwen-2.5-72b", "qwen2.5:72b", "llama-3.3-70b", "llama3.3:70b", "gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o-mini"))
        is_fast_lightweight = any(k in low_id for k in ("7b", "8b", "haiku", "flash-lite", "mini", "small", "turbo", "instant"))
        is_top_quality = any(k in low_id for k in ("deepseek-v3", "deepseek-chat", "claude-3.5-sonnet", "gpt-4o", "qwen-2.5-72b", "llama-3.3-70b"))
        is_value = any(k in low_id for k in ("flash", "haiku", "mini", "7b", "8b", "14b"))

        if is_flagship_allrounder and len(categories["recommended"]) < 3:
            categories["recommended"].append(item)
        elif is_fast_lightweight and len(categories["fast"]) < 4:
            categories["fast"].append(item)
        elif is_top_quality and len(categories["quality"]) < 4:
            categories["quality"].append(item)
        elif is_value and len(categories["value"]) < 4:
            categories["value"].append(item)
        else:
            categories["other"].append(item)

    # Fallback if no recommended matched
    if not categories["recommended"] and raw_models:
        categories["recommended"].append(raw_models[0])

    return categories


class BaseFormattingProvider(ABC):
    """Abstract interface for all AI and Rule-based text formatting providers."""

    @abstractmethod
    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        pass

    @abstractmethod
    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        pass

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        """Transforms text according to instruction using LLM/AI."""
        out = self.format_text(text, system_prompt, user_message)
        if out and out.strip() != text.strip():
            return out.strip()
        return ""

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Returns {'success': bool, 'message': str, 'models_count': int, 'error': Optional[str]}"""
        pass


class LocalRulesProvider(BaseFormattingProvider):
    """Zero-cloud, 0ms latency rule-based text formatter."""

    def __init__(self, rule_engine_callback=None):
        self.rule_engine_callback = rule_engine_callback

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        if self.rule_engine_callback:
            return self.rule_engine_callback(text)
        return text

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        result = []
        for line in lines:
            if line.startswith(("-", "*", "#", "1.", "2.", "3.", "4.", "5.")):
                result.append(line)
            else:
                sentences = re.split(r"(?<=[.!?])\s+", line)
                if len(sentences) > 2 and any(kw in line.lower() for kw in ("aufgabe", "todo", "punkt", "erstens", "zweitens")):
                    for s in sentences:
                        if s.strip():
                            result.append(f"- {s.strip()}")
                else:
                    result.append(line)
        return "\n\n".join(result)

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        inst_low = instruction.lower().strip()
        
        # 1. Casing & Formatting
        if any(kw in inst_low for kw in ("groß", "uppercase", "versalien", "caps")):
            return text.upper()
        if any(kw in inst_low for kw in ("klein", "lowercase")):
            return text.lower()
        if any(kw in inst_low for kw in ("titel", "title", "überschrift")):
            return text.title()
        if any(kw in inst_low for kw in ("stichpunkte", "punkte", "bullet", "liste", "aufzählung")):
            lines = [l.strip() for l in re.split(r"[\n\r]+|(?<=[.!?])\s+", text) if l.strip()]
            return "\n".join(f"- {l.rstrip('.')}" if not l.startswith("- ") else l for l in lines)
        if any(kw in inst_low for kw in ("nummeriert", "nummern", "numbered", "ziffern")):
            lines = [l.strip() for l in re.split(r"[\n\r]+|(?<=[.!?])\s+", text) if l.strip()]
            return "\n".join(f"{i+1}. {l.rstrip('.')}" for i, l in enumerate(lines))
        if any(kw in inst_low for kw in ("anführungszeichen", "zitat", "quote", "zitieren")):
            return f'"{text.strip()}"'
        if any(kw in inst_low for kw in ("fett", "bold")):
            return f"**{text.strip()}**"
        if any(kw in inst_low for kw in ("kursiv", "italic")):
            return f"*{text.strip()}*"
        if any(kw in inst_low for kw in ("code", "inline code")):
            return f"`{text.strip()}`"
        if any(kw in inst_low for kw in ("codeblock", "code-block", "block")):
            return f"```\n{text.strip()}\n```"

        # 2. Tone: Polite & Formal (Sie-Form)
        if any(kw in inst_low for kw in ("höflich", "formell", "sie-form", "freundlicher", "respektvoll", "geschäftlich")):
            res = text.strip()
            replacements = [
                (r"\bdu\b", "Sie"), (r"\bdir\b", "Ihnen"), (r"\bdich\b", "Sie"),
                (r"\bdein\b", "Ihr"), (r"\bdeine\b", "Ihre"), (r"\bdeinem\b", "Ihrem"),
                (r"\bdeinen\b", "Ihren"), (r"\bdeiner\b", "Ihrer"), (r"\bdeines\b", "Ihres"),
                (r"\bkannst du\b", "könnten Sie bitte"), (r"\bkannst Du\b", "könnten Sie bitte"),
                (r"\bmach mal\b", "könnten Sie bitte machen"), (r"\bschick mir\b", "senden Sie mir bitte"),
                (r"\bgib mir\b", "geben Sie mir bitte"), (r"\bmelde dich\b", "melden Sie sich bitte"),
                (r"\bhallo\b", "Guten Tag,"), (r"\bhi\b", "Guten Tag,"), (r"\bhey\b", "Sehr geehrte Damen und Herren,")
            ]
            for pat, rep in replacements:
                res = re.sub(pat, rep, res, flags=re.IGNORECASE)
            return res

        # 3. Tone: Casual & Informal (Du-Form)
        if any(kw in inst_low for kw in ("du-form", "informell", "duzen", "locker", "kumpelhaft", "freundschaftlich")):
            res = text.strip()
            replacements = [
                (r"\bSie\b", "du"), (r"\bIhnen\b", "dir"), (r"\bIhr\b", "dein"),
                (r"\bIhre\b", "deine"), (r"\bIhrem\b", "deinem"), (r"\bIhren\b", "deinen"),
                (r"\bIhrer\b", "deiner"), (r"\bSehr geehrte Damen und Herren\b", "Hi zusammen,"),
                (r"\bSehr geehrter Herr\b", "Hallo"), (r"\bSehr geehrte Frau\b", "Hallo"),
                (r"\bMit freundlichen Grüßen\b", "Viele Grüße"), (r"\bGuten Tag\b", "Hi")
            ]
            for pat, rep in replacements:
                res = re.sub(pat, rep, res, flags=re.IGNORECASE)
            return res

        # 4. Conciseness (Kürzen & Verdichten)
        if any(kw in inst_low for kw in ("kürz", "kurz", "prägnant", "zusammenfassen", "essenz", "straffen")):
            fillers = [
                r"\beigentlich\b\s*", r"\bgewissermaßen\b\s*", r"\bsozusagen\b\s*",
                r"\birgendwie\b\s*", r"\bhalt\b\s*", r"\beinfach mal\b\s*", r"\bquasi\b\s*",
                r"\bim grunde genommen\b\s*", r"\bwie gesagt\b\s*"
            ]
            res = text.strip()
            for f in fillers:
                res = re.sub(f, "", res, flags=re.IGNORECASE)
            res = re.sub(r" +", " ", res).strip()
            return res

        return ""

    def test_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "message": "Lokale Regeln einsatzbereit (100% Offline / 0ms Latenz)",
            "models_count": 0,
            "error": None,
        }


class OllamaProvider(BaseFormattingProvider):
    """Local Ollama HTTP Daemon Provider."""

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:7b"):
        from config import validate_endpoint_url
        clean_url = (ollama_url or "http://127.0.0.1:11434").rstrip("/").replace("localhost", "127.0.0.1")
        validate_endpoint_url(clean_url, allow_localhost=True)
        self.ollama_url = clean_url
        self.model = model

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
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
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("message", {}).get("content", text).strip()

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.9},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=18.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("message", {}).get("content", text).strip()

    def fetch_models(self) -> List[Dict[str, Any]]:
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "Velodictum/1.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    models.append({"id": name, "name": name, "size_gb": m.get("size", 0) / (1024**3)})
                return models
        except Exception:
            return []

    def test_connection(self) -> Dict[str, Any]:
        try:
            models = self.fetch_models()
            if models:
                return {
                    "success": True,
                    "message": f"Ollama verbunden ({len(models)} lokale Modelle verfügbar)",
                    "models_count": len(models),
                    "error": None,
                }
            return {
                "success": False,
                "message": f"Ollama unter {self.ollama_url} erreichbar, aber keine Modelle gefunden.",
                "models_count": 0,
                "error": "Keine Modelle geladen",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Verbindung zu Ollama unter {self.ollama_url} fehlgeschlagen.",
                "models_count": 0,
                "error": str(e),
            }


def get_model_tiers() -> Dict[str, Dict[str, str]]:
    return {
        "speed": {
            "key": "speed",
            "title": tr("prio_speed_title"),
            "badge": tr("prio_speed_badge"),
            "model": "google/gemini-2.5-flash",
            "sub": "google/gemini-2.5-flash — Fast & Budget",
            "cost_input": "$0.075 / 1M Tokens (~$0.000008 / dictation)",
            "cost_output": "$0.300 / 1M Tokens",
            "typical_latency": "< 200 ms",
            "context": "1.000.000 Tokens (1M)",
            "recommended_for": tr("prio_speed_desc"),
        },
        "balanced": {
            "key": "balanced",
            "title": tr("prio_balanced_title"),
            "badge": tr("prio_balanced_badge"),
            "model": "deepseek/deepseek-chat",
            "sub": "deepseek/deepseek-chat — Balanced",
            "cost_input": "$0.140 / 1M Tokens (~$0.000014 / dictation)",
            "cost_output": "$0.280 / 1M Tokens",
            "typical_latency": "~400 - 600 ms",
            "context": "64.000 Tokens (64k)",
            "recommended_for": tr("prio_balanced_desc"),
        },
        "quality": {
            "key": "quality",
            "title": tr("prio_quality_title"),
            "badge": tr("prio_quality_badge"),
            "model": "qwen/qwen-2.5-72b-instruct",
            "sub": "qwen/qwen-2.5-72b-instruct — Maximum Depth",
            "cost_input": "$0.400 / 1M Tokens (~$0.000040 / dictation)",
            "cost_output": "$0.800 / 1M Tokens",
            "typical_latency": "~2 - 5 s",
            "context": "32.000 Tokens (32k)",
            "recommended_for": tr("prio_quality_desc"),
        },
    }

MODEL_TIERS = get_model_tiers()


def get_model_details(model_id: str) -> Dict[str, str]:
    m_low = (model_id or "").lower().strip()
    tiers = get_model_tiers()
    for tier_info in tiers.values():
        if tier_info["model"].lower() == m_low:
            return tier_info

    # Dynamic heuristics for other models
    if any(k in m_low for k in ("flash", "mini", "instant", "8b", "7b", "small")):
        return {
            "key": "custom",
            "title": tr("model_custom_compact_title"),
            "badge": tr("model_custom_compact_badge"),
            "model": model_id,
            "sub": model_id,
            "cost_input": tr("model_custom_compact_cost_in"),
            "cost_output": tr("model_custom_compact_cost_out"),
            "typical_latency": tr("model_custom_compact_lat"),
            "context": tr("model_custom_var_ctx"),
            "recommended_for": tr("model_custom_compact_rec"),
        }
    elif any(k in m_low for k in ("70b", "72b", "sonnet", "gpt-4o", "large", "plus")):
        return {
            "key": "custom",
            "title": tr("model_custom_large_title"),
            "badge": tr("model_custom_large_badge"),
            "model": model_id,
            "sub": model_id,
            "cost_input": tr("model_custom_large_cost_in"),
            "cost_output": tr("model_custom_large_cost_out"),
            "typical_latency": tr("model_custom_large_lat"),
            "context": tr("model_custom_var_ctx"),
            "recommended_for": tr("model_custom_large_rec"),
        }
    else:
        return {
            "key": "custom",
            "title": tr("model_custom_title"),
            "badge": tr("model_custom_badge"),
            "model": model_id,
            "sub": model_id,
            "cost_input": tr("model_custom_cost_dep"),
            "cost_output": tr("model_custom_cost_dep"),
            "typical_latency": tr("model_custom_lat_dep"),
            "context": tr("model_custom_var_ctx"),
            "recommended_for": tr("model_custom_rec_ind"),
        }


def normalize_endpoint(endpoint: str) -> str:
    ep = (endpoint or "").strip().rstrip("/")
    if not ep:
        return "https://openrouter.ai/api/v1"
    if ep in ("https://openrouter.ai", "http://openrouter.ai"):
        return "https://openrouter.ai/api/v1"
    if ep in ("https://api.openai.com", "http://api.openai.com"):
        return "https://api.openai.com/v1"
    if ep in ("https://api.together.xyz", "http://api.together.xyz"):
        return "https://api.together.xyz/v1"
    if ep in ("https://api.deepseek.com", "http://api.deepseek.com"):
        return "https://api.deepseek.com/v1"
    if ep in ("https://api.groq.com/openai", "http://api.groq.com/openai"):
        return "https://api.groq.com/openai/v1"

    from config import validate_endpoint_url
    validate_endpoint_url(ep, allow_localhost=True)
    return ep


class UniversalApiProvider(BaseFormattingProvider):
    """
    Generic, fully provider-agnostic OpenAI-compatible API client.
    Works with OpenRouter, Together AI, DeepSeek, Fireworks, vLLM, LiteLLM,
    self-hosted endpoints, or any standard OpenAI /chat/completions endpoint.
    """

    def __init__(
        self,
        endpoint: str = "https://openrouter.ai/api/v1",
        api_key: Optional[str] = None,
        model: str = "qwen/qwen-2.5-72b-instruct",
        custom_headers: Optional[Dict[str, str]] = None,
        routing_strategy: str = "latency",
        zero_data_retention: bool = True,
        allow_fallbacks: bool = True,
    ):
        self.endpoint = normalize_endpoint(endpoint)
        self._static_api_key = api_key
        self.model = model or "qwen/qwen-2.5-72b-instruct"
        self.custom_headers = custom_headers or {}
        self.routing_strategy = routing_strategy or "latency"
        self.zero_data_retention = zero_data_retention
        self.allow_fallbacks = allow_fallbacks

    def _resolve_api_key(self) -> Optional[str]:
        """Resolves API key Just-In-Time from Credential Vault or explicit override."""
        if self._static_api_key and self._static_api_key.strip():
            return self._static_api_key.strip()
        try:
            import security_credentials as sec
            from config import config
            detected = detect_provider(self.endpoint, None)
            if detected == "OpenAI":
                return sec.get_credential(sec.KEY_OPENAI_API) or config.formatting.get_api_key("openai")
            elif detected == "Groq":
                return sec.get_credential(sec.KEY_GROQ_API) or config.formatting.get_api_key("groq")
            elif detected == "Google Gemini":
                return sec.get_credential(sec.KEY_GEMINI_API) or config.formatting.get_api_key("gemini")
            else:
                return sec.get_credential(sec.KEY_UNIVERSAL_API) or config.formatting.get_api_key("universal")
        except Exception:
            return None

    @property
    def api_key(self) -> Optional[str]:
        return self._resolve_api_key()

    @api_key.setter
    def api_key(self, value: Optional[str]):
        self._static_api_key = value

    def _get_chat_url(self) -> str:
        if self.endpoint.endswith("/chat/completions"):
            return self.endpoint
        return f"{self.endpoint}/chat/completions"

    def _get_models_url(self) -> str:
        if self.endpoint.endswith("/chat/completions"):
            base = self.endpoint[: -len("/chat/completions")]
            return f"{base}/models"
        return f"{self.endpoint}/models"

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Velodictum/1.0",
        }
        key = self._resolve_api_key()
        if key and key.strip():
            headers["Authorization"] = f"Bearer {key.strip()}"
        del key

        detected = detect_provider(self.endpoint, None)
        if detected == "OpenRouter":
            headers["HTTP-Referer"] = "https://github.com/velodictum"
            headers["X-Title"] = "Velodictum"

        headers.update(self.custom_headers)
        return headers

    def _build_payload(self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        detected = detect_provider(self.endpoint, self.api_key)
        if detected == "OpenRouter" or "openrouter" in self.endpoint:
            p_obj: Dict[str, Any] = {}
            if self.routing_strategy in ("latency", "price", "throughput"):
                p_obj["sort"] = self.routing_strategy
            if self.zero_data_retention:
                p_obj["data_collection"] = "deny"
                p_obj["zdr"] = True
            if self.allow_fallbacks is not None:
                p_obj["allow_fallbacks"] = bool(self.allow_fallbacks)
            if p_obj:
                payload["provider"] = p_obj

        return payload

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        url = self._get_chat_url()
        headers = self._build_headers()
        payload = self._build_payload(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", text).strip()
        except Exception as e:
            print(f"[UniversalApiProvider] format_text error from {url}: {e}")
        return text

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        url = self._get_chat_url()
        headers = self._build_headers()
        payload = self._build_payload(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", text).strip()
        except Exception as e:
            print(f"[UniversalApiProvider] structure_notes error from {url}: {e}")
        return text

    def fetch_models(self) -> List[Dict[str, Any]]:
        models, _ = self.fetch_models_detailed()
        return models

    def fetch_models_detailed(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Dynamically fetches model list from the configured endpoint (/models).
        Returns (models_list, error_message).
        """
        url = self._get_models_url()
        headers = self._build_headers()
        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                raw_list = res_json.get("data", []) if isinstance(res_json, dict) else []
                if not raw_list and isinstance(res_json, list):
                    raw_list = res_json

                models = []
                for item in raw_list:
                    if isinstance(item, str):
                        models.append({"id": item, "name": item})
                    elif isinstance(item, dict):
                        m_id = item.get("id", "")
                        if m_id:
                            name = item.get("name", m_id)
                            context_length = item.get("context_length", item.get("context_window"))
                            pricing = item.get("pricing", {})
                            models.append({
                                "id": m_id,
                                "name": name,
                                "context_length": context_length,
                                "pricing": pricing,
                            })
                return models, None
        except urllib.error.HTTPError as he:
            err_msg = f"HTTP {he.code}: {he.reason}"
            try:
                b = he.read().decode("utf-8")
                j = json.loads(b)
                if "error" in j:
                    err_msg = f"HTTP {he.code}: {j['error'].get('message', j['error'])}"
            except Exception:
                pass
            return [], err_msg
        except urllib.error.URLError as ue:
            return [], f"Verbindungsfehler: {ue.reason}"
        except Exception as e:
            return [], str(e)

    def test_connection(self) -> Dict[str, Any]:
        detected = detect_provider(self.endpoint, self.api_key)
        
        # 1. Try to fetch models
        models, err = self.fetch_models_detailed()
        if models:
            return {
                "success": True,
                "message": f"Verbindung erfolgreich ({len(models)} Modelle über {detected} geladen)",
                "models_count": len(models),
                "detected_provider": detected,
                "error": None,
            }
        
        # 2. If fetch_models failed with auth error or connection error, return detailed error
        if err:
            if "404" not in err:
                return {
                    "success": False,
                    "message": f"Verbindung fehlgeschlagen ({detected}): {err}",
                    "models_count": 0,
                    "detected_provider": detected,
                    "error": err,
                }

        # 3. Test chat completions directly
        try:
            url = self._get_chat_url()
            headers = self._build_headers()
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "Antworte mit OK"},
                ],
                "max_tokens": 10,
                "temperature": 0.1,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    return {
                        "success": True,
                        "message": f"Verbindung erfolgreich ({detected} antwortet: '{content[:30]}')",
                        "models_count": 0,
                        "detected_provider": detected,
                        "error": None,
                    }
            return {
                "success": False,
                "message": f"Endpunkt {self.endpoint} lieferte leere Antwort.",
                "models_count": 0,
                "detected_provider": detected,
                "error": "Leere Antwort",
            }
        except urllib.error.HTTPError as he:
            err_msg = f"HTTP {he.code}: {he.reason}"
            try:
                b = he.read().decode("utf-8")
                j = json.loads(b)
                if "error" in j:
                    err_msg = f"HTTP {he.code}: {j['error'].get('message', j['error'])}"
            except Exception:
                pass
            return {
                "success": False,
                "message": f"Verbindung fehlgeschlagen ({detected}): {err_msg}",
                "models_count": 0,
                "detected_provider": detected,
                "error": err_msg,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Verbindung fehlgeschlagen: {str(e)}",
                "models_count": 0,
                "detected_provider": detected,
                "error": str(e),
            }


class OpenAIProvider(BaseFormattingProvider):
    """Dedicated Official OpenAI Provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self._universal = UniversalApiProvider(
            endpoint="https://api.openai.com/v1",
            api_key=self.api_key,
            model=self.model,
        )

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.format_text(text, system_prompt, user_message)

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.structure_notes(text, system_prompt, user_message)

    def test_connection(self) -> Dict[str, Any]:
        return self._universal.test_connection()


class GeminiProvider(BaseFormattingProvider):
    """Dedicated Google Gemini Provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self._static_api_key = api_key
        self.model = model or "gemini-2.5-flash"

    def _resolve_api_key(self) -> Optional[str]:
        if self._static_api_key and self._static_api_key.strip():
            return self._static_api_key.strip()
        try:
            import security_credentials as sec
            from config import config
            return sec.get_credential(sec.KEY_GEMINI_API) or config.formatting.get_api_key("gemini")
        except Exception:
            return None

    @property
    def api_key(self) -> Optional[str]:
        return self._resolve_api_key()

    @api_key.setter
    def api_key(self, value: Optional[str]):
        self._static_api_key = value

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        key = self._resolve_api_key()
        if not key:
            return text
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
        del key
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", text).strip()
        except Exception:
            pass
        return text

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        key = self._resolve_api_key()
        if not key:
            return text
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
        del key
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2000},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", text).strip()
        except Exception:
            pass
        return text

    def test_connection(self) -> Dict[str, Any]:
        key = self._resolve_api_key()
        if not key:
            return {"success": False, "message": "Kein Google Gemini API-Key angegeben.", "models_count": 0, "error": "API-Key fehlt"}
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            del key
            req = urllib.request.Request(url, headers={"User-Agent": "Velodictum/1.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                models = res.get("models", [])
                return {
                    "success": True,
                    "message": f"Google Gemini verbunden ({len(models)} Modelle verfügbar)",
                    "models_count": len(models),
                    "error": None,
                }
        except Exception as e:
            return {"success": False, "message": f"Google Gemini Verbindung fehlgeschlagen: {e}", "models_count": 0, "error": str(e)}


class GroqProvider(BaseFormattingProvider):
    """Dedicated Groq LPU Provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model or "llama-3.3-70b-versatile"
        self._universal = UniversalApiProvider(
            endpoint="https://api.groq.com/openai/v1",
            api_key=self.api_key,
            model=self.model,
        )

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.format_text(text, system_prompt, user_message)

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.structure_notes(text, system_prompt, user_message)

    def test_connection(self) -> Dict[str, Any]:
        return self._universal.test_connection()
