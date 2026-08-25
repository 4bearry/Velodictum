"""
Velodictum - Accelerated Speech-to-Text Engine
Optimized for local GPU/CPU (CUDA / FP16 / Int8) and Cloud Providers (Grok AI & OpenAI) with reentrant locking, anti-hallucination and de-duplication.
"""
import os
import sys
import re
import threading
import time
from typing import Dict, Optional
import numpy as np


def init_cuda_dll_paths():
    """Ensure NVIDIA CUDA/cuDNN DLL directories and system CUDA paths are registered with Windows."""
    # 1. Check if running inside PyInstaller bundle (_MEIPASS or dist/Velodictum)
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        if os.path.isdir(base_dir):
            try:
                os.add_dll_directory(base_dir)
            except Exception:
                pass
            os.environ["PATH"] = base_dir + os.pathsep + os.environ.get("PATH", "")
        internal_dir = os.path.join(os.path.dirname(sys.executable), "_internal")
        if os.path.isdir(internal_dir):
            try:
                os.add_dll_directory(internal_dir)
            except Exception:
                pass
            os.environ["PATH"] = internal_dir + os.pathsep + os.environ.get("PATH", "")

    # 2. Check site-packages/nvidia modules in venv
    try:
        import site
        site_dirs = []
        if hasattr(site, "getsitepackages"):
            site_dirs.extend(site.getsitepackages())
        if hasattr(site, "getusersitepackages"):
            site_dirs.append(site.getusersitepackages())
        
        py_dir = os.path.dirname(sys.executable)
        site_dirs.append(os.path.join(py_dir, "Lib", "site-packages"))
        site_dirs.append(os.path.join(os.path.dirname(py_dir), "Lib", "site-packages"))

        for s_dir in site_dirs:
            nvidia_dir = os.path.join(s_dir, "nvidia")
            if os.path.isdir(nvidia_dir):
                for root, dirs, files in os.walk(nvidia_dir):
                    if "bin" in dirs or any(f.endswith(".dll") for f in files):
                        bin_path = os.path.join(root, "bin") if "bin" in dirs else root
                        try:
                            os.add_dll_directory(bin_path)
                        except Exception:
                            pass
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

    # 3. Check system CUDA_PATH environment variable
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        cuda_bin = os.path.join(cuda_path, "bin")
        if os.path.isdir(cuda_bin):
            try:
                os.add_dll_directory(cuda_bin)
            except Exception:
                pass
            os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")


init_cuda_dll_paths()

from faster_whisper import WhisperModel
from custom_vocabulary import vocab_manager
from config import config



MAX_AUDIO_DURATION_SEC = 600.0  # Max 10 minutes per dictation to prevent RAM/VRAM exhaustion


class WhisperEngine:
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter

        self._model: Optional[WhisperModel] = None
        self._is_loaded = False
        # IMPORTANT: Must use RLock (reentrant) so change_model can call load() on same thread!
        self._load_lock = threading.RLock()

    def unload(self):
        """Explicitly frees CTranslate2 WhisperModel and releases CUDA VRAM caches."""
        with self._load_lock:
            if self._model is not None:
                try:
                    del self._model
                except Exception:
                    pass
                self._model = None
            self._is_loaded = False

            # Force immediate garbage collection
            import gc
            gc.collect()

            # Release PyTorch / CUDA memory caches if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except Exception:
                pass

    def load(self):
        """Loads the Whisper model into GPU VRAM (thread-safe with RLock)."""
        with self._load_lock:
            if self._is_loaded and self._model is not None:
                return

            effective_compute = self.compute_type
            if self.device == "cpu" and effective_compute in ("float16", "int8_float16"):
                effective_compute = "int8"

            print(f"[STT] Loading faster-whisper model '{self.model_size}' on {self.device} ({effective_compute})...")
            start_t = time.perf_counter()

            # Resolve model path: use the exact per-model subdirectory when already
            # downloaded; otherwise let WhisperModel download into the base dir.
            from model_manager import model_manager
            base_dir = model_manager.get_models_dir()
            model_subdir = model_manager.get_model_dir(self.model_size, base_dir)

            if os.path.isdir(model_subdir) and os.path.exists(os.path.join(model_subdir, "model.bin")):
                # Model already downloaded: pass the exact path for instant load.
                model_ref = model_subdir
                print(f"[STT] Found local model at '{model_subdir}'.")
            else:
                # Model not yet local: let WhisperModel download it into base_dir.
                model_ref = self.model_size

            try:
                self._model = WhisperModel(
                    model_ref,
                    device=self.device,
                    compute_type=effective_compute,
                    download_root=base_dir,
                    num_workers=2,
                )
                self._is_loaded = True
                load_time = time.perf_counter() - start_t
                print(f"[STT] Model '{self.model_size}' loaded successfully in {load_time:.2f}s.")
            except Exception as e:
                if self.device == "cuda":
                    print(f"[STT] CUDA load failed ({e}). Falling back to CPU...")
                    try:
                        self.device = "cpu"
                        self._model = WhisperModel(
                            model_ref,
                            device="cpu",
                            compute_type="int8",
                            download_root=base_dir,
                            num_workers=2,
                        )
                        self._is_loaded = True
                        print(f"[STT] Fallback model '{self.model_size}' loaded on CPU (int8).")
                        return
                    except Exception as cpu_err:
                        print(f"[STT] CPU fallback failed: {cpu_err}")
                self.unload()
                print(f"[STT] Error loading model '{self.model_size}': {e}")
                raise

    def change_model(self, new_model_size: str, language: Optional[str] = None):
        """Switch to a different model size or language profile at runtime with clean VRAM release."""
        with self._load_lock:
            if self.model_size == new_model_size and self.language == language and self._is_loaded and self._model is not None:
                return
            # Release existing model VRAM first before allocating new model
            self.unload()
            self.model_size = new_model_size
            self.language = language
            self.load()
            self.warmup()

    def warmup(self):
        """Performs a dummy inference to compile CUDA graphs and warm up GPU caches."""
        with self._load_lock:
            if not self._is_loaded or self._model is None:
                self.load()

            if self._model is None:
                print("[STT] Cannot warm up: Model is not initialized.")
                return

            print("[STT] Warming up inference kernels...")
            warmup_audio = np.zeros(1600, dtype=np.float32)  # 100ms silence (fast compilation)
            try:
                self._model.transcribe(
                    warmup_audio,
                    beam_size=1,
                    vad_filter=False,
                    language="en",
                    condition_on_previous_text=False,
                    temperature=0.0,
                )
                print("[STT] Warmup complete. Engine ready for instant dictation.")
            except Exception as e:
                print(f"[STT] Warmup warning: {e}")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, task: str = "transcribe") -> Dict:
        """
        Transcribe audio numpy array. Supports task='transcribe' or task='translate'.
        Enforces maximum audio boundaries and catches CUDA OOM exceptions gracefully.
        """
        if audio_data is None or len(audio_data) == 0:
            return {
                "text": "",
                "language": self.language or "de",
                "language_prob": 0.0,
                "duration": 0.0,
                "latency": 0.0,
                "rtf": 0,
            }

        # Enforce maximum audio length boundary to prevent memory exhaustion
        max_samples = int(MAX_AUDIO_DURATION_SEC * sample_rate)
        if len(audio_data) > max_samples:
            print(f"[STT] Audio array exceeds max duration limit ({MAX_AUDIO_DURATION_SEC}s). Truncating to prevent VRAM overflow.")
            audio_data = audio_data[:max_samples]

        active_provider = getattr(config.whisper, "provider", "local")
        if active_provider in ("universal", "openrouter", "custom", "grok", "groq", "openai"):
            api_key = config.whisper.get_api_key(active_provider)
            # Universal / Custom can proceed even without an API key if hitting a local endpoint
            endpoint = getattr(config.whisper, "universal_endpoint", None) if active_provider in ("universal", "openrouter", "custom") else None
            model = getattr(config.whisper, "universal_model", None) if active_provider in ("universal", "openrouter", "custom") else None
            if api_key or (active_provider in ("universal", "openrouter", "custom") and endpoint and "localhost" in endpoint or "127.0.0.1" in (endpoint or "")):
                try:
                    from cloud_stt import CloudWhisperEngine
                    cloud_eng = CloudWhisperEngine(
                        provider=active_provider,
                        api_key=api_key,
                        endpoint=endpoint,
                        model=model,
                    )
                    initial_prompt = vocab_manager.get_prompt_injection(self.language or "de")
                    res = cloud_eng.transcribe(audio_data, sample_rate=sample_rate, language=self.language, initial_prompt=initial_prompt)
                    res["text"] = self.deduplicate_repeated_phrases(res.get("text", ""))
                    return res
                except Exception as e:
                    print(f"[STT] {active_provider.upper()} Cloud STT error, falling back to local: {e}")

        with self._load_lock:
            if not self._is_loaded or self._model is None:
                self.load()

            if self._model is None:
                raise RuntimeError("Whisper Modell konnte nicht in den GPU-Speicher geladen werden.")

            audio_duration = len(audio_data) / sample_rate
            start_t = time.perf_counter()

            # Language-specific initial prompt conditioned on custom vocabulary terms
            initial_prompt = vocab_manager.get_prompt_injection(self.language or "de")

            try:
                # Anti-Hallucination & Anti-Repetition settings
                segments, info = self._model.transcribe(
                    audio_data,
                    task=task,
                    beam_size=self.beam_size,
                    vad_filter=self.vad_filter,
                    vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=150),
                    language=self.language,
                    initial_prompt=initial_prompt,
                    condition_on_previous_text=False,
                    repetition_penalty=1.15,
                    no_repeat_ngram_size=3,
                )

                # Collect segment texts (filtering out high no-speech probability)
                raw_chunks = [
                    segment.text.strip()
                    for segment in segments
                    if segment.text.strip() and getattr(segment, "no_speech_prob", 0.0) < 0.65
                ]
                
                # Deduplicate consecutive identical segments
                cleaned_chunks = []
                for chunk in raw_chunks:
                    if not cleaned_chunks or chunk.lower() != cleaned_chunks[-1].lower():
                        cleaned_chunks.append(chunk)

                full_text = " ".join(cleaned_chunks).strip()
                full_text = self.deduplicate_repeated_phrases(full_text)

                # Hallucination Squelcher: Entropy, VAD Energy, and Silence Dataset Filter
                if self.is_hallucination(full_text, audio_data=audio_data):
                    full_text = ""

                latency = time.perf_counter() - start_t

                return {
                    "text": full_text,
                    "language": info.language,
                    "language_prob": info.language_probability,
                    "duration": audio_duration,
                    "latency": latency,
                    "rtf": latency / audio_duration if audio_duration > 0 else 0,
                }
            except Exception as e:
                err_msg = str(e).lower()
                if "out of memory" in err_msg or "cuda" in err_msg:
                    print(f"[STT] CUDA Out-of-Memory / GPU resource error: {e}. Executing emergency VRAM cleanup...")
                    self.unload()
                    return {
                        "text": "",
                        "language": self.language or "de",
                        "language_prob": 0.0,
                        "duration": audio_duration,
                        "latency": time.perf_counter() - start_t,
                        "rtf": 0,
                        "error": f"GPU VRAM Error: {e}",
                    }
                raise

    @staticmethod
    def is_hallucination(text: str, audio_data: Optional[np.ndarray] = None) -> bool:
        """
        Heuristic Entropy, Repetition, and Silence Hallucination Squelcher.
        Returns True if the transcribed text is a Whisper hallucination.
        """
        if not text or not text.strip():
            return True

        clean = text.strip()
        low = clean.lower().strip(" .!?,;:-_~#\"'")

        # 1. Noise artifacts / punctuation only
        if len(low) < 2 or re.match(r"^[\W\d_]+$", clean):
            return True

        # 2. Audio Energy Check (if raw audio passed)
        if audio_data is not None and len(audio_data) > 0:
            rms = float(np.sqrt(np.mean(audio_data**2)))
            # Extremely silent audio (<0.002 RMS) cannot produce meaningful multi-word speech
            if rms < 0.002 and len(clean.split()) > 2:
                return True

        # 3. Known Silence / Dataset Hallucination Blacklist
        hallucinations = [
            "vielen dank fürs zuschauen",
            "vielen dank für das zuschauen",
            "vielen dank für ihre aufmerksamkeit",
            "vielen dank fürs zuhören",
            "vielen dank für die aufmerksamkeit",
            "danke fürs zuschauen",
            "danke für eure aufmerksamkeit",
            "danke fürs zuhören",
            "untertitel:",
            "untertitelung",
            "untertitel der sendung",
            "untertitel von",
            "zdf",
            "ard",
            "amara.org",
            "opensubtitles",
            "thank you for watching",
            "thanks for watching",
            "thank you very much for watching",
            "thank you for listening",
            "thanks for listening",
            "subscribe to my channel",
            "like and subscribe",
            "see you next time",
            "see you in the next video",
            "diktat mit korrekter",
            "fachbegriffe und eigennamen",
            "copyright",
            "all rights reserved",
            "tschüss bis zum nächsten mal",
            "bis zum nächsten mal",
            "wdr",
            "swr",
            "ndr",
            "mdr",
            "br fernsehen",
        ]
        for h in hallucinations:
            if h in low and len(low) < len(h) + 25:
                return True

        # 4. Low-Entropy / Looping Repetition Squelcher
        words = low.split()
        if len(words) >= 4:
            unique_words = set(words)
            # If high proportion of repeated words
            if len(unique_words) / len(words) < 0.35:
                return True

        # 5. Word repetition loops (e.g., "da da da da")
        if re.search(r"(\b\w+\b)(?:\s+\1){3,}", low):
            return True

        return False

    @staticmethod
    def deduplicate_repeated_phrases(text: str) -> str:
        """Removes duplicate repeated sentences or adjacent identical phrases."""
        if not text:
            return ""

        # Remove adjacent identical sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        deduped = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            if not deduped or s_clean.lower() != deduped[-1].lower():
                deduped.append(s_clean)
        
        result = " ".join(deduped)

        # Remove immediate duplicated word loops e.g. "aber aber"
        result = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", result, flags=re.IGNORECASE)

        return result

    @staticmethod
    def clean_filler_words(text: str) -> str:
        """Removes common German and English spoken hesitations."""
        if not text:
            return ""

        fillers = [
            r"\b(äh+m?)\b", r"\b(ähm+)\b", r"\b(öhm+)\b", r"\b(mhm+)\b",
            r"\b(um+)\b", r"\b(uh+)\b", r"\b(er+)\b", r"\b(ah+)\b",
        ]
        cleaned = text
        for pat in fillers:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)

        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]

        return cleaned
