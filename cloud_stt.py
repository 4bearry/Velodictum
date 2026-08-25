"""
Velodictum - Cloud Speech-to-Text Adapters (Universal API, Grok AI & OpenAI)
Provides ultra-low-latency Cloud Whisper API integration with BYOK (Bring Your Own Key) architecture.
"""
import io
import json
import os
import time
import urllib.request
import urllib.error
import wave
from typing import Dict, Optional
import numpy as np


class CloudWhisperEngine:
    """
    Unified Cloud STT engine for Universal API (OpenRouter, Custom / Self-Hosted), Grok AI (Groq LPU) and OpenAI Whisper API.
    """
    def __init__(
        self,
        provider: str = "universal",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider.lower().strip()
        self._static_api_key = api_key
        self.endpoint = endpoint
        self.model = model

    def _resolve_api_key(self) -> Optional[str]:
        """Resolves API key Just-In-Time from Credential Vault or explicit override."""
        if self._static_api_key and self._static_api_key.strip():
            return self._static_api_key.strip()
        try:
            import security_credentials as sec
            from config import config
            if self.provider in ("universal", "openrouter", "custom"):
                return sec.get_credential(sec.KEY_WHISPER_UNIVERSAL_API) or config.whisper.get_api_key("universal")
            elif self.provider in ("grok", "groq"):
                return sec.get_credential(sec.KEY_WHISPER_GROQ_API) or config.whisper.get_api_key("groq")
            elif self.provider == "openai":
                return sec.get_credential(sec.KEY_WHISPER_OPENAI_API) or config.whisper.get_api_key("openai")
        except Exception:
            return None
        return None

    @property
    def api_key(self) -> Optional[str]:
        return self._resolve_api_key()

    @api_key.setter
    def api_key(self, value: Optional[str]):
        self._static_api_key = value

    def set_config(
        self,
        provider: str,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider.lower().strip()
        self._static_api_key = api_key
        if endpoint is not None:
            self.endpoint = endpoint
        if model is not None:
            self.model = model

    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Transcribe audio using the chosen cloud provider or generic OpenAI-compatible endpoint.
        """
        from config import validate_endpoint_url

        audio_duration = len(audio_data) / sample_rate
        start_t = time.perf_counter()

        # Convert float32 numpy audio to 16-bit PCM WAV in memory
        arr16 = (np.clip(audio_data, -1.0, 1.0) * 32767.0).astype(np.int16)
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(arr16.tobytes())
        wav_bytes = wav_buf.getvalue()

        # Resolve key JIT
        key = self._resolve_api_key()

        # Configure provider endpoints & models
        if self.provider in ("universal", "openrouter", "custom"):
            raw_endpoint = self.endpoint or "https://openrouter.ai/api/v1/audio/transcriptions"
            endpoint = validate_endpoint_url(raw_endpoint, allow_localhost=True)
            model_name = self.model or "openai/whisper-large-v3"
            provider_name = "Universal API"
            if not key and ("openrouter.ai" in endpoint or "api.openai.com" in endpoint):
                raise ValueError("Kein API-Schlüssel für die Universal STT API hinterlegt. Bitte in den Einstellungen eintragen.")
        elif self.provider in ("grok", "groq"):
            raw_endpoint = self.endpoint or "https://api.groq.com/openai/v1/audio/transcriptions"
            endpoint = validate_endpoint_url(raw_endpoint, allow_localhost=True)
            model_name = self.model or "whisper-large-v3"
            provider_name = "Grok AI"
            if not key:
                raise ValueError("Kein API-Schlüssel für Grok AI hinterlegt. Bitte in den Einstellungen eintragen.")
        else:
            raw_endpoint = self.endpoint or "https://api.openai.com/v1/audio/transcriptions"
            endpoint = validate_endpoint_url(raw_endpoint, allow_localhost=True)
            model_name = self.model or "whisper-1"
            provider_name = "OpenAI"
            if not key:
                raise ValueError("Kein API-Schlüssel für OpenAI hinterlegt. Bitte in den Einstellungen eintragen.")

        # Build multipart/form-data payload
        boundary = f"----WebKitFormBoundary{int(time.time()*1000)}"
        body = bytearray()

        def _add_field(name: str, value: str):
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{value}\r\n".encode("utf-8"))

        def _add_file(name: str, filename: str, file_bytes: bytes, content_type: str):
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body.extend(file_bytes)
            body.extend(b"\r\n")

        _add_field("model", model_name)
        _add_field("response_format", "verbose_json")
        if language:
            _add_field("language", language)
        if initial_prompt:
            _add_field("prompt", initial_prompt)

        _add_file("file", "audio.wav", wav_bytes, "audio/wav")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Velodictum/1.0",
        }
        if key and key.strip():
            headers["Authorization"] = f"Bearer {key.strip()}"
        del key

        if "openrouter.ai" in endpoint:
            headers["HTTP-Referer"] = "https://velodictum.ai"
            headers["X-Title"] = "Velodictum"

        req = urllib.request.Request(
            endpoint,
            data=bytes(body),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                text = res_json.get("text", "").strip()
                detected_lang = res_json.get("language", language or "de")
                latency = time.perf_counter() - start_t

                return {
                    "text": text,
                    "language": detected_lang,
                    "language_prob": 0.99,
                    "duration": audio_duration,
                    "latency": latency,
                    "rtf": latency / audio_duration if audio_duration > 0 else 0,
                    "provider": provider_name,
                }
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", err_body)
                raise RuntimeError(f"{provider_name} API Fehler ({e.code}): {err_msg}")
            except Exception:
                raise RuntimeError(f"{provider_name} API HTTP {e.code} Fehler: {e.reason}")
