"""
Velodictum - Minimalist Floating HUD Indicator (Dark Neomorphism 2.0 Edition)
Calm, compact, non-intrusive floating indicator with tactile neomorphic surfaces,
physics-based spring morphing, and responsive audio level metering.
"""
import math
import time
from typing import Optional
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont, QFontMetrics, QPainterPath
from PyQt6.QtWidgets import QWidget, QApplication
from config import config
from gui.signals import signals
from gui.theme import ThemeColors, ThemeTypography, ThemeMetrics, is_reduced_motion
from i18n import tr, get_current_language


class FloatingHUD(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Window Flags: Frameless, Always on top, Tool (no taskbar button), No Focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetWindowLongW(int(self.winId()), -20, user32.GetWindowLongW(int(self.winId()), -20) | 0x08000000)
        except Exception:
            pass

        # Transparent Canvas Dimensions (Accommodates dynamic spring expansions, user scaling & rubber overshoot)
        self.canvas_w = 460
        self.canvas_h = 68
        self.resize(self.canvas_w, self.canvas_h)

        # States: "hidden", "recording", "voice_edit", "transcribing", "done"
        self.state = "hidden"
        self.status_text = ""
        self.sub_text = ""
        self.recording_start_time = 0.0

        # --- Physics-based Spring State ---
        self.current_w = 40.0
        self.target_w = 40.0
        self.vel_w = 0.0

        self.current_h = 32.0
        self.target_h = 32.0
        self.vel_h = 0.0

        self.current_scale = 0.0
        self.target_scale = 0.0
        self.vel_scale = 0.0

        self.current_opacity = 0.0
        self.target_opacity = 0.0
        self.vel_opacity = 0.0

        # Audio visualizer reactive bars
        self.num_bars = 7
        self.bar_heights = [0.15] * self.num_bars
        self.current_rms = 0.0
        self.target_rms = 0.0

        # Shimmer wave phase for processing state
        self.shimmer_phase = 0.0

        # Windows 11 Fluent Segoe UI Variable Typography
        self.title_font = ThemeTypography.get_qfont(size=9, weight=QFont.Weight.DemiBold, small_variant=True)
        self.title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.2)
        self.title_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

        self.sub_font = ThemeTypography.get_qfont(size=8, weight=QFont.Weight.Normal, small_variant=True)
        self.sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.1)
        self.sub_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

        self.done_title_font = ThemeTypography.get_qfont(size=8, weight=QFont.Weight.DemiBold, small_variant=True)
        self.done_title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.2)
        self.done_title_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

        self.done_sub_font = ThemeTypography.get_qfont(size=7, weight=QFont.Weight.Normal, small_variant=True)
        self.done_sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.1)
        self.done_sub_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

        # Dragging & Click support
        self._drag_start_pos = QPoint()
        self._win_start_pos = QPoint()
        self._is_dragging = False
        self._mouse_pressed = False

        # Refusal shake physics
        self.is_shaking = False
        self.shake_time = 0.0
        self.shake_offset = 0.0

        # High-Refresh timing & Micro-Crossfade state
        self._last_anim_time = None
        self._is_crossfading = False
        self._crossfade_time = 0.0
        self.content_fade_alpha = 1.0

        # Position at configured or saved position
        self._init_position()

        # Visualizer & Spring Physics animation timer (60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        # Note: Do not keep timer running when idle to save CPU/battery!

        # Auto-hide timer for "done" state
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_hud)

        # Connect Qt signals
        signals.recording_started.connect(self.on_recording_started)
        signals.recording_stopped.connect(self.on_recording_stopped)
        signals.audio_level_updated.connect(self.on_audio_level)
        signals.transcription_started.connect(self.on_transcription_started)
        signals.formatting_started.connect(self.on_formatting_started)
        signals.transcription_completed.connect(self.on_transcription_completed)
        signals.transcription_failed.connect(self.on_transcription_failed)
        signals.voice_edit_started.connect(self.on_voice_edit_started)
        signals.voice_edit_completed.connect(self.on_voice_edit_completed)
        signals.injection_reverted.connect(self.on_injection_reverted)
        signals.audio_device_switched.connect(self.on_audio_device_switched)
        signals.vocab_word_learned.connect(self.on_vocab_word_learned)
        signals.vocab_suggestion_prompt.connect(self.on_vocab_suggestion_prompt)
        signals.recording_cancelled.connect(self.on_recording_cancelled)
        signals.injection_blocked.connect(self.on_injection_blocked)
        signals.language_changed.connect(self.retranslate_ui)

        self.hide()

    def _init_position(self):
        self._update_hud_position()

    def _update_hud_position(self):
        """
        Dynamically positions the HUD according to user preference:
        1. 'bottom_center' + remember_position: User previously dragged the HUD.
        2. 'follow_cursor': Near active caret or mouse on the active screen.
        3. 'bottom_center': Centered horizontally at the bottom of the active screen.
        """
        try:
            import ctypes
            from ctypes import wintypes
            from PyQt6.QtGui import QCursor
            from PyQt6.QtCore import QRect
            from config import config

            mode = getattr(config.hud, "position_mode", "bottom_center")

            # 1. Custom dragged position is ONLY respected in bottom_center mode
            if mode == "bottom_center" and getattr(config.hud, "remember_position", True):
                cx_saved = getattr(config.hud, "custom_x", None)
                cy_saved = getattr(config.hud, "custom_y", None)
                if cx_saved is not None and cy_saved is not None:
                    test_pt = QPoint(int(cx_saved) + self.canvas_w // 2, int(cy_saved) + self.canvas_h // 2)
                    scr = QApplication.screenAt(test_pt)
                    if scr:
                        geo = scr.availableGeometry()
                        target_x = max(geo.x(), min(int(cx_saved), geo.x() + geo.width() - self.canvas_w))
                        target_y = max(geo.y(), min(int(cy_saved), geo.y() + geo.height() - self.canvas_h))
                        self.move(target_x, target_y)
                        return

            mouse_pos = QCursor.pos()
            active_screen = QApplication.screenAt(mouse_pos)

            if not active_screen:
                try:
                    user32 = ctypes.windll.user32
                    hwnd = user32.GetForegroundWindow()
                    if hwnd:
                        rect = wintypes.RECT()
                        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                            center_pt = QPoint((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                            active_screen = QApplication.screenAt(center_pt)
                except Exception:
                    pass

            if not active_screen:
                active_screen = QApplication.primaryScreen()

            geo = active_screen.availableGeometry() if active_screen else QRect(0, 0, 1920, 1080)

            target_x = None
            target_y = None

            if mode == "follow_cursor":
                try:
                    from ui_automation_context import get_caret_screen_position
                    caret = get_caret_screen_position()
                except Exception:
                    caret = None

                if caret and (caret[0] > 10 or caret[1] > 10):
                    cx, cy = caret
                    caret_pt = QPoint(cx, cy)
                    caret_scr = QApplication.screenAt(caret_pt)
                    if caret_scr:
                        geo = caret_scr.availableGeometry()
                    target_x = cx - self.canvas_w // 2
                    target_y = cy + 8
                    if target_y + self.canvas_h > geo.y() + geo.height():
                        target_y = cy - self.canvas_h - 8
                else:
                    target_x = mouse_pos.x() - self.canvas_w // 2
                    target_y = mouse_pos.y() + 12
                    if target_y + self.canvas_h > geo.y() + geo.height():
                        target_y = mouse_pos.y() - self.canvas_h - 12

            # Fallback to bottom-center of active monitor
            if target_x is None or target_y is None:
                target_x = geo.x() + (geo.width() - self.canvas_w) // 2
                target_y = geo.y() + geo.height() - self.canvas_h - 70

            # Strict bounds clamping to ensure pill is 100% visible on screen
            target_x = max(geo.x() + 10, min(target_x, geo.x() + geo.width() - self.canvas_w - 10))
            target_y = max(geo.y() + 10, min(target_y, geo.y() + geo.height() - self.canvas_h - 10))

            self.move(int(target_x), int(target_y))
        except Exception as e:
            screen = QApplication.primaryScreen()
            if screen:
                g = screen.availableGeometry()
                self.move(g.x() + (g.width() - self.canvas_w) // 2, g.y() + g.height() - self.canvas_h - 70)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._win_start_pos = self.pos()
            self._is_dragging = False
            self._mouse_pressed = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self._mouse_pressed and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if self._is_dragging or delta.manhattanLength() > 4:
                self._is_dragging = True
                self.move(self._win_start_pos + delta)
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Right Click -> Immediate Cancel / Discard
            if self.state in ("recording", "voice_edit"):
                signals.dictation_cancel_requested.emit()
            elif self.state == "prompt":
                self.hide_timer.start(100)
            self._mouse_pressed = False
            self._is_dragging = False
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._mouse_pressed:
            if self._is_dragging:
                # User finished dragging -> Persist position if memory enabled AND in bottom_center mode
                if getattr(config.hud, "position_mode", "bottom_center") == "bottom_center" and getattr(config.hud, "remember_position", True):
                    config.hud.custom_x = self.x()
                    config.hud.custom_y = self.y()
                    config.save()
                self._is_dragging = False
            else:
                # Click on Prompt -> Accept candidate word into dictionary
                if self.state == "prompt" and hasattr(self, "_pending_vocab_word") and self._pending_vocab_word:
                    word = self._pending_vocab_word
                    orig = getattr(self, "_pending_vocab_orig", "")
                    self._pending_vocab_word = None
                    self._pending_vocab_orig = None

                    from correction_detector import correction_detector
                    correction_detector.accept_candidate(word, orig)

                    self.state = "done"
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.status_text = tr("hud_saved")
                    self.sub_text = tr("hud_word_in_vocab", word=word)
                    self.target_w = 195.0
                    self._trigger_morph_impulse(0.5)
                    self.update()
                    self.hide_timer.start(2200)
                    self._mouse_pressed = False
                    event.accept()
                    return

                # Click without dragging -> End recording / voice edit on mouse click
                if self.state in ("recording", "voice_edit"):
                    signals.dictation_toggle_requested.emit()
            self._mouse_pressed = False
            event.accept()

    def retranslate_ui(self, lang_code: Optional[str] = None) -> None:
        """
        Dynamically refreshes all localized strings for the current HUD state.
        Safely validates lang_code in ("en", "de") without failing on invalid inputs.
        Satisfies PROJECT.md Feature 7 contract.
        """
        try:
            if lang_code and isinstance(lang_code, str) and lang_code in ("en", "de"):
                from i18n import set_current_language
                try:
                    set_current_language(lang_code)
                except Exception:
                    pass

            if self.state == "recording":
                self.status_text = tr("hud_listening")
            elif self.state == "voice_edit":
                self.status_text = tr("hud_transform")
                self.sub_text = tr("hud_instruction")
                is_minimal = getattr(config.hud, "minimal_mode", False)
                is_en = (get_current_language() == "en")
                self.target_w = 64.0 if is_minimal else (170.0 if is_en else 188.0)
            elif self.state == "transcribing":
                if getattr(self, "_is_formatting", False) or "format" in (self.status_text or "").lower():
                    self.status_text = tr("hud_formatting")
                else:
                    self.status_text = tr("hud_processing")
            elif self.state == "done":
                if self.status_text in ("", "Done", "Fertig", tr("hud_done")):
                    self.status_text = tr("hud_done")
                elif self.status_text in ("Saved", "Gespeichert", tr("hud_saved")):
                    self.status_text = tr("hud_saved")
                elif self.status_text in ("Transformed", "Transformiert", tr("hud_transformed")):
                    self.status_text = tr("hud_transformed")
                elif self.status_text in ("Reverted", "Rückgängig", tr("hud_reverted")):
                    self.status_text = tr("hud_reverted")
            elif self.state == "cancelled":
                self.status_text = tr("hud_cancelled")
                self.sub_text = tr("hud_recording_discarded")
            elif self.state == "error":
                low_msg = (self.status_text or "").lower()
                low_sub = (self.sub_text or "").lower()
                if "password" in low_msg or "passwort" in low_msg:
                    self.status_text = tr("hud_password_protected")
                    self.sub_text = tr("hud_dictation_disabled")
                elif "speech" in low_msg or "sprache" in low_msg:
                    self.status_text = tr("hud_no_speech")
                    self.sub_text = tr("hud_nothing_heard")
                elif "select" in low_msg or "auswahl" in low_msg:
                    self.status_text = tr("hud_no_text_selected")
                    self.sub_text = tr("hud_select_text_first")
                else:
                    self.status_text = tr("hud_error")
                    if "transform" in low_sub:
                        self.sub_text = tr("hud_transform_not_possible")
                if not getattr(config.hud, "minimal_mode", False):
                    self.target_w = self._compute_pill_width(min_w=196.0, max_w=380.0, pad=64.0)
            elif self.state == "prompt":
                word = getattr(self, "_pending_vocab_word", "")
                orig = getattr(self, "_pending_vocab_orig", "")
                if word:
                    self.status_text = tr("hud_vocab_prompt_title", word=word)
                    self.sub_text = tr("hud_vocab_prompt_save_orig", orig=orig) if orig else tr("hud_vocab_prompt_save")
                    if not getattr(config.hud, "minimal_mode", False):
                        self.target_w = self._compute_pill_width(min_w=210.0, max_w=380.0, pad=64.0)

            self.title_font = ThemeTypography.get_qfont(size=9, weight=QFont.Weight.DemiBold, small_variant=True)
            self.title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.2)
            self.title_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

            self.sub_font = ThemeTypography.get_qfont(size=8, weight=QFont.Weight.Normal, small_variant=True)
            self.sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.1)
            self.sub_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

            self.done_title_font = ThemeTypography.get_qfont(size=8, weight=QFont.Weight.DemiBold, small_variant=True)
            self.done_title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.2)
            self.done_title_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

            self.done_sub_font = ThemeTypography.get_qfont(size=7, weight=QFont.Weight.Normal, small_variant=True)
            self.done_sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.1)
            self.done_sub_font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)

            self.update()
        except Exception:
            pass

    def _compute_pill_width(self, min_w: float = 188.0, max_w: float = 380.0, pad: float = 64.0, use_done_fonts: bool = True) -> float:
        """
        Computes required target_w so that even when user_scale < 1.0 (e.g. 88%),
        the rendered pill draw_w is guaranteed to fit both status_text and sub_text without clipping.
        """
        t_font = self.done_title_font if use_done_fonts else self.title_font
        s_font = self.done_sub_font if use_done_fonts else self.sub_font
        text_w = QFontMetrics(t_font).horizontalAdvance(self.status_text or "")
        sub_w = QFontMetrics(s_font).horizontalAdvance(self.sub_text or "")
        needed_px = max(min_w, float(max(text_w, sub_w)) + pad)
        user_scale = max(0.85, min(1.15, getattr(config.hud, "scale_percent", 100) / 100.0))
        if user_scale < 1.0:
            needed_px = needed_px / user_scale
        return min(max_w, needed_px)

    def on_recording_started(self):
        if not getattr(config.hud, "enabled", True):
            return
        self.state = "recording"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording_start_time = time.time()
        self.status_text = tr("hud_listening")
        self.sub_text = "00:00"
        self._last_anim_time = None
        self._is_crossfading = False
        self.content_fade_alpha = 1.0
        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 64.0 if is_minimal else self._compute_pill_width(min_w=156.0, max_w=260.0, pad=84.0, use_done_fonts=False)
        self.target_h = 36.0
        self.target_scale = 1.0
        self.target_opacity = 1.0

        if not self.isVisible() or self.current_scale < 0.1:
            self.current_w = 50.0 if is_minimal else 80.0
            self.current_h = 34.0
            self.current_scale = 0.50
            self.current_opacity = 0.0
            self.vel_w = 100.0  # Controlled, elegant initial impulse
            self.vel_scale = 2.5

        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()

    def on_voice_edit_started(self):
        if not getattr(config.hud, "enabled", True):
            return
        self.state = "voice_edit"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording_start_time = time.time()
        self.status_text = tr("hud_transform")
        self.sub_text = tr("hud_instruction")
        self._last_anim_time = None
        self._is_crossfading = False
        self.content_fade_alpha = 1.0
        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        is_en = (get_current_language() == "en")
        base_w = 170.0 if is_en else 188.0
        self.target_w = 64.0 if is_minimal else self._compute_pill_width(min_w=base_w, max_w=280.0, pad=84.0, use_done_fonts=False)
        self.target_h = 36.0
        self.target_scale = 1.0
        self.target_opacity = 1.0

        if not self.isVisible() or self.current_scale < 0.1:
            self.current_w = 50.0 if is_minimal else 80.0
            self.current_h = 34.0
            self.current_scale = 0.50
            self.current_opacity = 0.0
            self.vel_w = 100.0
            self.vel_scale = 2.5

        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()

    def _trigger_morph_impulse(self, impulse_scale: float = 0.5):
        """Triggers a subtle, silky-smooth elastic pop and micro-crossfade on state changes."""
        if getattr(config.hud, "fluid_animations", True) and not is_reduced_motion(config):
            self.vel_scale = impulse_scale
            self._is_crossfading = True
            self._crossfade_time = 0.0
            self.content_fade_alpha = 0.0
            if not self.anim_timer.isActive():
                self.anim_timer.start(16)

    def on_recording_stopped(self):
        if self.state in ("recording", "voice_edit"):
            self.state = "transcribing"
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.is_shaking = False
            self.shake_offset = 0.0
            self.status_text = tr("hud_processing")
            self.sub_text = "Whisper"
            is_minimal = getattr(config.hud, "minimal_mode", False)
            self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=148.0, max_w=240.0, pad=56.0, use_done_fonts=False)
            self.target_h = 36.0
            self._trigger_morph_impulse(0.4)
            self.update()

    def on_audio_level(self, rms: float):
        if not math.isfinite(rms):
            self.target_rms = 0.0
        else:
            self.target_rms = max(0.0, min(1.0, rms * 14.0))

    def on_transcription_started(self):
        self.state = "transcribing"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_processing")
        self.sub_text = "Whisper"
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=148.0, max_w=240.0, pad=56.0, use_done_fonts=False)
        self.target_h = 36.0
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()

    def on_formatting_started(self):
        self.state = "transcribing"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_formatting")
        self.sub_text = "Flow Layer"
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=154.0, max_w=250.0, pad=56.0, use_done_fonts=False)
        self.target_h = 36.0
        self._trigger_morph_impulse(0.3)
        self.update()

    def on_transcription_completed(self, data: dict):
        self.state = "done"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        text = data.get("text", "")
        preview = (text[:20] + "...") if len(text) > 20 else text
        self.status_text = preview if preview else tr("hud_done")
        dur_ms = data.get("latency", 0) * 1000
        action = data.get("action")
        if action == "send_enter":
            self.sub_text = tr("hud_sent", dur=f"{dur_ms:.0f}")
        else:
            self.sub_text = tr("hud_injected", dur=f"{dur_ms:.0f}")

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=172.0, max_w=340.0, pad=62.0)
        self.target_h = 36.0

        self._trigger_morph_impulse(0.5)
        self.update()
        self.hide_timer.start(2100)

    def on_voice_edit_completed(self, data: dict):
        self.state = "done"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_transformed")
        dur_ms = data.get("latency", 0) * 1000
        self.sub_text = tr("hud_replaced", dur=f"{dur_ms:.0f}")
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=176.0, max_w=300.0, pad=62.0)
        self.target_h = 36.0
        self._trigger_morph_impulse(0.5)
        self.update()
        self.hide_timer.start(2200)

    def on_injection_reverted(self, data: dict):
        self.state = "done"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_reverted")
        if data.get("success"):
            self.sub_text = tr("hud_dict_removed")
        else:
            self.sub_text = tr("hud_nothing_reverted")
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=168.0, max_w=300.0, pad=62.0)
        self.target_h = 36.0
        self._trigger_morph_impulse(0.5)
        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(1800)

    def on_audio_device_switched(self, device_name: str):
        self.state = "done"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_mic_switched")
        self.sub_text = (device_name or tr("hud_default_mic"))[:26]

        self.target_scale = 1.0
        self.target_opacity = 1.0
        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=200.0, max_w=360.0, pad=64.0)

        self.target_h = 36.0

        if not self.isVisible() or self.current_scale < 0.1 or self.current_opacity < 0.1:
            self.current_w = 50.0 if is_minimal else 80.0
            self.current_h = 34.0
            self.current_scale = 0.60
            self.current_opacity = 0.1
            self.vel_w = 120.0
            self.vel_scale = 2.8

        self._trigger_morph_impulse(0.5)
        self._update_hud_position()
        self.show()
        self.raise_()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(3000)

    def on_vocab_word_learned(self, word: str):
        self.state = "done"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_noun_learned")
        self.sub_text = word[:22]
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=185.0, max_w=320.0, pad=62.0)
        self.target_h = 36.0
        self._trigger_morph_impulse(0.5)
        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(2200)

    def on_vocab_suggestion_prompt(self, payload: dict):
        word = payload.get("word", "").strip()
        orig = payload.get("orig", "").strip()
        if not word:
            return

        self._pending_vocab_word = word
        self._pending_vocab_orig = orig

        self.state = "prompt"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_vocab_prompt_title", word=word)
        self.sub_text = tr("hud_vocab_prompt_save_orig", orig=orig) if orig else tr("hud_vocab_prompt_save")

        self.target_scale = 1.0
        self.target_opacity = 1.0
        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=210.0, max_w=380.0, pad=64.0)

        self.target_h = 36.0

        if not self.isVisible() or self.current_scale < 0.1 or self.current_opacity < 0.1:
            self.current_w = 50.0 if is_minimal else 80.0
            self.current_h = 34.0
            self.current_scale = 0.60
            self.current_opacity = 0.1
            self.vel_w = 120.0
            self.vel_scale = 2.8

        self._trigger_morph_impulse(0.6)
        self._update_hud_position()
        self.show()
        self.raise_()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(8000)

    def on_recording_cancelled(self):
        self.state = "cancelled"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.is_shaking = False
        self.shake_offset = 0.0
        self.status_text = tr("hud_cancelled")
        self.sub_text = tr("hud_recording_discarded")
        self.target_scale = 1.0
        self.target_opacity = 1.0
        self.hide_timer.stop()
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=180.0, max_w=320.0, pad=62.0)
        self.target_h = 36.0
        self._trigger_morph_impulse(0.5)
        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(1200)

    def on_transcription_failed(self, err_msg: str):
        self.state = "error"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.hide_timer.stop()
        low_msg = (err_msg or "").lower()
        if not err_msg or "keine sprache" in low_msg or "zu kurz" in low_msg or "squelched" in low_msg or "nichts" in low_msg or "keine anweisung" in low_msg or "no speech" in low_msg or "no instruction" in low_msg or "too short" in low_msg:
            self.status_text = tr("hud_no_speech")
            self.sub_text = tr("hud_nothing_heard")
        elif "kein text" in low_msg or "keine auswahl" in low_msg or "no text" in low_msg:
            self.status_text = tr("hud_no_text_selected")
            self.sub_text = tr("hud_select_text_first")
        else:
            self.status_text = tr("hud_error")
            self.sub_text = err_msg[:48]

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=196.0, max_w=380.0, pad=64.0)
        self.target_h = 36.0
        self.target_scale = 1.0
        self.target_opacity = 1.0

        # Lateral Refusal Shake Animation ONLY for error
        self.shake_time = 0.0
        self.is_shaking = True
        self.shake_offset = 0.0

        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(2400)

    def on_injection_blocked(self, reason: str = ""):
        self.state = "error"
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.hide_timer.stop()
        self.status_text = tr("hud_password_protected")
        self.sub_text = tr("hud_dictation_disabled")

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=200.0, max_w=380.0, pad=64.0)
        self.target_h = 36.0
        self.target_scale = 1.0
        self.target_opacity = 1.0

        # Lateral Refusal Shake Animation
        self.shake_time = 0.0
        self.is_shaking = True
        self.shake_offset = 0.0

        self._update_hud_position()
        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()
        self.hide_timer.start(2200)

    def hide_hud(self):
        # Controlled, clean collapse
        self.target_scale = 0.0
        self.target_opacity = 0.0
        self.vel_scale = -2.5
        self.state = "hidden"
        self._last_anim_time = None
        self._is_crossfading = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_animation(self):
        now = time.perf_counter()
        if self._last_anim_time is None:
            dt = 0.016
        else:
            dt = min(0.04, max(0.001, now - self._last_anim_time))
        self._last_anim_time = now

        fluid_enabled = getattr(config.hud, "fluid_animations", True) and not is_reduced_motion(config)

        # Micro-Crossfade interpolation (75ms smoothstep for ultra-fluid content morphs)
        if self._is_crossfading and fluid_enabled:
            self._crossfade_time += dt
            progress = min(1.0, self._crossfade_time / 0.075)
            self.content_fade_alpha = progress * progress * (3.0 - 2.0 * progress)
            if self._crossfade_time >= 0.075:
                self._is_crossfading = False
                self.content_fade_alpha = 1.0
        else:
            self._is_crossfading = False
            self.content_fade_alpha = 1.0

        # Lateral Refusal Shake
        if self.is_shaking and fluid_enabled:
            self.shake_time += dt
            decay = max(0.0, 1.0 - self.shake_time / 0.38)
            self.shake_offset = 9.0 * math.sin(self.shake_time * 38.0) * (decay ** 1.8)
            if self.shake_time >= 0.38:
                self.is_shaking = False
                self.shake_offset = 0.0
        else:
            self.is_shaking = False
            self.shake_offset = 0.0

        if fluid_enabled:
            # Dynamically calculate damping based on user bounce setting (0=minimal/calm, 50=balanced default, 100=elastic)
            bounce_factor = getattr(config.hud, "bounce_intensity", 50) / 100.0
            cw = 28.0 - (11.5 * bounce_factor)
            ch = 30.0 - (12.0 * bounce_factor)
            cs = 29.0 - (12.0 * bounce_factor)

            # 1. Width Spring
            kw = 320.0
            fw = -kw * (self.current_w - self.target_w) - cw * self.vel_w
            self.vel_w += fw * dt
            self.current_w += self.vel_w * dt
            if abs(self.current_w - self.target_w) < 0.2 and abs(self.vel_w) < 0.25:
                self.current_w = self.target_w
                self.vel_w = 0.0

            # 2. Height Spring
            kh = 340.0
            fh = -kh * (self.current_h - self.target_h) - ch * self.vel_h
            self.vel_h += fh * dt
            self.current_h += self.vel_h * dt
            if abs(self.current_h - self.target_h) < 0.2 and abs(self.vel_h) < 0.25:
                self.current_h = self.target_h
                self.vel_h = 0.0

            # 3. Scale Spring
            ks = 330.0
            fs = -ks * (self.current_scale - self.target_scale) - cs * self.vel_scale
            self.vel_scale += fs * dt
            self.current_scale = max(0.0, min(1.20, self.current_scale + self.vel_scale * dt))
            if abs(self.current_scale - self.target_scale) < 0.005 and abs(self.vel_scale) < 0.01:
                self.current_scale = self.target_scale
                self.vel_scale = 0.0

            # 4. Opacity Spring
            fo = -280.0 * (self.current_opacity - self.target_opacity) - 24.0 * self.vel_opacity
            self.vel_opacity += fo * dt
            self.current_opacity = max(0.0, min(1.0, self.current_opacity + self.vel_opacity * dt))
            if abs(self.current_opacity - self.target_opacity) < 0.005 and abs(self.vel_opacity) < 0.01:
                self.current_opacity = self.target_opacity
                self.vel_opacity = 0.0

        else:
            # Instant rigid fallback / Reduced-Motion
            self.current_w = self.target_w
            self.current_h = self.target_h
            self.current_scale = self.target_scale
            self.current_opacity = self.target_opacity

        # Check if fully hidden and settled -> Stop timer to save 100% CPU!
        if self.state == "hidden" and self.current_scale < 0.02 and self.current_opacity < 0.02:
            self.hide()
            self.anim_timer.stop()
            return

        if self.state == "recording":
            dur = int(time.time() - self.recording_start_time)
            m, s = divmod(dur, 60)
            self.sub_text = f"{m:02d}:{s:02d}"

            self.current_rms += (self.target_rms - self.current_rms) * 0.35
            if self.current_rms < 0.03:
                # Silence / quiet room: static clean baseline with zero jitter
                for i in range(self.num_bars):
                    self.bar_heights[i] += (0.12 - self.bar_heights[i]) * 0.25
            else:
                # Active speech: calm reactive audio waveform shaped by human vocal formant envelope
                t = time.time() * (2.5 if not fluid_enabled else 8.0)
                weights_7 = (0.75, 0.85, 0.95, 1.0, 0.95, 0.85, 0.75)
                for i in range(self.num_bars):
                    w_factor = weights_7[i] if i < len(weights_7) else 1.0
                    wave = math.sin(t + i * 0.75) * 0.25 + 0.75 if fluid_enabled else 0.85
                    target_h = max(0.12, min(1.0, self.current_rms * wave * 1.25 * w_factor))
                    self.bar_heights[i] += (target_h - self.bar_heights[i]) * 0.45

        elif self.state == "transcribing":
            # Slower, calmer sweep with an elegant pause between sweeps (~3.5 seconds total period)
            if fluid_enabled:
                self.shimmer_phase = (self.shimmer_phase + 0.009) % 2.2

        self.update()

    def paintEvent(self, event):
        if self.current_scale < 0.01 or self.current_opacity < 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setOpacity(max(0.0, min(1.0, self.current_opacity)))

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        fluid_enabled = getattr(config.hud, "fluid_animations", True) and not is_reduced_motion(config)
        user_scale = max(0.85, min(1.15, getattr(config.hud, "scale_percent", 100) / 100.0))

        # Subtle volume preservation during expansion
        squish = max(-0.04, min(0.04, -self.vel_w * 0.0001)) if fluid_enabled else 0.0
        
        # Exact integer pixel snapping to eliminate text/icon subpixel wobble + lateral refusal shake
        draw_w = round(max(16.0, self.current_w * self.current_scale * user_scale))
        draw_h = round(max(16.0, self.current_h * (1.0 + squish) * self.current_scale * user_scale))
        rx = round(cx - draw_w / 2.0 + self.shake_offset)
        ry = round(cy - draw_h / 2.0)

        rect = QRectF(rx, ry, draw_w, draw_h)
        radius = draw_h / 2.0

        # 0. Dark Neomorphism 2.0 Dual Shadow Base
        painter.setPen(Qt.PenStyle.NoPen)
        # Top-left subtle ambient light rim
        painter.setBrush(QBrush(QColor(46, 56, 86, 40)))
        painter.drawRoundedRect(rect.adjusted(-1.0, -1.0, 0.5, 0.5), radius + 1.0, radius + 1.0)
        # Bottom-right deep graphite drop shadow
        painter.setBrush(QBrush(QColor(3, 5, 10, 120)))
        painter.drawRoundedRect(rect.adjusted(0.5, 1.5, 2.5, 4.0), radius + 1.5, radius + 1.5)
        painter.setBrush(QBrush(QColor(3, 5, 10, 165)))
        painter.drawRoundedRect(rect.adjusted(0.0, 1.0, 1.0, 2.0), radius + 0.5, radius + 0.5)

        # 1. Tactile Neomorphic Graphite Surface (Solid deep blue-black / graphite gradient, no glass blur)
        surf_grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        surf_grad.setColorAt(0.0, QColor("#181d2b"))
        surf_grad.setColorAt(0.5, QColor("#131722"))
        surf_grad.setColorAt(1.0, QColor("#0d1018"))
        painter.setBrush(QBrush(surf_grad))

        # 2. Tactile Neomorphic Border per state
        if self.state == "recording":
            border_pen = QPen(QColor("#eb5e38"), 1.2)            # Coral / Orange Primary Action
        elif self.state == "voice_edit":
            border_pen = QPen(QColor("#7c83e0"), 1.2)            # Muted Indigo / Violet
        elif self.state == "transcribing":
            border_pen = QPen(QColor("#5861b5"), 1.1)            # Muted Indigo Processing
        elif self.state == "done":
            border_pen = QPen(QColor("#34d399"), 1.2)            # Mint / Green Positive State
        elif self.state == "prompt":
            border_pen = QPen(QColor("#f59e0b"), 1.2)            # Amber Warning
        elif self.state in ("cancelled", "error"):
            border_pen = QPen(QColor("#ef4444"), 1.2)            # Crimson Error
        else:
            border_pen = QPen(QColor("#2c344d"), 1.0)            # Neomorphic Graphite Rim

        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)

        # 3. Fine Top Neomorphic Edge Highlight (1px top edge bevel)
        bevel_grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + draw_h * 0.45)
        bevel_grad.setColorAt(0.0, QColor(255, 255, 255, 32))
        bevel_grad.setColorAt(0.5, QColor(255, 255, 255, 6))
        bevel_grad.setColorAt(1.0, QColor(0, 0, 0, 45))
        spec_pen = QPen(QBrush(bevel_grad), 1.0)
        painter.setPen(spec_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        # 4. Transcribing Subtle Indigo Sweep
        if self.state == "transcribing" and fluid_enabled and self.shimmer_phase <= 1.0:
            eased_progress = (1.0 - math.cos(self.shimmer_phase * math.pi)) * 0.5
            shimmer_x = rect.left() - 40.0 + (rect.width() + 80.0) * eased_progress
            shimmer_grad = QLinearGradient(shimmer_x - 35.0, rect.top(), shimmer_x + 35.0, rect.bottom())
            shimmer_grad.setColorAt(0.0, QColor(124, 131, 224, 0))
            shimmer_grad.setColorAt(0.5, QColor(124, 131, 224, 24))
            shimmer_grad.setColorAt(1.0, QColor(124, 131, 224, 0))
            painter.setBrush(QBrush(shimmer_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        # 5. Coordinated Content Rendering
        is_minimal = getattr(config.hud, "minimal_mode", False)
        threshold_w = 28.0 if is_minimal else 75.0

        if draw_w > threshold_w and self.current_scale > 0.35:
            pill_cx = rx + draw_w / 2.0
            progress = min(1.0, max(0.0, (draw_w - 30.0) / max(1.0, self.target_w - 30.0)))
            eased_t = progress * progress * (3.0 - 2.0 * progress)
            center_origin = pill_cx - 24.0
            content_left = round(center_origin * (1.0 - eased_t) + rx * eased_t)
            center_y = round(cy)

            content_alpha = min(1.0, max(0.0, (self.current_opacity - 0.15) / 0.85))
            painter.save()
            painter.setOpacity(self.current_opacity * content_alpha * self.content_fade_alpha)

            clip_path = QPainterPath()
            clip_path.addRoundedRect(rect, radius, radius)
            painter.setClipPath(clip_path)

            if self.state in ("recording", "voice_edit"):
                is_voice_edit = (self.state == "voice_edit")
                # Coral (#eb5e38) for recording, Muted Indigo (#7c83e0) for voice_edit
                accent_color = QColor("#7c83e0") if is_voice_edit else QColor("#eb5e38")
                vocal_bloom = max(0.0, min(1.0, (self.current_rms - 0.15) / 0.65))

                if is_voice_edit:
                    top_r = int(124 + 45 * vocal_bloom)
                    top_g = int(131 + 45 * vocal_bloom)
                    top_b = int(224 + 25 * vocal_bloom)
                    top_color = QColor(top_r, top_g, top_b, 255)
                    bot_color = QColor(88, 97, 181, 240)
                else:
                    top_r = int(235 + 20 * vocal_bloom)
                    top_g = int(94 + 38 * vocal_bloom)
                    top_b = int(56 + 24 * vocal_bloom)
                    top_color = QColor(top_r, top_g, top_b, 255)
                    bot_color = QColor(200, 68, 34, 240)

                if is_minimal:
                    min_left = round(pill_cx - 24.0)
                    pulse = ((math.sin(time.time() * 2.6) + 1.0) * 0.5) if fluid_enabled else 0.5
                    halo_alpha = int(28 + 30 * pulse)
                    painter.setBrush(QBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), halo_alpha)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(min_left + 8), int(center_y)), 5, 5)

                    painter.setBrush(QBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 250)))
                    painter.drawEllipse(QPoint(int(min_left + 8), int(center_y)), 3, 3)

                    wave_x = min_left + 17
                    bar_w = 2.2
                    gap = 2.0
                    max_bar_h = 14.0
                    bar_r = bar_w / 2.0
                    painter.setPen(Qt.PenStyle.NoPen)
                    for i in range(min(4, self.num_bars)):
                        bh = max(2.5, self.bar_heights[i] * max_bar_h)
                        bx = wave_x + i * (bar_w + gap)
                        by = center_y - (bh / 2.0)
                        bar_rect = QRectF(bx, by, bar_w, bh)
                        bar_grad = QLinearGradient(bx, by, bx, by + bh)
                        bar_grad.setColorAt(0.0, top_color)
                        bar_grad.setColorAt(1.0, bot_color)
                        painter.setBrush(QBrush(bar_grad))
                        painter.drawRoundedRect(bar_rect, bar_r, bar_r)

                else:
                    pulse = ((math.sin(time.time() * 2.6) + 1.0) * 0.5) if fluid_enabled else 0.5
                    halo_alpha = int(28 + 30 * pulse)
                    halo_r = 4.5 + 1.0 * pulse
                    painter.setBrush(QBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), halo_alpha)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(content_left + 16), int(center_y)), int(halo_r), int(halo_r))

                    painter.setBrush(QBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 250)))
                    painter.drawEllipse(QPoint(int(content_left + 16), int(center_y)), 3, 3)

                    wave_x = content_left + 26
                    bar_w = 2.5
                    gap = 2.0
                    max_bar_h = 16.0
                    bar_r = bar_w / 2.0

                    painter.setPen(Qt.PenStyle.NoPen)
                    for i in range(self.num_bars):
                        bh = max(2.5, self.bar_heights[i] * max_bar_h)
                        bx = wave_x + i * (bar_w + gap)
                        by = center_y - (bh / 2.0)
                        bar_rect = QRectF(bx, by, bar_w, bh)
                        bar_grad = QLinearGradient(bx, by, bx, by + bh)
                        bar_grad.setColorAt(0.0, top_color)
                        bar_grad.setColorAt(1.0, bot_color)
                        painter.setBrush(QBrush(bar_grad))
                        painter.drawRoundedRect(bar_rect, bar_r, bar_r)

                    # Text labels (Cool white primary, legible blue-gray secondary)
                    tfm = QFontMetrics(self.title_font)
                    sfm = QFontMetrics(self.sub_font)
                    t_asc = tfm.ascent()
                    s_asc = sfm.ascent()
                    total_text_h = t_asc + 2.0 + s_asc
                    text_top = center_y - total_text_h / 2.0
                    title_y = int(text_top + t_asc)
                    sub_y = int(title_y + 2.0 + s_asc)

                    painter.setPen(QColor("#f8fafc"))
                    painter.setFont(self.title_font)
                    painter.drawText(int(content_left + 66), title_y, self.status_text)

                    painter.setPen(QColor("#a5b4fc") if self.state == "voice_edit" else QColor("#94a3b8"))
                    painter.setFont(self.sub_font)
                    painter.drawText(int(content_left + 66), sub_y, self.sub_text)

            elif self.state == "transcribing":
                angle = int((time.time() * 240) % 360) if fluid_enabled else 45
                spin_pen = QPen(QColor("#7c83e0"), 1.8)
                spin_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(spin_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)

                if is_minimal:
                    painter.drawArc(QRectF(pill_cx - 7, center_y - 7, 14, 14), -angle * 16, 220 * 16)
                else:
                    painter.drawArc(QRectF(content_left + 14, center_y - 7, 14, 14), -angle * 16, 220 * 16)

                    tfm = QFontMetrics(self.title_font)
                    sfm = QFontMetrics(self.sub_font)
                    t_asc = tfm.ascent()
                    s_asc = sfm.ascent()
                    total_text_h = t_asc + 2.0 + s_asc
                    text_top = center_y - total_text_h / 2.0
                    title_y = int(text_top + t_asc)
                    sub_y = int(title_y + 2.0 + s_asc)

                    painter.setPen(QColor("#f8fafc"))
                    painter.setFont(self.title_font)
                    painter.drawText(int(content_left + 36), title_y, self.status_text)

                    painter.setPen(QColor("#94a3b8"))
                    painter.setFont(self.sub_font)
                    painter.drawText(int(content_left + 36), sub_y, self.sub_text)

            elif self.state == "done":
                if is_minimal:
                    painter.setBrush(QBrush(QColor("#34d399")))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(pill_cx), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#0b0d14"), 1.5))
                    painter.drawLine(int(pill_cx - 3), int(center_y), int(pill_cx - 1), int(center_y) + 2)
                    painter.drawLine(int(pill_cx - 1), int(center_y) + 2, int(pill_cx + 3), int(center_y) - 2)
                else:
                    painter.setBrush(QBrush(QColor("#34d399")))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(content_left + 18), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#0b0d14"), 1.5))
                    painter.drawLine(int(content_left + 15), int(center_y), int(content_left + 17), int(center_y) + 2)
                    painter.drawLine(int(content_left + 17), int(center_y) + 2, int(content_left + 21), int(center_y) - 2)

                    tfm = QFontMetrics(self.done_title_font)
                    sfm = QFontMetrics(self.done_sub_font)
                    t_asc = tfm.ascent()
                    s_asc = sfm.ascent()
                    total_text_h = t_asc + 2.0 + s_asc
                    text_top = center_y - total_text_h / 2.0
                    title_y = int(text_top + t_asc)
                    sub_y = int(title_y + 2.0 + s_asc)

                    painter.setPen(QColor("#f8fafc"))
                    painter.setFont(self.done_title_font)
                    painter.drawText(int(content_left + 34), title_y, self.status_text)

                    painter.setPen(QColor("#34d399"))
                    painter.setFont(self.done_sub_font)
                    painter.drawText(int(content_left + 34), sub_y, self.sub_text)

            elif self.state == "prompt":
                if is_minimal:
                    painter.setBrush(QBrush(QColor("#f59e0b")))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(pill_cx), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#0b0d14"), 1.5))
                    painter.drawLine(int(pill_cx - 3), int(center_y), int(pill_cx + 3), int(center_y))
                    painter.drawLine(int(pill_cx), int(center_y - 3), int(pill_cx), int(center_y + 3))
                else:
                    painter.setBrush(QBrush(QColor("#f59e0b")))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(content_left + 18), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#0b0d14"), 1.5))
                    painter.drawLine(int(content_left + 15), int(center_y), int(content_left + 21), int(center_y))
                    painter.drawLine(int(content_left + 18), int(center_y - 3), int(content_left + 18), int(center_y + 3))

                    tfm = QFontMetrics(self.done_title_font)
                    sfm = QFontMetrics(self.done_sub_font)
                    t_asc = tfm.ascent()
                    s_asc = sfm.ascent()
                    total_text_h = t_asc + 2.0 + s_asc
                    text_top = center_y - total_text_h / 2.0
                    title_y = int(text_top + t_asc)
                    sub_y = int(title_y + 2.0 + s_asc)

                    painter.setPen(QColor("#fef08a"))
                    painter.setFont(self.done_title_font)
                    painter.drawText(int(content_left + 34), title_y, self.status_text)

                    painter.setPen(QColor("#f59e0b"))
                    painter.setFont(self.done_sub_font)
                    painter.drawText(int(content_left + 34), sub_y, self.sub_text)

            elif self.state in ("cancelled", "error"):
                is_cancel = (self.state == "cancelled")
                badge_color = QColor("#ef4444") if not is_cancel else QColor("#e11d48")
                sub_color = QColor("#f87171") if not is_cancel else QColor("#fda4af")

                if is_minimal:
                    painter.setBrush(QBrush(badge_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(pill_cx), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#ffffff"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    painter.drawLine(int(pill_cx - 3), int(center_y) - 3, int(pill_cx + 3), int(center_y) + 3)
                    painter.drawLine(int(pill_cx + 3), int(center_y) - 3, int(pill_cx - 3), int(center_y) + 3)
                else:
                    painter.setBrush(QBrush(badge_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(int(content_left + 18), int(center_y)), 6, 6)

                    painter.setPen(QPen(QColor("#ffffff"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    painter.drawLine(int(content_left + 15), int(center_y) - 3, int(content_left + 21), int(center_y) + 3)
                    painter.drawLine(int(content_left + 21), int(center_y) - 3, int(content_left + 15), int(center_y) + 3)

                    tfm = QFontMetrics(self.done_title_font)
                    sfm = QFontMetrics(self.done_sub_font)
                    t_asc = tfm.ascent()
                    s_asc = sfm.ascent()
                    total_text_h = t_asc + 2.0 + s_asc
                    text_top = center_y - total_text_h / 2.0
                    title_y = int(text_top + t_asc)
                    sub_y = int(title_y + 2.0 + s_asc)

                    painter.setPen(QColor("#f8fafc"))
                    painter.setFont(self.done_title_font)
                    painter.drawText(int(content_left + 34), title_y, self.status_text)

                    painter.setPen(sub_color)
                    painter.setFont(self.done_sub_font)
                    painter.drawText(int(content_left + 34), sub_y, self.sub_text)

            painter.restore()

        painter.end()
