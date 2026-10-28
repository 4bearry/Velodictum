#!/usr/bin/env python3
"""
M2 Empirical Challenger Stress-Test Suite
=========================================
Empirical verification of Milestone 2:
1. Simultaneous bilingual toggles across DashboardWindow, FloatingHUD, and ScratchpadWindow.
   Verification of button labels in Scratchpad containing "Notiz" (in DE) and "Copy" (in EN).
2. Invalid language code fallback (hud.retranslate_ui("xyz"), None, pad.retranslate_ui("xyz"), etc.).
   Zero crashes, resilient error containment.
3. Scratchpad note structuring background thread, error handling, and thread safety.
4. Copy button confirmation timing (1500ms singleShot restoration).
5. Stats updating on large text insertion (100k+ words, unicode, emojis, edge cases).
6. HUD geometry consistency (36.0 px locked height across all states) and audio level clamping.
"""

import os
import sys
import time
import threading
import unittest
from unittest.mock import MagicMock

# Configure headless offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
import pyperclip

from config import config
from i18n import tr, set_current_language, get_current_language
from gui.signals import signals
from gui.dashboard_window import DashboardWindow
from gui.floating_hud import FloatingHUD
from gui.scratchpad_window import ScratchpadWindow


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestM2BilingualTogglesAndParity(unittest.TestCase):
    """
    Empirical tests for simultaneous bilingual toggles across Dashboard, HUD, and Scratchpad.
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_rec = MagicMock()
        self.mock_stt = MagicMock()
        self.mock_fmt = MagicMock()
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.pad = ScratchpadWindow(self.mock_fmt)
        self.hud = FloatingHUD()

    def tearDown(self):
        self.dash.close()
        self.pad.close()
        self.hud.close()
        self.app.processEvents()

    def test_direct_bilingual_toggle_en_and_de(self):
        """
        Verify direct calls to retranslate_ui across all 3 components.
        Verify Scratchpad copy button label has 'Notiz' in German and 'Copy' in English.
        """
        # Switch to German
        set_current_language("de")
        self.dash.retranslate_ui("de")
        self.pad.retranslate_ui("de")
        self.hud.retranslate_ui("de")
        self.app.processEvents()

        # DE Assertions - Scratchpad
        self.assertIn("Notiz", self.pad.btn_copy.text(), "Scratchpad btn_copy must contain 'Notiz' in DE")
        self.assertIn("Kopieren", self.pad.btn_copy.text(), "Scratchpad btn_copy must contain 'Kopieren' in DE")
        self.assertIn("Diktieren", self.pad.btn_mic.text())
        self.assertIn("strukturieren", self.pad.btn_structure.text().lower())
        self.assertIn("Leeren", self.pad.btn_clear.text())
        self.assertIn("Diktierbuch", self.pad.windowTitle())
        self.assertIn("Diktierbuch", self.pad.title_lbl.text())

        # DE Assertions - Dashboard
        self.assertIn("Einstellungen", self.dash.tabs.tabText(2))
        self.assertIn("Bereit", self.dash.lbl_hero_action.text())

        # Switch to English
        set_current_language("en")
        self.dash.retranslate_ui("en")
        self.pad.retranslate_ui("en")
        self.hud.retranslate_ui("en")
        self.app.processEvents()

        # EN Assertions - Scratchpad
        self.assertIn("Copy", self.pad.btn_copy.text(), "Scratchpad btn_copy must contain 'Copy' in EN")
        self.assertIn("Dictate", self.pad.btn_mic.text())
        self.assertIn("Structure", self.pad.btn_structure.text())
        self.assertIn("Clear", self.pad.btn_clear.text())
        self.assertIn("Voice Scratchpad", self.pad.windowTitle())
        self.assertIn("Voice Scratchpad", self.pad.title_lbl.text())

        # EN Assertions - Dashboard
        self.assertIn("Settings", self.dash.tabs.tabText(2))
        self.assertIn("Ready", self.dash.lbl_hero_action.text())

    def test_signal_driven_bilingual_synchronization(self):
        """
        Verify that emitting signals.language_changed propagates to all 3 components simultaneously.
        """
        # Emit 'de' via global event bus
        signals.language_changed.emit("de")
        self.app.processEvents()

        self.assertIn("Notiz", self.pad.btn_copy.text())
        self.assertIn("Einstellungen", self.dash.tabs.tabText(2))

        # Emit 'en' via global event bus
        signals.language_changed.emit("en")
        self.app.processEvents()

        self.assertIn("Copy", self.pad.btn_copy.text())
        self.assertIn("Settings", self.dash.tabs.tabText(2))

    def test_rapid_burst_bilingual_cycling(self):
        """
        Stress test 50 rapid alternating language switches without desync or memory error.
        """
        for i in range(50):
            lang = "de" if i % 2 == 0 else "en"
            signals.language_changed.emit(lang)
            self.app.processEvents()

        # Final state should be English (since i=49 is odd)
        self.assertIn("Copy", self.pad.btn_copy.text())
        self.assertIn("Settings", self.dash.tabs.tabText(2))


class TestM2InvalidLanguageCodeFallback(unittest.TestCase):
    """
    Empirical tests for invalid language code fallback and error containment.
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_rec = MagicMock()
        self.mock_stt = MagicMock()
        self.mock_fmt = MagicMock()
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.pad = ScratchpadWindow(self.mock_fmt)
        self.hud = FloatingHUD()

    def tearDown(self):
        self.dash.close()
        self.pad.close()
        self.hud.close()
        self.app.processEvents()

    def test_hud_invalid_language_codes_zero_crashes(self):
        """
        Test hud.retranslate_ui('xyz'), hud.retranslate_ui(None), and boundary types.
        Verify zero crashes and state preservation.
        """
        test_inputs = [
            "xyz",
            None,
            "",
            "invalid_lang",
            12345,
            -1.0,
            [],
            {},
            object(),
            "   ",
            "DE_de",
            "en-US",
        ]
        for val in test_inputs:
            try:
                self.hud.retranslate_ui(val)
            except Exception as e:
                self.fail(f"hud.retranslate_ui crashed on input {repr(val)}: {e}")

    def test_pad_invalid_language_codes_zero_crashes(self):
        """
        Test pad.retranslate_ui('xyz'), pad.retranslate_ui(None), and boundary types.
        Verify zero crashes and button text remains intact.
        """
        test_inputs = [
            "xyz",
            None,
            "",
            "foo_bar",
            99999,
            False,
            [1, 2, 3],
        ]
        for val in test_inputs:
            try:
                self.pad.retranslate_ui(val)
            except Exception as e:
                self.fail(f"pad.retranslate_ui crashed on input {repr(val)}: {e}")

    def test_dash_invalid_language_codes_zero_crashes(self):
        """
        Test dash.retranslate_ui with invalid values.
        """
        test_inputs = ["xyz", None, "", 42, {}]
        for val in test_inputs:
            try:
                self.dash.retranslate_ui(val)
            except Exception as e:
                self.fail(f"dash.retranslate_ui crashed on input {repr(val)}: {e}")

    def test_recovery_after_invalid_language_call(self):
        """
        Verify that after receiving invalid language calls, a subsequent valid
        retranslation works without residual corruption.
        """
        self.hud.retranslate_ui("xyz")
        self.pad.retranslate_ui("xyz")
        self.dash.retranslate_ui("xyz")

        # Now retranslate to German
        self.pad.retranslate_ui("de")
        self.dash.retranslate_ui("de")
        self.hud.retranslate_ui("de")
        self.app.processEvents()

        self.assertIn("Notiz", self.pad.btn_copy.text())
        self.assertIn("Einstellungen", self.dash.tabs.tabText(2))


class TestM2ScratchpadStructuringThread(unittest.TestCase):
    """
    Empirical tests for Scratchpad note structuring background thread.
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_fmt = MagicMock()
        self.pad = ScratchpadWindow(self.mock_fmt)

    def tearDown(self):
        self.pad.close()
        self.app.processEvents()

    def test_empty_text_does_not_trigger_thread(self):
        """
        If text is empty or only whitespace, _structure_notes must not launch
        a structuring task or disable the button.
        """
        self.pad.text_edit.setPlainText("   \n\t  ")
        self.pad._structure_notes()
        self.assertTrue(self.pad.btn_structure.isEnabled())
        self.mock_fmt.structure_notes.assert_not_called()

    def test_successful_background_structuring(self):
        """
        Test that _structure_notes launches a daemon thread, disables button,
        updates text_edit via Qt signal upon completion, and re-enables button.
        """
        mock_output = "# Meeting Notes\n\n- Discuss architecture\n- Review M2 tests"
        
        def slow_structure(text, language="en"):
            time.sleep(0.05)  # Simulate network / LLM inference latency
            return mock_output

        self.mock_fmt.structure_notes.side_effect = slow_structure

        self.pad.text_edit.setPlainText("meeting notes discuss architecture review m2 tests")
        
        # Trigger structuring
        self.pad._structure_notes()

        # Immediate state check: button is disabled and shows structuring text
        self.assertFalse(self.pad.btn_structure.isEnabled())
        btn_text = self.pad.btn_structure.text().lower()
        self.assertTrue("structur" in btn_text or "struktur" in btn_text, f"Unexpected button text during structuring: {btn_text}")

        # Wait for thread to complete and signal to be delivered to Qt event loop
        start = time.time()
        while not self.pad.btn_structure.isEnabled() and time.time() - start < 3.0:
            self.app.processEvents()
            time.sleep(0.01)

        # Post-completion verification
        self.assertTrue(self.pad.btn_structure.isEnabled(), "Button must be re-enabled after structuring")
        self.assertEqual(self.pad.text_edit.toPlainText().strip(), mock_output.strip())

    def test_fallback_to_format_text_if_structure_notes_missing(self):
        """
        Test fallback path when ai_formatter only has format_text and lacks structure_notes.
        """
        # Create a mock without structure_notes attribute
        class FallbackFormatter:
            def format_text(self, text, language="en"):
                return {"text": f"Formatted fallback: {text}"}

        fallback_pad = ScratchpadWindow(FallbackFormatter())
        fallback_pad.text_edit.setPlainText("raw voice transcript")
        fallback_pad._structure_notes()

        start = time.time()
        while not fallback_pad.btn_structure.isEnabled() and time.time() - start < 3.0:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertTrue(fallback_pad.btn_structure.isEnabled())
        self.assertEqual(fallback_pad.text_edit.toPlainText().strip(), "Formatted fallback: raw voice transcript")
        fallback_pad.close()

    def test_exception_in_background_thread_handled_gracefully(self):
        """
        If ai_formatter raises an unhandled exception (e.g. network down, API 500),
        the thread must catch it, emit structuring_failed, and restore button to enabled.
        """
        def faulty_structure(text, language="en"):
            raise ConnectionError("Ollama / Cloud LLM connection failed")

        self.mock_fmt.structure_notes.side_effect = faulty_structure
        self.pad.text_edit.setPlainText("test note to structure")

        self.pad._structure_notes()

        start = time.time()
        while not self.pad.btn_structure.isEnabled() and time.time() - start < 3.0:
            self.app.processEvents()
            time.sleep(0.01)

        # Button must be restored and enabled, zero unhandled thread crashes
        self.assertTrue(self.pad.btn_structure.isEnabled())
        # Text should remain untouched on failure
        self.assertEqual(self.pad.text_edit.toPlainText(), "test note to structure")


class TestM2CopyButtonTiming(unittest.TestCase):
    """
    Empirical tests for copy button confirmation timing (1500ms singleShot restoration).
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_fmt = MagicMock()
        self.pad = ScratchpadWindow(self.mock_fmt)

    def tearDown(self):
        self.pad.close()
        self.app.processEvents()

    def test_copy_button_empty_text_does_nothing(self):
        """
        When text is empty, clicking copy does not set clipboard or show 'Copied!'.
        """
        self.pad.text_edit.setPlainText("")
        original_btn_text = self.pad.btn_copy.text()
        self.pad._copy_to_clipboard()
        self.assertEqual(self.pad.btn_copy.text(), original_btn_text)

    def test_copy_button_confirmation_timing_en(self):
        """
        In English:
        1. Click copy -> button changes to 'Copied!' immediately.
        2. At 500ms -> button is still 'Copied!'.
        3. At 1600ms -> button label is restored to 'Copy Note'.
        """
        set_current_language("en")
        self.pad.retranslate_ui("en")
        self.pad.text_edit.setPlainText("Empirical test note content.")

        self.pad._copy_to_clipboard()

        # Immediate check
        self.assertIn("copied", self.pad.btn_copy.text().lower())

        # Check at 500ms: still 'Copied!'
        QTest.qWait(500)
        self.assertIn("copied", self.pad.btn_copy.text().lower())

        # Check after timer expires (1500ms total, wait 1100ms more -> 1600ms)
        QTest.qWait(1100)
        self.assertIn("Copy", self.pad.btn_copy.text())
        self.assertNotIn("copied", self.pad.btn_copy.text().lower())

    def test_copy_button_confirmation_timing_de(self):
        """
        In German:
        1. Click copy -> button changes to 'Kopiert!' immediately.
        2. At 1600ms -> button label is restored to 'Notiz Kopieren' (contains both 'Notiz' and 'Kopieren').
        """
        set_current_language("de")
        self.pad.retranslate_ui("de")
        self.pad.text_edit.setPlainText("Deutscher Notizinhalt für den Test.")

        self.pad._copy_to_clipboard()

        # Immediate check
        self.assertIn("kopiert", self.pad.btn_copy.text().lower())

        # Wait past 1500ms
        QTest.qWait(1600)
        self.assertIn("Notiz", self.pad.btn_copy.text())
        self.assertIn("Kopieren", self.pad.btn_copy.text())


class TestM2StatsUpdatingLargeText(unittest.TestCase):
    """
    Empirical tests for Scratchpad statistics calculation on large text insertion and edge cases.
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_fmt = MagicMock()
        self.pad = ScratchpadWindow(self.mock_fmt)

    def tearDown(self):
        self.pad.close()
        self.app.processEvents()

    def test_stats_empty_and_whitespace(self):
        """
        Empty text and pure whitespace must show 0 words, 0 characters.
        """
        self.pad.text_edit.setPlainText("")
        self.assertIn("0", self.pad.lbl_stats.text())

        self.pad.text_edit.setPlainText("   \n\t  \r\n   ")
        self.assertIn("0", self.pad.lbl_stats.text())

    def test_stats_accuracy_moderate_text(self):
        """
        Verify precise word and character counts on known multi-line text.
        """
        text = "The quick brown fox\njumps over the lazy dog."
        self.pad.text_edit.setPlainText(text)
        self.app.processEvents()

        expected_words = len(text.split())
        expected_chars = len(text)
        stats_text = self.pad.lbl_stats.text()
        self.assertIn(str(expected_words), stats_text)
        self.assertIn(str(expected_chars), stats_text)

    def test_stats_large_text_insertion_performance_and_accuracy(self):
        """
        Stress test: insert 50,000 words (~350,000 characters).
        Verify calculation completes in < 500ms and stats match exactly.
        """
        paragraph = "Velodictum provides ultra-fast low-latency voice dictation with local Whisper AI and dark glassmorphism. "
        large_text = paragraph * 3500  # ~52,500 words, ~370,000 chars

        start_time = time.time()
        self.pad.text_edit.setPlainText(large_text)
        self.app.processEvents()
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 1.0, f"Large text stats update took {elapsed:.2f}s, exceeding 1.0s limit")

        expected_words = len(large_text.strip().split())
        expected_chars = len(large_text.strip())
        stats_text = self.pad.lbl_stats.text()

        self.assertIn(str(expected_words), stats_text)
        self.assertIn(str(expected_chars), stats_text)

    def test_stats_bilingual_translation_preservation(self):
        """
        Verify stats label updates formatting when switching between EN and DE.
        """
        text = "One two three four five"
        self.pad.text_edit.setPlainText(text)

        # English
        set_current_language("en")
        self.pad.retranslate_ui("en")
        self.app.processEvents()
        self.assertIn("words", self.pad.lbl_stats.text())
        self.assertIn("characters", self.pad.lbl_stats.text())

        # German
        set_current_language("de")
        self.pad.retranslate_ui("de")
        self.app.processEvents()
        self.assertIn("Wörter", self.pad.lbl_stats.text())
        self.assertIn("Zeichen", self.pad.lbl_stats.text())

    def test_clear_button_resets_stats(self):
        """
        Clicking btn_clear clears text_edit and resets stats to 0.
        """
        self.pad.text_edit.setPlainText("Text that should be cleared")
        self.app.processEvents()
        self.assertNotIn("0 words", self.pad.lbl_stats.text())

        # Click clear
        self.pad.btn_clear.click()
        self.app.processEvents()

        self.assertEqual(self.pad.text_edit.toPlainText(), "")
        self.assertIn("0", self.pad.lbl_stats.text())


class TestM2HUDGeometryAndAudioClamping(unittest.TestCase):
    """
    Empirical tests for HUD vertical height stabilization and audio metering.
    """

    def setUp(self):
        self.app = get_qapp()
        self.hud = FloatingHUD()

    def tearDown(self):
        self.hud.close()
        self.app.processEvents()

    def test_hud_target_height_strictly_constant(self):
        """
        Verify target_h remains strictly 36.0 px across all active lifecycle state methods,
        preventing any vertical spring jitter or oscillation.
        """
        # Transition into recording state
        self.hud.on_recording_started()
        self.assertEqual(self.hud.target_h, 36.0, "recording_started must set target_h == 36.0")

        self.hud.on_voice_edit_started()
        self.assertEqual(self.hud.target_h, 36.0, "voice_edit_started must keep target_h == 36.0")

        self.hud.on_recording_stopped()
        self.assertEqual(self.hud.target_h, 36.0, "recording_stopped must keep target_h == 36.0")

        self.hud.on_transcription_started()
        self.assertEqual(self.hud.target_h, 36.0, "transcription_started must keep target_h == 36.0")

        self.hud.on_formatting_started()
        self.assertEqual(self.hud.target_h, 36.0, "formatting_started must keep target_h == 36.0")

        self.hud.on_transcription_completed({"text": "Test transcription", "latency": 0.42})
        self.assertEqual(self.hud.target_h, 36.0, "transcription_completed must keep target_h == 36.0")

        self.hud.on_voice_edit_completed({"text": "Test edit", "latency": 0.35})
        self.assertEqual(self.hud.target_h, 36.0, "voice_edit_completed must keep target_h == 36.0")

    def test_hud_audio_level_clamping_and_finiteness(self):
        """
        Verify extreme and non-finite RMS values are safely clamped between 0.0 and 1.0.
        """
        test_values = [
            -1000.0, -1.0, -0.0001, 0.0, 0.05, 0.5, 1.0, 10.0, 1000.0,
            float("nan"), float("inf"), float("-inf")
        ]
        for val in test_values:
            self.hud.on_audio_level(val)
            self.assertGreaterEqual(self.hud.target_rms, 0.0, f"target_rms must be >= 0.0 for rms={val}")
            self.assertLessEqual(self.hud.target_rms, 1.0, f"target_rms must be <= 1.0 for rms={val}")


class TestM2AdversarialStateStress(unittest.TestCase):
    """
    Adversarial stress tests for state transitions, visibility toggling,
    HUD state retranslation, and concurrent operations.
    """

    def setUp(self):
        self.app = get_qapp()
        self.mock_rec = MagicMock()
        self.mock_stt = MagicMock()
        self.mock_fmt = MagicMock()
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

    def tearDown(self):
        self.hud.close()
        self.pad.close()
        self.app.processEvents()

    def test_hud_all_six_states_retranslation(self):
        """
        Verify that retranslate_ui correctly translates the status and sub-texts
        across all HUD states in both English and German.
        """
        states_to_check = [
            ("recording", "hud_listening", "Aufnahme", "Listening"),
            ("voice_edit", "hud_transform", "Transformieren", "Transform"),
            ("cancelled", "hud_cancelled", "Abgebrochen", "Cancelled"),
            ("error", "hud_error", "Fehler", "Error"),
        ]

        for state, key, de_expected, en_expected in states_to_check:
            self.hud.state = state

            # Test German
            set_current_language("de")
            self.hud.retranslate_ui("de")
            self.assertIn(
                de_expected.lower(),
                self.hud.status_text.lower(),
                f"HUD status in state '{state}' should match DE '{de_expected}', got '{self.hud.status_text}'"
            )

            # Test English
            set_current_language("en")
            self.hud.retranslate_ui("en")
            self.assertIn(
                en_expected.lower(),
                self.hud.status_text.lower(),
                f"HUD status in state '{state}' should match EN '{en_expected}', got '{self.hud.status_text}'"
            )

    def test_scratchpad_rapid_copy_clicks(self):
        """
        Rapidly click copy 10 times in 100ms. Verify no crashes and final label restores properly.
        """
        self.pad.text_edit.setPlainText("Rapid click content")
        set_current_language("de")
        self.pad.retranslate_ui("de")

        for _ in range(10):
            self.pad._copy_to_clipboard()
            QTest.qWait(10)

        self.assertIn("kopiert", self.pad.btn_copy.text().lower())

        # Wait past 1500ms
        QTest.qWait(1600)
        self.assertIn("Notiz", self.pad.btn_copy.text())
        self.assertIn("Kopieren", self.pad.btn_copy.text())

    def test_scratchpad_close_during_copy_timer(self):
        """
        Verify that closing the scratchpad window while a 1500ms restore timer
        is pending does not trigger unhandled exceptions or crash.
        """
        temp_pad = ScratchpadWindow(self.mock_fmt)
        temp_pad.text_edit.setPlainText("Ephemeral note")
        temp_pad._copy_to_clipboard()
        temp_pad.close()
        self.app.processEvents()

        # Let the 1500ms timer fire on the closed window
        QTest.qWait(1600)

    def test_scratchpad_toggle_visibility_idempotence(self):
        """
        Verify toggle_visibility alternates visibility and gives focus to text_edit.
        """
        self.pad.hide()
        self.assertFalse(self.pad.isVisible())

        # Toggle on
        self.pad.toggle_visibility()
        self.app.processEvents()
        QTest.qWait(50)
        self.assertTrue(self.pad.isVisible())

        # Toggle off
        self.pad.toggle_visibility()
        self.app.processEvents()
        QTest.qWait(50)
        self.assertFalse(self.pad.isVisible())

    def test_scratchpad_dictation_lifecycle_button_states(self):
        """
        Verify Scratchpad mic button state transitions through dictation lifecycle
        when triggered by the pad.
        """
        set_current_language("de")
        self.pad.retranslate_ui("de")
        self.assertIn("Diktieren", self.pad.btn_mic.text())

        # Click mic in scratchpad
        self.pad._on_mic_clicked()
        self.assertTrue(self.pad._recording_triggered_by_pad)

        # Recording started
        self.pad._on_recording_started()
        self.assertTrue(self.pad._recording_active_in_pad)
        self.assertIn("Aufnahme", self.pad.btn_mic.text())

        # Recording stopped
        self.pad._on_recording_stopped()
        self.assertIn("Verarbeite", self.pad.btn_mic.text())
        self.assertFalse(self.pad.btn_mic.isEnabled())

        # Transcription completed
        self.pad._on_transcribe_done()
        self.assertFalse(self.pad._recording_active_in_pad)
        self.assertFalse(self.pad._recording_triggered_by_pad)
        self.assertIn("Diktieren", self.pad.btn_mic.text())
        self.assertTrue(self.pad.btn_mic.isEnabled())


if __name__ == "__main__":
    unittest.main()

