"""
Velodictum - Groq Cloud Whisper STT Adapter
Provides ultra-low-latency Whisper-Large-v3 inference (<80ms) on Groq LPU cloud hardware.
Ideal for laptops, ultrabooks, and systems without dedicated NVIDIA RTX GPUs.
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


class GroqWhisperEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = "whisper-large-v3"

    def set_api_key(self, api_key: Optional[str]):
        self.api_key = api_key

    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Transcribe audio array using Groq Whisper-Large-v3 API.
        """
        if not self.api_key:
            raise ValueError("Kein Groq API-Schlüssel hinterlegt. Bitte in den Einstellungen eintragen.")

        audio_duration = len(audio_data) / sample_rate
        start_t = time.perf_counter()

        # Convert float32 audio to 16-bit PCM WAV in memory
        arr16 = (np.clip(audio_data, -1.0, 1.0) * 32767.0).astype(np.int16)
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(arr16.tobytes())
        wav_bytes = wav_buf.getvalue()

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

        _add_field("model", self.model)
        _add_field("response_format", "verbose_json")
        if language:
            _add_field("language", language)
        if initial_prompt:
            _add_field("prompt", initial_prompt)

        _add_file("file", "audio.wav", wav_bytes, "audio/wav")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        req = urllib.request.Request(
            url,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "Velodictum/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
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
                }
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", err_body)
                raise RuntimeError(f"Groq API Fehler ({e.code}): {err_msg}")
            except Exception:
                raise RuntimeError(f"Groq API HTTP {e.code} Fehler: {e.reason}")
