#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_arbeitszeiten.py
Menüpunkt "Arbeitszeiten" — Monatsansicht aller Arbeitstage.

Lädt Daten aus Salesforce oder ermöglicht manuelle Eingabe.
Alle Tage sind inline editierbar; das Detail-Panel unten ermöglicht
die Bearbeitung einzelner Einträge (Kunden, Zeiten usw.).
"""

import os
import datetime
import calendar
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSplitter,
    QSpinBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils import (
    C, KW_DIR, MONTH_NAMES,
    load_json, save_json, load_month_data, get_month_summary, get_feiertage,
    get_arbeitszeiten_export_dir, btn, lbl, make_combo, page_hero,
)
from gemeinsame_widgets import DetailPanel, DayRow
from workers import SFLoadWorker
import export_excel
import export_pdf


class ArbeitsZeitenPage(QWidget):
    """
    Monatsansicht aller Arbeitstage. Lädt Daten aus Salesforce oder
    ermöglicht manuelle Eingabe. Detail-Panel unten für Einzeleinträge.
    """
    status_msg = pyqtSignal(str)

    def __init__(self, get_sf, get_wohnort, profile, parent=None):
        super().__init__(parent)
        self._get_sf      = get_sf       # Callable → (token, inst_url, user_id) oder None
        self._get_wohnort = get_wohnort
        self._profile     = profile
        today = datetime.date.today()
        self._month = today.month
        self._year  = today.year
        self._day_data: dict = {}        # {iso_date: day_data}
        self._rows:  dict = {}           # {iso_date: DayRow}
        self._selected: str | None = None
        self._build()
        self._load_local()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # ── Einheitlicher Seitenkopf (wie auf allen Inhaltsseiten) ──────────────
        root.addWidget(page_hero(
            "icons/arbeitszeiten.png", "Arbeitszeiten",
            "Servicezeiten je Monat erfassen, bearbeiten und als Meldung exportieren",
            "Export in SAP und TIA möglich. Was wird benötigt? Salesforce API (read), TIA und SAP API (write)",
        ))

        hdr = QFrame()
        hdr.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)

        # Monatsauswahl
        self._month_cb = make_combo(MONTH_NAMES, 120, MONTH_NAMES[self._month-1])
        self._month_cb.currentIndexChanged.connect(self._on_month_change)
        hl.addWidget(self._month_cb)

        self._year_sb = QSpinBox()
        self._year_sb.setRange(2020, 2099)
        self._year_sb.setValue(self._year)
        self._year_sb.setFixedWidth(90)
        self._year_sb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._year_sb.valueChanged.connect(self._on_month_change)
        hl.addWidget(self._year_sb)

        hl.addStretch()

        sf_btn = btn("☁  Von SF laden", self._load_from_sf,
                     "Daten aus Salesforce für diesen Monat laden", color=C["accent"])
        hl.addWidget(sf_btn)

        save_btn = btn("💾  Speichern", self._save_all, "Alle Monatsdaten lokal speichern", color=C["green"])
        hl.addWidget(save_btn)

        export_btn = btn("📊  Excel-Export", self._export_stundenblatt,
                          "Servicezeitenmeldung für diesen Monat als Excel exportieren")
        hl.addWidget(export_btn)

        pdf_btn = btn("📄  PDF-Export", self._export_stundenblatt_pdf,
                      "Servicezeitenmeldung für diesen Monat als PDF exportieren")
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

        # ── Hauptbereich: Liste + Detail-Panel ────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        # Scroll-Bereich für Tageszeilen
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

        # Detail-Panel
        self._detail = DetailPanel(show_meals=False, parent=self)
        self._detail.saved.connect(self._on_entry_saved)
        splitter.addWidget(self._detail)

        splitter.setSizes([380, 240])
        root.addWidget(splitter, 1)

        # ── Stunden-Bar ────────────────────────────────────────────────────────
        bar = QFrame()
        bar.setStyleSheet(f"background:{C['header']}; border-top:1px solid {C['border']};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 6, 14, 6)
        bl.setSpacing(8)

        self._bar_month = lbl("—", C["accent"], bold=True)
        self._bar_prev  = lbl("—", C["subtext"])
        self._bar_gleit = lbl("—", C["yellow"], bold=True)

        for lab, val_lbl in [
            (lbl("Monat:", C["subtext"]), self._bar_month),
            (lbl("  │  ", C["dimtext"]), None),
            (lbl("Vormonat:", C["subtext"]), self._bar_prev),
            (lbl("  │  ", C["dimtext"]), None),
            (lbl("Gleitzeitkonto:", C["subtext"]), self._bar_gleit),
        ]:
            bl.addWidget(lab)
            if val_lbl:
                bl.addWidget(val_lbl)
        bl.addStretch()
        root.addWidget(bar)

    # ── Monatswechsel ──────────────────────────────────────────────────────────

    def _on_month_change(self, *_):
        self._month = self._month_cb.currentIndex() + 1
        self._year  = self._year_sb.value()
        self._load_local()

    def _load_local(self):
        """Monatsdaten aus KW-JSON-Dateien laden und Ansicht aufbauen."""
        self._day_data = load_month_data(self._year, self._month)
        self._selected = None
        self._rebuild_list()
        self._update_bar()

    def _rebuild_list(self):
        """Alle Tageszeilen des Monats neu aufbauen."""
        while self._list_layout.count():
            w = self._list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._rows.clear()

        # Feiertage für das eingestellte Bundesland — Tage werden nur damit
        # vorbelegt (Status "Feiertag"), bleiben aber wie Wochenendtage frei
        # editierbar (z.B. wenn an dem Tag in einem anderen Bundesland
        # gearbeitet wurde).
        feiertage = get_feiertage(self._year, self._profile.get("bundesland"))

        cal_days = calendar.monthrange(self._year, self._month)[1]
        for dn in range(1, cal_days + 1):
            d  = datetime.date(self._year, self._month, dn)
            ds = d.isoformat()
            if ds not in self._day_data:
                self._day_data[ds] = {}
            row = DayRow(d, self._day_data[ds], alt=(dn % 2 == 0), feiertag=feiertage.get(ds))
            row.clicked.connect(self._select_day)
            self._rows[ds] = row
            self._list_layout.addWidget(row)

        self._list_layout.addStretch()

    def _select_day(self, iso_date):
        """Tag auswählen und in Detail-Panel laden."""
        if self._selected and self._selected in self._rows:
            self._rows[self._selected].select(False)
        self._selected = iso_date
        self._rows[iso_date].select(True)
        day_data = self._day_data.setdefault(iso_date, {})
        if not day_data.get("entries"):
            day_data.setdefault("entries", [{}])
        self._detail.load_day(iso_date, day_data, self._get_wohnort())

    def _on_entry_saved(self, iso_date, day_data):
        """Nach 'Übernehmen' im Detail-Panel: Ansicht aktualisieren."""
        self._day_data[iso_date] = day_data
        if iso_date in self._rows:
            self._rows[iso_date].refresh()
        self._update_bar()
        self.status_msg.emit(f"Eintrag {iso_date} übernommen — bitte noch speichern!")

    def _update_bar(self):
        """Monats-Stunden und Gleitzeitkonto neu berechnen."""
        total, gleit = get_month_summary(self._year, self._month, self._day_data)
        mn = MONTH_NAMES[self._month - 1]
        self._bar_month.setText(f"{mn} {self._year}: {total:.2f} h")

        prev_m = self._month - 1 or 12
        prev_y = self._year - (1 if self._month == 1 else 0)
        prev_h, _ = get_month_summary(prev_y, prev_m)
        prev_name = MONTH_NAMES[prev_m - 1]
        self._bar_prev.setText(f"{prev_name}: {prev_h:.2f} h")

        g_txt = f"+{gleit:.2f} h" if gleit > 0 else f"{gleit:.2f} h"
        g_col = C["green"] if gleit > 0 else C["red"] if gleit < 0 else C["subtext"]
        self._bar_gleit.setText(g_txt)
        self._bar_gleit.setStyleSheet(f"color:{g_col}; font-weight:bold;")

    # ── Salesforce laden ───────────────────────────────────────────────────────

    def _load_from_sf(self):
        sf = self._get_sf()
        if not sf:
            QMessageBox.warning(self, "Hinweis", "Bitte zuerst bei Salesforce anmelden (Start-Seite).")
            return
        token, inst_url, user_id = sf
        first = datetime.date(self._year, self._month, 1).isoformat()
        last  = datetime.date(self._year, self._month,
                              calendar.monthrange(self._year, self._month)[1]).isoformat()
        self._sf_worker = SFLoadWorker(token, inst_url, user_id,
                                       first, last, self._get_wohnort())
        self._sf_worker.success.connect(self._on_sf_success)
        self._sf_worker.error.connect(self._on_sf_error)
        self._sf_worker.progress.connect(lambda m: self.status_msg.emit(m))
        self._sf_worker.start()
        self.status_msg.emit("🔄  Lade Daten aus Salesforce…")

    def _on_sf_success(self, new_data):
        count = len(new_data)
        self._day_data.update(new_data)
        self._rebuild_list()
        self._update_bar()
        self._save_all(silent=True)
        self.status_msg.emit(f"✅  {count} Tag(e) aus Salesforce geladen und gespeichert.")
        QMessageBox.information(self, "SF Laden",
            f"✅  {count} Tag(e) geladen.\nDaten wurden automatisch gespeichert.")

    def _on_sf_error(self, err):
        self.status_msg.emit(f"❌  SF-Fehler: {err[:80]}")
        QMessageBox.critical(self, "Salesforce Fehler", err)

    # ── Excel-Export (Servicezeitenmeldung) ────────────────────────────────────

    def _export_stundenblatt(self):
        """Servicezeitenmeldung des aktuellen Monats als Excel exportieren."""
        mn = MONTH_NAMES[self._month - 1]
        export_dir = get_arbeitszeiten_export_dir(self._profile)
        default_name = export_excel.default_stundenblatt_filename(mn, self._year, self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Servicezeitenmeldung speichern",
            os.path.join(export_dir, default_name),
            "Excel (*.xlsx)")
        if not dest:
            return
        try:
            ad_days, id_days, total_h = export_excel.export_stundenblatt(
                dest, self._day_data, self._month, self._year,
                self._profile, self._get_wohnort())
            self.status_msg.emit(f"✅  Servicezeitenmeldung exportiert: {dest}")
            QMessageBox.information(
                self, "Exportiert",
                f"Servicezeitenmeldung gespeichert:\n{dest}\n\n"
                f"Außendienst: {ad_days} Tage\n"
                f"Innendienst: {id_days} Tage\n"
                f"Gesamt: {total_h:.2f} Stunden")
        except Exception as e:
            QMessageBox.critical(self, "Excel-Fehler", str(e))

    def _export_stundenblatt_pdf(self):
        """Servicezeitenmeldung des aktuellen Monats als PDF exportieren."""
        mn = MONTH_NAMES[self._month - 1]
        export_dir = get_arbeitszeiten_export_dir(self._profile)
        default_name = export_pdf.default_stundenblatt_pdf_name(mn, self._year, self._profile)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Servicezeitenmeldung als PDF speichern",
            os.path.join(export_dir, default_name),
            "PDF-Dateien (*.pdf)")
        if not dest:
            return
        try:
            ad_days, id_days, total_h = export_pdf.export_stundenblatt(
                dest, self._day_data, self._month, self._year,
                self._profile, self._get_wohnort())
            self.status_msg.emit(f"✅  Servicezeitenmeldung als PDF exportiert: {dest}")
            QMessageBox.information(
                self, "Exportiert",
                f"Servicezeitenmeldung (PDF) gespeichert:\n{dest}\n\n"
                f"Außendienst: {ad_days} Tage\n"
                f"Innendienst: {id_days} Tage\n"
                f"Gesamt: {total_h:.2f} Stunden")
        except Exception as e:
            QMessageBox.critical(self, "PDF-Fehler", str(e))

    def _save_all(self, silent=False):
        """Monatsdaten in die passenden KW-JSON-Dateien speichern."""
        kw_groups = defaultdict(dict)
        for ds, day in self._day_data.items():
            try:
                d   = datetime.date.fromisoformat(ds)
                iso = d.isocalendar()
                kw_groups[(iso[0], iso[1])][ds] = day
            except Exception:
                pass
        for (ky, kw), kd in kw_groups.items():
            path = os.path.join(KW_DIR, f"{ky}-W{kw:02d}.json")
            existing = load_json(path, {})
            existing.update(kd)
            save_json(path, existing)
        if not silent:
            QMessageBox.information(self, "Gespeichert",
                f"Monatsdaten für {MONTH_NAMES[self._month-1]} {self._year} gespeichert.")
