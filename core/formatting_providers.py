"""
Velodictum - Modular Provider-Agnostic Formatting Architecture
Provides a unified interface for Local Rules, Ollama, Universal API (OpenAI-compatible),
OpenAI, Google Gemini, and Groq.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import http.client
import io
import json
import os
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request
import urllib.error


from i18n import tr


class _PooledHttpResponse:
    """Lightweight response wrapper compatible with urllib.request.urlopen context manager."""

    def __init__(self, body: bytes, status: int, reason: str, headers: Any):
        self._body = body
        self.status = status
        self.code = status
        self.reason = reason
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class PersistentHttpPool:
    """
    Thread-safe HTTP/1.1 Keep-Alive connection pool with background TLS pre-warming.
    Eliminates 150-350ms DNS + TCP + TLS handshake overhead on post-recording API calls.
    """

    MAX_IDLE_SEC = 50.0
    MAX_POOL_PER_HOST = 4

    def __init__(self):
        self._lock = threading.Lock()
        self._pool: Dict[Tuple[str, str, int], List[Tuple[http.client.HTTPConnection, float]]] = {}
        self._ssl_ctx = ssl.create_default_context()

    def _get_host_key(self, url: str) -> Tuple[str, str, int, str]:
        parsed = urllib.parse.urlsplit(url)
        scheme = (parsed.scheme or "https").lower()
        hostname = parsed.hostname or "localhost"
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return scheme, hostname, port, path

    def _create_connection(self, scheme: str, hostname: str, port: int, timeout: float) -> http.client.HTTPConnection:
        if scheme == "https":
            return http.client.HTTPSConnection(hostname, port, timeout=timeout, context=self._ssl_ctx)
        return http.client.HTTPConnection(hostname, port, timeout=timeout)

    def _acquire_conn(self, key: Tuple[str, str, int], timeout: float) -> Tuple[http.client.HTTPConnection, bool]:
        scheme, hostname, port = key
        now = time.monotonic()
        with self._lock:
            bucket = self._pool.get(key, [])
            while bucket:
                conn, ts = bucket.pop()
                if (now - ts) < self.MAX_IDLE_SEC and getattr(conn, "sock", None) is not None:
                    try:
                        conn.sock.settimeout(timeout)
                        return conn, True
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass
                else:
                    try:
                        conn.close()
                    except Exception:
                        pass

        conn = self._create_connection(scheme, hostname, port, timeout)
        return conn, False

    def _release_conn(self, key: Tuple[str, str, int], conn: http.client.HTTPConnection):
        if getattr(conn, "sock", None) is None:
            return
        with self._lock:
            bucket = self._pool.setdefault(key, [])
            if len(bucket) < self.MAX_POOL_PER_HOST:
                bucket.append((conn, time.monotonic()))
            else:
                try:
                    conn.close()
                except Exception:
                    pass

    def prewarm(self, url: str, timeout: float = 3.5) -> bool:
        """
        Establishes and pools a warm TCP/TLS socket to `url` in the background (e.g. when recording starts)
        so that when speech ends, 0ms is spent on TCP/TLS handshakes.
        """
        try:
            from config import validate_endpoint_url
            validate_endpoint_url(url, allow_localhost=True)
            scheme, hostname, port, _ = self._get_host_key(url)
            key = (scheme, hostname, port)
            now = time.monotonic()
            with self._lock:
                bucket = self._pool.get(key, [])
                valid = [(c, ts) for (c, ts) in bucket if (now - ts) < self.MAX_IDLE_SEC and getattr(c, "sock", None) is not None]
                self._pool[key] = valid
                if valid:
                    return True

            conn = self._create_connection(scheme, hostname, port, timeout)
            conn.connect()
            if getattr(conn, "sock", None) is None:
                conn.sock = True  # Fallback for mocked connections in unit tests
            self._release_conn(key, conn)
            return True
        except Exception:
            return False

    def urlopen(self, req: urllib.request.Request, timeout: float = 10.0) -> _PooledHttpResponse:
        # Respect unittest.mock patches on urllib.request.urlopen
        if hasattr(urllib.request.urlopen, "_mock_name") or getattr(urllib.request.urlopen, "__module__", "") != "urllib.request":
            return urllib.request.urlopen(req, timeout=timeout)

        full_url = req.full_url
        scheme, hostname, port, path = self._get_host_key(full_url)
        key = (scheme, hostname, port)
        method = req.get_method()
        body = req.data

        headers = dict(req.header_items())
        headers.setdefault("Connection", "keep-alive")

        for attempt in range(2):
            conn, reused = self._acquire_conn(key, timeout=timeout)
            try:
                conn.request(method, path, body=body, headers=headers)
                resp = conn.getresponse()
                resp_bytes = resp.read()
                status = resp.status
                reason = resp.reason
                resp_headers = resp.headers

                conn_hdr = (resp.getheader("Connection") or "").lower()
                if conn_hdr != "close" and not getattr(resp, "will_close", False):
                    self._release_conn(key, conn)
                else:
                    try:
                        conn.close()
                    except Exception:
                        pass

                if status >= 400:
                    raise urllib.error.HTTPError(
                        full_url, status, reason, resp_headers, io.BytesIO(resp_bytes)
                    )

                return _PooledHttpResponse(resp_bytes, status, reason, resp_headers)
            except urllib.error.HTTPError:
                raise
            except (http.client.HTTPException, OSError, ConnectionError, EOFError) as e:
                try:
                    conn.close()
                except Exception:
                    pass
                if reused and attempt == 0:
                    continue
                raise urllib.error.URLError(e)


http_pool = PersistentHttpPool()


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

    def prewarm_connection(self) -> bool:
        """Optionally pre-warms underlying HTTP/TLS connection while the user is speaking."""
        return True


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
        inst_low = instruction.lower().strip().rstrip(".!?")
        orig_clean = text.strip()
        if not orig_clean:
            return ""

        def _split_items(src: str) -> List[str]:
            items = [l.strip() for l in re.split(r"[\n\r]+|(?<=[.!?])\s+", src) if l.strip()]
            if len(items) == 1 and (";" in items[0] or "," in items[0]):
                sep = ";" if ";" in items[0] else ","
                sub_items = [s.strip() for s in items[0].split(sep) if s.strip()]
                if len(sub_items) >= 2:
                    items = sub_items
            return [re.sub(r"^(?:[-*•]|\d+[.)]|\[\s*[xX ]?\s*\])\s*", "", it).strip() for it in items if it.strip()]

        # 0. Explicit Search & Replace / Remove
        m_rep_de = re.search(r"ersetze\s+[\"']?(.+?)[\"']?\s+(?:durch|mit)\s+[\"']?(.+?)[\"']?$", instruction.strip().rstrip(".!?"), flags=re.IGNORECASE)
        if m_rep_de:
            old_w, new_w = m_rep_de.group(1).strip(), m_rep_de.group(2).strip()
            if old_w:
                return re.sub(re.escape(old_w), new_w, orig_clean, flags=re.IGNORECASE)

        m_rep_en = re.search(r"replace\s+[\"']?(.+?)[\"']?\s+(?:with|by)\s+[\"']?(.+?)[\"']?$", instruction.strip().rstrip(".!?"), flags=re.IGNORECASE)
        if m_rep_en:
            old_w, new_w = m_rep_en.group(1).strip(), m_rep_en.group(2).strip()
            if old_w:
                return re.sub(re.escape(old_w), new_w, orig_clean, flags=re.IGNORECASE)

        m_del = re.search(r"^(?:entferne|lösche|streiche|remove|delete)\s+(?:das\s+wort\s+|the\s+word\s+)?[\"']?(.+?)[\"']?$", instruction.strip().rstrip(".!?"), flags=re.IGNORECASE)
        if m_del:
            target_del = m_del.group(1).strip()
            if target_del and target_del.lower() not in ("das", "dies", "this", "it", "stichpunkte", "bullets"):
                cleaned_del = re.sub(r"\b" + re.escape(target_del) + r"\b\s*", "", orig_clean, flags=re.IGNORECASE)
                cleaned_del = re.sub(r" +", " ", cleaned_del).strip()
                if cleaned_del:
                    return cleaned_del

        # 1. Casing & Formatting
        if any(kw in inst_low for kw in ("groß", "uppercase", "versalien", "caps", "capital")):
            return orig_clean.upper()
        if any(kw in inst_low for kw in ("klein", "lowercase", "small letters")):
            return orig_clean.lower()
        if any(kw in inst_low for kw in ("überschrift 3", "heading 3", "h3")):
            return f"### {orig_clean.lstrip('# ').strip()}"
        if any(kw in inst_low for kw in ("überschrift 2", "heading 2", "h2")):
            return f"## {orig_clean.lstrip('# ').strip()}"
        if any(kw in inst_low for kw in ("überschrift 1", "heading 1", "h1")):
            return f"# {orig_clean.lstrip('# ').strip()}"
        if any(kw in inst_low for kw in ("titel", "title", "überschrift", "heading", "header")):
            return orig_clean.title()
        if any(kw in inst_low for kw in ("checkbox", "todo", "to-do", "aufgaben", "checkliste", "checklist", "abhaken")):
            lines = _split_items(orig_clean)
            return "\n".join(f"- [ ] {l.rstrip('.')}" for l in lines)
        if any(kw in inst_low for kw in ("ohne stichpunkte", "fließtext", "fliesstext", "absatz", "paragraph", "prose", "zusammenfügen", "ein satz")):
            lines = _split_items(orig_clean)
            joined = " ".join(l if l.endswith((".", "!", "?")) else f"{l}." for l in lines)
            return re.sub(r" +", " ", joined).strip()
        if any(kw in inst_low for kw in ("stichpunkte", "stichpunkt", "punkte", "bullet", "liste", "aufzählung", "auflisten", "list")) and not any(kw in inst_low for kw in ("nummeriert", "nummern", "numbered", "ziffern")):
            lines = _split_items(orig_clean)
            return "\n".join(f"- {l.rstrip('.')}" for l in lines)
        if any(kw in inst_low for kw in ("nummeriert", "nummerieren", "nummern", "numbered", "ziffern", "durchnummerieren")):
            lines = _split_items(orig_clean)
            return "\n".join(f"{i+1}. {l.rstrip('.')}" for i, l in enumerate(lines))
        if any(kw in inst_low for kw in ("anführungszeichen", "zitat", "quote", "zitieren")):
            return f'"{orig_clean.strip(chr(34))}"'
        if any(kw in inst_low for kw in ("klammern", "parentheses", "brackets")):
            return f"({orig_clean.strip('()')})"
        if any(kw in inst_low for kw in ("fett", "bold")):
            return f"**{orig_clean.strip('*')}**"
        if any(kw in inst_low for kw in ("kursiv", "italic")):
            return f"*{orig_clean.strip('*')}*"
        if any(kw in inst_low for kw in ("codeblock", "code-block", "block")):
            return f"```\n{orig_clean}\n```"
        if any(kw in inst_low for kw in ("code", "inline code")):
            return f"`{orig_clean.strip('`')}`"

        # 2. Email Formatting
        if any(kw in inst_low for kw in ("e-mail", "email", "als mail")):
            is_en_inst = any(w in inst_low for w in ("english", "format as", "write as", "make it an email"))
            body = self.format_text(orig_clean, system_prompt, user_message) if self.rule_engine_callback else orig_clean
            if body and body[0].islower():
                body = body[0].upper() + body[1:]
            if body and not body.endswith((".", "!", "?")):
                body += "."
            if is_en_inst:
                return f"Hi,\n\n{body}\n\nBest regards"
            return f"Guten Tag,\n\n{body}\n\nMit freundlichen Grüßen"

        # 3. Tone: Polite & Formal (Sie-Form / Business)
        if any(kw in inst_low for kw in ("höflich", "formell", "sie-form", "siezen", "freundlicher", "respektvoll", "geschäftlich", "professionell", "polite", "formal", "professional", "business", "courteous")):
            res = orig_clean
            replacements = [
                (r"\bkannst du mir\b", "könnten Sie mir bitte"),
                (r"\bkannst du\b", "könnten Sie bitte"),
                (r"\bmach mal\b", "könnten Sie bitte veranlassen"),
                (r"\bschick mir\b", "senden Sie mir bitte"),
                (r"\bgib mir\b", "geben Sie mir bitte"),
                (r"\bmelde dich\b", "melden Sie sich bitte"),
                (r"\bsag mir\b", "teilen Sie mir bitte mit"),
                (r"\bdu musst\b", "bitte beachten Sie, dass Sie"),
                (r"\bdu\b", "Sie"), (r"\bdir\b", "Ihnen"), (r"\bdich\b", "Sie"),
                (r"\bdein\b", "Ihr"), (r"\bdeine\b", "Ihre"), (r"\bdeinem\b", "Ihrem"),
                (r"\bdeinen\b", "Ihren"), (r"\bdeiner\b", "Ihrer"), (r"\bdeines\b", "Ihres"),
                (r"\bhallo\b", "Guten Tag,"), (r"\bhi\b", "Guten Tag,"), (r"\bhey\b", "Sehr geehrte Damen und Herren,"),
                (r"\bLG\b", "Mit freundlichen Grüßen"), (r"\bVG\b", "Mit freundlichen Grüßen"),
                (r"\bviele grüße\b", "Mit freundlichen Grüßen"),
                (r"\bcan you\b", "could you please"), (r"\bsend me\b", "please send me"),
                (r"\bgive me\b", "could you please provide"), (r"\btell me\b", "please let me know"),
                (r"\bi want\b", "I would like"), (r"\bi need\b", "I would appreciate"),
                (r"\bdon't\b", "do not"), (r"\bcan't\b", "cannot"), (r"\bwon't\b", "will not"), (r"\bi'm\b", "I am"),
            ]
            for pat, rep in replacements:
                res = re.sub(pat, rep, res, flags=re.IGNORECASE)
            if res and res[0].islower():
                res = res[0].upper() + res[1:]
            if res == orig_clean:
                is_en_text = bool(re.search(r"\b(the|and|please|you|this|that|with|for|have)\b", orig_clean, flags=re.IGNORECASE)) or any(w in inst_low for w in ("polite", "formal", "professional", "business"))
                body = orig_clean.rstrip(".!?")
                if is_en_text:
                    if not orig_clean.lower().startswith("please") and not orig_clean.lower().startswith("could you"):
                        res = f"Could you please note: {body}. Thank you in advance."
                    else:
                        res = f"{body}. Thank you very much."
                else:
                    if "bitte" not in orig_clean.lower() and "danke" not in orig_clean.lower():
                        res = f"{body}. Vielen Dank im Voraus."
                    else:
                        res = f"Guten Tag, {body}. Mit freundlichen Grüßen"
            return res

        # 4. Tone: Casual & Informal (Du-Form / Friendly)
        if any(kw in inst_low for kw in ("du-form", "informell", "duzen", "locker", "kumpelhaft", "freundschaftlich", "casual", "informal", "friendly", "relaxed")):
            res = orig_clean
            replacements = [
                (r"\bkönnten Sie mir bitte\b", "kannst du mir"),
                (r"\bkönnten Sie bitte\b", "kannst du"),
                (r"\bsenden Sie mir bitte\b", "schick mir"),
                (r"\bSie\b", "du"), (r"\bIhnen\b", "dir"), (r"\bIhr\b", "dein"),
                (r"\bIhre\b", "deine"), (r"\bIhrem\b", "deinem"), (r"\bIhren\b", "deinen"),
                (r"\bIhrer\b", "deiner"), (r"\bSehr geehrte Damen und Herren,?\b", "Hi zusammen,"),
                (r"\bSehr geehrter Herr\b", "Hallo"), (r"\bSehr geehrte Frau\b", "Hallo"),
                (r"\bMit freundlichen Grüßen\b", "Viele Grüße"), (r"\bGuten Tag,?\b", "Hi"),
                (r"\bcould you please\b", "can you"), (r"\bdo not\b", "don't"),
                (r"\bcannot\b", "can't"), (r"\bwill not\b", "won't"), (r"\bI am\b", "I'm"),
                (r"\bSincerely,?\b", "Cheers,"), (r"\bBest regards,?\b", "Best,"),
            ]
            for pat, rep in replacements:
                res = re.sub(pat, rep, res, flags=re.IGNORECASE)
            if res == orig_clean:
                if not re.match(r"^(?:hi|hey|hallo)\b", res, flags=re.IGNORECASE):
                    res = f"Hi! {res}"
            return res

        # 5. Conciseness (Kürzen & Zusammenfassen)
        if any(kw in inst_low for kw in ("kürz", "kurz", "prägnant", "zusammenfassen", "zusammenfassung", "essenz", "straffen", "kompakt", "short", "summarize", "summary", "concise", "brief", "condense")):
            fillers = [
                r"\beigentlich\b\s*", r"\bgewissermaßen\b\s*", r"\bsozusagen\b\s*",
                r"\birgendwie\b\s*", r"\bhalt\b\s*", r"\beinfach mal\b\s*", r"\bquasi\b\s*",
                r"\bim grunde genommen\b\s*", r"\bwie gesagt\b\s*", r"\behrlich gesagt\b,?\s*",
                r"\bich wollte nur sagen,?\s*dass\b\s*", r"\bes ist wichtig zu erwähnen,?\s*dass\b\s*",
                r"\bbasically\b,?\s*", r"\bactually\b,?\s*", r"\bliterally\b,?\s*",
                r"\bto be honest\b,?\s*", r"\bin my opinion\b,?\s*", r"\bas a matter of fact\b,?\s*",
            ]
            res = orig_clean
            for f in fillers:
                res = re.sub(f, "", res, flags=re.IGNORECASE)
            res = re.sub(r"\bin order to\b", "to", res, flags=re.IGNORECASE)
            res = re.sub(r"\bdue to the fact that\b", "because", res, flags=re.IGNORECASE)
            res = re.sub(r"\s*\([^)]*\)", "", res)
            res = re.sub(r" +", " ", res).strip()

            # Check if specific sentence count was requested (e.g. "auf 2 Sätze", "auf einen Satz", "in 1 sentence")
            target_sents = None
            m_num = re.search(r"(?:auf|in|to)\s+(\d+|ein(?:en)?|one|zwei|two|drei|three)\s+(?:sätz|satz|sentence)", inst_low)
            if m_num:
                tok = m_num.group(1)
                word_to_int = {"ein": 1, "einen": 1, "one": 1, "zwei": 2, "two": 2, "drei": 3, "three": 3}
                target_sents = word_to_int.get(tok, int(tok) if tok.isdigit() else 1)

            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", res) if s.strip()]
            if target_sents and len(sents) > target_sents:
                res = " ".join(sents[:target_sents])
            elif res == orig_clean and len(sents) > 1:
                res = " ".join(sents[: max(1, len(sents) - 1)])
            elif res == orig_clean and "," in res:
                clauses = [c.strip() for c in res.split(",") if c.strip()]
                if len(clauses) > 1:
                    res = clauses[0] + ("." if not clauses[0].endswith((".", "!", "?")) else "")

            if res and res[0].islower():
                res = res[0].upper() + res[1:]
            return res

        # 6. Grammar, Punctuation, Cleanup & General Rewrite
        if any(kw in inst_low for kw in ("korrigier", "grammatik", "rechtschreibung", "satzzeichen", "verbesser", "umformulier", "überarbeit", "sauber", "klär", "fix", "grammar", "spelling", "correct", "improve", "rewrite", "clean", "rephrase", "polish", "format")):
            res = self.format_text(orig_clean, system_prompt, user_message) if self.rule_engine_callback else orig_clean
            res = re.sub(r"\s+([,.!?:;])", r"\1", res)
            res = re.sub(r" +", " ", res).strip()
            if res and res[0].islower():
                res = res[0].upper() + res[1:]
            if res and not res.endswith((".", "!", "?", ":", ";", '"', "'", ")")):
                res += "."
            return res

        return ""

    def test_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "message": "Lokale Regeln einsatzbereit (100% Offline / 0ms Latenz)",
            "models_count": 0,
            "error": None,
        }


def ensure_ollama_running(ollama_url: str = "http://127.0.0.1:11434") -> bool:
    """Checks if Ollama daemon is running, and attempts auto-start if local and installed."""
    import socket, urllib.parse, shutil, subprocess, os, time, sys
    parsed = urllib.parse.urlsplit(ollama_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    if host not in ("127.0.0.1", "localhost"):
        return True
    try:
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except Exception:
        pass

    ollama_exe = shutil.which("ollama")
    if not ollama_exe:
        cand = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if os.path.exists(cand):
            ollama_exe = cand
    if ollama_exe:
        try:
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            subprocess.Popen([ollama_exe, "serve"], creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(25):
                time.sleep(0.15)
                try:
                    with socket.create_connection((host, port), timeout=0.15):
                        return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


class OllamaProvider(BaseFormattingProvider):
    """Local Ollama HTTP Daemon Provider."""

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:7b"):
        from config import validate_endpoint_url
        clean_url = (ollama_url or "http://127.0.0.1:11434").rstrip("/").replace("localhost", "127.0.0.1")
        validate_endpoint_url(clean_url, allow_localhost=True)
        self.ollama_url = clean_url
        self.model = model

    def prewarm_connection(self) -> bool:
        return http_pool.prewarm(f"{self.ollama_url}/api/chat")

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
        try:
            with http_pool.urlopen(req, timeout=15.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("message", {}).get("content", text).strip()
        except Exception as e:
            if ensure_ollama_running(self.ollama_url):
                try:
                    with http_pool.urlopen(req, timeout=20.0) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        return res_json.get("message", {}).get("content", text).strip()
                except Exception:
                    pass
            raise e

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
        with http_pool.urlopen(req, timeout=18.0) as resp:
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


CURATED_MODELS_SPECS: Dict[str, Dict[str, Any]] = {
    # --- TIER 1: SPEED (< 250 ms) ---
    "google/gemini-2.5-flash": {
        "id": "google/gemini-2.5-flash",
        "tier": "speed",
        "name": "Google: Gemini 2.5 Flash",
        "sub": "google/gemini-2.5-flash — Fast & Budget Allrounder",
        "cost_input": "$0.300 / 1M Tokens (~$0.000030 / dictation)",
        "cost_output": "$2.500 / 1M Tokens",
        "typical_latency": "~200 - 300 ms",
        "context": "1.048.576 Tokens (1M)",
        "recommended_for": "Standard-Diktate, E-Mails, gemischter Text, hohe Fehlertoleranz",
        "is_default": True,
    },
    "google/gemini-2.5-flash-lite": {
        "id": "google/gemini-2.5-flash-lite",
        "tier": "speed",
        "name": "Google: Gemini 2.5 Flash Lite",
        "sub": "google/gemini-2.5-flash-lite — Ultra-Fast & Minimal Cost",
        "cost_input": "$0.100 / 1M Tokens (~$0.000010 / dictation)",
        "cost_output": "$0.400 / 1M Tokens",
        "typical_latency": "< 150 ms",
        "context": "1.048.576 Tokens (1M)",
        "recommended_for": "Maximale Geschwindigkeit, minimale Kosten, schnelle Satzzeichenkorrektur",
        "is_default": False,
    },
    "openai/gpt-4o-mini": {
        "id": "openai/gpt-4o-mini",
        "tier": "speed",
        "name": "OpenAI: GPT-4o-mini",
        "sub": "openai/gpt-4o-mini — Reliable Mini Standard",
        "cost_input": "$0.150 / 1M Tokens (~$0.000015 / dictation)",
        "cost_output": "$0.600 / 1M Tokens",
        "typical_latency": "~200 ms",
        "context": "128.000 Tokens (128k)",
        "recommended_for": "Präzise Standard-Formatierung, strukturierte Ausgaben, kein Dazuerfinden",
        "is_default": False,
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "tier": "speed",
        "name": "Meta: Llama 3.3 70B Instruct",
        "sub": "meta-llama/llama-3.3-70b-instruct — High Throughput & Structure",
        "cost_input": "$0.710 / 1M Tokens (~$0.000071 / dictation)",
        "cost_output": "$0.710 / 1M Tokens",
        "typical_latency": "~200 ms (>250 T/s via Groq)",
        "context": "131.072 Tokens (131k)",
        "recommended_for": "Maximaler Token-Durchsatz, stark im deutschen Satzbau, flüssige Absätze",
        "is_default": False,
    },

    # --- TIER 2: BALANCED (300 - 500 ms) ---
    "deepseek/deepseek-chat": {
        "id": "deepseek/deepseek-chat",
        "tier": "balanced",
        "name": "DeepSeek: DeepSeek V3 (Chat)",
        "sub": "deepseek/deepseek-chat — Balanced Value Champion",
        "cost_input": "$0.257 / 1M Tokens (~$0.000026 / dictation)",
        "cost_output": "$1.029 / 1M Tokens",
        "typical_latency": "~400 - 500 ms",
        "context": "163.840 Tokens (164k)",
        "recommended_for": "Ausgewogene Satzglättung, intelligente Umformulierungen & Notizen",
        "is_default": True,
    },
    "mistralai/mistral-small-24b-instruct-2501": {
        "id": "mistralai/mistral-small-24b-instruct-2501",
        "tier": "balanced",
        "name": "Mistral: Mistral Small 3 (24B)",
        "sub": "mistralai/mistral-small-24b-instruct-2501 — European Language Pro",
        "cost_input": "$0.070 / 1M Tokens (~$0.000007 / dictation)",
        "cost_output": "$0.140 / 1M Tokens",
        "typical_latency": "~300 - 400 ms",
        "context": "32.768 Tokens (32k)",
        "recommended_for": "Exzellente deutsche Grammatik bei minimalen Kosten, europäisches Modell",
        "is_default": False,
    },
    "anthropic/claude-3-haiku": {
        "id": "anthropic/claude-3-haiku",
        "tier": "balanced",
        "name": "Anthropic: Claude 3 Haiku",
        "sub": "anthropic/claude-3-haiku — Natural Flow & Tone",
        "cost_input": "$0.250 / 1M Tokens (~$0.000025 / dictation)",
        "cost_output": "$1.250 / 1M Tokens",
        "typical_latency": "~350 - 450 ms",
        "context": "200.000 Tokens (200k)",
        "recommended_for": "Besonders natürlicher Sprachfluss, verhindert ungewollte Überkorrekturen",
        "is_default": False,
    },

    # --- TIER 3: QUALITY (1 - 2 s) ---
    "qwen/qwen-2.5-72b-instruct": {
        "id": "qwen/qwen-2.5-72b-instruct",
        "tier": "quality",
        "name": "Qwen: Qwen 2.5 72B Instruct",
        "sub": "qwen/qwen-2.5-72b-instruct — Maximum Rule & Format Fidelity",
        "cost_input": "$0.360 / 1M Tokens (~$0.000036 / dictation)",
        "cost_output": "$0.400 / 1M Tokens",
        "typical_latency": "~1.0 - 2.0 s",
        "context": "32.768 Tokens (32k)",
        "recommended_for": "Höchste Regeltreue, strikte Negativ-Prompts, komplexe Markdown-Strukturen",
        "is_default": True,
    },
    "openai/gpt-4o": {
        "id": "openai/gpt-4o",
        "tier": "quality",
        "name": "OpenAI: GPT-4o",
        "sub": "openai/gpt-4o — Flagship Precision",
        "cost_input": "$2.500 / 1M Tokens (~$0.000250 / dictation)",
        "cost_output": "$10.000 / 1M Tokens",
        "typical_latency": "~1.0 - 1.5 s",
        "context": "128.000 Tokens (128k)",
        "recommended_for": "Anspruchsvolle Fachsprache (Medizin, Jura, Technik), komplexe Diktate",
        "is_default": False,
    },
    "anthropic/claude-sonnet-4": {
        "id": "anthropic/claude-sonnet-4",
        "tier": "quality",
        "name": "Anthropic: Claude Sonnet 4",
        "sub": "anthropic/claude-sonnet-4 — Editorial Excellence",
        "cost_input": "$3.000 / 1M Tokens (~$0.000300 / dictation)",
        "cost_output": "$15.000 / 1M Tokens",
        "typical_latency": "~1.2 - 2.0 s",
        "context": "1.000.000 Tokens (1M)",
        "recommended_for": "Höchste redaktionelle Tiefe, perfekte Berichte & lange Dokumente",
        "is_default": False,
    },
}


def get_model_tiers() -> Dict[str, Dict[str, Any]]:
    return {
        "speed": {
            "key": "speed",
            "title": tr("prio_speed_title"),
            "badge": tr("prio_speed_badge"),
            "model": "google/gemini-2.5-flash",
            "sub": "google/gemini-2.5-flash — Fast & Budget",
            "cost_input": "$0.300 / 1M Tokens (~$0.000030 / dictation)",
            "cost_output": "$2.500 / 1M Tokens",
            "typical_latency": "< 250 ms",
            "context": "1.048.576 Tokens (1M)",
            "recommended_for": tr("prio_speed_desc"),
            "models": [
                "google/gemini-2.5-flash",
                "google/gemini-2.5-flash-lite",
                "openai/gpt-4o-mini",
                "meta-llama/llama-3.3-70b-instruct",
            ],
        },
        "balanced": {
            "key": "balanced",
            "title": tr("prio_balanced_title"),
            "badge": tr("prio_balanced_badge"),
            "model": "deepseek/deepseek-chat",
            "sub": "deepseek/deepseek-chat — Balanced Value",
            "cost_input": "$0.257 / 1M Tokens (~$0.000026 / dictation)",
            "cost_output": "$1.029 / 1M Tokens",
            "typical_latency": "~400 - 500 ms",
            "context": "163.840 Tokens (164k)",
            "recommended_for": tr("prio_balanced_desc"),
            "models": [
                "deepseek/deepseek-chat",
                "mistralai/mistral-small-24b-instruct-2501",
                "anthropic/claude-3-haiku",
            ],
        },
        "quality": {
            "key": "quality",
            "title": tr("prio_quality_title"),
            "badge": tr("prio_quality_badge"),
            "model": "qwen/qwen-2.5-72b-instruct",
            "sub": "qwen/qwen-2.5-72b-instruct — Maximum Depth",
            "cost_input": "$0.360 / 1M Tokens (~$0.000036 / dictation)",
            "cost_output": "$0.400 / 1M Tokens",
            "typical_latency": "~1 - 2 s",
            "context": "32.768 Tokens (32k)",
            "recommended_for": tr("prio_quality_desc"),
            "models": [
                "qwen/qwen-2.5-72b-instruct",
                "openai/gpt-4o",
                "anthropic/claude-sonnet-4",
            ],
        },
    }


MODEL_TIERS = get_model_tiers()


def get_tier_for_model(model_id: str) -> Optional[str]:
    """Returns 'speed', 'balanced', or 'quality' for known models/aliases, or None."""
    if not model_id:
        return None
    m_low = model_id.lower().strip()
    m_clean = m_low.replace("models/", "").replace("openai/", "").replace("google/", "").replace("meta-llama/", "").replace("anthropic/", "").replace("mistralai/", "").replace("deepseek/", "").replace("qwen/", "")

    # 1. Exact match by full ID in CURATED_MODELS_SPECS
    if m_low in CURATED_MODELS_SPECS:
        return CURATED_MODELS_SPECS[m_low]["tier"]

    # 2. Exact match by clean ID
    for spec_id, spec in CURATED_MODELS_SPECS.items():
        spec_clean = spec_id.lower().split("/")[-1]
        if m_clean == spec_clean or m_low == spec_clean:
            return spec["tier"]

    # 3. Specific aliases (order matters: lite before general flash)
    if "flash-lite" in m_low or "lite" in m_low:
        return "speed"
    if any(k in m_low for k in ("gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o-mini", "llama-3.3-70b", "llama3.3:70b", "llama-3.1-8b", "llama3.1:8b")):
        return "speed"
    if any(k in m_low for k in ("deepseek-chat", "deepseek-v3", "mistral-small", "haiku")):
        return "balanced"
    if any(k in m_low for k in ("qwen-2.5-72b", "qwen2.5:72b", "gpt-4o", "sonnet")):
        return "quality"
    return None


def get_curated_models_catalog() -> List[Dict[str, Any]]:
    """Returns the full list of curated model dicts in tiered order."""
    return list(CURATED_MODELS_SPECS.values())


def get_model_details(model_id: str) -> Dict[str, Any]:
    m_low = (model_id or "").lower().strip()
    m_clean = m_low.replace("models/", "").replace("openai/", "").replace("google/", "").replace("meta-llama/", "").replace("anthropic/", "").replace("mistralai/", "").replace("deepseek/", "").replace("qwen/", "")

    # 1. Exact match by full ID in CURATED_MODELS_SPECS
    if m_low in CURATED_MODELS_SPECS:
        spec = CURATED_MODELS_SPECS[m_low]
        tier_key = spec.get("tier", "speed")
        tier_info = get_model_tiers().get(tier_key, {})
        return {
            "key": tier_key,
            "title": tier_info.get("title", spec.get("name", model_id)),
            "badge": tier_info.get("badge", ""),
            "model": spec["id"],
            "sub": spec.get("sub", spec["id"]),
            "cost_input": spec.get("cost_input", "$0.30 / 1M"),
            "cost_output": spec.get("cost_output", "$0.50 / 1M"),
            "typical_latency": spec.get("typical_latency", "~300ms"),
            "context": spec.get("context", "32k Tokens"),
            "recommended_for": spec.get("recommended_for", ""),
        }

    # 2. Exact match by clean ID
    for spec_id, spec in CURATED_MODELS_SPECS.items():
        spec_clean = spec_id.lower().split("/")[-1]
        if m_clean == spec_clean or m_low == spec_clean:
            tier_key = spec.get("tier", "speed")
            tier_info = get_model_tiers().get(tier_key, {})
            return {
                "key": tier_key,
                "title": tier_info.get("title", spec.get("name", model_id)),
                "badge": tier_info.get("badge", ""),
                "model": spec["id"],
                "sub": spec.get("sub", spec["id"]),
                "cost_input": spec.get("cost_input", "$0.30 / 1M"),
                "cost_output": spec.get("cost_output", "$0.50 / 1M"),
                "typical_latency": spec.get("typical_latency", "~300ms"),
                "context": spec.get("context", "32k Tokens"),
                "recommended_for": spec.get("recommended_for", ""),
            }

    # 3. Dynamic heuristics for other unlisted / custom models
    if any(k in m_low for k in ("flash-lite", "lite", "mini", "instant", "8b", "7b", "small", "turbo")):
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
    elif any(k in m_low for k in ("70b", "72b", "sonnet", "gpt-4o", "large", "plus", "opus")):
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

    def prewarm_connection(self) -> bool:
        return http_pool.prewarm(self._get_chat_url())

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

        detected = detect_provider(self.endpoint, self._static_api_key)
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
            with http_pool.urlopen(req, timeout=10.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", text).strip()
        except urllib.error.HTTPError as he:
            if "provider" in payload and self.allow_fallbacks and he.code in (400, 404, 422, 502, 503):
                try:
                    fallback_payload = dict(payload)
                    fallback_payload.pop("provider", None)
                    fb_req = urllib.request.Request(
                        url,
                        data=json.dumps(fallback_payload).encode("utf-8"),
                        headers=headers,
                        method="POST",
                    )
                    with http_pool.urlopen(fb_req, timeout=10.0) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        choices = res_json.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", text).strip()
                except Exception:
                    pass
            print(f"[UniversalApiProvider] format_text error from {url}: {he}")
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
            with http_pool.urlopen(req, timeout=15.0) as resp:
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
            with http_pool.urlopen(req, timeout=8.0) as resp:
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
            with http_pool.urlopen(req, timeout=8.0) as resp:
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

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        key = self._resolve_api_key()
        if not key:
            raise ValueError(f"Kein API-Key hinterlegt ({detect_provider(self.endpoint, None)})")
        out = self.format_text(text, system_prompt, user_message)
        if out and out.strip() != text.strip():
            return out.strip()
        return ""


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

    def prewarm_connection(self) -> bool:
        return self._universal.prewarm_connection()

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.format_text(text, system_prompt, user_message)

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.structure_notes(text, system_prompt, user_message)

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        return self._universal.transform_text(text, instruction, system_prompt, user_message)

    def test_connection(self) -> Dict[str, Any]:
        return self._universal.test_connection()


class GeminiProvider(BaseFormattingProvider):
    """Dedicated Google Gemini Provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self._static_api_key = api_key
        self.model = model or "gemini-2.5-flash"

    def prewarm_connection(self) -> bool:
        return http_pool.prewarm("https://generativelanguage.googleapis.com/v1beta/models")

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
            with http_pool.urlopen(req, timeout=8.0) as resp:
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
            with http_pool.urlopen(req, timeout=12.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", text).strip()
        except Exception:
            pass
        return text

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        key = self._resolve_api_key()
        if not key:
            raise ValueError("Kein API-Key hinterlegt (Google Gemini)")
        out = self.format_text(text, system_prompt, user_message)
        if out and out.strip() != text.strip():
            return out.strip()
        return ""

    def test_connection(self) -> Dict[str, Any]:
        key = self._resolve_api_key()
        if not key:
            return {"success": False, "message": "Kein Google Gemini API-Key angegeben.", "models_count": 0, "error": "API-Key fehlt"}
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            del key
            req = urllib.request.Request(url, headers={"User-Agent": "Velodictum/1.0"}, method="GET")
            with http_pool.urlopen(req, timeout=5.0) as resp:
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

    def prewarm_connection(self) -> bool:
        return self._universal.prewarm_connection()

    def format_text(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.format_text(text, system_prompt, user_message)

    def structure_notes(self, text: str, system_prompt: str, user_message: str) -> str:
        return self._universal.structure_notes(text, system_prompt, user_message)

    def transform_text(self, text: str, instruction: str, system_prompt: str, user_message: str) -> str:
        return self._universal.transform_text(text, instruction, system_prompt, user_message)

    def test_connection(self) -> Dict[str, Any]:
        return self._universal.test_connection()
