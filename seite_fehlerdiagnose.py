#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_fehlerdiagnose.py
Menüpunkt "Fehlerdiagnose" — Master-Detail-Ansicht je Gerätesystem.

Daten liegen in res/fd/<system>.json mit Format {"entries": [...]}.
Welche Systeme es gibt, steht in res/fd/systeme.json (key -> Anzeigename).
Neue Systeme und neue Einträge können direkt im Tool angelegt werden.
"""

import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QTextEdit,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt

from utils import C, FD_DIR, btn, lbl, make_combo, page_hero
from katalog_utils import (
    load_registry, save_registry, load_liste, save_liste,
    NeuesSystemDialog, EintragDialog, SONSTIGES,
)

# Standard-Systeme, die beim allerersten Start angelegt werden (Registry leer).
# Hinweis: der alte tkinter-Schlüssel "AJ epti" passte nicht zum Dateinamen
# ajd_epti.json — hier wird konsequent der Datei-Stamm als Schlüssel benutzt.
_STANDARD_SYSTEME = {
    "aj5":      "alphaJET 5 (HS · HS-M · SP · X)",
    "ajd":      "alphaJET D (mondo)",
    "ajd_epti": "alphaJET epti / duo",
}

# Feldspezifikation für den Editier-Dialog: (key, Label, Art)
# Kategorie = einzelne Auswahl (checkbox_single) — vorhandene Kategorien
# werden als Checkboxen angezeigt, neue können über das "Neu:"-Feld
# angelegt werden (siehe katalog_utils.py).
_FELDER = [
    ("cat",     "Kategorie", "checkbox_single"),
    ("title",   "Titel",     "text"),
    ("content", "Inhalt",    "mehrzeilig"),
]


class FehlerdiagnoseSeite(QWidget):
    """Fehlerdiagnose-Katalog: Master-Tabelle (Kategorie/Titel) + Detailansicht."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = load_registry(FD_DIR, _STANDARD_SYSTEME)
        self._eintraege = []        # alle Einträge des aktuell gewählten Systems
        self._aktueller_key = None
        self._build()
        self._systeme_neu_laden()

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/fehlerdiagnose.png", "Fehlerdiagnose",
            "Fehlercodes und Diagnosen je Gerätesystem nachschlagen und pflegen",
        )) 

        # Kopfzeile (Steuerleiste)
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)
        hl.addWidget(lbl("System:", C["subtext"]))

        self._system_cb = make_combo([], 260)
        self._system_cb.currentIndexChanged.connect(self._on_system_change)
        hl.addWidget(self._system_cb)

        hl.addWidget(btn("＋ Neues System", self._neues_system, "Neues Gerätesystem anlegen"))
        hl.addStretch()
        root.addWidget(hdr)

        # Suchzeile
        filt = QFrame()
        filt.setStyleSheet(f"background:{C['header']}; border-bottom:1px solid {C['border']};")
        fl = QHBoxLayout(filt)
        fl.setContentsMargins(14, 6, 14, 6)
        fl.setSpacing(8)
        fl.addWidget(lbl("🔍", C["subtext"]))
        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Suche nach Kategorie oder Titel…")
        self._suche.textChanged.connect(self._filtern)
        fl.addWidget(self._suche, 1)
        fl.addWidget(btn("✕ Suche leeren", self._suche_leeren))
        self._anzahl_lbl = lbl("", C["dimtext"], size=9)
        fl.addWidget(self._anzahl_lbl)
        root.addWidget(filt)

        # Splitter: Master-Tabelle oben, Detail-Text unten
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        self._tabelle = QTableWidget()
        self._tabelle.setColumnCount(2)
        self._tabelle.setHorizontalHeaderLabels(["Kategorie", "Titel"])
        self._tabelle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabelle.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabelle.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabelle.verticalHeader().setVisible(False)
        self._tabelle.setColumnWidth(0, 160)
        self._tabelle.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tabelle.itemSelectionChanged.connect(self._zeige_detail)
        splitter.addWidget(self._tabelle)

        detail_wrap = QFrame()
        dl = QVBoxLayout(detail_wrap)
        dl.setContentsMargins(10, 8, 10, 8)
        dl.setSpacing(6)
        kopf = QHBoxLayout()
        kopf.addWidget(lbl("Detail:", C["accent"], bold=True))
        kopf.addStretch()
        kopf.addWidget(btn("📋 Kopieren", self._kopieren))
        dl.addLayout(kopf)
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        dl.addWidget(self._detail_text)
        splitter.addWidget(detail_wrap)

        splitter.setSizes([320, 260])
        root.addWidget(splitter, 1)

        # Aktionsleiste
        akt = QFrame()
        akt.setStyleSheet(f"background:{C['surface']}; border-top:1px solid {C['border']};")
        al = QHBoxLayout(akt)
        al.setContentsMargins(14, 8, 14, 8)
        al.setSpacing(8)
        al.addWidget(btn("＋ Neuer Eintrag", self._neuer_eintrag, color=C["green"]))
        al.addWidget(btn("✎ Bearbeiten", self._bearbeiten))
        al.addWidget(btn("🗑 Löschen", self._loeschen, color=C["red"]))
        al.addStretch()
        root.addWidget(akt)

    # ── Systeme verwalten ─────────────────────────────────────────────────────

    def _systeme_neu_laden(self):
        self._system_cb.blockSignals(True)
        self._system_cb.clear()
        for key, label in sorted(self._registry.items(), key=lambda kv: kv[1]):
            self._system_cb.addItem(label, key)
        self._system_cb.blockSignals(False)
        if self._system_cb.count():
            self._system_cb.setCurrentIndex(0)
            self._on_system_change()

    def _neues_system(self):
        dlg = NeuesSystemDialog(self)
        if dlg.exec():
            key, label = dlg.values()
            if not key:
                return
            if key in self._registry:
                QMessageBox.warning(self, "Hinweis", "Dieses System existiert bereits.")
                return
            self._registry[key] = label
            save_registry(FD_DIR, self._registry)
            save_liste(FD_DIR, key, "entries", [])  # leere JSON-Datei anlegen
            self._systeme_neu_laden()
            idx = self._system_cb.findData(key)
            if idx >= 0:
                self._system_cb.setCurrentIndex(idx)

    def _on_system_change(self, *_):
        key = self._system_cb.currentData()
        if not key:
            return
        self._aktueller_key = key
        self._eintraege = load_liste(FD_DIR, key, "entries")
        self._filtern()

    def _kategorien_optionen(self):
        """Vorhandene Kategorien des aktuellen Systems (für die Checkboxen
        im Dialog), 'Sonstiges' immer dabei, da auch der Fallback-Wert ist."""
        kategorien = sorted({(e.get("cat") or "") for e in self._eintraege if e.get("cat")})
        if SONSTIGES not in kategorien:
            kategorien.append(SONSTIGES)
        return kategorien

    # ── Suche / Anzeige ───────────────────────────────────────────────────────

    def _suche_leeren(self):
        self._suche.clear()

    def _gefiltert(self):
        """
        Gibt (index, eintrag)-Paare zurück, 'index' = Position in
        self._eintraege. WICHTIG: PyQt kopiert Python-dicts beim
        Speichern via QTableWidgetItem.setData()/data() (Roundtrip über
        QVariant) — die Objektidentität geht dabei verloren. Deshalb wird
        nur der Index (überlebt den Roundtrip unverändert) in der Zelle
        abgelegt und beim Zugriff direkt in self._eintraege nachgeschlagen.
        """
        text = self._suche.text().strip().lower()
        if not text:
            return list(enumerate(self._eintraege))
        return [(i, e) for i, e in enumerate(self._eintraege)
                if text in e.get("cat", "").lower() or text in e.get("title", "").lower()]

    def _filtern(self, *_):
        gefiltert = self._gefiltert()
        self._tabelle.setRowCount(len(gefiltert))
        for row, (idx, eintrag) in enumerate(gefiltert):
            for col, key in enumerate(("cat", "title")):
                wert = eintrag.get(key, "")
                if key == "cat" and not wert:
                    wert = SONSTIGES
                item = QTableWidgetItem(str(wert))
                item.setData(Qt.ItemDataRole.UserRole, idx)
                self._tabelle.setItem(row, col, item)
        self._anzahl_lbl.setText(f"{len(gefiltert)} / {len(self._eintraege)} Einträge")
        self._detail_text.clear()

    def _ausgewaehlter_index(self):
        row = self._tabelle.currentRow()
        if row < 0:
            return None
        item = self._tabelle.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _ausgewaehlter_eintrag(self):
        idx = self._ausgewaehlter_index()
        if idx is None or idx >= len(self._eintraege):
            return None
        return self._eintraege[idx]

    def _zeige_detail(self):
        eintrag = self._ausgewaehlter_eintrag()
        if not eintrag:
            self._detail_text.clear()
            return
        # Einfache Formatierung: doppelte Zeilenumbrüche als Absätze beibehalten,
        # überflüssige Leerzeichen entfernen (analog zur alten tkinter-Variante).
        inhalt = eintrag.get("content", "") or ""
        inhalt = re.sub(r"[ \t]+\n", "\n", inhalt)
        self._detail_text.setPlainText(inhalt)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _neuer_eintrag(self):
        if not self._aktueller_key:
            return
        dlg = EintragDialog(_FELDER, titel="Neuer Fehlerdiagnose-Eintrag", parent=self,
                             options_map={"cat": self._kategorien_optionen()})
        if dlg.exec():
            werte = dlg.werte()
            werte["cat"] = werte.get("cat") or SONSTIGES
            self._eintraege.append(werte)
            self._speichern()
            self._filtern()

    def _bearbeiten(self):
        eintrag = self._ausgewaehlter_eintrag()
        if not eintrag:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        werte_init = dict(eintrag)
        werte_init["cat"] = eintrag.get("cat") or SONSTIGES
        dlg = EintragDialog(_FELDER, werte_init=werte_init, titel="Eintrag bearbeiten", parent=self,
                             options_map={"cat": self._kategorien_optionen()})
        if dlg.exec():
            werte = dlg.werte()
            werte["cat"] = werte.get("cat") or SONSTIGES
            eintrag.clear()
            eintrag.update(werte)  # gleiche Objektreferenz -> Original in self._eintraege aktualisiert
            self._speichern()
            self._filtern()

    def _loeschen(self):
        idx = self._ausgewaehlter_index()
        if idx is None:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        if QMessageBox.question(self, "Löschen", "Diesen Eintrag wirklich löschen?") != QMessageBox.StandardButton.Yes:
            return
        del self._eintraege[idx]
        self._speichern()
        self._filtern()

    def _speichern(self):
        save_liste(FD_DIR, self._aktueller_key, "entries", self._eintraege)

    def _kopieren(self):
        text = self._detail_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
