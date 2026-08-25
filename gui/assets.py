"""
Velodictum - GUI Brand Assets & Icon Generator
Creates high-resolution SVG and QIcon graphics programmatically.
"""
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient, QLinearGradient, QBrush, QPen
from PyQt6.QtSvg import QSvgRenderer


def create_app_icon(size: int = 64) -> QIcon:
    """Create a sleek modern brand icon: glowing purple-to-cyan gradient waveform."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background rounded squircle with gradient
    bg_gradient = QLinearGradient(0, 0, size, size)
    bg_gradient.setColorAt(0.0, QColor("#6366f1"))  # Indigo
    bg_gradient.setColorAt(0.5, QColor("#8b5cf6"))  # Violet
    bg_gradient.setColorAt(1.0, QColor("#06b6d4"))  # Cyan

    painter.setBrush(QBrush(bg_gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    radius = size * 0.28
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    # Inner subtle glow
    glow = QRadialGradient(size * 0.5, size * 0.5, size * 0.4)
    glow.setColorAt(0.0, QColor(255, 255, 255, 60))
    glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(QBrush(glow))
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    # Center sound wave bars
    painter.setBrush(QBrush(QColor("#ffffff")))
    bar_width = max(2.0, size * 0.08)
    bar_gap = max(2.0, size * 0.05)
    heights = [0.25, 0.5, 0.8, 0.55, 0.35]
    total_w = len(heights) * bar_width + (len(heights) - 1) * bar_gap
    start_x = (size - total_w) / 2
    center_y = size / 2

    for i, h_ratio in enumerate(heights):
        bx = start_x + i * (bar_width + bar_gap)
        bh = size * 0.5 * h_ratio
        by = center_y - (bh / 2)
        r = bar_width / 2
        painter.drawRoundedRect(int(bx), int(by), int(bar_width), int(bh), r, r)

    painter.end()
    return QIcon(pixmap)


def create_tray_icon() -> QIcon:
    """Create a 32x32 high-contrast tray icon."""
    return create_app_icon(32)
