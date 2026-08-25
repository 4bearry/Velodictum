#!/usr/bin/env python3
"""
Unit test verifying the restructured 7-card Settings Information Architecture,
live search bar filtering, and visual dependency toggles in DashboardWindow.
"""
import sys
import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

from config import config
from gui.dashboard_window import DashboardWindow


class TestSettingsArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def test_seven_cards_presence(self):
        self.assertEqual(len(self.dash.all_settings_cards), 7)
        # Verify English titles
        self.dash.retranslate_ui('en')
        card_titles_en = [c.lbl_title.text() for c in self.dash.all_settings_cards]
        self.assertTrue(any('GENERAL' in t for t in card_titles_en))
        self.assertTrue(any('AUDIO' in t for t in card_titles_en))
        self.assertTrue(any('SPEECH RECOGNITION' in t for t in card_titles_en))
        self.assertTrue(any('FORMATTING' in t for t in card_titles_en))
        self.assertTrue(any('SHORTCUTS' in t for t in card_titles_en))
        self.assertTrue(any('FLOATING HUD' in t for t in card_titles_en))
        self.assertTrue(any('SYSTEM' in t for t in card_titles_en))

        # Verify German switch
        self.dash.retranslate_ui('de')
        card_titles_de = [c.lbl_title.text() for c in self.dash.all_settings_cards]
        self.assertTrue(any('ALLGEMEIN' in t for t in card_titles_de))
        self.assertTrue(any('AUDIO' in t for t in card_titles_de))
        self.assertTrue(any('SPRACHERKENNUNG' in t for t in card_titles_de))
        self.assertTrue(any('FORMATIERUNG' in t for t in card_titles_de))
        self.assertTrue(any('SHORTCUTS' in t for t in card_titles_de))
        self.assertTrue(any('FLOATING HUD' in t for t in card_titles_de))
        self.assertTrue(any('SYSTEM' in t for t in card_titles_de))

    def test_backward_compatibility_aliases(self):
        self.assertEqual(self.dash.card_llm, self.dash.card_fmt)
        self.assertEqual(self.dash.card_sound, self.dash.card_gen)
        self.assertEqual(self.dash.card_mob, self.dash.card_audio)
        self.assertEqual(self.dash.card_sys, self.dash.card_adv)

    def test_search_filtering(self):
        search = self.dash.input_settings_search
        self.dash._on_settings_search_changed('Mikrofon')
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.card_audio.is_expanded)

        self.dash._on_settings_search_changed('Hotkey')
        self.assertFalse(self.dash.card_hk.isHidden())
        self.assertTrue(self.dash.card_hk.is_expanded)

        self.dash._on_settings_search_changed('')
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_visual_dependency_toggling(self):
        self.dash.chk_sound_cues.setChecked(False)
        self.assertFalse(self.dash.sound_options_widget.isEnabled())
        self.dash.chk_sound_cues.setChecked(True)
        self.assertTrue(self.dash.sound_options_widget.isEnabled())

        self.dash.chk_auto_ducking.setChecked(False)
        self.assertFalse(self.dash.duck_options_widget.isEnabled())
        self.dash.chk_auto_ducking.setChecked(True)
        self.assertTrue(self.dash.duck_options_widget.isEnabled())

        self.dash.chk_mobile_bridge.setChecked(False)
        self.assertFalse(self.dash.mob_options_widget.isEnabled())
        self.dash.chk_mobile_bridge.setChecked(True)
        self.assertTrue(self.dash.mob_options_widget.isEnabled())

        self.dash.chk_hud_enable.setChecked(False)
        self.assertFalse(self.dash.hud_options_widget.isEnabled())
        self.dash.chk_hud_enable.setChecked(True)
        self.assertTrue(self.dash.hud_options_widget.isEnabled())

    def test_expand_and_collapse_all(self):
        self.dash._expand_all_settings()
        for card in self.dash.all_settings_cards:
            self.assertTrue(card.is_expanded)

        self.dash._collapse_all_settings()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.is_expanded)

    def test_priority_cards_highlighting(self):
        # Click Fast / Speed card
        self.dash._on_priority_card_clicked('speed')
        self.assertTrue(self.dash.card_prio_fast.selected)
        self.assertFalse(self.dash.card_prio_balanced.selected)
        self.assertFalse(self.dash.card_prio_quality.selected)

        # Click Balanced card
        self.dash._on_priority_card_clicked('balanced')
        self.assertFalse(self.dash.card_prio_fast.selected)
        self.assertTrue(self.dash.card_prio_balanced.selected)
        self.assertFalse(self.dash.card_prio_quality.selected)

        # Click Quality card
        self.dash._on_priority_card_clicked('quality')
        self.assertFalse(self.dash.card_prio_fast.selected)
        self.assertFalse(self.dash.card_prio_balanced.selected)
        self.assertTrue(self.dash.card_prio_quality.selected)

    def test_checkbox_plain_und_labels(self):
        self.dash.retranslate_ui('de')
        self.assertTrue('Start' in self.dash.chk_sound_cues.text() and 'Stopp' in self.dash.chk_sound_cues.text())
        self.assertIn('Artefakte', self.dash.chk_hallucination.text())

        self.dash.retranslate_ui('en')
        self.assertTrue('start' in self.dash.chk_sound_cues.text().lower() and 'stop' in self.dash.chk_sound_cues.text().lower())
        self.assertIn('artifacts', self.dash.chk_hallucination.text().lower())

    def test_mic_test_toggle(self):
        self.mock_rec.is_testing = False
        self.mock_rec.start_test.return_value = True
        self.dash.retranslate_ui('de')

        # Click Start Test
        self.dash._toggle_mic_test()
        self.mock_rec.start_test.assert_called_once()
        self.assertTrue("beenden" in self.dash.btn_mic_test.text().lower() or "stop" in self.dash.btn_mic_test.text().lower())

        # Click Stop Test
        self.mock_rec.is_testing = True
        self.dash._toggle_mic_test()
        self.mock_rec.stop_test.assert_called_once()
        self.assertTrue("starten" in self.dash.btn_mic_test.text().lower() or "start" in self.dash.btn_mic_test.text().lower())
        self.assertTrue("inaktiv" in self.dash.lbl_mic_test_status.text().lower() or "inactive" in self.dash.lbl_mic_test_status.text().lower())

    def test_mic_test_auto_stops_on_recording_started(self):
        self.mock_rec.is_testing = True
        self.dash.btn_mic_test.setText("Mikrofontest beenden")

        self.dash._on_rec_started()
        self.mock_rec.stop_test.assert_called()
        self.assertTrue("starten" in self.dash.btn_mic_test.text().lower() or "start" in self.dash.btn_mic_test.text().lower())


    def test_dynamic_whisper_model_activation(self):
        # 1. Activate standard profile model
        self.dash._on_activate_whisper_model("large-v3-turbo")
        self.assertEqual(config.whisper.model_size, "large-v3-turbo")
        self.assertEqual(config.whisper.profile, "de_max")
        self.assertTrue(self.dash.profile_cards["de_max"].selected)

        # 2. Activate arbitrary downloaded model (e.g. tiny)
        self.dash._on_activate_whisper_model("tiny")
        self.assertEqual(config.whisper.model_size, "tiny")
        self.assertEqual(config.whisper.profile, "tiny")
        # Ensure preset cards are unselected cleanly for custom model
        for card in self.dash.profile_cards.values():
            self.assertFalse(card.selected)
        self.assertIn("TINY", self.dash.pill_profile.text())


if __name__ == '__main__':
    unittest.main()
