#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_start.py
Menüpunkt "Start" — Übersicht und Schnellzugriff.

Zeigt alle verfügbaren Module als klickbare Kacheln (mit Kurzbeschreibung)
sowie eine "Erste Schritte"-Anleitung. Die eigentliche Salesforce-Anmeldung
liegt im direkt darunter folgenden Menüpunkt "Salesforce".
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QGridLayout, QLabel,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QCursor

from utils import C, APP_NAME, APP_VERSION, lbl, btn, MEIPASS_DIR, MODULES


class _Card(QFrame):
    """Klickbare Modul-Kachel — flaches Design, Hover mit Akzent-Streifen."""
    clicked = pyqtSignal(int)

    def __init__(self, nav_idx, icon_path, title, desc, parent=None):
        super().__init__(parent)
        self._idx = nav_idx
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Objekt-Name, damit die Kachel-Stylesheet NICHT auf den Akzent-Streifen
        # (ebenfalls ein QFrame) durchschlägt.
        self.setObjectName("card")
        self._normal = (
            f"QFrame#card {{ background:transparent; border:none; "
            f"border-radius:8px; }}"
        )
        self._hover = (
            f"QFrame#card {{ background:{C['overlay']}; border:none; "
            f"border-radius:8px; }}"
        )
        self.setStyleSheet(self._normal)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 14, 14, 14)
        lay.setSpacing(14)

        # Akzent-Streifen ganz links — eigenes Widget statt border-left-Trick,
        # damit es beim Hover genau EINEN sauberen, abgerundeten Streifen gibt.
        self._accent = QFrame()
        self._accent.setFixedWidth(3)
        self._accent_normal = "background:transparent; border-radius:1px;"
        self._accent_hover = f"background:{C['accent']}; border-radius:1px;"
        self._accent.setStyleSheet(self._accent_normal)
        lay.addWidget(self._accent)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        pix = QPixmap(os.path.join(MEIPASS_DIR, icon_path))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(36, 36,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        lay.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.addWidget(lbl(title, C["text"], bold=True, size=10))
        desc_lbl = lbl(desc, C["subtext"], size=9)
        desc_lbl.setWordWrap(True)
        text_col.addWidget(desc_lbl)
        lay.addLayout(text_col, 1)

    def enterEvent(self, e):
        self.setStyleSheet(self._hover)
        self._accent.setStyleSheet(self._accent_hover)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet(self._normal)
        self._accent.setStyleSheet(self._accent_normal)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._idx)
        super().mousePressEvent(e)


class StartPage(QWidget):
    """Startseite mit Tool-Übersicht und klickbaren Modul-Kacheln."""
    navigate_to = pyqtSignal(int)

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self._profile = profile
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(20)

        # ── Hero-Header ──────────────────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(
            f"QFrame {{ background:{C['surface']}; border-radius:12px; border:none; }}"
        )
        hero_lay = QHBoxLayout(hero)
        hero_lay.setContentsMargins(24, 20, 24, 20)
        hero_lay.setSpacing(20)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(56, 56)
        pix = QPixmap(os.path.join(MEIPASS_DIR, "icons/icon.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(56, 56,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        hero_lay.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_col.addWidget(lbl(APP_NAME, C["accent"], bold=True, size=20))
        title_col.addWidget(lbl(
            "Arbeitszeiten, Reisekosten, Ersatzteile & mehr — alles an einem Ort",
            C["subtext"], size=10,
        ))
        title_col.addWidget(lbl(f"Version {APP_VERSION}", C["dimtext"], size=9))
        hero_lay.addLayout(title_col, 1)
        hero_lay.addWidget(
            btn("🧭  Tour starten", self._start_tour,
                "Startet eine kurze geführte Tour durch das Tool.",
                color=C["accent"]),
            0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(hero)

        # ── Sektion-Label Module ─────────────────────────────────────────────
        root.addWidget(lbl("Module", C["subtext"], bold=True, size=9))

        # ── Modul-Kacheln (rahmenlos) ────────────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        # Modul-Kacheln aus dem zentralen Register (utils.MODULES) — so bleiben
        # Reihenfolge, Icons, Namen und Beschreibungen synchron zu Sidebar & Info.
        cols = 3
        for i, m in enumerate(MODULES):
            card = _Card(m["nav"], m["icon"], m["name"], m["desc"])
            card.clicked.connect(self.navigate_to)
            grid.addWidget(card, i // cols, i % cols)

        root.addLayout(grid)

        # ── Sektion-Label Erste Schritte ─────────────────────────────────────
        root.addWidget(lbl("Erste Schritte", C["subtext"], bold=True, size=9))

        # ── Schritt-für-Schritt-Anleitung ────────────────────────────────────
        steps_frame = QFrame()
        steps_frame.setStyleSheet(
            f"QFrame {{ background:{C['surface']}; border-radius:10px; border:none; }}"
        )
        steps_lay = QVBoxLayout(steps_frame)
        steps_lay.setContentsMargins(20, 16, 20, 16)
        steps_lay.setSpacing(14)

        STEPS = [
            (1, "Bei Salesforce anmelden",
             "Direkt nach der Startseite folgt der Menüpunkt »Salesforce«. Dort meldest du dich per Session ID oder OAuth an. Eine grüne Statusanzeige bestätigt die Verbindung — danach lassen sich Daten laden."),
            (2, "Arbeitszeiten erfassen",
             "Im Menü »Arbeitszeiten« die Servicezeiten je Monat eintragen oder aus Salesforce laden, bearbeiten und als Servicezeitenmeldung exportieren."),
            (3, "Reisekostenabrechnung erstellen",
             "Unter »Reisekosten« die Woche (KW) erfassen — inklusive Mahlzeiten und Sonstigem — und als Reisekostenabrechnung exportieren."),
            (4, "Ersatzteile & Bestellungen",
             "Im »Ersatzteile«-Katalog Teile suchen und per Doppelklick direkt in eine »Bestellung« übernehmen, zusammenstellen und exportieren."),
            (5, "Einstellungen anpassen",
             "Unter »Einstellungen« persönliche Daten, Export-Ordner, das Farbthema ändern und anpassen oder automatische Updates konfigurieren."),
        ]

        for i, (num, title, desc) in enumerate(STEPS):
            if i > 0:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background:{C['border']}; border:none;")
                steps_lay.addWidget(sep)

            row = QHBoxLayout()
            row.setSpacing(14)

            num_lbl = QLabel(str(num))
            num_lbl.setFixedSize(26, 26)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setStyleSheet(
                f"QLabel {{ background:{C['accent']}; color:#ffffff; "
                f"border-radius:13px; font-weight:bold; font-size:9pt; }}"
            )
            row.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignTop)

            text_col = QVBoxLayout()
            text_col.setSpacing(3)
            text_col.addWidget(lbl(title, C["text"], bold=True, size=10))
            desc_lbl = lbl(desc, C["subtext"], size=9)
            desc_lbl.setWordWrap(True)
            text_col.addWidget(desc_lbl)
            row.addLayout(text_col, 1)

            steps_lay.addLayout(row)

        root.addWidget(steps_frame)
        root.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _start_tour(self):
        """Öffnet die geführte Tour (navigiert das Hauptfenster mit)."""
        from tour import TourDialog
        TourDialog(navigate=self.navigate_to.emit, parent=self).exec()
