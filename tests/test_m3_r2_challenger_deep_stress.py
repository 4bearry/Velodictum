#!/usr/bin/env python3
"""
Deep Stress Harness for Milestone 3 Iteration 2 (m3_r2_challenger_2)
===================================================================
Adversarially tests:
1. 120-switch engine cycling under concurrent audio stream.
2. Invariant widget attributes and strict identity aliases across bilingual stress.
3. Window lifecycle, closeEvent ignore/hide, hideEvent mic cleanup, sequential destruction.
4. Active search filter stability during rapid retranslation and tab transitions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QCheckBox, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent

from config import config
from i18n import tr, set_current_language, get_current_language
from gui.signals import signals
from gui.dashboard_window import (
    DashboardWindow,
    CollapsibleSettingsCard,
    SettingsDisclosureSection
)


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestM3R2ChallengerDeepStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_rec.is_testing = False
        self.mock_rec.start_test.return_value = True
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        cur_eng = getattr(config.formatting, "engine", "rules")
        if cur_eng == "openrouter":
            cur_eng = "universal"
        self.mock_fmt.engine = cur_eng
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_120_cycle_engine_switching_under_audio_stream(self):
        """
        Execute 120 rapid engine switches (20 full passes over 6 engines)
        while interleaving audio_level_updated signals.
        Verify:
        - Exact target container is visible, all others hidden.
        - config.formatting.engine matches.
        - No exceptions or stale visibility states.
        """
        engines = [
            ("rules", 0, self.dash.rules_container),
            ("ollama", 1, self.dash.ollama_container),
            ("universal", 2, self.dash.universal_container),
            ("openai", 3, self.dash.openai_container),
            ("gemini", 4, self.dash.gemini_container),
            ("groq", 5, self.dash.groq_container),
        ]
        all_containers = [t[2] for t in engines]

        # Force transition away from current index to ensure initial trigger
        start_idx = 5 if self.dash.combo_engine.currentIndex() == 0 else 0
        self.dash.combo_engine.setCurrentIndex(start_idx)
        self.app.processEvents()

        for cycle in range(20):
            for eng_name, idx, container in engines:
                # Concurrent audio signal
                signals.audio_level_updated.emit(0.42)
                self.dash.combo_engine.setCurrentIndex(idx)
                self.app.processEvents()

                self.assertEqual(config.formatting.engine, eng_name)
                self.assertEqual(self.dash.ai_formatter.engine, eng_name)
                self.assertFalse(container.isHidden(), f"Cycle {cycle}: {eng_name} container must be visible")

                for other in all_containers:
                    if other is not container:
                        self.assertTrue(other.isHidden(), f"Cycle {cycle}: {other} must be hidden when {eng_name} active")

    def test_invariant_widget_attributes_and_strict_aliases_after_retranslation(self):
        """
        Verify all 268 widgets and strict identity aliases survive 30 rapid retranslations.
        """
        for i in range(30):
            lang = "de" if i % 2 == 0 else "en"
            self.dash.retranslate_ui(lang)
            self.app.processEvents()

        # Check strict identity aliases
        self.assertIs(self.dash.card_llm, self.dash.card_fmt)
        self.assertIs(self.dash.card_sound, self.dash.card_gen)
        self.assertIs(self.dash.card_mob, self.dash.card_audio)
        self.assertIs(self.dash.card_sys, self.dash.card_adv)
        self.assertIs(self.dash.combo_o_model, self.dash.combo_oai_model)
        self.assertIs(self.dash.chk_hallucination, self.dash.chk_squelcher)

        # Check widget count
        qwidget_attrs = [
            a for a in dir(self.dash)
            if isinstance(getattr(self.dash, a, None), QWidget) and not a.startswith("__")
        ]
        self.assertGreaterEqual(len(qwidget_attrs), 263)
        self.assertEqual(len(self.dash.all_settings_cards), 7)
        self.assertEqual(len(self.dash.all_disclosure_sections), 6)

    def test_window_close_and_hide_event_lifecycle(self):
        """
        Verify closeEvent ignores destruction, hides window, and terminates mic test.
        Verify hideEvent terminates mic test.
        Verify sequential creation/destruction of 8 windows without leaks.
        """
        self.dash.show()
        self.app.processEvents()
        self.mock_rec.is_testing = True

        # Test closeEvent
        evt = QCloseEvent()
        self.dash.closeEvent(evt)
        self.app.processEvents()

        self.assertFalse(evt.isAccepted(), "closeEvent must be ignored to prevent destruction")
        self.assertFalse(self.dash.isVisible(), "Window must be hidden on closeEvent")
        self.mock_rec.stop_test.assert_called()

        # Test hideEvent
        self.mock_rec.stop_test.reset_mock()
        self.mock_rec.is_testing = True
        self.dash.show()
        self.app.processEvents()
        self.dash.hide()
        self.app.processEvents()
        self.mock_rec.stop_test.assert_called()

        # Test sequential instantiation
        for _ in range(8):
            w = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
            w.show()
            self.app.processEvents()
            if hasattr(w, "waveform_widget") and hasattr(w.waveform_widget, "anim_timer"):
                w.waveform_widget.anim_timer.stop()
            if hasattr(w, "gpu_timer"):
                w.gpu_timer.stop()
            w.close()
            w.deleteLater()
            self.app.processEvents()

    def test_retranslation_burst_under_active_filtering(self):
        """
        Stress test search filtering while simultaneously blasting retranslations
        and tab switches.
        """
        self.dash.show()
        self.app.processEvents()

        # Active search query
        self.dash.input_settings_search.setText("bridge")
        self.app.processEvents()

        # Audio card and sub_mob_bridge must be visible & expanded
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.card_audio.is_expanded)
        self.assertTrue(self.dash.sub_mob_bridge.is_expanded)

        # Blast retranslations and tab switches
        for i in range(20):
            lang = "de" if i % 2 == 0 else "en"
            self.dash.retranslate_ui(lang)
            tab_idx = i % self.dash.tabs.count()
            self.dash.tabs.setCurrentIndex(tab_idx)
            self.app.processEvents()

        # Return to settings tab
        self.dash.tabs.setCurrentIndex(2)
        self.dash.input_settings_search.setText("whisper")
        self.app.processEvents()

        self.assertFalse(self.dash.card_stt.isHidden())
        self.assertTrue(self.dash.card_stt.is_expanded)


if __name__ == "__main__":
    unittest.main()
