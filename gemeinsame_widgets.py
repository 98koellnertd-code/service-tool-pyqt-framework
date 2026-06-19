#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemeinsame_widgets.py
Widgets, die sowohl im Menü "Arbeitszeiten" als auch "Reisekosten"
verwendet werden:

  - DetailPanel : Editier-Panel für einen Tageseintrag (Zeiten, Kunde,
                   Allgemeinkosten, optional Mahlzeiten/Übernachtung)
  - DayRow      : Eine kompakte, inline-editierbare Tageszeile in der
                   Monats-/Wochenübersicht

Werden beide Seiten doppelt gepflegt, laufen sie früher oder später
aus dem Tritt — deshalb liegen sie hier zentral.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QGroupBox, QPushButton, QSizePolicy, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils import (
    C, KUNDEN_FILE, ALLGEMEIN_CODES, DAY_NAMES,
    load_json, save_json, calc_day_hours,
    btn, lbl, make_entry, make_combo,
)

# ══════════════════════════════════════════════════════════════════════════════
# Status-Farben & -Icons für die Tageszeilen
# ══════════════════════════════════════════════════════════════════════════════
STATUS_BG = {
    "Krank":      C["krank_bg"], "Urlaub":    C["urlaub_bg"],
    "Kurzarbeit": C["glz_bg"],   "GLZ":       C["glz_bg"],
    "Feiertag":   C["urlaub_bg"], "Sonstiges": C["surface2"],
    "Frei":       C["we_bg"],
}
STATUS_ICON = {
    "Arbeit": "💼", "Krank": "🤒", "Urlaub": "🏖", "Kurzarbeit": "📉",
    "GLZ": "⏸", "Feiertag": "🎉", "Sonstiges": "📌", "Frei": "🏠",
}


# ══════════════════════════════════════════════════════════════════════════════
# DetailPanel — Editier-Panel für Tageseinträge
# ══════════════════════════════════════════════════════════════════════════════

class DetailPanel(QFrame):
    """
    Editier-Panel für Tageseinträge.
    Wird am unteren Rand der Arbeitszeiten- / Reisekosten-Seite angezeigt.
    Signalisiert 'saved' wenn der Nutzer auf 'Übernehmen' klickt.
    """
    saved = pyqtSignal(str, dict)   # iso_date, aktualisierte day_data

    def __init__(self, show_meals=False, parent=None):
        super().__init__(parent)
        self._show_meals = show_meals
        self._iso_date    = None
        self._day_data    = {}
        self._entry_idx   = 0
        self._vorlagen    = load_json(KUNDEN_FILE, {})
        self.setStyleSheet(f"background:{C['surface']}; border-top:2px solid {C['accent']};")
        self.setMinimumHeight(210)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # ── Kopfzeile ──────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)
        top.addWidget(lbl("📋  Auftrags-Details", C["accent"], bold=True))
        top.addWidget(lbl("(klicke einen Tag für Details)", C["dimtext"], size=8))

        self._nav_lbl = lbl("Eintrag 1 / 1", C["subtext"], size=9)
        top.addWidget(self._nav_lbl)

        for t, cb, tip, col in [
            ("◀", self._prev, "Vorheriger Eintrag", None),
            ("▶", self._next, "Nächster Eintrag", None),
            ("＋ Neu", self._new, "Neuen Eintrag hinzufügen", C["green"]),
            ("🗑", self._del, "Eintrag löschen", C["red"]),
        ]:
            b = btn(t, cb, tip)
            b.setFixedHeight(26)
            if col:
                b.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{col};font-size:10pt;}} QPushButton:hover{{color:{C['text']};}}")
            else:
                b.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{C['subtext']};}} QPushButton:hover{{color:{C['text']};}}")
            top.addWidget(b)

        top.addStretch()

        # Kundenvorlagen
        top.addWidget(lbl("Vorlage:", C["subtext"], size=9))
        self._vorl_cb = make_combo([""] + list(self._vorlagen.keys()), width=160)
        self._vorl_cb.setPlaceholderText("Vorlage wählen…")
        self._vorl_cb.currentTextChanged.connect(self._load_vorlage)
        top.addWidget(self._vorl_cb)
        top.addWidget(btn("💾  Vorlage speichern", self._save_vorlage,
                          "Aktuelle Felder als Vorlage speichern", color=C["mauve"]))
        root.addLayout(top)

        # ── Felder-Bereich ─────────────────────────────────────────────────────
        fields = QHBoxLayout()
        fields.setSpacing(10)

        # Gruppe 1: Zeiten & Art
        g1 = QGroupBox("⏱  Zeiten & Dienstart")
        fl1 = QFormLayout(g1)
        fl1.setSpacing(4)
        self._f_start  = make_entry("08:00", 70)
        self._f_end    = make_entry("17:00", 70)
        self._f_pause  = make_entry("30", 50)
        self._f_dienst = make_combo(["Außendienst", "Innendienst", "Ausland"], 130)
        self._f_dienst.currentTextChanged.connect(self._dienst_toggle)
        self._f_land   = make_entry("DE", 45)
        fl1.addRow("Start:",       self._f_start)
        fl1.addRow("Ende:",        self._f_end)
        fl1.addRow("Pause (min):", self._f_pause)
        fl1.addRow("Dienstart:",   self._f_dienst)
        fl1.addRow("Land:",        self._f_land)
        fields.addWidget(g1)

        # Gruppe 2a: Auftrag/Kunde (Außendienst)
        self._g_ad = QGroupBox("🏢  Auftrag / Kunde")
        fl2 = QFormLayout(self._g_ad)
        fl2.setSpacing(4)
        self._f_auftr    = make_entry("Auftragsnummer", 120)
        self._f_kunde    = make_entry("Kundenname", 200)
        self._f_standort = make_entry("Standort / Ort", 160)
        self._f_startpkt = make_combo(["Wohnort", "Hotel"], 100)
        self._f_endpkt   = make_combo(["Wohnort", "Hotel"], 100)
        fl2.addRow("Auftrags-Nr:", self._f_auftr)
        fl2.addRow("Kundenname:",  self._f_kunde)
        fl2.addRow("Standort:",    self._f_standort)
        fl2.addRow("Startpunkt:",  self._f_startpkt)
        fl2.addRow("Endpunkt:",    self._f_endpkt)
        fields.addWidget(self._g_ad)

        # Gruppe 2b: Allgemeinkosten (Innendienst)
        self._g_id = QGroupBox("📋  Allgemeinkosten")
        fl3 = QFormLayout(self._g_id)
        fl3.setSpacing(4)
        self._f_allg = QComboBox()
        for code, name in ALLGEMEIN_CODES.items():
            self._f_allg.addItem(f"{code}  –  {name}", code)
        self._f_allg.setMinimumWidth(280)
        fl3.addRow("Code:", self._f_allg)
        self._f_allg_detail = make_entry("z.B. Schulung Laser", 220)
        fl3.addRow("Details:", self._f_allg_detail)
        self._g_id.hide()
        fields.addWidget(self._g_id)

        # Gruppe 3: Reisekosten (optional, nur Reisekosten-Seite)
        self._g_rk = QGroupBox("🍽  Mahlzeiten / Übernachtung")
        fl4 = QFormLayout(self._g_rk)
        fl4.setSpacing(4)
        self._f_uebernacht  = make_combo(["nein", "ja"], 70)
        self._f_fruehstueck = make_combo(["nein", "ja"], 70)
        self._f_mittag      = make_combo(["nein", "ja"], 70)
        self._f_abend       = make_combo(["nein", "ja"], 70)
        fl4.addRow("Übernachtung:", self._f_uebernacht)
        fl4.addRow("Frühstück:",    self._f_fruehstueck)
        fl4.addRow("Mittagessen:",  self._f_mittag)
        fl4.addRow("Abendessen:",   self._f_abend)
        if not self._show_meals:
            self._g_rk.hide()
        fields.addWidget(self._g_rk)

        fields.addStretch()
        root.addLayout(fields)

        # ── Buttons ────────────────────────────────────────────────────────────
        bot = QHBoxLayout()
        b_kunde = btn("💾  Kunde speichern", self._quick_save_kunde,
                      "Kundenname + Standort als Vorlage speichern")
        b_kunde.setStyleSheet(f"QPushButton{{background:{C['surface2']};border:1px solid {C['border']};border-radius:7px;color:{C['green']};padding:5px 12px;}} QPushButton:hover{{background:{C['overlay']};border-color:{C['green']};}}")
        bot.addWidget(b_kunde)
        bot.addStretch()
        b_apply = btn("✓  Übernehmen", self._apply,
                      "Änderungen in den Tageseintrag übernehmen (dann noch KW speichern!)",
                      color=C["green"])
        bot.addWidget(b_apply)
        root.addLayout(bot)

    # ── Laden / Speichern ──────────────────────────────────────────────────────

    def load_day(self, iso_date, day_data, wohnort="Wohnort"):
        """Tag in das Panel laden."""
        self._iso_date  = iso_date
        self._day_data  = day_data
        self._wohnort   = wohnort
        self._entry_idx = 0
        self._load_entry()

    def _load_entry(self):
        if not self._iso_date:
            return
        entries = self._day_data.get("entries", [{}])
        if not entries:
            entries = [{}]
        idx = max(0, min(self._entry_idx, len(entries) - 1))
        self._entry_idx = idx
        e = entries[idx]
        wohnort = getattr(self, "_wohnort", "Wohnort")

        self._f_start.setText(e.get("start", self._day_data.get("start", "08:00")))
        self._f_end.setText(  e.get("end",   self._day_data.get("end",  "17:00")))
        self._f_pause.setText(e.get("pause", self._day_data.get("pause", "30")))
        self._f_dienst.setCurrentText(e.get("dienst", "Außendienst"))
        self._f_land.setText(e.get("land", "DE"))
        self._f_auftr.setText(e.get("auftr_nr", ""))
        self._f_kunde.setText(e.get("kunde_name", ""))
        self._f_standort.setText(e.get("standort", ""))
        self._f_startpkt.setCurrentText(e.get("start_punkt", wohnort))
        self._f_endpkt.setCurrentText(  e.get("end_punkt",   wohnort))
        # Allgemeinkosten-Code setzen
        code = e.get("allg_code", "")
        for i in range(self._f_allg.count()):
            if self._f_allg.itemData(i) == code:
                self._f_allg.setCurrentIndex(i)
                break
        self._f_allg_detail.setText(e.get("allg_detail", ""))
        # Mahlzeiten (auf Tag-Ebene)
        self._f_uebernacht.setCurrentText( self._day_data.get("uebernacht", "nein"))
        self._f_fruehstueck.setCurrentText(self._day_data.get("fruehstueck", "nein"))
        self._f_mittag.setCurrentText(     self._day_data.get("mittag", "nein"))
        self._f_abend.setCurrentText(      self._day_data.get("abend", "nein"))

        total = len(entries)
        self._nav_lbl.setText(f"Eintrag  {idx+1} / {total}")
        self._nav_lbl.setStyleSheet(
            f"color:{C['accent']}; font-size:9pt;" if total > 1
            else f"color:{C['subtext']}; font-size:9pt;")
        self._dienst_toggle(self._f_dienst.currentText())

    def _dienst_toggle(self, dienst):
        """Zeigt Kunden-Felder oder Allgemeinkosten je nach Dienstart."""
        is_id = dienst in ("Innendienst", "Homeoffice", "Home Office")
        self._g_ad.setVisible(not is_id)
        self._g_id.setVisible(is_id)

    def _apply(self):
        """Aktuelle Felder in day_data übernehmen und Signal senden."""
        if not self._iso_date:
            return
        self._apply_silent()
        self._day_data["uebernacht"]  = self._f_uebernacht.currentText()
        self._day_data["fruehstueck"] = self._f_fruehstueck.currentText()
        self._day_data["mittag"]      = self._f_mittag.currentText()
        self._day_data["abend"]       = self._f_abend.currentText()
        self.saved.emit(self._iso_date, self._day_data)

    # ── Eintrag-Navigation ─────────────────────────────────────────────────────

    def _prev(self):
        if self._iso_date:
            self._apply_silent()
            self._entry_idx -= 1
            self._load_entry()

    def _next(self):
        if self._iso_date:
            self._apply_silent()
            self._entry_idx += 1
            self._load_entry()

    def _new(self):
        if not self._iso_date:
            return
        self._apply_silent()
        entries = self._day_data.setdefault("entries", [{}])
        entries.append({})
        self._entry_idx = len(entries) - 1
        self._load_entry()

    def _del(self):
        if not self._iso_date:
            return
        entries = self._day_data.get("entries", [])
        if len(entries) <= 1:
            QMessageBox.information(self, "Hinweis", "Mindestens ein Eintrag muss verbleiben.")
            return
        entries.pop(self._entry_idx)
        self._entry_idx = max(0, self._entry_idx - 1)
        self._load_entry()

    def _apply_silent(self):
        """Übernimmt die Eingabefelder in day_data, ohne 'saved' zu senden
        (wird für die Navigation zwischen Einträgen benutzt)."""
        if not self._iso_date:
            return
        entries = self._day_data.setdefault("entries", [{}])
        if not entries:
            entries.append({})
        idx = max(0, min(self._entry_idx, len(entries) - 1))
        wohnort = getattr(self, "_wohnort", "Wohnort")
        entries[idx] = {
            "start": self._f_start.text(), "end": self._f_end.text(),
            "pause": self._f_pause.text(), "dienst": self._f_dienst.currentText(),
            "land": self._f_land.text() or "DE", "auftr_nr": self._f_auftr.text(),
            "kunde_name": self._f_kunde.text(), "standort": self._f_standort.text(),
            "start_punkt": self._f_startpkt.currentText() or wohnort,
            "end_punkt":   self._f_endpkt.currentText()   or wohnort,
            "allg_code":   self._f_allg.currentData() or "",
            "allg_detail": self._f_allg_detail.text(),
        }
        # Tag-Ebene synchronisieren
        if entries:
            self._day_data["start"] = entries[0].get("start", "")
            self._day_data["end"]   = entries[-1].get("end", "")
            self._day_data["pause"] = entries[0].get("pause", "")

    # ── Vorlagen ───────────────────────────────────────────────────────────────

    def _load_vorlage(self, name):
        if not name:
            return
        v = self._vorlagen.get(name, {})
        if not v:
            return
        self._f_auftr.setText(   v.get("auftr_nr", ""))
        self._f_kunde.setText(   v.get("kunde_name", ""))
        self._f_standort.setText(v.get("standort", ""))
        self._f_dienst.setCurrentText(v.get("dienst", "Außendienst"))
        self._f_land.setText(    v.get("land", "DE"))
        self._f_startpkt.setCurrentText(v.get("start_punkt", "Wohnort"))
        self._f_endpkt.setCurrentText(  v.get("end_punkt", "Wohnort"))
        code = v.get("allg_code", "")
        for i in range(self._f_allg.count()):
            if self._f_allg.itemData(i) == code:
                self._f_allg.setCurrentIndex(i)
                break

    def _save_vorlage(self):
        name, ok = QInputDialog.getText(self, "Vorlage speichern", "Name für diese Vorlage:")
        if not ok or not name.strip():
            return
        self._vorlagen[name.strip()] = {
            "auftr_nr":    self._f_auftr.text(),
            "kunde_name":  self._f_kunde.text(),
            "standort":    self._f_standort.text(),
            "dienst":      self._f_dienst.currentText(),
            "land":        self._f_land.text(),
            "allg_code":   self._f_allg.currentData() or "",
            "start_punkt": self._f_startpkt.currentText(),
            "end_punkt":   self._f_endpkt.currentText(),
        }
        save_json(KUNDEN_FILE, self._vorlagen)
        self._vorl_cb.clear()
        self._vorl_cb.addItems([""] + list(self._vorlagen.keys()))
        self._vorl_cb.setCurrentText(name.strip())

    def _quick_save_kunde(self):
        kunde    = self._f_kunde.text().strip()
        standort = self._f_standort.text().strip()
        default = f"{kunde} – {standort}" if kunde and standort else kunde or standort
        if not default:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst Kundenname oder Standort eingeben.")
            return
        name, ok = QInputDialog.getText(self, "Kunde speichern", "Name für diesen Kunden:", text=default)
        if not ok or not name.strip():
            return
        self._vorlagen[name.strip()] = {
            "auftr_nr":    self._f_auftr.text(),
            "kunde_name":  kunde,
            "standort":    standort,
            "dienst":      self._f_dienst.currentText(),
            "land":        self._f_land.text(),
            "allg_code":   self._f_allg.currentData() or "",
            "start_punkt": self._f_startpkt.currentText(),
            "end_punkt":   self._f_endpkt.currentText(),
        }
        save_json(KUNDEN_FILE, self._vorlagen)
        self._vorl_cb.clear()
        self._vorl_cb.addItems([""] + list(self._vorlagen.keys()))
        QMessageBox.information(self, "Gespeichert", f"Kunde gespeichert als: {name.strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# DayRow — Tag-Zeile für Monats- und Wochenansicht
# ══════════════════════════════════════════════════════════════════════════════

class DayRow(QFrame):
    """
    Eine kompakte Tageszeile in der Übersichtstabelle.
    Inline-editierbar: Status, Start, Ende, Pause.
    Klick → Auswahl und Laden ins Detail-Panel.
    """
    clicked = pyqtSignal(str)  # iso_date

    def __init__(self, date, day_data, alt=False, feiertag=None, parent=None):
        super().__init__(parent)
        self.iso  = date.isoformat()
        self.date = date
        self._d   = day_data     # Referenz auf globales Dict
        self._alt = alt
        self._sel = False
        self._is_we = date.weekday() >= 5
        # Name des gesetzlichen Feiertags (je Bundesland aus den Einstellungen)
        # oder None — dient nur als Vorbelegung, der Status bleibt frei editierbar
        # (z.B. wenn an dem Tag in einem anderen Bundesland gearbeitet wurde).
        self._feiertag = feiertag
        self._build()
        self._apply_bg()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(6)
        is_we = self._is_we
        if self._feiertag:
            default_st = "Feiertag"
        else:
            default_st = "Frei" if is_we else "Arbeit"

        # Wochentag-Label
        wt = lbl(DAY_NAMES[self.date.weekday()])
        wt.setFixedWidth(26)
        wt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wt.setStyleSheet(
            f"font-weight:{'bold' if not is_we else 'normal'};"
            f"color:{C['subtext'] if is_we else C['text']};")
        lay.addWidget(wt)

        # Datum
        dl = lbl(self.date.strftime("%d.%m.%Y"))
        dl.setFixedWidth(76)
        dl.setStyleSheet(f"color:{C['subtext'] if is_we else C['text']};")
        if self._feiertag:
            dl.setToolTip(f"Feiertag: {self._feiertag}")
        lay.addWidget(dl)

        # Status-ComboBox
        from utils import STATUS_OPTIONS
        self._scb = make_combo(STATUS_OPTIONS, 110, self._d.get("status", default_st))
        self._scb.currentTextChanged.connect(self._on_status)
        lay.addWidget(self._scb)

        # Zeit-Felder
        for txt, key, w in [("Start", "start", 62), ("Ende", "end", 62), ("P", "pause", 44)]:
            lay.addWidget(lbl(txt, C["dimtext"], size=8))
            f = QLineEdit(self._d.get(key, ""))
            f.setFixedWidth(w)
            f.setAlignment(Qt.AlignmentFlag.AlignCenter)
            f.setPlaceholderText("--:--" if key != "pause" else "0")
            f.textChanged.connect(lambda v, k=key: self._set(k, v))
            setattr(self, f"_f_{key}", f)
            lay.addWidget(f)

        # Stunden-Anzeige
        self._hlbl = lbl(self._hours_txt(), C["accent"])
        self._hlbl.setFixedWidth(46)
        self._hlbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hlbl.setStyleSheet(f"color:{C['accent']};font-weight:bold;font-size:9pt;")
        lay.addWidget(self._hlbl)

        # Eintrags-Zusammenfassung
        self._slbl = lbl(self._summary(), C["subtext"])
        self._slbl.setStyleSheet(f"color:{C['subtext']};font-size:8pt;")
        self._slbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._slbl)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_status(self, status):
        self._d["status"] = status
        if status not in ("Arbeit",):
            for f in [self._f_start, self._f_end, self._f_pause]:
                f.setText("")
        self._hlbl.setText(self._hours_txt())
        self._apply_bg()

    def _set(self, key, val):
        self._d[key] = val
        self._hlbl.setText(self._hours_txt())

    def _hours_txt(self):
        STATUS_L = {"Krank": "🤒", "Urlaub": "🏖", "Kurzarbeit": "KA",
                    "GLZ": "−8h", "Feiertag": "🎉", "Sonstiges": "●", "Frei": "—"}
        s = self._d.get("status", "")
        if s in STATUS_L:
            return STATUS_L[s]
        h = calc_day_hours(self._d)
        return f"{h:.2f}h" if h > 0 else "—"

    def _summary(self):
        entries = self._d.get("entries", [])
        parts = []
        if self._feiertag:
            parts.append(f"🎉 {self._feiertag}")
        if not entries:
            return "  •  ".join(parts)
        for e in entries[:4]:
            d = e.get("dienst", "Außendienst")
            if d in ("Innendienst", "Homeoffice", "Home Office"):
                c = e.get("allg_code", "")
                base = ALLGEMEIN_CODES.get(c, c) if c else "ID"
                detail = (e.get("allg_detail") or "").strip()
                parts.append(f"{base}: {detail}" if detail else base)
            else:
                k = e.get("kunde_name", "") or e.get("auftr_nr", "")
                if k:
                    parts.append(k)
        if len(entries) > 4:
            parts.append(f"+{len(entries)-4}")
        return "  •  ".join(parts)

    def _apply_bg(self):
        status = self._d.get("status", "")
        if self._sel:
            bg = C["overlay"]
        elif self._is_we:
            bg = C["we_bg"]
        elif status in STATUS_BG:
            bg = STATUS_BG[status]
        elif self._alt:
            bg = C["surface2"]
        else:
            bg = C["surface"]
        bc = C["accent"] if self._sel else C["border"]
        self.setStyleSheet(f"QFrame{{background:{bg};border-bottom:1px solid {bc};}}")

    def select(self, on):
        self._sel = on
        self._apply_bg()

    def refresh(self):
        """Aus self._d neu laden (z.B. nach SF-Import)."""
        is_we = self._is_we
        self._scb.blockSignals(True)
        self._scb.setCurrentText(self._d.get("status", "Frei" if is_we else "Arbeit"))
        self._scb.blockSignals(False)
        self._f_start.setText(self._d.get("start", ""))
        self._f_end.setText(  self._d.get("end", ""))
        self._f_pause.setText(self._d.get("pause", ""))
        self._hlbl.setText(self._hours_txt())
        self._slbl.setText(self._summary())
        self._apply_bg()

    def mousePressEvent(self, ev):
        self.clicked.emit(self.iso)
        super().mousePressEvent(ev)
