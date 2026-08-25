"""
Velodictum - Minimalist Studio Edition Dashboard (Polished)
High-end desktop interface built on neutral slate/zinc design system,
fully dynamic GPU detection, dedicated unclipped Preset Card widgets,
seamless surface blends (no harsh black boxes), and quiet typography.
"""
import math
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, pyqtSignal, QUrl
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QLinearGradient,
    QKeyEvent, QDesktopServices
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTabWidget, QComboBox, QCheckBox, QLineEdit,
    QApplication, QGridLayout, QScrollArea, QSizePolicy, QDialog, QStackedWidget,
    QSlider
)
import pyperclip

from config import config, PROFILES
from gui.assets import create_app_icon
from gui.signals import signals
from audio_recorder import AudioRecorder
from gpu_monitor import GPUMonitor
from ai_formatter import MODES
from window_context import get_active_window_context
from custom_vocabulary import vocab_manager
from model_manager import model_manager
from smart_snippets import snippet_manager
from app_profiles import app_profile_manager
import autostart_manager
from style_profiles import TONE_PROFILES
from sound_effects import SOUND_THEMES, preview_cue
from mobile_bridge_server import get_local_ip
from formatting_providers import (
    detect_provider,
    categorize_models,
    UniversalApiProvider,
    OllamaProvider,
    OpenAIProvider,
    GeminiProvider,
    GroqProvider,
    MODEL_TIERS,
    get_model_details,
)
from gui.theme import get_stylesheet, apply_window_backdrop
from i18n import tr, set_current_language, get_current_language


# =========================================================================
# 1. Custom Interactive Preset Cards (Zero Layout-Squashing / No Clipping)
# =========================================================================

class ModelPresetCard(QFrame):
    """
    Dedicated unclipped hardware model preset card.
    Avoids QPushButton internal child-layout squashing and font overlap bugs.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, name: str, tag: str, desc: str, led_color: str, led_text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #ffffff; background: transparent;")

        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(
            "font-size: 9.5px; font-weight: 600; color: #8a8a96; background: rgba(255, 255, 255, 0.05); "
            "padding: 1px 5px; border-radius: 3px;"
        )

        top_row.addWidget(self.lbl_name)
        top_row.addWidget(self.lbl_tag)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-size: 11px; color: #94949e; background: transparent;")
        layout.addWidget(self.lbl_desc)

        self.lbl_led = QLabel(f'<span style="color:{led_color}; font-size:10px; font-weight:600;">{led_text}</span>')
        self.lbl_led.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_led.setStyleSheet("background: transparent;")
        layout.addWidget(self.lbl_led)

        self.update_style()

    def update_led(self, color: str, text: str):
        self.lbl_led.setText(f'<span style="color:{color}; font-size:10px; font-weight:600;">{text}</span>')

    def set_selected(self, val: bool):
        self.selected = val
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                "ModelPresetCard { background-color: #172033; border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 7px; }"
            )
            self.lbl_name.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #ffffff; background: transparent;")
            self.lbl_desc.setStyleSheet("font-size: 11px; color: #bae6fd; background: transparent;")
        else:
            self.setStyleSheet(
                "ModelPresetCard { background-color: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.045); border-radius: 7px; } "
                "ModelPresetCard:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.09); }"
            )
            self.lbl_name.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #eeeeef; background: transparent;")
            self.lbl_desc.setStyleSheet("font-size: 11px; color: #94949e; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class ModePresetCard(QFrame):
    """
    Dedicated unclipped operational mode card for Studio Tab.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #eeeeef; background: transparent;")
        layout.addWidget(self.lbl_title)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #787884; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def set_selected(self, val: bool):
        self.selected = val
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                "ModePresetCard { background-color: #172033; border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 7px; }"
            )
            self.lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #ffffff; background: transparent;")
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #bae6fd; background: transparent;")
        else:
            self.setStyleSheet(
                "ModePresetCard { background-color: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 7px; } "
                "ModePresetCard:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.08); }"
            )
            self.lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #eeeeef; background: transparent;")
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #787884; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class TonePresetCard(QFrame):
    """
    Dedicated unclipped tone profile card for Studio Tab.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, tag: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #eeeeef; background: transparent;")
        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(
            "font-size: 9px; font-weight: 600; color: #8a8a96; background: rgba(255, 255, 255, 0.05); "
            "padding: 1px 4px; border-radius: 3px;"
        )
        top.addWidget(self.lbl_title)
        top.addWidget(self.lbl_tag)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("font-size: 10.5px; color: #787884; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def set_selected(self, val: bool):
        self.selected = val
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                "TonePresetCard { background-color: #172033; border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 7px; }"
            )
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #ffffff; background: transparent;")
            self.lbl_sub.setStyleSheet("font-size: 10.5px; color: #bae6fd; background: transparent;")
        else:
            self.setStyleSheet(
                "TonePresetCard { background-color: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 7px; } "
                "TonePresetCard:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.08); }"
            )
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #eeeeef; background: transparent;")
            self.lbl_sub.setStyleSheet("font-size: 10.5px; color: #787884; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class LevelCalibrationWidget(QFrame):
    """
    Live Audio Calibration Helper & Visual Peak Meter.
    Shows current microphone signal levels with 3 color-coded target zones:
    1. Blue (< 30% / < -28 dB): Zu leise
    2. Emerald Green (30% - 80% / -24 dB to -6 dB): Optimaler Whisper-Pegel
    3. Red (> 80% / > -3 dB): Clipping-Gefahr
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.current_level = 0.0
        self.peak_level = 0.0
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._decay)
        self.decay_timer.start(30)
        self.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px;")

    def update_level(self, rms: float):
        gain = getattr(config.audio, "input_gain", 1.0)
        eff_level = min(1.0, rms * 4.5 * gain)
        self.current_level = eff_level
        if eff_level > self.peak_level:
            self.peak_level = eff_level
        self.update()

    def _decay(self):
        if self.peak_level > 0.005:
            self.peak_level = max(0.0, self.peak_level - 0.025)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        bar_x = 12.0
        bar_y = 10.0
        bar_w = max(40.0, w - 24.0)
        bar_h = 10.0

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 26)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3.0, 3.0)

        # 3-Zone target brackets
        z1_w = bar_w * 0.30
        painter.setBrush(QBrush(QColor(56, 189, 248, 25)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, z1_w, bar_h), 3.0, 3.0)

        z2_x = bar_x + z1_w
        z2_w = bar_w * 0.50
        painter.setBrush(QBrush(QColor(16, 185, 129, 45)))
        painter.drawRoundedRect(QRectF(z2_x, bar_y, z2_w, bar_h), 0.0, 0.0)

        z3_x = z2_x + z2_w
        z3_w = bar_w - z1_w - z2_w
        painter.setBrush(QBrush(QColor(239, 68, 68, 35)))
        painter.drawRoundedRect(QRectF(z3_x, bar_y, z3_w, bar_h), 3.0, 3.0)

        fill_w = max(0.0, min(bar_w, bar_w * self.current_level))
        if fill_w > 0:
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            grad.setColorAt(0.0, QColor(56, 189, 248))
            grad.setColorAt(0.30, QColor(16, 185, 129))
            grad.setColorAt(0.80, QColor(234, 179, 8))
            grad.setColorAt(0.95, QColor(239, 68, 68))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 3.0, 3.0)

        if self.peak_level > 0.01:
            px = bar_x + min(bar_w - 2.0, bar_w * self.peak_level)
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.8))
            painter.drawLine(int(px), int(bar_y - 1), int(px), int(bar_y + bar_h + 1))

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor("#71717a"))
        painter.drawText(int(bar_x), int(bar_y + bar_h + 16), tr("meter_too_quiet"))

        painter.setPen(QColor("#10b981"))
        painter.drawText(int(z2_x + 6), int(bar_y + bar_h + 16), tr("meter_optimal"))

        painter.setPen(QColor("#f87171"))
        painter.drawText(int(z3_x - 10), int(bar_y + bar_h + 16), tr("meter_clipping"))
        painter.end()


class ModelPriorityCard(QFrame):
    """
    Selectable 3-Tier Priority Card (Schnelligkeit vs Ausgewogen vs Höchste Qualität).
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, badge: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.lbl_title = QLabel(title)
        self.lbl_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #eeeeef; background: transparent;")

        self.lbl_badge = QLabel(badge)
        self.lbl_badge.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_badge.setStyleSheet(
            "font-size: 9px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.1); "
            "padding: 1px 5px; border-radius: 3px; border: 1px solid rgba(56, 189, 248, 0.25);"
        )
        top.addWidget(self.lbl_title)
        top.addWidget(self.lbl_badge)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("font-size: 10px; color: #787884; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def update_texts(self, title: str, badge: str, sub: str):
        self.lbl_title.setText(title)
        self.lbl_badge.setText(badge)
        self.lbl_sub.setText(sub)

    def set_selected(self, val: bool):
        self.selected = bool(val)
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                "QFrame { background-color: #172033; border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 7px; }"
            )
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #ffffff; background: transparent;")
            self.lbl_badge.setStyleSheet(
                "font-size: 9px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.2); "
                "padding: 1px 5px; border-radius: 3px; border: 1px solid rgba(56, 189, 248, 0.45);"
            )
            self.lbl_sub.setStyleSheet("font-size: 10px; color: #bae6fd; background: transparent; font-weight: 400;")
        else:
            self.setStyleSheet(
                "QFrame { background-color: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.045); border-radius: 7px; } "
                "QFrame:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.09); }"
            )
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #eeeeef; background: transparent;")
            self.lbl_badge.setStyleSheet(
                "font-size: 9px; font-weight: 600; color: #8a8a96; background: rgba(255, 255, 255, 0.05); "
                "padding: 1px 5px; border-radius: 3px; border: none;"
            )
            self.lbl_sub.setStyleSheet("font-size: 10px; color: #787884; background: transparent; font-weight: 400;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class CollapsibleSettingsCard(QFrame):
    """
    Clean, modern accordion card with click-to-toggle header, live status badge, description, and hover effects.
    """
    def __init__(self, title: str, summary: str = "", description: str = "", is_expanded: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_expanded = is_expanded

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(6)

        # Header (Clickable)
        self.header_widget = QWidget()
        self.header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("section_title")
        self.lbl_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff; background: transparent;")

        self.lbl_summary = QLabel(summary)
        self.lbl_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_summary.setStyleSheet("font-size: 11px; color: #71717a; font-weight: 500; background: transparent;")

        self.lbl_toggle = QLabel("[-]" if is_expanded else "[+]")
        self.lbl_toggle.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8; background: transparent;")

        h_layout.addWidget(self.lbl_title)
        h_layout.addWidget(self.lbl_summary)
        h_layout.addStretch()
        h_layout.addWidget(self.lbl_toggle)

        self.main_layout.addWidget(self.header_widget)

        # Subdued Description beneath title
        if description:
            self.lbl_desc = QLabel(description)
            self.lbl_desc.setTextFormat(Qt.TextFormat.PlainText)
            self.lbl_desc.setWordWrap(True)
            self.lbl_desc.setStyleSheet("font-size: 11px; color: #828290; margin-top: -2px; margin-bottom: 4px; background: transparent;")
            self.main_layout.addWidget(self.lbl_desc)
        else:
            self.lbl_desc = None

        # Content Body
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 4, 0, 0)
        self.body_layout.setSpacing(10)
        self.body_widget.setVisible(is_expanded)

        self.main_layout.addWidget(self.body_widget)

        self.header_widget.mousePressEvent = self._on_header_clicked

    def _on_header_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def set_summary(self, text: str):
        self.lbl_summary.setText(text)

    def set_description(self, text: str):
        if self.lbl_desc:
            self.lbl_desc.setText(text)

    def toggle(self):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, val: bool):
        self.is_expanded = val
        self.body_widget.setVisible(val)
        self.lbl_toggle.setText("[-]" if val else "[+]")
        if val:
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff; background: transparent;")
        else:
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #d4d4d8; background: transparent;")


# =========================================================================
# 2. Hotkey Capture Modal Dialog
# =========================================================================

class HotkeyCaptureDialog(QDialog):
    """Clean minimalist dialog to record key combinations without clutter."""
    def __init__(self, current_key="f8", parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("hotkey_dialog_title"))
        self.setFixedSize(380, 190)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            "QDialog { background-color: #131317; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }"
            "QLabel { color: #f1f1f4; font-size: 12px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel(tr("hotkey_dialog_heading"))
        title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(tr("hotkey_dialog_sub"))
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #787884; font-size: 11px;")
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        self.key_display = QLabel(current_key.upper())
        self.key_display.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.04); color: #38bdf8; font-weight: 700; font-size: 13px; "
            "letter-spacing: 0.8px; padding: 7px 16px; border-radius: 5px; border: 1px solid rgba(255, 255, 255, 0.08);"
        )
        layout.addWidget(self.key_display, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_cancel = QPushButton(tr("cancel"))
        self.btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(tr("save"))
        self.btn_save.setObjectName("btn_primary")
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_save.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        self.captured_combo = current_key.lower()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.captured_combo:
                self.accept()
            return

        parts = []
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("cmd")

        if key == Qt.Key.Key_Space:
            parts.append("space")
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            parts.append(f"f{key - Qt.Key.Key_F1 + 1}")
        elif key == Qt.Key.Key_CapsLock:
            parts.append("caps_lock")
        else:
            text = event.text().strip().lower()
            if text and text not in ("\t", "\r", "\n", " ") and text not in parts:
                parts.append(text)

        unique_parts = []
        for p in parts:
            if p not in unique_parts:
                unique_parts.append(p)

        if unique_parts:
            self.captured_combo = "+".join(unique_parts)
            self.key_display.setText(" + ".join(p.upper() for p in unique_parts))


# =========================================================================
# 3. Minimalist Audio Spectrum Visualizer Widget
# =========================================================================

class HeroWaveformWidget(QWidget):
    """
    Calm 36-bar Audio Spectrum Analyzer.
    Renders steady ambient presence or real-time voice reactivity at 60 FPS.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.num_bars = 36
        self.bar_heights = [0.06] * self.num_bars
        self.current_rms = 0.0
        self.target_rms = 0.0
        self.is_recording = False
        self.is_transcribing = False

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_frame)
        self.anim_timer.start(16)

    def set_level(self, rms: float):
        self.target_rms = min(1.0, rms * 3.2)

    def set_state(self, state: str):
        self.is_recording = (state == "recording")
        self.is_transcribing = (state == "transcribing")
        if not self.is_recording:
            self.target_rms = 0.0

    def _on_anim_frame(self):
        self.current_rms += (self.target_rms - self.current_rms) * 0.35
        t = time.time() * 4.5

        for i in range(self.num_bars):
            if self.is_recording:
                wave = math.sin(t * 2.0 + i * 0.38) * 0.25 + 0.75
                target_h = max(0.06, min(1.0, self.current_rms * wave * 1.25))
            elif self.is_transcribing:
                scan = (math.sin(t * 3.0 - i * 0.25) + 1.0) * 0.5
                target_h = 0.08 + 0.40 * (scan ** 3)
            else:
                target_h = 0.05 + 0.03 * math.sin(t * 0.6 + i * 0.20)

            self.bar_heights[i] += (target_h - self.bar_heights[i]) * 0.40

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center_y = h / 2.0

        bar_w = 3.0
        gap = max(2.0, (w - (self.num_bars * bar_w)) / (self.num_bars + 1))
        max_h = h * 0.74

        for i in range(self.num_bars):
            bh = max(2.5, self.bar_heights[i] * max_h)
            bx = gap + i * (bar_w + gap)
            by = center_y - (bh / 2.0)

            if self.is_recording:
                painter.setBrush(QBrush(QColor("#38bdf8")))
            elif self.is_transcribing:
                painter.setBrush(QBrush(QColor("#82828e")))
            else:
                painter.setBrush(QBrush(QColor("#24242c")))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.5, 1.5)

        painter.end()


# =========================================================================
# 4. Main Dashboard Window
# =========================================================================

class DashboardWindow(QMainWindow):
    models_fetched_signal = pyqtSignal(list, str)  # (raw_models, error_msg)
    connection_test_signal = pyqtSignal(str, dict)  # (provider_name, result_dict)
    downloader_finished_signal = pyqtSignal(str, bool, str)  # (model_id, success, message)

    def __init__(self, audio_recorder: AudioRecorder, stt_engine, ai_formatter, parent=None):
        super().__init__(parent)
        self.audio_recorder = audio_recorder
        self.stt_engine = stt_engine
        self.ai_formatter = ai_formatter
        self.gpu_monitor = GPUMonitor()

        # Dynamic Hardware Detection
        self._detect_hardware()

        # Window Configuration
        self.setWindowTitle("Velodictum")
        self.setWindowIcon(create_app_icon(64))
        self.resize(960, 740)
        self.setMinimumSize(880, 640)

        # State trackers
        self.total_dictations = 0
        self.total_words = 0
        self.latencies: List[float] = []
        self.history_records: List[Dict] = []
        self.mode_cards: Dict[str, ModePresetCard] = {}
        self.profile_cards: Dict[str, ModelPresetCard] = {}
        self.tone_cards: Dict[str, TonePresetCard] = {}
        self.priority_cards: Dict[str, ModelPriorityCard] = {}

        # Central Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(12)

        # Build UI
        self._build_header()
        self._build_tabs()

        # Telemetry Polling Timer (Passive inspection every 2 seconds)
        self.gpu_timer = QTimer(self)
        self.gpu_timer.timeout.connect(self._update_telemetry)
        self.gpu_timer.start(2000)

        # Connect Signals
        self.models_fetched_signal.connect(self._on_models_fetched_result)
        self.connection_test_signal.connect(self._on_connection_test_result)
        self.downloader_finished_signal.connect(self._on_downloader_finished)
        signals.audio_device_switched.connect(self._on_audio_device_switched_event)
        signals.vocab_word_learned.connect(lambda _: self._refresh_vocab_list(self.vocab_search.text() if hasattr(self, "vocab_search") else ""))
        signals.recording_started.connect(self._on_rec_started)
        signals.recording_stopped.connect(self._on_rec_stopped)
        signals.recording_cancelled.connect(self._on_rec_cancelled)
        signals.audio_level_updated.connect(self._on_audio_level)
        signals.transcription_started.connect(self._on_transcribe_started)
        signals.formatting_started.connect(self._on_formatting_started)
        signals.transcription_completed.connect(self._on_transcribe_completed)
        signals.transcription_failed.connect(self._on_transcribe_failed)
        signals.mode_changed.connect(self._sync_mode_ui)
        signals.dictation_mode_changed.connect(self._sync_dict_mode_ui)
        signals.language_changed.connect(self.retranslate_ui)

        # Apply initial localized strings
        self.retranslate_ui()

    def _detect_hardware(self):
        """Dynamically detect GPU hardware and VRAM specifications without hardcoding."""
        telem = self.gpu_monitor.get_telemetry()
        self.gpu_available = telem.get("available", False)
        self.short_gpu_name = self.gpu_monitor.short_name
        self.vram_total_gb = telem.get("vram_total_gb", 0.0)
        self._update_hw_badge_string()

    def _update_hw_badge_string(self):
        active_provider = getattr(config.whisper, "provider", "local")
        if active_provider in ("grok", "groq"):
            self.hw_badge_text = "Grok AI · Cloud LPU"
        elif active_provider == "openai":
            self.hw_badge_text = "OpenAI · Whisper-1"
        else:
            if self.gpu_available and self.gpu_monitor.backend in ("nvml", "torch_cuda"):
                self.hw_badge_text = f"{self.short_gpu_name} · CUDA FP16"
            else:
                self.hw_badge_text = f"{self.short_gpu_name} · Int8"

    def showEvent(self, event):
        super().showEvent(event)
        apply_window_backdrop(int(self.winId()))

    # =========================================================================
    # Header & Status Row
    # =========================================================================

    def _build_header(self):
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Left: Clean Brand Headline & Subdued System Telemetry
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title = QLabel("Velodictum")
        title.setObjectName("brand_title")

        tag = QLabel("Studio")
        tag.setObjectName("brand_tag")

        self.lbl_hw_badge = QLabel(self.hw_badge_text)
        self.lbl_hw_badge.setStyleSheet("color: #555562; font-size: 11px; font-weight: 400; margin-left: 6px;")

        title_row.addWidget(title)
        title_row.addWidget(tag)
        title_row.addWidget(self.lbl_hw_badge)
        title_row.addStretch()

        header_layout.addLayout(title_row)
        header_layout.addStretch()

        # Right: Privacy Shield Indicator & Refined Status Indicator
        self.privacy_badge = QLabel("Offline-Schutz")
        self.privacy_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.08); color: #10b981; font-weight: 500; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.15);"
        )
        self.privacy_badge.setVisible(getattr(config.system, "offline_privacy_mode", False))
        header_layout.addWidget(self.privacy_badge)

        self.status_badge = QLabel(tr("ready"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.08); color: #10b981; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.16);"
        )
        header_layout.addWidget(self.status_badge)

        self.main_layout.addWidget(header_frame)

    # =========================================================================
    # 3-Tab Architecture
    # =========================================================================

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_studio = QWidget()
        self.tab_library = QWidget()
        self.tab_settings = QWidget()

        self.tabs.addTab(self.tab_studio, tr("tab_dashboard"))
        self.tabs.addTab(self.tab_library, tr("tab_library_combined"))
        self.tabs.addTab(self.tab_settings, tr("tab_settings"))

        self._setup_studio_tab()
        self._setup_library_tab()
        self._setup_settings_tab()

        self.main_layout.addWidget(self.tabs)

    # =========================================================================
    # TAB 1: STUDIO (Home & Live Command Center)
    # =========================================================================

    def _setup_studio_tab(self):
        root_layout = QVBoxLayout(self.tab_studio)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 6, 2, 8)
        layout.setSpacing(12)

        # 1. Hero Waveform Card
        hero_card = QFrame()
        hero_card.setObjectName("hero_card")
        hc_layout = QVBoxLayout(hero_card)
        hc_layout.setContentsMargins(18, 14, 18, 14)
        hc_layout.setSpacing(8)

        hero_top = QHBoxLayout()
        self.lbl_hero_action = QLabel(tr("hero_status_ready"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #f1f1f4;")

        is_toggle = (getattr(config.hotkey, "mode", "push_to_talk") == "toggle")
        sub_text = tr("hero_sub_toggle", key=config.hotkey.key.upper()) if is_toggle else tr("hero_sub_ptt", key=config.hotkey.key.upper())
        self.lbl_hero_sub = QLabel(sub_text)
        self.lbl_hero_sub.setStyleSheet("font-size: 11.5px; color: #38bdf8; font-weight: 500;")

        hero_top.addWidget(self.lbl_hero_action)
        hero_top.addStretch()
        hero_top.addWidget(self.lbl_hero_sub)
        hc_layout.addLayout(hero_top)

        # 36-Bar Spectrum Meter
        self.hero_waveform = HeroWaveformWidget(self)
        hc_layout.addWidget(self.hero_waveform)

        # Bottom info pills
        hero_pills = QHBoxLayout()
        hero_pills.setSpacing(6)

        self.pill_hotkey = QLabel(tr("pill_hotkey", key=config.hotkey.key.upper()))
        self.pill_hotkey.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.035); color: #787884; font-size: 11px; font-weight: 500; "
            "padding: 2px 7px; border-radius: 4px;"
        )

        self.pill_engine = QLabel(tr("pill_engine", engine=config.formatting.engine.upper()))
        self.pill_engine.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.035); color: #787884; font-size: 11px; font-weight: 500; "
            "padding: 2px 7px; border-radius: 4px;"
        )

        active_provider = getattr(config.whisper, "provider", "local")
        if active_provider in ("grok", "groq"):
            prof_str = "GROK AI"
        elif active_provider == "openai":
            prof_str = "OPENAI"
        else:
            prof_str = config.whisper.profile.upper()

        self.pill_profile = QLabel(tr("pill_stt", stt=prof_str))
        self.pill_profile.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.035); color: #787884; font-size: 11px; font-weight: 500; "
            "padding: 2px 7px; border-radius: 4px;"
        )

        self.btn_hero_scratchpad = QPushButton(tr("hero_scratchpad_btn"))
        self.btn_hero_scratchpad.setStyleSheet(
            "QPushButton { background-color: rgba(56, 189, 248, 0.08); color: #38bdf8; font-size: 10.5px; font-weight: 600; "
            "padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.2); } "
            "QPushButton:hover { background-color: rgba(56, 189, 248, 0.16); }"
        )
        self.btn_hero_scratchpad.clicked.connect(self._on_open_scratchpad_clicked)

        self.pill_latency = QLabel(tr("pill_latency", latency=280))
        self.pill_latency.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.06); color: #10b981; font-size: 11px; font-weight: 500; "
            "padding: 2px 7px; border-radius: 4px;"
        )

        hero_pills.addWidget(self.pill_hotkey)
        hero_pills.addWidget(self.pill_engine)
        hero_pills.addWidget(self.pill_profile)
        hero_pills.addWidget(self.btn_hero_scratchpad)
        hero_pills.addStretch()
        hero_pills.addWidget(self.pill_latency)
        hc_layout.addLayout(hero_pills)

        layout.addWidget(hero_card)

        # 2. Latest Transcription Output Card
        trans_card = QFrame()
        trans_card.setObjectName("card")
        tc_layout = QVBoxLayout(trans_card)
        tc_layout.setContentsMargins(18, 14, 18, 14)
        tc_layout.setSpacing(8)

        tc_top = QHBoxLayout()
        self.tc_title = QLabel(tr("latest_dictation_title"))
        self.tc_title.setObjectName("section_title")

        self.lbl_latest_stats = QLabel(tr("latest_dictation_ready"))
        self.lbl_latest_stats.setStyleSheet("color: #555562; font-size: 11px; font-weight: 400;")

        self.btn_copy_latest = QPushButton(tr("copy"))
        self.btn_copy_latest.setObjectName("btn_secondary")
        self.btn_copy_latest.clicked.connect(self._copy_latest_text)

        tc_top.addWidget(self.tc_title)
        tc_top.addStretch()
        tc_top.addWidget(self.lbl_latest_stats)
        tc_top.addWidget(self.btn_copy_latest)
        tc_layout.addLayout(tc_top)

        self.lbl_latest_text = QLabel(tr("latest_dictation_empty"))
        self.lbl_latest_text.setWordWrap(True)
        self.lbl_latest_text.setMinimumHeight(38)
        self.lbl_latest_text.setStyleSheet(
            "font-size: 13px; color: #787884; line-height: 145%; padding: 2px 0;"
        )
        tc_layout.addWidget(self.lbl_latest_text)

        layout.addWidget(trans_card)

        # 3. Tier 1: Operating Mode (Flow vs. Raw Bypass)
        mode_card = QFrame()
        mode_card.setObjectName("card")
        mc_layout = QVBoxLayout(mode_card)
        mc_layout.setContentsMargins(18, 14, 18, 14)
        mc_layout.setSpacing(8)

        self.mc_title = QLabel(tr("section_mode_title"))
        self.mc_title.setObjectName("section_title")
        mc_layout.addWidget(self.mc_title)

        grid_mode = QGridLayout()
        grid_mode.setSpacing(8)

        active_mode = getattr(config.formatting, "mode", "flow")
        if active_mode not in ("flow", "raw"):
            active_mode = "flow"

        for idx, (m_key, m_info) in enumerate(MODES.items()):
            title_text = tr("mode_flow_title") if m_key == "flow" else tr("mode_raw_title")
            desc_text = tr("mode_flow_desc") if m_key == "flow" else tr("mode_raw_desc")
            card = ModePresetCard(m_key, title_text, desc_text, self)
            card.set_selected(m_key == active_mode)
            card.clicked.connect(self._on_mode_clicked)

            self.mode_cards[m_key] = card
            grid_mode.addWidget(card, 0, idx)

        mc_layout.addLayout(grid_mode)
        layout.addWidget(mode_card)

        # 4. Tier 2: Tone & Style Profiles (for Intelligent Flow)
        self.tone_section_card = QFrame()
        self.tone_section_card.setObjectName("card")
        tc_layout_tone = QVBoxLayout(self.tone_section_card)
        tc_layout_tone.setContentsMargins(18, 14, 18, 14)
        tc_layout_tone.setSpacing(8)

        tone_top = QHBoxLayout()
        self.tone_title = QLabel(tr("tone_section_title"))
        self.tone_title.setObjectName("section_title")
        self.lbl_tone_status = QLabel(tr("tone_status_active") if active_mode == "flow" else tr("tone_status_inactive"))
        self.lbl_tone_status.setStyleSheet("color: #787884; font-size: 11px;")
        tone_top.addWidget(self.tone_title)
        tone_top.addStretch()
        tone_top.addWidget(self.lbl_tone_status)
        tc_layout_tone.addLayout(tone_top)

        grid_tone = QGridLayout()
        grid_tone.setSpacing(8)

        active_tone = getattr(config.formatting, "tone", "default")
        tone_order = ["default", "formal_sie", "informal_du", "concise", "academic", "latex"]
        tone_trans = {
            "default": ("tone_default_title", "tone_default_desc"),
            "formal_sie": ("tone_formal_title", "tone_formal_desc"),
            "informal_du": ("tone_informal_title", "tone_informal_desc"),
            "concise": ("tone_concise_title", "tone_concise_desc"),
            "academic": ("tone_academic_title", "tone_academic_desc"),
            "latex": ("tone_latex_title", "tone_latex_desc"),
        }

        for idx, t_key in enumerate(tone_order):
            if t_key not in TONE_PROFILES:
                continue
            t_info = TONE_PROFILES[t_key]
            row = idx // 3
            col = idx % 3

            title_k, desc_k = tone_trans.get(t_key, ("tone_default_title", "tone_default_desc"))
            t_card = TonePresetCard(
                key=t_key,
                title=tr(title_k),
                tag=t_info.get("tag", "STYLE"),
                sub=tr(desc_k),
                parent=self,
            )
            t_card.set_selected(t_key == active_tone)
            t_card.clicked.connect(self._on_tone_preset_clicked)

            self.tone_cards[t_key] = t_card
            grid_tone.addWidget(t_card, row, col)

        tc_layout_tone.addLayout(grid_tone)
        layout.addWidget(self.tone_section_card)

        # Sync Tone Card interactivity with active mode
        self.tone_section_card.setEnabled(active_mode == "flow")

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    # =========================================================================
    # TAB 2: LIBRARY & HISTORY (2-Spalten Split View mit Sub-Selektor)
    # =========================================================================

    def _setup_library_tab(self):
        tab_layout = QHBoxLayout(self.tab_library)
        tab_layout.setContentsMargins(0, 8, 0, 0)
        tab_layout.setSpacing(12)

        # Left Column (45%): Library Sub-Tabs (Fachwörterbuch / Sprach-Makros / App-Profile)
        left_card = QFrame()
        left_card.setObjectName("card")
        lc_layout = QVBoxLayout(left_card)
        lc_layout.setContentsMargins(16, 14, 16, 14)
        lc_layout.setSpacing(10)

        # Segmented Sub-View Switcher
        sub_nav = QHBoxLayout()
        sub_nav.setSpacing(4)

        self.btn_sub_vocab = QPushButton(tr("tab_vocabulary"))
        self.btn_sub_vocab.setCheckable(True)
        self.btn_sub_vocab.setChecked(True)
        self.btn_sub_vocab.clicked.connect(lambda: self._switch_library_subview(0))

        self.btn_sub_snippets = QPushButton(tr("tab_snippets"))
        self.btn_sub_snippets.setCheckable(True)
        self.btn_sub_snippets.clicked.connect(lambda: self._switch_library_subview(1))

        self.btn_sub_apps = QPushButton(tr("tab_profiles"))
        self.btn_sub_apps.setCheckable(True)
        self.btn_sub_apps.clicked.connect(lambda: self._switch_library_subview(2))

        sub_nav.addWidget(self.btn_sub_vocab)
        sub_nav.addWidget(self.btn_sub_snippets)
        sub_nav.addWidget(self.btn_sub_apps)
        lc_layout.addLayout(sub_nav)

        self.lib_stacked = QStackedWidget()

        # View 0: Custom Vocabulary (Clean list styling, no boxed fields)
        v_widget = QWidget()
        vw_layout = QVBoxLayout(v_widget)
        vw_layout.setContentsMargins(0, 0, 0, 0)
        vw_layout.setSpacing(8)

        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self.input_new_word = QLineEdit()
        self.input_new_word.setPlaceholderText(tr("word_placeholder"))
        self.input_new_word.returnPressed.connect(self._on_add_vocab_word)
        self.combo_new_cat = QComboBox()
        self.combo_new_cat.addItems([tr("cat_tech"), tr("cat_dev"), tr("cat_name"), tr("cat_company"), tr("cat_abbr"), tr("cat_general")])
        self.btn_vocab_add = QPushButton(tr("btn_add_term"))
        self.btn_vocab_add.setObjectName("btn_primary")
        self.btn_vocab_add.clicked.connect(self._on_add_vocab_word)
        self.btn_vocab_cancel = QPushButton(tr("cancel"))
        self.btn_vocab_cancel.setObjectName("btn_secondary")
        self.btn_vocab_cancel.setVisible(False)
        self.btn_vocab_cancel.clicked.connect(self._cancel_vocab_edit)
        add_row.addWidget(self.input_new_word, stretch=2)
        add_row.addWidget(self.combo_new_cat)
        add_row.addWidget(self.btn_vocab_add)
        add_row.addWidget(self.btn_vocab_cancel)
        vw_layout.addLayout(add_row)

        self.vocab_search = QLineEdit()
        self.vocab_search.setPlaceholderText(tr("filter_vocab_placeholder"))
        self.vocab_search.textChanged.connect(self._filter_vocab)
        vw_layout.addWidget(self.vocab_search)

        v_scroll = QScrollArea()
        v_scroll.setWidgetResizable(True)
        v_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.vocab_container = QWidget()
        self.vocab_list_layout = QVBoxLayout(self.vocab_container)
        self.vocab_list_layout.setContentsMargins(0, 2, 0, 0)
        self.vocab_list_layout.setSpacing(3)
        self.vocab_list_layout.addStretch()
        v_scroll.setWidget(self.vocab_container)
        vw_layout.addWidget(v_scroll, stretch=1)

        self.lib_stacked.addWidget(v_widget)

        # View 1: Smart Snippets / Sprach-Makros
        snip_widget = QWidget()
        sw_layout = QVBoxLayout(snip_widget)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(8)

        snip_add_row = QHBoxLayout()
        snip_add_row.setSpacing(6)
        self.input_snip_trig = QLineEdit()
        self.input_snip_trig.setPlaceholderText(tr("trigger_placeholder"))
        self.input_snip_exp = QLineEdit()
        self.input_snip_exp.setPlaceholderText(tr("expansion_placeholder"))
        self.input_snip_exp.returnPressed.connect(self._on_add_snippet)
        self.btn_snip_add = QPushButton(tr("btn_add_snippet"))
        self.btn_snip_add.setObjectName("btn_primary")
        self.btn_snip_add.clicked.connect(self._on_add_snippet)
        self.btn_snip_cancel = QPushButton(tr("cancel"))
        self.btn_snip_cancel.setObjectName("btn_secondary")
        self.btn_snip_cancel.setVisible(False)
        self.btn_snip_cancel.clicked.connect(self._cancel_snippet_edit)
        snip_add_row.addWidget(self.input_snip_trig, stretch=1)
        snip_add_row.addWidget(self.input_snip_exp, stretch=2)
        snip_add_row.addWidget(self.btn_snip_add)
        snip_add_row.addWidget(self.btn_snip_cancel)
        sw_layout.addLayout(snip_add_row)

        snip_scroll = QScrollArea()
        snip_scroll.setWidgetResizable(True)
        snip_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.snip_container = QWidget()
        self.snip_list_layout = QVBoxLayout(self.snip_container)
        self.snip_list_layout.setContentsMargins(0, 2, 0, 0)
        self.snip_list_layout.setSpacing(3)
        self.snip_list_layout.addStretch()
        snip_scroll.setWidget(self.snip_container)
        sw_layout.addWidget(snip_scroll, stretch=1)

        self.lib_stacked.addWidget(snip_widget)

        # View 2: App-Profile
        app_widget = QWidget()
        aw_layout = QVBoxLayout(app_widget)
        aw_layout.setContentsMargins(0, 0, 0, 0)
        aw_layout.setSpacing(8)

        self.lbl_app_info = QLabel(tr("app_rules_info"))
        self.lbl_app_info.setStyleSheet("color: #71717a; font-size: 11px;")
        aw_layout.addWidget(self.lbl_app_info)

        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.app_container = QWidget()
        self.app_list_layout = QVBoxLayout(self.app_container)
        self.app_list_layout.setContentsMargins(0, 2, 0, 0)
        self.app_list_layout.setSpacing(3)
        self.app_list_layout.addStretch()
        app_scroll.setWidget(self.app_container)
        aw_layout.addWidget(app_scroll, stretch=1)

        self.lib_stacked.addWidget(app_widget)

        lc_layout.addWidget(self.lib_stacked)
        tab_layout.addWidget(left_card, stretch=2)

        # Right Column (55%): Dictation History with Quiet Empty State
        hist_card = QFrame()
        hist_card.setObjectName("card")
        hc_layout = QVBoxLayout(hist_card)
        hc_layout.setContentsMargins(16, 14, 16, 14)
        hc_layout.setSpacing(10)

        h_head = QHBoxLayout()
        self.lbl_history_title = QLabel(tr("history_title"))
        self.lbl_history_title.setObjectName("section_title")
        self.lbl_hist_count = QLabel(tr("history_entries_count", count=0))
        self.lbl_hist_count.setStyleSheet("color: #555562; font-size: 11px; font-weight: 400;")
        h_head.addWidget(self.lbl_history_title)
        h_head.addStretch()
        h_head.addWidget(self.lbl_hist_count)
        hc_layout.addLayout(h_head)

        h_scroll = QScrollArea()
        h_scroll.setWidgetResizable(True)
        h_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.hist_container = QWidget()
        self.hist_list_layout = QVBoxLayout(self.hist_container)
        self.hist_list_layout.setContentsMargins(0, 2, 0, 0)
        self.hist_list_layout.setSpacing(6)

        # Empty state banner
        self.empty_state_widget = QWidget()
        es_layout = QVBoxLayout(self.empty_state_widget)
        es_layout.setContentsMargins(16, 60, 16, 60)
        es_layout.setSpacing(8)

        self.lbl_hist_empty_title = QLabel(tr("history_empty_title"))
        self.lbl_hist_empty_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #71717a;")
        self.lbl_hist_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_hist_empty_sub = QLabel(tr("history_empty_desc", key=config.hotkey.key.upper()))
        self.lbl_hist_empty_sub.setStyleSheet("font-size: 11.5px; color: #4a4a56; line-height: 140%;")
        self.lbl_hist_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        es_layout.addWidget(self.lbl_hist_empty_title)
        es_layout.addWidget(self.lbl_hist_empty_sub)
        self.hist_list_layout.addWidget(self.empty_state_widget)

        self.hist_list_layout.addStretch()
        h_scroll.setWidget(self.hist_container)
        hc_layout.addWidget(h_scroll, stretch=1)

        tab_layout.addWidget(hist_card, stretch=3)

        self._refresh_vocab_list()
        self._refresh_snippets_list()
        self._refresh_app_rules_list()

    def _switch_library_subview(self, idx: int):
        self.btn_sub_vocab.setChecked(idx == 0)
        self.btn_sub_snippets.setChecked(idx == 1)
        self.btn_sub_apps.setChecked(idx == 2)
        self.lib_stacked.setCurrentIndex(idx)

    # =========================================================================
    # TAB 3: SETTINGS (System-Konfiguration & Hardware)
    # =========================================================================

    def _setup_settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(10)

        # Settings Search Bar & Toolbar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 2, 4, 2)
        self.lbl_top_info = QLabel(tr("settings_header"))
        self.lbl_top_info.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #a1a1aa; letter-spacing: 0.5px;")

        self.btn_expand_all = QPushButton(tr("expand_all"))
        self.btn_expand_all.setObjectName("btn_secondary")
        self.btn_expand_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand_all.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_expand_all.clicked.connect(self._expand_all_settings)

        self.btn_collapse_all = QPushButton(tr("collapse_all"))
        self.btn_collapse_all.setObjectName("btn_secondary")
        self.btn_collapse_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse_all.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_collapse_all.clicked.connect(self._collapse_all_settings)

        top_bar.addWidget(self.lbl_top_info)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_expand_all)
        top_bar.addWidget(self.btn_collapse_all)
        layout.addLayout(top_bar)

        # Search Bar
        search_row = QHBoxLayout()
        search_row.setContentsMargins(4, 0, 4, 4)
        self.input_settings_search = QLineEdit()
        self.input_settings_search.setPlaceholderText("Einstellung suchen... (z. B. 'Mikrofon', 'Gain', 'Hotkey', 'Whisper', 'Autostart')")
        self.input_settings_search.setStyleSheet(
            "QLineEdit { background-color: #141419; border: 1px solid #23232b; border-radius: 6px; "
            "padding: 7px 12px; color: #f1f1f4; font-size: 12px; } "
            "QLineEdit:focus { border-color: #38bdf8; }"
        )
        self.input_settings_search.textChanged.connect(self._on_settings_search_changed)
        search_row.addWidget(self.input_settings_search)
        layout.addLayout(search_row)

        # =====================================================================
        # CARD 1: ALLGEMEIN (General System & Feedback)
        # =====================================================================
        self.card_gen = CollapsibleSettingsCard(
            tr("card_gen_title"),
            summary="",
            description=tr("card_gen_desc"),
            is_expanded=False,
        )
        gen_layout = self.card_gen.body_layout

        self.chk_autostart = QCheckBox(tr("lbl_autostart"))
        self.chk_autostart.setChecked(autostart_manager.is_autostart_enabled())
        self.chk_autostart.toggled.connect(self._on_autostart_toggled)
        gen_layout.addWidget(self.chk_autostart)

        self.chk_minimized = QCheckBox(tr("lbl_start_minimized"))
        self.chk_minimized.setChecked(getattr(config.system, "start_minimized", False))
        self.chk_minimized.toggled.connect(self._on_minimized_toggled)
        gen_layout.addWidget(self.chk_minimized)

        sep_gen = QFrame()
        sep_gen.setFrameShape(QFrame.Shape.HLine)
        sep_gen.setStyleSheet("color: rgba(255, 255, 255, 0.06); margin: 4px 0;")
        gen_layout.addWidget(sep_gen)

        self.chk_sound_cues = QCheckBox(tr("lbl_sound_cues"))
        self.chk_sound_cues.setChecked(getattr(config.system, "sound_cues", True))
        self.chk_sound_cues.toggled.connect(self._on_sound_cues_toggled)
        gen_layout.addWidget(self.chk_sound_cues)

        self.sound_options_widget = QWidget()
        sopt_layout = QVBoxLayout(self.sound_options_widget)
        sopt_layout.setContentsMargins(0, 0, 0, 0)
        sopt_layout.setSpacing(8)

        row_stheme = QHBoxLayout()
        self.lbl_stheme = QLabel(tr("lbl_sound_theme"))
        self.lbl_stheme.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_sound_theme = QComboBox()
        self.sound_theme_keys = list(SOUND_THEMES.keys())
        for k, v in SOUND_THEMES.items():
            self.combo_sound_theme.addItem(f"{v['name']}", k)
        cur_theme = getattr(config.system, "sound_theme", "velodictum_silk")
        if cur_theme in self.sound_theme_keys:
            self.combo_sound_theme.setCurrentIndex(self.sound_theme_keys.index(cur_theme))
        self.combo_sound_theme.currentIndexChanged.connect(self._on_sound_theme_changed)

        self.btn_preview_sound = QPushButton(tr("btn_sound_preview"))
        self.btn_preview_sound.setObjectName("btn_secondary")
        self.btn_preview_sound.clicked.connect(self._on_preview_sound_clicked)

        row_stheme.addWidget(self.lbl_stheme)
        row_stheme.addWidget(self.combo_sound_theme, stretch=1)
        row_stheme.addWidget(self.btn_preview_sound)
        sopt_layout.addLayout(row_stheme)

        row_svol = QHBoxLayout()
        self.lbl_svol = QLabel(tr("lbl_sound_volume"))
        self.lbl_svol.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_sound_vol = QComboBox()
        vol_options = [
            (0.25, "25% (Sehr leise)"),
            (0.45, "45% (Sanft)"),
            (0.65, "65% (Standard)"),
            (0.75, "75% (Präsent)"),
            (1.00, "100% (Maximum)"),
        ]
        self.vol_values = [v[0] for v in vol_options]
        for vval, vlabel in vol_options:
            self.combo_sound_vol.addItem(vlabel, vval)

        cur_vol = getattr(config.system, "sound_volume", 0.75)
        closest_idx = min(range(len(self.vol_values)), key=lambda i: abs(self.vol_values[i] - cur_vol))
        self.combo_sound_vol.setCurrentIndex(closest_idx)
        self.combo_sound_vol.currentIndexChanged.connect(self._on_sound_volume_changed)

        row_svol.addWidget(self.lbl_svol)
        row_svol.addWidget(self.combo_sound_vol, stretch=1)
        sopt_layout.addLayout(row_svol)

        self.chk_sound_cues.toggled.connect(self.sound_options_widget.setEnabled)
        self.sound_options_widget.setEnabled(getattr(config.system, "sound_cues", True))
        gen_layout.addWidget(self.sound_options_widget)

        layout.addWidget(self.card_gen)

        # =====================================================================
        # CARD 2: AUDIO & MIKROFON (Hardware, Levels, Pre-Amp & Ducking)
        # =====================================================================
        self.card_audio = CollapsibleSettingsCard(
            tr("card_audio_title"),
            summary="",
            description=tr("card_audio_desc"),
            is_expanded=True,
        )
        aud_layout = self.card_audio.body_layout

        # 1. Device Selection
        row_mic = QHBoxLayout()
        self.lbl_mic = QLabel(tr("lbl_mic_input"))
        self.lbl_mic.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_mic = QComboBox()
        devices = self.audio_recorder.list_devices()
        self.mic_device_ids = []
        default_idx = 0
        for i, dev in enumerate(devices):
            self.combo_mic.addItem(f"{dev['name']}")
            self.mic_device_ids.append(dev["id"])
            if config.audio.input_device == dev["id"]:
                default_idx = i
        self.combo_mic.setCurrentIndex(default_idx)
        self.combo_mic.currentIndexChanged.connect(self._on_mic_combo_changed)
        row_mic.addWidget(self.lbl_mic)
        row_mic.addWidget(self.combo_mic, stretch=1)
        aud_layout.addLayout(row_mic)

        # 2. Pre-Amplification (Gain) & Soft Limiter
        row_gain = QHBoxLayout()
        self.lbl_gain_title = QLabel(tr("lbl_gain_title"))
        self.lbl_gain_title.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")

        cur_gain = getattr(config.audio, "input_gain", 1.0)
        self.slider_gain = QSlider(Qt.Orientation.Horizontal)
        self.slider_gain.setRange(50, 300)
        self.slider_gain.setValue(int(cur_gain * 100))
        self.slider_gain.setTickInterval(25)
        self.slider_gain.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_gain.setStyleSheet("QSlider::handle:horizontal { background: #38bdf8; }")
        self.slider_gain.valueChanged.connect(self._on_gain_slider_changed)

        db_val = 20.0 * math.log10(cur_gain) if cur_gain > 0 else 0.0
        db_str = f"+{db_val:.1f}" if db_val > 0 else f"{db_val:.1f}"
        self.lbl_gain_value = QLabel(f"{int(cur_gain * 100)}% ({cur_gain:.1f}x · {db_str} dB)")
        self.lbl_gain_value.setStyleSheet("font-size: 11px; font-weight: 600; color: #38bdf8; min-width: 130px;")

        row_gain.addWidget(self.lbl_gain_title)
        row_gain.addWidget(self.slider_gain, stretch=1)
        row_gain.addWidget(self.lbl_gain_value)
        aud_layout.addLayout(row_gain)

        # 3. Live Calibration Meter & Microphone Test Button
        row_mic_test = QHBoxLayout()
        row_mic_test.setSpacing(10)
        self.btn_mic_test = QPushButton(tr("btn_mic_test_start"))
        self.btn_mic_test.setObjectName("btn_secondary")
        self.btn_mic_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic_test.setStyleSheet("font-size: 11px; font-weight: 600; padding: 5px 14px;")
        self.btn_mic_test.clicked.connect(self._toggle_mic_test)

        self.lbl_mic_test_status = QLabel(tr("lbl_mic_inactive"))
        self.lbl_mic_test_status.setStyleSheet("font-size: 11px; color: #71717a;")

        row_mic_test.addWidget(self.btn_mic_test)
        row_mic_test.addWidget(self.lbl_mic_test_status, stretch=1)
        aud_layout.addLayout(row_mic_test)

        self.calib_meter = LevelCalibrationWidget(self)
        aud_layout.addWidget(self.calib_meter)

        self.lbl_gain_help = QLabel(tr("lbl_mic_tip"))
        self.lbl_gain_help.setWordWrap(True)
        self.lbl_gain_help.setStyleSheet("font-size: 11px; color: #71717a; line-height: 140%; margin-top: 2px;")
        aud_layout.addWidget(self.lbl_gain_help)

        sep_aud1 = QFrame()
        sep_aud1.setFrameShape(QFrame.Shape.HLine)
        sep_aud1.setStyleSheet("color: rgba(255, 255, 255, 0.06); margin: 6px 0;")
        aud_layout.addWidget(sep_aud1)

        # 4. Auto-Ducking Section
        self.chk_auto_ducking = QCheckBox(tr("lbl_auto_ducking"))
        self.chk_auto_ducking.setChecked(getattr(config.audio, "auto_ducking", True))
        self.chk_auto_ducking.toggled.connect(self._on_auto_ducking_toggled)
        aud_layout.addWidget(self.chk_auto_ducking)

        self.duck_options_widget = QWidget()
        duck_layout = QVBoxLayout(self.duck_options_widget)
        duck_layout.setContentsMargins(0, 0, 0, 0)
        duck_layout.setSpacing(6)

        row_duck_val = QHBoxLayout()
        self.lbl_duck_title = QLabel(tr("lbl_duck_title"))
        self.lbl_duck_title.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.slider_ducking_level = QSlider(Qt.Orientation.Horizontal)
        self.slider_ducking_level.setRange(10, 50)
        self.slider_ducking_level.setValue(getattr(config.audio, "ducking_volume_percent", 25))
        self.lbl_ducking_level_val = QLabel(f"{self.slider_ducking_level.value()}% (Sehr leise)")
        self.lbl_ducking_level_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 110px; text-align: right;")
        self.slider_ducking_level.valueChanged.connect(self._on_ducking_level_changed)
        row_duck_val.addWidget(self.lbl_duck_title)
        row_duck_val.addWidget(self.slider_ducking_level, stretch=1)
        row_duck_val.addWidget(self.lbl_ducking_level_val)
        duck_layout.addLayout(row_duck_val)

        self.chk_auto_ducking.toggled.connect(self.duck_options_widget.setEnabled)
        self.duck_options_widget.setEnabled(getattr(config.audio, "auto_ducking", True))
        aud_layout.addWidget(self.duck_options_widget)

        sep_aud2 = QFrame()
        sep_aud2.setFrameShape(QFrame.Shape.HLine)
        sep_aud2.setStyleSheet("color: rgba(255, 255, 255, 0.06); margin: 6px 0;")
        aud_layout.addWidget(sep_aud2)

        # 5. Wireless Mobile LAN Bridge
        self.chk_mobile_bridge = QCheckBox(tr("lbl_mobile_bridge"))
        self.chk_mobile_bridge.setChecked(getattr(config.mobile_bridge, "enabled", False))
        self.chk_mobile_bridge.toggled.connect(self._on_mobile_bridge_toggled)
        aud_layout.addWidget(self.chk_mobile_bridge)

        self.mob_options_widget = QWidget()
        mob_opt_layout = QVBoxLayout(self.mob_options_widget)
        mob_opt_layout.setContentsMargins(0, 0, 0, 0)
        mob_opt_layout.setSpacing(6)

        row_mob_url = QHBoxLayout()
        self.lbl_murl = QLabel(tr("lbl_mobile_url"))
        self.lbl_murl.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.local_lan_ip = get_local_ip()
        token = getattr(config.mobile_bridge, "auth_token", "")
        proto = "https" if getattr(config.mobile_bridge, "use_https", True) else "http"
        url_str = f"{proto}://{self.local_lan_ip}:8765/?token={token}" if token else f"{proto}://{self.local_lan_ip}:8765/"
        self.lbl_mobile_url = QLineEdit(url_str)
        self.lbl_mobile_url.setReadOnly(True)

        self.btn_copy_mob = QPushButton(tr("copy"))
        self.btn_copy_mob.setObjectName("btn_secondary")
        self.btn_copy_mob.clicked.connect(self._on_copy_mobile_url)

        self.btn_open_mob = QPushButton(tr("btn_open_browser"))
        self.btn_open_mob.setObjectName("btn_secondary")
        self.btn_open_mob.clicked.connect(self._on_open_mobile_url)

        self.btn_rotate_mob_token = QPushButton(tr("btn_rotate_token"))
        self.btn_rotate_mob_token.setObjectName("btn_secondary")
        self.btn_rotate_mob_token.setToolTip(tr("btn_token_tooltip"))
        self.btn_rotate_mob_token.clicked.connect(self._on_rotate_mobile_token)

        row_mob_url.addWidget(self.lbl_murl)
        row_mob_url.addWidget(self.lbl_mobile_url, stretch=1)
        row_mob_url.addWidget(self.btn_copy_mob)
        row_mob_url.addWidget(self.btn_open_mob)
        row_mob_url.addWidget(self.btn_rotate_mob_token)
        mob_opt_layout.addLayout(row_mob_url)

        self.lbl_mobile_status = QLabel(tr("lbl_mobile_active") if getattr(config.mobile_bridge, "enabled", False) else tr("lbl_mobile_inactive"))
        self.lbl_mobile_status.setStyleSheet("font-size: 11px; color: #10b981;" if getattr(config.mobile_bridge, "enabled", False) else "font-size: 11px; color: #71717a;")
        mob_opt_layout.addWidget(self.lbl_mobile_status)

        self.lbl_mob_hint = QLabel(tr("lbl_mobile_hint"))
        self.lbl_mob_hint.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.3;")
        self.lbl_mob_hint.setWordWrap(True)
        mob_opt_layout.addWidget(self.lbl_mob_hint)

        self.chk_mobile_bridge.toggled.connect(self.mob_options_widget.setEnabled)
        self.mob_options_widget.setEnabled(getattr(config.mobile_bridge, "enabled", False))
        aud_layout.addWidget(self.mob_options_widget)

        layout.addWidget(self.card_audio)

        # =====================================================================
        # CARD 3: SPRACHERKENNUNG (Speech Recognition / STT Pipeline)
        # =====================================================================
        self.card_stt = CollapsibleSettingsCard(
            f"{tr('card_stt_title')} ({self.short_gpu_name.upper()})",
            summary="",
            description=tr("card_stt_desc"),
            is_expanded=False,
        )
        sc_layout = self.card_stt.body_layout

        row_prov = QHBoxLayout()
        self.lbl_prov = QLabel(tr("lbl_stt_provider"))
        self.lbl_prov.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_stt_provider = QComboBox()
        self.combo_stt_provider.addItems([
            tr("stt_prov_local", gpu=self.short_gpu_name),
            tr("stt_prov_universal"),
            tr("stt_prov_grok"),
            tr("stt_prov_openai"),
        ])
        cur_prov = getattr(config.whisper, "provider", "local")
        prov_map = {"local": 0, "universal": 1, "openrouter": 1, "custom": 1, "grok": 2, "groq": 2, "openai": 3}
        self.combo_stt_provider.setCurrentIndex(prov_map.get(cur_prov, 0))
        self.combo_stt_provider.currentIndexChanged.connect(self._on_stt_provider_changed)
        row_prov.addWidget(self.lbl_prov)
        row_prov.addWidget(self.combo_stt_provider, stretch=1)
        sc_layout.addLayout(row_prov)

        self.cloud_banner = QLabel()
        self.cloud_banner.setWordWrap(True)
        self.cloud_banner.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.06); color: #7dd3fc; font-size: 11px; padding: 8px 12px; "
            "border-radius: 5px; border: 1px solid rgba(56, 189, 248, 0.15);"
        )
        sc_layout.addWidget(self.cloud_banner)

        # Universal STT API / Custom Endpoint Configuration Widget
        self.universal_stt_widget = QWidget()
        u_stt_layout = QVBoxLayout(self.universal_stt_widget)
        u_stt_layout.setContentsMargins(0, 0, 0, 0)
        u_stt_layout.setSpacing(6)

        row_u_url = QHBoxLayout()
        self.lbl_u_url = QLabel(tr("lbl_universal_stt_url"))
        self.lbl_u_url.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_universal_stt_url = QLineEdit(getattr(config.whisper, "universal_endpoint", "https://openrouter.ai/api/v1/audio/transcriptions"))
        self.input_universal_stt_url.setPlaceholderText("https://openrouter.ai/api/v1/audio/transcriptions oder http://localhost:8000/v1/audio/transcriptions")
        self.input_universal_stt_url.textChanged.connect(self._on_universal_stt_url_changed)
        row_u_url.addWidget(self.lbl_u_url)
        row_u_url.addWidget(self.input_universal_stt_url, stretch=1)
        u_stt_layout.addLayout(row_u_url)

        row_u_key = QHBoxLayout()
        self.lbl_u_stt_key = QLabel(tr("lbl_universal_stt_key"))
        self.lbl_u_stt_key.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_universal_stt_key = QLineEdit(config.whisper.get_api_key("universal") or "")
        self.input_universal_stt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_universal_stt_key.setPlaceholderText(tr("universal_stt_key_placeholder"))
        self.input_universal_stt_key.textChanged.connect(self._on_universal_stt_key_changed)
        row_u_key.addWidget(self.lbl_u_stt_key)
        row_u_key.addWidget(self.input_universal_stt_key, stretch=1)
        u_stt_layout.addLayout(row_u_key)

        row_u_model = QHBoxLayout()
        self.lbl_u_stt_model = QLabel(tr("lbl_universal_stt_model"))
        self.lbl_u_stt_model.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_universal_stt_model = QLineEdit(getattr(config.whisper, "universal_model", "openai/whisper-large-v3"))
        self.input_universal_stt_model.setPlaceholderText("openai/whisper-large-v3, whisper-1, etc.")
        self.input_universal_stt_model.textChanged.connect(self._on_universal_stt_model_changed)
        row_u_model.addWidget(self.lbl_u_stt_model)
        row_u_model.addWidget(self.input_universal_stt_model, stretch=1)
        u_stt_layout.addLayout(row_u_model)

        sc_layout.addWidget(self.universal_stt_widget)

        self.groq_key_widget = QWidget()
        row_gkey = QHBoxLayout(self.groq_key_widget)
        row_gkey.setContentsMargins(0, 0, 0, 0)
        self.lbl_gkey = QLabel(tr("lbl_api_key"))
        self.lbl_gkey.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_groq_key = QLineEdit(config.whisper.get_api_key("groq") or "")
        self.input_groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_groq_key.setPlaceholderText(tr("groq_key_placeholder"))
        self.input_groq_key.textChanged.connect(self._on_groq_key_changed)
        row_gkey.addWidget(self.lbl_gkey)
        row_gkey.addWidget(self.input_groq_key, stretch=1)
        sc_layout.addWidget(self.groq_key_widget)

        self.openai_key_widget = QWidget()
        row_oai_key = QHBoxLayout(self.openai_key_widget)
        row_oai_key.setContentsMargins(0, 0, 0, 0)
        self.lbl_oai_stt_key = QLabel(tr("lbl_api_key"))
        self.lbl_oai_stt_key.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_openai_key = QLineEdit(config.whisper.get_api_key("openai") or "")
        self.input_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_openai_key.setPlaceholderText(tr("openai_key_placeholder"))
        self.input_openai_key.textChanged.connect(self._on_openai_key_changed)
        row_oai_key.addWidget(self.lbl_oai_stt_key)
        row_oai_key.addWidget(self.input_openai_key, stretch=1)
        sc_layout.addWidget(self.openai_key_widget)

        self.local_models_widget = QWidget()
        lm_layout = QVBoxLayout(self.local_models_widget)
        lm_layout.setContentsMargins(0, 0, 0, 0)
        lm_layout.setSpacing(6)

        p_grid = QGridLayout()
        p_grid.setSpacing(8)

        vram_specs = {
            "multilingual": {"req": 4.5, "desc": "4.5 GB VRAM", "sub": "Schwerstes Modell · Maximale Qualität"},
            "de_max": {"req": 3.2, "desc": "3.2 GB VRAM", "sub": "Flaggschiff für Deutsch & Fachbegriffe"},
            "de_fast": {"req": 2.2, "desc": "2.2 GB VRAM", "sub": "Ausbalancierte Geschwindigkeit"},
            "low_vram": {"req": 0.9, "desc": "0.9 GB VRAM", "sub": "Geringster Speicherverbrauch (<1 GB)"},
            # Backward compatibility aliases
            "en_fast": {"req": 1.9, "desc": "1.9 GB VRAM", "sub": "Schneller Turbo-Modus"},
            "lite": {"req": 0.9, "desc": "0.9 GB VRAM", "sub": "Geringster Speicherverbrauch"},
        }

        active_prof = getattr(config.whisper, "profile", "de_max")
        for idx, (p_key, p_info) in enumerate(PROFILES.items()):
            row = idx // 2
            col = idx % 2
            spec = vram_specs.get(p_key, {"req": 2.0, "desc": "~2 GB", "sub": "Standard-Transkription"})
            req_gb = spec["req"]

            if not self.gpu_available:
                if p_key == "lite":
                    led_color, led_text = "#10b981", "CPU Bereit"
                elif p_key in ("de_fast", "en_fast"):
                    led_color, led_text = "#f59e0b", "CPU (Langsam)"
                else:
                    led_color, led_text = "#ef4444", "Nicht empfohlen (CPU)"
            else:
                if self.vram_total_gb >= req_gb + 1.0:
                    led_color, led_text = "#10b981", f"Kompatibel · {spec['desc']}"
                elif self.vram_total_gb >= req_gb:
                    led_color, led_text = "#f59e0b", f"Knapp · {spec['desc']}"
                else:
                    led_color, led_text = "#ef4444", f"VRAM zu gering (>={req_gb:.1f} GB nötig)"

            card = ModelPresetCard(
                key=p_key,
                name=p_info["name"],
                tag=p_info["tag"],
                desc=spec["sub"],
                led_color=led_color,
                led_text=led_text,
                parent=self,
            )
            card.set_selected(p_key == active_prof)
            card.clicked.connect(self._on_profile_clicked)
            self.profile_cards[p_key] = card
            p_grid.addWidget(card, row, col)

        lm_layout.addLayout(p_grid)

        # Whisper Model Storage & Downloader Frame
        self.model_storage_frame = QFrame()
        self.model_storage_frame.setStyleSheet("background-color: #141419; border: 1px solid #23232b; border-radius: 8px;")
        ms_layout = QVBoxLayout(self.model_storage_frame)
        ms_layout.setContentsMargins(12, 10, 12, 10)
        ms_layout.setSpacing(8)

        row_storage = QHBoxLayout()
        self.lbl_storage_title = QLabel(tr("lbl_models_storage"))
        self.lbl_storage_title.setStyleSheet("font-weight: 600; min-width: 170px; color: #d4d4d8;")
        self.input_storage_path = QLineEdit(model_manager.get_models_dir())
        self.input_storage_path.setReadOnly(True)
        self.btn_change_storage = QPushButton("Speicherort ändern...")
        self.btn_change_storage.setObjectName("btn_secondary")
        self.btn_change_storage.clicked.connect(self._on_change_models_dir)
        row_storage.addWidget(self.lbl_storage_title)
        row_storage.addWidget(self.input_storage_path, stretch=1)
        row_storage.addWidget(self.btn_change_storage)
        ms_layout.addLayout(row_storage)

        # Disk space bar / status
        self.lbl_disk_space = QLabel()
        self.lbl_disk_space.setStyleSheet("font-size: 11px; color: #38bdf8;")
        self._update_disk_space_label()
        ms_layout.addWidget(self.lbl_disk_space)

        # Model Downloader List Header
        self.lbl_models_header = QLabel(tr("lbl_available_models"))
        self.lbl_models_header.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #a1a1aa; margin-top: 4px;")
        ms_layout.addWidget(self.lbl_models_header)

        self.model_list_container = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_list_container)
        self.model_list_layout.setContentsMargins(0, 0, 0, 0)
        self.model_list_layout.setSpacing(6)
        ms_layout.addWidget(self.model_list_container)

        self._refresh_model_downloader_list()
        lm_layout.addWidget(self.model_storage_frame)

        sc_layout.addWidget(self.local_models_widget)
        self._update_stt_provider_visibility()

        sep_stt = QFrame()
        sep_stt.setFrameShape(QFrame.Shape.HLine)
        sep_stt.setStyleSheet("color: rgba(255, 255, 255, 0.06); margin: 6px 0;")
        sc_layout.addWidget(sep_stt)

        self.chk_squelcher = QCheckBox(tr("lbl_hallucination_filter"))
        self.chk_hallucination = self.chk_squelcher
        self.chk_squelcher.setChecked(getattr(config.whisper, "hallucination_filter", True))
        self.chk_squelcher.toggled.connect(self._on_squelcher_toggled)
        sc_layout.addWidget(self.chk_squelcher)

        layout.addWidget(self.card_stt)

        # =====================================================================
        # CARD 4: FORMATIERUNG & TEXT-INTELLIGENZ (Post-Processing & LLMs)
        # =====================================================================
        self.card_fmt = CollapsibleSettingsCard(
            tr("card_fmt_title"),
            summary="",
            description=tr("card_fmt_desc"),
            is_expanded=False,
        )
        lc_layout = self.card_fmt.body_layout

        # 1. Engine Selector
        row_eng = QHBoxLayout()
        self.lbl_eng = QLabel(tr("lbl_fmt_engine"))
        self.lbl_eng.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_engine = QComboBox()
        self.combo_engine.addItems([
            "Lokale Regeln (Offline / 0ms)",
            "Lokal: Ollama (Lokales KI-Backend)",
            "Universal API (Konfigurierbarer API-Endpunkt)",
            "OpenAI (Offizielle Cloud-API)",
            "Google Gemini (Offizielle Cloud-API)",
            "Groq (Ultra-Fast Cloud)",
        ])
        engine_map = {"rules": 0, "ollama": 1, "universal": 2, "openrouter": 2, "openai": 3, "gemini": 4, "groq": 5}
        cur_eng = getattr(config.formatting, "engine", "rules")
        if cur_eng == "openrouter":
            cur_eng = "universal"
        self.combo_engine.setCurrentIndex(engine_map.get(cur_eng, 0))
        self.combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        row_eng.addWidget(self.lbl_eng)
        row_eng.addWidget(self.combo_engine, stretch=1)
        lc_layout.addLayout(row_eng)

        # 2. Universal API Container
        self.universal_container = QWidget()
        u_layout = QVBoxLayout(self.universal_container)
        u_layout.setContentsMargins(0, 0, 0, 0)
        u_layout.setSpacing(8)

        # API Endpoint (Base URL)
        row_u_ep = QHBoxLayout()
        self.lbl_u_ep = QLabel(tr("lbl_api_endpoint"))
        self.lbl_u_ep.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_u_endpoint = QLineEdit(getattr(config.formatting, "api_endpoint", "https://openrouter.ai/api/v1"))
        self.input_u_endpoint.setPlaceholderText("https://openrouter.ai/api/v1, https://api.together.xyz/v1 etc.")
        self.input_u_endpoint.textChanged.connect(self._on_u_endpoint_changed)
        row_u_ep.addWidget(self.lbl_u_ep)
        row_u_ep.addWidget(self.input_u_endpoint, stretch=1)
        u_layout.addLayout(row_u_ep)

        # Detected Provider Badge
        row_u_det = QHBoxLayout()
        self.lbl_u_det = QLabel(tr("lbl_detected_provider"))
        self.lbl_u_det.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.lbl_u_detected = QLabel("Erkenne...")
        self.lbl_u_detected.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.05); color: #38bdf8; font-weight: 600; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.2);"
        )
        row_u_det.addWidget(self.lbl_u_det)
        row_u_det.addWidget(self.lbl_u_detected)
        row_u_det.addStretch()
        u_layout.addLayout(row_u_det)

        # Universal API Key
        row_u_key = QHBoxLayout()
        self.lbl_u_key = QLabel(tr("lbl_api_key"))
        self.input_u_key = QLineEdit(config.formatting.get_api_key("universal") or "")
        self.input_u_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_u_key.setPlaceholderText(tr("api_key_placeholder"))
        self.input_u_key.textChanged.connect(self._on_u_key_changed)

        self.btn_u_toggle_key = QPushButton(tr("btn_show_key"))
        self.btn_u_toggle_key.setObjectName("btn_secondary")
        self.btn_u_toggle_key.setFixedWidth(70)
        self.btn_u_toggle_key.clicked.connect(lambda: self._toggle_lineedit_password(self.input_u_key, self.btn_u_toggle_key))

        row_u_key.addWidget(self.lbl_u_key)
        row_u_key.addWidget(self.input_u_key, stretch=1)
        row_u_key.addWidget(self.btn_u_toggle_key)
        u_layout.addLayout(row_u_key)

        # Modell-Priorität (3 Stufen)
        self.lbl_prio = QLabel(tr("lbl_prio_title"))
        self.lbl_prio.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #a1a1aa; margin-top: 4px;")
        u_layout.addWidget(self.lbl_prio)

        grid_prio = QGridLayout()
        grid_prio.setSpacing(8)

        self.card_prio_fast = ModelPriorityCard(
            key="speed",
            title=tr("prio_speed_title"),
            badge=tr("prio_speed_badge"),
            sub=tr("prio_speed_desc"),
            parent=self,
        )
        self.card_prio_fast.clicked.connect(self._on_priority_card_clicked)
        self.priority_cards["speed"] = self.card_prio_fast
        self.priority_cards["fast"] = self.card_prio_fast
        grid_prio.addWidget(self.card_prio_fast, 0, 0)

        self.card_prio_balanced = ModelPriorityCard(
            key="balanced",
            title=tr("prio_balanced_title"),
            badge=tr("prio_balanced_badge"),
            sub=tr("prio_balanced_desc"),
            parent=self,
        )
        self.card_prio_balanced.clicked.connect(self._on_priority_card_clicked)
        self.priority_cards["balanced"] = self.card_prio_balanced
        grid_prio.addWidget(self.card_prio_balanced, 0, 1)

        self.card_prio_quality = ModelPriorityCard(
            key="quality",
            title=tr("prio_quality_title"),
            badge=tr("prio_quality_badge"),
            sub=tr("prio_quality_desc"),
            parent=self,
        )
        self.card_prio_quality.clicked.connect(self._on_priority_card_clicked)
        self.priority_cards["quality"] = self.card_prio_quality
        grid_prio.addWidget(self.card_prio_quality, 0, 2)

        u_layout.addLayout(grid_prio)

        # Collapsible Details Panel
        self.model_details_frame = QFrame()
        self.model_details_frame.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 6px; padding: 6px; }"
        )
        det_grid = QGridLayout(self.model_details_frame)
        det_grid.setContentsMargins(8, 6, 8, 6)
        det_grid.setHorizontalSpacing(16)
        det_grid.setVerticalSpacing(4)

        self.lbl_d_m_title = QLabel(tr("lbl_det_model_title"))
        self.lbl_d_m_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        cur_u_model = getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
        self.lbl_det_model = QLabel(cur_u_model)
        self.lbl_det_model.setStyleSheet("font-size: 11px; color: #ffffff; font-weight: 600;")

        self.lbl_d_lat_title = QLabel(tr("lbl_det_lat_title"))
        self.lbl_d_lat_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_latency = QLabel("~450ms")
        self.lbl_det_latency.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600;")

        self.lbl_d_cin_title = QLabel(tr("lbl_det_cin_title"))
        self.lbl_d_cin_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_cost_in = QLabel("$0.40 / 1M")
        self.lbl_det_cost_in.setStyleSheet("font-size: 11px; color: #d4d4d8;")

        self.lbl_d_cout_title = QLabel(tr("lbl_det_cout_title"))
        self.lbl_d_cout_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_cost_out = QLabel("$0.40 / 1M")
        self.lbl_det_cost_out.setStyleSheet("font-size: 11px; color: #d4d4d8;")

        self.lbl_d_ctx_title = QLabel(tr("lbl_det_ctx_title"))
        self.lbl_d_ctx_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_context = QLabel("32k Tokens")
        self.lbl_det_context.setStyleSheet("font-size: 11px; color: #d4d4d8;")

        self.lbl_d_usg_title = QLabel(tr("lbl_det_usg_title"))
        self.lbl_d_usg_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_usage = QLabel(tr("model_custom_compact_rec"))
        self.lbl_det_usage.setStyleSheet("font-size: 11px; color: #d4d4d8;")

        self.lbl_d_route_title = QLabel(tr("lbl_det_route_title"))
        self.lbl_d_route_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_route = QLabel(tr("route_opt_latency"))
        self.lbl_det_route.setStyleSheet("font-size: 11px; color: #38bdf8;")

        self.lbl_d_zdr_title = QLabel(tr("lbl_det_zdr_title"))
        self.lbl_d_zdr_title.setStyleSheet("font-size: 11px; color: #787884; font-weight: 500;")
        self.lbl_det_zdr = QLabel(tr("zdr_active"))
        self.lbl_det_zdr.setStyleSheet("font-size: 11px; color: #10b981;")

        det_grid.addWidget(self.lbl_d_m_title, 0, 0)
        det_grid.addWidget(self.lbl_det_model, 0, 1)
        det_grid.addWidget(self.lbl_d_lat_title, 0, 2)
        det_grid.addWidget(self.lbl_det_latency, 0, 3)

        det_grid.addWidget(self.lbl_d_cin_title, 1, 0)
        det_grid.addWidget(self.lbl_det_cost_in, 1, 1)
        det_grid.addWidget(self.lbl_d_cout_title, 1, 2)
        det_grid.addWidget(self.lbl_det_cost_out, 1, 3)

        det_grid.addWidget(self.lbl_d_ctx_title, 2, 0)
        det_grid.addWidget(self.lbl_det_context, 2, 1)
        det_grid.addWidget(self.lbl_d_usg_title, 2, 2)
        det_grid.addWidget(self.lbl_det_usage, 2, 3)

        det_grid.addWidget(self.lbl_d_route_title, 3, 0)
        det_grid.addWidget(self.lbl_det_route, 3, 1)
        det_grid.addWidget(self.lbl_d_zdr_title, 3, 2)
        det_grid.addWidget(self.lbl_det_zdr, 3, 3)

        u_layout.addWidget(self.model_details_frame)

        # Custom / Catalog Frame
        self.custom_catalog_frame = QFrame()
        self.custom_catalog_frame.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 6px; }"
        )
        self.custom_catalog_frame.setVisible(False)
        cat_layout = QVBoxLayout(self.custom_catalog_frame)
        cat_layout.setContentsMargins(10, 8, 10, 8)
        cat_layout.setSpacing(8)

        row_u_model = QHBoxLayout()
        self.lbl_u_model = QLabel(tr("lbl_u_model_catalog"))
        self.lbl_u_model.setStyleSheet("font-weight: 500; min-width: 150px; color: #9d9da8; font-size: 11.5px;")
        self.combo_u_model = QComboBox()
        self.combo_u_model.setEditable(True)
        self.combo_u_model.setEditText(cur_u_model)
        self.combo_u_model.currentTextChanged.connect(self._on_u_model_changed)

        self.btn_u_fetch_models = QPushButton(tr("btn_fetch_models"))
        self.btn_u_fetch_models.setObjectName("btn_secondary")
        self.btn_u_fetch_models.clicked.connect(self._fetch_universal_models)

        row_u_model.addWidget(self.lbl_u_model)
        row_u_model.addWidget(self.combo_u_model, stretch=1)
        row_u_model.addWidget(self.btn_u_fetch_models)
        cat_layout.addLayout(row_u_model)

        row_route = QHBoxLayout()
        self.lbl_route = QLabel(tr("lbl_route_strategy"))
        self.lbl_route.setStyleSheet("font-weight: 500; min-width: 150px; color: #9d9da8; font-size: 11.5px;")
        self.combo_u_routing = QComboBox()
        self.combo_u_routing.addItem(tr("route_opt_latency"), "latency")
        self.combo_u_routing.addItem(tr("route_opt_price"), "price")
        self.combo_u_routing.addItem(tr("route_opt_throughput"), "throughput")
        self.combo_u_routing.addItem(tr("route_opt_default"), "default")
        
        cur_route = getattr(config.formatting, "routing_strategy", "latency")
        idx_route = 0
        for i in range(self.combo_u_routing.count()):
            if self.combo_u_routing.itemData(i) == cur_route:
                idx_route = i
                break
        self.combo_u_routing.setCurrentIndex(idx_route)
        self.combo_u_routing.currentIndexChanged.connect(self._on_u_routing_changed)

        row_route.addWidget(self.lbl_route)
        row_route.addWidget(self.combo_u_routing, stretch=1)
        cat_layout.addLayout(row_route)

        row_priv = QHBoxLayout()
        row_priv.setSpacing(16)
        self.chk_u_zdr = QCheckBox(tr("chk_u_zdr"))
        self.chk_u_zdr.setStyleSheet("color: #d4d4d8; font-size: 11px;")
        self.chk_u_zdr.setChecked(getattr(config.formatting, "zero_data_retention", True))
        self.chk_u_zdr.toggled.connect(self._on_u_zdr_toggled)

        self.chk_u_fallbacks = QCheckBox(tr("chk_u_fallbacks"))
        self.chk_u_fallbacks.setStyleSheet("color: #d4d4d8; font-size: 11px;")
        self.chk_u_fallbacks.setChecked(getattr(config.formatting, "allow_fallbacks", True))
        self.chk_u_fallbacks.toggled.connect(self._on_u_fallbacks_toggled)

        row_priv.addWidget(self.chk_u_zdr)
        row_priv.addWidget(self.chk_u_fallbacks)
        row_priv.addStretch()
        cat_layout.addLayout(row_priv)

        row_u_test = QHBoxLayout()
        self.lbl_u_test = QLabel(tr("lbl_conn_test"))
        self.lbl_u_test.setStyleSheet("font-weight: 500; min-width: 150px; color: #9d9da8; font-size: 11.5px;")
        self.btn_u_test = QPushButton(tr("btn_test_api"))
        self.btn_u_test.setObjectName("btn_secondary")
        self.btn_u_test.clicked.connect(self._test_universal_connection)
        self.lbl_u_test_status = QLabel("")
        self.lbl_u_test_status.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9d9da8;")

        row_u_test.addWidget(self.lbl_u_test)
        row_u_test.addWidget(self.btn_u_test)
        row_u_test.addWidget(self.lbl_u_test_status, stretch=1)
        cat_layout.addLayout(row_u_test)

        u_layout.addWidget(self.custom_catalog_frame)

        self.btn_toggle_custom_catalog = QPushButton(tr("btn_toggle_custom_catalog"))
        self.btn_toggle_custom_catalog.setObjectName("btn_secondary")
        self.btn_toggle_custom_catalog.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_custom_catalog.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_toggle_custom_catalog.clicked.connect(self._toggle_custom_catalog)
        u_layout.addWidget(self.btn_toggle_custom_catalog)

        lc_layout.addWidget(self.universal_container)

        # 3. Ollama Container
        self.ollama_container = QWidget()
        ol_layout = QVBoxLayout(self.ollama_container)
        ol_layout.setContentsMargins(0, 0, 0, 0)
        ol_layout.setSpacing(8)

        row_ol_url = QHBoxLayout()
        self.lbl_ol_url = QLabel("Ollama Server URL:")
        self.lbl_ol_url.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_ol_url = QLineEdit(getattr(config.formatting, "ollama_url", "http://127.0.0.1:11434"))
        self.input_ol_url.textChanged.connect(self._on_ol_url_changed)
        self.input_ollama_url = self.input_ol_url
        row_ol_url.addWidget(self.lbl_ol_url)
        row_ol_url.addWidget(self.input_ollama_url, stretch=1)
        ol_layout.addLayout(row_ol_url)

        row_ol_model = QHBoxLayout()
        self.lbl_ol_model = QLabel("Ollama Modell:")
        self.lbl_ol_model.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_ol_model = QLineEdit(getattr(config.formatting, "ollama_model", "qwen2.5:7b"))
        self.input_ol_model.setPlaceholderText(tr("custom_model_placeholder"))
        self.input_ol_model.textChanged.connect(self._on_ol_model_changed)
        self.input_ollama_model = self.input_ol_model
        row_ol_model.addWidget(self.lbl_ol_model)
        row_ol_model.addWidget(self.input_ol_model, stretch=1)
        ol_layout.addLayout(row_ol_model)

        row_ol_test = QHBoxLayout()
        self.lbl_ol_test = QLabel(tr("lbl_conn_test"))
        self.lbl_ol_test.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.btn_ol_test = QPushButton(tr("btn_test_ollama"))
        self.btn_ol_test.setObjectName("btn_secondary")
        self.btn_ol_test.clicked.connect(self._test_ollama_connection)
        self.btn_test_ollama = self.btn_ol_test
        self.lbl_ol_test_status = QLabel("")
        self.lbl_ol_test_status.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9d9da8;")
        self.lbl_ollama_status = self.lbl_ol_test_status
        row_ol_test.addWidget(self.lbl_ol_test)
        row_ol_test.addWidget(self.btn_ol_test)
        row_ol_test.addWidget(self.lbl_ol_test_status, stretch=1)
        ol_layout.addLayout(row_ol_test)
        lc_layout.addWidget(self.ollama_container)

        # 4. OpenAI Container
        self.openai_container = QWidget()
        oai_layout = QVBoxLayout(self.openai_container)
        oai_layout.setContentsMargins(0, 0, 0, 0)
        oai_layout.setSpacing(8)

        row_oai_key = QHBoxLayout()
        self.lbl_oai_key = QLabel("OpenAI API-Key:")
        self.lbl_oai_key.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_oai_key = QLineEdit(config.formatting.get_api_key("openai") or "")
        self.input_oai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_oai_key.setPlaceholderText(tr("openai_key_placeholder"))
        self.input_oai_key.textChanged.connect(self._on_oai_key_changed)
        self.input_o_key = self.input_oai_key
        self.btn_oai_toggle_key = QPushButton(tr("btn_show_key"))
        self.btn_oai_toggle_key.setObjectName("btn_secondary")
        self.btn_oai_toggle_key.setFixedWidth(70)
        self.btn_oai_toggle_key.clicked.connect(lambda: self._toggle_lineedit_password(self.input_oai_key, self.btn_oai_toggle_key))
        self.btn_o_toggle_key = self.btn_oai_toggle_key
        row_oai_key.addWidget(self.lbl_oai_key)
        row_oai_key.addWidget(self.input_o_key, stretch=1)
        row_oai_key.addWidget(self.btn_o_toggle_key)
        oai_layout.addLayout(row_oai_key)

        row_oai_model = QHBoxLayout()
        self.lbl_oai_model = QLabel("OpenAI Modell:")
        self.lbl_oai_model.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_oai_model = QComboBox()
        self.combo_oai_model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o3-mini", "o4-mini"])
        cur_oai_model = getattr(config.formatting, "openai_model", "gpt-4o-mini")
        if cur_oai_model in ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o3-mini", "o4-mini"]:
            self.combo_oai_model.setCurrentText(cur_oai_model)
        self.combo_oai_model.currentTextChanged.connect(self._on_oai_model_changed)
        self.combo_o_model = self.combo_oai_model
        row_oai_model.addWidget(self.lbl_oai_model)
        row_oai_model.addWidget(self.combo_o_model, stretch=1)
        oai_layout.addLayout(row_oai_model)

        row_oai_test = QHBoxLayout()
        self.lbl_oai_test = QLabel(tr("lbl_conn_test"))
        self.lbl_oai_test.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.btn_oai_test = QPushButton(tr("btn_test_api"))
        self.btn_oai_test.setObjectName("btn_secondary")
        self.btn_oai_test.clicked.connect(self._test_openai_connection)
        self.btn_o_test = self.btn_oai_test
        self.lbl_oai_test_status = QLabel("")
        self.lbl_oai_test_status.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9d9da8;")
        self.lbl_o_test_status = self.lbl_oai_test_status
        row_oai_test.addWidget(self.lbl_oai_test)
        row_oai_test.addWidget(self.btn_oai_test)
        row_oai_test.addWidget(self.lbl_oai_test_status, stretch=1)
        oai_layout.addLayout(row_oai_test)
        lc_layout.addWidget(self.openai_container)

        # 5. Gemini Container
        self.gemini_container = QWidget()
        gem_layout = QVBoxLayout(self.gemini_container)
        gem_layout.setContentsMargins(0, 0, 0, 0)
        gem_layout.setSpacing(8)

        row_gem_key = QHBoxLayout()
        self.lbl_gem_key = QLabel("Gemini API-Key:")
        self.lbl_gem_key.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_gem_key = QLineEdit(config.formatting.get_api_key("gemini") or "")
        self.input_gem_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_gem_key.setPlaceholderText(tr("gemini_key_placeholder"))
        self.input_gem_key.textChanged.connect(self._on_gem_key_changed)
        self.btn_gem_toggle_key = QPushButton(tr("btn_show_key"))
        self.btn_gem_toggle_key.setObjectName("btn_secondary")
        self.btn_gem_toggle_key.setFixedWidth(70)
        self.btn_gem_toggle_key.clicked.connect(lambda: self._toggle_lineedit_password(self.input_gem_key, self.btn_gem_toggle_key))
        row_gem_key.addWidget(self.lbl_gem_key)
        row_gem_key.addWidget(self.input_gem_key, stretch=1)
        row_gem_key.addWidget(self.btn_gem_toggle_key)
        gem_layout.addLayout(row_gem_key)

        row_gem_model = QHBoxLayout()
        self.lbl_gem_model = QLabel("Gemini Modell:")
        self.lbl_gem_model.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_gem_model = QComboBox()
        self.combo_gem_model.addItems(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"])
        cur_gem_model = getattr(config.formatting, "gemini_model", "gemini-2.5-flash")
        if cur_gem_model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]:
            self.combo_gem_model.setCurrentText(cur_gem_model)
        self.combo_gem_model.currentTextChanged.connect(self._on_gem_model_changed)
        row_gem_model.addWidget(self.lbl_gem_model)
        row_gem_model.addWidget(self.combo_gem_model, stretch=1)
        gem_layout.addLayout(row_gem_model)

        row_gem_test = QHBoxLayout()
        self.lbl_gem_test = QLabel(tr("lbl_conn_test"))
        self.lbl_gem_test.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.btn_gem_test = QPushButton(tr("btn_test_api"))
        self.btn_gem_test.setObjectName("btn_secondary")
        self.btn_gem_test.clicked.connect(self._test_gemini_connection)
        self.lbl_gem_test_status = QLabel("")
        self.lbl_gem_test_status.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9d9da8;")
        row_gem_test.addWidget(self.lbl_gem_test)
        row_gem_test.addWidget(self.btn_gem_test)
        row_gem_test.addWidget(self.lbl_gem_test_status, stretch=1)
        gem_layout.addLayout(row_gem_test)
        lc_layout.addWidget(self.gemini_container)

        # 6. Groq Container
        self.groq_container = QWidget()
        grq_layout = QVBoxLayout(self.groq_container)
        grq_layout.setContentsMargins(0, 0, 0, 0)
        grq_layout.setSpacing(8)

        row_grq_key = QHBoxLayout()
        self.lbl_grq_key = QLabel("Groq API-Key:")
        self.lbl_grq_key.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_grq_key = QLineEdit(config.formatting.get_api_key("groq") or "")
        self.input_grq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_grq_key.setPlaceholderText(tr("groq_key_placeholder"))
        self.input_grq_key.textChanged.connect(self._on_grq_key_changed)
        self.btn_grq_toggle_key = QPushButton(tr("btn_show_key"))
        self.btn_grq_toggle_key.setObjectName("btn_secondary")
        self.btn_grq_toggle_key.setFixedWidth(70)
        self.btn_grq_toggle_key.clicked.connect(lambda: self._toggle_lineedit_password(self.input_grq_key, self.btn_grq_toggle_key))
        row_grq_key.addWidget(self.lbl_grq_key)
        row_grq_key.addWidget(self.input_grq_key, stretch=1)
        row_grq_key.addWidget(self.btn_grq_toggle_key)
        grq_layout.addLayout(row_grq_key)

        row_grq_model = QHBoxLayout()
        self.lbl_grq_model = QLabel("Groq Modell:")
        self.lbl_grq_model.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_grq_model = QComboBox()
        self.combo_grq_model.addItems(["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"])
        cur_grq_model = getattr(config.formatting, "groq_model", "llama-3.3-70b-versatile")
        if cur_grq_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]:
            self.combo_grq_model.setCurrentText(cur_grq_model)
        self.combo_grq_model.currentTextChanged.connect(self._on_grq_model_changed)
        row_grq_model.addWidget(self.lbl_grq_model)
        row_grq_model.addWidget(self.combo_grq_model, stretch=1)
        grq_layout.addLayout(row_grq_model)

        row_grq_test = QHBoxLayout()
        self.lbl_grq_test = QLabel(tr("lbl_conn_test"))
        self.lbl_grq_test.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.btn_grq_test = QPushButton(tr("btn_test_api"))
        self.btn_grq_test.setObjectName("btn_secondary")
        self.btn_grq_test.clicked.connect(self._test_groq_connection)
        self.lbl_grq_test_status = QLabel("")
        self.lbl_grq_test_status.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9d9da8;")
        row_grq_test.addWidget(self.lbl_grq_test)
        row_grq_test.addWidget(self.btn_grq_test)
        row_grq_test.addWidget(self.lbl_grq_test_status, stretch=1)
        grq_layout.addLayout(row_grq_test)
        lc_layout.addWidget(self.groq_container)

        # 7. Rules Container
        self.rules_container = QWidget()
        rl_layout = QVBoxLayout(self.rules_container)
        rl_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_rules_info = QLabel(tr("rules_info_text"))
        self.lbl_rules_info.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.02); color: #82828e; font-size: 11.5px; line-height: 1.4; "
            "padding: 10px 14px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.05);"
        )
        rl_layout.addWidget(self.lbl_rules_info)
        lc_layout.addWidget(self.rules_container)

        self._update_detected_provider_badge()
        self._update_engine_panels()
        self._sync_priority_cards_ui(cur_u_model)
        self._update_model_details_ui(cur_u_model)

        sep_fmt1 = QFrame()
        sep_fmt1.setFrameShape(QFrame.Shape.HLine)
        sep_fmt1.setStyleSheet("color: rgba(255, 255, 255, 0.06); margin: 6px 0;")
        lc_layout.addWidget(sep_fmt1)

        # Style & Tone Row
        row_tone = QHBoxLayout()
        self.lbl_tone = QLabel(tr("lbl_tone_profiles"))
        self.lbl_tone.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_tone = QComboBox()
        self.tone_keys = list(TONE_PROFILES.keys())
        for k, v in TONE_PROFILES.items():
            desc = v.get("description", "")
            self.combo_tone.addItem(f"{v['name']} — {desc}")
        cur_tone = getattr(config.formatting, "tone", "default")
        if cur_tone in self.tone_keys:
            self.combo_tone.setCurrentIndex(self.tone_keys.index(cur_tone))
        self.combo_tone.currentIndexChanged.connect(self._on_tone_changed)
        row_tone.addWidget(self.lbl_tone)
        row_tone.addWidget(self.combo_tone, stretch=1)
        lc_layout.addLayout(row_tone)

        # Custom Prompt Input
        row_cp = QHBoxLayout()
        self.lbl_cp = QLabel(tr("lbl_custom_instructions"))
        self.lbl_cp.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_custom_prompt = QLineEdit(getattr(config.formatting, "custom_instructions", ""))
        self.input_custom_prompt.setPlaceholderText("z.B. 'Schreibe stets in prägnanter Fachsprache'")
        self.input_custom_prompt.textChanged.connect(self._on_custom_prompt_changed)
        row_cp.addWidget(self.lbl_cp)
        row_cp.addWidget(self.input_custom_prompt, stretch=1)
        lc_layout.addLayout(row_cp)

        # Collapsible Advanced Formatting Options
        self.btn_toggle_adv_formatting = QPushButton(tr("btn_toggle_adv_formatting"))
        self.btn_toggle_adv_formatting.setObjectName("btn_secondary")
        self.btn_toggle_adv_formatting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_adv_formatting.setStyleSheet("font-size: 11px; padding: 4px 10px; margin-top: 4px;")
        self.btn_toggle_adv_formatting.clicked.connect(self._toggle_advanced_formatting)
        lc_layout.addWidget(self.btn_toggle_adv_formatting)

        self.adv_formatting_frame = QFrame()
        self.adv_formatting_frame.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 6px; }"
        )
        self.adv_formatting_frame.setVisible(False)
        adv_layout = QVBoxLayout(self.adv_formatting_frame)
        adv_layout.setContentsMargins(10, 8, 10, 8)
        adv_layout.setSpacing(8)

        self.chk_filler = QCheckBox(tr("chk_filler"))
        self.chk_filler.setChecked(config.injection.clean_filler_words)
        self.chk_filler.toggled.connect(self._on_filler_toggled)
        adv_layout.addWidget(self.chk_filler)

        self.chk_auto_app_profiles = QCheckBox(tr("chk_auto_app_profiles"))
        self.chk_auto_app_profiles.setChecked(getattr(config.formatting, "auto_app_profiles", True))
        self.chk_auto_app_profiles.toggled.connect(self._on_auto_app_profiles_toggled)
        adv_layout.addWidget(self.chk_auto_app_profiles)

        self.chk_apply_snippets = QCheckBox(tr("chk_apply_snippets"))
        self.chk_apply_snippets.setChecked(getattr(config.injection, "apply_snippets", True))
        self.chk_apply_snippets.toggled.connect(self._on_apply_snippets_toggled)
        adv_layout.addWidget(self.chk_apply_snippets)

        self.chk_send_it = QCheckBox(tr("chk_send_it"))
        self.chk_send_it.setChecked(getattr(config.formatting, "send_it_enabled", True) and getattr(config.injection, "send_it_enabled", True))
        self.chk_send_it.toggled.connect(self._on_send_it_toggled)
        adv_layout.addWidget(self.chk_send_it)

        self.chk_context_intelligence = QCheckBox(tr("chk_context_intelligence"))
        self.chk_context_intelligence.setChecked(getattr(config.formatting, "context_intelligence", True))
        self.chk_context_intelligence.toggled.connect(self._on_context_intelligence_toggled)
        adv_layout.addWidget(self.chk_context_intelligence)

        self.chk_workspace_seeding = QCheckBox(tr("chk_workspace_seeding"))
        self.chk_workspace_seeding.setChecked(getattr(config.formatting, "workspace_seeding", True))
        self.chk_workspace_seeding.toggled.connect(self._on_workspace_seeding_toggled)
        adv_layout.addWidget(self.chk_workspace_seeding)

        self.chk_spoken_markdown = QCheckBox(tr("chk_spoken_markdown"))
        self.chk_spoken_markdown.setChecked(getattr(config.formatting, "spoken_markdown", True))
        self.chk_spoken_markdown.toggled.connect(self._on_spoken_markdown_toggled)
        adv_layout.addWidget(self.chk_spoken_markdown)

        lc_layout.addWidget(self.adv_formatting_frame)
        layout.addWidget(self.card_fmt)

        # =====================================================================
        # CARD 5: SHORTCUTS UND TASTENKOMBINATIONEN (Hotkeys)
        # =====================================================================
        self.card_hk = CollapsibleSettingsCard(
            tr("card_hotkey_title"),
            summary="",
            description=tr("card_hotkey_desc"),
            is_expanded=False,
        )
        hkc_layout = self.card_hk.body_layout

        row_hk = QHBoxLayout()
        self.lbl_hk = QLabel(tr("lbl_hotkey_ptt"))
        self.lbl_hk.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_hotkey = QLineEdit(config.hotkey.key.upper())
        self.input_hotkey.setReadOnly(True)
        self.btn_record_hk = QPushButton(tr("btn_record_hotkey"))
        self.btn_record_hk.setObjectName("btn_secondary")
        self.btn_record_hk.clicked.connect(self._open_hotkey_capture)
        row_hk.addWidget(self.lbl_hk)
        row_hk.addWidget(self.input_hotkey, stretch=1)
        row_hk.addWidget(self.btn_record_hk)
        hkc_layout.addLayout(row_hk)

        row_hk_mode = QHBoxLayout()
        self.lbl_hk_mode = QLabel(tr("lbl_hotkey_mode"))
        self.lbl_hk_mode.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_hk_mode = QComboBox()
        self.combo_hk_mode.addItems([
            tr("hotkey_mode_ptt"),
            tr("hotkey_mode_toggle"),
        ])
        mode_idx = 1 if getattr(config.hotkey, "mode", "push_to_talk") == "toggle" else 0
        self.combo_hk_mode.setCurrentIndex(mode_idx)
        self.combo_hk_mode.currentIndexChanged.connect(self._on_hotkey_mode_changed)
        row_hk_mode.addWidget(self.lbl_hk_mode)
        row_hk_mode.addWidget(self.combo_hk_mode, stretch=1)
        hkc_layout.addLayout(row_hk_mode)

        row_ve = QHBoxLayout()
        self.lbl_ve = QLabel(tr("lbl_voice_edit_key"))
        self.lbl_ve.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_voice_edit_hotkey = QLineEdit(getattr(config.hotkey, "edit_key", "ctrl+alt+space").upper())
        self.input_voice_edit_hotkey.setReadOnly(True)
        self.btn_record_ve = QPushButton(tr("btn_record_hotkey"))
        self.btn_record_ve.setObjectName("btn_secondary")
        self.btn_record_ve.clicked.connect(self._open_voice_edit_hotkey_capture)
        row_ve.addWidget(self.lbl_ve)
        row_ve.addWidget(self.input_voice_edit_hotkey, stretch=1)
        row_ve.addWidget(self.btn_record_ve)
        hkc_layout.addLayout(row_ve)

        row_un = QHBoxLayout()
        self.lbl_un = QLabel(tr("lbl_undo_key"))
        self.lbl_un.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_undo_hotkey = QLineEdit(getattr(config.hotkey, "undo_key", "ctrl+alt+z").upper())
        self.input_undo_hotkey.setReadOnly(True)
        self.btn_record_un = QPushButton(tr("btn_record_hotkey"))
        self.btn_record_un.setObjectName("btn_secondary")
        self.btn_record_un.clicked.connect(self._open_undo_hotkey_capture)
        row_un.addWidget(self.lbl_un)
        row_un.addWidget(self.input_undo_hotkey, stretch=1)
        row_un.addWidget(self.btn_record_un)
        hkc_layout.addLayout(row_un)

        row_sp = QHBoxLayout()
        self.lbl_sp = QLabel(tr("lbl_scratchpad_key"))
        self.lbl_sp.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.input_scratchpad_hotkey = QLineEdit(getattr(config.hotkey, "scratchpad_key", "ctrl+shift+d").upper())
        self.input_scratchpad_hotkey.setReadOnly(True)
        self.btn_record_sp = QPushButton(tr("btn_record_hotkey"))
        self.btn_record_sp.setObjectName("btn_secondary")
        self.btn_record_sp.clicked.connect(self._open_scratchpad_hotkey_capture)
        self.btn_open_sp = QPushButton(tr("btn_open_scratchpad"))
        self.btn_open_sp.setObjectName("btn_secondary")
        self.btn_open_sp.clicked.connect(self._on_open_scratchpad_clicked)
        row_sp.addWidget(self.lbl_sp)
        row_sp.addWidget(self.input_scratchpad_hotkey, stretch=1)
        row_sp.addWidget(self.btn_record_sp)
        row_sp.addWidget(self.btn_open_sp)
        hkc_layout.addLayout(row_sp)

        self.lbl_cancel_info = QLabel(tr("hotkey_tip_cancel"))
        self.lbl_cancel_info.setWordWrap(True)
        self.lbl_cancel_info.setStyleSheet("font-size: 11px; color: #71717a; line-height: 130%; margin-top: 2px;")
        hkc_layout.addWidget(self.lbl_cancel_info)

        layout.addWidget(self.card_hk)

        # =====================================================================
        # CARD 6: DARSTELLUNG UND FLOATING HUD (Appearance und Physics)
        # =====================================================================
        self.card_hud = CollapsibleSettingsCard(
            tr("card_hud_title"),
            summary="",
            description=tr("card_hud_desc"),
            is_expanded=False,
        )
        hud_layout = self.card_hud.body_layout

        self.chk_hud_enable = QCheckBox(tr("lbl_hud_enable"))
        self.chk_hud_enable.setChecked(getattr(config.hud, "enabled", True))
        self.chk_hud_enable.toggled.connect(self._on_hud_enable_toggled)
        hud_layout.addWidget(self.chk_hud_enable)

        self.hud_options_widget = QWidget()
        hopt_layout = QVBoxLayout(self.hud_options_widget)
        hopt_layout.setContentsMargins(0, 0, 0, 0)
        hopt_layout.setSpacing(8)

        row_hud_pos = QHBoxLayout()
        self.lbl_hpos = QLabel(tr("lbl_hud_pos_mode"))
        self.lbl_hpos.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_hud_pos = QComboBox()
        self.combo_hud_pos.addItems(["Unten mittig auf dem Bildschirm", "Dynamisch dem Text-Cursor folgen"])
        pos_idx = 1 if getattr(config.hud, "position_mode", "bottom_center") == "follow_cursor" else 0
        self.combo_hud_pos.setCurrentIndex(pos_idx)
        self.combo_hud_pos.currentIndexChanged.connect(self._on_hud_pos_changed)
        row_hud_pos.addWidget(self.lbl_hpos)
        row_hud_pos.addWidget(self.combo_hud_pos, stretch=1)
        hopt_layout.addLayout(row_hud_pos)

        self.chk_hud_fluid = QCheckBox(tr("lbl_hud_fluid"))
        self.chk_hud_fluid.setChecked(getattr(config.hud, "fluid_animations", True))
        self.chk_hud_fluid.toggled.connect(self._on_hud_fluid_toggled)
        hopt_layout.addWidget(self.chk_hud_fluid)

        self.chk_hud_minimal = QCheckBox(tr("lbl_hud_minimal"))
        self.chk_hud_minimal.setChecked(getattr(config.hud, "minimal_mode", False))
        self.chk_hud_minimal.toggled.connect(self._on_hud_minimal_toggled)
        hopt_layout.addWidget(self.chk_hud_minimal)

        self.hud_pos_mem_widget = QWidget()
        row_hud_mem = QHBoxLayout(self.hud_pos_mem_widget)
        row_hud_mem.setContentsMargins(0, 0, 0, 0)
        self.chk_hud_remember_pos = QCheckBox(tr("lbl_hud_remember_pos"))
        self.chk_hud_remember_pos.setChecked(getattr(config.hud, "remember_position", True))
        self.chk_hud_remember_pos.toggled.connect(self._on_hud_remember_pos_toggled)
        row_hud_mem.addWidget(self.chk_hud_remember_pos, stretch=1)

        self.btn_hud_reset_pos = QPushButton(tr("btn_hud_reset_pos"))
        self.btn_hud_reset_pos.setObjectName("btn_secondary")
        self.btn_hud_reset_pos.clicked.connect(self._on_hud_reset_pos_clicked)
        row_hud_mem.addWidget(self.btn_hud_reset_pos)
        self.hud_pos_mem_widget.setVisible(pos_idx == 0)
        hopt_layout.addWidget(self.hud_pos_mem_widget)

        hud_sliders_frame = QFrame()
        hud_sliders_frame.setStyleSheet("background-color: #141419; border: 1px solid #23232b; border-radius: 8px;")
        hud_sliders_layout = QVBoxLayout(hud_sliders_frame)
        hud_sliders_layout.setContentsMargins(12, 10, 12, 10)
        hud_sliders_layout.setSpacing(10)

        row_opacity = QHBoxLayout()
        self.lbl_opacity_title = QLabel(tr("lbl_hud_opacity"))
        self.lbl_opacity_title.setStyleSheet("font-weight: 500; min-width: 140px; color: #d4d4d8;")
        self.slider_hud_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_hud_opacity.setRange(65, 95)
        self.slider_hud_opacity.setValue(getattr(config.hud, "opacity_percent", 78))
        self.lbl_hud_opacity_val = QLabel(f"{self.slider_hud_opacity.value()}%")
        self.lbl_hud_opacity_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 45px; text-align: right;")
        self.slider_hud_opacity.valueChanged.connect(self._on_hud_opacity_changed)
        row_opacity.addWidget(self.lbl_opacity_title)
        row_opacity.addWidget(self.slider_hud_opacity, stretch=1)
        row_opacity.addWidget(self.lbl_hud_opacity_val)
        hud_sliders_layout.addLayout(row_opacity)

        row_bounce = QHBoxLayout()
        self.lbl_bounce_title = QLabel(tr("lbl_hud_bounce"))
        self.lbl_bounce_title.setStyleSheet("font-weight: 500; min-width: 140px; color: #d4d4d8;")
        self.slider_hud_bounce = QSlider(Qt.Orientation.Horizontal)
        self.slider_hud_bounce.setRange(0, 100)
        self.slider_hud_bounce.setValue(getattr(config.hud, "bounce_intensity", 50))
        self.lbl_hud_bounce_val = QLabel(self._get_bounce_label(self.slider_hud_bounce.value()))
        self.lbl_hud_bounce_val.setStyleSheet("color: #a855f7; font-weight: bold; min-width: 130px; text-align: right;")
        self.slider_hud_bounce.valueChanged.connect(self._on_hud_bounce_changed)
        row_bounce.addWidget(self.lbl_bounce_title)
        row_bounce.addWidget(self.slider_hud_bounce, stretch=1)
        row_bounce.addWidget(self.lbl_hud_bounce_val)
        hud_sliders_layout.addLayout(row_bounce)

        row_scale = QHBoxLayout()
        self.lbl_scale_title = QLabel(tr("lbl_hud_scale"))
        self.lbl_scale_title.setStyleSheet("font-weight: 500; min-width: 140px; color: #d4d4d8;")
        self.slider_hud_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_hud_scale.setRange(85, 115)
        self.slider_hud_scale.setValue(getattr(config.hud, "scale_percent", 100))
        self.lbl_hud_scale_val = QLabel(self._get_scale_label(self.slider_hud_scale.value()))
        self.lbl_hud_scale_val.setStyleSheet("color: #10b981; font-weight: bold; min-width: 130px; text-align: right;")
        self.slider_hud_scale.valueChanged.connect(self._on_hud_scale_changed)
        row_scale.addWidget(self.lbl_scale_title)
        row_scale.addWidget(self.slider_hud_scale, stretch=1)
        row_scale.addWidget(self.lbl_hud_scale_val)
        hud_sliders_layout.addLayout(row_scale)

        hopt_layout.addWidget(hud_sliders_frame)

        self.chk_hud_enable.toggled.connect(self.hud_options_widget.setEnabled)
        self.hud_options_widget.setEnabled(getattr(config.hud, "enabled", True))
        hud_layout.addWidget(self.hud_options_widget)

        layout.addWidget(self.card_hud)

        # =====================================================================
        # CARD 7: ERWEITERT & DATENSCHUTZ (Air-Gapped Privacy & Diagnostics)
        # =====================================================================
        self.card_adv = CollapsibleSettingsCard(
            tr("card_sys_title"),
            summary="",
            description=tr("card_sys_desc"),
            is_expanded=False,
        )
        adv_card_layout = self.card_adv.body_layout

        # UI Language Selection
        row_lang = QHBoxLayout()
        self.lbl_ui_lang_title = QLabel(tr("lbl_ui_language"))
        self.lbl_ui_lang_title.setStyleSheet("font-weight: 500; min-width: 170px; color: #9d9da8;")
        self.combo_ui_lang = QComboBox()
        self.combo_ui_lang.addItem("English", "en")
        self.combo_ui_lang.addItem("Deutsch", "de")
        cur_lang = getattr(config.system, "ui_language", "en")
        self.combo_ui_lang.setCurrentIndex(1 if cur_lang == "de" else 0)
        self.combo_ui_lang.currentIndexChanged.connect(self._on_ui_language_changed)
        row_lang.addWidget(self.lbl_ui_lang_title)
        row_lang.addWidget(self.combo_ui_lang, stretch=1)
        adv_card_layout.addLayout(row_lang)

        self.chk_privacy_shield = QCheckBox(tr("lbl_privacy_shield"))
        self.chk_privacy_shield.setChecked(getattr(config.system, "offline_privacy_mode", False))
        self.chk_privacy_shield.toggled.connect(self._on_privacy_shield_toggled)
        adv_card_layout.addWidget(self.chk_privacy_shield)

        self.chk_restore_clip = QCheckBox(tr("lbl_restore_clipboard"))
        self.chk_restore_clip.setChecked(getattr(config.injection, "restore_clipboard", True))
        self.chk_restore_clip.toggled.connect(lambda v: setattr(config.injection, "restore_clipboard", v) or config.save())
        adv_card_layout.addWidget(self.chk_restore_clip)

        self.lbl_diag = QLabel(tr("lbl_hardware_diag", hw=self.hw_badge_text))
        self.lbl_diag.setStyleSheet("font-size: 11px; color: #555562; margin-top: 4px;")
        adv_card_layout.addWidget(self.lbl_diag)

        layout.addWidget(self.card_adv)

        # Backward compatibility aliases
        self.card_llm = self.card_fmt
        self.card_sound = self.card_gen
        self.card_mob = self.card_audio
        self.card_sys = self.card_adv

        self.all_settings_cards = [
            self.card_gen,
            self.card_audio,
            self.card_stt,
            self.card_fmt,
            self.card_hk,
            self.card_hud,
            self.card_adv,
        ]

        layout.addStretch()

        
        # Update All Sub-Labels Across Settings Cards
        if hasattr(self, "lbl_top_info"):
            self.lbl_top_info.setText(tr("settings_header"))
        if hasattr(self, "lbl_stheme"):
            self.lbl_stheme.setText(tr("lbl_sound_theme"))
        if hasattr(self, "lbl_svol"):
            self.lbl_svol.setText(tr("lbl_sound_volume"))
        if hasattr(self, "lbl_mic"):
            self.lbl_mic.setText(tr("lbl_mic_input"))
        if hasattr(self, "lbl_gain_title"):
            self.lbl_gain_title.setText(tr("lbl_gain_title"))
        if hasattr(self, "lbl_gain_help"):
            self.lbl_gain_help.setText(tr("lbl_mic_tip"))
        if hasattr(self, "lbl_duck_title"):
            self.lbl_duck_title.setText(tr("lbl_duck_title"))
        if hasattr(self, "lbl_murl"):
            self.lbl_murl.setText(tr("lbl_mobile_url"))
        if hasattr(self, "lbl_mob_hint"):
            self.lbl_mob_hint.setText(tr("lbl_mobile_hint"))
        if hasattr(self, "lbl_mobile_status"):
            self.lbl_mobile_status.setText(tr("lbl_mobile_active") if getattr(config.mobile_bridge, "enabled", False) else tr("lbl_mobile_inactive"))
        if hasattr(self, "lbl_prov"):
            self.lbl_prov.setText(tr("lbl_stt_provider"))
        if hasattr(self, "lbl_storage_title"):
            self.lbl_storage_title.setText(tr("lbl_models_storage"))
        if hasattr(self, "lbl_models_header"):
            self.lbl_models_header.setText(tr("lbl_available_models"))
        if hasattr(self, "lbl_eng"):
            self.lbl_eng.setText(tr("lbl_fmt_engine"))
        if hasattr(self, "lbl_u_ep"):
            self.lbl_u_ep.setText(tr("lbl_api_endpoint"))
        if hasattr(self, "lbl_u_det"):
            self.lbl_u_det.setText(tr("lbl_detected_provider"))
        if hasattr(self, "lbl_u_key"):
            self.lbl_u_key.setText(tr("lbl_api_key"))
        if hasattr(self, "lbl_prio"):
            self.lbl_prio.setText(tr("lbl_prio_title"))
        if hasattr(self, "lbl_cp"):
            self.lbl_cp.setText(tr("lbl_custom_instructions"))
        if hasattr(self, "lbl_hk"):
            self.lbl_hk.setText(tr("lbl_hotkey_ptt"))
        if hasattr(self, "lbl_hk_mode"):
            self.lbl_hk_mode.setText(tr("lbl_hotkey_mode"))
        if hasattr(self, "lbl_ve"):
            self.lbl_ve.setText(tr("lbl_voice_edit_key"))
        if hasattr(self, "lbl_un"):
            self.lbl_un.setText(tr("lbl_undo_key"))
        if hasattr(self, "lbl_sp"):
            self.lbl_sp.setText(tr("lbl_scratchpad_key"))
        if hasattr(self, "lbl_cancel_info"):
            self.lbl_cancel_info.setText(tr("hotkey_tip_cancel"))
        if hasattr(self, "lbl_hpos"):
            self.lbl_hpos.setText(tr("lbl_hud_pos_mode"))
        if hasattr(self, "lbl_opacity_title"):
            self.lbl_opacity_title.setText(tr("lbl_hud_opacity"))
        if hasattr(self, "lbl_bounce_title"):
            self.lbl_bounce_title.setText(tr("lbl_hud_bounce"))
        if hasattr(self, "lbl_scale_title"):
            self.lbl_scale_title.setText(tr("lbl_hud_scale"))
        if hasattr(self, "lbl_diag"):
            self.lbl_diag.setText(tr("lbl_hardware_diag", hw=self.hw_badge_text))

        self._update_settings_summaries()

        scroll.setWidget(container)
        tab_layout = QVBoxLayout(self.tab_settings)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

    # =========================================================================
    # STT Provider State & Dynamic Visibility
    # =========================================================================

    def _on_stt_provider_changed(self, idx: int):
        provider_map = {0: "local", 1: "universal", 2: "grok", 3: "openai"}
        chosen = provider_map.get(idx, "local")
        config.whisper.provider = chosen
        config.save()
        self._update_stt_provider_visibility()

    def _update_stt_provider_visibility(self):
        active_provider = getattr(config.whisper, "provider", "local")

        # 1. Local Mode
        if active_provider == "local":
            self.local_models_widget.setVisible(True)
            if hasattr(self, "universal_stt_widget"):
                self.universal_stt_widget.setVisible(False)
            self.groq_key_widget.setVisible(False)
            self.openai_key_widget.setVisible(False)
            self.cloud_banner.setVisible(False)
            if hasattr(self, "card_stt"):
                self.card_stt.lbl_title.setText(f"{tr('card_stt_title')} ({self.short_gpu_name.upper()})")
            self.pill_profile.setText(f"STT: {config.whisper.profile.upper()}")

        # 2. Universal STT API Mode (OpenRouter, Custom Endpoint, Self-Hosted)
        elif active_provider in ("universal", "openrouter", "custom"):
            self.local_models_widget.setVisible(False)
            if hasattr(self, "universal_stt_widget"):
                self.universal_stt_widget.setVisible(True)
            self.groq_key_widget.setVisible(False)
            self.openai_key_widget.setVisible(False)
            m_name = getattr(config.whisper, "universal_model", "openai/whisper-large-v3")
            self.cloud_banner.setText(tr("cloud_banner_universal", model=m_name))
            self.cloud_banner.setVisible(True)
            if hasattr(self, "card_stt"):
                self.card_stt.lbl_title.setText(f"{tr('card_stt_title')} (UNIVERSAL API)")
            self.pill_profile.setText("STT: UNIVERSAL API")

        # 3. Grok AI Mode
        elif active_provider in ("grok", "groq"):
            self.local_models_widget.setVisible(False)
            if hasattr(self, "universal_stt_widget"):
                self.universal_stt_widget.setVisible(False)
            self.groq_key_widget.setVisible(True)
            self.openai_key_widget.setVisible(False)
            self.cloud_banner.setText(tr("cloud_banner_groq"))
            self.cloud_banner.setVisible(True)
            if hasattr(self, "card_stt"):
                self.card_stt.lbl_title.setText(f"{tr('card_stt_title')} (GROQ LPU)")
            self.pill_profile.setText("STT: GROQ LPU")

        # 4. OpenAI Mode
        elif active_provider == "openai":
            self.local_models_widget.setVisible(False)
            if hasattr(self, "universal_stt_widget"):
                self.universal_stt_widget.setVisible(False)
            self.groq_key_widget.setVisible(False)
            self.openai_key_widget.setVisible(True)
            self.cloud_banner.setText(tr("cloud_banner_openai"))
            self.cloud_banner.setVisible(True)
            if hasattr(self, "card_stt"):
                self.card_stt.lbl_title.setText(f"{tr('card_stt_title')} (OPENAI)")
            self.pill_profile.setText("STT: OPENAI")

        if hasattr(self, "card_stt"):
            self._update_settings_summaries()

        self._update_hw_badge_string()
        self.lbl_hw_badge.setText(self.hw_badge_text)

    def _on_ui_language_changed(self, idx: int):
        lang_code = self.combo_ui_lang.itemData(idx) or ("de" if idx == 1 else "en")
        config.system.ui_language = lang_code
        set_current_language(lang_code)
        config.save()
        signals.language_changed.emit(lang_code)

    def retranslate_ui(self, lang_code: Optional[str] = None):
        """Dynamically update all user-facing labels, buttons, cards, placeholders and dropdown options across the dashboard."""
        if lang_code:
            set_current_language(lang_code)
        self.setWindowTitle(tr("app_title"))
        if hasattr(self, "tabs"):
            self.tabs.setTabText(0, tr("tab_dashboard"))
            self.tabs.setTabText(1, tr("tab_library_combined"))
            self.tabs.setTabText(2, tr("tab_settings"))

        # Studio Tab Hero & Status
        if hasattr(self, "lbl_hero_action") and not getattr(self.hero_waveform, "is_recording", False):
            self.lbl_hero_action.setText(tr("hero_status_ready"))
            is_toggle = (getattr(config.hotkey, "mode", "push_to_talk") == "toggle")
            k = config.hotkey.key.upper()
            self.lbl_hero_sub.setText(tr("hero_sub_toggle", key=k) if is_toggle else tr("hero_sub_ptt", key=k))

        if hasattr(self, "status_badge") and not getattr(self.hero_waveform, "is_recording", False):
            self.status_badge.setText(tr("ready"))

        if hasattr(self, "privacy_badge"):
            self.privacy_badge.setText(tr("privacy_badge_text"))

        if hasattr(self, "btn_hero_scratchpad"):
            self.btn_hero_scratchpad.setText(tr("hero_scratchpad_btn"))

        # Studio Latest Transcription Card
        if hasattr(self, "tc_title"):
            self.tc_title.setText(tr("latest_dictation_title"))
        if hasattr(self, "btn_copy_latest"):
            self.btn_copy_latest.setText(tr("copy"))

        # Studio Section Titles & Mode Cards
        if hasattr(self, "mc_title"):
            self.mc_title.setText(tr("section_mode_title"))
        if hasattr(self, "mode_cards"):
            if "flow" in self.mode_cards:
                self.mode_cards["flow"].lbl_title.setText(tr("mode_flow_title"))
                self.mode_cards["flow"].lbl_sub.setText(tr("mode_flow_desc"))
            if "raw" in self.mode_cards:
                self.mode_cards["raw"].lbl_title.setText(tr("mode_raw_title"))
                self.mode_cards["raw"].lbl_sub.setText(tr("mode_raw_desc"))

        # Studio Tone Section & Cards
        if hasattr(self, "tone_title"):
            self.tone_title.setText(tr("tone_section_title"))
        if hasattr(self, "lbl_tone_status"):
            is_flow = (getattr(config.formatting, "mode", "flow") == "flow")
            self.lbl_tone_status.setText(tr("tone_status_active") if is_flow else tr("tone_status_inactive"))

        if hasattr(self, "tone_cards"):
            tone_trans = {
                "default": ("tone_default_title", "tone_default_desc"),
                "formal_sie": ("tone_formal_title", "tone_formal_desc"),
                "informal_du": ("tone_informal_title", "tone_informal_desc"),
                "concise": ("tone_concise_title", "tone_concise_desc"),
                "academic": ("tone_academic_title", "tone_academic_desc"),
                "latex": ("tone_latex_title", "tone_latex_desc"),
            }
            for tk, t_card in self.tone_cards.items():
                if tk in tone_trans:
                    title_k, desc_k = tone_trans[tk]
                    if hasattr(t_card, "lbl_title"):
                        t_card.lbl_title.setText(tr(title_k))
                    if hasattr(t_card, "lbl_sub"):
                        t_card.lbl_sub.setText(tr(desc_k))

        # Library Sub-Navigation & Forms
        if hasattr(self, "btn_sub_vocab"):
            self.btn_sub_vocab.setText(tr("tab_vocabulary"))
        if hasattr(self, "btn_sub_snippets"):
            self.btn_sub_snippets.setText(tr("tab_snippets"))
        if hasattr(self, "btn_sub_apps"):
            self.btn_sub_apps.setText(tr("tab_profiles"))
        if hasattr(self, "lbl_app_info"):
            self.lbl_app_info.setText(tr("app_rules_info"))

        if hasattr(self, "lbl_history_title"):
            self.lbl_history_title.setText(tr("history_title"))
        if hasattr(self, "lbl_hist_count"):
            self.lbl_hist_count.setText(tr("history_entries_count", count=len(self.history_records)))
        if hasattr(self, "lbl_hist_empty_title"):
            self.lbl_hist_empty_title.setText(tr("history_empty_title"))
        if hasattr(self, "lbl_hist_empty_sub"):
            self.lbl_hist_empty_sub.setText(tr("history_empty_desc", key=config.hotkey.key.upper()))

        if hasattr(self, "input_new_word"):
            self.input_new_word.setPlaceholderText(tr("word_placeholder"))
        if hasattr(self, "combo_new_cat"):
            cur_cat_idx = self.combo_new_cat.currentIndex()
            self.combo_new_cat.blockSignals(True)
            self.combo_new_cat.clear()
            self.combo_new_cat.addItems([tr("cat_tech"), tr("cat_dev"), tr("cat_name"), tr("cat_company"), tr("cat_abbr"), tr("cat_general")])
            if 0 <= cur_cat_idx < self.combo_new_cat.count():
                self.combo_new_cat.setCurrentIndex(cur_cat_idx)
            self.combo_new_cat.blockSignals(False)
        if hasattr(self, "vocab_search"):
            self.vocab_search.setPlaceholderText(tr("filter_vocab_placeholder"))
        if hasattr(self, "btn_vocab_add"):
            self.btn_vocab_add.setText(tr("btn_add_term"))
        if hasattr(self, "btn_vocab_cancel"):
            self.btn_vocab_cancel.setText(tr("cancel"))

        if hasattr(self, "input_snip_trig"):
            self.input_snip_trig.setPlaceholderText(tr("trigger_placeholder"))
        if hasattr(self, "input_snip_exp"):
            self.input_snip_exp.setPlaceholderText(tr("expansion_placeholder"))
        if hasattr(self, "btn_snip_add"):
            self.btn_snip_add.setText(tr("btn_add_snippet"))
        if hasattr(self, "btn_snip_cancel"):
            self.btn_snip_cancel.setText(tr("cancel"))

        # Settings Search & Toolbar
        if hasattr(self, "lbl_top_info"):
            self.lbl_top_info.setText(tr("settings_header"))
        if hasattr(self, "btn_expand_all"):
            self.btn_expand_all.setText(tr("expand_all"))
        if hasattr(self, "btn_collapse_all"):
            self.btn_collapse_all.setText(tr("collapse_all"))
        if hasattr(self, "input_settings_search"):
            self.input_settings_search.setPlaceholderText(tr("search_settings_placeholder"))

        # 7 Collapsible Settings Cards (Titles & Descriptions)
        if hasattr(self, "card_gen"):
            self.card_gen.lbl_title.setText(tr("card_gen_title"))
            self.card_gen.lbl_desc.setText(tr("card_gen_desc"))
        if hasattr(self, "card_audio"):
            self.card_audio.lbl_title.setText(tr("card_audio_title"))
            self.card_audio.lbl_desc.setText(tr("card_audio_desc"))
        if hasattr(self, "card_stt"):
            self.card_stt.lbl_title.setText(tr("card_stt_title"))
            self.card_stt.lbl_desc.setText(tr("card_stt_desc"))
        if hasattr(self, "card_fmt"):
            self.card_fmt.lbl_title.setText(tr("card_fmt_title"))
            self.card_fmt.lbl_desc.setText(tr("card_fmt_desc"))
        if hasattr(self, "card_hk"):
            self.card_hk.lbl_title.setText(tr("card_hotkey_title"))
            self.card_hk.lbl_desc.setText(tr("card_hotkey_desc"))
        if hasattr(self, "card_hud"):
            self.card_hud.lbl_title.setText(tr("card_hud_title"))
            self.card_hud.lbl_desc.setText(tr("card_hud_desc"))
        if hasattr(self, "card_adv"):
            self.card_adv.lbl_title.setText(tr("card_sys_title"))
            self.card_adv.lbl_desc.setText(tr("card_sys_desc"))

        # Card 1: Allgemein & Klänge
        if hasattr(self, "chk_autostart"):
            self.chk_autostart.setText(tr("lbl_autostart"))
        if hasattr(self, "chk_minimized"):
            self.chk_minimized.setText(tr("lbl_start_minimized"))
        if hasattr(self, "chk_sound_cues"):
            self.chk_sound_cues.setText(tr("lbl_sound_cues"))
        if hasattr(self, "lbl_stheme"):
            self.lbl_stheme.setText(tr("lbl_sound_theme"))
        if hasattr(self, "btn_preview_sound"):
            self.btn_preview_sound.setText(tr("btn_sound_preview"))
        if hasattr(self, "lbl_svol"):
            self.lbl_svol.setText(tr("lbl_sound_volume"))

        if hasattr(self, "combo_sound_theme"):
            cur_th_data = getattr(config.system, "sound_theme", "velodictum_silk")
            self.combo_sound_theme.blockSignals(True)
            self.combo_sound_theme.clear()
            from sound_effects import get_sound_themes
            self.sound_theme_keys = []
            for th_id, th_meta in get_sound_themes().items():
                self.combo_sound_theme.addItem(f"{th_meta['name']}", th_id)
                self.sound_theme_keys.append(th_id)
            for i in range(self.combo_sound_theme.count()):
                if self.combo_sound_theme.itemData(i) == cur_th_data:
                    self.combo_sound_theme.setCurrentIndex(i)
                    break
            self.combo_sound_theme.blockSignals(False)

        if hasattr(self, "combo_sound_vol") and hasattr(self, "vol_values"):
            cur_idx = self.combo_sound_vol.currentIndex()
            self.combo_sound_vol.blockSignals(True)
            self.combo_sound_vol.clear()
            vol_trans = [
                (0.25, f"25% ({tr('vol_very_quiet')})"),
                (0.45, f"45% ({tr('vol_soft')})"),
                (0.65, f"65% ({tr('vol_standard')})"),
                (0.75, f"75% ({tr('vol_present')})"),
                (1.00, f"100% ({tr('vol_maximum')})"),
            ]
            for vval, vlbl in vol_trans:
                self.combo_sound_vol.addItem(vlbl, vval)
            if 0 <= cur_idx < self.combo_sound_vol.count():
                self.combo_sound_vol.setCurrentIndex(cur_idx)
            self.combo_sound_vol.blockSignals(False)

        # Card 2: Audio & Mikrofon
        if hasattr(self, "lbl_mic"):
            self.lbl_mic.setText(tr("lbl_mic_input"))
        if hasattr(self, "lbl_gain_title"):
            self.lbl_gain_title.setText(tr("lbl_gain_title"))
        if hasattr(self, "lbl_gain_help"):
            self.lbl_gain_help.setText(tr("lbl_mic_tip"))
        if hasattr(self, "btn_mic_test"):
            self.btn_mic_test.setText(tr("btn_mic_test_start") if not getattr(self, "mic_test_running", False) else tr("btn_mic_test_stop"))
        if hasattr(self, "lbl_mic_test_status"):
            self.lbl_mic_test_status.setText(tr("lbl_mic_inactive") if not getattr(self, "mic_test_running", False) else tr("listening"))
        if hasattr(self, "chk_auto_ducking"):
            self.chk_auto_ducking.setText(tr("lbl_auto_ducking"))
        if hasattr(self, "lbl_duck_title"):
            self.lbl_duck_title.setText(tr("lbl_duck_title"))
        if hasattr(self, "lbl_ducking_level_val") and hasattr(self, "slider_ducking_level"):
            val = self.slider_ducking_level.value()
            desc = tr("vol_very_quiet") if val <= 15 else tr("vol_soft") if val <= 30 else tr("vol_standard")
            self.lbl_ducking_level_val.setText(f"{val}% ({desc})")
        if hasattr(self, "chk_mobile_bridge"):
            self.chk_mobile_bridge.setText(tr("lbl_mobile_bridge"))
        if hasattr(self, "lbl_murl"):
            self.lbl_murl.setText(tr("lbl_mobile_url"))
        if hasattr(self, "btn_copy_mob"):
            self.btn_copy_mob.setText(tr("copy"))
        if hasattr(self, "btn_open_mob"):
            self.btn_open_mob.setText(tr("btn_open_browser"))
        if hasattr(self, "btn_rotate_mob_token"):
            self.btn_rotate_mob_token.setText(tr("btn_rotate_token"))
        if hasattr(self, "lbl_mobile_status"):
            self.lbl_mobile_status.setText(tr("lbl_mobile_active") if getattr(config.mobile_bridge, "enabled", False) else tr("lbl_mobile_inactive"))
        if hasattr(self, "lbl_mob_hint"):
            self.lbl_mob_hint.setText(tr("lbl_mobile_hint"))

        # Card 3: Spracherkennung (STT)
        if hasattr(self, "lbl_prov"):
            self.lbl_prov.setText(tr("lbl_stt_provider"))
        if hasattr(self, "combo_stt_provider"):
            cur_p_idx = self.combo_stt_provider.currentIndex()
            self.combo_stt_provider.blockSignals(True)
            self.combo_stt_provider.clear()
            self.combo_stt_provider.addItems([
                tr("stt_prov_local", gpu=self.short_gpu_name),
                tr("stt_prov_universal"),
                tr("stt_prov_grok"),
                tr("stt_prov_openai"),
            ])
            self.combo_stt_provider.setCurrentIndex(cur_p_idx)
            self.combo_stt_provider.blockSignals(False)

        if hasattr(self, "lbl_u_url"):
            self.lbl_u_url.setText(tr("lbl_universal_stt_url"))
        if hasattr(self, "lbl_u_stt_key"):
            self.lbl_u_stt_key.setText(tr("lbl_universal_stt_key"))
        if hasattr(self, "lbl_u_stt_model"):
            self.lbl_u_stt_model.setText(tr("lbl_universal_stt_model"))
        if hasattr(self, "lbl_gkey"):
            self.lbl_gkey.setText(tr("lbl_api_key"))
        if hasattr(self, "lbl_oai_stt_key"):
            self.lbl_oai_stt_key.setText(tr("lbl_api_key"))

        # VRAM Model Presets Retranslation
        if hasattr(self, "profile_cards"):
            vram_sub_keys = {
                "multilingual": ("vram_sub_multilingual", 4.5, "4.5 GB VRAM"),
                "de_max": ("vram_sub_de_max", 3.2, "3.2 GB VRAM"),
                "de_fast": ("vram_sub_de_fast", 2.2, "2.2 GB VRAM"),
                "low_vram": ("vram_sub_low_vram", 0.9, "0.9 GB VRAM"),
                "en_fast": ("vram_sub_de_fast", 1.9, "1.9 GB VRAM"),
                "lite": ("vram_sub_low_vram", 0.9, "0.9 GB VRAM"),
            }
            preset_name_map = {
                "multilingual": ("preset_multilingual_name", "preset_multilingual_tag"),
                "de_max": ("preset_de_max_name", "preset_de_max_tag"),
                "de_fast": ("preset_de_fast_name", "preset_de_fast_tag"),
                "low_vram": ("preset_low_vram_name", "preset_low_vram_tag"),
                "en_fast": ("preset_de_fast_name", "preset_de_fast_tag"),
                "lite": ("preset_low_vram_name", "preset_low_vram_tag"),
            }
            for pk, card in self.profile_cards.items():
                if pk in preset_name_map:
                    nk, tk = preset_name_map[pk]
                    if hasattr(card, "lbl_name"):
                        card.lbl_name.setText(tr(nk))
                    if hasattr(card, "lbl_tag"):
                        card.lbl_tag.setText(tr(tk))
                if pk in vram_sub_keys:
                    sk, req_gb, desc_gb = vram_sub_keys[pk]
                    if hasattr(card, "lbl_desc"):
                        card.lbl_desc.setText(tr(sk))
                    if not self.gpu_available:
                        if pk == "lite":
                            col, txt = "#10b981", tr("vram_cpu_ready")
                        elif pk in ("de_fast", "en_fast"):
                            col, txt = "#f59e0b", tr("vram_cpu_slow")
                        else:
                            col, txt = "#ef4444", tr("vram_cpu_not_rec")
                    else:
                        if self.vram_total_gb >= req_gb + 1.0:
                            col, txt = "#10b981", tr("vram_compat", desc=desc_gb)
                        elif self.vram_total_gb >= req_gb:
                            col, txt = "#f59e0b", tr("vram_tight", desc=desc_gb)
                        else:
                            col, txt = "#ef4444", tr("vram_too_low", req=f"{req_gb:.1f}")
                    if hasattr(card, "update_led"):
                        card.update_led(col, txt)

        if hasattr(self, "lbl_storage_title"):
            self.lbl_storage_title.setText(tr("lbl_models_storage"))
        if hasattr(self, "btn_change_storage"):
            self.btn_change_storage.setText(tr("btn_change_storage"))
        if hasattr(self, "lbl_models_header"):
            self.lbl_models_header.setText(tr("lbl_available_models"))
        if hasattr(self, "chk_squelcher"):
            self.chk_squelcher.setText(tr("lbl_hallucination_filter"))
        if hasattr(self, "chk_hallucination"):
            self.chk_hallucination.setText(tr("lbl_hallucination_filter"))

        self._update_disk_space_label()
        self._refresh_model_downloader_list()

        # Card 4: Formatierung & Text-Intelligenz
        if hasattr(self, "lbl_eng"):
            self.lbl_eng.setText(tr("lbl_fmt_engine"))
        if hasattr(self, "combo_engine"):
            cur_e_idx = self.combo_engine.currentIndex()
            self.combo_engine.blockSignals(True)
            self.combo_engine.clear()
            self.combo_engine.addItems([
                tr("fmt_engine_rules"),
                tr("fmt_engine_ollama"),
                tr("fmt_engine_universal"),
                tr("fmt_engine_openai"),
                tr("fmt_engine_gemini"),
                tr("fmt_engine_groq"),
            ])
            self.combo_engine.setCurrentIndex(cur_e_idx)
            self.combo_engine.blockSignals(False)

        if hasattr(self, "lbl_u_ep"):
            self.lbl_u_ep.setText(tr("lbl_api_endpoint"))
        if hasattr(self, "lbl_u_det"):
            self.lbl_u_det.setText(tr("lbl_detected_provider"))
        if hasattr(self, "lbl_u_key"):
            self.lbl_u_key.setText(tr("lbl_api_key"))
        if hasattr(self, "btn_u_toggle_key"):
            self.btn_u_toggle_key.setText(tr("btn_show_key") if self.input_u_key.echoMode() == QLineEdit.EchoMode.Password else tr("btn_hide_key"))
        if hasattr(self, "btn_oai_toggle_key"):
            self.btn_oai_toggle_key.setText(tr("btn_show_key") if self.input_oai_key.echoMode() == QLineEdit.EchoMode.Password else tr("btn_hide_key"))
        if hasattr(self, "btn_gem_toggle_key"):
            self.btn_gem_toggle_key.setText(tr("btn_show_key") if self.input_gem_key.echoMode() == QLineEdit.EchoMode.Password else tr("btn_hide_key"))
        if hasattr(self, "btn_grq_toggle_key"):
            self.btn_grq_toggle_key.setText(tr("btn_show_key") if self.input_grq_key.echoMode() == QLineEdit.EchoMode.Password else tr("btn_hide_key"))

        if hasattr(self, "lbl_prio"):
            self.lbl_prio.setText(tr("lbl_prio_title"))

        if hasattr(self, "card_prio_fast") and hasattr(self.card_prio_fast, "update_texts"):
            self.card_prio_fast.update_texts(tr("prio_speed_title"), tr("prio_speed_badge"), tr("prio_speed_desc"))
        if hasattr(self, "card_prio_balanced") and hasattr(self.card_prio_balanced, "update_texts"):
            self.card_prio_balanced.update_texts(tr("prio_balanced_title"), tr("prio_balanced_badge"), tr("prio_balanced_desc"))
        if hasattr(self, "card_prio_quality") and hasattr(self.card_prio_quality, "update_texts"):
            self.card_prio_quality.update_texts(tr("prio_quality_title"), tr("prio_quality_badge"), tr("prio_quality_desc"))

        if hasattr(self, "lbl_d_m_title"):
            self.lbl_d_m_title.setText(tr("lbl_det_model_title"))
        if hasattr(self, "lbl_d_lat_title"):
            self.lbl_d_lat_title.setText(tr("lbl_det_lat_title"))
        if hasattr(self, "lbl_d_cin_title"):
            self.lbl_d_cin_title.setText(tr("lbl_det_cin_title"))
        if hasattr(self, "lbl_d_cout_title"):
            self.lbl_d_cout_title.setText(tr("lbl_det_cout_title"))
        if hasattr(self, "lbl_d_ctx_title"):
            self.lbl_d_ctx_title.setText(tr("lbl_det_ctx_title"))
        if hasattr(self, "lbl_d_usg_title"):
            self.lbl_d_usg_title.setText(tr("lbl_det_usg_title"))
        if hasattr(self, "lbl_d_route_title"):
            self.lbl_d_route_title.setText(tr("lbl_det_route_title"))
        if hasattr(self, "lbl_d_zdr_title"):
            self.lbl_d_zdr_title.setText(tr("lbl_det_zdr_title"))

        self._update_model_details_ui()

        if hasattr(self, "lbl_u_model"):
            self.lbl_u_model.setText(tr("lbl_u_model_catalog"))
        if hasattr(self, "btn_u_fetch_models"):
            self.btn_u_fetch_models.setText(tr("btn_fetch_models"))
        if hasattr(self, "lbl_route"):
            self.lbl_route.setText(tr("lbl_route_strategy"))

        if hasattr(self, "combo_u_routing"):
            cur_r_idx = self.combo_u_routing.currentIndex()
            self.combo_u_routing.blockSignals(True)
            self.combo_u_routing.clear()
            self.combo_u_routing.addItem(tr("route_opt_latency"), "latency")
            self.combo_u_routing.addItem(tr("route_opt_price"), "price")
            self.combo_u_routing.addItem(tr("route_opt_throughput"), "throughput")
            self.combo_u_routing.addItem(tr("route_opt_default"), "default")
            self.combo_u_routing.setCurrentIndex(cur_r_idx)
            self.combo_u_routing.blockSignals(False)

        if hasattr(self, "chk_u_zdr"):
            self.chk_u_zdr.setText(tr("chk_u_zdr"))
        if hasattr(self, "chk_u_fallbacks"):
            self.chk_u_fallbacks.setText(tr("chk_u_fallbacks"))
        if hasattr(self, "lbl_u_test"):
            self.lbl_u_test.setText(tr("lbl_conn_test"))
        if hasattr(self, "btn_u_test"):
            self.btn_u_test.setText(tr("btn_test_api"))

        if hasattr(self, "btn_toggle_custom_catalog"):
            is_vis = getattr(self, "custom_catalog_frame", None) and not self.custom_catalog_frame.isHidden()
            self.btn_toggle_custom_catalog.setText(tr("btn_hide_custom_catalog") if is_vis else tr("btn_toggle_custom_catalog"))

        if hasattr(self, "lbl_ol_test"):
            self.lbl_ol_test.setText(tr("lbl_conn_test"))
        if hasattr(self, "btn_ol_test"):
            self.btn_ol_test.setText(tr("btn_test_ollama"))

        if hasattr(self, "lbl_oai_test"):
            self.lbl_oai_test.setText(tr("lbl_conn_test"))
        if hasattr(self, "btn_oai_test"):
            self.btn_oai_test.setText(tr("btn_test_api"))

        if hasattr(self, "lbl_gem_test"):
            self.lbl_gem_test.setText(tr("lbl_conn_test"))
        if hasattr(self, "btn_gem_test"):
            self.btn_gem_test.setText(tr("btn_test_api"))

        if hasattr(self, "lbl_grq_test"):
            self.lbl_grq_test.setText(tr("lbl_conn_test"))
        if hasattr(self, "btn_grq_test"):
            self.btn_grq_test.setText(tr("btn_test_api"))

        if hasattr(self, "lbl_rules_info"):
            self.lbl_rules_info.setText(tr("rules_info_text"))

        if hasattr(self, "lbl_tone"):
            self.lbl_tone.setText(tr("lbl_tone_profiles"))

        if hasattr(self, "combo_tone") and hasattr(self, "tone_keys"):
            cur_t_idx = self.combo_tone.currentIndex()
            self.combo_tone.blockSignals(True)
            self.combo_tone.clear()
            tone_trans_map = {
                "default": ("tone_default_title", "tone_default_desc"),
                "formal_sie": ("tone_formal_title", "tone_formal_desc"),
                "informal_du": ("tone_informal_title", "tone_informal_desc"),
                "concise": ("tone_concise_title", "tone_concise_desc"),
                "academic": ("tone_academic_title", "tone_academic_desc"),
                "latex": ("tone_latex_title", "tone_latex_desc"),
            }
            for k in self.tone_keys:
                if k in tone_trans_map:
                    t_title, t_desc = tone_trans_map[k]
                    self.combo_tone.addItem(f"{tr(t_title)} — {tr(t_desc)}", k)
                else:
                    self.combo_tone.addItem(k, k)
            if 0 <= cur_t_idx < self.combo_tone.count():
                self.combo_tone.setCurrentIndex(cur_t_idx)
            self.combo_tone.blockSignals(False)

        if hasattr(self, "lbl_cp"):
            self.lbl_cp.setText(tr("lbl_custom_instructions"))
        if hasattr(self, "input_custom_prompt"):
            self.input_custom_prompt.setPlaceholderText(tr("custom_instructions_placeholder"))

        if hasattr(self, "btn_toggle_adv_formatting"):
            is_adv_vis = getattr(self, "adv_formatting_frame", None) and not self.adv_formatting_frame.isHidden()
            self.btn_toggle_adv_formatting.setText(tr("btn_hide_adv_formatting") if is_adv_vis else tr("btn_toggle_adv_formatting"))

        if hasattr(self, "chk_filler"):
            self.chk_filler.setText(tr("chk_filler"))
        if hasattr(self, "chk_auto_app_profiles"):
            self.chk_auto_app_profiles.setText(tr("chk_auto_app_profiles"))
        if hasattr(self, "chk_apply_snippets"):
            self.chk_apply_snippets.setText(tr("chk_apply_snippets"))
        if hasattr(self, "chk_send_it"):
            self.chk_send_it.setText(tr("chk_send_it"))
        if hasattr(self, "chk_context_intelligence"):
            self.chk_context_intelligence.setText(tr("chk_context_intelligence"))
        if hasattr(self, "chk_workspace_seeding"):
            self.chk_workspace_seeding.setText(tr("chk_workspace_seeding"))
        if hasattr(self, "chk_spoken_markdown"):
            self.chk_spoken_markdown.setText(tr("chk_spoken_markdown"))

        # Card 5: Shortcuts & Tasten
        if hasattr(self, "lbl_hk"):
            self.lbl_hk.setText(tr("lbl_hotkey_ptt"))
        if hasattr(self, "btn_record_hk"):
            self.btn_record_hk.setText(tr("btn_record_hotkey"))
        if hasattr(self, "lbl_hk_mode"):
            self.lbl_hk_mode.setText(tr("lbl_hotkey_mode"))
        if hasattr(self, "combo_hk_mode"):
            cur_hkm_idx = self.combo_hk_mode.currentIndex()
            self.combo_hk_mode.blockSignals(True)
            self.combo_hk_mode.clear()
            self.combo_hk_mode.addItems([tr("mode_ptt"), tr("mode_toggle")])
            self.combo_hk_mode.setCurrentIndex(cur_hkm_idx)
            self.combo_hk_mode.blockSignals(False)

        if hasattr(self, "lbl_ve"):
            self.lbl_ve.setText(tr("lbl_voice_edit_key"))
        if hasattr(self, "btn_record_ve"):
            self.btn_record_ve.setText(tr("btn_record_hotkey"))
        if hasattr(self, "lbl_un"):
            self.lbl_un.setText(tr("lbl_undo_key"))
        if hasattr(self, "btn_record_un"):
            self.btn_record_un.setText(tr("btn_record_hotkey"))
        if hasattr(self, "lbl_sp"):
            self.lbl_sp.setText(tr("lbl_scratchpad_key"))
        if hasattr(self, "btn_record_sp"):
            self.btn_record_sp.setText(tr("btn_record_hotkey"))
        if hasattr(self, "btn_open_sp"):
            self.btn_open_sp.setText(tr("btn_open_scratchpad"))
        if hasattr(self, "lbl_cancel_info"):
            self.lbl_cancel_info.setText(tr("hotkey_tip_cancel"))

        # Card 6: Darstellung & Mini-HUD
        if hasattr(self, "chk_hud_enable"):
            self.chk_hud_enable.setText(tr("lbl_hud_enable"))
        if hasattr(self, "lbl_hpos"):
            self.lbl_hpos.setText(tr("lbl_hud_pos_mode"))
        if hasattr(self, "combo_hud_pos"):
            cur_hp_idx = self.combo_hud_pos.currentIndex()
            self.combo_hud_pos.blockSignals(True)
            self.combo_hud_pos.clear()
            self.combo_hud_pos.addItems([tr("hud_pos_bottom"), tr("hud_pos_cursor")])
            self.combo_hud_pos.setCurrentIndex(cur_hp_idx)
            self.combo_hud_pos.blockSignals(False)

        if hasattr(self, "chk_hud_fluid"):
            self.chk_hud_fluid.setText(tr("lbl_hud_fluid"))
        if hasattr(self, "chk_hud_minimal"):
            self.chk_hud_minimal.setText(tr("lbl_hud_minimal"))
        if hasattr(self, "chk_hud_remember_pos"):
            self.chk_hud_remember_pos.setText(tr("lbl_hud_remember_pos"))
        if hasattr(self, "btn_hud_reset_pos"):
            self.btn_hud_reset_pos.setText(tr("btn_hud_reset_pos"))
        if hasattr(self, "lbl_opacity_title"):
            self.lbl_opacity_title.setText(tr("lbl_hud_opacity"))
        if hasattr(self, "lbl_bounce_title"):
            self.lbl_bounce_title.setText(tr("lbl_hud_bounce"))
        if hasattr(self, "lbl_scale_title"):
            self.lbl_scale_title.setText(tr("lbl_hud_scale"))

        # Card 7: System & Datenschutz
        if hasattr(self, "lbl_ui_lang_title"):
            self.lbl_ui_lang_title.setText(tr("lbl_ui_language"))
        if hasattr(self, "chk_privacy_shield"):
            self.chk_privacy_shield.setText(tr("lbl_privacy_shield"))
        if hasattr(self, "chk_restore_clip"):
            self.chk_restore_clip.setText(tr("lbl_restore_clipboard"))
        if hasattr(self, "lbl_diag"):
            self.lbl_diag.setText(tr("lbl_hardware_diag", hw=self.hw_badge_text))

        if hasattr(self, "combo_ui_lang"):
            cur = get_current_language()
            idx = 1 if cur == "de" else 0
            if self.combo_ui_lang.currentIndex() != idx:
                self.combo_ui_lang.blockSignals(True)
                self.combo_ui_lang.setCurrentIndex(idx)
                self.combo_ui_lang.blockSignals(False)

        self._update_settings_summaries()
        self._update_hw_badge_string()

    def _toggle_key_visibility(self):
        if self.input_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText(tr("btn_hide_key"))
        else:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText(tr("btn_show_key"))

    def _on_rec_started(self):
        self._stop_mic_test()
        self.status_badge.setText(f"● {tr('listening')}")
        self.status_badge.setStyleSheet(
            "background-color: rgba(239, 68, 68, 0.08); color: #ef4444; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.16);"
        )
        self.lbl_hero_action.setText(tr("hero_status_recording"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #ef4444;")
        self.hero_waveform.set_state("recording")

    def _on_rec_stopped(self):
        self.hero_waveform.set_state("idle")

    def _on_rec_cancelled(self):
        self.hero_waveform.set_state("idle")
        self.status_badge.setText(tr("ready"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.08); color: #10b981; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.16);"
        )
        self.lbl_hero_action.setText(tr("hero_status_ready"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #f1f1f4;")

    def _on_audio_level(self, rms: float):
        self.hero_waveform.set_level(rms)
        if hasattr(self, "calib_meter"):
            self.calib_meter.update_level(rms)

    def _on_transcribe_started(self):
        self.status_badge.setText(tr("processing"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.08); color: #38bdf8; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.16);"
        )
        self.lbl_hero_action.setText(tr("hero_status_processing"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #38bdf8;")
        self.hero_waveform.set_state("transcribing")

    def _on_formatting_started(self):
        self.status_badge.setText(tr("formatting"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(192, 132, 252, 0.08); color: #c084fc; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(192, 132, 252, 0.16);"
        )
        self.lbl_hero_action.setText(tr("formatting"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #c084fc;")
        self.hero_waveform.set_state("transcribing")

    def _on_transcribe_completed(self, data: Dict):
        self.status_badge.setText(tr("ready"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.08); color: #10b981; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.16);"
        )
        self.lbl_hero_action.setText(tr("injected"))
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #10b981;")
        self.hero_waveform.set_state("idle")

        text = data.get("text", "")
        latency = data.get("latency", 0.0)

        if text.strip():
            self.lbl_latest_text.setText(f'"{text.strip()}"')
            self.lbl_latest_text.setStyleSheet("font-size: 13px; color: #eeeeef; font-weight: 400; line-height: 145%; padding: 2px 0;")
            
            words = len(text.strip().split())
            word_label = "words" if get_current_language() == "en" else "Wörter"
            lat_label = "Latency" if get_current_language() == "en" else "Latenz"
            self.lbl_latest_stats.setText(f"{words} {word_label} · {latency:.2f}s")
            self.pill_latency.setText(f"{lat_label}: {latency:.2f}s")
            self._add_to_history(text, latency)

    def _on_transcribe_failed(self, err_msg: str):
        self.status_badge.setText(tr("transcription_failed"))
        self.status_badge.setStyleSheet(
            "background-color: rgba(239, 68, 68, 0.08); color: #ef4444; font-weight: 500; font-size: 11.5px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.16);"
        )
        self.lbl_hero_action.setText(f"{tr('transcription_failed')}: {err_msg}")
        self.lbl_hero_action.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #ef4444;")
        self.hero_waveform.set_state("idle")

    def _copy_latest_text(self):
        txt = self.lbl_latest_text.text().strip('"\n\r ')
        if txt and not txt.startswith("Press ") and not txt.startswith("Drücke "):
            pyperclip.copy(txt)
            self.btn_copy_latest.setText(tr("copied"))
            QTimer.singleShot(1500, lambda: self.btn_copy_latest.setText(tr("copy")))

    def _on_mode_clicked(self, mode_key: str):
        config.formatting.mode = mode_key
        config.save()
        self.ai_formatter.mode = mode_key
        for mk, card in self.mode_cards.items():
            card.set_selected(mk == mode_key)
        if hasattr(self, "tone_section_card"):
            self.tone_section_card.setEnabled(mode_key == "flow")
        if hasattr(self, "lbl_tone_status"):
            self.lbl_tone_status.setText("Aktiv für Flow" if mode_key == "flow" else "Inaktiv im Rohdiktat")
        signals.dictation_mode_changed.emit(mode_key)

    def _on_tone_preset_clicked(self, tone_key: str):
        config.formatting.tone = tone_key
        config.save()
        self.ai_formatter.tone = tone_key
        for tk, card in self.tone_cards.items():
            card.set_selected(tk == tone_key)
        if hasattr(self, "combo_tone") and hasattr(self, "tone_keys"):
            if tone_key in self.tone_keys:
                self.combo_tone.blockSignals(True)
                self.combo_tone.setCurrentIndex(self.tone_keys.index(tone_key))
                self.combo_tone.blockSignals(False)

        # Automatic model tier optimization for LaTeX mode (Qwen 2.5 72B / quality)
        if tone_key == "latex":
            if hasattr(self, "_on_priority_card_clicked"):
                self._on_priority_card_clicked("quality")

    def _on_activate_whisper_model(self, model_id: str):
        """Activates any downloaded or selected Whisper model dynamically across UI, backend, and config."""
        config.whisper.model_size = model_id
        config.whisper.provider = "local"

        matched_profile_key = None
        for pk, p_info in PROFILES.items():
            if p_info.get("model") == model_id:
                matched_profile_key = pk
                break

        if matched_profile_key:
            config.whisper.profile = matched_profile_key
            config.whisper.language = PROFILES[matched_profile_key].get("language")
        else:
            config.whisper.profile = model_id
            config.whisper.language = getattr(config.whisper, "language", None)

        config.save()

        # Update preset cards selection
        for pk, card in self.profile_cards.items():
            card.set_selected(pk == matched_profile_key)

        if hasattr(self, "pill_profile"):
            display_name = matched_profile_key.upper() if matched_profile_key else model_id.upper()
            self.pill_profile.setText(f"STT: {display_name}")

        if hasattr(self, "card_stt"):
            self._update_settings_summaries()

        self._refresh_model_downloader_list()

        def _switch():
            try:
                lang = config.whisper.language
                self.stt_engine.change_model(model_id, lang)
            except Exception as e:
                print(f"[ModelSwitch] Error switching model to '{model_id}': {e}")

        threading.Thread(target=_switch, daemon=True).start()

    def _on_profile_clicked(self, profile_key: str):
        if profile_key not in PROFILES:
            return
        p_info = PROFILES[profile_key]
        self._on_activate_whisper_model(p_info["model"])

    def _open_hotkey_capture(self):
        dlg = HotkeyCaptureDialog(current_key=config.hotkey.key, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_combo:
            combo_str = dlg.captured_combo.lower()
            self.input_hotkey.setText(combo_str.upper())
            config.hotkey.key = combo_str
            config.save()
            self.pill_hotkey.setText(tr("pill_hotkey", key=combo_str.upper()))
            if getattr(config.hotkey, "mode", "push_to_talk") == "toggle":
                self.lbl_hero_sub.setText(tr("hero_sub_toggle", key=combo_str.upper()))
            else:
                self.lbl_hero_sub.setText(tr("hero_sub_ptt", key=combo_str.upper()))
            signals.mode_changed.emit(config.hotkey.mode)
            if hasattr(self, "card_hk"):
                self._update_settings_summaries()

    def _open_voice_edit_hotkey_capture(self):
        current = getattr(config.hotkey, "edit_key", "ctrl+alt+space")
        dlg = HotkeyCaptureDialog(current_key=current, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_combo:
            combo_str = dlg.captured_combo.lower()
            self.input_voice_edit_hotkey.setText(combo_str.upper())
            config.hotkey.edit_key = combo_str
            config.save()
            signals.mode_changed.emit(config.hotkey.mode)
            if hasattr(self, "card_hk"):
                self._update_settings_summaries()

    def _open_undo_hotkey_capture(self):
        current = getattr(config.hotkey, "undo_key", "ctrl+alt+z")
        dlg = HotkeyCaptureDialog(current_key=current, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_combo:
            combo_str = dlg.captured_combo.lower()
            self.input_undo_hotkey.setText(combo_str.upper())
            config.hotkey.undo_key = combo_str
            config.save()
            signals.mode_changed.emit(config.hotkey.mode)
            if hasattr(self, "card_hk"):
                self._update_settings_summaries()

    def _open_scratchpad_hotkey_capture(self):
        current = getattr(config.hotkey, "scratchpad_key", "ctrl+shift+d")
        dlg = HotkeyCaptureDialog(current_key=current, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_combo:
            combo_str = dlg.captured_combo.lower()
            self.input_scratchpad_hotkey.setText(combo_str.upper())
            config.hotkey.scratchpad_key = combo_str
            config.save()
            signals.mode_changed.emit(config.hotkey.mode)
            if hasattr(self, "card_hk"):
                self._update_settings_summaries()

    def _on_hotkey_mode_changed(self, idx: int):
        mode = "toggle" if idx == 1 else "push_to_talk"
        config.hotkey.mode = mode
        config.save()
        key_str = config.hotkey.key.upper()
        if mode == "toggle":
            self.lbl_hero_sub.setText(tr("hero_sub_toggle", key=key_str))
        else:
            self.lbl_hero_sub.setText(tr("hero_sub_ptt", key=key_str))
        signals.mode_changed.emit(mode)
        if hasattr(self, "card_hk"):
            self._update_settings_summaries()

    def _on_engine_changed(self, idx: int):
        engines = ["rules", "ollama", "universal", "openai", "gemini", "groq"]
        if idx < len(engines):
            chosen = engines[idx]
            config.formatting.engine = chosen
            config.save()
            self.ai_formatter.engine = chosen
            pill_text = "UNIVERSAL API" if chosen == "universal" else chosen.upper()
            self.pill_engine.setText(tr("pill_engine", engine=pill_text))
            self._update_engine_panels()
            if hasattr(self, "card_llm"):
                self._update_settings_summaries()

    def _update_engine_panels(self):
        eng = getattr(config.formatting, "engine", "rules")
        if eng == "openrouter":
            eng = "universal"
        self.rules_container.setVisible(eng == "rules")
        self.ollama_container.setVisible(eng == "ollama")
        self.universal_container.setVisible(eng == "universal")
        self.openai_container.setVisible(eng == "openai")
        self.gemini_container.setVisible(eng == "gemini")
        self.groq_container.setVisible(eng == "groq")

    def _update_detected_provider_badge(self):
        ep = getattr(config.formatting, "api_endpoint", "")
        key = config.formatting.get_api_key("universal") or ""
        detected = detect_provider(ep, key)
        self.lbl_u_detected.setText(detected)

    def _toggle_lineedit_password(self, line_edit: QLineEdit, button: QPushButton):
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText(tr("btn_hide_key"))
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText(tr("btn_show_key"))

    def _on_u_endpoint_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.api_endpoint = cleaned
        config.save()
        self.ai_formatter.api_endpoint = cleaned
        self._update_detected_provider_badge()

    def _on_u_key_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.set_api_key(cleaned, "universal")
        config.save()
        self.ai_formatter.api_key = cleaned if cleaned else None
        self._update_detected_provider_badge()

    def _on_priority_card_clicked(self, tier_key: str):
        if tier_key == "fast":
            tier_key = "speed"
        tier_data = MODEL_TIERS.get(tier_key)
        if not tier_data:
            return
        m_id = tier_data["model"]
        config.formatting.model = m_id
        config.formatting.openrouter_model = m_id
        config.save()
        self.ai_formatter.model = m_id
        self.ai_formatter.openrouter_model = m_id

        self.combo_u_model.blockSignals(True)
        self.combo_u_model.setEditText(m_id)
        self.combo_u_model.blockSignals(False)

        self._sync_priority_cards_ui(m_id)
        self._update_model_details_ui(m_id)
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    def _sync_priority_cards_ui(self, current_model: str):
        c_raw = (current_model or "").lower().strip()
        c_clean = c_raw.replace("models/", "").replace("openai/", "").replace("google/", "")

        matched = set()
        for k in ("speed", "balanced", "quality"):
            card = self.priority_cards.get(k)
            if not card:
                continue
            tier_info = MODEL_TIERS.get(k, {})
            t_model = tier_info.get("model", "").lower().strip()
            t_clean = t_model.replace("models/", "").replace("openai/", "").replace("google/", "")

            is_match = (
                (c_raw and c_raw == t_model)
                or (c_clean and c_clean == t_clean)
                or (c_clean and c_clean in t_clean)
                or (t_clean and t_clean in c_clean)
                or (c_raw and c_raw in t_model)
                or (t_model and t_model in c_raw)
            )
            if is_match and not matched:
                matched.add(k)
                card.set_selected(True)
            else:
                card.set_selected(False)

    def _update_model_details_ui(self, model_id: Optional[str] = None):
        if not model_id:
            model_id = getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
        det = get_model_details(model_id)
        if hasattr(self, "lbl_det_model"):
            self.lbl_det_model.setText(det.get("model", model_id))
        if hasattr(self, "lbl_det_latency"):
            self.lbl_det_latency.setText(det.get("typical_latency", "-"))
        if hasattr(self, "lbl_det_cost_in"):
            self.lbl_det_cost_in.setText(det.get("cost_input", "-"))
        if hasattr(self, "lbl_det_cost_out"):
            self.lbl_det_cost_out.setText(det.get("cost_output", "-"))
        if hasattr(self, "lbl_det_context"):
            self.lbl_det_context.setText(det.get("context", "-"))
        if hasattr(self, "lbl_det_usage"):
            self.lbl_det_usage.setText(det.get("recommended_for", "-"))

        route_names = {
            "latency": tr("route_opt_latency"),
            "price": tr("route_opt_price"),
            "throughput": tr("route_opt_throughput"),
            "default": tr("route_opt_default"),
        }
        cur_r = getattr(config.formatting, "routing_strategy", "latency")
        if hasattr(self, "lbl_det_route"):
            self.lbl_det_route.setText(route_names.get(cur_r, cur_r))

        zdr_on = getattr(config.formatting, "zero_data_retention", True)
        if hasattr(self, "lbl_det_zdr"):
            if zdr_on:
                self.lbl_det_zdr.setText(tr("zdr_active"))
                self.lbl_det_zdr.setStyleSheet("font-size: 11px; color: #10b981;")
            else:
                self.lbl_det_zdr.setText(tr("zdr_inactive"))
                self.lbl_det_zdr.setStyleSheet("font-size: 11px; color: #787884;")

    def _on_u_routing_changed(self, index: int):
        strategy = self.combo_u_routing.itemData(index) or "latency"
        config.formatting.routing_strategy = strategy
        config.save()
        self._update_model_details_ui()

    def _on_u_zdr_toggled(self, checked: bool):
        config.formatting.zero_data_retention = checked
        config.save()
        self._update_model_details_ui()

    def _on_u_fallbacks_toggled(self, checked: bool):
        config.formatting.allow_fallbacks = checked
        config.save()

    def _toggle_model_details(self):
        is_vis = not self.model_details_frame.isHidden()
        self.model_details_frame.setVisible(not is_vis)
        if hasattr(self, "btn_toggle_model_details"):
            self.btn_toggle_model_details.setText(tr("btn_hide_custom_catalog") if not is_vis else tr("btn_toggle_custom_catalog"))

    def _toggle_custom_catalog(self):
        is_vis = not self.custom_catalog_frame.isHidden()
        self.custom_catalog_frame.setVisible(not is_vis)
        if hasattr(self, "btn_toggle_custom_catalog"):
            self.btn_toggle_custom_catalog.setText(tr("btn_hide_custom_catalog") if not is_vis else tr("btn_toggle_custom_catalog"))

    def _toggle_advanced_formatting(self):
        is_vis = not self.adv_formatting_frame.isHidden()
        self.adv_formatting_frame.setVisible(not is_vis)
        if hasattr(self, "btn_toggle_adv_formatting"):
            self.btn_toggle_adv_formatting.setText(tr("btn_hide_adv_formatting") if not is_vis else tr("btn_toggle_adv_formatting"))

    def _expand_all_settings(self):
        for card in getattr(self, "all_settings_cards", []):
            card.set_expanded(True)

    def _collapse_all_settings(self):
        for card in getattr(self, "all_settings_cards", []):
            card.set_expanded(False)

    def _on_settings_search_changed(self, query: str):
        query = query.strip().lower()
        cards = getattr(self, "all_settings_cards", [])
        if not query:
            for card in cards:
                card.setVisible(True)
                card.set_expanded(False)
            if hasattr(self, "card_audio"):
                self.card_audio.set_expanded(True)
            return

        for card in cards:
            match = False
            # Check title, description, summary
            if query in card.lbl_title.text().lower():
                match = True
            if card.lbl_desc and query in card.lbl_desc.text().lower():
                match = True
            if query in card.lbl_summary.text().lower():
                match = True

            # Check all child labels, checkboxes, buttons, lineedits inside card
            if not match:
                for child in card.body_widget.findChildren((QLabel, QCheckBox, QPushButton, QLineEdit, QComboBox)):
                    if isinstance(child, (QLabel, QCheckBox, QPushButton)) and query in child.text().lower():
                        match = True
                        break
                    elif isinstance(child, QLineEdit) and query in child.placeholderText().lower():
                        match = True
                        break

            card.setVisible(match)
            if match:
                card.set_expanded(True)

    def _update_settings_summaries(self):
        # Card 1: Allgemein
        if hasattr(self, "card_gen"):
            gen_parts = []
            if autostart_manager.is_autostart_enabled():
                gen_parts.append(tr("summary_autostart"))
            if getattr(config.system, "sound_cues", True):
                theme_key = getattr(config.system, "sound_theme", "velodictum_silk")
                theme_name = SOUND_THEMES.get(theme_key, {}).get("name", theme_key)
                vol_pct = int(getattr(config.system, "sound_volume", 0.75) * 100)
                gen_parts.append(f"{theme_name} ({vol_pct}%)")
            else:
                gen_parts.append(tr("summary_muted"))
            self.card_gen.set_summary(" · ".join(gen_parts))

        # Card 2: Audio & Mikrofon
        if hasattr(self, "card_audio"):
            aud_parts = []
            gain = getattr(config.audio, "input_gain", 1.0)
            aud_parts.append(f"{tr('summary_gain')}: {gain:.1f}x")
            if getattr(config.audio, "auto_ducking", True):
                duck_vol = getattr(config.audio, "ducking_volume_percent", 25)
                aud_parts.append(f"{tr('summary_ducking')}: {duck_vol}%")
            if getattr(config.mobile_bridge, "enabled", False):
                aud_parts.append(tr("summary_lan_mic_active"))
            self.card_audio.set_summary(" · ".join(aud_parts))

        # Card 3: Spracherkennung (STT)
        if hasattr(self, "card_stt"):
            stt_p = getattr(config.whisper, "provider", "local")
            if stt_p == "local":
                prof = getattr(config.whisper, "profile", "de_max")
                stt_summary = f"{tr('summary_local')} ({self.short_gpu_name}) · {prof.upper()}"
            elif stt_p in ("universal", "openrouter", "custom"):
                m = getattr(config.whisper, "universal_model", "openai/whisper-large-v3")
                stt_summary = f"Universal API ({m})"
            elif stt_p in ("grok", "groq"):
                stt_summary = "Grok AI Cloud (Whisper-large-v3)"
            elif stt_p == "openai":
                stt_summary = "OpenAI Cloud (Whisper-1)"
            else:
                stt_summary = stt_p
            self.card_stt.set_summary(stt_summary)

        # Card 4: Formatierung & Text-Intelligenz
        if hasattr(self, "card_fmt"):
            eng = getattr(config.formatting, "engine", "rules")
            if eng == "rules":
                llm_summary = tr("summary_local_rules")
            elif eng == "universal":
                m = getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
                llm_summary = f"Universal API · {m}"
            elif eng == "ollama":
                m = getattr(config.formatting, "ollama_model", "qwen2.5:7b")
                llm_summary = f"Ollama · {m}"
            elif eng == "openai":
                m = getattr(config.formatting, "openai_model", "gpt-4o-mini")
                llm_summary = f"OpenAI · {m}"
            elif eng == "gemini":
                m = getattr(config.formatting, "gemini_model", "gemini-2.5-flash")
                llm_summary = f"Gemini · {m}"
            elif eng == "groq":
                m = getattr(config.formatting, "groq_model", "llama-3.3-70b-versatile")
                llm_summary = f"Groq · {m}"
            else:
                llm_summary = eng
            self.card_fmt.set_summary(llm_summary)

        # Card 5: Shortcuts & Tasten
        if hasattr(self, "card_hk"):
            hk_key = config.hotkey.key.upper()
            ve_key = getattr(config.hotkey, "edit_key", "ctrl+alt+space").upper()
            hk_mode = "Push-to-Talk" if getattr(config.hotkey, "mode", "push_to_talk") == "push_to_talk" else "Toggle"
            self.card_hk.set_summary(f"{tr('summary_dictation')}: {hk_key} ({hk_mode}) · {tr('summary_transform')}: {ve_key}")

        # Card 6: Darstellung & HUD
        if hasattr(self, "card_hud"):
            if getattr(config.hud, "enabled", True):
                pos = "Cursor" if getattr(config.hud, "position_mode", "bottom_center") == "follow_cursor" else "Bottom"
                op = getattr(config.hud, "opacity_percent", 78)
                self.card_hud.set_summary(f"{tr('summary_active')} · {pos} · {op}% {tr('summary_opacity')}")
            else:
                self.card_hud.set_summary(tr("summary_disabled"))

        # Card 7: Erweitert & Datenschutz
        if hasattr(self, "card_adv"):
            adv_parts = []
            if getattr(config.system, "offline_privacy_mode", False):
                adv_parts.append(tr("summary_offline_shield"))
            else:
                adv_parts.append(tr("summary_standard_security"))
            self.card_adv.set_summary(" · ".join(adv_parts))

    def _on_u_model_changed(self, text: str):
        raw = text.split(" — ")[0].strip() if " — " in text else text.strip()
        if raw and not raw.startswith("---"):
            config.formatting.model = raw
            config.formatting.openrouter_model = raw
            config.save()
            self.ai_formatter.model = raw
            self.ai_formatter.openrouter_model = raw
            self._sync_priority_cards_ui(raw)
            self._update_model_details_ui(raw)

    def _on_models_fetched_result(self, raw_models: list, error_msg: str):
        self.btn_u_fetch_models.setText(tr("btn_u_fetch_models"))
        self.btn_u_fetch_models.setEnabled(True)
        if raw_models:
            categorized = categorize_models(raw_models)
            self.combo_u_model.blockSignals(True)
            self.combo_u_model.clear()
            
            cat_labels = [
                ("recommended", tr("cat_recommended")),
                ("value", tr("cat_value")),
                ("fast", tr("cat_fast")),
                ("quality", tr("cat_quality")),
                ("other", tr("cat_other")),
            ]
            for cat_key, cat_title in cat_labels:
                m_list = categorized.get(cat_key, [])
                if m_list:
                    self.combo_u_model.addItem(f"--- {cat_title} ---", "")
                    for m in m_list:
                        m_id = m.get("id", "")
                        m_name = m.get("name", m_id)
                        self.combo_u_model.addItem(f"{m_id} — {m_name}", m_id)

            cur_m = getattr(config.formatting, "model", "")
            matched = -1
            for idx in range(self.combo_u_model.count()):
                if self.combo_u_model.itemData(idx) == cur_m:
                    matched = idx
                    break
            if matched >= 0:
                self.combo_u_model.setCurrentIndex(matched)
            else:
                self.combo_u_model.setEditText(cur_m)

            self.combo_u_model.blockSignals(False)
            self.lbl_u_test_status.setText(tr("models_loaded_count", count=len(raw_models)))
            self.lbl_u_test_status.setStyleSheet("color: #10b981;")
        else:
            msg = error_msg if error_msg else "Keine Modelle gefunden oder Auth-Fehler"
            self.lbl_u_test_status.setText(msg)
            self.lbl_u_test_status.setStyleSheet("color: #ef4444;")

    def _on_connection_test_result(self, provider_name: str, res: dict):
        if provider_name == "universal":
            self.btn_u_test.setText(tr("btn_test_api"))
            self.btn_u_test.setEnabled(True)
            lbl = self.lbl_u_test_status
        elif provider_name == "ollama":
            self.btn_ol_test.setText(tr("btn_test_ollama"))
            self.btn_ol_test.setEnabled(True)
            lbl = self.lbl_ol_test_status
        elif provider_name == "openai":
            self.btn_oai_test.setText(tr("btn_test_api"))
            self.btn_oai_test.setEnabled(True)
            lbl = self.lbl_oai_test_status
        elif provider_name == "gemini":
            self.btn_gem_test.setText(tr("btn_test_api"))
            self.btn_gem_test.setEnabled(True)
            lbl = self.lbl_gem_test_status
        elif provider_name == "groq":
            self.btn_grq_test.setText(tr("btn_test_api"))
            self.btn_grq_test.setEnabled(True)
            lbl = self.lbl_grq_test_status
        else:
            return

        if res.get("success"):
            lbl.setText(res.get("message", tr("conn_success")))
            lbl.setStyleSheet("color: #10b981;")
        else:
            lbl.setText(res.get("message", tr("conn_failed")))
            lbl.setStyleSheet("color: #ef4444;")

    def _fetch_universal_models(self):
        self.btn_u_fetch_models.setText(tr("btn_loading"))
        self.btn_u_fetch_models.setEnabled(False)
        self.lbl_u_test_status.setText(tr("loading_catalog"))
        self.lbl_u_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                endpoint = getattr(config.formatting, "api_endpoint", "https://openrouter.ai/api/v1")
                key = getattr(config.formatting, "api_key", None)
                provider = UniversalApiProvider(endpoint=endpoint, api_key=key)
                raw_models, err = provider.fetch_models_detailed()
                self.models_fetched_signal.emit(raw_models, err or "")
            except Exception as e:
                self.models_fetched_signal.emit([], str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _test_universal_connection(self):
        self.btn_u_test.setText(tr("btn_testing"))
        self.btn_u_test.setEnabled(False)
        self.lbl_u_test_status.setText(tr("conn_testing"))
        self.lbl_u_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                endpoint = getattr(config.formatting, "api_endpoint", "https://openrouter.ai/api/v1")
                key = getattr(config.formatting, "api_key", None)
                model = getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
                provider = UniversalApiProvider(endpoint=endpoint, api_key=key, model=model)
                res = provider.test_connection()
                self.connection_test_signal.emit("universal", res)
            except Exception as e:
                self.connection_test_signal.emit("universal", {"success": False, "message": f"{tr('hud_error')}: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ol_url_changed(self, text: str):
        config.formatting.ollama_url = text.strip()
        config.save()
        self.ai_formatter.ollama_url = config.formatting.ollama_url

    _on_ollama_url_changed = _on_ol_url_changed

    def _on_ol_model_changed(self, text: str):
        config.formatting.ollama_model = text.strip()
        config.save()
        self.ai_formatter.ollama_model = config.formatting.ollama_model
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    _on_ollama_model_changed = _on_ol_model_changed

    def _test_ollama_connection(self):
        self.btn_ol_test.setText(tr("btn_testing"))
        self.btn_ol_test.setEnabled(False)
        self.lbl_ol_test_status.setText(tr("conn_testing"))
        self.lbl_ol_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                url = getattr(config.formatting, "ollama_url", "http://127.0.0.1:11434")
                model = getattr(config.formatting, "ollama_model", "qwen2.5:7b")
                provider = OllamaProvider(ollama_url=url, model=model)
                res = provider.test_connection()
                self.connection_test_signal.emit("ollama", res)
            except Exception as e:
                self.connection_test_signal.emit("ollama", {"success": False, "message": f"{tr('hud_error')}: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_oai_key_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.set_api_key(cleaned, "openai")
        config.save()

    def _on_oai_model_changed(self, text: str):
        config.formatting.openai_model = text.strip()
        config.save()
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    def _test_openai_connection(self):
        self.btn_oai_test.setText(tr("btn_testing"))
        self.btn_oai_test.setEnabled(False)
        self.lbl_oai_test_status.setText(tr("conn_testing"))
        self.lbl_oai_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                key = config.formatting.get_api_key("openai") or config.formatting.get_api_key("universal")
                model = getattr(config.formatting, "openai_model", "gpt-4o-mini")
                provider = OpenAIProvider(api_key=key, model=model)
                res = provider.test_connection()
                self.connection_test_signal.emit("openai", res)
            except Exception as e:
                self.connection_test_signal.emit("openai", {"success": False, "message": f"{tr('hud_error')}: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_gem_key_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.set_api_key(cleaned, "gemini")
        config.save()

    def _on_gem_model_changed(self, text: str):
        config.formatting.gemini_model = text.strip()
        config.save()
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    def _test_gemini_connection(self):
        self.btn_gem_test.setText(tr("btn_testing"))
        self.btn_gem_test.setEnabled(False)
        self.lbl_gem_test_status.setText(tr("conn_testing"))
        self.lbl_gem_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                key = config.formatting.get_api_key("gemini") or config.formatting.get_api_key("universal")
                model = getattr(config.formatting, "gemini_model", "gemini-2.5-flash")
                provider = GeminiProvider(api_key=key, model=model)
                res = provider.test_connection()
                self.connection_test_signal.emit("gemini", res)
            except Exception as e:
                self.connection_test_signal.emit("gemini", {"success": False, "message": f"{tr('hud_error')}: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_grq_key_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.set_api_key(cleaned, "groq")
        config.save()

    def _on_grq_model_changed(self, text: str):
        config.formatting.groq_model = text.strip()
        config.save()
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    def _test_groq_connection(self):
        self.btn_grq_test.setText(tr("btn_testing"))
        self.btn_grq_test.setEnabled(False)
        self.lbl_grq_test_status.setText(tr("conn_testing"))
        self.lbl_grq_test_status.setStyleSheet("color: #38bdf8;")

        def _worker():
            try:
                key = config.formatting.get_api_key("groq") or config.formatting.get_api_key("universal")
                model = getattr(config.formatting, "groq_model", "llama-3.3-70b-versatile")
                provider = GroqProvider(api_key=key, model=model)
                res = provider.test_connection()
                self.connection_test_signal.emit("groq", res)
            except Exception as e:
                self.connection_test_signal.emit("groq", {"success": False, "message": f"{tr('hud_error')}: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_universal_stt_url_changed(self, text: str):
        config.whisper.universal_endpoint = text.strip()
        config.save()
        if hasattr(self, "card_stt"):
            self._update_settings_summaries()

    def _on_universal_stt_key_changed(self, text: str):
        cleaned = text.strip()
        config.whisper.set_api_key(cleaned, "universal")
        config.save()

    def _on_universal_stt_model_changed(self, text: str):
        config.whisper.universal_model = text.strip()
        config.save()
        if hasattr(self, "card_stt"):
            self._update_settings_summaries()

    def _on_groq_key_changed(self, text: str):
        cleaned = text.strip()
        config.whisper.set_api_key(cleaned, "groq")
        config.save()

    def _on_openai_key_changed(self, text: str):
        cleaned = text.strip()
        config.whisper.set_api_key(cleaned, "openai")
        config.save()

    def _on_privacy_shield_toggled(self, val: bool):
        config.system.offline_privacy_mode = val
        config.save()
        self.privacy_badge.setVisible(val)
        if hasattr(self, "card_sys"):
            self._update_settings_summaries()

    def _on_hud_fluid_toggled(self, val: bool):
        config.hud.fluid_animations = val
        config.save()

    def _on_auto_app_profiles_toggled(self, val: bool):
        config.formatting.auto_app_profiles = val
        config.save()

    def _on_apply_snippets_toggled(self, val: bool):
        config.injection.apply_snippets = val
        config.save()

    def _on_send_it_toggled(self, val: bool):
        config.formatting.send_it_enabled = val
        config.injection.send_it_enabled = val
        config.save()

    def _on_context_intelligence_toggled(self, val: bool):
        config.formatting.context_intelligence = val
        config.save()

    def _on_workspace_seeding_toggled(self, val: bool):
        config.formatting.workspace_seeding = val
        config.save()

    def _on_spoken_markdown_toggled(self, val: bool):
        config.formatting.spoken_markdown = val
        config.save()

    def _on_squelcher_toggled(self, val: bool):
        config.whisper.hallucination_filter = val
        config.save()

    def _on_open_scratchpad_clicked(self):
        signals.scratchpad_toggle_requested.emit()

    def _on_mobile_bridge_toggled(self, val: bool):
        config.mobile_bridge.enabled = val
        config.save()
        signals.mobile_bridge_toggled.emit(val)
        if hasattr(self, "lbl_mobile_status"):
            self.lbl_mobile_status.setText("Server aktiv · Adresse im Smartphone-Browser öffnen" if val else "Server inaktiv")
            self.lbl_mobile_status.setStyleSheet("font-size: 11px; color: #10b981;" if val else "font-size: 11px; color: #71717a;")
        if hasattr(self, "card_mob"):
            self._update_settings_summaries()

    def _on_copy_mobile_url(self):
        url = getattr(self, "lbl_mobile_url", None)
        if url:
            pyperclip.copy(url.text())
            if hasattr(self, "btn_copy_mob"):
                self.btn_copy_mob.setText("Kopiert")
                QTimer.singleShot(1500, lambda: self.btn_copy_mob.setText("Kopieren"))

    def _on_open_mobile_url(self):
        url = getattr(self, "lbl_mobile_url", None)
        if url:
            QDesktopServices.openUrl(QUrl(url.text()))

    def _on_rotate_mobile_token(self):
        import secrets
        new_token = secrets.token_hex(8)
        config.mobile_bridge.auth_token = new_token
        config.save()

        try:
            from mobile_bridge_server import MobileBridgeHandler
            MobileBridgeHandler.auth_token = new_token
        except Exception:
            pass

        proto = "https" if getattr(config.mobile_bridge, "use_https", True) else "http"
        url_str = f"{proto}://{self.local_lan_ip}:8765/?token={new_token}"
        if hasattr(self, "lbl_mobile_url"):
            self.lbl_mobile_url.setText(url_str)
        if hasattr(self, "btn_rotate_mob_token"):
            self.btn_rotate_mob_token.setText("Token erneuert!")
            QTimer.singleShot(1500, lambda: self.btn_rotate_mob_token.setText("Neues Token"))

    def _on_tone_changed(self, idx: int):
        if hasattr(self, "tone_keys") and idx < len(self.tone_keys):
            chosen = self.tone_keys[idx]
            config.formatting.tone = chosen
            config.save()
            self.ai_formatter.tone = chosen
            for tk, card in self.tone_cards.items():
                card.set_selected(tk == chosen)
            if chosen == "latex":
                if hasattr(self, "_on_priority_card_clicked"):
                    self._on_priority_card_clicked("quality")

    def _on_custom_prompt_changed(self, text: str):
        cleaned = text.strip()
        config.formatting.custom_instructions = cleaned
        config.save()
        self.ai_formatter.custom_instructions = cleaned

    def _on_mic_combo_changed(self, idx: int):
        if idx < len(self.mic_device_ids):
            dev_id = self.mic_device_ids[idx]
            config.audio.input_device = dev_id
            config.save()
            self.audio_recorder.set_device(dev_id)

    def _on_filler_toggled(self, val: bool):
        config.injection.clean_filler_words = val
        config.save()

    def _update_disk_space_label(self):
        if not hasattr(self, "lbl_disk_space"):
            return
        from model_manager import model_manager
        usage = model_manager.get_disk_space()
        self.lbl_disk_space.setText(tr("disk_space_info", free=usage['free_gb'], total=usage['total_gb'], pct=usage['free_percent']))

    def _refresh_model_downloader_list(self):
        if not hasattr(self, "model_list_layout"):
            return
        while self.model_list_layout.count() > 0:
            child = self.model_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        from model_manager import model_manager
        status_list = model_manager.get_models_status()
        active_model_id = getattr(config.whisper, "model_size", "large-v3-turbo")

        for m in status_list:
            is_active = (m["id"] == active_model_id and getattr(config.whisper, "provider", "local") == "local")
            row_w = QFrame()
            if is_active:
                row_w.setStyleSheet("background-color: #172033; border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 6px;")
            else:
                row_w.setStyleSheet("background-color: #1a1a22; border: 1px solid #282834; border-radius: 6px;")
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(10, 6, 10, 6)
            r_lay.setSpacing(10)

            # Name & info
            lbl_name = QLabel(f"<b>{m['name']}</b> <span style='color: #8e8e98;'>({m['size_mb']} MB · {m['vram_gb']} GB VRAM)</span>")
            lbl_name.setStyleSheet("color: #f4f4f5; font-size: 12px;")
            r_lay.addWidget(lbl_name, stretch=1)

            # Status Badge
            if is_active:
                lbl_st = QLabel(tr("status_active"))
                lbl_st.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600; background: #0c2d48; border: 1px solid rgba(56, 189, 248, 0.4); padding: 3px 8px; border-radius: 4px;")
            elif m["is_downloaded"]:
                lbl_st = QLabel(tr("status_downloaded"))
                lbl_st.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 600; background: #064e3b; padding: 3px 8px; border-radius: 4px;")
            else:
                lbl_st = QLabel(tr("status_not_downloaded"))
                lbl_st.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: 500; background: #27272a; padding: 3px 8px; border-radius: 4px;")
            r_lay.addWidget(lbl_st)

            # Action Buttons
            if m["is_downloaded"]:
                if not is_active:
                    btn_act = QPushButton(tr("btn_activate"))
                    btn_act.setObjectName("btn_primary")
                    btn_act.setStyleSheet("background-color: #0284c7; color: #ffffff; font-weight: 600; font-size: 11px; padding: 2px 10px; border-radius: 4px;")
                    btn_act.setFixedHeight(26)
                    btn_act.clicked.connect(lambda _, mid=m["id"]: self._on_activate_whisper_model(mid))
                    r_lay.addWidget(btn_act)
                else:
                    btn_act = QPushButton(tr("btn_active"))
                    btn_act.setEnabled(False)
                    btn_act.setStyleSheet("background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; font-weight: 600; font-size: 11px; padding: 2px 10px; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 4px;")
                    btn_act.setFixedHeight(26)
                    r_lay.addWidget(btn_act)

                btn_del = QPushButton(tr("btn_delete"))
                btn_del.setObjectName("btn_secondary")
                btn_del.setStyleSheet("color: #f87171; border: 1px solid #7f1d1d; font-size: 11px; padding: 2px 8px; border-radius: 4px;")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, mid=m["id"]: self._on_delete_model(mid))
                r_lay.addWidget(btn_del)
            else:
                btn_dl = QPushButton(tr("btn_download"))
                btn_dl.setObjectName("btn_secondary")
                btn_dl.setStyleSheet("font-size: 11px; padding: 2px 10px; border-radius: 4px;")
                btn_dl.setFixedHeight(26)
                btn_dl.clicked.connect(lambda _, mid=m["id"]: self._on_download_model(mid))
                r_lay.addWidget(btn_dl)

            self.model_list_layout.addWidget(row_w)

    def _on_change_models_dir(self):
        from PyQt6.QtWidgets import QFileDialog
        from model_manager import model_manager
        current = model_manager.get_models_dir()
        selected = QFileDialog.getExistingDirectory(self, tr("models_dir_dialog_title"), current)
        if selected:
            ok = model_manager.set_models_dir(selected)
            if ok:
                self.input_storage_path.setText(model_manager.get_models_dir())
                self._update_disk_space_label()
                self._refresh_model_downloader_list()

    def _on_download_model(self, model_id: str):
        from model_manager import model_manager
        self.btn_change_storage.setEnabled(False)
        self.lbl_disk_space.setText(tr("downloading_model_info", model_id=model_id))
        self.lbl_disk_space.setStyleSheet("font-size: 11px; color: #eab308; font-weight: 600;")

        def _on_finished(mid, success, msg):
            self.downloader_finished_signal.emit(mid, success, msg)

        model_manager.download_model_async(
            model_id=model_id,
            on_finished=_on_finished,
        )

    def _on_delete_model(self, model_id: str):
        from model_manager import model_manager
        model_manager.delete_model(model_id)
        self._update_disk_space_label()
        self._refresh_model_downloader_list()

    def _on_downloader_finished(self, model_id: str, success: bool, msg: str):
        self.btn_change_storage.setEnabled(True)
        self._update_disk_space_label()
        self._refresh_model_downloader_list()

    def _on_audio_device_switched_event(self, device_name: str):
        if hasattr(self, "combo_mic") and hasattr(self, "mic_device_ids"):
            target_id = getattr(config.audio, "input_device", None)
            for i, dev_id in enumerate(self.mic_device_ids):
                if dev_id == target_id:
                    self.combo_mic.blockSignals(True)
                    self.combo_mic.setCurrentIndex(i)
                    self.combo_mic.blockSignals(False)
                    break

    def _on_auto_ducking_toggled(self, checked: bool):
        config.audio.auto_ducking = checked
        config.save()

    def _on_ducking_level_changed(self, value: int):
        config.audio.ducking_volume_percent = value
        config.save()
        if hasattr(self, "lbl_ducking_level_val"):
            label_desc = tr("duck_fast_mute") if value <= 15 else (tr("vol_very_quiet") if value <= 25 else tr("duck_moderate"))
            self.lbl_ducking_level_val.setText(f"{value}% ({label_desc})")

    def _on_sound_cues_toggled(self, val: bool):
        config.system.sound_cues = val
        config.save()
        if hasattr(self, "card_sound"):
            self._update_settings_summaries()

    def _on_sound_theme_changed(self, idx: int):
        if hasattr(self, "sound_theme_keys") and idx < len(self.sound_theme_keys):
            chosen = self.sound_theme_keys[idx]
            config.system.sound_theme = chosen
            config.save()
            if hasattr(self, "card_sound"):
                self._update_settings_summaries()

    def _on_sound_volume_changed(self, idx: int):
        if hasattr(self, "vol_values") and idx < len(self.vol_values):
            chosen_vol = self.vol_values[idx]
            config.system.sound_volume = chosen_vol
            config.save()
            if hasattr(self, "card_sound"):
                self._update_settings_summaries()

    def _on_preview_sound_clicked(self):
        theme = getattr(config.system, "sound_theme", "velodictum_silk")
        vol = getattr(config.system, "sound_volume", 0.75)
        preview_cue(theme=theme, volume=vol)

    def _on_gain_slider_changed(self, val: int):
        gain = val / 100.0
        config.audio.input_gain = gain
        config.save()
        db_val = 20.0 * math.log10(gain) if gain > 0 else 0.0
        db_str = f"+{db_val:.1f}" if db_val > 0 else f"{db_val:.1f}"
        if hasattr(self, "lbl_gain_value"):
            self.lbl_gain_value.setText(f"{val}% ({gain:.1f}x · {db_str} dB)")
        if hasattr(self, "card_sound"):
            self._update_settings_summaries()

    def _toggle_mic_test(self):
        if not hasattr(self.audio_recorder, "is_testing"):
            return
        if self.audio_recorder.is_testing:
            self._stop_mic_test()
        else:
            self._start_mic_test()

    def _start_mic_test(self):
        if hasattr(self.audio_recorder, "start_test"):
            ok = self.audio_recorder.start_test()
            if ok:
                if hasattr(self, "btn_mic_test"):
                    self.btn_mic_test.setText(tr("btn_mic_test_stop"))
                    self.btn_mic_test.setStyleSheet(
                        "background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 11px; font-weight: 600; "
                        "padding: 5px 14px; border: 1px solid rgba(56, 189, 248, 0.5); border-radius: 4px;"
                    )
                if hasattr(self, "lbl_mic_test_status"):
                    self.lbl_mic_test_status.setText(tr("lbl_mic_active_live"))
                    self.lbl_mic_test_status.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 500;")

    def _stop_mic_test(self):
        if hasattr(self.audio_recorder, "stop_test"):
            self.audio_recorder.stop_test()
        if hasattr(self, "btn_mic_test"):
            self.btn_mic_test.setText(tr("btn_mic_test_start"))
            self.btn_mic_test.setStyleSheet("font-size: 11px; font-weight: 600; padding: 5px 14px;")
        if hasattr(self, "lbl_mic_test_status"):
            self.lbl_mic_test_status.setText(tr("lbl_mic_inactive"))
            self.lbl_mic_test_status.setStyleSheet("font-size: 11px; color: #71717a;")
        if hasattr(self, "calib_meter"):
            self.calib_meter.update_level(0.0)

    def _on_hud_enable_toggled(self, val: bool):
        config.hud.enabled = val
        config.save()
        if hasattr(self, "card_sys"):
            self._update_settings_summaries()

    def _on_hud_pos_changed(self, idx: int):
        mode = "follow_cursor" if idx == 1 else "bottom_center"
        config.hud.position_mode = mode
        config.save()
        if hasattr(self, "hud_pos_mem_widget"):
            self.hud_pos_mem_widget.setVisible(idx == 0)

    def _on_hud_minimal_toggled(self, val: bool):
        config.hud.minimal_mode = val
        config.save()

    def _on_hud_remember_pos_toggled(self, val: bool):
        config.hud.remember_position = val
        config.save()

    def _get_bounce_label(self, val: int) -> str:
        if val <= 15:
            return tr("bounce_crisp", val=val)
        elif val <= 70:
            return tr("bounce_balanced", val=val)
        else:
            return tr("bounce_elastic", val=val)

    def _get_scale_label(self, val: int) -> str:
        if val < 95:
            return tr("scale_compact", val=val)
        elif val <= 105:
            return tr("scale_standard", val=val)
        else:
            return tr("scale_large", val=val)

    def _on_hud_opacity_changed(self, val: int):
        config.hud.opacity_percent = val
        config.save()
        if hasattr(self, "lbl_hud_opacity_val"):
            self.lbl_hud_opacity_val.setText(f"{val}%")

    def _on_hud_bounce_changed(self, val: int):
        config.hud.bounce_intensity = val
        config.save()
        if hasattr(self, "lbl_hud_bounce_val"):
            self.lbl_hud_bounce_val.setText(self._get_bounce_label(val))

    def _on_hud_scale_changed(self, val: int):
        config.hud.scale_percent = val
        config.save()
        if hasattr(self, "lbl_hud_scale_val"):
            self.lbl_hud_scale_val.setText(self._get_scale_label(val))

    def _on_hud_reset_pos_clicked(self):
        config.hud.custom_x = None
        config.hud.custom_y = None
        config.hud.opacity_percent = 78
        config.hud.bounce_intensity = 50
        config.hud.scale_percent = 100
        config.save()
        if hasattr(self, "slider_hud_opacity"):
            self.slider_hud_opacity.setValue(78)
            self.lbl_hud_opacity_val.setText("78%")
        if hasattr(self, "slider_hud_bounce"):
            self.slider_hud_bounce.setValue(50)
            self.lbl_hud_bounce_val.setText(self._get_bounce_label(50))
        if hasattr(self, "slider_hud_scale"):
            self.slider_hud_scale.setValue(100)
            self.lbl_hud_scale_val.setText(self._get_scale_label(100))
        if hasattr(self, "btn_hud_reset_pos"):
            self.btn_hud_reset_pos.setText(tr("btn_hud_reset_done"))
            QTimer.singleShot(1500, lambda: self.btn_hud_reset_pos.setText(tr("btn_hud_reset_pos")) if hasattr(self, "btn_hud_reset_pos") else None)

    def _on_autostart_toggled(self, val: bool):
        config.system.autostart = val
        config.save()
        autostart_manager.set_autostart_enabled(val)
        if hasattr(self, "card_sys"):
            self._update_settings_summaries()

    def _on_minimized_toggled(self, val: bool):
        config.system.start_minimized = val
        config.save()

    def _update_telemetry(self):
        self._update_hw_badge_string()
        if hasattr(self, "lbl_hw_badge"):
            self.lbl_hw_badge.setText(self.hw_badge_text)

    # =========================================================================
    # Vocabulary, Snippets & History Helpers
    # =========================================================================

    def _refresh_vocab_list(self, filter_query: str = ""):
        while self.vocab_list_layout.count() > 1:
            child = self.vocab_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        words = vocab_manager.get_words_list()
        clean_filter = filter_query.strip().lower()

        for item in words:
            word = item.get("word", "")
            category = item.get("category", "Allgemein")
            if clean_filter and clean_filter not in word.lower() and clean_filter not in category.lower():
                continue

            card = QFrame()
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet(
                "QFrame { background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.035); "
                "border-radius: 5px; } "
                "QFrame:hover { background-color: rgba(255, 255, 255, 0.06); border-color: rgba(56, 189, 248, 0.25); }"
            )
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 7, 10, 7)
            c_layout.setSpacing(10)

            lbl_word = QLabel(word)
            lbl_word.setStyleSheet("font-size: 12px; font-weight: 500; color: #eeeeef;")

            lbl_cat = QLabel(category.upper())
            lbl_cat.setStyleSheet(
                "font-size: 9.5px; font-weight: 600; color: #94a3b8; background: rgba(255, 255, 255, 0.05); "
                "padding: 2px 7px; border-radius: 3px;"
            )

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(
                "QPushButton { background: transparent; border: none; "
                "border-radius: 3px; color: #4a4a56; font-size: 14px; font-weight: bold; padding: 0; } "
                "QPushButton:hover { background: rgba(239, 68, 68, 0.15); color: #ef4444; }"
            )
            btn_del.clicked.connect(lambda _, w=word: self._on_delete_vocab_word(w))

            c_layout.addWidget(lbl_word, stretch=1)
            c_layout.addWidget(lbl_cat)
            c_layout.addWidget(btn_del)
            
            # Click to edit
            card.mousePressEvent = lambda e, w=word, c=category: self._start_vocab_edit(w, c)
            self.vocab_list_layout.insertWidget(self.vocab_list_layout.count() - 1, card)

    def _start_vocab_edit(self, word: str, category: str):
        self._editing_vocab_orig = word
        self.input_new_word.setText(word)
        idx = self.combo_new_cat.findText(category)
        if idx >= 0:
            self.combo_new_cat.setCurrentIndex(idx)
        self.btn_vocab_add.setText(tr("btn_save_term"))
        self.btn_vocab_cancel.setVisible(True)
        self.input_new_word.setFocus()

    def _cancel_vocab_edit(self):
        self._editing_vocab_orig = None
        self.input_new_word.clear()
        self.btn_vocab_add.setText(tr("btn_add_term"))
        self.btn_vocab_cancel.setVisible(False)

    def _on_add_vocab_word(self):
        text = self.input_new_word.text().strip()
        cat = self.combo_new_cat.currentText()
        if text:
            orig = getattr(self, "_editing_vocab_orig", None)
            if orig:
                vocab_manager.remove_word(orig)
            if vocab_manager.add_word(text, category=cat):
                self._cancel_vocab_edit()
                self._refresh_vocab_list(self.vocab_search.text())

    def _on_delete_vocab_word(self, word: str):
        if vocab_manager.remove_word(word):
            if getattr(self, "_editing_vocab_orig", None) == word:
                self._cancel_vocab_edit()
            self._refresh_vocab_list(self.vocab_search.text())

    def _filter_vocab(self, query: str):
        self._refresh_vocab_list(query)

    def _refresh_snippets_list(self):
        while self.snip_list_layout.count() > 1:
            child = self.snip_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        snippets = snippet_manager.get_all_snippets()
        for item in snippets:
            trig = item.get("trigger", "")
            exp = item.get("expansion", "")
            card = QFrame()
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet(
                "QFrame { background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.035); "
                "border-radius: 5px; } "
                "QFrame:hover { background-color: rgba(255, 255, 255, 0.06); border-color: rgba(56, 189, 248, 0.25); }"
            )
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 7, 10, 7)
            c_layout.setSpacing(10)

            # Rigid column for trigger
            lbl_trig = QLabel(f'"{trig}"')
            lbl_trig.setFixedWidth(145)
            lbl_trig.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #38bdf8;")

            lbl_arr = QLabel("→")
            lbl_arr.setFixedWidth(16)
            lbl_arr.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")

            # Clean single-line representation of expansion
            clean_display = exp.replace("\r\n", " ↵ ").replace("\n", " ↵ ")
            lbl_exp = QLabel(clean_display)
            lbl_exp.setStyleSheet("font-size: 11.5px; color: #cbd5e1;")

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(
                "QPushButton { background: transparent; border: none; "
                "border-radius: 3px; color: #4a4a56; font-size: 14px; font-weight: bold; padding: 0; } "
                "QPushButton:hover { background: rgba(239, 68, 68, 0.15); color: #ef4444; }"
            )
            btn_del.clicked.connect(lambda _, t=trig: self._on_delete_snippet(t))

            c_layout.addWidget(lbl_trig)
            c_layout.addWidget(lbl_arr)
            c_layout.addWidget(lbl_exp, stretch=1)
            c_layout.addWidget(btn_del)

            # Click to edit
            card.mousePressEvent = lambda e, t=trig, x=exp: self._start_snippet_edit(t, x)
            self.snip_list_layout.insertWidget(self.snip_list_layout.count() - 1, card)

    def _start_snippet_edit(self, trigger: str, expansion: str):
        self._editing_snip_orig = trigger
        self.input_snip_trig.setText(trigger)
        self.input_snip_exp.setText(expansion)
        self.btn_snip_add.setText(tr("btn_save_snippet"))
        self.btn_snip_cancel.setVisible(True)
        self.input_snip_exp.setFocus()

    def _cancel_snippet_edit(self):
        self._editing_snip_orig = None
        self.input_snip_trig.clear()
        self.input_snip_exp.clear()
        self.btn_snip_add.setText(tr("btn_add_snippet"))
        self.btn_snip_cancel.setVisible(False)

    def _on_add_snippet(self):
        trig = self.input_snip_trig.text().strip()
        exp = self.input_snip_exp.text()
        if trig and exp:
            orig = getattr(self, "_editing_snip_orig", None)
            if orig and orig.lower() != trig.lower():
                snippet_manager.remove_snippet(orig)
            if snippet_manager.add_snippet(trig, exp):
                self._cancel_snippet_edit()
                self._refresh_snippets_list()

    def _on_delete_snippet(self, trigger: str):
        if snippet_manager.remove_snippet(trigger):
            if getattr(self, "_editing_snip_orig", None) == trigger:
                self._cancel_snippet_edit()
            self._refresh_snippets_list()

    def _refresh_app_rules_list(self):
        while self.app_list_layout.count() > 1:
            child = self.app_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        rules = app_profile_manager.get_all_rules()
        for r in rules:
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.035); "
                "border-radius: 5px; } "
                "QFrame:hover { background-color: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.08); }"
            )
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 6, 10, 6)
            c_layout.setSpacing(8)

            lbl_name = QLabel(r.get("name", ""))
            lbl_name.setStyleSheet("font-size: 12px; font-weight: 500; color: #eeeeef;")

            lbl_proc = QLabel(f"({r.get('process', '')})")
            lbl_proc.setStyleSheet("font-size: 10px; color: #555562;")

            lbl_mode = QLabel(f"{r.get('mode', '').upper()}")
            lbl_mode.setStyleSheet(
                "font-size: 9px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.06); "
                "padding: 1px 5px; border-radius: 3px;"
            )

            c_layout.addWidget(lbl_name)
            c_layout.addWidget(lbl_proc)
            c_layout.addStretch()
            c_layout.addWidget(lbl_mode)
            self.app_list_layout.insertWidget(self.app_list_layout.count() - 1, card)

    def _add_to_history(self, text: str, latency: float):
        if self.empty_state_widget.isVisible():
            self.empty_state_widget.setVisible(False)

        record = {
            "text": text,
            "latency": latency,
            "time": time.strftime("%H:%M:%S"),
            "mode": config.formatting.mode,
        }
        self.history_records.insert(0, record)
        if len(self.history_records) > 40:
            self.history_records.pop()

        self.lbl_hist_count.setText(tr("history_entries_count", count=len(self.history_records)))

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.035); "
            "border-radius: 6px; } "
            "QFrame:hover { background-color: rgba(255, 255, 255, 0.045); border-color: rgba(255, 255, 255, 0.07); }"
        )
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 10, 14, 10)
        c_layout.setSpacing(6)

        top_row = QHBoxLayout()
        time_lbl = QLabel(record["time"])
        time_lbl.setStyleSheet("color: #555562; font-size: 11px; font-weight: 400;")

        mode_lbl = QLabel(record["mode"].upper())
        mode_lbl.setStyleSheet(
            "font-size: 9px; font-weight: 600; color: #71717a; background: rgba(255, 255, 255, 0.04); "
            "padding: 1px 5px; border-radius: 3px;"
        )

        lat_lbl = QLabel(f"{latency:.2f}s")
        lat_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 400;")

        btn_copy = QPushButton(tr("copy"))
        btn_copy.setObjectName("btn_secondary")
        btn_copy.setStyleSheet("padding: 2px 6px; font-size: 10.5px; min-height: 14px;")
        btn_copy.clicked.connect(lambda checked, t=text: pyperclip.copy(t))

        top_row.addWidget(time_lbl)
        top_row.addWidget(mode_lbl)
        top_row.addStretch()
        top_row.addWidget(lat_lbl)
        top_row.addWidget(btn_copy)
        c_layout.addLayout(top_row)

        txt_lbl = QLabel(text)
        txt_lbl.setWordWrap(True)
        txt_lbl.setStyleSheet("color: #eeeeef; font-size: 12.5px; line-height: 140%;")
        c_layout.addWidget(txt_lbl)

        self.hist_list_layout.insertWidget(0, card)

    def _sync_mode_ui(self, mode: str):
        pass

    def _sync_dict_mode_ui(self, mode: str):
        active_mode = config.formatting.mode
        for mk, card in self.mode_cards.items():
            card.set_selected(mk == active_mode)

    def show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_and_activate()

    def hideEvent(self, event):
        self._stop_mic_test()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._stop_mic_test()
        event.ignore()
        self.hide()

    def close_app(self):
        self._stop_mic_test()
        QApplication.quit()
