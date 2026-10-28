"""
Velodictum - GUI Brand Assets & Icon Generator
Creates high-resolution SVG and QIcon graphics programmatically in Dark Neomorphism 2.0 style.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush, QPen


def create_app_icon(size: int = 64) -> QIcon:
    """Create the Dark Neomorphism 2.0 brand icon: deep graphite recessed badge with muted indigo soundwave bars."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Neomorphic graphite squircle surface
    bg_gradient = QLinearGradient(0, 0, size, size)
    bg_gradient.setColorAt(0.0, QColor("#1b2030"))
    bg_gradient.setColorAt(1.0, QColor("#0e111a"))

    radius = size * 0.28
    painter.setBrush(QBrush(bg_gradient))
    painter.setPen(QPen(QColor(255, 255, 255, 26), max(1.0, size * 0.025)))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, radius, radius)

    # Center sound wave bars (Muted Indigo / Violet as in the Dark Neomorphism 2.0 reference)
    bar_gradient = QLinearGradient(0, size * 0.15, 0, size * 0.85)
    bar_gradient.setColorAt(0.0, QColor("#818cf8"))
    bar_gradient.setColorAt(1.0, QColor("#5861b5"))
    painter.setBrush(QBrush(bar_gradient))
    painter.setPen(Qt.PenStyle.NoPen)

    bar_width = max(2.0, size * 0.095)
    bar_gap = max(2.0, size * 0.055)
    heights = [0.28, 0.56, 0.84, 0.60, 0.34]
    total_w = len(heights) * bar_width + (len(heights) - 1) * bar_gap
    start_x = (size - total_w) / 2.0
    center_y = size / 2.0

    for i, h_ratio in enumerate(heights):
        bx = start_x + i * (bar_width + bar_gap)
        bh = size * 0.56 * h_ratio
        by = center_y - (bh / 2.0)
        r = bar_width / 2.0
        painter.drawRoundedRect(int(bx), int(by), int(bar_width), int(bh), r, r)

    painter.end()
    return QIcon(pixmap)


def create_tray_icon() -> QIcon:
    """Create a 32x32 high-contrast tray icon."""
    return create_app_icon(32)
