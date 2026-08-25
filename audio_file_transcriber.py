"""
Velodictum - Batch Audio File Transcriber
Transcribes audio files (.mp3, .wav, .m4a, .ogg, .aac, .flac) offline or via cloud STT,
applies the Flow Layer post-processing, and exports clean Markdown documents.
"""
import os
import time
from typing import Callable, Dict, Optional
from stt_engine import WhisperEngine
from ai_formatter import AIFormatter


from config import validate_safe_filepath

MAX_AUDIO_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB max audio file
MAX_AUDIO_DURATION_SEC = 600.0  # 10 minutes max duration


class AudioFileTranscriber:
    def __init__(self, stt_engine: WhisperEngine, ai_formatter: AIFormatter):
        self.stt_engine = stt_engine
        self.ai_formatter = ai_formatter

    def transcribe_file(
        self,
        filepath: str,
        language: Optional[str] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Dict:
        safe_path = validate_safe_filepath(filepath)
        if not os.path.exists(safe_path):
            raise FileNotFoundError(f'Audio-Datei nicht gefunden: {safe_path}')

        # 1. DoS / OOM Protection: File size limit (100 MB)
        file_size = os.path.getsize(safe_path)
        if file_size > MAX_AUDIO_FILE_SIZE_BYTES:
            raise ValueError(f"Audio-Datei überschreitet die maximale Größe von 100 MB ({file_size} Bytes).")

        if on_progress:
            on_progress(0.1, 'Lade Audio-Datei...')

        start_t = time.perf_counter()

        self.stt_engine.load()
        if on_progress:
            on_progress(0.3, 'Transkribiere Audio...')

        segments, info = self.stt_engine._model.transcribe(
            safe_path,
            language=language or self.stt_engine.language,
            vad_filter=True,
            beam_size=self.stt_engine.beam_size,
        )

        # 2. Duration limit check
        if info and getattr(info, "duration", 0.0) > MAX_AUDIO_DURATION_SEC:
            raise ValueError(f"Audio-Dauer überschreitet das Limit von 10 Minuten ({info.duration:.1f} Sekunden).")

        raw_chunks = []
        for seg in segments:
            txt = seg.text.strip()
            if txt:
                raw_chunks.append(txt)

        raw_text = ' '.join(raw_chunks).strip()

        if on_progress:
            on_progress(0.7, 'Wende Flow Layer Formatierung an...')

        fmt_res = self.ai_formatter.format_text(
            raw_text,
            language=info.language if info else 'de',
        )

        final_text = fmt_res.get('text', raw_text)
        total_latency = time.perf_counter() - start_t

        if on_progress:
            on_progress(1.0, 'Fertig!')

        return {
            'file': os.path.basename(filepath),
            'filepath': filepath,
            'text': final_text,
            'raw_text': raw_text,
            'duration': info.duration if info else 0.0,
            'language': info.language if info else 'de',
            'latency': total_latency,
        }
