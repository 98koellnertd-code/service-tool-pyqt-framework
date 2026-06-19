#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_bestellungen.py
Menüpunkt "Bestellung" — schnelles Erstellen von Ersatzteil-Bestellungen.

Eine Bestellung besteht aus Name, Datum und einer Liste von Positionen
(Bestellnummer, Name, Anzahl). Bestellungen werden als JSON unter
res/orders/<id>.json gespeichert — die id wird beim Speichern automatisch
fortlaufend vergeben (1, 2, 3, …). Gespeicherte Bestellungen können über
die Combobox "Bestellung laden" wieder geöffnet werden.

Häufig benötigte Ersatzteile lassen sich als Favoriten speichern
(res/orders/favoriten.json), um sie beim nächsten Mal schneller in eine
Bestellung übernehmen zu können. Positionen können außerdem jederzeit
manuell hinzugefügt/bearbeitet werden.

Da Seiten im Hauptfenster erst beim ersten Aufruf erzeugt werden (Lazy
Loading, siehe main.py), steht beim allerersten Öffnen dieses Menüs immer
automatisch eine neue, leere Bestellung bereit — __init__ ruft dafür
_neue_bestellung() auf.

Ein Doppelklick auf ein Ersatzteil im Menü "Ersatzteile" fügt dieses Teil
automatisch der hier aktuell offenen Bestellung hinzu — main.py verdrahtet
dafür das Signal ErsatzteileSeite.teil_hinzufuegen mit der öffentlichen
Methode teil_hinzufuegen() dieser Klasse.
"""

import os
import glob
import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSpinBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import pyqtSignal

from utils import (
    C, ORDERS_DIR, btn, lbl, make_combo, make_entry, load_json, save_json,
    get_bestellungen_export_dir, page_hero,
)
import export_excel
import export_pdf

FAVORITEN_FILE = os.path.join(ORDERS_DIR, "favoriten.json")


# ══════════════════════════════════════════════════════════════════════════════
# JSON-Verwaltung der Bestellungen (eine Datei pro Bestellung, Dateiname = id)
# ══════════════════════════════════════════════════════════════════════════════

def _pfad(bestell_id):
    """Pfad zur JSON-Datei einer Bestellung."""
    return os.path.join(ORDERS_DIR, f"{bestell_id}.json")


def _alle_ids():
    """Alle vorhandenen Bestell-IDs (aus den Dateinamen, favoriten.json ausgenommen)."""
    ids = []
    for path in glob.glob(os.path.join(ORDERS_DIR, "*.json")):
        stamm = os.path.splitext(os.path.basename(path))[0]
        if stamm.isdigit():
            ids.append(int(stamm))
    return sorted(ids)


def _naechste_id():
    """Nächste freie Bestell-ID — höchste vorhandene + 1, sonst 1."""
    ids = _alle_ids()
    return (ids[-1] + 1) if ids else 1


def _bestellung_laden(bestell_id):
    return load_json(_pfad(bestell_id), {})


def _bestellung_speichern(bestell_id, daten):
    save_json(_pfad(bestell_id), daten)


def _bestellung_loeschen(bestell_id):
    try:
        os.remove(_pfad(bestell_id))
    except OSError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Seite "Bestellung"
# ══════════════════════════════════════════════════════════════════════════════

class BestellungenSeite(QWidget):
    """Erstellen, Laden, Bearbeiten und Exportieren von Ersatzteil-Bestellungen."""

    status_msg = pyqtSignal(str)

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)
        self._profile = profile or {}
        self._aktuelle_id = None          # None = neue, noch nicht gespeicherte Bestellung
        self._favoriten = load_json(FAVORITEN_FILE, [])
        self._build()
        self._laden_liste_aktualisieren()
        self._neue_bestellung()           # beim Öffnen immer mit leerer Bestellung starten

    # ── Aufbau ───────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/bestellung.png", "Bestellung",
            "Ersatzteil-Bestellungen zusammenstellen, speichern und exportieren",
        )) 

        # Kopfzeile (Steuerleiste): Bestellung laden/neu/löschen
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)

        hl.addWidget(lbl("Bestellung laden:", C["subtext"]))
        self._laden_cb = make_combo([], 280)
        self._laden_cb.currentIndexChanged.connect(self._on_laden_gewaehlt)
        hl.addWidget(self._laden_cb)

        hl.addWidget(btn("🆕 Neue Bestellung", self._neue_bestellung,
                         "Aktuelle Eingabe verwerfen und eine neue, leere Bestellung beginnen"))
        hl.addWidget(btn("🗑 Bestellung löschen", self._bestellung_loeschen_klick,
                         "Die aktuell geladene, gespeicherte Bestellung endgültig löschen", color=C["red"]))
        hl.addStretch()
        root.addWidget(hdr)

        # Kopfdaten: Name + Datum
        kopf = QFrame()
        kopf.setStyleSheet(f"background:{C['header']}; border-bottom:1px solid {C['border']};")
        kl = QHBoxLayout(kopf)
        kl.setContentsMargins(14, 6, 14, 6)
        kl.setSpacing(8)
        kl.addWidget(lbl("Name:", C["subtext"]))
        self._name_feld = make_entry("Name des Bestellers", 220)
        kl.addWidget(self._name_feld)
        kl.addWidget(lbl("Datum:", C["subtext"]))
        self._datum_feld = make_entry("TT.MM.JJJJ", 110)
        kl.addWidget(self._datum_feld)
        kl.addStretch()
        self._id_lbl = lbl("", C["dimtext"], size=9)
        kl.addWidget(self._id_lbl)
        root.addWidget(kopf)

        # Favoriten-Zeile — schnelles Hinzufügen oft benötigter Ersatzteile
        fav = QFrame()
        fav.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        fl = QHBoxLayout(fav)
        fl.setContentsMargins(14, 6, 14, 6)
        fl.setSpacing(8)
        fl.addWidget(lbl("⭐ Favorit:", C["subtext"]))
        self._fav_cb = make_combo([], 280)
        fl.addWidget(self._fav_cb)
        fl.addWidget(btn("➕ Übernehmen", self._favorit_uebernehmen,
                         "Ausgewählten Favoriten der Bestellung hinzufügen"))
        fl.addWidget(btn("☆ Auswahl als Favorit", self._favorit_speichern,
                         "Markierte Tabellenzeile als Favorit speichern"))
        fl.addWidget(btn("🗑 Favorit entfernen", self._favorit_entfernen,
                         "Ausgewählten Favoriten aus der Liste entfernen", color=C["red"]))
        fl.addStretch()
        root.addWidget(fav)

        # Tabelle der Positionen (Ersatzteile dieser Bestellung)
        self._tabelle = QTableWidget()
        self._tabelle.setColumnCount(3)
        self._tabelle.setHorizontalHeaderLabels(["Bestellnummer", "Name", "Anzahl"])
        self._tabelle.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabelle.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabelle.verticalHeader().setVisible(False)
        self._tabelle.setColumnWidth(0, 160)
        self._tabelle.setColumnWidth(2, 90)
        self._tabelle.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._tabelle, 1)

        # Aktionsleiste
        akt = QFrame()
        akt.setStyleSheet(f"background:{C['surface']}; border-top:1px solid {C['border']};")
        al = QHBoxLayout(akt)
        al.setContentsMargins(14, 8, 14, 8)
        al.setSpacing(8)
        al.addWidget(btn("＋ Position hinzufügen", self._position_hinzufuegen, color=C["green"]))
        al.addWidget(btn("🗑 Position entfernen", self._position_entfernen, color=C["red"]))
        al.addStretch()
        al.addWidget(btn("💾 Speichern", self._speichern))
        al.addWidget(btn("📊 Excel-Export", self._exportieren, color=C["accent"]))
        al.addWidget(btn("📄 PDF-Export", self._exportieren_pdf, color=C["green"]))
        root.addWidget(akt)

        self._favoriten_combo_aktualisieren()

    # ── Neue Bestellung / Laden / Löschen ──────────────────────────────────────

    def _neue_bestellung(self):
        """Setzt das Formular auf eine frische, leere Bestellung zurück."""
        self._aktuelle_id = None
        self._tabelle.setRowCount(0)
        name = f"{self._profile.get('vorname','')} {self._profile.get('nachname','')}".strip()
        self._name_feld.setText(name)
        self._datum_feld.setText(datetime.date.today().strftime("%d.%m.%Y"))
        self._id_lbl.setText("Neue Bestellung (noch nicht gespeichert)")
        self._laden_cb.blockSignals(True)
        self._laden_cb.setCurrentIndex(-1)
        self._laden_cb.blockSignals(False)

    def _laden_liste_aktualisieren(self, auswahl_id=None):
        """Combo mit allen gespeicherten Bestellungen neu befüllen (neueste zuerst)."""
        self._laden_cb.blockSignals(True)
        self._laden_cb.clear()
        for bid in reversed(_alle_ids()):
            daten = _bestellung_laden(bid)
            anzeige_name = daten.get("name", "")
            datum = daten.get("datum", "")
            self._laden_cb.addItem(f"#{bid}  –  {anzeige_name}  –  {datum}", bid)
        if auswahl_id is not None:
            idx = self._laden_cb.findData(auswahl_id)
            if idx >= 0:
                self._laden_cb.setCurrentIndex(idx)
        else:
            self._laden_cb.setCurrentIndex(-1)
        self._laden_cb.blockSignals(False)

    def _on_laden_gewaehlt(self, *_):
        bid = self._laden_cb.currentData()
        if bid is None:
            return
        daten = _bestellung_laden(bid)
        if not daten:
            return
        self._aktuelle_id = bid
        self._name_feld.setText(daten.get("name", ""))
        self._datum_feld.setText(daten.get("datum", ""))
        self._id_lbl.setText(f"Bestellung #{bid}")
        self._tabelle.setRowCount(0)
        for teil in daten.get("teile", []):
            self._zeile_hinzufuegen(teil.get("order_no", ""), teil.get("name", ""), teil.get("anzahl", 1))
        self.status_msg.emit(f"📂  Bestellung #{bid} geladen.")

    def _bestellung_loeschen_klick(self):
        if self._aktuelle_id is None:
            QMessageBox.information(self, "Hinweis", "Diese Bestellung wurde noch nicht gespeichert.")
            return
        if QMessageBox.question(
                self, "Löschen", f"Bestellung #{self._aktuelle_id} wirklich endgültig löschen?"
        ) != QMessageBox.StandardButton.Yes:
            return
        geloeschte_id = self._aktuelle_id
        _bestellung_loeschen(geloeschte_id)
        self._neue_bestellung()
        self._laden_liste_aktualisieren()
        self.status_msg.emit(f"🗑  Bestellung #{geloeschte_id} gelöscht.")

    # ── Positionen (Ersatzteile in der Bestellung) ───────────────────────────────

    def _anzahl_spinbox(self, wert=1):
        """Eigenes SpinBox-Widget je Zeile statt Freitext — verhindert ungültige
        Mengenangaben und lässt sich bequem mit den Pfeiltasten anpassen."""
        spin = QSpinBox()
        spin.setRange(1, 9999)
        try:
            spin.setValue(max(1, int(wert)))
        except (TypeError, ValueError):
            spin.setValue(1)
        spin.setFixedWidth(70)
        return spin

    def _zeile_hinzufuegen(self, order_no="", name="", anzahl=1):
        row = self._tabelle.rowCount()
        self._tabelle.insertRow(row)
        self._tabelle.setItem(row, 0, QTableWidgetItem(order_no))
        self._tabelle.setItem(row, 1, QTableWidgetItem(name))
        self._tabelle.setCellWidget(row, 2, self._anzahl_spinbox(anzahl))
        return row

    def _position_hinzufuegen(self):
        """Manuelles Hinzufügen einer leeren Position zum direkten Ausfüllen."""
        row = self._zeile_hinzufuegen("", "", 1)
        self._tabelle.setCurrentCell(row, 0)
        self._tabelle.editItem(self._tabelle.item(row, 0))

    def _position_entfernen(self):
        row = self._tabelle.currentRow()
        if row < 0:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst eine Position auswählen.")
            return
        self._tabelle.removeRow(row)

    def _zeile_index_fuer_order_no(self, order_no):
        """Liefert die Tabellenzeile mit dieser Bestellnummer, falls bereits vorhanden."""
        if not order_no:
            return None
        for row in range(self._tabelle.rowCount()):
            item = self._tabelle.item(row, 0)
            if item and item.text().strip() == order_no.strip():
                return row
        return None

    def teil_hinzufuegen(self, teil):
        """
        Von außen aufgerufen (siehe main.py): fügt ein Ersatzteil — z.B. per
        Doppelklick im Menü 'Ersatzteile' oder per Favorit — der aktuellen
        Bestellung hinzu. Ist die Bestellnummer schon in der Tabelle, wird
        nur die Anzahl um 1 erhöht statt eine doppelte Zeile anzulegen.
        """
        order_no = (teil.get("order_no") or "").strip()
        name = (teil.get("name") or "").strip()
        if not order_no and not name:
            return
        row = self._zeile_index_fuer_order_no(order_no)
        if row is not None:
            spin = self._tabelle.cellWidget(row, 2)
            if spin:
                spin.setValue(spin.value() + 1)
        else:
            self._zeile_hinzufuegen(order_no, name, 1)

    def _tabellen_daten(self):
        """Liest die aktuellen Positionen aus der Tabelle aus."""
        teile = []
        for row in range(self._tabelle.rowCount()):
            order_item = self._tabelle.item(row, 0)
            name_item = self._tabelle.item(row, 1)
            spin = self._tabelle.cellWidget(row, 2)
            order_no = order_item.text().strip() if order_item else ""
            name = name_item.text().strip() if name_item else ""
            anzahl = spin.value() if spin else 1
            if order_no or name:
                teile.append({"order_no": order_no, "name": name, "anzahl": anzahl})
        return teile

    # ── Favoriten ─────────────────────────────────────────────────────────────

    def _favoriten_combo_aktualisieren(self):
        self._fav_cb.blockSignals(True)
        self._fav_cb.clear()
        for fav in self._favoriten:
            self._fav_cb.addItem(f"{fav.get('order_no','')}  –  {fav.get('name','')}", fav)
        self._fav_cb.blockSignals(False)

    def _favorit_uebernehmen(self):
        fav = self._fav_cb.currentData()
        if not fav:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Favoriten auswählen.")
            return
        self.teil_hinzufuegen(fav)

    def _favorit_speichern(self):
        row = self._tabelle.currentRow()
        if row < 0:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst eine Position in der Tabelle auswählen.")
            return
        order_item = self._tabelle.item(row, 0)
        name_item = self._tabelle.item(row, 1)
        order_no = order_item.text().strip() if order_item else ""
        name = name_item.text().strip() if name_item else ""
        if not order_no and not name:
            return
        if any(f.get("order_no") == order_no and f.get("name") == name for f in self._favoriten):
            QMessageBox.information(self, "Hinweis", "Dieser Favorit ist bereits gespeichert.")
            return
        self._favoriten.append({"order_no": order_no, "name": name})
        save_json(FAVORITEN_FILE, self._favoriten)
        self._favoriten_combo_aktualisieren()
        self.status_msg.emit(f"⭐  Favorit gespeichert: {name or order_no}")

    def _favorit_entfernen(self):
        idx = self._fav_cb.currentIndex()
        if idx < 0:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst einen Favoriten auswählen.")
            return
        del self._favoriten[idx]
        save_json(FAVORITEN_FILE, self._favoriten)
        self._favoriten_combo_aktualisieren()

    # ── Speichern / Exportieren ──────────────────────────────────────────────────

    def _aktuelle_daten(self):
        return {
            "id": self._aktuelle_id,
            "name": self._name_feld.text().strip(),
            "datum": self._datum_feld.text().strip(),
            "teile": self._tabellen_daten(),
        }

    def _speichern(self):
        if not self._tabellen_daten():
            QMessageBox.information(self, "Hinweis", "Die Bestellung hat noch keine Positionen.")
            return
        # Neue Bestellung -> jetzt erst eine fortlaufende id vergeben (1, 2, 3, …).
        if self._aktuelle_id is None:
            self._aktuelle_id = _naechste_id()
        daten = self._aktuelle_daten()
        daten["id"] = self._aktuelle_id
        _bestellung_speichern(self._aktuelle_id, daten)
        self._id_lbl.setText(f"Bestellung #{self._aktuelle_id}")
        self._laden_liste_aktualisieren(auswahl_id=self._aktuelle_id)
        self.status_msg.emit(f"💾  Bestellung #{self._aktuelle_id} gespeichert.")

    def _exportieren(self):
        if not self._tabellen_daten():
            QMessageBox.information(self, "Hinweis", "Die Bestellung hat noch keine Positionen.")
            return
        # Vor dem Export speichern, damit der JSON-Stand zum exportierten
        # Excel passt (und eine neue Bestellung dabei ihre id bekommt).
        self._speichern()
        daten = self._aktuelle_daten()
        dateiname = export_excel.default_bestellung_filename(daten)
        export_dir = get_bestellungen_export_dir(self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Bestellung exportieren",
            os.path.join(export_dir, dateiname),
            "Excel-Dateien (*.xlsx)")
        if not dest:
            return
        try:
            export_excel.export_bestellung(dest, daten)
            self.status_msg.emit(f"✅  Bestellung exportiert: {dest}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{exc}")

    def _exportieren_pdf(self):
        if not self._tabellen_daten():
            QMessageBox.information(self, "Hinweis", "Die Bestellung hat noch keine Positionen.")
            return
        # Vor dem Export speichern, damit der JSON-Stand zur exportierten
        # PDF passt (und eine neue Bestellung dabei ihre id bekommt).
        self._speichern()
        daten = self._aktuelle_daten()
        dateiname = export_pdf.default_bestellung_pdf_name(daten)
        export_dir = get_bestellungen_export_dir(self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Bestellung als PDF exportieren",
            os.path.join(export_dir, dateiname),
            "PDF-Dateien (*.pdf)")
        if not dest:
            return
        try:
            export_pdf.export_bestellung(dest, daten)
            self.status_msg.emit(f"✅  Bestellung als PDF exportiert: {dest}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"PDF-Export fehlgeschlagen:\n{exc}")
