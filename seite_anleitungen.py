#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_anleitungen.py
Menüpunkt "Anleitungen" — Dokumentations-/Anleitungskatalog je Kategorie.

Aufbau analog zu "Fehlerdiagnose" und "Ersatzteile":
  Daten liegen in res/anl/<kategorie>.json mit Format {"entries": [...]}.
  Welche Kategorien es gibt, steht in res/anl/systeme.json
  (key -> Anzeigename). Neue Kategorien und neue Einträge können direkt
  im Tool angelegt und als JSON gespeichert/bearbeitet werden.

Besonderheiten gegenüber der Fehlerdiagnose:
  - Oben kann eine einzelne Kategorie ODER "Alle" gewählt werden; "Alle"
    ist die Voreinstellung und zeigt die Einträge sämtlicher Kategorien.
  - Die Spalte "Kategorie" zeigt, zu welcher Kategorie (z.B. "Hotline")
    ein Eintrag gehört.
  - Es wird in Titel UND Inhalt gesucht. Treffer im Titel (die präzisesten)
    erscheinen oben, danach folgen die reinen Inhaltstreffer.
  - Ein Eintrag kann auf eine Original-PDF verweisen (Feld "file", relativ
    zu res/anl). Diese lässt sich per Knopf im Standardprogramm öffnen.
    Per Import-Skript (extract_anleitungen.py) erzeugte Einträge tragen
    zusätzlich "file"/"pages"; diese Felder bleiben beim Bearbeiten erhalten.
"""

import os
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QTextEdit,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

from utils import C, ANL_DIR, btn, lbl, make_combo, page_hero
from katalog_utils import (
    load_registry, save_registry, load_liste, save_liste,
    NeuesSystemDialog, EintragDialog,
)

# Standard-Kategorien, die beim allerersten Start angelegt werden (Registry leer).
# Hinweis: aktuell existiert nur "hotline"; weitere Kategorien werden über
# das Import-Skript (extract_anleitungen.py) oder direkt im Tool ergänzt.
_STANDARD_SYSTEME = {
    "hotline": "Hotline (SAP / Salesforce)",
}

# Feldspezifikation für den Editier-Dialog: (key, Label, Art)
_FELDER = [
    ("title",   "Titel",  "text"),
    ("content", "Inhalt", "mehrzeilig"),
]


class AnleitungenSeite(QWidget):
    """Anleitungs-Katalog: Master-Tabelle (Kategorie/Titel) + Detailansicht.

    Volltextsuche über Titel und Inhalt; PDF-Verweis per Knopf öffenbar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = load_registry(ANL_DIR, _STANDARD_SYSTEME)
        self._eintraege = []        # angezeigte Einträge (ggf. über alle Kategorien)
        self._eintrag_keys = []     # parallel: Kategorie-Key je Eintrag (für Speichern)
        self._aktueller_key = None  # gewählte Kategorie; None = "Alle"
        self._build()
        self._systeme_neu_laden()

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/configs.png", "Anleitungen",
            "Anleitungen, Troubleshooting's und Dokumentationen, je Kategorie durchsuchen und pflegen",
        ))

        # Kopfzeile (Steuerleiste)
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)
        hl.addWidget(lbl("Kategorie:", C["subtext"]))

        self._system_cb = make_combo([], 260)
        self._system_cb.currentIndexChanged.connect(self._on_system_change)
        hl.addWidget(self._system_cb)

        hl.addWidget(btn("＋ Neue Kategorie", self._neues_system, "Neue Anleitungs-Kategorie anlegen"))
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
        self._suche.setPlaceholderText("Suche nach Titel oder Inhalt…")
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
        self._tabelle.setColumnCount(3)
        self._tabelle.setHorizontalHeaderLabels(["Kategorie", "Titel", "Treffer"])
        self._tabelle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabelle.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabelle.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabelle.verticalHeader().setVisible(False)
        self._tabelle.setColumnWidth(0, 220)
        self._tabelle.setColumnWidth(2, 90)
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
        self._pdf_btn = btn("📄 PDF öffnen", self._pdf_oeffnen, "Hinterlegte Original-PDF öffnen")
        self._pdf_btn.setEnabled(False)
        kopf.addWidget(self._pdf_btn)
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

    # ── Kategorien verwalten ────────────────────────────────────────────────────

    def _systeme_neu_laden(self):
        self._system_cb.blockSignals(True)
        self._system_cb.clear()
        self._system_cb.addItem("Alle", None)   # Voreinstellung: alle Kategorien
        for key, label in sorted(self._registry.items(), key=lambda kv: kv[1]):
            self._system_cb.addItem(label, key)
        self._system_cb.blockSignals(False)
        self._system_cb.setCurrentIndex(0)
        self._on_system_change()

    def _neues_system(self):
        dlg = NeuesSystemDialog(self)
        if dlg.exec():
            key, label = dlg.values()
            if not key:
                return
            if key in self._registry:
                QMessageBox.warning(self, "Hinweis", "Diese Kategorie existiert bereits.")
                return
            self._registry[key] = label
            save_registry(ANL_DIR, self._registry)
            save_liste(ANL_DIR, key, "entries", [])  # leere JSON-Datei anlegen
            self._systeme_neu_laden()
            idx = self._system_cb.findData(key)
            if idx >= 0:
                self._system_cb.setCurrentIndex(idx)

    def _on_system_change(self, *_):
        self._aktueller_key = self._system_cb.currentData()  # None = "Alle"
        self._lade_eintraege()
        self._filtern()

    def _lade_eintraege(self):
        """Einträge der aktuellen Auswahl laden. Bei 'Alle' werden die Einträge
        aller Kategorien zusammengeführt; je Eintrag wird sein Kategorie-Key
        in self._eintrag_keys mitgeführt (für Speichern/Anzeige)."""
        self._eintraege = []
        self._eintrag_keys = []
        if self._aktueller_key is None:
            for key in sorted(self._registry, key=lambda k: self._registry[k]):
                for e in load_liste(ANL_DIR, key, "entries"):
                    self._eintraege.append(e)
                    self._eintrag_keys.append(key)
        else:
            key = self._aktueller_key
            for e in load_liste(ANL_DIR, key, "entries"):
                self._eintraege.append(e)
                self._eintrag_keys.append(key)

    def _kategorie_label(self, key):
        return self._registry.get(key, key)

    # ── Suche / Anzeige ───────────────────────────────────────────────────────

    def _suche_leeren(self):
        self._suche.clear()

    def _gefiltert(self):
        """
        Gibt (index, eintrag, treffer)-Tripel zurück, 'index' = Position in
        self._eintraege, 'treffer' ∈ {"Titel", "Inhalt", ""}.

        Sortierung: zuerst die präzisesten Treffer (Suchbegriff im Titel),
        danach die reinen Inhaltstreffer. So steht das Gesuchte mit der
        höchsten Trefferwahrscheinlichkeit ganz oben.

        WICHTIG: PyQt kopiert Python-dicts beim Speichern via
        QTableWidgetItem.setData()/data() (Roundtrip über QVariant) — die
        Objektidentität geht dabei verloren. Deshalb wird nur der Index (ein
        int, der den Roundtrip unverändert überlebt) in der Zelle abgelegt
        und beim Zugriff direkt in self._eintraege nachgeschlagen.
        """
        text = self._suche.text().strip().lower()
        if not text:
            return [(i, e, "") for i, e in enumerate(self._eintraege)]

        titel_treffer = []
        inhalt_treffer = []
        for i, e in enumerate(self._eintraege):
            if text in e.get("title", "").lower():
                titel_treffer.append((i, e, "Titel"))
            elif text in (e.get("content", "") or "").lower():
                inhalt_treffer.append((i, e, "Inhalt"))
        return titel_treffer + inhalt_treffer

    def _filtern(self, *_):
        gefiltert = self._gefiltert()
        self._tabelle.setRowCount(len(gefiltert))
        for row, (idx, eintrag, treffer) in enumerate(gefiltert):
            kategorie = self._kategorie_label(self._eintrag_keys[idx])
            werte = (kategorie, eintrag.get("title", ""), treffer)
            for col, wert in enumerate(werte):
                item = QTableWidgetItem(str(wert))
                item.setData(Qt.ItemDataRole.UserRole, idx)
                if col == 2 and treffer == "Titel":
                    item.setForeground(Qt.GlobalColor.green)
                self._tabelle.setItem(row, col, item)
        self._anzahl_lbl.setText(f"{len(gefiltert)} / {len(self._eintraege)} Einträge")
        self._detail_text.clear()
        self._pdf_btn.setEnabled(False)

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
            self._pdf_btn.setEnabled(False)
            return
        # Einfache Formatierung: doppelte Zeilenumbrüche als Absätze beibehalten,
        # überflüssige Leerzeichen entfernen (analog zur Fehlerdiagnose).
        inhalt = eintrag.get("content", "") or ""
        inhalt = re.sub(r"[ \t]+\n", "\n", inhalt)
        self._detail_text.setPlainText(inhalt)
        self._pdf_btn.setEnabled(self._pdf_pfad(eintrag) is not None)

    # ── PDF öffnen ──────────────────────────────────────────────────────────────

    def _pdf_pfad(self, eintrag):
        """Absoluten Pfad zur hinterlegten PDF liefern, falls vorhanden und
        die Datei tatsächlich existiert; sonst None."""
        rel = eintrag.get("file")
        if not rel:
            return None
        pfad = os.path.join(ANL_DIR, rel.replace("/", os.sep))
        return pfad if os.path.isfile(pfad) else None

    def _pdf_oeffnen(self):
        eintrag = self._ausgewaehlter_eintrag()
        if not eintrag:
            return
        pfad = self._pdf_pfad(eintrag)
        if not pfad:
            QMessageBox.information(self, "Hinweis", "Zu diesem Eintrag ist keine PDF hinterlegt.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(pfad))

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _neuer_eintrag(self):
        key = self._aktueller_key
        if key is None:
            QMessageBox.information(
                self, "Hinweis",
                "Bitte oben zuerst eine konkrete Kategorie auswählen (nicht „Alle“), "
                "um einen neuen Eintrag anzulegen.")
            return
        dlg = EintragDialog(_FELDER, titel="Neue Anleitung", parent=self)
        if dlg.exec():
            self._eintraege.append(dlg.werte())
            self._eintrag_keys.append(key)
            self._speichern_key(key)
            self._filtern()

    def _bearbeiten(self):
        idx = self._ausgewaehlter_index()
        eintrag = self._ausgewaehlter_eintrag()
        if not eintrag:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        dlg = EintragDialog(_FELDER, werte_init=dict(eintrag), titel="Anleitung bearbeiten", parent=self)
        if dlg.exec():
            # Nur die im Dialog vorhandenen Felder aktualisieren — sonst gingen
            # importierte Zusatzfelder wie "file"/"pages"/"id" verloren.
            eintrag.update(dlg.werte())  # gleiche Objektreferenz -> Original aktualisiert
            self._speichern_key(self._eintrag_keys[idx])
            self._filtern()

    def _loeschen(self):
        idx = self._ausgewaehlter_index()
        if idx is None:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        if QMessageBox.question(self, "Löschen", "Diesen Eintrag wirklich löschen?") != QMessageBox.StandardButton.Yes:
            return
        key = self._eintrag_keys[idx]
        del self._eintraege[idx]
        del self._eintrag_keys[idx]
        self._speichern_key(key)
        self._filtern()

    def _speichern_key(self, key):
        """Alle aktuell geladenen Einträge der Kategorie 'key' in deren JSON
        zurückschreiben (funktioniert auch im 'Alle'-Modus, da je Eintrag der
        zugehörige Key in self._eintrag_keys mitgeführt wird)."""
        items = [e for e, k in zip(self._eintraege, self._eintrag_keys) if k == key]
        save_liste(ANL_DIR, key, "entries", items)

    def _kopieren(self):
        text = self._detail_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
