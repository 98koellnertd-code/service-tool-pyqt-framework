#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_dashboard.py
Menüpunkt "Dashboard" — Wochenübersicht "Meine Woche".

DEMO-/MOCK-STAND: Diese Seite ist eine reine Vorschau mit fest hinterlegten
Beispieldaten (MOCK_*). Sie zeigt, wie das fertige Dashboard aussehen soll:
KPI-Karten (Stunden, offene Aufträge, gefahrene km, verbaute Teile), ein
kleines Wochen-Chart (Stunden je Wochentag) und die nächsten Termine.

Später werden die Mock-Werte gegen echte Daten ersetzt — z.B. aus den
Arbeitszeiten/Reisekosten-Seiten und aus Salesforce. Layout, Karten und
Chart funktionieren bereits vollständig; es muss nur die Datenquelle
getauscht werden.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QPen

from utils import C, lbl, page_hero


# ── Mock-Daten (später echte Quellen) ─────────────────────────────────────────
# KPI-Karten: (Schlüssel, Titel, Wert, Einheit, Zusatz/Trend, Farbschlüssel)
MOCK_KPIS = [
    ("stunden",  "Stunden",         "38,5", "h",     "+2,5 h zur Vorwoche", "accent"),
    ("auftraege","Offene Aufträge", "4",    "",      "2 fällig diese Woche", "yellow"),
    ("km",       "Gefahrene km",    "612",  "km",    "8 Einsätze",           "mauve"),
    ("teile",    "Verbaute Teile",  "27",   "Stk",   "in 6 Aufträgen",       "green"),
]

# Wochen-Chart: Stunden je Wochentag (Mo–Fr)
MOCK_WEEK_HOURS = [
    ("Mo", 8.5),
    ("Di", 7.0),
    ("Mi", 9.0),
    ("Do", 8.0),
    ("Fr", 6.0),
]

# Nächste Termine: (Datum, Uhrzeit, Titel, Ort/Kunde, Farbschlüssel)
MOCK_TERMINE = [
    ("Do 19.06.", "09:00", "Wartung ALPHAJET", "Müller GmbH · Stuttgart",   "accent"),
    ("Fr 20.06.", "13:30", "Störung Druckkopf", "Bäckerei Klein · Esslingen","red"),
    ("Mo 23.06.", "08:00", "Inbetriebnahme",    "Logistik Süd · Heilbronn",  "green"),
    ("Di 24.06.", "11:00", "Filterwechsel",     "Pharma AG · Karlsruhe",     "mauve"),
]


# ══════════════════════════════════════════════════════════════════════════════
# Wochen-Chart (kleines Balkendiagramm, mit QPainter gezeichnet)
# ══════════════════════════════════════════════════════════════════════════════

class _WeekChart(QWidget):
    """Schlankes Balkendiagramm: Stunden je Wochentag. Reines Mock-Chart."""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 8, 8, 14, 26
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        if not self._data or plot_h <= 0:
            return

        max_val = max(v for _, v in self._data) or 1.0
        n = len(self._data)
        slot = plot_w / n
        bar_w = min(slot * 0.5, 46)

        accent = QColor(C["accent"])
        grid_col = QColor(C["border"])
        txt_col = QColor(C["subtext"])
        val_col = QColor(C["text"])

        # Dezente horizontale Hilfslinien (0 / Mitte / Max)
        p.setPen(QPen(grid_col, 1, Qt.PenStyle.DashLine))
        for frac in (0.0, 0.5, 1.0):
            y = pad_t + plot_h * (1 - frac)
            p.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))

        f_lbl = QFont(self.font())
        f_lbl.setPointSize(8)
        f_val = QFont(self.font())
        f_val.setPointSize(8)
        f_val.setBold(True)

        for i, (label, val) in enumerate(self._data):
            cx = pad_l + slot * i + slot / 2
            bh = plot_h * (val / max_val)
            x = cx - bar_w / 2
            y = pad_t + (plot_h - bh)
            rect = QRectF(x, y, bar_w, bh)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(accent))
            p.drawRoundedRect(rect, 4, 4)

            # Wert über dem Balken
            p.setFont(f_val)
            p.setPen(val_col)
            p.drawText(
                QRectF(cx - slot / 2, y - 16, slot, 14),
                Qt.AlignmentFlag.AlignCenter,
                f"{val:.1f}".replace(".", ","),
            )

            # Wochentag unter dem Balken
            p.setFont(f_lbl)
            p.setPen(txt_col)
            p.drawText(
                QRectF(cx - slot / 2, h - pad_b + 4, slot, 18),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# KPI-Karte
# ══════════════════════════════════════════════════════════════════════════════

def _kpi_card(title, value, unit, sub, color_key):
    """Eine KPI-Kachel: großer Wert + Titel + kleiner Zusatztext, farbiger Streifen."""
    accent = C.get(color_key, C["accent"])

    card = QFrame()
    card.setObjectName("kpiCard")
    card.setStyleSheet(
        f"QFrame#kpiCard {{ background:{C['surface']}; border:none; "
        f"border-radius:12px; border-left:4px solid {accent}; }}"
    )
    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(4)

    lay.addWidget(lbl(title.upper(), C["subtext"], bold=True, size=8))

    # Wert + Einheit in einer Zeile
    val_row = QHBoxLayout()
    val_row.setContentsMargins(0, 0, 0, 0)
    val_row.setSpacing(5)
    val_lbl = lbl(value, accent, bold=True, size=24)
    val_row.addWidget(val_lbl)
    if unit:
        u = lbl(unit, C["dimtext"], size=10)
        val_row.addWidget(u, 0, Qt.AlignmentFlag.AlignBottom)
    val_row.addStretch()
    lay.addLayout(val_row)

    sub_lbl = lbl(sub, C["dimtext"], size=8)
    sub_lbl.setWordWrap(True)
    lay.addWidget(sub_lbl)
    return card


# ══════════════════════════════════════════════════════════════════════════════
# Termin-Zeile
# ══════════════════════════════════════════════════════════════════════════════

def _termin_row(datum, zeit, titel, ort, color_key):
    accent = C.get(color_key, C["accent"])

    row = QFrame()
    row.setObjectName("terminRow")
    row.setStyleSheet(
        f"QFrame#terminRow {{ background:{C['surface2']}; border:none; "
        f"border-radius:8px; }}"
    )
    h = QHBoxLayout(row)
    h.setContentsMargins(12, 10, 14, 10)
    h.setSpacing(14)

    # Datum/Zeit-Block links
    dt_col = QVBoxLayout()
    dt_col.setSpacing(1)
    dt_col.addWidget(lbl(datum, C["text"], bold=True, size=9))
    dt_col.addWidget(lbl(zeit, accent, bold=True, size=10))
    dt_wrap = QWidget()
    dt_wrap.setFixedWidth(74)
    dt_wrap.setLayout(dt_col)
    h.addWidget(dt_wrap)

    # farbiger Trenner
    bar = QFrame()
    bar.setFixedWidth(3)
    bar.setStyleSheet(f"background:{accent}; border-radius:1px;")
    h.addWidget(bar)

    # Titel + Ort
    info_col = QVBoxLayout()
    info_col.setSpacing(2)
    info_col.addWidget(lbl(titel, C["text"], bold=True, size=10))
    ort_lbl = lbl(ort, C["subtext"], size=9)
    info_col.addWidget(ort_lbl)
    h.addLayout(info_col, 1)
    return row


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard-Seite
# ══════════════════════════════════════════════════════════════════════════════

class DashboardSeite(QWidget):
    """Dashboard 'Meine Woche' — Demo-Vorschau mit Mock-Daten."""

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)
        self._profile = profile or {}
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

        # ── Seitenkopf ───────────────────────────────────────────────────────
        root.addWidget(page_hero(
            "icons/monitor.png",
            "Dashboard **Demo-Seite**",
            "Meine Woche auf einen Blick — Kennzahlen, Auslastung und nächste Termine",
            "Was wird benötigt? Salesforce API (read)",            
        ))

        # Demo-Hinweis
        hint = lbl(
            "Vorschau mit Beispieldaten — echte Werte folgen aus Arbeitszeiten, "
            "Reisekosten und Salesforce.",
            C["dimtext"], size=9,
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── KPI-Karten ───────────────────────────────────────────────────────
        root.addWidget(lbl("Meine Woche", C["subtext"], bold=True, size=9))

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(14)
        cols = 4
        for i, (_key, title, value, unit, sub, ckey) in enumerate(MOCK_KPIS):
            card = _kpi_card(title, value, unit, sub, ckey)
            kpi_grid.addWidget(card, i // cols, i % cols)
        for c in range(cols):
            kpi_grid.setColumnStretch(c, 1)
        root.addLayout(kpi_grid)

        # ── Untere Reihe: Chart links, Termine rechts ────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(20)

        # Chart-Karte
        chart_card = QFrame()
        chart_card.setStyleSheet(
            f"QFrame {{ background:{C['surface']}; border:none; border-radius:12px; }}"
        )
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(20, 16, 20, 16)
        chart_lay.setSpacing(10)
        chart_head = QHBoxLayout()
        chart_head.addWidget(lbl("Stunden je Wochentag", C["text"], bold=True, size=11))
        chart_head.addStretch()
        chart_head.addWidget(lbl("KW 25", C["dimtext"], size=9))
        chart_lay.addLayout(chart_head)
        chart_lay.addWidget(_WeekChart(MOCK_WEEK_HOURS), 1)
        bottom.addWidget(chart_card, 3)

        # Termine-Karte
        termin_card = QFrame()
        termin_card.setStyleSheet(
            f"QFrame {{ background:{C['surface']}; border:none; border-radius:12px; }}"
        )
        termin_lay = QVBoxLayout(termin_card)
        termin_lay.setContentsMargins(20, 16, 20, 16)
        termin_lay.setSpacing(10)
        th = QHBoxLayout()
        th.addWidget(lbl("Nächste Termine", C["text"], bold=True, size=11))
        th.addStretch()
        th.addWidget(lbl(f"{len(MOCK_TERMINE)}", C["dimtext"], size=9))
        termin_lay.addLayout(th)
        for datum, zeit, titel, ort, ckey in MOCK_TERMINE:
            termin_lay.addWidget(_termin_row(datum, zeit, titel, ort, ckey))
        termin_lay.addStretch()
        bottom.addWidget(termin_card, 2)

        root.addLayout(bottom)
        root.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)
