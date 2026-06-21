#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_lager.py
Menüpunkt "Mein Lager" — persönlicher Fahrzeug-/Kofferbestand des Technikers.

DEMO-/MOCK-STAND: Die Bestände sind aktuell fest hinterlegte Beispieldaten.
Später ist hier ein read-only Zugriff auf SAP vorgesehen, sodass jeder
Techniker seinen eigenen Lagerbestand sieht. Die Tabelle, die Suche, die
Unterbestands-Warnung und der PDF-Export funktionieren bereits vollständig —
es muss nur die Datenquelle (MOCK_BESTAND) gegen die SAP-Abfrage getauscht
werden.

Der PDF-Export nutzt QPdfWriter + QTextDocument (in PyQt6 enthalten), daher
ist keine zusätzliche Bibliothek nötig.
"""

import os
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from utils import C, btn, lbl, page_hero


# ── Mock-Lagerbestand (später SAP read) ───────────────────────────────────────
# Felder: Teilenr., Bezeichnung, Lagerort, Bestand, Mindestbestand
MOCK_BESTAND = [
    ("1039.4238", "Service Set Filters V3",          "Fahrzeug · Fach A1",  4,  2),
    ("1041.0102", "Tinte ALPHAJET DYE schwarz 1L",   "Fahrzeug · Fach B2",  6,  3),
    ("1041.0210", "Make-up / Solvent 1L",            "Fahrzeug · Fach B3",  2,  3),
    ("1052.1180", "Druckkopf-Dichtungssatz",         "Fahrzeug · Fach A2",  1,  1),
    ("1052.4401", "Düsenplatte 60µ",                 "Koffer · klein",      0,  1),
    ("1060.7702", "Hauptfilter Tinte",               "Fahrzeug · Fach A1",  3,  2),
    ("1060.7711", "Vorfilter Make-up",               "Fahrzeug · Fach A1",  5,  2),
    ("1071.3320", "Membranpumpe komplett",           "Fahrzeug · Fach C1",  1,  1),
    ("1071.3325", "Pumpenmembran-Satz",              "Fahrzeug · Fach C1",  2,  2),
    ("1083.0905", "Ladeelektrode",                   "Koffer · klein",      1,  1),
    ("1083.0912", "Phasensensor",                    "Koffer · klein",      0,  1),
    ("1090.5540", "Viskositätssensor",               "Fahrzeug · Fach C2",  1,  1),
    ("1102.6601", "Schlauchset Hydrauliksystem",     "Fahrzeug · Fach C3",  2,  1),
    ("1110.8810", "Lichtschranke / Trigger",         "Koffer · groß",       3,  2),
    ("1125.0030", "Reinigungsset Druckkopf",         "Fahrzeug · Fach A2",  4,  2),
]


def _status(bestand, minimum):
    """Gibt (Text, Farbschlüssel) für den Bestandsstatus zurück."""
    if bestand <= 0:
        return "Kritisch", C["red"]
    if bestand < minimum:
        return "Nachbestellen", C["yellow"]
    return "OK", C["green"]


class LagerSeite(QWidget):
    """Persönlicher Lagerbestand des Technikers (Demo mit Mock-Daten)."""

    status_msg = pyqtSignal(str)

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)
        self._profile = profile or {}
        self._bestand = list(MOCK_BESTAND)
        self._build()
        self._fill()

    # ── Techniker-Name (für Kopf + PDF) ───────────────────────────────────────

    def _techniker_name(self):
        vorname = self._profile.get("vorname", "")
        nachname = self._profile.get("nachname", "")
        name = f"{vorname} {nachname}".strip()
        return name or "Techniker"

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(12)

        root.addWidget(page_hero(
            "icons/lager.png", "Mein Lager **Demo Seite**",
            "Persönlicher Fahrzeug- und Kofferbestand — später per SAP (read-only)",
            "Was wird benötigt? SAP und Salesforce API (read)",
        ))

        # ── Aktionsleiste ──────────────────────────────────────────────────────
        bar = QFrame()
        bar.setStyleSheet(f"background:{C['surface']}; border-radius:10px;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 8, 14, 8)
        bl.setSpacing(10)

        bl.addWidget(lbl("🔍", C["subtext"]))
        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Suche nach Teilenummer oder Bezeichnung …")
        self._suche.textChanged.connect(self._fill)
        bl.addWidget(self._suche, 1)

        self._nur_unter = QCheckBox("Nur Unterbestand")
        self._nur_unter.stateChanged.connect(self._fill)
        bl.addWidget(self._nur_unter)

        self._sap_btn = btn("⟳  SAP synchronisieren", self._sap_sync,
                            tooltip="Bestand aus SAP laden (in dieser Demo: Beispieldaten)")
        bl.addWidget(self._sap_btn)
        self._pdf_btn = btn("📄  Als PDF exportieren", self._export_pdf, color=C["green"])
        bl.addWidget(self._pdf_btn)
        root.addWidget(bar)

        # ── Hinweis-Banner (Demo) ──────────────────────────────────────────────
        hint = lbl("Demo-Ansicht mit Beispieldaten — die spätere Version liest den "
                   "Bestand schreibgeschützt aus SAP (pro Techniker).",
                   C["dimtext"], size=8)
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── Stats-Karten ───────────────────────────────────────────────────────
        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._stat_pos = self._stat_card(stats, "Positionen")
        self._stat_unter = self._stat_card(stats, "Unterbestand")
        self._stat_stueck = self._stat_card(stats, "Stück gesamt")
        root.addLayout(stats)

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._tv = QTableWidget(0, 6)
        self._tv.setHorizontalHeaderLabels(
            ["Teilenummer", "Bezeichnung", "Lagerort", "Bestand", "Mindest", "Status"])
        self._tv.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tv.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tv.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tv.verticalHeader().setVisible(False)
        self._tv.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._tv.setColumnWidth(0, 110)
        self._tv.setColumnWidth(2, 160)
        self._tv.setColumnWidth(3, 80)
        self._tv.setColumnWidth(4, 80)
        self._tv.setColumnWidth(5, 130)
        root.addWidget(self._tv, 1)

    def _stat_card(self, parent_layout, label):
        f = QFrame()
        f.setStyleSheet(f"background:{C['surface2']}; border-radius:10px;")
        v = QVBoxLayout(f)
        v.setContentsMargins(20, 10, 20, 10)
        v.setSpacing(2)
        v.addWidget(lbl(label, C["subtext"], size=8))
        value = lbl("—", C["accent"], bold=True, size=20)
        v.addWidget(value)
        parent_layout.addWidget(f)
        return value

    # ── Daten/Filter ──────────────────────────────────────────────────────────

    def _gefiltert(self):
        text = self._suche.text().strip().lower()
        nur_unter = self._nur_unter.isChecked()
        rows = []
        for teilenr, bez, ort, bestand, minimum in self._bestand:
            if nur_unter and bestand >= minimum:
                continue
            if text and text not in teilenr.lower() and text not in bez.lower():
                continue
            rows.append((teilenr, bez, ort, bestand, minimum))
        return rows

    def _fill(self):
        rows = self._gefiltert()
        tv = self._tv
        tv.setRowCount(len(rows))
        for r, (teilenr, bez, ort, bestand, minimum) in enumerate(rows):
            stext, scolor = _status(bestand, minimum)
            werte = [teilenr, bez, ort, str(bestand), str(minimum), stext]
            for c, val in enumerate(werte):
                item = QTableWidgetItem(val)
                if c in (3, 5):
                    item.setForeground(QBrush(QColor(scolor)))
                    if c == 5 or bestand < minimum:
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)
                tv.setItem(r, c, item)

        # Statistik über den GESAMTEN Bestand (nicht nur gefiltert)
        pos = len(self._bestand)
        unter = sum(1 for *_, b, m in self._bestand if b < m)
        stueck = sum(b for *_, b, _m in self._bestand)
        self._stat_pos.setText(str(pos))
        self._stat_unter.setText(str(unter))
        self._stat_unter.setStyleSheet(
            f"color:{C['red'] if unter else C['accent']};")
        self._stat_stueck.setText(str(stueck))

    def _sap_sync(self):
        # Demo: nur neu zeichnen + Statusmeldung. Später: SAP-Abfrage.
        self._fill()
        self.status_msg.emit("⟳  Lagerbestand aktualisiert (Demo-Daten)")

    # ── PDF-Export ────────────────────────────────────────────────────────────

    def _export_pdf(self):
        name = self._techniker_name()
        default = f"Lagerbestand_{name.replace(' ', '_')}_{date.today():%Y-%m-%d}.pdf"
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Lagerbestand als PDF speichern", default, "PDF-Dateien (*.pdf)")
        if not pfad:
            return
        try:
            self._schreibe_pdf(pfad)
        except Exception as e:
            QMessageBox.critical(self, "PDF-Fehler", str(e))
            return
        self.status_msg.emit(f"📄  PDF gespeichert: {os.path.basename(pfad)}")
        if QMessageBox.question(
                self, "PDF erstellt",
                f"PDF wurde gespeichert:\n{pfad}\n\nJetzt öffnen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes) == QMessageBox.StandardButton.Yes:
            try:
                os.startfile(pfad)   # type: ignore[attr-defined]
            except Exception:
                pass

    def _schreibe_pdf(self, pfad):
        # Lazy-Import, damit der App-Start nicht belastet wird.
        from PyQt6.QtGui import QPdfWriter, QTextDocument, QPageSize, QPageLayout
        from PyQt6.QtCore import QMarginsF

        rows = self._gefiltert()
        name = self._techniker_name()
        unter = sum(1 for *_, b, m in self._bestand if b < m)

        zeilen = []
        for teilenr, bez, ort, bestand, minimum in rows:
            stext, scolor = _status(bestand, minimum)
            warn = bestand < minimum
            stil = f"color:{scolor}; font-weight:bold;" if warn else ""
            zeilen.append(
                f"<tr>"
                f"<td>{teilenr}</td>"
                f"<td>{bez}</td>"
                f"<td>{ort}</td>"
                f"<td align='center' style='{stil}'>{bestand}</td>"
                f"<td align='center'>{minimum}</td>"
                f"<td style='{stil}'>{stext}</td>"
                f"</tr>"
            )

        html = f"""
        <html><body style="font-family:Arial, sans-serif; color:#202124;">
          <h2 style="margin-bottom:2px;">Lagerbestand — {name}</h2>
          <p style="color:#5c5e66; margin-top:0;">
            Stand: {date.today():%d.%m.%Y} &nbsp;·&nbsp;
            {len(rows)} Position(en) &nbsp;·&nbsp;
            {unter} unter Mindestbestand
          </p>
          <table width="100%" cellspacing="0" cellpadding="5" border="1"
                 style="border-collapse:collapse; font-size:10pt;">
            <thead>
              <tr style="background:#dddde0;">
                <th align="left">Teilenummer</th>
                <th align="left">Bezeichnung</th>
                <th align="left">Lagerort</th>
                <th align="center">Bestand</th>
                <th align="center">Mindest</th>
                <th align="left">Status</th>
              </tr>
            </thead>
            <tbody>
              {''.join(zeilen)}
            </tbody>
          </table>
          <p style="color:#97989f; font-size:8pt; margin-top:14px;">
            Erstellt mit dem Service Tool · Demo-Ansicht (Beispieldaten,
            spätere Datenquelle: SAP read-only).
          </p>
        </body></html>
        """

        writer = QPdfWriter(pfad)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print(writer)
