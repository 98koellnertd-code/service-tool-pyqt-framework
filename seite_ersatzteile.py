#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_ersatzteile.py
Menüpunkt "Ersatzteile" — Ersatzteilkatalog je Gerätesystem.

Daten liegen in res/et/<system>.json mit Format {"parts": [...]}.
Welche Systeme es gibt, steht in res/et/systeme.json (key -> Anzeigename).
Neue Systeme und neue Einträge können direkt im Tool angelegt werden.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils import C, ET_DIR, btn, lbl, make_combo, page_hero
from katalog_utils import (
    load_registry, save_registry, load_liste, save_liste,
    NeuesSystemDialog, EintragDialog, SONSTIGES,
)

# Standard-Systeme, die beim allerersten Start angelegt werden (Registry leer).
_STANDARD_SYSTEME = {
    "aj5": "alphaJET 5 (HS · HS-M · SP)",
    "ajx": "alphaJET 5 X / X-FP",
    "ajd": "alphaJET D (evo · into · mondo · tempo/pico)",
}

# Feldspezifikation für den Editier-Dialog: (key, Label, Art)
# Baugruppe = einzelne Auswahl (checkbox_single), Modelle = Mehrfachauswahl
# (checkbox_multi) — beide zeigen vorhandene Werte als Checkboxen an und
# erlauben über das "Neu:"-Feld zusätzlich neue Werte (siehe katalog_utils.py).
_FELDER = [
    ("order_no", "Bestell-Nr.", "text"),
    ("name",     "Bezeichnung", "mehrzeilig"),
    ("group_de", "Baugruppe",   "checkbox_single"),
    ("sources",  "Modelle",     "checkbox_multi"),
]

# Tabellenspalten: (key, Überschrift, Breite)
_SPALTEN = [
    ("order_no", "Bestell-Nr.", 120),
    ("name",     "Bezeichnung", 420),
    ("group_de", "Baugruppe",   140),
    ("sources",  "Modelle",     170),
]


class ErsatzteileSeite(QWidget):
    """Ersatzteilkatalog mit System-Auswahl, Suche und CRUD-Funktionen."""

    # Wird bei Doppelklick auf einen Eintrag ausgelöst (dict mit order_no/name).
    # main.py verdrahtet dieses Signal mit der Bestellungen-Seite, damit das
    # Teil dort automatisch der aktuellen Bestellung hinzugefügt wird.
    teil_hinzufuegen = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = load_registry(ET_DIR, _STANDARD_SYSTEME)
        self._teile = []          # alle Einträge des aktuell gewählten Systems
        self._aktueller_key = None
        self._build()
        self._systeme_neu_laden(initial=True)

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/ersatzteile.png", "Ersatzteile",
            "Ersatzteilkatalog je Gerätesystem durchsuchen und pflegen",
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

        neues_sys_btn = btn("＋ Neues System", self._neues_system, "Neues Gerätesystem anlegen")
        hl.addWidget(neues_sys_btn)
        hl.addStretch()
        root.addWidget(hdr)

        # Such-/Filterzeile
        filt = QFrame()
        filt.setStyleSheet(f"background:{C['header']}; border-bottom:1px solid {C['border']};")
        fl = QHBoxLayout(filt)
        fl.setContentsMargins(14, 6, 14, 6)
        fl.setSpacing(8)
        fl.addWidget(lbl("🔍", C["subtext"]))
        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Suche nach Bestell-Nr. oder Bezeichnung…")
        self._suche.textChanged.connect(self._filtern)
        fl.addWidget(self._suche, 1)

        fl.addWidget(lbl("Baugruppe:", C["subtext"]))
        self._gruppe_cb = make_combo(["Alle"], 160)
        self._gruppe_cb.currentIndexChanged.connect(self._filtern)
        fl.addWidget(self._gruppe_cb)

        leeren_btn = btn("✕ Suche leeren", self._suche_leeren)
        fl.addWidget(leeren_btn)

        self._anzahl_lbl = lbl("", C["dimtext"], size=9)
        fl.addWidget(self._anzahl_lbl)
        root.addWidget(filt)

        # Tabelle
        self._tabelle = QTableWidget()
        self._tabelle.setColumnCount(len(_SPALTEN))
        self._tabelle.setHorizontalHeaderLabels([s[1] for s in _SPALTEN])
        self._tabelle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabelle.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabelle.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabelle.verticalHeader().setVisible(False)
        for i, (_, _, breite) in enumerate(_SPALTEN):
            self._tabelle.setColumnWidth(i, breite)
        self._tabelle.horizontalHeader().setSectionResizeMode(
            len(_SPALTEN) - 1, QHeaderView.ResizeMode.Stretch)
        self._tabelle.doubleClicked.connect(self._kopieren)
        root.addWidget(self._tabelle, 1)

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
        al.addWidget(lbl("Doppelklick = Bestell-Nr. kopieren & zur Bestellung hinzufügen", C["dimtext"], size=9))
        root.addWidget(akt)

    # ── Systeme verwalten ─────────────────────────────────────────────────────

    def _systeme_neu_laden(self, initial=False):
        """Füllt die System-Combobox aus der Registry (alphabetisch nach Label)."""
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
            save_registry(ET_DIR, self._registry)
            save_liste(ET_DIR, key, "parts", [])  # leere JSON-Datei anlegen
            self._systeme_neu_laden()
            # neu angelegtes System direkt auswählen
            idx = self._system_cb.findData(key)
            if idx >= 0:
                self._system_cb.setCurrentIndex(idx)

    def _on_system_change(self, *_):
        key = self._system_cb.currentData()
        if not key:
            return
        self._aktueller_key = key
        self._teile = load_liste(ET_DIR, key, "parts")
        self._gruppen_combo_aktualisieren()
        self._filtern()

    def _gruppen_combo_aktualisieren(self):
        gruppen = sorted({(t.get("group_de") or SONSTIGES) for t in self._teile})
        self._gruppe_cb.blockSignals(True)
        self._gruppe_cb.clear()
        self._gruppe_cb.addItems(["Alle"] + gruppen)
        self._gruppe_cb.blockSignals(False)

    def _baugruppen_optionen(self):
        """Vorhandene Baugruppen des aktuellen Systems (für die Checkboxen
        im Dialog), 'Sonstiges' immer dabei, da auch der Fallback-Wert ist."""
        gruppen = sorted({(t.get("group_de") or "") for t in self._teile if t.get("group_de")})
        if SONSTIGES not in gruppen:
            gruppen.append(SONSTIGES)
        return gruppen

    def _modelle_optionen(self):
        """Vorhandene Modelle (sources) des aktuellen Systems, gesammelt aus
        allen bisherigen Einträgen, damit man nicht jedes Mal neu tippen muss."""
        modelle = set()
        for t in self._teile:
            quellen = t.get("sources", [])
            if isinstance(quellen, list):
                modelle.update(q for q in quellen if q)
        return sorted(modelle)

    # ── Suche / Filter ────────────────────────────────────────────────────────

    def _suche_leeren(self):
        self._suche.clear()
        self._gruppe_cb.setCurrentIndex(0)

    def _gefiltert(self):
        """
        Gibt (index, eintrag)-Paare zurück, wobei 'index' die Position in
        self._teile ist. WICHTIG: PyQt kopiert Python-dicts beim Speichern
        via QTableWidgetItem.setData()/data() (Roundtrip über QVariant) —
        die Objektidentität geht dabei verloren. Deshalb wird hier nur der
        Index (ein int, der den Roundtrip unverändert überlebt) in der
        Tabellenzelle abgelegt, und beim Zugriff direkt in self._teile
        nachgeschlagen. So zeigen Bearbeiten/Löschen immer auf den
        echten Eintrag.
        """
        text = self._suche.text().strip().lower()
        gruppe = self._gruppe_cb.currentText()
        ergebnis = []
        for idx, t in enumerate(self._teile):
            if gruppe != "Alle" and (t.get("group_de") or SONSTIGES) != gruppe:
                continue
            if text and text not in t.get("order_no", "").lower() and text not in t.get("name", "").lower():
                continue
            ergebnis.append((idx, t))
        return ergebnis

    def _filtern(self, *_):
        gefiltert = self._gefiltert()
        self._tabelle.setRowCount(len(gefiltert))
        for row, (idx, teil) in enumerate(gefiltert):
            for col, (key, _, _) in enumerate(_SPALTEN):
                wert = teil.get(key, "")
                if isinstance(wert, list):
                    wert = ", ".join(wert)
                if key == "group_de" and not wert:
                    wert = SONSTIGES
                item = QTableWidgetItem(str(wert))
                item.setData(Qt.ItemDataRole.UserRole, idx)
                self._tabelle.setItem(row, col, item)
        self._anzahl_lbl.setText(f"{len(gefiltert)} / {len(self._teile)} Einträge")

    def _ausgewaehlter_index(self):
        row = self._tabelle.currentRow()
        if row < 0:
            return None
        item = self._tabelle.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _ausgewaehlter_eintrag(self):
        idx = self._ausgewaehlter_index()
        if idx is None or idx >= len(self._teile):
            return None
        return self._teile[idx]

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _optionen_fuer_dialog(self):
        return {"group_de": self._baugruppen_optionen(), "sources": self._modelle_optionen()}

    def _neuer_eintrag(self):
        if not self._aktueller_key:
            return
        dlg = EintragDialog(_FELDER, titel="Neues Ersatzteil", parent=self,
                             options_map=self._optionen_fuer_dialog())
        if dlg.exec():
            werte = dlg.werte()
            werte["group_de"] = werte.get("group_de") or SONSTIGES
            self._teile.append(werte)
            self._speichern()
            self._gruppen_combo_aktualisieren()
            self._filtern()

    def _bearbeiten(self):
        teil = self._ausgewaehlter_eintrag()
        if not teil:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        werte_init = dict(teil)
        werte_init["group_de"] = teil.get("group_de") or SONSTIGES
        dlg = EintragDialog(_FELDER, werte_init=werte_init, titel="Ersatzteil bearbeiten", parent=self,
                             options_map=self._optionen_fuer_dialog())
        if dlg.exec():
            werte = dlg.werte()
            werte["group_de"] = werte.get("group_de") or SONSTIGES
            teil.clear()
            teil.update(werte)  # gleiche Objektreferenz -> Original in self._teile wird aktualisiert
            self._speichern()
            self._gruppen_combo_aktualisieren()
            self._filtern()

    def _loeschen(self):
        idx = self._ausgewaehlter_index()
        if idx is None:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Eintrag auswählen.")
            return
        if QMessageBox.question(self, "Löschen", "Diesen Eintrag wirklich löschen?") != QMessageBox.StandardButton.Yes:
            return
        del self._teile[idx]
        self._speichern()
        self._gruppen_combo_aktualisieren()
        self._filtern()

    def _speichern(self):
        save_liste(ET_DIR, self._aktueller_key, "parts", self._teile)

    def _kopieren(self):
        """
        Bei Doppelklick: Bestell-Nr. in die Zwischenablage kopieren UND das
        Teil automatisch der aktuellen Bestellung hinzufügen (siehe
        teil_hinzufuegen-Signal, verdrahtet in main.py).
        """
        teil = self._ausgewaehlter_eintrag()
        if not teil:
            return
        if teil.get("order_no"):
            QApplication.clipboard().setText(teil["order_no"])
        self.teil_hinzufuegen.emit({"order_no": teil.get("order_no", ""), "name": teil.get("name", "")})
