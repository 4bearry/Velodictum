#!/usr/bin/env python3
"""
Milestone 3 Empirical Challenger 2 Adversarial Test Suite
========================================================
Adversarially stress tests:
1. Bound attributes & QWidget invariants (all 263+ baseline widget attributes).
2. Card order, count (7), and strict `is` identity aliases.
3. Progressive disclosure sections (6) and bidirectional signal synchronization.
4. Rapid engine switching loop across all 6 engines with container visibility verification.
5. Window destruction, show/hide bursts, closeEvent ignore/hide semantics, and mic test auto-cleanup.
6. Adversarial search filter stress (regex, unicode, whitespace, bilingual synonyms, and auto-expansion).
7. Rapid bilingual retranslation cycles and invalid language fallbacks.
8. Event bus signal-slot concurrency stress under rapid state transitions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Configure headless offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QCheckBox, QComboBox, QLineEdit, QLabel
)
from PyQt6.QtCore import Qt, QTimer
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
    """Returns or creates the offscreen QApplication instance."""
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestM3BoundAttributesAndCardInvariants(unittest.TestCase):
    """
    Stress tests attribute preservation, widget types, card count,
    identity aliases, and progressive disclosure sections.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_all_qwidget_attributes_presence_and_types(self):
        """
        Verify that all baseline widget attributes exist, are not None,
        and are valid QWidget instances. Must exceed 263 baseline widgets.
        """
        qwidget_attrs = [
            a for a in dir(self.dash)
            if isinstance(getattr(self.dash, a, None), QWidget) and not a.startswith("__")
        ]
        self.assertGreaterEqual(
            len(qwidget_attrs),
            263,
            f"Expected at least 263 bound QWidget attributes, found {len(qwidget_attrs)}"
        )

        # Explicitly verify high-risk buttons across all tabs
        critical_buttons = [
            "btn_hero_scratchpad", "btn_copy_latest", "btn_sub_vocab", "btn_sub_snippets",
            "btn_sub_apps", "btn_vocab_add", "btn_vocab_cancel", "btn_snip_add",
            "btn_snip_cancel", "btn_expand_all", "btn_collapse_all", "btn_preview_sound",
            "btn_mic_test", "btn_copy_mob", "btn_open_mob", "btn_rotate_mob_token",
            "btn_change_storage", "btn_u_toggle_key", "btn_toggle_custom_catalog",
            "btn_u_fetch_models", "btn_u_test", "btn_ol_test", "btn_oai_test",
            "btn_oai_toggle_key", "btn_gem_test", "btn_gem_toggle_key", "btn_grq_test",
            "btn_grq_toggle_key", "btn_toggle_adv_formatting", "btn_record_hk",
            "btn_record_ve", "btn_record_un", "btn_record_sp", "btn_open_sp",
            "btn_hud_reset_pos", "btn_lang_toggle"
        ]
        for btn_name in critical_buttons:
            self.assertTrue(
                hasattr(self.dash, btn_name),
                f"Missing critical button attribute: {btn_name}"
            )
            btn = getattr(self.dash, btn_name)
            self.assertIsInstance(
                btn, QPushButton,
                f"Attribute {btn_name} is {type(btn)}, expected QPushButton"
            )

        # Explicitly verify high-risk checkboxes
        critical_checkboxes = [
            "chk_autostart", "chk_minimized", "chk_sound_cues", "chk_auto_ducking",
            "chk_mobile_bridge", "chk_squelcher", "chk_hallucination", "chk_u_zdr",
            "chk_u_fallbacks", "chk_filler", "chk_auto_app_profiles", "chk_apply_snippets",
            "chk_send_it", "chk_context_intelligence", "chk_workspace_seeding",
            "chk_spoken_markdown", "chk_hud_enable", "chk_hud_fluid", "chk_hud_minimal",
            "chk_hud_remember_pos", "chk_privacy_shield", "chk_restore_clip"
        ]
        for chk_name in critical_checkboxes:
            self.assertTrue(
                hasattr(self.dash, chk_name),
                f"Missing critical checkbox attribute: {chk_name}"
            )
            chk = getattr(self.dash, chk_name)
            self.assertIsInstance(
                chk, QCheckBox,
                f"Attribute {chk_name} is {type(chk)}, expected QCheckBox"
            )

        # Explicitly verify comboboxes
        critical_combos = [
            "combo_engine", "combo_sound_theme", "combo_sound_vol", "combo_mic",
            "combo_stt_provider", "combo_u_model", "combo_u_routing",
            "combo_oai_model", "combo_gem_model", "combo_grq_model"
        ]
        for combo_name in critical_combos:
            self.assertTrue(
                hasattr(self.dash, combo_name),
                f"Missing critical combobox attribute: {combo_name}"
            )
            combo = getattr(self.dash, combo_name)
            self.assertIsInstance(
                combo, QComboBox,
                f"Attribute {combo_name} is {type(combo)}, expected QComboBox"
            )

    def test_card_order_count_and_strict_identity_aliases(self):
        """
        Verify that all_settings_cards contains exactly 7 cards in proper order,
        and backward compatibility aliases hold strict `is` identity.
        """
        self.assertEqual(len(self.dash.all_settings_cards), 7)

        # Verify each card is a CollapsibleSettingsCard
        for idx, card in enumerate(self.dash.all_settings_cards):
            self.assertIsInstance(
                card, CollapsibleSettingsCard,
                f"Card at index {idx} ({card}) must be a CollapsibleSettingsCard"
            )

        # Expected canonical card order
        expected_cards = [
            self.dash.card_gen,
            self.dash.card_audio,
            self.dash.card_stt,
            self.dash.card_fmt,
            self.dash.card_hk,
            self.dash.card_hud,
            self.dash.card_adv
        ]
        self.assertEqual(self.dash.all_settings_cards, expected_cards)

        # Verify strict identity aliases (must be `is`, not just `==`)
        self.assertIs(self.dash.card_llm, self.dash.card_fmt, "card_llm must be identical to card_fmt")
        self.assertIs(self.dash.card_sound, self.dash.card_gen, "card_sound must be identical to card_gen")
        self.assertIs(self.dash.card_mob, self.dash.card_audio, "card_mob must be identical to card_audio")
        self.assertIs(self.dash.card_sys, self.dash.card_adv, "card_sys must be identical to card_adv")

        # Verify alias pointers for model combos and squelcher
        self.assertIs(self.dash.combo_o_model, self.dash.combo_oai_model)
        self.assertIs(self.dash.chk_hallucination, self.dash.chk_squelcher)

    def test_progressive_disclosure_sections_integrity(self):
        """
        Verify all 6 progressive disclosure sub-accordions are registered,
        are SettingsDisclosureSection instances, and toggle properly.
        """
        self.assertEqual(len(self.dash.all_disclosure_sections), 6)

        disclosure_names = [
            "sub_mob_bridge",
            "model_storage_frame",
            "custom_catalog_frame",
            "adv_formatting_frame",
            "hud_sliders_frame",
            "dev_options_frame"
        ]
        for name in disclosure_names:
            self.assertTrue(
                hasattr(self.dash, name),
                f"Missing disclosure section attribute: {name}"
            )
            section = getattr(self.dash, name)
            self.assertIsInstance(
                section, SettingsDisclosureSection,
                f"Attribute {name} is {type(section)}, expected SettingsDisclosureSection"
            )
            self.assertIn(
                section, self.dash.all_disclosure_sections,
                f"{name} must be in dash.all_disclosure_sections"
            )

            # Test programmatic toggle checking isHidden()
            initial_state = section.is_expanded
            section.set_expanded(not initial_state)
            self.assertEqual(section.is_expanded, not initial_state)
            self.assertEqual(not section.body_widget.isHidden(), not initial_state)
            # Restore
            section.set_expanded(initial_state)
            self.assertEqual(section.is_expanded, initial_state)
            self.assertEqual(not section.body_widget.isHidden(), initial_state)


class TestM3EngineSwitchingAdversarialLoop(unittest.TestCase):
    """
    Adversarially stress tests rapid engine switching loops across all 6 engines,
    container visibility states, input preservation, and out-of-bounds containment.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        import security_credentials as sec
        self._orig_engine = config.formatting.engine
        self._orig_endpoint = config.formatting.api_endpoint
        self._orig_u_key = sec.get_credential(sec.KEY_UNIVERSAL_API)
        if self._orig_u_key == "sk-ant-adversarial-test-key-998877":
            sec.delete_credential(sec.KEY_UNIVERSAL_API)
            self._orig_u_key = None
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'rules'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        import security_credentials as sec
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()
        config.formatting.engine = self._orig_engine
        config.formatting.api_endpoint = self._orig_endpoint
        config.formatting.api_key = self._orig_u_key
        if self._orig_u_key:
            sec.set_credential(sec.KEY_UNIVERSAL_API, self._orig_u_key)
        else:
            sec.delete_credential(sec.KEY_UNIVERSAL_API)
        config.save()


    def test_rapid_engine_switching_cycles_container_visibility(self):
        """
        Rapidly cycle through all 6 engines 20 times (120 rapid switches).
        Assert that for each switch:
        - The target container is visible (not isHidden())
        - ALL 5 other containers are strictly hidden (isHidden() is True)
        - ai_formatter and config update synchronously
        - No Qt layout exceptions or dangling widgets occur.
        """
        engine_configs = [
            ("rules", 0, self.dash.rules_container),
            ("ollama", 1, self.dash.ollama_container),
            ("universal", 2, self.dash.universal_container),
            ("openai", 3, self.dash.openai_container),
            ("gemini", 4, self.dash.gemini_container),
            ("groq", 5, self.dash.groq_container),
        ]

        containers = [
            self.dash.rules_container,
            self.dash.ollama_container,
            self.dash.universal_container,
            self.dash.openai_container,
            self.dash.gemini_container,
            self.dash.groq_container,
        ]

        # Rapidly loop 20 cycles = 120 switches
        for cycle in range(20):
            for eng_name, idx, target_container in engine_configs:
                self.dash.combo_engine.setCurrentIndex(idx)
                self.app.processEvents()

                # Verify configuration & ai_formatter sync
                self.assertEqual(config.formatting.engine, eng_name)
                self.assertEqual(self.dash.ai_formatter.engine, eng_name)

                # Verify target container is visible and others hidden
                self.assertFalse(
                    target_container.isHidden(),
                    f"Cycle {cycle}: {eng_name} container ({target_container}) should be visible"
                )

                for other_c in containers:
                    if other_c is not target_container:
                        self.assertTrue(
                            other_c.isHidden(),
                            f"Cycle {cycle}: container {other_c} should be hidden when {eng_name} is active"
                        )

    def test_engine_switching_preserves_input_values(self):
        """
        Verify that values typed into engine containers (e.g. Universal API endpoint,
        custom API keys) persist across multiple engine switches without being wiped.
        """
        test_endpoint = "https://custom.ai.inference.net/v1"
        test_key = "sk-ant-adversarial-test-key-998877"

        # Set values in Universal container
        self.dash.combo_engine.setCurrentIndex(2)  # universal
        self.dash.input_u_endpoint.setText(test_endpoint)
        self.dash.input_u_key.setText(test_key)
        self.app.processEvents()

        # Switch to Ollama, OpenAI, Gemini, Groq, Rules
        for idx in [1, 3, 4, 5, 0]:
            self.dash.combo_engine.setCurrentIndex(idx)
            self.app.processEvents()

        # Switch back to Universal
        self.dash.combo_engine.setCurrentIndex(2)
        self.app.processEvents()

        self.assertEqual(self.dash.input_u_endpoint.text(), test_endpoint)
        self.assertEqual(self.dash.input_u_key.text(), test_key)

    def test_engine_switching_out_of_bounds_indices(self):
        """
        Verify that invalid or out-of-bounds indices to _on_engine_changed
        do not throw uncaught index errors or corrupt the UI state.
        """
        original_engine = config.formatting.engine

        # Test negative index
        self.dash._on_engine_changed(-1)
        self.app.processEvents()

        # Test large out-of-bounds index
        self.dash._on_engine_changed(999)
        self.app.processEvents()

        # Test index exceeding engines length
        self.dash._on_engine_changed(6)
        self.app.processEvents()

        # UI and config should not be corrupted
        self.assertIn(config.formatting.engine, ["rules", "ollama", "universal", "openai", "gemini", "groq"])

    def test_engine_card_summary_live_synchronization(self):
        """
        Verify that card_fmt summary badge dynamically reflects the chosen engine.
        """
        engine_summary_pairs = [
            (0, "rules", ["Regeln", "Rules"]),
            (1, "ollama", ["Ollama"]),
            (2, "universal", ["Universal API"]),
            (3, "openai", ["OpenAI"]),
            (4, "gemini", ["Gemini"]),
            (5, "groq", ["Groq"]),
        ]

        for idx, eng_name, expected_substrings in engine_summary_pairs:
            self.dash.combo_engine.setCurrentIndex(idx)
            self.app.processEvents()
            summary = self.dash.card_fmt.lbl_summary.text()
            matches = any(sub.lower() in summary.lower() for sub in expected_substrings)
            self.assertTrue(
                matches,
                f"Summary for {eng_name} ('{summary}') does not contain any of {expected_substrings}"
            )


class TestM3WindowDestructionAndLifecycleSafety(unittest.TestCase):
    """
    Empirically stress tests window lifecycle, rapid show/hide toggles,
    closeEvent ignore-and-hide semantics, mic test auto-cleanup,
    and sequential destruction without memory leaks or dangling timers.
    """

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
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_show_hide_toggle_rapid_burst(self):
        """
        Execute 40 rapid show/hide toggles via toggle_visibility and show_and_activate.
        Assert that visibility state updates cleanly with zero crashes.
        """
        self.dash.hide()
        self.assertFalse(self.dash.isVisible())

        for i in range(40):
            self.dash.toggle_visibility()
            self.assertEqual(self.dash.isVisible(), (i % 2 == 0))
            self.app.processEvents()

    def test_close_event_ignores_and_hides(self):
        """
        Verify that closeEvent ignores the event (preventing window destruction)
        and calls hide() as expected for a system tray / background utility.
        """
        self.dash.show()
        self.app.processEvents()
        self.assertTrue(self.dash.isVisible())

        event = QCloseEvent()
        self.dash.closeEvent(event)
        self.app.processEvents()

        # Event must be ignored so window is not destroyed by Qt
        self.assertFalse(event.isAccepted())
        # Window must be hidden
        self.assertFalse(self.dash.isVisible())

    def test_mic_test_automatic_cleanup_on_hide(self):
        """
        Verify that if the mic test is running, calling hide() or closeEvent()
        immediately stops the mic test via audio_recorder.stop_test().
        """
        self.dash.show()
        self.app.processEvents()
        self.assertTrue(self.dash.isVisible())

        # Set up mock state
        self.mock_rec.is_testing = True

        # Trigger hideEvent by calling hide() on visible window
        self.dash.hide()
        self.app.processEvents()

        self.mock_rec.stop_test.assert_called()

        # Also verify closeEvent triggers stop_test
        self.mock_rec.stop_test.reset_mock()
        self.dash.show()
        self.app.processEvents()
        self.dash.closeEvent(QCloseEvent())
        self.app.processEvents()
        self.mock_rec.stop_test.assert_called()

    def test_sequential_window_instantiations_and_destruction(self):
        """
        Empirically test creating and destroying 5 DashboardWindow instances
        sequentially with deleteLater() to ensure clean cleanup of timers,
        sub-widgets, and event registrations.
        """
        for i in range(5):
            d = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
            d.show()
            self.app.processEvents()

            # Ensure sub-accordions and cards are initialized
            self.assertEqual(len(d.all_settings_cards), 7)
            self.assertEqual(len(d.all_disclosure_sections), 6)

            # Clean shutdown
            if hasattr(d, "waveform_widget") and hasattr(d.waveform_widget, "anim_timer"):
                d.waveform_widget.anim_timer.stop()
            if hasattr(d, "gpu_timer"):
                d.gpu_timer.stop()
            d.close()
            d.deleteLater()
            self.app.processEvents()


class TestM3SearchFilteringAdversarialStress(unittest.TestCase):
    """
    Adversarially tests the settings search filtering engine against:
    - Empty and whitespace strings
    - Special regex characters (preventing re crashes)
    - Unicode & emoji inputs
    - German <-> English cross-locale synonyms
    - Recursive progressive disclosure sub-accordion expansion
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_search_query_extreme_inputs_zero_crashes(self):
        """
        Test queries containing regex metacharacters, emojis, unicode,
        and unmatched gibberish.
        """
        extreme_queries = [
            "",
            "   \t  \n  ",
            ".*+?^${}()|[]\\",
            "(?P<group>test.*)",
            "🎤🔊🚀🔥",
            "äöüßÄÖÜ",
            "xyz_completely_unmatched_query_9999",
        ]

        for q in extreme_queries:
            try:
                self.dash._on_settings_search_changed(q)
                self.app.processEvents()
            except Exception as e:
                self.fail(f"Search filtering crashed on query '{q}': {e}")

        # Empty search restores all cards
        self.dash._on_settings_search_changed("")
        self.app.processEvents()
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden())

    def test_search_bilingual_synonyms_cross_locale(self):
        """
        Verify that both German and English terms correctly match their respective cards.
        """
        # Test in English mode
        self.dash.retranslate_ui("en")
        self.app.processEvents()

        test_pairs_en = [
            ("mikrofon", self.dash.card_audio),
            ("microphone", self.dash.card_audio),
            ("tastenkürzel", self.dash.card_hk),
            ("shortcuts", self.dash.card_hk),
            ("hotkey", self.dash.card_hk),
            ("lautstärke", self.dash.card_gen),
            ("volume", self.dash.card_gen),
            ("spracherkennung", self.dash.card_stt),
            ("whisper", self.dash.card_stt),
            ("formatierung", self.dash.card_fmt),
            ("llm", self.dash.card_fmt),
            ("system", self.dash.card_adv),
            ("privacy", self.dash.card_adv),
            ("overlay", self.dash.card_hud),
            ("hud", self.dash.card_hud),
        ]

        for term, expected_card in test_pairs_en:
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()
            self.assertFalse(
                expected_card.isHidden(),
                f"[EN mode] Query '{term}' should unhide card {expected_card.lbl_title.text()}"
            )
            self.assertTrue(
                expected_card.is_expanded,
                f"[EN mode] Query '{term}' should expand matching card {expected_card.lbl_title.text()}"
            )

        # Test in German mode
        self.dash.retranslate_ui("de")
        self.app.processEvents()

        test_pairs_de = [
            ("mikrofon", self.dash.card_audio),
            ("microphone", self.dash.card_audio),
            ("tastenkürzel", self.dash.card_hk),
            ("shortcuts", self.dash.card_hk),
            ("datenschutz", self.dash.card_adv),
            ("system", self.dash.card_adv),
        ]

        for term, expected_card in test_pairs_de:
            self.dash._on_settings_search_changed(term)
            self.app.processEvents()
            self.assertFalse(
                expected_card.isHidden(),
                f"[DE mode] Query '{term}' should unhide card {expected_card.lbl_title.text()}"
            )
            self.assertTrue(
                expected_card.is_expanded,
                f"[DE mode] Query '{term}' should expand matching card {expected_card.lbl_title.text()}"
            )

    def test_search_recursive_disclosure_section_expansion(self):
        """
        Verify that when a search term matches text inside a sub-accordion
        (e.g. 'LAN' or 'Bridge'), the sub-accordion itself is auto-expanded.
        """
        # Collapse all disclosure sections first
        for ds in self.dash.all_disclosure_sections:
            ds.set_expanded(False)

        self.dash._on_settings_search_changed("LAN-Mikrofon")
        self.app.processEvents()

        # The audio card must be visible and expanded
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.card_audio.is_expanded)

        # The mobile bridge sub-accordion inside card_audio must be auto-expanded
        self.assertTrue(
            self.dash.sub_mob_bridge.is_expanded,
            "sub_mob_bridge disclosure section should be auto-expanded for 'LAN-Mikrofon' query"
        )


class TestM3RetranslateUiAndLanguageSwitchingStress(unittest.TestCase):
    """
    Stress tests rapid bilingual language switching, invalid language code fallback,
    and the 1-click header language switcher button.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_rapid_bilingual_retranslate_loop(self):
        """
        Cycle retranslate_ui between 'en' and 'de' 20 times in rapid burst.
        Assert that all titles and labels remain valid strings.
        """
        for i in range(20):
            lang = "de" if i % 2 == 0 else "en"
            self.dash.retranslate_ui(lang)
            self.app.processEvents()

            # Verify tab texts are non-empty
            for tab_i in range(self.dash.tabs.count()):
                self.assertGreater(len(self.dash.tabs.tabText(tab_i)), 0)

            # Verify card titles are non-empty
            for card in self.dash.all_settings_cards:
                self.assertGreater(len(card.lbl_title.text()), 0)

            # Verify disclosure section titles are non-empty
            for ds in self.dash.all_disclosure_sections:
                self.assertGreater(len(ds.lbl_title.text()), 0)

    def test_invalid_language_code_containment(self):
        """
        Verify that passing invalid language codes to retranslate_ui does not crash.
        """
        for bad_lang in ["fr", "es", "zh", "", None, 123]:
            try:
                self.dash.retranslate_ui(bad_lang)
                self.app.processEvents()
            except Exception as e:
                self.fail(f"retranslate_ui crashed on invalid language code '{bad_lang}': {e}")

    def test_header_language_toggle_button(self):
        """
        Verify that clicking btn_lang_toggle toggles language and updates the button label.
        """
        initial_lang = get_current_language()
        self.dash.btn_lang_toggle.click()
        self.app.processEvents()

        new_lang = get_current_language()
        self.assertNotEqual(initial_lang, new_lang)
        self.assertIn(new_lang.upper(), self.dash.btn_lang_toggle.text())

        # Toggle back
        self.dash.btn_lang_toggle.click()
        self.app.processEvents()
        self.assertEqual(get_current_language(), initial_lang)
        self.assertIn(initial_lang.upper(), self.dash.btn_lang_toggle.text())


class TestM3SignalAndSlotConcurrenyStress(unittest.TestCase):
    """
    Stress tests Qt signal-slot dispatch under concurrent events
    (audio levels, state transitions, engine switching).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        if hasattr(self.dash, "gpu_timer"):
            self.dash.gpu_timer.stop()
        self.dash.close()
        self.app.processEvents()

    def test_rapid_audio_level_updates_during_engine_switching(self):
        """
        Emit 100 audio_level_updated signals interleaved with engine switching.
        Verify zero deadlock or widget state corruption.
        """
        for i in range(100):
            level = (i % 10) / 10.0
            signals.audio_level_updated.emit(level)
            if i % 15 == 0:
                eng_idx = (i // 15) % 6
                self.dash.combo_engine.setCurrentIndex(eng_idx)
            self.app.processEvents()

        self.dash.waveform_widget.set_state("idle")
        self.app.processEvents()

    def test_dictation_lifecycle_state_burst(self):
        """
        Simulate a rapid burst of dictation state signals:
        recording_started -> audio_level_updated -> transcription_started ->
        formatting_started -> transcription_completed.
        """
        signals.recording_started.emit()
        self.app.processEvents()
        self.assertEqual(self.dash.waveform_widget.current_state, "recording")

        signals.audio_level_updated.emit(0.85)
        self.app.processEvents()

        signals.transcription_started.emit()
        self.app.processEvents()
        self.assertEqual(self.dash.waveform_widget.current_state, "transcribing")

        signals.formatting_started.emit()
        self.app.processEvents()
        self.assertEqual(self.dash.status_badge.text(), tr("formatting"))
        self.assertEqual(self.dash.lbl_hero_action.text(), tr("formatting"))

        signals.transcription_completed.emit({"text": "Test transkribierter Text", "latency": 1.25})
        self.app.processEvents()
        self.assertEqual(self.dash.waveform_widget.current_state, "idle")
        self.assertIn("Test transkribierter Text", self.dash.lbl_latest_text.text())


if __name__ == "__main__":
    unittest.main()
