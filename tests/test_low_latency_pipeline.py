"""
Unit & Integration Tests for the Low-Latency Dictation Pipeline:
1. Persistent HTTP/1.1 Keep-Alive Connection Pool & Pre-Warming
2. Smart Fast-Path Formatting & Prefix-Cache-Optimized System Prompt
3. Incremental Pause-Based Audio Chunk Slicing (AudioRecorder)
4. CTranslate2 Turbo Greedy Decoding (WhisperEngine)
5. Parallel Window Context Prefetching & Chunk Stitching (VelodictumCoreApp)
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Ensure project root & core are on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORE = os.path.join(_ROOT, "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)
if _ROOT not in sys.path:
    sys.path.insert(1, _ROOT)


class TestPersistentHttpPool(unittest.TestCase):
    def test_socket_reuse_and_prewarm(self):
        from formatting_providers import PersistentHttpPool

        pool = PersistentHttpPool()
        mock_conn = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.read.return_value = b'{"choices":[{"message":{"content":"Hallo Welt."}}]}'
        mock_resp.getheaders.return_value = [("Content-Type", "application/json")]
        mock_conn.getresponse.return_value = mock_resp

        with patch.object(pool, "_create_connection", return_value=mock_conn) as mock_create:
            # 1. Prewarm opens and caches connection
            pool.prewarm("https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(mock_create.call_count, 1)
            mock_conn.connect.assert_called_once()

            # 2. Subsequent urlopen reuses the cached connection without reconnecting
            import urllib.request
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pool.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                self.assertIn("Hallo Welt.", body)

            # Still only 1 connection created!
            self.assertEqual(mock_create.call_count, 1)
            mock_conn.request.assert_called_once()


class TestSmartFastPathAndPromptCaching(unittest.TestCase):
    def setUp(self):
        from ai_formatter import AIFormatter
        from config import config
        self.orig_fast_path = getattr(config.formatting, "smart_fast_path", True)
        config.formatting.smart_fast_path = True
        self.formatter = AIFormatter(
            mode="flow",
            engine="universal",
            api_endpoint="https://openrouter.ai/api/v1",
            api_key="sk-test-dummy-key",
            model="google/gemini-2.5-flash-lite",
        )

    def tearDown(self):
        from config import config
        config.formatting.smart_fast_path = self.orig_fast_path

    def test_smart_fast_path_bypasses_llm_for_clean_short_sentences(self):
        with patch.object(self.formatter, "get_provider") as mock_get_prov:
            res = self.formatter.format_text(
                "Ich bin gleich im Meeting.",
                language="de",
                window_context={"style": "chat", "app_name": "Slack"},
            )
            self.assertEqual(res["text"], "Ich bin gleich im Meeting.")
            self.assertEqual(res["engine"], "smart_fast_path")
            mock_get_prov.assert_not_called()

    def test_smart_fast_path_declines_fillers_corrections_and_umlaut_substitutes(self):
        # 1. Self-correction -> must use LLM
        self.assertFalse(
            self.formatter._can_use_fast_local_path(
                "Wir treffen uns am Dienstag nein Mittwoch.",
                {"style": "chat"},
            )
        )
        # 2. ASCII umlaut substitute -> must use LLM
        self.assertFalse(
            self.formatter._can_use_fast_local_path(
                "Schoene Gruesse aus Muenchen.",
                {"style": "chat"},
            )
        )
        # 3. Code / Terminal style -> must use LLM
        self.assertFalse(
            self.formatter._can_use_fast_local_path(
                "Das funktioniert super.",
                {"style": "code"},
            )
        )
        # 4. Spoken markdown -> must use LLM
        self.assertFalse(
            self.formatter._can_use_fast_local_path(
                "Überschrift eins Projektstatus.",
                {"style": "chat"},
            )
        )

    def test_system_prompt_static_prefix_caching(self):
        ctx_a = {
            "app_name": "Slack",
            "style": "chat",
            "preceding_text": "Hey team, ",
            "workspace_project": "Velodictum",
        }
        ctx_b = {
            "app_name": "Outlook",
            "style": "email",
            "preceding_text": "Sehr geehrte Damen und Herren,",
            "selected_text": "Entwurf",
        }
        prompt_a = self.formatter._build_system_prompt("de", ctx_a)
        prompt_b = self.formatter._build_system_prompt("de", ctx_b)

        # Static core up to the end of BEISPIELE must be 100% byte-identical for LLM Prefix Caching
        split_marker = "Ausgabe: 'Wir sollten lieber am Donnerstag um 14 Uhr mit dem Release starten.'"
        self.assertIn(split_marker, prompt_a)
        self.assertIn(split_marker, prompt_b)
        prefix_a = prompt_a.split(split_marker)[0]
        prefix_b = prompt_b.split(split_marker)[0]
        self.assertEqual(prefix_a, prefix_b)


class TestIncrementalAudioChunking(unittest.TestCase):
    def test_pop_completed_chunk_on_silence(self):
        from audio_recorder import AudioRecorder

        rec = AudioRecorder(sample_rate=16000, channels=1)
        rec._is_recording = True
        frame_len = int(16000 * 0.05)  # 800 samples per 50ms frame

        # Push 2.0 seconds of active speech (40 frames, RMS = 0.1)
        speech_frame = np.full((frame_len, 1), 0.1, dtype=np.float32)
        for _ in range(40):
            rec._frames.append(speech_frame.copy())

        # Before silence pause: should not pop
        self.assertIsNone(rec.pop_completed_chunk_on_silence(min_speech_sec=1.6, silence_sec=0.40))

        # Push 0.45 seconds of silence (9 frames, RMS = 0.001)
        silence_frame = np.full((frame_len, 1), 0.001, dtype=np.float32)
        for _ in range(9):
            rec._frames.append(silence_frame.copy())

        chunk = rec.pop_completed_chunk_on_silence(min_speech_sec=1.6, silence_sec=0.40, silence_rms=0.008)
        self.assertIsNotNone(chunk)
        # 47 frames popped, 2 trailing silence frames retained as padding for next phrase
        self.assertEqual(len(chunk), 47 * frame_len)
        self.assertEqual(len(rec._frames), 2)


class TestWhisperTurboGreedyDecoding(unittest.TestCase):
    def test_turbo_model_uses_greedy_beam_1_and_without_timestamps(self):
        from stt_engine import WhisperEngine
        from config import config

        orig_prov = config.whisper.provider
        config.whisper.provider = "local"
        try:
            engine = WhisperEngine(model_size="large-v3-turbo", device="cuda", beam_size=5)
            mock_model = MagicMock()
            Seg = MagicMock()
            Seg.text = "Das ist ein schneller Test."
            Seg.no_speech_prob = 0.01
            Info = MagicMock()
            Info.language = "de"
            Info.language_probability = 0.99
            Info.duration = 2.1
            mock_model.transcribe.return_value = ([Seg], Info)
            engine._model = mock_model
            engine._is_loaded = True

            with patch.object(engine, "load"):
                audio = np.full(16000 * 2, 0.05, dtype=np.float32)
                res = engine.transcribe(audio, sample_rate=16000)

            self.assertEqual(res["text"], "Das ist ein schneller Test.")
            call_kwargs = mock_model.transcribe.call_args[1]
            self.assertEqual(call_kwargs["beam_size"], 1)
            self.assertEqual(call_kwargs["best_of"], 1)
            self.assertTrue(call_kwargs["without_timestamps"])
            self.assertEqual(call_kwargs["no_repeat_ngram_size"], 0)
            self.assertEqual(call_kwargs["repetition_penalty"], 1.0)
        finally:
            config.whisper.provider = orig_prov


class TestParallelPipelineStitching(unittest.TestCase):
    def test_zero_tail_stt_when_chunk_already_transcribed_in_pause(self):
        from main import VelodictumCoreApp

        with patch("main.AudioRecorder"), \
             patch("main.WhisperEngine"), \
             patch("main.TextInjector"), \
             patch("main.HotkeyManager"), \
             patch("main.MobileBridgeServer"), \
             patch("audio_device_monitor.audio_device_monitor"), \
             patch("correction_detector.correction_detector"):

            app = VelodictumCoreApp()
            # Simulate a chunk already transcribed during a recording pause
            app._streamed_chunks = ["Erster Satz wurde bereits in der Pause transkribiert."]
            app._streamed_duration = 2.4
            app._streamed_lang = "de"
            app._streamed_prob = 0.99
            app._prefetched_win_ctx = {
                "app_name": "Slack",
                "style": "chat",
                "needs_leading_space": False,
            }
            app._prefetch_event.set()

            app.formatter.format_text = MagicMock(return_value={
                "text": "Erster Satz wurde bereits in der Pause transkribiert.",
                "mode": "flow",
                "engine": "smart_fast_path",
                "latency": 0.001,
                "action": None,
            })

            # Tail audio is just 100ms of silence before the user pressed Stop
            silent_tail = np.zeros(int(16000 * 0.1), dtype=np.float32)
            app._process_audio_worker(silent_tail)

            # Whisper should NOT be called again on stop because tail is silent!
            app.stt.transcribe.assert_not_called()
            app.injector.inject.assert_called_once_with(
                "Erster Satz wurde bereits in der Pause transkribiert.",
                raw_text="Erster Satz wurde bereits in der Pause transkribiert.",
                send_enter=False,
            )


if __name__ == "__main__":
    unittest.main()
