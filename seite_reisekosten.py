#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_reisekosten.py
Menüpunkt "Reisekosten" — Wochenansicht (KW) für Reisekostenerfassung.

Zeigt Mo–So mit allen Feldern inkl. Mahlzeiten und Sonstiges.
Daten werden automatisch nach SF-Import lokal gespeichert.
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSplitter,
    QSpinBox, QLineEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils import (
    C, KW_DIR, load_json, save_json, current_kw, week_dates,
    get_reisekosten_export_dir, find_reisekosten_template,
    btn, lbl, page_hero,
)
from gemeinsame_widgets import DetailPanel, DayRow
from workers import SFLoadWorker
import export_excel
import export_pdf


class ReisekostenPage(QWidget):
    """
    Wochenansicht (KW) für Reisekostenerfassung.
    Zeigt Mo–So mit allen Feldern inkl. Mahlzeiten und Sonstiges.
    """
    status_msg = pyqtSignal(str)

    def __init__(self, get_sf, get_wohnort, profile, parent=None):
        super().__init__(parent)
        self._get_sf      = get_sf
        self._get_wohnort = get_wohnort
        self._profile     = profile
        kw, yr = current_kw()
        self._kw   = kw
        self._year = yr
        self._day_data: dict = {}
        self._extras: dict   = {}
        self._rows:  dict    = {}
        self._selected: str | None = None
        self._build()
        self._load_local()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/reisekosten.png", "Reisekosten",
            "Reisekosten je Kalenderwoche erfassen und als Abrechnung exportieren",
        ))    

        # ── Kopfzeile (Steuerleiste) ────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        hl  = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)

        hl.addWidget(lbl("KW", C["subtext"]))

        self._kw_sb = QSpinBox()
        self._kw_sb.setRange(1, 53)
        self._kw_sb.setValue(self._kw)
        self._kw_sb.setFixedWidth(72)
        self._kw_sb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._kw_sb.valueChanged.connect(self._on_kw_change)
        hl.addWidget(self._kw_sb)

        hl.addWidget(lbl("/", C["subtext"]))
        self._yr_sb = QSpinBox()
        self._yr_sb.setRange(2020, 2099)
        self._yr_sb.setValue(self._year)
        self._yr_sb.setFixedWidth(90)
        self._yr_sb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._yr_sb.valueChanged.connect(self._on_kw_change)
        hl.addWidget(self._yr_sb)

        self._range_lbl = lbl("", C["dimtext"], size=9)
        hl.addWidget(self._range_lbl)
        hl.addStretch()

        sf_btn = btn("☁  Von SF laden", self._load_from_sf, "Wochendaten aus Salesforce laden", color=C["accent"])
        hl.addWidget(sf_btn)

        save_btn = btn("💾  Speichern", self._save_kw, "KW-Daten lokal speichern", color=C["green"])
        hl.addWidget(save_btn)

        export_btn = btn("📊  Excel-Export", self._export_reisekosten,
                          "Reisekostenabrechnung (FB_0020) für diese KW exportieren")
        hl.addWidget(export_btn)

        pdf_btn = btn("📄  PDF-Export", self._export_reisekosten_pdf,
                      "Reisekostenabrechnung für diese KW als PDF exportieren")
        hl.addWidget(pdf_btn)
        root.addWidget(hdr)

        # ── Spaltenköpfe ───────────────────────────────────────────────────────
        col_hdr = QFrame()
        col_hdr.setStyleSheet(f"background:{C['header']}; border-bottom:1px solid {C['border']};")
        cl = QHBoxLayout(col_hdr)
        cl.setContentsMargins(8, 4, 8, 4)
        cl.setSpacing(6)
        for txt, w in [("Wt", 26), ("Datum", 76), ("Status", 110),
                       ("Start", 62), ("Ende", 62), ("P", 44), ("Std", 46)]:
            lb = lbl(txt, C["accent"])
            lb.setFixedWidth(w)
            cl.addWidget(lbl(" ", size=8) if txt in ("Start", "Ende", "P") else lb)
            if txt in ("Start", "Ende", "P"):
                cl.addWidget(lb)
        cl.addWidget(lbl("Einträge / Zusammenfassung", C["accent"]))
        cl.addStretch()
        root.addWidget(col_hdr)        

        # ── Splitter: Liste + Detail ───────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        scroll.setWidget(self._list_widget)
        splitter.addWidget(scroll)

        self._detail = DetailPanel(show_meals=True, parent=self)
        self._detail.saved.connect(self._on_entry_saved)
        splitter.addWidget(self._detail)

        splitter.setSizes([380, 240])
        root.addWidget(splitter, 1)

        # ── Sonstiges-Zeile ────────────────────────────────────────────────────
        ebar = QFrame()
        ebar.setStyleSheet(f"background:{C['surface']}; border-top:1px solid {C['border']};")
        el = QHBoxLayout(ebar)
        el.setContentsMargins(14, 6, 14, 6)
        el.setSpacing(8)
        el.addWidget(lbl("💰  Sonstiges €:", C["subtext"]))
        self._sonstiges_val = QLineEdit()
        self._sonstiges_val.setFixedWidth(80)
        self._sonstiges_val.setPlaceholderText("0.00")
        el.addWidget(self._sonstiges_val)
        el.addWidget(lbl("Bezeichnung:", C["subtext"]))
        self._sonstiges_txt = QLineEdit()
        self._sonstiges_txt.setFixedWidth(220)
        self._sonstiges_txt.setPlaceholderText("Parkgebühren, Maut, Fähre…")
        el.addWidget(self._sonstiges_txt)
        el.addStretch()
        root.addWidget(ebar)

    # ── KW-Wechsel ─────────────────────────────────────────────────────────────

    def _on_kw_change(self, *_):
        self._kw   = self._kw_sb.value()
        self._year = self._yr_sb.value()
        self._load_local()

    def _load_local(self):
        dates = week_dates(self._year, self._kw)
        self._range_lbl.setText(
            f"{dates[0].strftime('%d.%m.')} – {dates[-1].strftime('%d.%m.%Y')}")
        path = os.path.join(KW_DIR, f"{self._year}-W{self._kw:02d}.json")
        raw  = load_json(path, {})
        self._extras = raw.pop("_extras", {})
        self._day_data = raw
        self._selected = None
        self._rebuild_list(dates)
        self._sonstiges_val.setText(self._extras.get("sonstiges", ""))
        self._sonstiges_txt.setText(self._extras.get("sonstiges_txt", ""))

    def _rebuild_list(self, dates=None):
        if dates is None:
            dates = week_dates(self._year, self._kw)
        while self._list_layout.count():
            w = self._list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._rows.clear()

        for i, d in enumerate(dates):
            ds = d.isoformat()
            if ds not in self._day_data:
                self._day_data[ds] = {}
            row = DayRow(d, self._day_data[ds], alt=(i % 2 == 0))
            row.clicked.connect(self._select_day)
            self._rows[ds] = row
            self._list_layout.addWidget(row)

        self._list_layout.addStretch()

    def _select_day(self, iso_date):
        if self._selected and self._selected in self._rows:
            self._rows[self._selected].select(False)
        self._selected = iso_date
        self._rows[iso_date].select(True)
        day_data = self._day_data.setdefault(iso_date, {})
        if not day_data.get("entries"):
            day_data.setdefault("entries", [{}])
        self._detail.load_day(iso_date, day_data, self._get_wohnort())

    def _on_entry_saved(self, iso_date, day_data):
        self._day_data[iso_date] = day_data
        if iso_date in self._rows:
            self._rows[iso_date].refresh()
        self.status_msg.emit(f"Eintrag {iso_date} übernommen — bitte noch KW speichern!")

    # ── SF laden ───────────────────────────────────────────────────────────────

    def _load_from_sf(self):
        sf = self._get_sf()
        if not sf:
            QMessageBox.warning(self, "Hinweis", "Bitte zuerst bei Salesforce anmelden.")
            return
        token, inst_url, user_id = sf
        dates = week_dates(self._year, self._kw)
        self._sf_worker = SFLoadWorker(
            token, inst_url, user_id,
            dates[0].isoformat(), dates[-1].isoformat(), self._get_wohnort())
        self._sf_worker.success.connect(self._on_sf_success)
        self._sf_worker.error.connect(self._on_sf_error)
        self._sf_worker.progress.connect(lambda m: self.status_msg.emit(m))
        self._sf_worker.start()
        self.status_msg.emit("🔄  Lade Daten aus Salesforce…")

    def _on_sf_success(self, new_data):
        self._day_data.update(new_data)
        self._rebuild_list()
        self._save_kw(silent=True)
        count = len(new_data)
        self.status_msg.emit(f"✅  {count} Tag(e) geladen und gespeichert.")
        QMessageBox.information(self, "SF Laden",
            f"✅  {count} Tag(e) geladen.\nDaten wurden automatisch gespeichert.")

    def _on_sf_error(self, err):
        self.status_msg.emit(f"❌  SF-Fehler: {err[:80]}")
        QMessageBox.critical(self, "Salesforce Fehler", err)

    # ── Excel-Export (Reisekostenabrechnung FB_0020) ───────────────────────────

    def _export_reisekosten(self):
        """Reisekostenabrechnung der aktuellen KW als Excel exportieren (FB_0020-Vorlage)."""
        tmpl = find_reisekosten_template()
        if not tmpl:
            QMessageBox.warning(
                self, "Vorlage fehlt",
                "Die Vorlage 'FB_0020 Reisekostenabrechnung' wurde im Ordner "
                "res/templates nicht gefunden.\nBitte die Vorlage dort ablegen.")
            return

        export_dir = get_reisekosten_export_dir(self._profile)
        default_name = export_excel.default_reisekosten_filename(self._kw, self._year, self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Reisekostenabrechnung speichern",
            os.path.join(export_dir, default_name),
            "Excel (*.xlsx)")
        if not dest:
            return

        # Aktuelle (ggf. noch ungespeicherte) KW-Daten + lokal gespeicherte
        # KW-Datei zusammenführen, damit Änderungen sofort exportiert werden.
        path = os.path.join(KW_DIR, f"{self._year}-W{self._kw:02d}.json")
        kw_data = load_json(path, {})
        kw_data.update(self._day_data)
        kw_data["_extras"] = {
            "sonstiges":     self._sonstiges_val.text(),
            "sonstiges_txt": self._sonstiges_txt.text(),
        }

        try:
            block = export_excel.export_reisekosten(
                tmpl, dest, kw_data, self._kw, self._year,
                self._profile, self._get_wohnort())
            self.status_msg.emit(f"✅  Reisekostenabrechnung exportiert: {dest}")
            QMessageBox.information(
                self, "Exportiert",
                f"Reisekostenabrechnung gespeichert:\n{dest}\n\n"
                f"KW {self._kw} / {self._year}  –  {block} Einträge")
        except Exception as e:
            QMessageBox.critical(self, "Excel-Fehler", str(e))

    def _export_reisekosten_pdf(self):
        """Reisekostenabrechnung der aktuellen KW als PDF exportieren (ohne Vorlage)."""
        export_dir = get_reisekosten_export_dir(self._profile)
        default_name = export_pdf.default_reisekosten_pdf_name(self._kw, self._year, self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Reisekostenabrechnung als PDF speichern",
            os.path.join(export_dir, default_name),
            "PDF-Dateien (*.pdf)")
        if not dest:
            return

        # Aktuelle (ggf. noch ungespeicherte) KW-Daten + lokal gespeicherte
        # KW-Datei zusammenführen, damit Änderungen sofort exportiert werden.
        path = os.path.join(KW_DIR, f"{self._year}-W{self._kw:02d}.json")
        kw_data = load_json(path, {})
        kw_data.update(self._day_data)
        kw_data["_extras"] = {
            "sonstiges":     self._sonstiges_val.text(),
            "sonstiges_txt": self._sonstiges_txt.text(),
        }

        try:
            block = export_pdf.export_reisekosten(
                dest, kw_data, self._kw, self._year,
                self._profile, self._get_wohnort())
            self.status_msg.emit(f"✅  Reisekostenabrechnung als PDF exportiert: {dest}")
            QMessageBox.information(
                self, "Exportiert",
                f"Reisekostenabrechnung (PDF) gespeichert:\n{dest}\n\n"
                f"KW {self._kw} / {self._year}  –  {block} Einträge")
        except Exception as e:
            QMessageBox.critical(self, "PDF-Fehler", str(e))

    def _save_kw(self, silent=False):
        path = os.path.join(KW_DIR, f"{self._year}-W{self._kw:02d}.json")
        data = dict(self._day_data)
        data["_extras"] = {
            "sonstiges":     self._sonstiges_val.text(),
            "sonstiges_txt": self._sonstiges_txt.text(),
        }
        save_json(path, data)
        if not silent:
            QMessageBox.information(self, "Gespeichert", f"KW {self._kw} / {self._year} gespeichert.")
