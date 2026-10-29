"""
Velodictum - Minimalist Floating HUD Indicator (Dark Neomorphism 2.0 & Liquid Optical Glass Edition)
Calm, compact, non-intrusive floating indicator with Siri-inspired translucent smoked glass optics,
prismatic horizon caustic refraction, physics-based spring morphing, and responsive audio level metering.
"""
import math
import time
from typing import Optional
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPen,
    QLinearGradient,
    QRadialGradient,
    QFont,
    QFontMetrics,
    QPainterPath,
    QPixmap,
)
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
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetWindowLongW(int(self.winId()), -20, user32.GetWindowLongW(int(self.winId()), -20) | 0x08000000)
        except Exception:
            pass

        # Transparent Canvas Dimensions (Accommodates dynamic spring expansions, vertical emergence & rubber overshoot)
        self.canvas_w = 460
        self.canvas_h = 76
        self.resize(self.canvas_w, self.canvas_h)

        # States: "hidden", "recording", "voice_edit", "transcribing", "done"
        self.state = "hidden"
        self.status_text = ""
        self.sub_text = ""
        self.recording_start_time = 0.0

        # --- Physics-based Spring State (Apple Fluid Unfolding & Vertical Emergence) ---
        self.current_w = 36.0
        self.target_w = 36.0
        self.vel_w = 0.0

        self.current_h = 28.0
        self.target_h = 36.0
        self.vel_h = 0.0

        self.current_scale = 0.0
        self.target_scale = 0.0
        self.vel_scale = 0.0

        self.current_opacity = 0.0
        self.target_opacity = 0.0
        self.vel_opacity = 0.0

        self.current_y_offset = 18.0
        self.target_y_offset = 18.0
        self.vel_y = 0.0

        # --- Tactile Hover & Press Micro-Interactions ---
        self._is_hovered = False
        self.current_interaction_scale = 1.0
        self.target_interaction_scale = 1.0
        self.vel_interaction_scale = 0.0
        self.current_hover_glow = 0.0
        self.target_hover_glow = 0.0

        # --- Smooth RGB Accent Color Lerp & Progressive Icon Stroke ---
        self._accent_r = 235.0
        self._accent_g = 94.0
        self._accent_b = 56.0
        self.icon_draw_progress = 1.0

        # --- Frosted Optical Glass Backdrop Cache ---
        self._frosted_backdrop: Optional[QPixmap] = None
        self._last_backdrop_grab_time = 0.0

        # Audio visualizer reactive bars (Symmetrical 7-bar Apple Voice-Wave)
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

    def enterEvent(self, event):
        self._is_hovered = True
        self.target_interaction_scale = 1.028
        self.target_hover_glow = 1.0
        if self.state != "hidden" and not self.anim_timer.isActive():
            self.anim_timer.start(16)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.target_interaction_scale = 1.0
        self.target_hover_glow = 0.0
        if self.state != "hidden" and not self.anim_timer.isActive():
            self.anim_timer.start(16)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._win_start_pos = self.pos()
            self._is_dragging = False
            self._mouse_pressed = True
            self.target_interaction_scale = 0.96
            if self.state != "hidden" and not self.anim_timer.isActive():
                self.anim_timer.start(16)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._mouse_pressed and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if self._is_dragging or delta.manhattanLength() > 4:
                self._is_dragging = True
                self.move(self._win_start_pos + delta)
                event.accept()

    def mouseReleaseEvent(self, event):
        self.target_interaction_scale = 1.028 if self._is_hovered else 1.0
        self.vel_interaction_scale = 1.4
        if self.state != "hidden" and not self.anim_timer.isActive():
            self.anim_timer.start(16)

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
                self.target_w = 64.0 if is_minimal else self._compute_pill_width(min_w=(170.0 if is_en else 188.0), max_w=290.0, pad=82.0, use_done_fonts=False)
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
        Computes required target_w for the Apple single-axis horizontal layout
        (left indicator + primary status_text + breathing gap + right-aligned sub_text badge)
        so both strings sit comfortably on one line without clipping, clamped to [min_w, max_w].
        """
        t_font = self.done_title_font if use_done_fonts else self.title_font
        s_font = self.done_sub_font if use_done_fonts else self.sub_font
        text_w = QFontMetrics(t_font).horizontalAdvance(self.status_text or "")
        sub_w = QFontMetrics(s_font).horizontalAdvance(self.sub_text or "")
        single_line_px = float(text_w + (sub_w + 26.0 if sub_w > 0 else 0.0)) + pad
        needed_px = max(min_w, single_line_px)
        user_scale = max(0.85, min(1.15, getattr(config.hud, "scale_percent", 100) / 100.0))
        if user_scale < 1.0:
            needed_px = needed_px / user_scale
        return min(max_w, needed_px)

    def _capture_frosted_backdrop(self):
        """
        Captures the desktop patch directly behind the HUD before it appears and applies
        a two-pass smooth downscale/upscale Gaussian-like optical blur for true frosted glass.
        Safely skipped in headless/offscreen test environments.
        """
        try:
            app = QApplication.instance()
            if not app or app.platformName().lower() in ("offscreen", "minimal"):
                return
            now = time.perf_counter()
            if now - self._last_backdrop_grab_time < 0.35:
                return
            self._last_backdrop_grab_time = now

            scr = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
            if not scr:
                return
            raw_pix = scr.grabWindow(0, self.x(), self.y(), self.canvas_w, self.canvas_h)
            if raw_pix.isNull() or raw_pix.width() < 16 or raw_pix.height() < 16:
                return
            # Two-pass optical downscale/upscale blur (10x reduction -> smooth upscale)
            small_w = max(4, raw_pix.width() // 10)
            small_h = max(2, raw_pix.height() // 10)
            mid_w = max(8, raw_pix.width() // 4)
            mid_h = max(4, raw_pix.height() // 4)
            p1 = raw_pix.scaled(small_w, small_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p2 = p1.scaled(mid_w, mid_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._frosted_backdrop = p2.scaled(
                raw_pix.width(), raw_pix.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        except Exception:
            self._frosted_backdrop = None

    def _prepare_apple_emergence(self, is_minimal: bool):
        """
        Initializes Apple-style bottom-up spring emergence and seed-to-capsule unfolding
        when the HUD wakes up from a hidden or collapsed state.
        """
        self.target_h = 36.0
        self.target_scale = 1.0
        self.target_opacity = 1.0
        self.target_y_offset = 0.0

        fluid_enabled = getattr(config.hud, "fluid_animations", True) and not is_reduced_motion(config)
        if self.state in ("done", "prompt", "cancelled", "error"):
            self.icon_draw_progress = 0.0 if fluid_enabled else 1.0

        is_bottom = (getattr(config.hud, "position_mode", "bottom_center") == "bottom_center")
        if not self.isVisible() or self.current_scale < 0.15 or self.current_opacity < 0.15:
            # Snap initial accent color when waking from hidden so it starts clean
            accent = self._get_state_accent_color()
            self._accent_r = float(accent.red())
            self._accent_g = float(accent.green())
            self._accent_b = float(accent.blue())

            # Start as a compact optical seed lower down, rising and unfolding simultaneously
            self.current_w = 34.0 if is_minimal else 42.0
            self.current_h = 26.0
            self.current_scale = 0.44
            self.current_opacity = 0.0
            self.current_y_offset = 18.0 if is_bottom else 10.0

            self.vel_w = 85.0 if is_minimal else 155.0
            self.vel_h = 60.0
            self.vel_scale = 3.0
            self.vel_opacity = 4.2
            self.vel_y = -150.0 if is_bottom else -95.0

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
        self.target_w = 64.0 if is_minimal else self._compute_pill_width(min_w=172.0, max_w=260.0, pad=76.0, use_done_fonts=False)
        self._update_hud_position()
        if not self.isVisible():
            self._capture_frosted_backdrop()
        self._prepare_apple_emergence(is_minimal)

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
        base_w = 186.0 if is_en else 204.0
        self.target_w = 64.0 if is_minimal else self._compute_pill_width(min_w=base_w, max_w=290.0, pad=76.0, use_done_fonts=False)
        self._update_hud_position()
        if not self.isVisible():
            self._capture_frosted_backdrop()
        self._prepare_apple_emergence(is_minimal)

        self.show()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)
        self.update()

    def _trigger_morph_impulse(self, impulse_scale: float = 0.5):
        """Triggers an Apple-style elastic morph pulse, subtle upward buoyancy hop, content crossfade, and icon stroke draw."""
        if getattr(config.hud, "fluid_animations", True) and not is_reduced_motion(config):
            self.vel_scale = impulse_scale
            self.vel_y = -28.0 * impulse_scale
            self._is_crossfading = True
            self._crossfade_time = 0.0
            self.content_fade_alpha = 0.0
            if self.state in ("done", "prompt", "cancelled", "error"):
                self.icon_draw_progress = 0.0
            if not self.anim_timer.isActive():
                self.anim_timer.start(16)
        else:
            self.icon_draw_progress = 1.0

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
            self.target_y_offset = 0.0
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
        self._prepare_apple_emergence(is_minimal)
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
        self.target_y_offset = 0.0
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
        self.target_y_offset = 0.0

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
        self.target_y_offset = 0.0
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
        self._prepare_apple_emergence(is_minimal)
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

        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=200.0, max_w=360.0, pad=64.0)

        self._prepare_apple_emergence(is_minimal)
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
        self._prepare_apple_emergence(is_minimal)
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

        self.hide_timer.stop()

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=210.0, max_w=380.0, pad=64.0)

        self._prepare_apple_emergence(is_minimal)
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
        self.hide_timer.stop()
        is_minimal = getattr(config.hud, "minimal_mode", False)
        self.target_w = 40.0 if is_minimal else self._compute_pill_width(min_w=180.0, max_w=320.0, pad=62.0)
        self._prepare_apple_emergence(is_minimal)
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
        elif "api-key" in low_msg or "api key" in low_msg:
            from core.i18n import get_current_language
            self.status_text = "API-Key fehlt" if get_current_language() == "de" else "API Key Missing"
            self.sub_text = "In Einstellungen eintragen" if get_current_language() == "de" else "Configure in Settings"
        elif "ollama" in low_msg:
            from core.i18n import get_current_language
            self.status_text = "Ollama offline"
            self.sub_text = "Ollama starten" if get_current_language() == "de" else "Start Ollama"
        else:
            self.status_text = tr("hud_error")
            self.sub_text = err_msg[:48]

        is_minimal = getattr(config.hud, "minimal_mode", False)
        if is_minimal:
            self.target_w = 40.0
        else:
            self.target_w = self._compute_pill_width(min_w=196.0, max_w=380.0, pad=64.0)
        self._prepare_apple_emergence(is_minimal)

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
        self._prepare_apple_emergence(is_minimal)

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
        # Apple Dynamic Island / Siri Bubble retraction: fold back into a compact seed & sink downward
        is_bottom = (getattr(config.hud, "position_mode", "bottom_center") == "bottom_center")
        self.target_w = 34.0
        self.vel_w = -125.0
        self.target_y_offset = 16.0 if is_bottom else 8.0
        self.vel_y = 75.0
        self.target_scale = 0.0
        self.target_opacity = 0.0
        self.vel_scale = -3.2
        self.vel_opacity = -3.0
        self._is_hovered = False
        self.target_interaction_scale = 1.0
        self.target_hover_glow = 0.0
        self._frosted_backdrop = None
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

        # Micro-Crossfade interpolation (85ms smoothstep for ultra-fluid Apple content morphs)
        if self._is_crossfading and fluid_enabled:
            self._crossfade_time += dt
            progress = min(1.0, self._crossfade_time / 0.085)
            self.content_fade_alpha = progress * progress * (3.0 - 2.0 * progress)
            if self._crossfade_time >= 0.085:
                self._is_crossfading = False
                self.content_fade_alpha = 1.0
        else:
            self._is_crossfading = False
            self.content_fade_alpha = 1.0

        # Progressive badge icon stroke animation (~160ms)
        if fluid_enabled and self.icon_draw_progress < 1.0:
            self.icon_draw_progress = min(1.0, self.icon_draw_progress + max(0.014, dt) / 0.16)
        elif not fluid_enabled:
            self.icon_draw_progress = 1.0

        # Smooth RGB Accent Color Interpolation across states
        target_accent = self._get_state_accent_color()
        if fluid_enabled:
            lerp_t = min(1.0, dt * 14.0)
            self._accent_r += (float(target_accent.red()) - self._accent_r) * lerp_t
            self._accent_g += (float(target_accent.green()) - self._accent_g) * lerp_t
            self._accent_b += (float(target_accent.blue()) - self._accent_b) * lerp_t
        else:
            self._accent_r = float(target_accent.red())
            self._accent_g = float(target_accent.green())
            self._accent_b = float(target_accent.blue())

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
            cw = 27.0 - (11.5 * bounce_factor)
            ch = 29.0 - (11.5 * bounce_factor)
            cs = 28.0 - (11.5 * bounce_factor)
            cy_damp = 26.0 - (10.5 * bounce_factor)

            # 1. Width Spring (Apple capsule horizontal unfolding)
            kw = 330.0
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
            self.current_scale = max(0.0, min(1.22, self.current_scale + self.vel_scale * dt))
            if abs(self.current_scale - self.target_scale) < 0.005 and abs(self.vel_scale) < 0.01:
                self.current_scale = self.target_scale
                self.vel_scale = 0.0

            # 4. Opacity Spring
            fo = -290.0 * (self.current_opacity - self.target_opacity) - 24.0 * self.vel_opacity
            self.vel_opacity += fo * dt
            self.current_opacity = max(0.0, min(1.0, self.current_opacity + self.vel_opacity * dt))
            if abs(self.current_opacity - self.target_opacity) < 0.005 and abs(self.vel_opacity) < 0.01:
                self.current_opacity = self.target_opacity
                self.vel_opacity = 0.0

            # 5. Vertical Emergence / Buoyancy Spring (Apple bottom-edge rise & sink)
            ky = 310.0
            fy = -ky * (self.current_y_offset - self.target_y_offset) - cy_damp * self.vel_y
            self.vel_y += fy * dt
            self.current_y_offset = max(-10.0, min(28.0, self.current_y_offset + self.vel_y * dt))
            if abs(self.current_y_offset - self.target_y_offset) < 0.15 and abs(self.vel_y) < 0.2:
                self.current_y_offset = self.target_y_offset
                self.vel_y = 0.0

            # 6. Tactile Hover & Click Interaction Scale Spring
            k_int = 390.0
            f_int = -k_int * (self.current_interaction_scale - self.target_interaction_scale) - 24.0 * self.vel_interaction_scale
            self.vel_interaction_scale += f_int * dt
            self.current_interaction_scale = max(0.90, min(1.10, self.current_interaction_scale + self.vel_interaction_scale * dt))
            if abs(self.current_interaction_scale - self.target_interaction_scale) < 0.002 and abs(self.vel_interaction_scale) < 0.01:
                self.current_interaction_scale = self.target_interaction_scale
                self.vel_interaction_scale = 0.0

            self.current_hover_glow += (self.target_hover_glow - self.current_hover_glow) * min(1.0, dt * 14.0)

        else:
            # Instant rigid fallback / Reduced-Motion
            self.current_w = self.target_w
            self.current_h = self.target_h
            self.current_scale = self.target_scale
            self.current_opacity = self.target_opacity
            self.current_y_offset = self.target_y_offset
            self.current_interaction_scale = self.target_interaction_scale
            self.current_hover_glow = self.target_hover_glow

        # Check if fully hidden and settled -> Stop timer to save 100% CPU!
        if self.state == "hidden" and self.current_scale < 0.02 and self.current_opacity < 0.02:
            self.hide()
            self.anim_timer.stop()
            return

        if self.state in ("recording", "voice_edit"):
            if self.state == "recording":
                dur = int(time.time() - self.recording_start_time)
                m, s = divmod(dur, 60)
                self.sub_text = f"{m:02d}:{s:02d}"

            self.current_rms += (self.target_rms - self.current_rms) * 0.35
            if self.current_rms < 0.03:
                # Silence / quiet room: calm uniform micro-dots with zero jitter
                for i in range(self.num_bars):
                    self.bar_heights[i] += (0.15 - self.bar_heights[i]) * 0.25
            else:
                # Active speech: symmetrical Apple Voice-Wave bell envelope radiating from center bar (index 3)
                t = time.time() * (2.5 if not fluid_enabled else 8.2)
                weights_7 = (0.38, 0.64, 0.88, 1.00, 0.88, 0.64, 0.38)
                for i in range(self.num_bars):
                    w_factor = weights_7[i] if i < len(weights_7) else 1.0
                    dist_from_center = abs(i - 3)
                    wave = math.sin(t - dist_from_center * 0.55) * 0.25 + 0.75 if fluid_enabled else 0.85
                    target_h = max(0.15, min(1.0, self.current_rms * wave * 1.28 * w_factor))
                    self.bar_heights[i] += (target_h - self.bar_heights[i]) * 0.45

        elif self.state == "transcribing":
            # Smooth optical caustic sweep across the glass lens (~3.2 seconds total period)
            if fluid_enabled:
                self.shimmer_phase = (self.shimmer_phase + 0.009) % 2.2

        self.update()

    def _get_state_accent_color(self) -> QColor:
        """Returns the semantic accent QColor for the active HUD state."""
        if self.state == "recording":
            return QColor("#eb5e38")  # Velodictum Coral
        elif self.state in ("voice_edit", "transcribing"):
            return QColor("#7c83e0")  # Muted Indigo
        elif self.state == "done":
            return QColor("#34d399")  # Mint / Emerald
        elif self.state == "prompt":
            return QColor("#f59e0b")  # Amber
        elif self.state in ("cancelled", "error"):
            return QColor("#ef4444")  # Crimson
        return QColor("#64748b")

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

        # Respect user's HUD glass density setting (65% to 95%, default 78%)
        raw_op = getattr(config.hud, "opacity_percent", 78)
        glass_density = max(0.55, min(0.96, (raw_op if isinstance(raw_op, (int, float)) else 78) / 100.0))
        norm_density = (glass_density - 0.55) / 0.41  # 0.0 (lightest glass) -> 1.0 (densest smoked glass)

        # Apple Anisotropic Squash & Stretch (couples horizontal expansion vel_w and vertical rise vel_y)
        if fluid_enabled:
            squish_y = max(-0.045, min(0.045, -self.vel_w * 0.00010 - self.vel_y * 0.00018))
            squish_x = max(-0.035, min(0.035, self.vel_y * 0.00012))
            y_off = self.current_y_offset
        else:
            squish_y = 0.0
            squish_x = 0.0
            y_off = 0.0

        # Exact integer pixel snapping + tactile hover/press scale + lateral refusal shake + vertical rise
        interact_s = self.current_interaction_scale
        draw_w = round(max(16.0, self.current_w * (1.0 + squish_x) * self.current_scale * interact_s * user_scale))
        draw_h = round(max(16.0, self.current_h * (1.0 + squish_y) * self.current_scale * interact_s * user_scale))
        rx = round(cx - draw_w / 2.0 + self.shake_offset)
        ry = round(max(2.0, min(h - draw_h - 4.0, cy - draw_h / 2.0 + y_off)))

        rect = QRectF(rx, ry, draw_w, draw_h)
        radius = draw_h / 2.0

        pill_path = QPainterPath()
        pill_path.addRoundedRect(rect, radius, radius)

        # Live smoothly interpolated semantic accent color
        live_accent = QColor(
            max(0, min(255, int(round(self._accent_r)))),
            max(0, min(255, int(round(self._accent_g)))),
            max(0, min(255, int(round(self._accent_b)))),
        )
        is_minimal = getattr(config.hud, "minimal_mode", False)
        vocal_bloom = max(0.0, min(1.0, (self.current_rms - 0.15) / 0.65)) if self.state in ("recording", "voice_edit") else 0.0

        # =========================================================================
        # 0. Exterior Soft Drop Shadow (Clipped strictly OUTSIDE the glass pill)
        #    Keeps the semi-transparent glass interior completely clean and un-mudded.
        # =========================================================================
        painter.save()
        canvas_path = QPainterPath()
        canvas_path.addRect(0.0, 0.0, w, h)
        painter.setClipPath(canvas_path.subtracted(pill_path))
        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QBrush(QColor(2, 4, 10, 48)))
        painter.drawRoundedRect(rect.adjusted(-2.0, 0.5, 2.0, 4.5), radius + 2.0, radius + 2.0)
        painter.setBrush(QBrush(QColor(2, 4, 10, 82)))
        painter.drawRoundedRect(rect.adjusted(-0.8, 1.0, 0.8, 2.5), radius + 0.8, radius + 0.8)
        painter.restore()

        # =========================================================================
        # 1. Frosted Backdrop Blur + Clean, Noble Smoked-Glass Capsule Body
        #    Deep grounded obsidian-black at the top fading smoothly and neutrally
        #    into a calm, semi-transparent smoked glass lower half — zero middle glare!
        # =========================================================================
        painter.save()
        painter.setClipPath(pill_path)
        painter.setPen(Qt.PenStyle.NoPen)

        # 1a. Optical Frosted Backdrop Blur (softens underlying sharp desktop text)
        if self._frosted_backdrop is not None and not self._frosted_backdrop.isNull():
            painter.save()
            painter.setOpacity(self.current_opacity * (0.42 * (1.0 - norm_density * 0.45)))
            src_rect = QRectF(rx, ry, draw_w, draw_h)
            painter.drawPixmap(rect, self._frosted_backdrop, src_rect)
            painter.restore()

        top_alpha = int(min(252, 232 + 18 * norm_density))
        upper_mid_alpha = int(min(242, 206 + 32 * norm_density))
        lower_mid_alpha = int(min(220, 158 + 56 * norm_density))
        bottom_glass_alpha = int(min(198, 118 + 72 * norm_density))

        surf_grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        surf_grad.setColorAt(0.00, QColor(5, 6, 10, top_alpha))
        surf_grad.setColorAt(0.38, QColor(9, 11, 17, upper_mid_alpha))
        surf_grad.setColorAt(0.72, QColor(15, 19, 28, lower_mid_alpha))
        surf_grad.setColorAt(1.00, QColor(22, 27, 39, bottom_glass_alpha))
        painter.setBrush(QBrush(surf_grad))
        painter.drawRect(rect)

        # =========================================================================
        # 2. Subtle Lower Glass Lens Cushion (Delicate neutral light refraction at bottom)
        # =========================================================================
        hover_boost = int(10 * self.current_hover_glow)
        cushion_grad = QLinearGradient(rect.left(), rect.top() + draw_h * 0.58, rect.left(), rect.bottom())
        cushion_grad.setColorAt(0.00, QColor(255, 255, 255, 0))
        cushion_grad.setColorAt(0.75, QColor(255, 255, 255, 6 + hover_boost // 2))
        cushion_grad.setColorAt(1.00, QColor(255, 255, 255, 20 + hover_boost))
        painter.setBrush(QBrush(cushion_grad))
        painter.drawRect(rect)

        # =========================================================================
        # 3. Transcribing Subtle Glass Sweep (Only during processing)
        # =========================================================================
        if self.state == "transcribing" and fluid_enabled and self.shimmer_phase <= 1.0:
            eased_progress = (1.0 - math.cos(self.shimmer_phase * math.pi)) * 0.5
            shimmer_x = rect.left() - 40.0 + (rect.width() + 80.0) * eased_progress
            shimmer_grad = QLinearGradient(shimmer_x - 35.0, rect.top(), shimmer_x + 35.0, rect.bottom())
            shimmer_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            shimmer_grad.setColorAt(0.5, QColor(200, 210, 255, 16))
            shimmer_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(shimmer_grad))
            painter.drawRect(rect)

        painter.restore()  # End interior pill_path clip

        # =========================================================================
        # 4. Ultra-Fine Specular Glass Rim (1.0px single neutral-glass border)
        #    Subtle and dark at the top edge, smoothly catching neutral light along
        #    the bottom curve with only a whisper (15%) of smoothly lerped state accent.
        # =========================================================================
        painter.setBrush(Qt.BrushStyle.NoBrush)

        rim_hover = int(22 * self.current_hover_glow)
        rim_grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        # Top edge: quiet, grounded specular sheen
        rim_grad.setColorAt(0.00, QColor(255, 255, 255, min(255, 22 + rim_hover // 2)))
        # Upper-mid sides: subtle dark glass edge
        rim_grad.setColorAt(0.40, QColor(255, 255, 255, min(255, 18 + rim_hover // 3)))
        # Lower sides: soft neutral glass reflection with a 15% whisper of live state color
        side_r = int(255 * 0.85 + live_accent.red() * 0.15)
        side_g = int(255 * 0.85 + live_accent.green() * 0.15)
        side_b = int(255 * 0.85 + live_accent.blue() * 0.15)
        rim_grad.setColorAt(0.78, QColor(side_r, side_g, side_b, min(255, 48 + rim_hover)))
        # Bottom edge: clean, noble optical glass highlight (Screenshot 2 bottom edge)
        rim_grad.setColorAt(1.00, QColor(side_r, side_g, side_b, min(255, 84 + rim_hover)))

        border_pen = QPen(QBrush(rim_grad), 1.0)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), max(1.0, radius - 0.5), max(1.0, radius - 0.5))

        # =========================================================================
        # 5. Coordinated Single-Axis Content Rendering
        #    (Symmetrical Apple Voice-Wave, Animated Icon Strokes & Airy Single-Line Text)
        # =========================================================================
        threshold_w = 28.0 if is_minimal else 75.0

        if draw_w > threshold_w and self.current_scale > 0.35:
            pill_cx = rx + draw_w / 2.0
            progress = min(1.0, max(0.0, (draw_w - 30.0) / max(1.0, self.target_w - 30.0)))
            eased_t = progress * progress * (3.0 - 2.0 * progress)
            center_origin = pill_cx - 24.0
            content_left = round(center_origin * (1.0 - eased_t) + rx * eased_t)
            # Content tracks the rising/sinking capsule center plus a subtle Apple upward settle during crossfades
            content_slide_y = (1.0 - self.content_fade_alpha) * 2.5 if (fluid_enabled and self._is_crossfading) else 0.0
            center_y = round(ry + draw_h / 2.0 + content_slide_y)

            content_alpha = min(1.0, max(0.0, (self.current_opacity - 0.15) / 0.85))
            painter.save()
            painter.setOpacity(self.current_opacity * content_alpha * self.content_fade_alpha)
            painter.setClipPath(pill_path)

            def _draw_crisp_text(x_pos: int, y_pos: int, text_str: str, font: QFont, fg_color: QColor):
                """Renders text with a subtle backing shadow for clean legibility on translucent glass."""
                painter.setFont(font)
                painter.setPen(QColor(2, 4, 10, 165))
                painter.drawText(x_pos, y_pos + 1, text_str)
                painter.setPen(fg_color)
                painter.drawText(x_pos, y_pos, text_str)

            def _draw_single_axis_row(
                text_left_x: int,
                t_font: QFont,
                s_font: QFont,
                title_col: QColor,
                sub_col: QColor,
                show_sub_pill: bool = True,
            ):
                """
                Renders primary status_text and secondary sub_text on a single horizontal axis (center_y)
                with generous negative space above and below, plus a subtle recessed glass pill for sub_text.
                """
                right_edge = int(rx + draw_w - 12)
                avail_w = max(20, right_edge - text_left_x)
                tfm = QFontMetrics(t_font)
                sfm = QFontMetrics(s_font)

                title_str = self.status_text or ""
                sub_str = self.sub_text or ""

                title_y = int(round(center_y + (tfm.ascent() - tfm.descent()) / 2.0))
                sub_y = int(round(center_y + (sfm.ascent() - sfm.descent()) / 2.0))

                if not sub_str:
                    disp_title = tfm.elidedText(title_str, Qt.TextElideMode.ElideRight, avail_w)
                    _draw_crisp_text(text_left_x, title_y, disp_title, t_font, title_col)
                    return

                raw_title_w = tfm.horizontalAdvance(title_str)
                raw_sub_w = sfm.horizontalAdvance(sub_str)
                pill_pad_x = 6 if show_sub_pill else 0
                gap = 10

                if raw_title_w + gap + raw_sub_w + pill_pad_x * 2 <= avail_w:
                    disp_title = title_str
                    disp_sub = sub_str
                else:
                    max_sub_w = max(34, min(raw_sub_w, int(avail_w * 0.46)))
                    disp_sub = sfm.elidedText(sub_str, Qt.TextElideMode.ElideRight, max_sub_w)
                    actual_sub_w = sfm.horizontalAdvance(disp_sub)
                    max_title_w = max(24, avail_w - actual_sub_w - pill_pad_x * 2 - gap)
                    disp_title = tfm.elidedText(title_str, Qt.TextElideMode.ElideRight, max_title_w)

                actual_sub_w = sfm.horizontalAdvance(disp_sub)
                _draw_crisp_text(text_left_x, title_y, disp_title, t_font, title_col)

                if actual_sub_w > 0:
                    if show_sub_pill:
                        tag_h = 17.0
                        tag_w = float(actual_sub_w + pill_pad_x * 2)
                        tag_rect = QRectF(right_edge - tag_w, center_y - tag_h / 2.0, tag_w, tag_h)
                        painter.setPen(QPen(QColor(255, 255, 255, 18), 0.7))
                        painter.setBrush(QBrush(QColor(255, 255, 255, 11)))
                        painter.drawRoundedRect(tag_rect, tag_h / 2.0, tag_h / 2.0)
                        sub_x = int(round(right_edge - pill_pad_x - actual_sub_w))
                    else:
                        sub_x = int(round(right_edge - actual_sub_w))
                    _draw_crisp_text(sub_x, sub_y, disp_sub, s_font, sub_col)

            if self.state in ("recording", "voice_edit"):
                # Pure symmetrical 7-bar Apple Voice-Wave (merged dot + bars) using live lerped accent color
                top_r = min(255, int(live_accent.red() + 20 * vocal_bloom))
                top_g = min(255, int(live_accent.green() + 34 * vocal_bloom))
                top_b = min(255, int(live_accent.blue() + 24 * vocal_bloom))
                top_color = QColor(top_r, top_g, top_b, 255)
                bot_color = QColor(
                    max(0, int(live_accent.red() * 0.82)),
                    max(0, int(live_accent.green() * 0.78)),
                    max(0, int(live_accent.blue() * 0.80)),
                    238,
                )

                if is_minimal:
                    # Symmetrical 7-bar Apple Voice-Wave centered dead-center inside the minimal capsule
                    bar_w = 2.4
                    gap = 2.1
                    bars_total_w = self.num_bars * bar_w + (self.num_bars - 1) * gap
                    wave_x = pill_cx - bars_total_w / 2.0
                    max_bar_h = 15.0
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

                else:
                    # Symmetrical 7-bar Apple Voice-Wave on the left + single-axis label & timer pill
                    wave_x = content_left + 15.0
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

                    sub_col = QColor("#a5b4fc") if self.state == "voice_edit" else QColor("#cbd5e1")
                    _draw_single_axis_row(
                        int(content_left + 53),
                        self.title_font,
                        self.sub_font,
                        QColor("#f8fafc"),
                        sub_col,
                        show_sub_pill=True,
                    )

            elif self.state == "transcribing":
                angle = int((time.time() * 240) % 360) if fluid_enabled else 45
                spin_cx = pill_cx if is_minimal else (content_left + 20.0)
                spin_rect = QRectF(spin_cx - 6.5, center_y - 6.5, 13.0, 13.0)

                track_pen = QPen(QColor(148, 163, 184, 42), 1.5)
                painter.setPen(track_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(spin_rect)

                spin_pen = QPen(live_accent, 1.8)
                spin_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(spin_pen)
                painter.drawArc(spin_rect, -angle * 16, 220 * 16)

                if not is_minimal:
                    _draw_single_axis_row(
                        int(content_left + 35),
                        self.title_font,
                        self.sub_font,
                        QColor("#f8fafc"),
                        QColor("#a5b4fc"),
                        show_sub_pill=True,
                    )

            elif self.state == "done":
                badge_cx = float(pill_cx) if is_minimal else float(content_left + 18)
                painter.setBrush(QBrush(live_accent))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(badge_cx, float(center_y)), 6.2, 6.2)

                # Progressive animated checkmark stroke
                p_icon = max(0.0, min(1.0, self.icon_draw_progress))
                ep = p_icon * p_icon * (3.0 - 2.0 * p_icon)
                painter.setPen(QPen(QColor("#060911"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p0 = QPointF(badge_cx - 3.0, float(center_y) + 0.1)
                p1 = QPointF(badge_cx - 0.8, float(center_y) + 2.3)
                p2 = QPointF(badge_cx + 3.1, float(center_y) - 2.1)
                if ep > 0.01:
                    seg1 = min(1.0, ep / 0.42)
                    p1_cur = QPointF(p0.x() + (p1.x() - p0.x()) * seg1, p0.y() + (p1.y() - p0.y()) * seg1)
                    painter.drawLine(p0, p1_cur)
                if ep > 0.42:
                    seg2 = min(1.0, (ep - 0.42) / 0.58)
                    p2_cur = QPointF(p1.x() + (p2.x() - p1.x()) * seg2, p1.y() + (p2.y() - p1.y()) * seg2)
                    painter.drawLine(p1, p2_cur)

                if not is_minimal:
                    _draw_single_axis_row(
                        int(content_left + 33),
                        self.done_title_font,
                        self.done_sub_font,
                        QColor("#f8fafc"),
                        QColor("#34d399"),
                        show_sub_pill=True,
                    )

            elif self.state == "prompt":
                badge_cx = float(pill_cx) if is_minimal else float(content_left + 18)
                painter.setBrush(QBrush(live_accent))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(badge_cx, float(center_y)), 6.2, 6.2)

                p_icon = max(0.0, min(1.0, self.icon_draw_progress))
                ep = p_icon * p_icon * (3.0 - 2.0 * p_icon)
                painter.setPen(QPen(QColor("#060911"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                if ep > 0.01:
                    seg1 = min(1.0, ep / 0.5)
                    painter.drawLine(QPointF(badge_cx - 3.0, float(center_y)), QPointF(badge_cx - 3.0 + 6.0 * seg1, float(center_y)))
                if ep > 0.5:
                    seg2 = min(1.0, (ep - 0.5) / 0.5)
                    painter.drawLine(QPointF(badge_cx, float(center_y) - 3.0), QPointF(badge_cx, float(center_y) - 3.0 + 6.0 * seg2))

                if not is_minimal:
                    _draw_single_axis_row(
                        int(content_left + 33),
                        self.done_title_font,
                        self.done_sub_font,
                        QColor("#fef08a"),
                        QColor("#f59e0b"),
                        show_sub_pill=True,
                    )

            elif self.state in ("cancelled", "error"):
                is_cancel = (self.state == "cancelled")
                sub_color = QColor("#f87171") if not is_cancel else QColor("#fda4af")
                badge_cx = float(pill_cx) if is_minimal else float(content_left + 18)

                painter.setBrush(QBrush(live_accent))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(badge_cx, float(center_y)), 6.2, 6.2)

                p_icon = max(0.0, min(1.0, self.icon_draw_progress))
                ep = p_icon * p_icon * (3.0 - 2.0 * p_icon)
                painter.setPen(QPen(QColor("#ffffff"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                if ep > 0.01:
                    seg1 = min(1.0, ep / 0.5)
                    painter.drawLine(
                        QPointF(badge_cx - 2.8, float(center_y) - 2.8),
                        QPointF(badge_cx - 2.8 + 5.6 * seg1, float(center_y) - 2.8 + 5.6 * seg1),
                    )
                if ep > 0.5:
                    seg2 = min(1.0, (ep - 0.5) / 0.5)
                    painter.drawLine(
                        QPointF(badge_cx + 2.8, float(center_y) - 2.8),
                        QPointF(badge_cx + 2.8 - 5.6 * seg2, float(center_y) - 2.8 + 5.6 * seg2),
                    )

                if not is_minimal:
                    _draw_single_axis_row(
                        int(content_left + 33),
                        self.done_title_font,
                        self.done_sub_font,
                        QColor("#f8fafc"),
                        sub_color,
                        show_sub_pill=True,
                    )

            painter.restore()

        painter.end()
