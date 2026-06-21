#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
splash.py
Animierter Lade-Splash fuer den App-Start.
"""

import os

from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QFontMetrics

from utils import C, APP_NAME, APP_VERSION, ICON_PNG, MEIPASS_DIR


_W, _H = 460, 240
_BG     = "#0f172a"
_ACCENT = C.get("accent", "#2563eb")
_TEXT   = "#f1f5f9"
_SUBTEXT = "#94a3b8"
_DOT_ON  = _ACCENT
_DOT_OFF = "#334155"


def _make_base_pixmap(icon_pix):
    pix = QPixmap(_W, _H)
    pix.fill(QColor(_BG))

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    from PyQt6.QtGui import QLinearGradient
    grad = QLinearGradient(0, 0, 0, _H // 2)
    grad.setColorAt(0, QColor(37, 99, 235, 25))
    grad.setColorAt(1, QColor(37, 99, 235, 0))
    p.fillRect(0, 0, _W, _H // 2, grad)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(_ACCENT))
    p.drawRect(0, 0, _W, 3)

    icon_size = 64
    icon_x = (_W - icon_size) // 2
    icon_y = 30
    if icon_pix and not icon_pix.isNull():
        scaled = icon_pix.scaled(
            icon_size, icon_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        p.drawPixmap(icon_x + (icon_size - scaled.width()) // 2,
                     icon_y + (icon_size - scaled.height()) // 2, scaled)

    name_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
    p.setFont(name_font)
    p.setPen(QColor(_TEXT))
    fm = QFontMetrics(name_font)
    nx = (_W - fm.horizontalAdvance(APP_NAME)) // 2
    p.drawText(nx, icon_y + icon_size + 28, APP_NAME)

    ver_font = QFont("Segoe UI", 9)
    p.setFont(ver_font)
    p.setPen(QColor(_SUBTEXT))
    ver_text = f"Version {APP_VERSION}"
    vfm = QFontMetrics(ver_font)
    vx = (_W - vfm.horizontalAdvance(ver_text)) // 2
    p.drawText(vx, icon_y + icon_size + 48, ver_text)

    p.end()
    return pix


def _draw_dots(base_pix, active_dot, status_text="Wird gestartet"):
    pix = base_pix.copy()
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.fillRect(0, _H - 54, _W, 54, QColor(_BG))

    st_font = QFont("Segoe UI", 8)
    p.setFont(st_font)
    p.setPen(QColor(_SUBTEXT))
    sfm = QFontMetrics(st_font)
    sx = (_W - sfm.horizontalAdvance(status_text)) // 2
    p.drawText(sx, _H - 30, status_text)

    n_dots  = 5
    dot_r   = 5
    spacing = 16
    total_w = n_dots * (dot_r * 2) + (n_dots - 1) * (spacing - dot_r * 2)
    dx = (_W - total_w) // 2
    dy = _H - 16

    for i in range(n_dots):
        color = QColor(_DOT_ON) if i == active_dot else QColor(_DOT_OFF)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(dx + i * spacing, dy - dot_r, dot_r * 2, dot_r * 2)

    p.end()
    return pix


class AnimatedSplash(QSplashScreen):
    _STATUS_STEPS = [
        "Module werden geladen ...",
        "Oberflaeche wird vorbereitet ...",
        "Daten werden geladen ...",
        "Fast fertig ...",
        "Wird gestartet ...",
    ]

    def __init__(self):
        icon_path = ICON_PNG if os.path.isfile(ICON_PNG) \
            else os.path.join(MEIPASS_DIR, "icon.png")
        self._icon_pix = QPixmap(icon_path)
        self._base     = _make_base_pixmap(self._icon_pix)
        self._dot      = 0
        self._step     = 0

        super().__init__(self._base)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(_W, _H)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(220)
        self._tick()

    def _tick(self):
        status = self._STATUS_STEPS[min(self._step, len(self._STATUS_STEPS) - 1)]
        pix = _draw_dots(self._base, self._dot, status)
        self.setPixmap(pix)
        self._dot = (self._dot + 1) % 5
        if self._dot == 0 and self._step < len(self._STATUS_STEPS) - 1:
            self._step += 1

    def advance(self, step_idx):
        self._step = min(step_idx, len(self._STATUS_STEPS) - 1)

    def close(self):
        self._timer.stop()
        super().close()


def show_splash():
    splash = AnimatedSplash()
    splash.show()
    QApplication.processEvents()
    return splash
