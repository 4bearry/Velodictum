"""
Velodictum - Minimalist Studio Edition Dashboard (Polished)
High-end desktop interface built on neutral slate/zinc design system,
fully dynamic GPU detection, dedicated unclipped Preset Card widgets,
seamless surface blends (no harsh black boxes), and quiet typography.
"""
import math
import os
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient,
    QKeyEvent, QDesktopServices, QPixmap, QIcon, QPainterPath, QAction
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTabWidget, QComboBox, QCheckBox, QLineEdit,
    QApplication, QGridLayout, QScrollArea, QSizePolicy, QDialog, QStackedWidget,
    QSlider, QMenu, QFileDialog
)
import pyperclip

from config import config, PROFILES
from gui.assets import create_app_icon
from gui.signals import signals
from text_injector import safe_clipboard_copy, safe_clipboard_paste
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
    CURATED_MODELS_SPECS,
    get_tier_for_model,
    get_curated_models_catalog,
    get_model_details,
)
from gui.theme import (
    get_stylesheet,
    apply_window_backdrop,
    ThemeColors,
    ThemeTypography,
    ThemeMetrics,
    get_sunken_qss,
    get_keycap_qss,
    is_reduced_motion,
    apply_neomorphic_shadow,
)
from i18n import tr, set_current_language, get_current_language


# =========================================================================
# 1. Custom Interactive Preset Cards & Neomorphic Studio Widgets
# =========================================================================

def _create_brand_wave_pixmap(size: int = 28) -> QPixmap:
    """Renders the 5-bar indigo/violet soundwave brand mark matching the Dark Neomorphism 2.0 target design."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    w = float(size)
    h = float(size)
    cy = h / 2.0
    heights = [0.16, 0.45, 0.86, 0.35, 0.65, 0.16]
    bar_w = 2.6
    gap = 2.1
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    start_x = (w - total_w) / 2.0

    for idx, rel_h in enumerate(heights):
        bh = max(2.8, rel_h * h)
        bx = start_x + idx * (bar_w + gap)
        by = cy - bh / 2.0
        grad = QLinearGradient(bx, by, bx, by + bh)
        grad.setColorAt(0.0, QColor("#60a5fa"))
        grad.setColorAt(0.5, QColor("#6366f1"))
        grad.setColorAt(1.0, QColor("#8b5cf6"))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.3, 1.3)

    painter.end()
    return pix


def _create_sidebar_icon(kind: str, color_hex: str, size: int = 18) -> QIcon:
    """Renders crisp vector navigation icons (studio, dictations, profiles, settings) for the fixed left sidebar."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    col = QColor(color_hex)
    pen = QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    s = float(size)
    if kind == "studio":
        # Filled/outlined house icon matching target design
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.48)
        path.lineTo(s * 0.50, s * 0.16)
        path.lineTo(s * 0.85, s * 0.48)
        path.lineTo(s * 0.78, s * 0.48)
        path.lineTo(s * 0.78, s * 0.84)
        path.lineTo(s * 0.58, s * 0.84)
        path.lineTo(s * 0.58, s * 0.60)
        path.lineTo(s * 0.42, s * 0.60)
        path.lineTo(s * 0.42, s * 0.84)
        path.lineTo(s * 0.22, s * 0.84)
        path.lineTo(s * 0.22, s * 0.48)
        path.closeSubpath()
        if color_hex.lower() == "#ffffff":
            painter.setBrush(QBrush(col))
        painter.drawPath(path)
    elif kind == "dictations":
        # Rounded document sheet with horizontal lines
        doc_rect = QRectF(s * 0.22, s * 0.14, s * 0.56, s * 0.72)
        painter.drawRoundedRect(doc_rect, 2.5, 2.5)
        painter.drawLine(QPointF(s * 0.34, s * 0.36), QPointF(s * 0.66, s * 0.36))
        painter.drawLine(QPointF(s * 0.34, s * 0.52), QPointF(s * 0.66, s * 0.52))
        painter.drawLine(QPointF(s * 0.34, s * 0.68), QPointF(s * 0.54, s * 0.68))
    elif kind == "profiles":
        # User head & shoulders outline
        painter.drawEllipse(QPointF(s * 0.50, s * 0.33), s * 0.17, s * 0.17)
        arc_rect = QRectF(s * 0.20, s * 0.55, s * 0.60, s * 0.42)
        painter.drawArc(arc_rect, 0 * 16, 180 * 16)
        painter.drawLine(QPointF(s * 0.20, s * 0.76), QPointF(s * 0.80, s * 0.76))
    elif kind == "settings":
        # Crisp gear / cogwheel icon
        cx, cy = s * 0.50, s * 0.50
        painter.drawEllipse(QPointF(cx, cy), s * 0.15, s * 0.15)
        outer_r = s * 0.36
        inner_r = s * 0.27
        for i in range(8):
            ang = i * (math.pi / 4.0)
            x1 = cx + math.cos(ang) * inner_r
            y1 = cy + math.sin(ang) * inner_r
            x2 = cx + math.cos(ang) * outer_r
            y2 = cy + math.sin(ang) * outer_r
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

    painter.end()
    return QIcon(pix)


class NeomorphicRecordButton(QPushButton):
    """
    Dominant circular Dark Neomorphism 2.0 Primary Action Button ("Diktat starten").
    Features a deep concave outer socket ring with ambient halo, a tactile convex
    Coral/Orange (#ff6b47 -> #e04622) circular orb, and a crisp vector microphone glyph.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(136, 136)
        self.setFixedSize(176, 176)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("btn_hero_record_cta")
        self.current_state = "idle"  # "idle", "recording", "transcribing", "formatting", "error"
        self._hovered = False
        self._pressed = False
        self.setStyleSheet("QPushButton#btn_hero_record_cta { background: transparent; border: none; }")

    def set_dictation_state(self, state: str):
        self.current_state = state
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx, cy = w / 2.0, h / 2.0
        max_r = min(w, h) / 2.0

        # 0. Subtle ambient radial aura around the neomorphic dish
        aura_grad = QRadialGradient(QPointF(cx, cy), max_r)
        aura_grad.setColorAt(0.0, QColor(235, 94, 56, 26))
        aura_grad.setColorAt(0.72, QColor(30, 38, 58, 35))
        aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(aura_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - max_r, cy - max_r, max_r * 2.0, max_r * 2.0))

        # 1. Outer Recessed Neomorphic Socket Ring (Level 2 Sunken Dish)
        outer_r = max_r - 8.0
        socket_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2.0, outer_r * 2.0)

        socket_grad = QLinearGradient(socket_rect.topLeft(), socket_rect.bottomRight())
        socket_grad.setColorAt(0.0, QColor("#0a0c12"))
        socket_grad.setColorAt(0.5, QColor("#10141e"))
        socket_grad.setColorAt(1.0, QColor("#1b2130"))
        painter.setBrush(QBrush(socket_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 22), 1.3))
        painter.drawEllipse(socket_rect)

        # Deep inner concave groove inside the socket
        rim_r = outer_r - 12.0
        rim_rect = QRectF(cx - rim_r, cy - rim_r, rim_r * 2.0, rim_r * 2.0)
        groove_grad = QLinearGradient(rim_rect.topLeft(), rim_rect.bottomRight())
        groove_grad.setColorAt(0.0, QColor("#07090e"))
        groove_grad.setColorAt(1.0, QColor("#121621"))
        painter.setBrush(QBrush(groove_grad))
        painter.setPen(QPen(QColor(0, 0, 0, 190), 1.6))
        painter.drawEllipse(rim_rect)

        # 2. Keyboard Focus Ring (WCAG 2.2 AA visible focus indicator)
        if self.hasFocus():
            focus_pen = QPen(QColor(ThemeColors.BORDER_FOCUS), 2.5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(focus_pen)
            painter.drawEllipse(socket_rect.adjusted(1.5, 1.5, -1.5, -1.5))

        # 3. Inner Raised Coral/Orange Primary Action Orb
        btn_r = outer_r - 22.0
        if self._pressed:
            btn_r -= 2.0
        btn_rect = QRectF(cx - btn_r, cy - btn_r, btn_r * 2.0, btn_r * 2.0)

        # Warm ambient glow + drop shadow under the raised Coral orb
        glow_grad = QRadialGradient(QPointF(cx, cy + 4.0), btn_r + 14.0)
        glow_grad.setColorAt(0.0, QColor(240, 88, 50, 95))
        glow_grad.setColorAt(0.75, QColor(5, 7, 12, 185))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - btn_r - 12.0, cy - btn_r - 8.0, (btn_r + 12.0) * 2.0, (btn_r + 12.0) * 2.0))

        # Determine fill colors by state
        if not self.isEnabled():
            c_top, c_bot, border_col = QColor("#262b3d"), QColor("#1a1e2b"), QColor(255, 255, 255, 25)
        elif self.current_state == "recording":
            c_top, c_bot, border_col = QColor("#ff7857"), QColor("#d93f1c"), QColor("#ffad99")
        elif self.current_state in ("transcribing", "formatting"):
            c_top, c_bot, border_col = QColor("#6366f1"), QColor("#3d448a"), QColor("#a5b4fc")
        elif self._pressed:
            c_top, c_bot, border_col = QColor("#d14b27"), QColor("#b83d1c"), QColor(255, 255, 255, 55)
        elif self._hovered:
            c_top, c_bot, border_col = QColor("#ff7754"), QColor("#e34e29"), QColor(255, 200, 180, 120)
        else:
            c_top, c_bot, border_col = QColor("#ff6d48"), QColor("#df4926"), QColor(255, 185, 165, 95)

        orb_grad = QLinearGradient(btn_rect.topLeft(), btn_rect.bottomRight())
        orb_grad.setColorAt(0.0, c_top)
        orb_grad.setColorAt(1.0, c_bot)

        painter.setBrush(QBrush(orb_grad))
        painter.setPen(QPen(border_col, 1.5))
        painter.drawEllipse(btn_rect)

        # 4. Crisp Vector Microphone Icon in the Center (scaled cleanly to orb)
        icon_col = QColor("#f8fafc") if self.isEnabled() else QColor("#64748b")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(icon_col))

        scale = btn_r / 54.0
        cap_w = 15.0 * scale
        cap_h = 25.0 * scale
        cap_rect = QRectF(cx - cap_w / 2.0, cy - 18.0 * scale, cap_w, cap_h)
        painter.drawRoundedRect(cap_rect, cap_w / 2.0, cap_w / 2.0)

        # Mic cradle arc & stand
        pen = QPen(icon_col, max(2.4, 3.1 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc_w = 27.0 * scale
        arc_h = 25.0 * scale
        arc_rect = QRectF(cx - arc_w / 2.0, cy - 13.5 * scale, arc_w, arc_h)
        painter.drawArc(arc_rect, 180 * 16, 180 * 16)
        stem_top = cy + 11.5 * scale
        stem_bot = cy + 19.5 * scale
        painter.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bot))
        foot_half = 8.0 * scale
        painter.drawLine(QPointF(cx - foot_half, stem_bot), QPointF(cx + foot_half, stem_bot))

        painter.end()


class StaticDictationWaveformWidget(QWidget):
    """
    Muted Indigo/Violet waveform preview inside the 'Letztes Diktat' secondary panel,
    matching the Dark Neomorphism 2.0 reference layout with quiet dotted rests and two wave bursts.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.pattern = [
            0.06, 0.06, 0.06, 0.06, 0.06, 0.16, 0.34, 0.22,
            0.48, 0.78, 0.96, 0.65, 0.38, 0.72, 0.56, 0.30,
            0.18, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06,
            0.22, 0.44, 0.75, 0.92, 0.62, 0.35, 0.48, 0.86,
            0.98, 0.68, 0.52, 0.36, 0.22, 0.12, 0.06, 0.06,
            0.06, 0.06, 0.06, 0.06,
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cy = h / 2.0
        n = len(self.pattern)
        bar_w = 2.6
        gap = max(2.2, (w - n * bar_w) / max(1, n - 1))
        total_w = n * bar_w + (n - 1) * gap
        start_x = max(0.0, (w - total_w) / 2.0)

        for i, val in enumerate(self.pattern):
            bx = start_x + i * (bar_w + gap)
            if bx + bar_w > w:
                break
            if val <= 0.08:
                dot_r = 2.4
                by = cy - dot_r / 2.0
                painter.setBrush(QBrush(QColor("#5b63b8")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(bx, by, dot_r, dot_r))
            else:
                bh = max(4.0, val * (h * 0.86))
                by = cy - bh / 2.0
                grad = QLinearGradient(bx, by, bx, by + bh)
                grad.setColorAt(0.0, QColor("#818cf8"))
                grad.setColorAt(0.5, QColor("#6366f1"))
                grad.setColorAt(1.0, QColor("#4f46e5"))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.3, 1.3)

        painter.end()


class StatusGlowDotWidget(QWidget):
    """Renders the glowing status indicator dot on the left of the compact bottom status bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.dot_color = QColor("#34d399")

    def set_color(self, hex_color: str):
        self.dot_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0

        glow = QRadialGradient(QPointF(cx, cy), 10.5)
        c_glow = QColor(self.dot_color)
        c_glow.setAlpha(95)
        c_zero = QColor(self.dot_color)
        c_zero.setAlpha(0)
        glow.setColorAt(0.0, c_glow)
        glow.setColorAt(1.0, c_zero)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 10.5, 10.5)

        painter.setBrush(QBrush(self.dot_color))
        painter.drawEllipse(QPointF(cx, cy), 4.8, 4.8)
        painter.end()


class LanguageSelectorButton(QPushButton):
    """
    Renders the status-bar language selector (Vector Globe icon + 'Deutsch' / 'English' + Chevron)
    matching the Dark Neomorphism 2.0 target image while preserving full language code text for tests.
    """
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setMinimumWidth(118)
        self._hovered = False

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cy = h / 2.0

        if self._hovered:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(0, 2, w, h - 4), 6.0, 6.0)

        # 1. Vector Globe Icon
        gx, gy, gr = 12.0, cy, 7.2
        icon_col = QColor("#cbd5e1") if self._hovered else QColor("#94a3b8")
        painter.setPen(QPen(icon_col, 1.35, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(gx, gy), gr, gr)
        painter.drawEllipse(QPointF(gx, gy), gr * 0.46, gr)
        painter.drawLine(QPointF(gx - gr, gy), QPointF(gx + gr, gy))

        # 2. Language Label ("Deutsch" or "English")
        raw = self.text()
        display_lang = "Deutsch" if "DE" in raw.upper() and "ENGLISH" not in raw.upper() else "English"
        font = ThemeTypography.get_qfont(10, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#f8fafc") if self._hovered else QColor("#e2e8f0"))
        text_rect = QRectF(27.0, 0.0, w - 46.0, h)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), display_lang)

        # 3. Vector Downward Chevron
        cx = w - 13.0
        chev_pen = QPen(icon_col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(chev_pen)
        painter.drawLine(QPointF(cx - 3.8, cy - 1.2), QPointF(cx, cy + 2.4))
        painter.drawLine(QPointF(cx, cy + 2.4), QPointF(cx + 3.8, cy - 1.2))
        painter.end()


class LatencyWaveBadgeButton(QPushButton):
    """
    Renders the right-aligned latency indicator in the status bar with a 5-bar indigo soundwave icon
    and '0,4 s Latenz' text matching the Dark Neomorphism 2.0 target image.
    """
    def __init__(self, text: str = "0,4 s Latenz", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setMinimumWidth(122)
        self._hovered = False

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cy = h / 2.0

        if self._hovered:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(0, 2, w, h - 4), 6.0, 6.0)

        # 1. Mini 5-bar Violet/Indigo Soundwave Icon
        bars = [0.22, 0.52, 0.90, 0.52, 0.22]
        bw = 2.0
        bgap = 1.8
        sx = 8.0
        for idx, bh_rel in enumerate(bars):
            bh = max(3.0, bh_rel * 15.0)
            bx = sx + idx * (bw + bgap)
            by = cy - bh / 2.0
            grad = QLinearGradient(bx, by, bx, by + bh)
            grad.setColorAt(0.0, QColor("#818cf8"))
            grad.setColorAt(1.0, QColor("#4f46e5"))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bw, bh), 1.0, 1.0)

        # 2. Clean Latency Label
        raw = self.text().replace("〰", "").strip()
        font = ThemeTypography.get_qfont(10, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#f8fafc") if self._hovered else QColor("#e2e8f0"))
        text_rect = QRectF(32.0, 0.0, w - 36.0, h)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), raw)
        painter.end()



class ModelPresetCard(QFrame):
    """
    Dedicated unclipped hardware model preset card in Dark Neomorphism 2.0 style.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, name: str, tag: str, desc: str, led_color: str, led_text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")

        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(
            f"font-size: 9.5px; font-weight: 600; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_SUNKEN}; "
            f"padding: 2px 6px; border-radius: {ThemeMetrics.RADIUS_BADGE}; border: 1px solid {ThemeColors.BORDER_SUBTLE};"
        )

        top_row.addWidget(self.lbl_name)
        top_row.addWidget(self.lbl_tag)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")
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
                f"ModelPresetCard {{ background-color: {ThemeColors.CHIP_BG_SELECTED}; "
                f"border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                f"ModelPresetCard:hover {{ background-color: {ThemeColors.CHIP_BG_SELECTED_HOVER}; }}"
            )
            self.lbl_name.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
            self.lbl_desc.setStyleSheet("font-size: 11px; color: #c7d2fe; background: transparent;")
        else:
            self.setStyleSheet(
                f"ModelPresetCard {{ background-color: {ThemeColors.BG_CARD}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                f"ModelPresetCard:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER}; "
                f"border-color: {ThemeColors.BORDER_HOVER}; }}"
            )
            self.lbl_name.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
            self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class ModePresetCard(QFrame):
    """
    Tactile Dark Neomorphism 2.0 card for operating mode selection (Flow Mode vs Raw Dictation).
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(3)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self.lbl_title)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def set_selected(self, val: bool):
        self.selected = val
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                f"ModePresetCard {{ background-color: {ThemeColors.CHIP_BG_SELECTED}; "
                f"border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #c7d2fe; background: transparent;")
        else:
            self.setStyleSheet(
                f"ModePresetCard {{ background-color: {ThemeColors.BG_CARD}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                f"ModePresetCard:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; "
                f"border-color: {ThemeColors.BORDER_HOVER}; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
            self.lbl_sub.setStyleSheet(f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class TonePresetCard(QFrame):
    """
    Tactile Dark Neomorphism 2.0 card for Tone & Style profile selection.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, tag: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(
            f"font-size: 9px; font-weight: 600; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_SUNKEN}; "
            f"padding: 2px 6px; border-radius: 5px; border: 1px solid {ThemeColors.BORDER_SUBTLE};"
        )
        top.addWidget(self.lbl_title)
        top.addStretch()
        top.addWidget(self.lbl_tag)
        layout.addLayout(top)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(f"font-size: 10.5px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def set_selected(self, val: bool):
        self.selected = val
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                f"TonePresetCard {{ background-color: {ThemeColors.CHIP_BG_SELECTED}; "
                f"border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
                f"border-radius: 12px; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
            self.lbl_tag.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: #e0e7ff; background: {ThemeColors.ACCENT_INDIGO}; "
                f"padding: 2px 6px; border-radius: 5px; border: none;"
            )
            self.lbl_sub.setStyleSheet("font-size: 10.5px; color: #c7d2fe; background: transparent;")
        else:
            self.setStyleSheet(
                f"TonePresetCard {{ background-color: {ThemeColors.BG_CARD}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: 12px; }} "
                f"TonePresetCard:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; "
                f"border-color: {ThemeColors.BORDER_HOVER}; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
            self.lbl_tag.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_SUNKEN}; "
                f"padding: 2px 6px; border-radius: 5px; border: 1px solid {ThemeColors.BORDER_SUBTLE};"
            )
            self.lbl_sub.setStyleSheet(f"font-size: 10.5px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class LevelCalibrationWidget(QFrame):
    """
    Live Audio Calibration Helper & Visual Peak Meter inside a sunken neomorphic well.
    Shows current microphone signal levels with 3 color-coded target zones:
    1. Indigo (< 30%): Too quiet
    2. Mint Green (30% - 80%): Optimal Whisper level
    3. Coral/Red (> 80%): Clipping risk
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.current_level = 0.0
        self.peak_level = 0.0
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._decay)
        self.decay_timer.start(30)
        self.setStyleSheet(
            f"background: {ThemeColors.BG_SUNKEN}; "
            f"border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP}; "
            f"border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM}; "
            f"border-radius: 8px;"
        )

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

        # Sunken track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#080a10")))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3.0, 3.0)

        # 3-Zone target brackets
        z1_w = bar_w * 0.30
        painter.setBrush(QBrush(QColor(99, 102, 241, 35)))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, z1_w, bar_h), 3.0, 3.0)

        z2_x = bar_x + z1_w
        z2_w = bar_w * 0.50
        painter.setBrush(QBrush(QColor(52, 211, 153, 45)))
        painter.drawRoundedRect(QRectF(z2_x, bar_y, z2_w, bar_h), 0.0, 0.0)

        z3_x = z2_x + z2_w
        z3_w = bar_w - z1_w - z2_w
        painter.setBrush(QBrush(QColor(235, 94, 56, 40)))
        painter.drawRoundedRect(QRectF(z3_x, bar_y, z3_w, bar_h), 3.0, 3.0)

        fill_w = max(0.0, min(bar_w, bar_w * self.current_level))
        if fill_w > 0:
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            grad.setColorAt(0.0, QColor("#7c83e0"))
            grad.setColorAt(0.30, QColor("#34d399"))
            grad.setColorAt(0.80, QColor("#f59e0b"))
            grad.setColorAt(0.95, QColor("#eb5e38"))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 3.0, 3.0)

        if self.peak_level > 0.01:
            px = bar_x + min(bar_w - 2.0, bar_w * self.peak_level)
            painter.setPen(QPen(QColor(248, 250, 252, 230), 1.8))
            painter.drawLine(int(px), int(bar_y - 1), int(px), int(bar_y + bar_h + 1))

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(int(bar_x), int(bar_y + bar_h + 16), tr("meter_too_quiet"))

        painter.setPen(QColor("#34d399"))
        painter.drawText(int(z2_x + 6), int(bar_y + bar_h + 16), tr("meter_optimal"))

        painter.setPen(QColor("#f26b46"))
        painter.drawText(int(z3_x - 10), int(bar_y + bar_h + 16), tr("meter_clipping"))
        painter.end()


class ModelPriorityCard(QFrame):
    """
    Selectable 3-Tier Priority Card (Speed vs Balanced vs Quality) in Dark Neomorphism 2.0.
    """
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, badge: str, sub: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(62)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.lbl_title = QLabel(title)
        self.lbl_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")

        self.lbl_badge = QLabel(badge)
        self.lbl_badge.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_badge.setStyleSheet(
            f"font-size: 9px; font-weight: 600; color: {ThemeColors.ACCENT_INDIGO_BRIGHT}; background: {ThemeColors.ACCENT_INDIGO_MUTED}; "
            f"padding: 1px 6px; border-radius: 4px; border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};"
        )
        top.addWidget(self.lbl_title)
        top.addWidget(self.lbl_badge)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(f"font-size: 10.5px; color: {ThemeColors.TEXT_MUTED}; background: transparent;")
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
        accent_color = ThemeColors.ACCENT_INDIGO_BRIGHT
        if self.key == "balanced":
            accent_color = ThemeColors.SUCCESS
        elif self.key == "quality":
            accent_color = ThemeColors.ACCENT_CORAL

        if self.selected:
            self.setStyleSheet(
                f"QFrame {{ background-color: {ThemeColors.CHIP_BG_SELECTED}; border: 1.5px solid {accent_color}; border-radius: {ThemeMetrics.RADIUS_CARD}; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
            self.lbl_badge.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {accent_color}; background: {ThemeColors.BG_SUNKEN}; "
                f"padding: 1px 6px; border-radius: {ThemeMetrics.RADIUS_BADGE}; border: 1px solid {accent_color};"
            )
            self.lbl_sub.setStyleSheet("font-size: 10.5px; color: #e2e8f0; background: transparent; font-weight: 400;")
        else:
            self.setStyleSheet(
                f"QFrame {{ background-color: {ThemeColors.BG_CARD}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: {ThemeMetrics.RADIUS_CARD}; }} "
                f"QFrame:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER}; "
                f"border-color: {ThemeColors.BORDER_HOVER}; }}"
            )
            self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
            self.lbl_badge.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_SUNKEN}; "
                f"padding: 1px 6px; border-radius: {ThemeMetrics.RADIUS_BADGE}; border: 1px solid {ThemeColors.BORDER_SUBTLE};"
            )
            self.lbl_sub.setStyleSheet(f"font-size: 10.5px; color: {ThemeColors.TEXT_MUTED}; background: transparent; font-weight: 400;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class SubModelChip(QPushButton):
    """
    Selectable Neomorphic Pill-style chip button for sub-models within the active tier.
    """
    def __init__(self, model_id: str, label: str, price_badge: str = "", parent=None):
        super().__init__(parent)
        self.model_id = model_id
        self.label = label
        self.price_badge = price_badge
        self.selected = False
        text_disp = f"{label}   ({price_badge})" if price_badge else label
        self.setText(text_disp)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.update_style()

    def set_selected(self, val: bool):
        self.selected = bool(val)
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet(
                f"QPushButton {{ background-color: {ThemeColors.CHIP_BG_SELECTED}; color: {ThemeColors.TEXT_PRIMARY}; "
                f"border: 1.5px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
                f"border-radius: {ThemeMetrics.RADIUS_CONTROL}; font-size: 11px; font-weight: 600; padding: 2px 12px; }} "
                f"QPushButton:hover {{ background-color: {ThemeColors.CHIP_BG_SELECTED_HOVER}; }}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{ background-color: {ThemeColors.BG_ELEVATED}; color: {ThemeColors.CHIP_TEXT_UNSELECTED}; "
                f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
                f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                f"border-radius: {ThemeMetrics.RADIUS_CONTROL}; font-size: 11px; font-weight: 500; padding: 2px 12px; }} "
                f"QPushButton:hover {{ background-color: {ThemeColors.BG_ELEVATED_HOVER}; color: {ThemeColors.TEXT_PRIMARY}; border-color: {ThemeColors.BORDER_HOVER}; }}"
            )


class CollapsibleSettingsCard(QFrame):
    """
    Dark Neomorphism 2.0 settings section card with raised graphite surface,
    dual bevel borders, clear summary pill, and progressive disclosure body.
    """
    def __init__(self, title: str, summary: str = "", description: str = "", is_expanded: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_expanded = is_expanded

        self.setStyleSheet(
            f"QFrame#card {{ "
            f"  background-color: {ThemeColors.BG_CARD}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM}; "
            f"  border-radius: {ThemeMetrics.RADIUS_CARD}; "
            f"}} "
            f"QFrame#card:hover {{ "
            f"  background-color: {ThemeColors.BG_CARD_HOVER}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HOVER}; "
            f"}}"
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setSpacing(6)

        # Header (Clickable)
        self.header_widget = QWidget()
        self.header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("section_title")
        self.lbl_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_title.setStyleSheet(
            f"font-size: 13.5px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; letter-spacing: 0.1px; background: transparent;"
        )

        self.lbl_summary = QLabel(summary)
        self.lbl_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_summary.setStyleSheet(
            f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; font-weight: 500; background-color: {ThemeColors.BG_SUNKEN}; "
            f"padding: 3px 10px; border-radius: 8px; border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP}; "
            f"border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};"
        )

        self.lbl_toggle = QLabel("▾" if is_expanded else "▸")
        self.lbl_toggle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_toggle.setFixedSize(24, 24)
        self.lbl_toggle.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_ELEVATED}; "
            f"border-radius: 6px; border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};"
        )

        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        h_layout.addWidget(self.lbl_summary)
        h_layout.addWidget(self.lbl_toggle)

        self.main_layout.addWidget(self.header_widget)

        # Subdued Description beneath title
        if description:
            self.lbl_desc = QLabel(description)
            self.lbl_desc.setTextFormat(Qt.TextFormat.PlainText)
            self.lbl_desc.setWordWrap(True)
            self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {ThemeColors.TEXT_MUTED}; margin-top: -2px; margin-bottom: 4px; background: transparent;")
            self.main_layout.addWidget(self.lbl_desc)
        else:
            self.lbl_desc = None

        # Content Body
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 10, 0, 2)
        self.body_layout.setSpacing(12)
        self.body_widget.setVisible(is_expanded)

        self.main_layout.addWidget(self.body_widget)

        self.header_widget.mousePressEvent = self._on_header_clicked

    def _on_header_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def set_summary(self, text: str):
        self.lbl_summary.setText(text)
        self.lbl_summary.setVisible(bool(text.strip()))

    def set_description(self, text: str):
        if self.lbl_desc:
            self.lbl_desc.setText(text)

    def toggle(self):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, val: bool):
        self.is_expanded = val
        self.body_widget.setVisible(val)
        self.lbl_toggle.setText("▾" if val else "▸")
        if val:
            self.lbl_title.setStyleSheet(f"font-size: 13.5px; font-weight: 700; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;")
            self.lbl_toggle.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: #ffffff; background: {ThemeColors.ACCENT_INDIGO_SURFACE}; "
                f"border-radius: 6px; border: 1px solid {ThemeColors.ACCENT_INDIGO_BRIGHT};"
            )
        else:
            self.lbl_title.setStyleSheet(f"font-size: 13.5px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;")
            self.lbl_toggle.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: {ThemeColors.TEXT_MUTED}; background: {ThemeColors.BG_ELEVATED}; "
                f"border-radius: 6px; border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM};"
            )


class SettingsDisclosureSection(QFrame):
    """
    Recessed Dark Neomorphism 2.0 progressive disclosure sub-accordion for technical details.
    """
    toggled = pyqtSignal(bool)

    def __init__(
        self,
        title: str,
        summary: str = "",
        is_expanded: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("disclosure_section")
        self.is_expanded = is_expanded

        self.setStyleSheet(
            f"QFrame#disclosure_section {{ "
            f"  background-color: {ThemeColors.BG_SUNKEN}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUNKEN_LEFT}; "
            f"  border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_SUNKEN_RIGHT}; "
            f"  border-radius: 10px; "
            f"}} "
            f"QFrame#disclosure_section:hover {{ "
            f"  border-color: {ThemeColors.BORDER_HOVER}; "
            f"}}"
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 10, 14, 10)
        self.main_layout.setSpacing(6)

        # Clickable Header
        self.header_widget = QWidget()
        self.header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_widget.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(2, 2, 2, 2)
        h_layout.setSpacing(8)

        self.lbl_toggle = QLabel("▾" if is_expanded else "▸")
        self.lbl_toggle.setStyleSheet(
            f"font-size: 11.5px; font-weight: 700; color: {ThemeColors.ACCENT_INDIGO_BRIGHT}; background: transparent;"
        )

        self.lbl_title = QLabel(title)
        self.lbl_title.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_title.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;"
        )

        self.lbl_summary = QLabel(summary)
        self.lbl_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_summary.setStyleSheet(
            f"font-size: 10.5px; font-weight: 500; color: {ThemeColors.TEXT_MUTED}; background: transparent;"
        )

        h_layout.addWidget(self.lbl_toggle)
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        h_layout.addWidget(self.lbl_summary)
        self.main_layout.addWidget(self.header_widget)

        # Content Body
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(6, 6, 6, 4)
        self.body_layout.setSpacing(8)
        self.body_widget.setVisible(is_expanded)
        self.main_layout.addWidget(self.body_widget)

        self.header_widget.mousePressEvent = self._on_header_clicked

    def _on_header_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def toggle(self):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, val: bool):
        self.is_expanded = val
        self.body_widget.setVisible(val)
        self.lbl_toggle.setText("▾" if val else "▸")
        if val:
            self.lbl_title.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_PRIMARY}; background: transparent;"
            )
            self.lbl_toggle.setStyleSheet(
                f"font-size: 11.5px; font-weight: 700; color: {ThemeColors.ACCENT_CORAL}; background: transparent;"
            )
        else:
            self.lbl_title.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {ThemeColors.TEXT_SECONDARY}; background: transparent;"
            )
            self.lbl_toggle.setStyleSheet(
                f"font-size: 11.5px; font-weight: 700; color: {ThemeColors.ACCENT_INDIGO_BRIGHT}; background: transparent;"
            )
        self.toggled.emit(val)

    def set_title(self, text: str):
        self.lbl_title.setText(text)

    def set_summary(self, text: str):
        self.lbl_summary.setText(text)

    def matches_query(self, query: str) -> bool:
        """Recursively checks whether query matches title, summary, or any child control."""
        q = query.lower()
        if q in self.lbl_title.text().lower():
            return True
        if q in self.lbl_summary.text().lower():
            return True
        for child in self.body_widget.findChildren((QLabel, QCheckBox, QPushButton, QLineEdit, QComboBox)):
            if isinstance(child, (QLabel, QCheckBox, QPushButton)) and q in child.text().lower():
                return True
            elif isinstance(child, QLineEdit) and (
                q in child.placeholderText().lower() or q in child.text().lower()
            ):
                return True
            elif isinstance(child, QComboBox):
                for i in range(child.count()):
                    if q in child.itemText(i).lower():
                        return True
                if q in child.currentText().lower():
                    return True
        return False


# =========================================================================
# 2. Hotkey Capture Modal Dialog
# =========================================================================

class HotkeyCaptureDialog(QDialog):
    """Dark Neomorphism 2.0 modal dialog to record key combinations."""
    def __init__(self, current_key="f8", parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("hotkey_dialog_title"))
        self.setFixedSize(390, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            f"QDialog {{ background-color: {ThemeColors.BG_DIALOG}; "
            f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; "
            f"border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM}; border-radius: 14px; }}"
            f"QLabel {{ color: {ThemeColors.TEXT_PRIMARY}; font-size: 12px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel(tr("hotkey_dialog_heading"))
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {ThemeColors.TEXT_PRIMARY};")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(tr("hotkey_dialog_sub"))
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        self.key_display = QLabel(current_key.upper())
        self.key_display.setStyleSheet(
            f"background-color: {ThemeColors.BG_SUNKEN}; color: {ThemeColors.ACCENT_CORAL}; font-weight: 700; font-size: 13px; "
            f"letter-spacing: 0.8px; padding: 8px 18px; border-radius: 8px; "
            f"border-top: 1px solid {ThemeColors.BORDER_SUNKEN_TOP}; border-bottom: 1px solid {ThemeColors.BORDER_SUNKEN_BOTTOM};"
        )
        layout.addWidget(self.key_display, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_cancel = QPushButton(tr("cancel"))
        self.btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(tr("save"))
        self.btn_save.setObjectName("btn_primary_coral")
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
# 3. Dark Neomorphism 2.0 Audio Spectrum Visualizer Widget
# =========================================================================

class HeroWaveformWidget(QWidget):
    """
    Calm 36-bar Audio Spectrum Analyzer with Dark Neomorphism 2.0 palette and Reduce Motion support.
    Uses Coral/Orange (#eb5e38) during recording, Muted Indigo/Violet (#7c83e0) during voice edit
    and formatting/transcription, and subtle recessed graphite bars in idle state.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.num_bars = 36
        self.bar_heights = [0.08] * self.num_bars
        self.current_rms = 0.0
        self.target_rms = 0.0
        self.current_state = "idle"
        self.is_recording = False
        self.is_voice_edit = False
        self.is_transcribing = False
        self.is_formatting = False
        self.is_error = False

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_frame)
        self.anim_timer.start(24)

    def set_level(self, rms: float):
        self.target_rms = min(1.0, rms * 3.4)

    def set_state(self, state: str):
        self.current_state = state
        self.is_recording = (state == "recording")
        self.is_voice_edit = (state == "voice_edit")
        self.is_transcribing = (state in ("transcribing", "formatting"))
        self.is_formatting = (state == "formatting")
        self.is_error = (state == "error")
        if not (self.is_recording or self.is_voice_edit):
            self.target_rms = 0.0
        self.update()

    def _on_anim_frame(self):
        reduced = is_reduced_motion(config)
        self.current_rms += (self.target_rms - self.current_rms) * (0.6 if reduced else 0.35)
        t = 0.0 if reduced else time.time() * 4.2

        for i in range(self.num_bars):
            if self.is_recording:
                wave = 0.85 if reduced else (math.sin(t * 2.2 + i * 0.38) * 0.25 + 0.75)
                target_h = max(0.10, min(1.0, self.current_rms * wave * 1.35))
            elif self.is_voice_edit:
                wave = 0.85 if reduced else (math.sin(t * 2.5 + i * 0.42) * 0.30 + 0.70)
                target_h = max(0.10, min(1.0, self.current_rms * wave * 1.30))
            elif self.is_formatting:
                scan = 0.45 if reduced else ((math.sin(t * 2.8 - i * 0.32) + 1.0) * 0.5)
                target_h = 0.10 + 0.42 * (scan ** 2)
            elif self.is_transcribing:
                scan = 0.45 if reduced else ((math.sin(t * 3.2 - i * 0.28) + 1.0) * 0.5)
                target_h = 0.10 + 0.45 * (scan ** 3)
            elif self.is_error:
                target_h = 0.16 if reduced else (0.12 + 0.08 * math.sin(t * 6.0 + i * 0.5))
            else:
                target_h = 0.08 if reduced else (0.07 + 0.025 * math.sin(t * 0.5 + i * 0.22))

            self.bar_heights[i] += (target_h - self.bar_heights[i]) * (0.7 if reduced else 0.35)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center_y = h / 2.0

        bar_w = 3.2
        gap = max(2.0, (w - (self.num_bars * bar_w)) / (self.num_bars + 1))
        max_h = h * 0.78

        for i in range(self.num_bars):
            bh = max(3.0, self.bar_heights[i] * max_h)
            bx = gap + i * (bar_w + gap)
            by = center_y - (bh / 2.0)

            grad = QLinearGradient(bx, by, bx, by + bh)
            if self.is_recording:
                grad.setColorAt(0.0, QColor("#f46d48"))
                grad.setColorAt(1.0, QColor("#d14b27"))
            elif self.is_voice_edit or self.is_formatting:
                grad.setColorAt(0.0, QColor("#818cf8"))
                grad.setColorAt(1.0, QColor("#4f46e5"))
            elif self.is_transcribing:
                grad.setColorAt(0.0, QColor("#7c83e0"))
                grad.setColorAt(1.0, QColor("#3d448a"))
            elif self.is_error:
                grad.setColorAt(0.0, QColor("#f87171"))
                grad.setColorAt(1.0, QColor("#dc2626"))
            else:
                grad.setColorAt(0.0, QColor("#262d42"))
                grad.setColorAt(1.0, QColor("#181d2c"))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.6, 1.6)

        painter.end()



# =========================================================================
# 4. Main Dashboard Window
# =========================================================================

class DashboardWindow(QMainWindow):
    models_fetched_signal = pyqtSignal(list, str)  # (raw_models, error_msg)
    connection_test_signal = pyqtSignal(str, dict)  # (provider_name, result_dict)
    downloader_finished_signal = pyqtSignal(str, bool, str)  # (model_id, success, message)

    def __init__(self, audio_recorder: AudioRecorder, stt_engine, ai_formatter, parent=None, injector=None):
        super().__init__(parent)
        self.audio_recorder = audio_recorder
        self.stt_engine = stt_engine
        self.ai_formatter = ai_formatter
        self.injector = injector
        self.gpu_monitor = GPUMonitor()

        # Dynamic Hardware Detection
        self._detect_hardware()

        # Window Configuration
        self.setWindowTitle("Velodictum")
        self.setWindowIcon(create_app_icon(64))
        self.resize(1040, 760)
        self.setMinimumSize(900, 640)
        apply_window_backdrop(self)

        # State trackers
        self.total_dictations = 0
        self.total_words = 0
        self.latencies: List[float] = []
        self.history_records: List[Dict] = []
        self.mode_cards: Dict[str, ModePresetCard] = {}
        self.profile_cards: Dict[str, ModelPresetCard] = {}
        self.tone_cards: Dict[str, TonePresetCard] = {}
        self.priority_cards: Dict[str, ModelPriorityCard] = {}
        self.all_disclosure_sections: List[SettingsDisclosureSection] = []
        self.sidebar_nav_buttons: List[QPushButton] = []

        # Root 2-Pane Dark Neomorphism 2.0 Layout (Deep Blue-Black #0b0d14 Canvas)
        self._active_sidebar_item = 0
        central_widget = QWidget(self)
        central_widget.setObjectName("neomorphic_canvas")
        central_widget.setStyleSheet(f"QWidget#neomorphic_canvas {{ background-color: {ThemeColors.BG_WINDOW}; }}")
        self.setCentralWidget(central_widget)

        self.shell_layout = QHBoxLayout(central_widget)
        self.shell_layout.setContentsMargins(16, 16, 16, 16)
        self.shell_layout.setSpacing(18)

        # Left Raised Neomorphic Sidebar Panel
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("fluent_sidebar")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(
            f"QFrame#fluent_sidebar {{ "
            f"  background-color: {ThemeColors.BG_SIDEBAR}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-radius: {ThemeMetrics.RADIUS_CARD_LARGE}; "
            f"}}"
        )
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(16, 22, 16, 18)
        self.sidebar_layout.setSpacing(8)

        # Right Content Stage
        self.content_stage = QFrame()
        self.content_stage.setObjectName("fluent_stage")
        self.content_stage.setStyleSheet("QFrame#fluent_stage { background: transparent; border: none; }")
        self.main_layout = QVBoxLayout(self.content_stage)
        self.main_layout.setContentsMargins(4, 2, 4, 2)
        self.main_layout.setSpacing(16)

        self.shell_layout.addWidget(self.sidebar_frame)
        self.shell_layout.addWidget(self.content_stage, stretch=1)

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
        apply_window_backdrop(self)

    def _toggle_ui_language(self):
        cur_lang = get_current_language()
        next_lang = "de" if cur_lang == "en" else "en"
        config.system.ui_language = next_lang
        set_current_language(next_lang)
        config.save()
        signals.language_changed.emit(next_lang)

    # =========================================================================
    # Dark Neomorphism 2.0 Sidebar Brand & Navigation (Studio, Diktate, Profile, Einstellungen)
    # =========================================================================

    def _build_header(self):
        # 1. Brand Header (Indigo Soundwave Icon + Velodictum)
        brand_box = QWidget()
        brand_row = QHBoxLayout(brand_box)
        brand_row.setContentsMargins(6, 4, 4, 22)
        brand_row.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(_create_brand_wave_pixmap(28))
        icon_lbl.setStyleSheet("background: transparent;")
        brand_row.addWidget(icon_lbl)

        title = QLabel("Velodictum")
        title.setObjectName("brand_title")
        title.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_DISPLAY}; font-size: 18px; font-weight: 700; "
            f"color: {ThemeColors.TEXT_PRIMARY}; letter-spacing: -0.3px; background: transparent;"
        )
        brand_row.addWidget(title)
        brand_row.addStretch()
        self.sidebar_layout.addWidget(brand_box)

        # 2. Navigation Buttons Container (Studio, Diktate, Profile, Einstellungen)
        self.nav_container = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(8)
        self.sidebar_layout.addWidget(self.nav_container)

        self.sidebar_layout.addStretch()

    def _on_sidebar_nav_clicked(self, nav_idx: int):
        """
        Routes the 4 Dark Neomorphism 2.0 sidebar items (Studio, Diktate, Profile, Einstellungen)
        while preserving the canonical 3-tab QTabWidget indices (0=Studio, 1=Library, 2=Settings).
        """
        self._active_sidebar_item = nav_idx
        if nav_idx == 0:
            if hasattr(self, "tabs"):
                self.tabs.setCurrentIndex(0)
        elif nav_idx == 1:
            if hasattr(self, "tabs"):
                self.tabs.setCurrentIndex(1)
            if hasattr(self, "_switch_library_subview"):
                self._switch_library_subview(0)
        elif nav_idx == 2:
            if hasattr(self, "tabs"):
                self.tabs.setCurrentIndex(1)
            if hasattr(self, "_switch_library_subview"):
                self._switch_library_subview(2)
        elif nav_idx == 3:
            if hasattr(self, "tabs"):
                self.tabs.setCurrentIndex(2)
        self._update_sidebar_nav_styles_by_button(nav_idx)

    def _switch_main_tab(self, index: int):
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(index)
        self._update_sidebar_nav_styles(index)

    def _update_sidebar_nav_styles(self, tab_idx: int):
        if tab_idx == 0:
            btn_idx = 0
        elif tab_idx == 1:
            btn_idx = 2 if getattr(self, "_active_sidebar_item", 1) == 2 else 1
        else:
            btn_idx = 3
        self._active_sidebar_item = btn_idx
        self._update_sidebar_nav_styles_by_button(btn_idx)

    def _update_sidebar_nav_styles_by_button(self, active_btn_idx: int):
        icon_kinds = ["studio", "dictations", "profiles", "settings"]
        for i, btn in enumerate(getattr(self, "sidebar_nav_buttons", [])):
            is_sel = (i == active_btn_idx)
            btn.setChecked(is_sel)
            kind = icon_kinds[i] if i < len(icon_kinds) else "studio"
            btn.setIcon(_create_sidebar_icon(kind, "#ffffff" if is_sel else "#8b93a7", 18))
            btn.setIconSize(QSize(18, 18))
            if is_sel:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {ThemeColors.ACCENT_INDIGO_SURFACE}; color: #ffffff; "
                    f"font-size: 13.5px; font-weight: 600; text-align: left; padding: 11px 16px; "
                    f"border-radius: 11px; "
                    f"border-top: 1px solid rgba(255, 255, 255, 0.22); "
                    f"border-left: 1px solid {ThemeColors.ACCENT_INDIGO_BRIGHT}; "
                    f"border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
                    f"border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM}; }} "
                    f"QPushButton:focus {{ border: 2px solid {ThemeColors.BORDER_FOCUS}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; color: {ThemeColors.TEXT_MUTED}; "
                    f"font-size: 13.5px; font-weight: 500; text-align: left; padding: 11px 16px; "
                    f"border-radius: 11px; border: 1px solid transparent; }} "
                    f"QPushButton:hover {{ background-color: {ThemeColors.BG_CARD_HOVER}; color: {ThemeColors.TEXT_PRIMARY}; "
                    f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
                    f"border-bottom: 1px solid {ThemeColors.BORDER_BOTTOM}; }} "
                    f"QPushButton:focus {{ border: 2px solid {ThemeColors.BORDER_FOCUS}; }}"
                )

    # =========================================================================
    # Tab Architecture & Sidebar Binding
    # =========================================================================

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setObjectName("dashboard_tabs")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setVisible(False)
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; background: transparent; }")

        self.tab_studio = QWidget()
        self.tab_library = QWidget()
        self.tab_settings = QWidget()

        self.tabs.addTab(self.tab_studio, tr("tab_dashboard"))
        self.tabs.addTab(self.tab_library, tr("tab_library_combined"))
        self.tabs.addTab(self.tab_settings, tr("tab_settings"))

        lang = get_current_language()
        nav_items = [
            ("studio", "  Studio", 0),
            ("dictations", "  Diktate" if lang == "de" else "  Dictations", 1),
            ("profiles", "  Profile" if lang == "de" else "  Profiles", 2),
            ("settings", f"  {tr('tab_settings')}", 3),
        ]
        self.sidebar_nav_buttons.clear()
        for kind, label_txt, nav_idx in nav_items:
            btn = QPushButton(label_txt)
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(_create_sidebar_icon(kind, "#8b93a7", 18))
            btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _, target=nav_idx: self._on_sidebar_nav_clicked(target))
            self.nav_layout.addWidget(btn)
            self.sidebar_nav_buttons.append(btn)

        self.tabs.currentChanged.connect(self._update_sidebar_nav_styles)
        self._update_sidebar_nav_styles_by_button(0)

        self._setup_studio_tab()
        self._setup_library_tab()
        self._setup_settings_tab()

        self.main_layout.addWidget(self.tabs)

    # =========================================================================
    # TAB 1: STUDIO (Dark Neomorphism 2.0 Non-Scrolling 3-Zone Command Center)
    # =========================================================================

    def _format_hotkey_parts(self, raw_key: str) -> List[str]:
        """Splits a hotkey string like 'ctrl+space' or 'f8' into localized keycap labels."""
        is_de = (get_current_language() == "de")
        key_map_de = {
            "ctrl": "Strg",
            "control": "Strg",
            "space": "Leertaste",
            "alt": "Alt",
            "shift": "Umschalt",
            "cmd": "Win",
            "win": "Win",
            "caps_lock": "Feststelltaste",
        }
        key_map_en = {
            "ctrl": "Ctrl",
            "control": "Ctrl",
            "space": "Space",
            "alt": "Alt",
            "shift": "Shift",
            "cmd": "Win",
            "win": "Win",
            "caps_lock": "CapsLock",
        }
        mapping = key_map_de if is_de else key_map_en
        tokens = [t.strip().lower() for t in (raw_key or "ctrl+space").split("+") if t.strip()]
        if not tokens:
            tokens = ["ctrl", "space"]
        return [mapping.get(t, t.upper()) for t in tokens]

    def _refresh_hero_keycaps(self):
        """Rebuilds the tactile neomorphic keycap badges in the Studio recording centerpiece."""
        if not hasattr(self, "hero_keycaps_layout"):
            return
        while self.hero_keycaps_layout.count() > 0:
            item = self.hero_keycaps_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        self.hero_keycaps_layout.addStretch(1)
        parts = self._format_hotkey_parts(getattr(config.hotkey, "key", "ctrl+space"))
        keycap_qss = get_keycap_qss("QLabel")
        for idx, part in enumerate(parts):
            if idx > 0:
                plus_lbl = QLabel("+")
                plus_lbl.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
                self.hero_keycaps_layout.addWidget(plus_lbl)
            cap = QLabel(part)
            cap.setStyleSheet(keycap_qss)
            self.hero_keycaps_layout.addWidget(cap)
        self.hero_keycaps_layout.addStretch(1)

    def _on_hero_cta_clicked(self):
        """Triggers or stops dictation when the user clicks the dominant Coral 'Diktat starten' button."""
        is_rec = getattr(self.hero_waveform, "is_recording", False)
        if is_rec:
            signals.recording_stopped.emit()
        else:
            signals.recording_started.emit()

    def _export_latest_text(self):
        """Exports the latest dictation transcript to a .txt or .md file."""
        txt = self.lbl_latest_text.text().strip('"\n\r ')
        if not txt:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Diktat exportieren" if get_current_language() == "de" else "Export Dictation",
            "velodictum_diktat.txt",
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(txt + "\n")
            except Exception as e:
                print(f"[Export] Failed to save dictation: {e}")

    def _open_latest_in_scratchpad(self):
        """Transfers the latest dictation into Scratchpad and opens the Scratchpad window."""
        self._on_open_scratchpad_clicked()
        txt = self.lbl_latest_text.text().strip('"\n\r ')
        if txt and hasattr(self, "scratchpad") and self.scratchpad:
            cur = self.scratchpad.text_edit.toPlainText().strip()
            combined = f"{cur}\n\n{txt}".strip() if cur else txt
            self.scratchpad.text_edit.setPlainText(combined)
            self.scratchpad._update_stats()

    def _show_latest_dictation_menu(self):
        """Opens the Dark Neomorphism 2.0 action menu from the '[•••]' button on the 'Letztes Diktat' card."""
        is_de = (get_current_language() == "de")
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {ThemeColors.BG_POPOVER}; color: {ThemeColors.TEXT_PRIMARY}; "
            f"border: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; border-radius: 10px; padding: 6px; }} "
            f"QMenu::item {{ padding: 7px 14px; border-radius: 6px; font-size: 12px; font-weight: 500; }} "
            f"QMenu::item:selected {{ background-color: {ThemeColors.ACCENT_INDIGO_SURFACE}; color: #ffffff; }} "
            f"QMenu::separator {{ height: 1px; background: {ThemeColors.BORDER_SUBTLE}; margin: 4px 6px; }}"
        )

        act_copy = QAction("📋  " + tr("copy"), self)
        act_copy.triggered.connect(self._copy_latest_text)
        menu.addAction(act_copy)

        act_export = QAction("💾  " + ("Als Datei exportieren (.txt / .md)..." if is_de else "Export to File (.txt / .md)..."), self)
        act_export.triggered.connect(self._export_latest_text)
        menu.addAction(act_export)

        menu.addSeparator()

        act_scratch = QAction("✦  " + ("Scratchpad öffnen" if is_de else "Open Scratchpad"), self)
        act_scratch.triggered.connect(self._on_open_scratchpad_clicked)
        menu.addAction(act_scratch)

        act_to_scratch = QAction("📝  " + ("Im Scratchpad bearbeiten" if is_de else "Edit in Scratchpad"), self)
        act_to_scratch.triggered.connect(self._open_latest_in_scratchpad)
        menu.addAction(act_to_scratch)

        act_hist = QAction("▤  " + ("Diktat-Verlauf & Bibliothek" if is_de else "Dictation History & Library"), self)
        act_hist.triggered.connect(lambda: self._on_sidebar_nav_clicked(1))
        menu.addAction(act_hist)

        act_prof = QAction("◈  " + ("Betriebsmodus & Profile verwalten" if is_de else "Manage Mode & Profiles"), self)
        act_prof.triggered.connect(lambda: self._on_sidebar_nav_clicked(2))
        menu.addAction(act_prof)

        menu.addSeparator()

        # Engine, Whisper Provider & Profile summary item
        eng_txt = self.pill_engine.text() if hasattr(self, "pill_engine") else ""
        stt_txt = self.pill_profile.text() if hasattr(self, "pill_profile") else ""
        hw_txt = self.lbl_hw_badge.text() if hasattr(self, "lbl_hw_badge") else ""
        info_action = QAction(f"⚙  {stt_txt} · {eng_txt} ({hw_txt})", self)
        info_action.triggered.connect(lambda: self._on_sidebar_nav_clicked(3))
        menu.addAction(info_action)

        if hasattr(self, "btn_latest_menu"):
            pos = self.btn_latest_menu.mapToGlobal(QPoint(0, self.btn_latest_menu.height() + 4))
            menu.exec(pos)

    def _setup_studio_tab(self):
        """
        Builds the viewport-fitted Dark Neomorphism 2.0 Studio Screen without QScrollArea
        and without permanent operating mode or profile card grids:
        - Top 2-Column Split: Dominant Central Recording Card + Right 'Letztes Diktat' Card
        - Bottom Compact Status Bar: Glowing Ready Dot + Language Selector + Latency Indicator
        """
        root_layout = QVBoxLayout(self.tab_studio)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        # Keep off-stage HeroWaveformWidget instance for live audio/state telemetry contract
        self.hero_waveform = HeroWaveformWidget(self)
        self.hero_waveform.setVisible(False)
        self.waveform_widget = self.hero_waveform

        # ---------------------------------------------------------------------
        # 1. Top 2-Column Split Stage (Viewport-fitted, No ScrollArea):
        #    Left (stretch=54): Dominant Recording Centerpiece ("Diktat starten")
        #    Right (stretch=46): Secondary Surface ("Letztes Diktat")
        # ---------------------------------------------------------------------
        self.studio_top_split = QHBoxLayout()
        self.studio_top_split.setSpacing(18)

        # --- LEFT: Primary Recording Hero Panel ---
        self.hero_card = QFrame()
        self.hero_card.setObjectName("hero_card")
        self.hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hero_card.setMinimumHeight(250)
        self.hero_card.setStyleSheet(
            f"QFrame#hero_card {{ "
            f"  background-color: {ThemeColors.BG_HERO_CARD}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-radius: {ThemeMetrics.RADIUS_CARD_LARGE}; "
            f"}}"
        )
        hc_layout = QVBoxLayout(self.hero_card)
        hc_layout.setContentsMargins(24, 24, 24, 24)
        hc_layout.setSpacing(10)

        hc_layout.addStretch(1)

        # Dominant Circular Coral/Orange Record CTA Button inside Sunken Ring Socket
        self.btn_hero_record_cta = NeomorphicRecordButton(self)
        self.btn_hero_record_cta.setToolTip("Diktat starten / stoppen")
        self.btn_hero_record_cta.clicked.connect(self._on_hero_cta_clicked)
        hc_layout.addWidget(self.btn_hero_record_cta, alignment=Qt.AlignmentFlag.AlignCenter)

        hc_layout.addSpacing(8)

        # Dominant Primary Action Title ("Diktat starten")
        lang = get_current_language()
        cta_headline = "Diktat starten" if lang == "de" else "Start Dictation"
        self.lbl_hero_cta_title = QLabel(cta_headline)
        self.lbl_hero_cta_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hero_cta_title.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_DISPLAY}; font-size: 26px; font-weight: 700; "
            f"color: {ThemeColors.TEXT_PRIMARY}; letter-spacing: -0.4px; background: transparent; border: none;"
        )
        hc_layout.addWidget(self.lbl_hero_cta_title)

        hc_layout.addSpacing(2)

        # Tactile Keycap Badges Row (e.g. [Strg] + [Leertaste])
        self.hero_keycaps_layout = QHBoxLayout()
        self.hero_keycaps_layout.setContentsMargins(0, 2, 0, 2)
        self.hero_keycaps_layout.setSpacing(8)
        hc_layout.addLayout(self.hero_keycaps_layout)
        self._refresh_hero_keycaps()

        hc_layout.addSpacing(4)

        # Subtitle Instruction
        sub_text = (
            "Drücken, um mit der Spracherkennung zu beginnen."
            if lang == "de"
            else "Press to start speech recognition."
        )
        self.lbl_hero_sub = QLabel(sub_text)
        self.lbl_hero_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hero_sub.setWordWrap(True)
        self.lbl_hero_sub.setMinimumHeight(34)
        self.lbl_hero_sub.setStyleSheet(
            f"font-size: 12.5px; color: {ThemeColors.TEXT_MUTED}; font-weight: 400; background: transparent; border: none;"
        )
        hc_layout.addWidget(self.lbl_hero_sub)

        hc_layout.addStretch(1)

        self.studio_top_split.addWidget(self.hero_card, stretch=54)

        # --- RIGHT: Secondary Panel ("Letztes Diktat") ---
        self.trans_card = QFrame()
        self.trans_card.setObjectName("card")
        self.trans_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.trans_card.setMinimumHeight(250)
        self.trans_card.setStyleSheet(
            f"QFrame#card {{ "
            f"  background-color: {ThemeColors.BG_CARD}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_SHADOW_DARK}; "
            f"  border-radius: {ThemeMetrics.RADIUS_CARD_LARGE}; "
            f"}}"
        )
        tc_layout = QVBoxLayout(self.trans_card)
        tc_layout.setContentsMargins(22, 20, 22, 20)
        tc_layout.setSpacing(14)

        tc_top = QHBoxLayout()
        tc_top.setSpacing(8)
        self.tc_title = QLabel("Letztes Diktat" if lang == "de" else "Latest Dictation")
        self.tc_title.setObjectName("section_title")
        self.tc_title.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_DISPLAY}; font-size: 18px; font-weight: 700; "
            f"color: {ThemeColors.TEXT_PRIMARY}; letter-spacing: -0.2px; background: transparent; border: none;"
        )

        # Tactile Neomorphic Overflow Action Button ("[•••]")
        self.btn_latest_menu = QPushButton("•••")
        self.btn_latest_menu.setObjectName("btn_latest_menu")
        self.btn_latest_menu.setFixedSize(36, 32)
        self.btn_latest_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_latest_menu.setToolTip("Aktionen: Kopieren, Exportieren, Scratchpad, Details")
        self.btn_latest_menu.setStyleSheet(
            f"QPushButton#btn_latest_menu {{ "
            f"  background-color: {ThemeColors.BG_ELEVATED}; color: {ThemeColors.TEXT_SECONDARY}; "
            f"  font-size: 12px; font-weight: 700; border-radius: 9px; padding: 0px; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM}; "
            f"}} "
            f"QPushButton#btn_latest_menu:hover {{ "
            f"  background-color: {ThemeColors.BG_ELEVATED_HOVER}; color: {ThemeColors.TEXT_PRIMARY}; "
            f"}}"
        )
        self.btn_latest_menu.clicked.connect(self._show_latest_dictation_menu)

        tc_top.addWidget(self.tc_title)
        tc_top.addStretch()
        tc_top.addWidget(self.btn_latest_menu)
        tc_layout.addLayout(tc_top)

        # Unified Sunken Neomorphic Well for Latest Dictation Text + Waveform + Timestamps
        self.latest_text_well = QFrame()
        self.latest_text_well.setObjectName("sunken_well")
        self.latest_text_well.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.latest_text_well.setStyleSheet(get_sunken_qss("16px", "QFrame#sunken_well"))
        well_layout = QVBoxLayout(self.latest_text_well)
        well_layout.setContentsMargins(18, 16, 18, 14)
        well_layout.setSpacing(12)

        default_dict_de = (
            "Das ist ein kurzer Test meines Diktats. Die Spracherkennung funktioniert "
            "sehr gut und spart mir im Alltag viel Zeit. So kann ich meine Gedanken "
            "schnell und einfach festhalten."
        )
        default_dict_en = (
            "This is a short test of my dictation. Speech recognition works very well "
            "and saves me a lot of time every day. This way I can capture my thoughts "
            "quickly and easily."
        )
        self.lbl_latest_text = QLabel(default_dict_de if lang == "de" else default_dict_en)
        self.lbl_latest_text.setWordWrap(True)
        self.lbl_latest_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_latest_text.setMinimumHeight(60)
        self.lbl_latest_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_latest_text.setStyleSheet(
            f"font-size: 13.5px; color: {ThemeColors.TEXT_SECONDARY}; line-height: 155%; background: transparent; border: none;"
        )
        well_layout.addWidget(self.lbl_latest_text, stretch=1)

        # Subtle horizontal divider line inside the well
        well_div = QFrame()
        well_div.setFrameShape(QFrame.Shape.HLine)
        well_div.setFixedHeight(1)
        well_div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        well_layout.addWidget(well_div)

        # Violet/Indigo Audio Waveform + Timestamps row below
        self.latest_wave_well = QWidget()
        self.latest_wave_well.setStyleSheet("background: transparent; border: none;")
        wave_box = QVBoxLayout(self.latest_wave_well)
        wave_box.setContentsMargins(0, 2, 0, 0)
        wave_box.setSpacing(6)

        self.latest_static_wave = StaticDictationWaveformWidget(self)
        wave_box.addWidget(self.latest_static_wave)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_latest_time_start = QLabel("00:00")
        self.lbl_latest_time_start.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_MONO}; font-size: 11px; color: {ThemeColors.TEXT_DIM}; background: transparent;"
        )
        self.lbl_latest_time_end = QLabel("00:12")
        self.lbl_latest_time_end.setStyleSheet(
            f"font-family: {ThemeTypography.FONT_FAMILY_MONO}; font-size: 11px; color: {ThemeColors.TEXT_DIM}; background: transparent;"
        )
        time_row.addWidget(self.lbl_latest_time_start)
        time_row.addStretch()
        time_row.addWidget(self.lbl_latest_time_end)
        wave_box.addLayout(time_row)

        well_layout.addWidget(self.latest_wave_well)
        tc_layout.addWidget(self.latest_text_well, stretch=1)

        self.studio_top_split.addWidget(self.trans_card, stretch=46)
        root_layout.addLayout(self.studio_top_split, stretch=1)

        # ---------------------------------------------------------------------
        # 2. Compact Neomorphic Bottom Status Bar (Ready Dot, Language, Latency)
        # ---------------------------------------------------------------------
        self.studio_status_bar = QFrame()
        self.studio_status_bar.setObjectName("studio_status_bar")
        self.studio_status_bar.setFixedHeight(48)
        self.studio_status_bar.setStyleSheet(
            f"QFrame#studio_status_bar {{ "
            f"  background-color: {ThemeColors.BG_STATUS_BAR}; "
            f"  border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP}; "
            f"  border-left: 1px solid {ThemeColors.BORDER_SUBTLE}; "
            f"  border-right: 1px solid {ThemeColors.BORDER_BOTTOM}; "
            f"  border-bottom: 2px solid {ThemeColors.BORDER_BOTTOM}; "
            f"  border-radius: 14px; "
            f"}}"
        )
        sb_layout = QHBoxLayout(self.studio_status_bar)
        sb_layout.setContentsMargins(18, 6, 18, 6)
        sb_layout.setSpacing(12)

        # Glowing Mint/Green Readiness Dot + Label ("Bereit")
        self.status_dot = StatusGlowDotWidget(self)
        sb_layout.addWidget(self.status_dot)

        self.status_badge = QLabel(tr("ready"))
        self.status_badge.setStyleSheet(
            f"color: {ThemeColors.TEXT_PRIMARY}; font-size: 12.5px; font-weight: 600; background: transparent; border: none;"
        )
        sb_layout.addWidget(self.status_badge)

        sb_layout.addSpacing(8)
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedSize(1, 18)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.10); border: none;")
        sb_layout.addWidget(sep1)
        sb_layout.addSpacing(4)

        # Language Selector ("🌐 Deutsch ⌄")
        lang_label = "🌐 Deutsch (DE) ▾" if lang == "de" else "🌐 English (EN) ▾"
        self.btn_lang_toggle = LanguageSelectorButton(lang_label, self)
        self.btn_lang_toggle.setObjectName("btn_lang_toggle")
        self.btn_lang_toggle.setToolTip("Switch Interface Language (DE / EN)")
        self.btn_lang_toggle.clicked.connect(self._toggle_ui_language)
        sb_layout.addWidget(self.btn_lang_toggle)

        sb_layout.addStretch(1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedSize(1, 18)
        sep2.setStyleSheet("background-color: rgba(255, 255, 255, 0.10); border: none;")
        sb_layout.addWidget(sep2)
        sb_layout.addSpacing(4)

        # Right-aligned Latency Indicator with 5-bar Indigo Waveform Icon ("0,4 s Latenz")
        lat_default = "0,4 s Latenz" if lang == "de" else "0.4 s Latency"
        self.pill_latency = LatencyWaveBadgeButton(lat_default, self)
        self.pill_latency.setToolTip("System-, Engine- & Profil-Details anzeigen")
        self.pill_latency.clicked.connect(self._show_latest_dictation_menu)
        sb_layout.addWidget(self.pill_latency)

        root_layout.addWidget(self.studio_status_bar)

    # =========================================================================
    # TAB 2: LIBRARY, PROFILES & HISTORY (Diktate & Profilverwaltung)
    # =========================================================================

    def _setup_library_tab(self):
        tab_layout = QHBoxLayout(self.tab_library)
        tab_layout.setContentsMargins(0, 8, 0, 0)
        tab_layout.setSpacing(12)

        # Left Column (50%): Library & Profile Sub-Tabs (Fachwörterbuch / Sprach-Makros / Profile)
        left_card = QFrame()
        left_card.setObjectName("card")
        lc_layout = QVBoxLayout(left_card)
        lc_layout.setContentsMargins(16, 14, 16, 14)
        lc_layout.setSpacing(10)

        # Segmented Sub-View Switcher + Quick Scratchpad Access
        sub_nav = QHBoxLayout()
        sub_nav.setSpacing(4)

        pill_style = (
            f"QPushButton {{ background: transparent; color: {ThemeColors.TEXT_MUTED}; "
            f"font-weight: 600; font-size: 11.5px; border: none; border-radius: 6px; padding: 5px 12px; }} "
            f"QPushButton:checked {{ background-color: {ThemeColors.BG_CARD_ACTIVE}; color: {ThemeColors.TEXT_PRIMARY}; "
            f"border-top: 1px solid {ThemeColors.BORDER_SPECULAR_TOP_HERO}; border: 1px solid rgba(99, 102, 241, 0.45); }} "
            f"QPushButton:hover:!checked {{ color: #ffffff; background-color: rgba(255, 255, 255, 0.05); }}"
        )

        self.btn_sub_vocab = QPushButton(tr("tab_vocabulary"))
        self.btn_sub_vocab.setCheckable(True)
        self.btn_sub_vocab.setChecked(True)
        self.btn_sub_vocab.setStyleSheet(pill_style)
        self.btn_sub_vocab.clicked.connect(lambda: self._switch_library_subview(0))

        self.btn_sub_snippets = QPushButton(tr("tab_snippets"))
        self.btn_sub_snippets.setCheckable(True)
        self.btn_sub_snippets.setStyleSheet(pill_style)
        self.btn_sub_snippets.clicked.connect(lambda: self._switch_library_subview(1))

        self.btn_sub_apps = QPushButton(tr("tab_profiles"))
        self.btn_sub_apps.setCheckable(True)
        self.btn_sub_apps.setStyleSheet(pill_style)
        self.btn_sub_apps.clicked.connect(lambda: self._switch_library_subview(2))

        self.btn_hero_scratchpad = QPushButton(tr("hero_scratchpad_btn"))
        self.btn_hero_scratchpad.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hero_scratchpad.setObjectName("btn_secondary")
        self.btn_hero_scratchpad.clicked.connect(self._on_open_scratchpad_clicked)
        self.btn_sidebar_scratchpad = self.btn_hero_scratchpad

        sub_nav.addWidget(self.btn_sub_vocab)
        sub_nav.addWidget(self.btn_sub_snippets)
        sub_nav.addWidget(self.btn_sub_apps)
        sub_nav.addStretch()
        sub_nav.addWidget(self.btn_hero_scratchpad)
        lc_layout.addLayout(sub_nav)

        self.lib_stacked = QStackedWidget()

        # View 0: Custom Vocabulary
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

        # View 2: Profile Management (Operating Mode + Tone Profiles + Engine/STT Info + App-Profiles)
        app_widget = QWidget()
        aw_layout = QVBoxLayout(app_widget)
        aw_layout.setContentsMargins(0, 0, 0, 0)
        aw_layout.setSpacing(8)

        prof_scroll = QScrollArea()
        prof_scroll.setWidgetResizable(True)
        prof_scroll.setFrameShape(QFrame.Shape.NoFrame)
        prof_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        prof_scroll_content = QWidget()
        psc_layout = QVBoxLayout(prof_scroll_content)
        psc_layout.setContentsMargins(2, 2, 4, 8)
        psc_layout.setSpacing(14)

        # A. Engine, Whisper/Provider & Hardware Status Summary Strip
        sys_info_frame = QFrame()
        sys_info_frame.setStyleSheet(get_sunken_qss("10px", "QFrame"))
        sys_info_layout = QHBoxLayout(sys_info_frame)
        sys_info_layout.setContentsMargins(10, 8, 10, 8)
        sys_info_layout.setSpacing(8)

        pill_style_info = (
            f"background-color: {ThemeColors.BG_CARD}; color: {ThemeColors.TEXT_SECONDARY}; "
            f"font-size: 10.5px; font-weight: 600; padding: 3px 8px; border-radius: 6px; "
            f"border: 1px solid {ThemeColors.BORDER_SUBTLE};"
        )
        self.pill_hotkey = QLabel(tr("pill_hotkey", key=config.hotkey.key.upper()))
        self.pill_hotkey.setStyleSheet(pill_style_info)

        self.pill_engine = QLabel(tr("pill_engine", engine=config.formatting.engine.upper()))
        self.pill_engine.setStyleSheet(pill_style_info)

        active_provider = getattr(config.whisper, "provider", "local")
        if active_provider in ("grok", "groq"):
            prof_str = "GROK AI"
        elif active_provider == "openai":
            prof_str = "OPENAI"
        else:
            prof_str = config.whisper.profile.upper()

        self.pill_profile = QLabel(tr("pill_stt", stt=prof_str))
        self.pill_profile.setStyleSheet(pill_style_info)

        self.lbl_hw_badge = QLabel(self.hw_badge_text)
        self.lbl_hw_badge.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 10.5px; font-weight: 500; background: transparent;")

        self.privacy_badge = QLabel(tr("privacy_badge_text"))
        self.privacy_badge.setStyleSheet(
            f"background-color: {ThemeColors.SUCCESS_MUTED}; color: {ThemeColors.SUCCESS}; "
            f"font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 6px; "
            f"border: 1px solid {ThemeColors.SUCCESS_BORDER};"
        )
        self.privacy_badge.setVisible(getattr(config.system, "offline_privacy_mode", False))

        sys_info_layout.addWidget(self.pill_profile)
        sys_info_layout.addWidget(self.pill_engine)
        sys_info_layout.addWidget(self.pill_hotkey)
        sys_info_layout.addStretch()
        sys_info_layout.addWidget(self.lbl_hw_badge)
        sys_info_layout.addWidget(self.privacy_badge)
        psc_layout.addWidget(sys_info_frame)

        # B. Operating Mode Selection ("Flow-Modus" vs. "Rohdiktat")
        self.mode_card = QFrame()
        self.mode_card.setStyleSheet("QFrame { background: transparent; border: none; }")
        mc_layout = QVBoxLayout(self.mode_card)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.setSpacing(8)

        self.mc_title = QLabel(tr("section_mode_title"))
        self.mc_title.setObjectName("section_title")
        mc_layout.addWidget(self.mc_title)

        grid_mode = QGridLayout()
        grid_mode.setSpacing(10)

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
        psc_layout.addWidget(self.mode_card)

        # C. Tone & Style Profiles Grid (6 Presets)
        self.tone_section_card = QFrame()
        self.tone_section_card.setStyleSheet("QFrame { background: transparent; border: none; }")
        tc_layout_tone = QVBoxLayout(self.tone_section_card)
        tc_layout_tone.setContentsMargins(0, 2, 0, 0)
        tc_layout_tone.setSpacing(8)

        tone_top = QHBoxLayout()
        self.tone_title = QLabel(tr("tone_section_title"))
        self.tone_title.setObjectName("section_title")
        self.lbl_tone_status = QLabel(tr("tone_status_active") if active_mode == "flow" else tr("tone_status_inactive"))
        self.lbl_tone_status.setStyleSheet(
            f"color: {ThemeColors.ACCENT_INDIGO_BRIGHT}; font-size: 11px; font-weight: 600; "
            f"background-color: {ThemeColors.ACCENT_INDIGO_MUTED}; padding: 2px 9px; border-radius: 6px; "
            f"border: 1px solid {ThemeColors.ACCENT_INDIGO_BORDER};"
        )
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
            row = idx // 2
            col = idx % 2

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
        psc_layout.addWidget(self.tone_section_card)
        self.tone_section_card.setEnabled(active_mode == "flow")

        # D. App-Profile Context Rules
        self.lbl_app_info = QLabel(tr("app_rules_info"))
        self.lbl_app_info.setStyleSheet("color: #71717a; font-size: 11px;")
        psc_layout.addWidget(self.lbl_app_info)

        self.app_container = QWidget()
        self.app_list_layout = QVBoxLayout(self.app_container)
        self.app_list_layout.setContentsMargins(0, 2, 0, 0)
        self.app_list_layout.setSpacing(3)
        self.app_list_layout.addStretch()
        psc_layout.addWidget(self.app_container)

        psc_layout.addStretch()
        prof_scroll.setWidget(prof_scroll_content)
        aw_layout.addWidget(prof_scroll, stretch=1)

        self.lib_stacked.addWidget(app_widget)

        lc_layout.addWidget(self.lib_stacked)
        tab_layout.addWidget(left_card, stretch=5)

        # Right Column (50%): Dictation History + Quick Latest Actions
        self.lib_hist_card = QFrame()
        self.lib_hist_card.setObjectName("card")
        hc_layout = QVBoxLayout(self.lib_hist_card)
        hc_layout.setContentsMargins(16, 14, 16, 14)
        hc_layout.setSpacing(8)

        h_head = QHBoxLayout()
        self.lbl_history_title = QLabel(tr("history_title"))
        self.lbl_history_title.setObjectName("section_title")

        self.btn_copy_latest = QPushButton(tr("copy"))
        self.btn_copy_latest.setObjectName("btn_secondary")
        self.btn_copy_latest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_latest.clicked.connect(self._copy_latest_text)

        self.lbl_hist_count = QLabel(tr("history_entries_count", count=0))
        self.lbl_hist_count.setStyleSheet("color: #555562; font-size: 11px; font-weight: 400;")

        h_head.addWidget(self.lbl_history_title)
        h_head.addStretch()
        h_head.addWidget(self.btn_copy_latest)
        h_head.addWidget(self.lbl_hist_count)
        hc_layout.addLayout(h_head)

        h_status_row = QHBoxLayout()
        self.lbl_hero_action = QLabel(tr("hero_status_ready"))
        self.lbl_hero_action.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 11px; font-weight: 600;")

        self.lbl_latest_stats = QLabel(tr("latest_dictation_ready"))
        self.lbl_latest_stats.setStyleSheet(f"color: {ThemeColors.TEXT_DIM}; font-size: 11px;")

        h_status_row.addWidget(self.lbl_hero_action)
        h_status_row.addStretch()
        h_status_row.addWidget(self.lbl_latest_stats)
        hc_layout.addLayout(h_status_row)

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

        tab_layout.addWidget(self.lib_hist_card, stretch=5)

        self._refresh_vocab_list()
        self._refresh_snippets_list()
        self._refresh_app_rules_list()

    def _switch_library_subview(self, idx: int):
        self.btn_sub_vocab.setChecked(idx == 0)
        self.btn_sub_snippets.setChecked(idx == 1)
        self.btn_sub_apps.setChecked(idx == 2)
        self.lib_stacked.setCurrentIndex(idx)
        if hasattr(self, "lib_hist_card"):
            self.lib_hist_card.setVisible(idx != 2)
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 1:
            self._active_sidebar_item = 2 if idx == 2 else 1
            self._update_sidebar_nav_styles_by_button(self._active_sidebar_item)

    # =========================================================================
    # TAB 3: SETTINGS (System-Konfiguration & Hardware)
    # =========================================================================

    def _setup_settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.all_disclosure_sections = []
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

        # 5. Wireless Mobile LAN Bridge (Progressive Disclosure Section)
        mob_active = getattr(config.mobile_bridge, "enabled", False)
        self.sub_mob_bridge = SettingsDisclosureSection(
            tr("lbl_mobile_bridge"),
            summary=tr("lbl_mobile_active") if mob_active else tr("lbl_mobile_inactive"),
            is_expanded=False,
            parent=self.card_audio,
        )
        self.all_disclosure_sections.append(self.sub_mob_bridge)
        disc_audio_layout = self.sub_mob_bridge.body_layout

        self.chk_mobile_bridge = QCheckBox(tr("lbl_mobile_bridge"))
        self.chk_mobile_bridge.setChecked(mob_active)
        self.chk_mobile_bridge.toggled.connect(self._on_mobile_bridge_toggled)
        disc_audio_layout.addWidget(self.chk_mobile_bridge)

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

        self.lbl_mobile_status = QLabel(tr("lbl_mobile_active") if mob_active else tr("lbl_mobile_inactive"))
        self.lbl_mobile_status.setStyleSheet("font-size: 11px; color: #10b981;" if mob_active else "font-size: 11px; color: #71717a;")
        mob_opt_layout.addWidget(self.lbl_mobile_status)

        self.lbl_mob_hint = QLabel(tr("lbl_mobile_hint"))
        self.lbl_mob_hint.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.3;")
        self.lbl_mob_hint.setWordWrap(True)
        mob_opt_layout.addWidget(self.lbl_mob_hint)

        self.chk_mobile_bridge.toggled.connect(self.mob_options_widget.setEnabled)
        self.mob_options_widget.setEnabled(mob_active)
        disc_audio_layout.addWidget(self.mob_options_widget)

        aud_layout.addWidget(self.sub_mob_bridge)

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

        # Whisper Model Storage & Downloader Frame (Progressive Disclosure Section)
        self.model_storage_frame = SettingsDisclosureSection(
            tr("lbl_models_storage"),
            summary="",
            is_expanded=False,
            parent=self.card_stt,
        )
        self.all_disclosure_sections.append(self.model_storage_frame)
        ms_layout = self.model_storage_frame.body_layout
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

        # Sub-Model Quick-Chips Bar for Active Tier
        self.sub_model_bar = QWidget()
        self.sub_model_bar.setStyleSheet("background: transparent; margin-top: 3px; margin-bottom: 3px;")
        sub_m_layout = QHBoxLayout(self.sub_model_bar)
        sub_m_layout.setContentsMargins(2, 0, 2, 0)
        sub_m_layout.setSpacing(8)

        self.lbl_sub_models_title = QLabel(tr("lbl_tier_models_available"))
        self.lbl_sub_models_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #a1a1aa; min-width: 130px;")
        sub_m_layout.addWidget(self.lbl_sub_models_title)

        self.sub_model_chips_container = QWidget()
        self.chips_h_layout = QHBoxLayout(self.sub_model_chips_container)
        self.chips_h_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_h_layout.setSpacing(6)
        sub_m_layout.addWidget(self.sub_model_chips_container, stretch=1)

        u_layout.addWidget(self.sub_model_bar)

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
        cur_u_model = getattr(config.formatting, "model", "google/gemini-2.5-flash")
        self.lbl_det_model = QLabel(cur_u_model)
        self.lbl_det_model.setStyleSheet("font-size: 11px; color: #ffffff; font-weight: 600;")
        self._update_sub_model_chips(get_tier_for_model(cur_u_model) or "speed", cur_u_model)

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

        # Custom / Catalog Frame (Progressive Disclosure Section)
        self.custom_catalog_frame = SettingsDisclosureSection(
            tr("btn_toggle_custom_catalog"),
            summary="OpenRouter / Custom Endpunkte",
            is_expanded=False,
            parent=self.card_fmt,
        )
        self.all_disclosure_sections.append(self.custom_catalog_frame)
        cat_layout = self.custom_catalog_frame.body_layout
        cat_layout.setContentsMargins(10, 8, 10, 8)
        cat_layout.setSpacing(8)

        row_u_model = QHBoxLayout()
        self.lbl_u_model = QLabel(tr("lbl_u_model_catalog"))
        self.lbl_u_model.setStyleSheet("font-weight: 500; min-width: 150px; color: #9d9da8; font-size: 11.5px;")
        self.combo_u_model = QComboBox()
        self.combo_u_model.setEditable(True)
        self._populate_curated_models_in_combo()
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
        self.custom_catalog_frame.toggled.connect(lambda exp: self.btn_toggle_custom_catalog.setText(tr("btn_hide_custom_catalog") if exp else tr("btn_toggle_custom_catalog")))
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

        # Collapsible Advanced Formatting Options (Progressive Disclosure Section)
        self.adv_formatting_frame = SettingsDisclosureSection(
            tr("btn_toggle_adv_formatting"),
            summary="7 Automations-Regeln",
            is_expanded=False,
            parent=self.card_fmt,
        )
        self.all_disclosure_sections.append(self.adv_formatting_frame)
        adv_layout = self.adv_formatting_frame.body_layout
        adv_layout.setContentsMargins(10, 8, 10, 8)
        adv_layout.setSpacing(8)

        self.btn_toggle_adv_formatting = QPushButton(tr("btn_toggle_adv_formatting"))
        self.btn_toggle_adv_formatting.setObjectName("btn_secondary")
        self.btn_toggle_adv_formatting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_adv_formatting.setStyleSheet("font-size: 11px; padding: 4px 10px; margin-top: 4px;")
        self.btn_toggle_adv_formatting.clicked.connect(self._toggle_advanced_formatting)
        self.adv_formatting_frame.toggled.connect(lambda exp: self.btn_toggle_adv_formatting.setText(tr("btn_hide_adv_formatting") if exp else tr("btn_toggle_adv_formatting")))
        lc_layout.addWidget(self.btn_toggle_adv_formatting)

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

        cur_lang_hud = getattr(config.system, "ui_language", "en")
        self.hud_sliders_frame = SettingsDisclosureSection(
            "HUD-Physik & Glas-Schieberegler" if cur_lang_hud == "de" else "HUD Physics & Glass Sliders",
            summary=f"Deckkraft {getattr(config.hud, 'opacity_percent', 78)}% · Bounce {getattr(config.hud, 'bounce_intensity', 50)}% · Skalierung {getattr(config.hud, 'scale_percent', 100)}%",
            is_expanded=False,
            parent=self.card_hud,
        )
        self.all_disclosure_sections.append(self.hud_sliders_frame)
        hud_sliders_layout = self.hud_sliders_frame.body_layout
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

        hopt_layout.addWidget(self.hud_sliders_frame)

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

        # Developer & Diagnostics Disclosure Section (Progressive Disclosure)
        self.dev_options_frame = SettingsDisclosureSection(
            "Entwickler- & Diagnoseoptionen" if cur_lang == "de" else "Developer Options & Diagnostics",
            summary="Hardware-Diagnose & Zwischenablage" if cur_lang == "de" else "Hardware Diagnostics & Clipboard",
            is_expanded=False,
            parent=self.card_adv,
        )
        self.all_disclosure_sections.append(self.dev_options_frame)
        dev_layout = self.dev_options_frame.body_layout
        dev_layout.setContentsMargins(10, 8, 10, 8)
        dev_layout.setSpacing(8)

        self.chk_restore_clip = QCheckBox(tr("lbl_restore_clipboard"))
        self.chk_restore_clip.setChecked(getattr(config.injection, "restore_clipboard", False))
        self.chk_restore_clip.toggled.connect(self._on_restore_clip_toggled)
        dev_layout.addWidget(self.chk_restore_clip)

        self.lbl_diag = QLabel(tr("lbl_hardware_diag", hw=self.hw_badge_text))
        self.lbl_diag.setStyleSheet("font-size: 11px; color: #555562; margin-top: 4px;")
        dev_layout.addWidget(self.lbl_diag)

        adv_card_layout.addWidget(self.dev_options_frame)

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
        cur_lang = get_current_language()
        self.setWindowTitle(tr("app_title"))
        if hasattr(self, "tabs"):
            self.tabs.setTabText(0, tr("tab_dashboard"))
            self.tabs.setTabText(1, tr("tab_library_combined"))
            self.tabs.setTabText(2, tr("tab_settings"))
        if hasattr(self, "sidebar_nav_buttons"):
            if len(self.sidebar_nav_buttons) >= 4:
                self.sidebar_nav_buttons[0].setText("  Studio")
                self.sidebar_nav_buttons[1].setText("  Diktate" if cur_lang == "de" else "  Dictations")
                self.sidebar_nav_buttons[2].setText("  Profile" if cur_lang == "de" else "  Profiles")
                self.sidebar_nav_buttons[3].setText(f"  {tr('tab_settings')}")
            elif len(self.sidebar_nav_buttons) >= 3:
                self.sidebar_nav_buttons[0].setText(f"  {tr('tab_dashboard')}")
                self.sidebar_nav_buttons[1].setText(f"  {tr('tab_library_combined')}")
                self.sidebar_nav_buttons[2].setText(f"  {tr('tab_settings')}")

        # Studio Tab Hero & Status
        if hasattr(self, "lbl_hero_cta_title") and not getattr(self.hero_waveform, "is_recording", False):
            self.lbl_hero_cta_title.setText("Diktat starten" if cur_lang == "de" else "Start Dictation")

        self._refresh_hero_keycaps()

        if hasattr(self, "lbl_hero_action") and not getattr(self.hero_waveform, "is_recording", False):
            self.lbl_hero_action.setText(tr("hero_status_ready"))
            self.lbl_hero_sub.setText(
                "Drücken, um mit der Spracherkennung zu beginnen."
                if cur_lang == "de"
                else "Press to start speech recognition."
            )

        if hasattr(self, "status_badge") and not getattr(self.hero_waveform, "is_recording", False):
            self.status_badge.setText(tr("ready"))
        if hasattr(self, "status_dot") and not getattr(self.hero_waveform, "is_recording", False):
            self.status_dot.set_color("#34d399")

        if hasattr(self, "privacy_badge"):
            self.privacy_badge.setText(tr("privacy_badge_text"))

        if hasattr(self, "btn_hero_scratchpad"):
            self.btn_hero_scratchpad.setText(tr("hero_scratchpad_btn"))

        # Studio Latest Transcription Card
        if hasattr(self, "tc_title"):
            self.tc_title.setText("Letztes Diktat" if cur_lang == "de" else "Latest Dictation")
        if hasattr(self, "btn_copy_latest"):
            self.btn_copy_latest.setText(tr("copy"))

        # Profile Tab Section Titles & Mode Cards
        if hasattr(self, "mc_title"):
            self.mc_title.setText(tr("section_mode_title"))
        if hasattr(self, "mode_cards"):
            if "flow" in self.mode_cards:
                self.mode_cards["flow"].lbl_title.setText(tr("mode_flow_title"))
                self.mode_cards["flow"].lbl_sub.setText(tr("mode_flow_desc"))
            if "raw" in self.mode_cards:
                self.mode_cards["raw"].lbl_title.setText(tr("mode_raw_title"))
                self.mode_cards["raw"].lbl_sub.setText(tr("mode_raw_desc"))

        # Profile Tab Tone Section & Cards
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

        if hasattr(self, "lbl_sub_models_title"):
            self.lbl_sub_models_title.setText(tr("lbl_tier_models_available"))

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

        # Retranslate Progressive Disclosure Sections
        lang = lang_code or get_current_language()
        if hasattr(self, "sub_mob_bridge") and hasattr(self.sub_mob_bridge, "set_title"):
            self.sub_mob_bridge.set_title(tr("lbl_mobile_bridge"))
            mob_on = getattr(config.mobile_bridge, "enabled", False)
            self.sub_mob_bridge.set_summary(tr("lbl_mobile_active") if mob_on else tr("lbl_mobile_inactive"))

        if hasattr(self, "model_storage_frame") and hasattr(self.model_storage_frame, "set_title"):
            self.model_storage_frame.set_title(tr("lbl_models_storage"))

        if hasattr(self, "custom_catalog_frame") and hasattr(self.custom_catalog_frame, "set_title"):
            self.custom_catalog_frame.set_title(tr("btn_toggle_custom_catalog"))

        if hasattr(self, "adv_formatting_frame") and hasattr(self.adv_formatting_frame, "set_title"):
            self.adv_formatting_frame.set_title(tr("btn_toggle_adv_formatting"))

        if hasattr(self, "hud_sliders_frame") and hasattr(self.hud_sliders_frame, "set_title"):
            self.hud_sliders_frame.set_title("HUD-Physik & Glas-Schieberegler" if lang == "de" else "HUD Physics & Glass Sliders")

        if hasattr(self, "dev_options_frame") and hasattr(self.dev_options_frame, "set_title"):
            self.dev_options_frame.set_title("Entwickler- & Diagnoseoptionen" if lang == "de" else "Developer Options & Diagnostics")
            if hasattr(self.dev_options_frame, "set_summary"):
                self.dev_options_frame.set_summary("Hardware-Diagnose & Zwischenablage" if lang == "de" else "Hardware Diagnostics & Clipboard")

        if hasattr(self, "btn_lang_toggle"):
            lang_lbl = "🌐 Deutsch (DE) ▾" if get_current_language() == "de" else "🌐 English (EN) ▾"
            self.btn_lang_toggle.setText(lang_lbl)
            self.btn_lang_toggle.update()

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
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#ff6b47")
        self.status_badge.setText(tr("listening"))
        self.lbl_hero_action.setText(tr("hero_status_recording"))
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {ThemeColors.ACCENT_CORAL_HOVER};")
        if hasattr(self, "lbl_hero_cta_title"):
            self.lbl_hero_cta_title.setText(tr("listening"))
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("recording")
        self.hero_waveform.set_state("recording")

    def _on_rec_stopped(self):
        self.hero_waveform.set_state("idle")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("idle")
        if hasattr(self, "lbl_hero_cta_title"):
            self.lbl_hero_cta_title.setText("Diktat starten" if get_current_language() == "de" else "Start Dictation")

    def _on_rec_cancelled(self):
        self.hero_waveform.set_state("idle")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("idle")
        if hasattr(self, "lbl_hero_cta_title"):
            self.lbl_hero_cta_title.setText("Diktat starten" if get_current_language() == "de" else "Start Dictation")
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#34d399")
        self.status_badge.setText(tr("ready"))
        self.lbl_hero_action.setText(tr("hero_status_ready"))
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {ThemeColors.TEXT_MUTED};")

    def _on_audio_level(self, rms: float):
        self.hero_waveform.set_level(rms)
        if hasattr(self, "calib_meter"):
            self.calib_meter.update_level(rms)

    def _on_transcribe_started(self):
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#818cf8")
        self.status_badge.setText(tr("processing"))
        self.lbl_hero_action.setText(tr("hero_status_processing"))
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {ThemeColors.ACCENT_INDIGO_BRIGHT};")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("transcribing")
        self.hero_waveform.set_state("transcribing")

    def _on_formatting_started(self):
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#a78bfa")
        self.status_badge.setText(tr("formatting"))
        self.lbl_hero_action.setText(tr("formatting"))
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {ThemeColors.PURPLE};")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("formatting")
        self.hero_waveform.set_state("transcribing")

    def _on_transcribe_completed(self, data: Dict):
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#34d399")
        self.status_badge.setText(tr("ready"))
        self.lbl_hero_action.setText(tr("injected"))
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {ThemeColors.SUCCESS};")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("idle")
        if hasattr(self, "lbl_hero_cta_title"):
            self.lbl_hero_cta_title.setText("Diktat starten" if get_current_language() == "de" else "Start Dictation")
        self.hero_waveform.set_state("idle")

        text = data.get("text", "")
        latency = data.get("latency", 0.0)

        if text.strip():
            self.lbl_latest_text.setText(text.strip())
            self.lbl_latest_text.setStyleSheet(
                f"font-size: 13.5px; color: {ThemeColors.TEXT_SECONDARY}; font-weight: 400; line-height: 155%; background: transparent;"
            )

            words = len(text.strip().split())
            word_label = "words" if get_current_language() == "en" else "Wörter"
            self.lbl_latest_stats.setText(f"{words} {word_label} · {latency:.2f}s")
            if get_current_language() == "de":
                lat_fmt = f"{latency:.1f}".replace(".", ",")
                self.pill_latency.setText(f"{lat_fmt} s Latenz")
            else:
                self.pill_latency.setText(f"{latency:.1f} s Latency")
            self.pill_latency.update()
            if hasattr(self, "lbl_latest_time_end"):
                est_secs = max(1, min(59, int(round(words * 0.42))))
                self.lbl_latest_time_end.setText(f"00:{est_secs:02d}")
            self._add_to_history(text, latency)

    def _on_transcribe_failed(self, err_msg: str):
        if hasattr(self, "status_dot"):
            self.status_dot.set_color("#ef4444")
        self.status_badge.setText(tr("transcription_failed"))
        self.lbl_hero_action.setText(f"{tr('transcription_failed')}: {err_msg}")
        self.lbl_hero_action.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {ThemeColors.ERROR};")
        if hasattr(self, "btn_hero_record_cta"):
            self.btn_hero_record_cta.set_dictation_state("idle")
        if hasattr(self, "lbl_hero_cta_title"):
            self.lbl_hero_cta_title.setText("Diktat starten" if get_current_language() == "de" else "Start Dictation")
        self.hero_waveform.set_state("idle")

    def _copy_latest_text(self):
        txt = self.lbl_latest_text.text().strip('"\n\r ')
        if txt and not txt.startswith("Press ") and not txt.startswith("Drücke "):
            if safe_clipboard_copy(txt):
                self.btn_copy_latest.setText(tr("copied"))
                QTimer.singleShot(1500, lambda: self.btn_copy_latest.setText(tr("copy")))

    def _on_restore_clip_toggled(self, checked: bool):
        config.injection.restore_clipboard = checked
        config.save()
        if hasattr(self, "injector") and self.injector:
            self.injector.restore_clipboard = checked

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
            self._refresh_hero_keycaps()
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

    def _populate_curated_models_in_combo(self):
        """Populates combo_u_model with the curated 3-tier models grouped by tier."""
        self.combo_u_model.blockSignals(True)
        self.combo_u_model.clear()

        tiers = MODEL_TIERS
        tier_icons = [
            ("speed", tr("prio_speed_title") + " (< 250 ms)"),
            ("balanced", tr("prio_balanced_title") + " (300 - 500 ms)"),
            ("quality", tr("prio_quality_title") + " (1 - 2 s)"),
        ]

        for t_key, t_title in tier_icons:
            t_data = tiers.get(t_key, {})
            model_list = t_data.get("models", [])
            if model_list:
                self.combo_u_model.addItem(f"--- {t_title} ---", "")
                for m_id in model_list:
                    spec = CURATED_MODELS_SPECS.get(m_id, {})
                    m_name = spec.get("name", m_id)
                    self.combo_u_model.addItem(f"{m_id} — {m_name}", m_id)

        cur_m = getattr(config.formatting, "model", "google/gemini-2.5-flash")
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

    def _update_sub_model_chips(self, tier_key: str, active_model_id: str):
        """Updates the visible sub-model pill chips for the active tier."""
        if not hasattr(self, "chips_h_layout"):
            return

        while self.chips_h_layout.count() > 0:
            item = self.chips_h_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        tier_data = MODEL_TIERS.get(tier_key, {})
        model_list = tier_data.get("models", [])
        if not model_list:
            model_list = MODEL_TIERS.get("speed", {}).get("models", [])

        chip_short_names = {
            "google/gemini-2.5-flash": "Gemini 2.5 Flash",
            "google/gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "openai/gpt-4o-mini": "GPT-4o-mini",
            "meta-llama/llama-3.3-70b-instruct": "Llama 3.3 70B",
            "deepseek/deepseek-chat": "DeepSeek V3",
            "mistralai/mistral-small-24b-instruct-2501": "Mistral Small 3",
            "anthropic/claude-3-haiku": "Claude 3 Haiku",
            "qwen/qwen-2.5-72b-instruct": "Qwen 2.5 72B",
            "openai/gpt-4o": "OpenAI GPT-4o",
            "anthropic/claude-sonnet-4": "Claude Sonnet 4",
        }

        chip_short_prices = {
            "google/gemini-2.5-flash": "$0.30/1M",
            "google/gemini-2.5-flash-lite": "$0.10/1M",
            "openai/gpt-4o-mini": "$0.15/1M",
            "meta-llama/llama-3.3-70b-instruct": "$0.71/1M",
            "deepseek/deepseek-chat": "$0.26/1M",
            "mistralai/mistral-small-24b-instruct-2501": "$0.07/1M",
            "anthropic/claude-3-haiku": "$0.25/1M",
            "qwen/qwen-2.5-72b-instruct": "$0.36/1M",
            "openai/gpt-4o": "$2.50/1M",
            "anthropic/claude-sonnet-4": "$3.00/1M",
        }

        self.sub_model_chips = {}
        for m_id in model_list:
            lbl = chip_short_names.get(m_id, m_id.split("/")[-1])
            price = chip_short_prices.get(m_id, "")
            chip = SubModelChip(model_id=m_id, label=lbl, price_badge=price, parent=self)
            is_active = (m_id.lower() == (active_model_id or "").lower())
            chip.set_selected(is_active)
            chip.clicked.connect(lambda _, mid=m_id: self._on_sub_model_chip_clicked(mid))
            self.chips_h_layout.addWidget(chip)
            self.sub_model_chips[m_id] = chip

        self.chips_h_layout.addStretch()

    def _on_sub_model_chip_clicked(self, model_id: str):
        """Handler when clicking a sub-model pill chip."""
        config.formatting.model = model_id
        config.formatting.openrouter_model = model_id
        config.save()
        self.ai_formatter.model = model_id
        self.ai_formatter.openrouter_model = model_id

        if hasattr(self, "sub_model_chips"):
            for m_id, chip in self.sub_model_chips.items():
                chip.set_selected(m_id.lower() == model_id.lower())

        tier_key = get_tier_for_model(model_id) or "speed"
        self._sync_priority_cards_ui(model_id)

        self.combo_u_model.blockSignals(True)
        matched = -1
        for idx in range(self.combo_u_model.count()):
            if self.combo_u_model.itemData(idx) == model_id:
                matched = idx
                break
        if matched >= 0:
            self.combo_u_model.setCurrentIndex(matched)
        else:
            self.combo_u_model.setEditText(model_id)
        self.combo_u_model.blockSignals(False)

        self._update_model_details_ui(model_id)
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

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

        self._sync_priority_cards_ui(m_id)
        self._update_sub_model_chips(tier_key, m_id)

        self.combo_u_model.blockSignals(True)
        matched = -1
        for idx in range(self.combo_u_model.count()):
            if self.combo_u_model.itemData(idx) == m_id:
                matched = idx
                break
        if matched >= 0:
            self.combo_u_model.setCurrentIndex(matched)
        else:
            self.combo_u_model.setEditText(m_id)
        self.combo_u_model.blockSignals(False)

        self._update_model_details_ui(m_id)
        if hasattr(self, "card_llm"):
            self._update_settings_summaries()

    def _sync_priority_cards_ui(self, current_model: str):
        matched_tier = get_tier_for_model(current_model) or "speed"
        for k in ("speed", "balanced", "quality"):
            card = self.priority_cards.get(k)
            if not card:
                continue
            card.set_selected(k == matched_tier)

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
        if hasattr(self, "custom_catalog_frame"):
            if hasattr(self.custom_catalog_frame, "toggle"):
                self.custom_catalog_frame.toggle()
                is_vis = self.custom_catalog_frame.is_expanded
            else:
                is_vis = not self.custom_catalog_frame.isHidden()
                self.custom_catalog_frame.setVisible(not is_vis)
            if hasattr(self, "btn_toggle_custom_catalog"):
                self.btn_toggle_custom_catalog.setText(tr("btn_hide_custom_catalog") if is_vis else tr("btn_toggle_custom_catalog"))

    def _toggle_advanced_formatting(self):
        if hasattr(self, "adv_formatting_frame"):
            if hasattr(self.adv_formatting_frame, "toggle"):
                self.adv_formatting_frame.toggle()
                is_vis = self.adv_formatting_frame.is_expanded
            else:
                is_vis = not self.adv_formatting_frame.isHidden()
                self.adv_formatting_frame.setVisible(not is_vis)
            if hasattr(self, "btn_toggle_adv_formatting"):
                self.btn_toggle_adv_formatting.setText(tr("btn_hide_adv_formatting") if is_vis else tr("btn_toggle_adv_formatting"))

    def _expand_all_settings(self):
        """Expands all 7 settings cards and all nested progressive disclosure sub-accordions."""
        for card in getattr(self, "all_settings_cards", []):
            card.set_expanded(True)
        for disc in getattr(self, "all_disclosure_sections", []):
            if hasattr(disc, "set_expanded"):
                disc.set_expanded(True)

    def _collapse_all_settings(self):
        """Collapses all 7 settings cards and all nested progressive disclosure sub-accordions."""
        for card in getattr(self, "all_settings_cards", []):
            card.set_expanded(False)
        for disc in getattr(self, "all_disclosure_sections", []):
            if hasattr(disc, "set_expanded"):
                disc.set_expanded(False)

    def _on_settings_search_changed(self, raw_query: str):
        """
        Deep recursive search filtering across primary cards and nested disclosure sections.
        Unhides matching cards, expands matching sub-accordions, and safely handles regex tokens.
        Bilingual synonym normalization ensures queries match across German and English interfaces.
        """
        clean_query = raw_query.strip().lower()
        cards = getattr(self, "all_settings_cards", [])
        disclosures = getattr(self, "all_disclosure_sections", [])

        if not clean_query:
            for card in cards:
                card.setVisible(True)
                card.set_expanded(False)
            if hasattr(self, "card_audio"):
                self.card_audio.set_expanded(True)
            for disc in disclosures:
                if hasattr(disc, "set_expanded"):
                    disc.set_expanded(False)
            return

        SEARCH_SYNONYMS = {
            "mikrofon": ["mikrofon", "microphone", "mic", "input", "gain", "eingang", "pegelerhöhung", "audio", "sound"],
            "microphone": ["mikrofon", "microphone", "mic", "input", "gain", "eingang", "audio", "sound"],
            "hotkey": ["hotkey", "tastenkürzel", "shortcut", "taste", "drücken", "toggle", "ptt"],
            "tastenkürzel": ["hotkey", "tastenkürzel", "shortcut", "taste", "drücken", "toggle", "ptt"],
            "lautstärke": ["lautstärke", "volume", "sound", "ton", "audio"],
            "volume": ["lautstärke", "volume", "sound", "ton", "audio"],
            "spracherkennung": ["spracherkennung", "speech", "whisper", "stt", "model", "modell"],
            "speech": ["spracherkennung", "speech", "whisper", "stt", "model", "modell"],
            "formatierung": ["formatierung", "formatting", "ai", "ki", "llm", "engine"],
            "formatting": ["formatierung", "formatting", "ai", "ki", "llm", "engine"],
            "bridge": ["bridge", "lan", "mobile", "server", "port", "qr", "token"],
            "lan": ["bridge", "lan", "mobile", "server", "port"],
            "storage": ["storage", "speicher", "speicherpfad", "disk", "whisper", "download"],
            "speicher": ["storage", "speicher", "speicherpfad", "disk", "whisper", "download"],
            "catalog": ["catalog", "katalog", "regeln", "prompt", "vokabular", "vocabulary", "custom"],
            "katalog": ["catalog", "katalog", "regeln", "prompt", "vokabular", "vocabulary", "custom"],
            "opacity": ["opacity", "transparenz", "deckkraft", "slider"],
            "transparenz": ["opacity", "transparenz", "deckkraft", "slider"],
            "scale": ["scale", "skalierung", "größe", "size"],
            "skalierung": ["scale", "skalierung", "größe", "size"],
            "cache": ["cache", "zwischenspeicher", "log", "protokoll", "reset", "zurücksetzen", "diagnose"],
            "zwischenspeicher": ["cache", "zwischenspeicher", "log", "protokoll", "reset", "zurücksetzen", "diagnose"],
        }

        words = clean_query.split()
        search_tokens = [clean_query] + [w for w in words if len(w) > 1]
        for syn_key, syn_vals in SEARCH_SYNONYMS.items():
            if clean_query == syn_key or syn_key in clean_query or any(clean_query == v for v in syn_vals) or any(w in syn_vals for w in words):
                for v in syn_vals:
                    if v not in search_tokens:
                        search_tokens.append(v)

        CARD_SYNONYMS = {
            getattr(self, "card_audio", None): {"audio", "sound", "mikrofon", "microphone", "mic", "pegel", "gain", "lautstärke", "volume", "ducking", "lan", "bridge", "mobile"},
            getattr(self, "card_stt", None): {"stt", "spracherkennung", "speech", "whisper", "model", "modell", "vram", "halluzination", "hallucination", "temp", "temperature", "prompt", "storage", "speicher"},
            getattr(self, "card_fmt", None): {"formatting", "formatierung", "ai", "ki", "llm", "engine", "ollama", "openai", "gemini", "groq", "universal", "system-prompt", "tone", "stil", "katalog", "catalog", "regeln"},
            getattr(self, "card_hk", None): {"hotkey", "shortcut", "taste", "tastenkürzel", "f8", "ptt", "toggle", "push to talk", "rückgängig", "undo", "scratchpad"},
            getattr(self, "card_hud", None): {"hud", "floating", "overlay", "pill", "waveform", "visualizer", "position", "opacity", "transparenz", "skalierung", "scale"},
            getattr(self, "card_gen", None): {"general", "allgemein", "autostart", "sound", "klänge", "cue", "minimized", "minimiert"},
            getattr(self, "card_adv", None): {"system", "advanced", "erweitert", "cache", "zwischenspeicher", "export", "backup", "log", "reset", "zurücksetzen", "datenschutz", "privacy"},
        }

        DISC_SYNONYMS = {
            getattr(self, "sub_mob_bridge", None): {"bridge", "lan", "mobile", "server", "port", "qr", "token"},
            getattr(self, "model_storage_frame", None): {"storage", "speicher", "speicherpfad", "disk", "whisper", "download"},
            getattr(self, "custom_catalog_frame", None): {"catalog", "katalog", "regeln", "prompt", "vokabular", "vocabulary", "custom"},
            getattr(self, "adv_formatting_frame", None): {"markdown", "filler", "füllwörter", "seeding", "context", "kontext", "formatting", "formatierung"},
            getattr(self, "hud_sliders_frame", None): {"hud", "opacity", "transparenz", "deckkraft", "scale", "skalierung", "bounce", "slider"},
            getattr(self, "dev_options_frame", None): {"dev", "entwickler", "cache", "zwischenspeicher", "log", "protokoll", "reset", "zurücksetzen", "diagnose"},
        }

        for card in cards:
            card_matches = False
            matched_disclosures_in_card = []

            # 1. Direct synonym match for card
            card_syns = CARD_SYNONYMS.get(card, set())
            if any(tok in card_syns for tok in search_tokens):
                card_matches = True

            # 2. Inspect Card Header (Title, Description, Summary)
            if not card_matches:
                t_lower = card.lbl_title.text().lower()
                d_lower = card.lbl_desc.text().lower() if card.lbl_desc else ""
                s_lower = card.lbl_summary.text().lower() if card.lbl_summary else ""
                if any(tok in t_lower or tok in d_lower or tok in s_lower for tok in search_tokens):
                    card_matches = True

            # 3. Inspect Child Disclosure Sections Belonging to this Card
            child_disclosures = [d for d in disclosures if card.isAncestorOf(d) or card == d.parent()]
            for disc in child_disclosures:
                disc_matches = False
                disc_syns = DISC_SYNONYMS.get(disc, set())
                if any(tok in disc_syns for tok in search_tokens):
                    disc_matches = True
                if not disc_matches and hasattr(disc, "lbl_title") and any(tok in disc.lbl_title.text().lower() for tok in search_tokens):
                    disc_matches = True
                if not disc_matches and hasattr(disc, "lbl_summary") and any(tok in disc.lbl_summary.text().lower() for tok in search_tokens):
                    disc_matches = True

                # Check child controls inside the disclosure body
                body = getattr(disc, "body_widget", disc)
                if not disc_matches:
                    for child in body.findChildren((QLabel, QCheckBox, QPushButton, QLineEdit, QComboBox)):
                        if isinstance(child, (QLabel, QCheckBox, QPushButton)) and any(tok in child.text().lower() for tok in search_tokens):
                            disc_matches = True
                            break
                        elif isinstance(child, QLineEdit):
                            ph = child.placeholderText().lower()
                            val = child.text().lower()
                            if any(tok in ph or tok in val for tok in search_tokens):
                                disc_matches = True
                                break
                        elif isinstance(child, QComboBox):
                            items_text = " ".join(child.itemText(i) for i in range(child.count())).lower()
                            cur_t = child.currentText().lower()
                            if any(tok in items_text or tok in cur_t for tok in search_tokens):
                                disc_matches = True
                                break

                if disc_matches:
                    matched_disclosures_in_card.append(disc)
                    card_matches = True

            # 4. Inspect All Other Controls in card.body_widget (excluding disclosures)
            if not card_matches:
                for child in card.body_widget.findChildren((QLabel, QCheckBox, QPushButton, QLineEdit, QComboBox)):
                    if any(d.isAncestorOf(child) for d in child_disclosures):
                        continue
                    if isinstance(child, (QLabel, QCheckBox, QPushButton)) and any(tok in child.text().lower() for tok in search_tokens):
                        card_matches = True
                        break
                    elif isinstance(child, QLineEdit):
                        ph = child.placeholderText().lower()
                        val = child.text().lower()
                        if any(tok in ph or tok in val for tok in search_tokens):
                            card_matches = True
                            break
                    elif isinstance(child, QComboBox):
                        items_text = " ".join(child.itemText(i) for i in range(child.count())).lower()
                        cur_t = child.currentText().lower()
                        if any(tok in items_text or tok in cur_t for tok in search_tokens):
                            card_matches = True
                            break

            # 5. Apply Visibility and Adaptive Expansion
            card.setVisible(card_matches)
            if card_matches:
                card.set_expanded(True)
                for disc in child_disclosures:
                    if disc in matched_disclosures_in_card:
                        disc.set_expanded(True)
                    else:
                        disc.set_expanded(False)
            else:
                for disc in child_disclosures:
                    disc.set_expanded(False)

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
            t_key = get_tier_for_model(raw) or "speed"
            self._sync_priority_cards_ui(raw)
            self._update_sub_model_chips(t_key, raw)
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

        def _on_hist_copy(b=btn_copy, t=text):
            if safe_clipboard_copy(t):
                b.setText(tr("copied"))
                QTimer.singleShot(1500, lambda: b.setText(tr("copy")))
        btn_copy.clicked.connect(_on_hist_copy)

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
