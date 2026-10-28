"""
Empirical Stress Test Suite for FloatingHUD (gui/floating_hud.py)

Testing:
1. Audio level clipping with extreme values (-100, -1, 0, 1, 100, NaN, Inf, -Inf).
   Verifies: no negative bar heights, no crash, no NaN propagation, valid paintEvent execution.
2. Rapid state transition bursts in tight loops (1000+ iterations).
   Verifies: memory stability, widget stability, no paint exceptions, responsive recovery.
3. Animation timer dormancy verification.
   Verifies: anim_timer.isActive() is False after HUD settles into hidden state across
   all bounce settings and with fluid_animations True/False.
"""

import gc
import math
import os
import sys
import time
import unittest

# Ensure base dir and core are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
CORE_DIR = os.path.join(BASE_DIR, "core")
if os.path.exists(CORE_DIR) and CORE_DIR not in sys.path:
    sys.path.insert(1, CORE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt

from config import config
from gui.signals import signals
from gui.floating_hud import FloatingHUD


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])
    return app


class TestFloatingHUDStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def setUp(self):
        # Reset config to defaults
        config.hud.enabled = True
        config.hud.minimal_mode = False
        config.hud.fluid_animations = True
        config.hud.bounce_intensity = 50
        self.hud = FloatingHUD()

    def tearDown(self):
        if self.hud:
            if hasattr(self.hud, "anim_timer"):
                self.hud.anim_timer.stop()
            if hasattr(self.hud, "hide_timer"):
                self.hud.hide_timer.stop()
            self.hud.close()
            self.hud.deleteLater()
            self.hud = None
        self.app.processEvents()

    def _render_hud(self):
        """Forces an actual paint event offscreen to catch any rendering crashes."""
        pixmap = QPixmap(self.hud.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        self.hud.render(pixmap)
        return pixmap

    # =========================================================================
    # Test 1: Audio Level Clipping and Robustness
    # =========================================================================

    def test_audio_level_extreme_values(self):
        """
        Verify extreme and non-finite RMS audio values are safely clamped,
        cause no NaN propagation, produce non-negative bar heights,
        and do not crash the painting pipeline.
        """
        extreme_rms_values = [
            -100.0,
            -1.0,
            -0.5,
            -1e-6,
            0.0,
            1e-6,
            0.5,
            1.0,
            1.5,
            10.0,
            100.0,
            1000.0,
            float("nan"),
            float("inf"),
            float("-inf"),
            float("-nan") if hasattr(math, "nan") else -float("nan"),
        ]

        self.hud.on_recording_started()
        self.app.processEvents()

        for mode in [False, True]:  # Standard and Minimal mode
            config.hud.minimal_mode = mode

            for rms in extreme_rms_values:
                # 1. Feed audio level
                self.hud.on_audio_level(rms)

                # 2. Check target_rms bounds
                self.assertFalse(math.isnan(self.hud.target_rms), f"target_rms is NaN for input {rms}")
                self.assertFalse(math.isinf(self.hud.target_rms), f"target_rms is Inf for input {rms}")
                self.assertGreaterEqual(self.hud.target_rms, 0.0, f"target_rms < 0 for input {rms}")
                self.assertLessEqual(self.hud.target_rms, 1.0, f"target_rms > 1.0 for input {rms}")

                # 3. Simulate multiple animation frames
                for _ in range(15):
                    self.hud._update_animation()

                # 4. Check current_rms and bar_heights
                self.assertFalse(math.isnan(self.hud.current_rms), f"current_rms is NaN for input {rms}")
                self.assertFalse(math.isinf(self.hud.current_rms), f"current_rms is Inf for input {rms}")
                self.assertGreaterEqual(self.hud.current_rms, 0.0, f"current_rms < 0 for input {rms}")
                self.assertLessEqual(self.hud.current_rms, 1.0, f"current_rms > 1.0 for input {rms}")

                for i, h in enumerate(self.hud.bar_heights):
                    self.assertFalse(math.isnan(h), f"bar_heights[{i}] is NaN for input {rms}")
                    self.assertFalse(math.isinf(h), f"bar_heights[{i}] is Inf for input {rms}")
                    self.assertGreaterEqual(h, 0.0, f"bar_heights[{i}] is negative ({h}) for input {rms}")
                    self.assertLessEqual(h, 1.0, f"bar_heights[{i}] exceeded 1.0 ({h}) for input {rms}")

                # 5. Render HUD to exercise paintEvent with these bar heights
                try:
                    self._render_hud()
                except Exception as e:
                    self.fail(f"paintEvent crashed for rms={rms} (minimal_mode={mode}): {e}")

    # =========================================================================
    # Test 2: Rapid State Transition Bursts
    # =========================================================================

    def test_rapid_state_transitions_burst_intense(self):
        """
        Stress-test rapid signal sequences in tight loops (1000 iterations).
        Verifies:
        - No unhandled exceptions or desynchronization
        - Paint pipeline survives at each intermediate state
        - Memory stability (no runaway leaks)
        - Final responsive state
        """
        import tracemalloc
        tracemalloc.start()
        gc.collect()

        def get_mem_bytes():
            try:
                import ctypes
                from ctypes import wintypes
                class PMC(ctypes.Structure):
                    _fields_ = [
                        ('cb', wintypes.DWORD),
                        ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t),
                    ]
                pmc = PMC()
                pmc.cb = ctypes.sizeof(PMC)
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb)
                return pmc.WorkingSetSize
            except Exception:
                return tracemalloc.get_traced_memory()[0]

        initial_mem = get_mem_bytes()

        iterations = 500  # 500 complete burst cycles = 3,000 state transitions
        for i in range(iterations):
            # 1. recording_started
            signals.recording_started.emit()
            self.hud.on_audio_level(0.42)
            self.hud._update_animation()

            # 2. recording_stopped
            signals.recording_stopped.emit()
            self.hud._update_animation()

            # 3. formatting_started
            signals.formatting_started.emit()
            self.hud._update_animation()

            # 4. transcription_completed
            signals.transcription_completed.emit({
                "text": f"Iteration {i}: Quick brown fox jumps over the lazy dog",
                "latency": 0.085,
                "action": "send_enter" if i % 2 == 0 else None
            })
            self.hud._update_animation()

            # 5. voice_edit_started
            signals.voice_edit_started.emit()
            self.hud.on_audio_level(0.78)
            self.hud._update_animation()

            # 6. transcription_failed
            signals.transcription_failed.emit(f"Error {i}: Connection dropped or squelched")
            self.hud._update_animation()

            # Every 50 iterations, pump Qt events and render
            if i % 50 == 0:
                self.app.processEvents()
                self._render_hud()

        # Final event processing and render
        self.app.processEvents()
        self._render_hud()

        # Confirm HUD is alive and handles a new recording cleanly
        self.assertEqual(self.hud.state, "error")
        signals.recording_started.emit()
        self.app.processEvents()
        self.assertEqual(self.hud.state, "recording")
        self._render_hud()

        # Check memory delta
        gc.collect()
        final_mem = get_mem_bytes()
        tracemalloc.stop()
        mem_growth_mb = (final_mem - initial_mem) / (1024 * 1024)
        # Memory growth over 3000 transitions should be minimal (< 20MB)
        self.assertLess(
            mem_growth_mb, 20.0,
            f"Excessive memory growth detected during rapid state transitions: {mem_growth_mb:.2f} MB"
        )

    # =========================================================================
    # Test 3: Animation Timer Dormancy When Settled
    # =========================================================================

    def test_anim_timer_dormancy_after_hide(self):
        """
        Verify that anim_timer.isActive() becomes False when the HUD settles into hidden state.
        Tests:
        - Default fluid animations (bounce_intensity = 50)
        - Elastic bounce (bounce_intensity = 100)
        - Calm bounce (bounce_intensity = 0)
        - Reduced-motion / fluid_animations = False
        """
        configurations = [
            {"fluid_animations": True, "bounce_intensity": 50},
            {"fluid_animations": True, "bounce_intensity": 100},
            {"fluid_animations": True, "bounce_intensity": 0},
            {"fluid_animations": False, "bounce_intensity": 50},
        ]

        for cfg in configurations:
            config.hud.fluid_animations = cfg["fluid_animations"]
            config.hud.bounce_intensity = cfg["bounce_intensity"]

            # Start recording -> timer active
            self.hud.on_recording_started()
            self.app.processEvents()
            self.assertTrue(self.hud.anim_timer.isActive(), f"anim_timer should be active during recording: {cfg}")

            # Transition to done
            self.hud.on_transcription_completed({"text": "Hello world", "latency": 0.1})
            self.app.processEvents()

            # Now hide the HUD
            self.hud.hide_hud()
            self.assertEqual(self.hud.state, "hidden")

            # Simulate frames until settled or timeout
            max_frames = 200  # At 60 FPS, 200 frames = ~3.3 seconds (HUD should settle in < 1s)
            settled = False
            for frame in range(max_frames):
                if not self.hud.anim_timer.isActive():
                    settled = True
                    break
                self.hud._update_animation()
                self.app.processEvents()

            self.assertTrue(
                settled,
                f"HUD failed to settle within {max_frames} frames under config {cfg}. "
                f"Timer still active: {self.hud.anim_timer.isActive()}, "
                f"scale={self.hud.current_scale:.4f}, opacity={self.hud.current_opacity:.4f}"
            )
            self.assertFalse(
                self.hud.anim_timer.isActive(),
                f"anim_timer must be inactive when settled: {cfg}"
            )
            self.assertTrue(
                self.hud.isHidden(),
                f"HUD widget must be hidden when settled: {cfg}"
            )

    def test_audio_level_subnormal_and_extreme_floats(self):
        """
        Verify subnormal floats (1e-320) and massive floats (1e300)
        are handled gracefully without overflow or arithmetic exceptions.
        """
        self.hud.on_recording_started()
        self.app.processEvents()

        subnormal_and_huge = [1e-320, 1e-100, 1e100, 1e300, -1e300, -1e-320]
        for val in subnormal_and_huge:
            self.hud.on_audio_level(val)
            self.assertFalse(math.isnan(self.hud.target_rms))
            self.assertFalse(math.isinf(self.hud.target_rms))
            self.assertGreaterEqual(self.hud.target_rms, 0.0)
            self.assertLessEqual(self.hud.target_rms, 1.0)
            self.hud._update_animation()
            self._render_hud()

    def test_extreme_string_lengths_and_unicode_rendering(self):
        """
        Verify paintEvent and layout calculations do not fail or exceed bounding
        boxes when receiving massive strings, Unicode/emojis, or zero-width spaces.
        """
        self.hud.on_recording_started()
        self.app.processEvents()

        test_payloads = [
            {"text": "A" * 10000, "latency": 0.05, "action": "send_enter"},
            {"text": "Emoji test: 🎙️✨🔥💡🚀🎉 ääää öööö üüüü ßßßß", "latency": 0.12},
            {"text": "Zero-width:\u200b\u200c\u200d\ufeff\u200e\u200f", "latency": 0.01},
            {"text": "", "latency": 0.0},
            {"text": "Line\nBreak\r\nTabs\tSeparated", "latency": 0.99},
        ]

        for payload in test_payloads:
            self.hud.on_transcription_completed(payload)
            self.hud._update_animation()
            self.app.processEvents()
            # Render to ensure QPainter and QFontMetrics handle it cleanly
            self._render_hud()
            self.assertGreaterEqual(self.hud.target_w, 40.0)
            self.assertLessEqual(self.hud.target_w, 400.0)

    def test_settle_after_hide_timer_fires(self):
        """
        Verify that when hide_timer triggers naturally, the HUD animates down
        and anim_timer is stopped.
        """
        self.hud.on_recording_started()
        self.app.processEvents()
        self.assertTrue(self.hud.anim_timer.isActive())

        # Complete transcription -> sets hide_timer for 2100ms
        self.hud.on_transcription_completed({"text": "Quick test", "latency": 0.05})
        self.app.processEvents()
        self.assertTrue(self.hud.hide_timer.isActive())

        # Manually trigger hide_timer timeout to simulate natural elapsed time
        self.hud.hide_timer.timeout.emit()
        self.assertEqual(self.hud.state, "hidden")

        # Let it animate to settle
        for _ in range(150):
            if not self.hud.anim_timer.isActive():
                break
            self.hud._update_animation()
            self.app.processEvents()

        self.assertFalse(self.hud.anim_timer.isActive())
        self.assertTrue(self.hud.isHidden())

    def test_rapid_language_retranslation_during_transitions(self):
        """
        Verify that calling retranslate_ui during active animations and state
        transitions does not crash, corrupt font metrics, or interrupt springs.
        """
        self.hud.on_recording_started()
        for i in range(100):
            lang = "de" if i % 2 == 0 else "en"
            self.hud.retranslate_ui(lang)
            self.hud.on_audio_level(0.3 * (i % 4))
            self.hud._update_animation()
            if i % 20 == 0:
                self._render_hud()
                self.app.processEvents()

        self.assertIn(self.hud.state, ["recording"])
        self._render_hud()


if __name__ == "__main__":
    unittest.main()

