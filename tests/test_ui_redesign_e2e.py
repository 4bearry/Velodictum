#!/usr/bin/env python3
"""
Velodictum UI Redesign - Comprehensive 4-Tier E2E Test Suite
=============================================================
Strictly verifies the interface contracts, boundary resilience,
cross-feature combinations, and real-world dictation workflows
for the Windows 11 Fluent & Dark Glassmorphism UI redesign.

Tiers:
- Tier 1: Feature Coverage & Interface Contracts
- Tier 2: Boundary & Corner Cases
- Tier 3: Cross-Feature Combinations
- Tier 4: Real-World Workload Scenarios
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Configure headless offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure core and project root are in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(1, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
import pyperclip

from config import config
from i18n import tr, set_current_language, get_current_language
from gui.signals import signals, get_signals
import gui.theme as theme
from gui.dashboard_window import DashboardWindow, HeroWaveformWidget
from gui.floating_hud import FloatingHUD
from gui.scratchpad_window import ScratchpadWindow


def get_qapp():
    """Returns or initializes the offscreen QApplication instance."""
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


# =========================================================================
# Tier 1: Feature Coverage & Interface Contracts
# =========================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 tests verify syntax compilation, clean imports, centralized theme tokens,
    valid stylesheet generation, polymorphic window backdrop application,
    offscreen window instantiations, HUD 6-state lifecycle support, scratchpad
    toolbar actions, and dashboard tab/card preservation.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = None
        self.hud = None
        self.pad = None

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        if self.hud:
            if hasattr(self.hud, "anim_timer"):
                self.hud.anim_timer.stop()
            if hasattr(self.hud, "hide_timer"):
                self.hud.hide_timer.stop()
            self.hud.close()
        if self.pad:
            self.pad.close()
        self.app.processEvents()

    def test_syntax_compilation_and_clean_import(self):
        """Verify all GUI and entrypoint modules import cleanly without exceptions."""
        import importlib
        modules_to_test = [
            "gui.theme",
            "gui.signals",
            "gui.floating_hud",
            "gui.scratchpad_window",
            "gui.dashboard_window",
            "gui.language_dialog",
            "main",
        ]
        for mod_name in modules_to_test:
            try:
                mod = importlib.import_module(mod_name)
                self.assertIsNotNone(mod, f"Module '{mod_name}' loaded as None")
            except Exception as e:
                self.fail(f"Module '{mod_name}' failed clean import: {e}")

    def test_theme_tokens_contract(self):
        """
        Verify Centralized Theme Tokens contract in gui/theme.py (PROJECT.md Feature 1):
        ThemeColors, ThemeTypography, and ThemeMetrics must exist and provide design constants.
        """
        self.assertTrue(
            hasattr(theme, "ThemeColors"),
            "Contract Violation: 'ThemeColors' class missing in gui/theme.py (PROJECT.md Feature 1)"
        )
        self.assertTrue(
            hasattr(theme, "ThemeTypography"),
            "Contract Violation: 'ThemeTypography' class missing in gui/theme.py (PROJECT.md Feature 1)"
        )
        self.assertTrue(
            hasattr(theme, "ThemeMetrics"),
            "Contract Violation: 'ThemeMetrics' class missing in gui/theme.py (PROJECT.md Feature 1)"
        )

        # Verify key token values if classes are present
        if hasattr(theme, "ThemeColors"):
            for color_token in ["BG_CANVAS", "BG_CARD", "BORDER_SPECULAR", "ACCENT_PRIMARY"]:
                self.assertTrue(
                    hasattr(theme.ThemeColors, color_token),
                    f"ThemeColors missing required token '{color_token}'"
                )

        if hasattr(theme, "ThemeTypography"):
            self.assertTrue(
                hasattr(theme.ThemeTypography, "FONT_FAMILY_PRIMARY"),
                "ThemeTypography missing 'FONT_FAMILY_PRIMARY'"
            )
            self.assertIn("Segoe UI", getattr(theme.ThemeTypography, "FONT_FAMILY_PRIMARY", ""))

        if hasattr(theme, "ThemeMetrics"):
            self.assertTrue(
                hasattr(theme.ThemeMetrics, "RADIUS_CARD"),
                "ThemeMetrics missing 'RADIUS_CARD'"
            )

    def test_stylesheet_validity_and_selectors(self):
        """
        Verify get_stylesheet() returns a valid Fluent Dark Glass stylesheet
        covering essential Qt widgets (PROJECT.md Feature 2).
        """
        qss = theme.get_stylesheet()
        self.assertIsInstance(qss, str, "get_stylesheet() must return a str")
        self.assertGreater(len(qss.strip()), 100, "Stylesheet content must be substantial")

        essential_selectors = [
            "QWidget",
            "QFrame",
            "QTabBar",
            "QPushButton",
            "QSlider",
            "QMenu",
            "QToolTip",
            "QTextEdit",
            "QScrollBar",
        ]
        for selector in essential_selectors:
            self.assertIn(
                selector, qss,
                f"Stylesheet missing essential Qt selector rule for '{selector}'"
            )

    def test_polymorphic_window_backdrop(self):
        """
        Verify apply_window_backdrop supports both int HWND and QWidget polymorphically
        without raising TypeError or unhandled exceptions (PROJECT.md Feature 4).
        """
        # Test with integer winId
        res_int = theme.apply_window_backdrop(0)
        self.assertIsInstance(res_int, bool, "apply_window_backdrop(int) must return bool")

        # Test with QWidget instance
        test_widget = QWidget()
        try:
            res_widget = theme.apply_window_backdrop(test_widget)
            self.assertIsInstance(
                res_widget, bool,
                "apply_window_backdrop(QWidget) must return bool"
            )
        except TypeError as e:
            self.fail(
                f"Contract Violation: apply_window_backdrop failed to accept QWidget target: {e}"
            )
        finally:
            test_widget.deleteLater()

    def test_window_instantiations_offscreen(self):
        """Verify DashboardWindow, FloatingHUD, and ScratchpadWindow instantiate offscreen."""
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

        self.assertIsInstance(self.dash, DashboardWindow)
        self.assertIsInstance(self.hud, FloatingHUD)
        self.assertIsInstance(self.pad, ScratchpadWindow)
        self.assertTrue(self.dash.isWidgetType())
        self.assertTrue(self.hud.isWidgetType())
        self.assertTrue(self.pad.isWidgetType())

    def test_hud_six_state_lifecycle_support(self):
        """
        Verify FloatingHUD supports full 6-state lifecycle via signals:
        recording, voice_edit, transcribing, formatting, done, error/blocked.
        """
        self.hud = FloatingHUD()

        # 1. Recording
        signals.recording_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "recording")

        # 2. Voice Edit
        signals.voice_edit_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "voice_edit")

        # 3. Transcribing
        signals.transcription_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "transcribing")

        # 4. Formatting (sub-state of transcribing with impulse)
        signals.formatting_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "transcribing")

        # 5. Done
        signals.transcription_completed.emit({
            "text": "Unit Test Transcription Completed",
            "latency": 0.15,
            "action": None
        })
        self.app.processEvents()
        self.assertEqual(self.hud.state, "done")
        self.assertIn("Unit Test", self.hud.status_text)

        # 6. Error (transcription failed, injection blocked, recording cancelled)
        signals.transcription_failed.emit("Network timeout")
        self.app.processEvents()
        self.assertEqual(self.hud.state, "error")

        signals.injection_blocked.emit("Protected password field")
        self.app.processEvents()
        self.assertEqual(self.hud.state, "error")

    def test_scratchpad_action_toolbar_and_attributes(self):
        """
        Verify ScratchpadWindow preserves all action toolbar buttons,
        text editor, live counter labels, and clean clearing.
        """
        self.pad = ScratchpadWindow(self.mock_fmt)

        required_attrs = [
            "btn_mic",
            "btn_structure",
            "btn_copy",
            "btn_clear",
            "text_edit",
            "title_lbl",
            "lbl_stats",
        ]
        for attr in required_attrs:
            self.assertTrue(
                hasattr(self.pad, attr),
                f"ScratchpadWindow missing required attribute '{attr}'"
            )

        # Verify clear button behavior
        self.pad.text_edit.setPlainText("Some scratchpad content to be cleared")
        self.assertEqual(self.pad.text_edit.toPlainText(), "Some scratchpad content to be cleared")
        self.pad.btn_clear.click()
        self.assertEqual(self.pad.text_edit.toPlainText(), "")

    def test_dashboard_tabs_and_seven_settings_cards_preservation(self):
        """
        Verify DashboardWindow preserves 3 navigation tabs, exactly 7 settings cards,
        and backward compatibility aliases (card_llm, card_sound, card_mob, card_sys).
        """
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

        # 3 Navigation Tabs
        self.assertTrue(hasattr(self.dash, "tabs"))
        self.assertGreaterEqual(self.dash.tabs.count(), 3)
        self.assertTrue(hasattr(self.dash, "tab_studio"))
        self.assertTrue(hasattr(self.dash, "tab_library"))
        self.assertTrue(hasattr(self.dash, "tab_settings"))

        # 7 Settings Cards
        self.assertEqual(
            len(self.dash.all_settings_cards), 7,
            "DashboardWindow must preserve exactly 7 settings cards"
        )

        # Compatibility Aliases
        self.assertEqual(self.dash.card_llm, self.dash.card_fmt)
        self.assertEqual(self.dash.card_sound, self.dash.card_gen)
        self.assertEqual(self.dash.card_mob, self.dash.card_audio)
        self.assertEqual(self.dash.card_sys, self.dash.card_adv)


# =========================================================================
# Tier 2: Boundary & Corner Cases
# =========================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 tests verify system resilience against edge conditions, extreme inputs,
    empty payloads, rapid signal bursts, invalid language codes, and extreme window bounds.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = None
        self.hud = None
        self.pad = None

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        if self.hud:
            if hasattr(self.hud, "anim_timer"):
                self.hud.anim_timer.stop()
            if hasattr(self.hud, "hide_timer"):
                self.hud.hide_timer.stop()
            self.hud.close()
        if self.pad:
            self.pad.close()
        self.app.processEvents()

    def test_empty_transcription_text_handling(self):
        """Verify empty transcription payload ({'text': ''}) handles gracefully without crashing."""
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

        signals.recording_started.emit()
        signals.transcription_completed.emit({
            "text": "",
            "latency": 0.05,
            "duration": 0.0
        })
        self.app.processEvents()

        # HUD should transition to done with fallback label (hud_done), not crash or display empty
        self.assertEqual(self.hud.state, "done")
        self.assertTrue(len(self.hud.status_text) > 0)

        # Pad stats should handle empty text gracefully
        self.pad.text_edit.setPlainText("")
        self.pad._update_stats()
        self.assertIn("0", self.pad.lbl_stats.text())

    def test_extreme_audio_levels_clipping(self):
        """
        Verify extreme audio RMS values (negative and > 1.0) are safely clamped
        without NaN, overflow, or mathematical exceptions in HUD and Dashboard waveform.
        """
        self.hud = FloatingHUD()
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

        extreme_levels = [-100.0, -1.0, -0.001, 0.0, 0.5, 1.0, 1.5, 100.0, 9999.0]
        for rms in extreme_levels:
            # HUD audio level handling
            self.hud.on_audio_level(rms)
            self.assertFalse(
                float("-inf") == self.hud.target_rms or float("inf") == self.hud.target_rms,
                f"HUD target_rms became infinite with rms={rms}"
            )
            self.assertLessEqual(
                self.hud.target_rms, 1.0,
                f"HUD target_rms must be clamped <= 1.0 for rms={rms}"
            )

            # Dashboard waveform level handling
            if hasattr(self.dash, "waveform_widget"):
                self.dash.waveform_widget.set_level(rms)
                self.assertLessEqual(
                    self.dash.waveform_widget.target_rms, 1.0,
                    f"Waveform target_rms must be clamped <= 1.0 for rms={rms}"
                )

    def test_rapid_state_transitions_burst(self):
        """
        Verify system resilience when firing rapid bursts of conflicting signals
        without state desynchronization, unhandled exceptions, or deadlocks.
        """
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

        for i in range(25):
            signals.recording_started.emit()
            signals.audio_level_updated.emit(0.25)
            signals.recording_stopped.emit()
            signals.transcription_started.emit()
            signals.formatting_started.emit()
            signals.voice_edit_started.emit()
            signals.transcription_failed.emit(f"Error burst {i}")
            signals.recording_cancelled.emit()
            self.app.processEvents()

        # At the end of the burst, HUD must remain alive and responsive in a valid terminal state
        self.assertIn(self.hud.state, ["error", "cancelled"])
        signals.recording_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "recording")

    def test_invalid_language_code_fallback(self):
        """
        Verify retranslate_ui handles invalid language codes or None gracefully
        by falling back safely without unhandled KeyError or crash.
        """
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.pad = ScratchpadWindow(self.mock_fmt)
        self.hud = FloatingHUD()

        invalid_codes = ["invalid_xyz", "", "12345", None]
        for code in invalid_codes:
            # DashboardWindow retranslate fallback
            try:
                self.dash.retranslate_ui(code)
            except Exception as e:
                self.fail(f"DashboardWindow.retranslate_ui crashed on invalid code '{code}': {e}")

            # ScratchpadWindow retranslate fallback
            try:
                self.pad.retranslate_ui(code)
            except Exception as e:
                self.fail(f"ScratchpadWindow.retranslate_ui crashed on invalid code '{code}': {e}")

            # FloatingHUD retranslate fallback (PROJECT.md Feature 7)
            self.assertTrue(
                hasattr(self.hud, "retranslate_ui"),
                "Contract Violation: 'retranslate_ui' method missing on FloatingHUD (PROJECT.md Feature 7)"
            )
            try:
                self.hud.retranslate_ui(code)
            except Exception as e:
                self.fail(f"FloatingHUD.retranslate_ui crashed on invalid code '{code}': {e}")

    def test_window_resizing_bounds(self):
        """
        Verify ScratchpadWindow and DashboardWindow behave correctly when resized
        to minimum constraints and large desktop bounds.
        """
        self.pad = ScratchpadWindow(self.mock_fmt)
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

        # Scratchpad minimum bounds
        self.pad.resize(100, 100)  # Attempt below minimum (420 x 380)
        self.app.processEvents()
        self.assertGreaterEqual(self.pad.width(), 420)
        self.assertGreaterEqual(self.pad.height(), 380)

        # Scratchpad extreme size
        self.pad.resize(1920, 1080)
        self.app.processEvents()
        self.assertEqual(self.pad.width(), 1920)
        self.assertEqual(self.pad.height(), 1080)

        # Dashboard resizing
        self.dash.resize(900, 600)
        self.app.processEvents()
        self.assertEqual(self.dash.width(), 900)
        self.dash.resize(1600, 900)
        self.app.processEvents()
        self.assertEqual(self.dash.width(), 1600)

    def test_search_filtering_edge_cases(self):
        """
        Verify settings search filtering handles empty strings, regex meta-characters,
        non-matching tokens, and case insensitivity safely.
        """
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

        # 1. Regex meta-characters should not throw regex syntax errors
        meta_queries = ["[", "*.*", "(?=", "]+", "{1,3}", "\\", "^$"]
        for query in meta_queries:
            try:
                self.dash._on_settings_search_changed(query)
            except Exception as e:
                self.fail(f"Search filtering crashed on regex meta-character '{query}': {e}")

        # 2. Non-matching query should hide cards
        self.dash._on_settings_search_changed("nonexistent_setting_token_9999")
        visible_cards = [c for c in self.dash.all_settings_cards if not c.isHidden()]
        self.assertEqual(len(visible_cards), 0, "No cards should be visible for non-matching query")

        # 3. Empty query should unhide all cards
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden(), "All cards should be visible when search is empty")

        # 4. Case-insensitivity: 'mikrofon' vs 'MIKROFON'
        self.dash._on_settings_search_changed("mikrofon")
        self.assertFalse(self.dash.card_audio.isHidden())
        self.dash._on_settings_search_changed("MIKROFON")
        self.assertFalse(self.dash.card_audio.isHidden())


# =========================================================================
# Tier 3: Cross-Feature Combinations
# =========================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3 tests verify pairwise and multi-feature interactions:
    signal-slot roundtrips under an active custom theme, simultaneous bilingual
    retranslation across all 3 windows, and accordion expansion under active search queries.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = None
        self.hud = None
        self.pad = None

    def tearDown(self):
        if self.dash:
            if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
                self.dash.waveform_widget.anim_timer.stop()
            self.dash.close()
        if self.hud:
            if hasattr(self.hud, "anim_timer"):
                self.hud.anim_timer.stop()
            if hasattr(self.hud, "hide_timer"):
                self.hud.hide_timer.stop()
            self.hud.close()
        if self.pad:
            self.pad.close()
        self.app.setStyleSheet("")
        self.app.processEvents()

    def test_signal_slot_roundtrip_with_custom_theme_active(self):
        """
        Verify that applying the full Fluent Dark Glass stylesheet to the application
        does not interfere with signal-slot event delivery across all windows.
        """
        # Apply theme stylesheet globally
        qss = theme.get_stylesheet()
        self.app.setStyleSheet(qss)

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

        # Trigger recording start
        signals.recording_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "recording")

        # Stream audio level
        signals.audio_level_updated.emit(0.35)
        self.app.processEvents()
        self.assertAlmostEqual(self.hud.target_rms, min(1.0, 0.35 * 14.0), places=2)

        # Trigger completion
        signals.transcription_completed.emit({
            "text": "Styled Signal Roundtrip Passed",
            "latency": 0.12,
            "action": None
        })
        self.app.processEvents()
        self.assertEqual(self.hud.state, "done")

    def test_simultaneous_bilingual_toggle_across_all_windows(self):
        """
        Verify simultaneous language toggling ('de' <-> 'en') updates texts
        consistently across DashboardWindow, ScratchpadWindow, and FloatingHUD.
        """
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.pad = ScratchpadWindow(self.mock_fmt)
        self.hud = FloatingHUD()

        # Switch to German ('de')
        set_current_language("de")
        self.dash.retranslate_ui("de")
        self.pad.retranslate_ui("de")
        self.assertTrue(
            hasattr(self.hud, "retranslate_ui"),
            "Contract Violation: 'retranslate_ui' missing on FloatingHUD"
        )
        self.hud.retranslate_ui("de")

        # German verifications
        self.assertIn("Einstellungen", self.dash.tabs.tabText(2))
        self.assertIn("Bereit", self.dash.lbl_hero_action.text())
        self.assertIn("Notiz", self.pad.btn_copy.text())

        # Switch to English ('en')
        set_current_language("en")
        self.dash.retranslate_ui("en")
        self.pad.retranslate_ui("en")
        self.hud.retranslate_ui("en")

        # English verifications
        self.assertIn("Settings", self.dash.tabs.tabText(2))
        self.assertIn("Ready", self.dash.lbl_hero_action.text())
        self.assertIn("Copy", self.pad.btn_copy.text())

    def test_settings_accordion_expansion_with_active_search_filter(self):
        """
        Verify that invoking _expand_all_settings and _collapse_all_settings while
        a search filter is active operates correctly on matching cards and preserves
        state upon clearing search.
        """
        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)

        # Search for Audio settings
        self.dash._on_settings_search_changed("Mikrofon")
        self.assertFalse(self.dash.card_audio.isHidden())
        self.assertTrue(self.dash.card_audio.is_expanded)

        # Collapse all while filtered
        self.dash._collapse_all_settings()
        self.assertFalse(self.dash.card_audio.is_expanded)

        # Expand all while filtered
        self.dash._expand_all_settings()
        self.assertTrue(self.dash.card_audio.is_expanded)

        # Clear search filter
        self.dash._on_settings_search_changed("")
        for card in self.dash.all_settings_cards:
            self.assertFalse(card.isHidden(), "All cards should return to visible on clear")


# =========================================================================
# Tier 4: Real-World Workload Scenarios
# =========================================================================

class TestTier4RealWorldWorkloadScenarios(unittest.TestCase):
    """
    Tier 4 tests execute an end-to-end user dictation workflow:
    Trigger -> Recording Start -> Audio Level Streaming -> Recording Stop ->
    Whisper Transcription -> AI Formatting -> Scratchpad Append ->
    Clipboard Copy -> HUD Status & Auto-Hide Dismissal.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        self.mock_rec = MagicMock()
        self.mock_rec.list_devices.return_value = [{'id': 0, 'name': 'Standard-Mikrofon'}]
        self.mock_stt = MagicMock()
        self.mock_stt.model_size = 'de_max'
        self.mock_fmt = MagicMock()
        self.mock_fmt.engine = 'universal'

        self.dash = DashboardWindow(self.mock_rec, self.mock_stt, self.mock_fmt)
        self.hud = FloatingHUD()
        self.pad = ScratchpadWindow(self.mock_fmt)

    def tearDown(self):
        if hasattr(self.dash, "waveform_widget") and hasattr(self.dash.waveform_widget, "anim_timer"):
            self.dash.waveform_widget.anim_timer.stop()
        self.dash.close()

        if hasattr(self.hud, "anim_timer"):
            self.hud.anim_timer.stop()
        if hasattr(self.hud, "hide_timer"):
            self.hud.hide_timer.stop()
        self.hud.close()

        self.pad.close()
        self.app.processEvents()

    def test_complete_dictation_lifecycle_end_to_end(self):
        """
        Executes a complete, realistic user dictation lifecycle from trigger to clipboard copy.
        """
        # Step 1: User triggers dictation from Scratchpad
        self.pad._recording_triggered_by_pad = True
        self.pad._recording_active_in_pad = True

        # Step 2: Audio recorder signals recording started
        signals.recording_started.emit()
        self.app.processEvents()

        self.assertEqual(self.hud.state, "recording")
        self.assertTrue(self.pad._recording_active_in_pad)
        self.assertEqual(self.pad.btn_mic.text(), tr("btn_dictate_recording"))

        # Step 3: Audio level streaming (simulating voice utterance)
        voice_rms_stream = [0.03, 0.08, 0.22, 0.55, 0.68, 0.34, 0.12, 0.04]
        for rms in voice_rms_stream:
            signals.audio_level_updated.emit(rms)
            self.app.processEvents()
            self.assertGreater(self.hud.target_rms, 0.0)

        # Step 4: User finishes speaking; recording stops
        signals.recording_stopped.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "transcribing")

        # Step 5: STT Engine processes speech
        signals.transcription_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "transcribing")

        # Step 6: AI Formatter processes text
        signals.formatting_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "transcribing")

        # Step 7: Final formatted transcription payload arrives
        test_transcript = "Velodictum delivers instant speech-to-text dictation with AI formatting."
        transcription_payload = {
            "text": test_transcript,
            "duration": 2.45,
            "latency": 0.18,
            "language": "en",
            "action": None
        }
        signals.transcription_completed.emit(transcription_payload)
        self.app.processEvents()

        # Step 8: HUD transitions to 'done' state with latency notice
        self.assertEqual(self.hud.state, "done")
        self.assertIn("Velodictum", self.hud.status_text)
        self.assertTrue(self.hud.hide_timer.isActive())

        # Step 9: Scratchpad appends the text and updates live word & character stats
        self.pad.text_edit.setPlainText(test_transcript)
        self.pad._update_stats()
        expected_words = len(test_transcript.strip().split())
        self.assertIn(str(expected_words), self.pad.lbl_stats.text())
        self.assertIn(str(len(test_transcript.strip())), self.pad.lbl_stats.text())

        # Step 10: User copies note to clipboard
        with patch.object(pyperclip, "copy") as mock_copy:
            self.pad._copy_to_clipboard()
            mock_copy.assert_called_once_with(test_transcript)
            self.assertIn(tr("copied"), self.pad.btn_copy.text())

        # Step 11: HUD auto-hide triggers dismiss
        self.hud.hide_timer.stop()
        self.hud.hide_hud()
        self.app.processEvents()
        self.assertEqual(self.hud.target_opacity, 0.0)


if __name__ == "__main__":
    unittest.main()
