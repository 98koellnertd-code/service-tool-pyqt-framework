#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_einstellungen.py
Menüpunkt "Einstellungen" — persönliche Daten & Salesforce-Konfiguration.
"""

import sys
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QMessageBox, QApplication, QColorDialog, QPushButton, QFileDialog,
    QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtGui import QColor

from utils import (
    C, DEFAULT_COLORS, COLOR_LABELS, PRESET_PALETTES, RES_DIR, KW_DIR, PROFILE_FILE,
    ARBEITSZEITEN_EXPORT_DIR_DEFAULT, REISEKOSTEN_EXPORT_DIR_DEFAULT,
    BESTELLUNGEN_EXPORT_DIR_DEFAULT, BUNDESLAND_NAMES,
    save_json, save_colors, restart_app, btn, lbl, make_entry, make_combo,
    page_hero,
)
from updater import UpdateManager


class EinstellungenPage(QWidget):
    """Persönliche Daten und Salesforce-Standardwerte speichern."""

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self._profile = profile
        self._update_mgr = UpdateManager(self)
        self._build()

    def _build(self):
        # Die Seite wird in eine QScrollArea gepackt, da bei kleineren
        # Fensterhöhen (oder vielen Farbfeldern) sonst der Inhalt gestaucht
        # bzw. abgeschnitten würde, statt scrollbar zu sein.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(16)
        lay.addWidget(page_hero(
            "icons/einstellungen.png", "Einstellungen",
            "Persönliche Daten, Salesforce, Export-Pfade und Programmverhalten konfigurieren",
        ))

        # Persönliche Daten
        g1 = QGroupBox("👤  Persönliche Daten")
        f1 = QFormLayout(g1)
        f1.setSpacing(8)
        self._vorname  = make_entry("Vorname")
        self._nachname = make_entry("Nachname")
        self._wohnort  = make_entry("Wohnort (Startpunkt für Routenberechnung)")
        self._pers_nr  = make_entry("Personalnummer")
        self._vorname.setText( self._profile.get("vorname", ""))
        self._nachname.setText(self._profile.get("nachname", ""))
        self._wohnort.setText( self._profile.get("wohnort", ""))
        self._pers_nr.setText( self._profile.get("pers_nr", ""))
        f1.addRow("Vorname:",      self._vorname)
        f1.addRow("Nachname:",     self._nachname)
        f1.addRow("Wohnort:",      self._wohnort)
        f1.addRow("Personal-Nr.:", self._pers_nr)

        self._bundesland_cb = make_combo(list(BUNDESLAND_NAMES.values()), 220)
        self._bundesland_cb.setCurrentText(
            BUNDESLAND_NAMES.get(self._profile.get("bundesland", "NW"), BUNDESLAND_NAMES["NW"]))
        self._bundesland_cb.setToolTip(
            "Wird genutzt, um Feiertage in 'Arbeitszeiten' automatisch vorzubelegen "
            "(Status bleibt für einzelne Tage trotzdem editierbar).")
        f1.addRow("Bundesland:", self._bundesland_cb)
        lay.addWidget(g1)

        # SF Session-ID & OAuth (alle Felder, die auch auf der Start-Seite
        # zum Verbinden genutzt werden — hier zentral hinterlegt, damit
        # Start sie automatisch vorausgefüllt anzeigt).
        g2 = QGroupBox("☁  Salesforce Standardwerte")
        f2 = QFormLayout(g2)
        f2.setSpacing(8)
        self._sf_session  = make_entry("Session ID (gespeicherter Wert)", pw=True)
        self._oauth_email = make_entry("OAuth E-Mail")
        self._oauth_pw    = make_entry("Passwort", pw=True)
        self._oauth_token = make_entry("Security Token (aus SF-Profil → Einstellungen)")
        self._oauth_cid   = make_entry("Consumer Key")
        self._oauth_csec  = make_entry("Consumer Secret", pw=True)
        self._oauth_url   = make_entry("Login-URL")
        for attr, key, default in [
            ("_sf_session",  "sf_session",          ""),
            ("_oauth_email", "oauth_email",          ""),
            ("_oauth_pw",    "oauth_password",       ""),
            ("_oauth_token", "oauth_security_token",  ""),
            ("_oauth_cid",   "oauth_client_id",       ""),
            ("_oauth_csec",  "oauth_client_secret",   ""),
            ("_oauth_url",   "oauth_login_url",        "https://login.salesforce.com"),
        ]:
            getattr(self, attr).setText(self._profile.get(key, default))
        f2.addRow("Session ID:",      self._sf_session)
        f2.addRow("OAuth E-Mail:",    self._oauth_email)
        f2.addRow("Passwort:",        self._oauth_pw)
        f2.addRow("Security Token:",  self._oauth_token)
        f2.addRow("Consumer Key:",    self._oauth_cid)
        f2.addRow("Consumer Secret:", self._oauth_csec)
        f2.addRow("Login-URL:",       self._oauth_url)
        lay.addWidget(g2)

        # Datenpfad-Info
        g3 = QGroupBox("📁  Datenspeicherung")
        g3l = QVBoxLayout(g3)
        g3l.addWidget(lbl(f"KW-Daten: {KW_DIR}", C["subtext"], size=9))
        g3l.addWidget(lbl(f"Profil:   {PROFILE_FILE}", C["subtext"], size=9))
        open_btn = btn("📂  Ordner öffnen",
                       lambda: os.startfile(RES_DIR) if sys.platform == "win32"
                               else os.system(f"xdg-open {RES_DIR}"),
                       "res-Ordner im Explorer öffnen")
        g3l.addWidget(open_btn)
        lay.addWidget(g3)

        # Export-Pfade (Servicezeitenmeldung & Reisekostenabrechnung)
        g5 = QGroupBox("📊  Export-Pfade")
        f5 = QVBoxLayout(g5)
        f5.setSpacing(8)
        f5.addWidget(lbl(
            "Standardordner, in dem die Excel-Exporte vorgeschlagen werden.",
            C["subtext"], size=9))

        self._export_az = make_entry("Pfad für Arbeitszeiten-Export")
        self._export_az.setText(
            self._profile.get("export_dir_arbeitszeiten", ARBEITSZEITEN_EXPORT_DIR_DEFAULT))
        row_az = QHBoxLayout()
        row_az.addWidget(lbl("Arbeitszeiten:", C["text"]))
        row_az.addWidget(self._export_az, 1)
        row_az.addWidget(btn("📂", lambda: self._pick_export_dir(self._export_az), "Ordner auswählen", small=True))
        f5.addLayout(row_az)

        self._export_rk = make_entry("Pfad für Reisekosten-Export")
        self._export_rk.setText(
            self._profile.get("export_dir_reisekosten", REISEKOSTEN_EXPORT_DIR_DEFAULT))
        row_rk = QHBoxLayout()
        row_rk.addWidget(lbl("Reisekosten:  ", C["text"]))
        row_rk.addWidget(self._export_rk, 1)
        row_rk.addWidget(btn("📂", lambda: self._pick_export_dir(self._export_rk), "Ordner auswählen", small=True))
        f5.addLayout(row_rk)

        self._export_best = make_entry("Pfad für Bestellungen-Export")
        self._export_best.setText(
            self._profile.get("export_dir_bestellungen", BESTELLUNGEN_EXPORT_DIR_DEFAULT))
        row_best = QHBoxLayout()
        row_best.addWidget(lbl("Bestellungen:", C["text"]))
        row_best.addWidget(self._export_best, 1)
        row_best.addWidget(btn("📂", lambda: self._pick_export_dir(self._export_best), "Ordner auswählen", small=True))
        f5.addLayout(row_best)

        lay.addWidget(g5)

        # Software-Update (GitHub: version.json + SHA-256-Prüfung)
        g6 = QGroupBox("🔄  Update")
        f6 = QVBoxLayout(g6)
        f6.setSpacing(8)
        f6.addWidget(lbl(
            "URL zur version.json, über die nach neuen Versionen gesucht wird.",
            C["subtext"], size=9))
        self._update_url = make_entry("z.B. https://raw.githubusercontent.com/.../version.json")
        self._update_url.setText(self._profile.get("update_url", ""))
        f6.addWidget(self._update_url)

        update_row = QHBoxLayout()
        self._auto_update_cb = QCheckBox("Beim Start automatisch prüfen")
        self._auto_update_cb.setChecked(bool(self._profile.get("auto_update", True)))
        update_row.addWidget(self._auto_update_cb)
        update_row.addStretch()
        update_row.addWidget(btn("🔄  Jetzt prüfen", self._check_update_now,
                                  "Prüft sofort, ob eine neue Version verfügbar ist."))
        f6.addLayout(update_row)
        lay.addWidget(g6)

        save_btn = btn("💾  Einstellungen speichern", self._save, "Alle Einstellungen speichern", color=C["green"])
        lay.addWidget(save_btn)

        # Farbanpassung
        g4 = QGroupBox("🎨  Farbanpassung")
        g4l = QVBoxLayout(g4)
        g4l.addWidget(lbl(
            "Farbe anklicken zum Ändern. Wirkt erst nach \"Speichern und neu starten\".",
            C["subtext"], size=9))

        # Standardpaletten — setzen einen kompletten Satz Farben auf einmal,
        # danach bleibt die individuelle Anpassung der einzelnen Felder unten
        # weiterhin möglich (Paletten sind nur ein Startpunkt für _pending_colors).
        g4l.addWidget(lbl("Standardpaletten:", C["text"], bold=True, size=9))
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for key, preset in PRESET_PALETTES.items():
            preset_row.addWidget(
                btn(preset["label"], lambda _checked=False, k=key: self._apply_palette(k),
                    "Diese Palette als Startpunkt übernehmen")
            )
        preset_row.addStretch()
        g4l.addLayout(preset_row)

        grid = QGridLayout()
        grid.setSpacing(8)
        self._color_buttons = {}
        self._pending_colors = dict(C)
        cols = 2
        for i, key in enumerate(COLOR_LABELS):
            row, col = divmod(i, cols)
            b = self._make_color_swatch(key)
            grid.addWidget(b, row, col * 2)
            grid.addWidget(lbl(COLOR_LABELS[key], C["text"]), row, col * 2 + 1)
            self._color_buttons[key] = b
        g4l.addLayout(grid)

        # Live-Vorschau des Themes (aktualisiert sich sofort bei jeder Änderung,
        # ohne Neustart — zeigt, wie die gewählten Farben zusammenwirken).
        g4l.addWidget(lbl("Vorschau:", C["text"], bold=True, size=9))
        g4l.addWidget(self._build_theme_preview())

        color_btns_row = QVBoxLayout()
        reset_btn = btn("↺  Auf Standardfarben zurücksetzen", self._reset_colors,
                         "Alle Farben auf die Werkseinstellung zurücksetzen")
        color_btns_row.addWidget(reset_btn)
        restart_btn = btn("💾  Speichern und neu starten", self._save_colors_and_restart,
                           "Farben lokal speichern und das Programm neu starten, "
                           "damit die neuen Farben angewendet werden", color=C["accent"])
        color_btns_row.addWidget(restart_btn)
        g4l.addLayout(color_btns_row)
        lay.addWidget(g4)

        lay.addStretch()

    def _build_theme_preview(self):
        """Kleines Mock-UI, das die aktuell gewählten Farben (self._pending_colors)
        live darstellt — wird bei jeder Farbänderung über _update_theme_preview
        neu eingefärbt."""
        f = QFrame()
        self._pv_frame = f
        v = QVBoxLayout(f)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self._pv_header = lbl("  Themen-Vorschau", C["accent"], bold=True, size=10)
        self._pv_header.setFixedHeight(28)
        v.addWidget(self._pv_header)

        body = QFrame()
        self._pv_body = body
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 10, 12, 12)
        bl.setSpacing(8)

        self._pv_card = QFrame()
        cl = QVBoxLayout(self._pv_card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(4)
        self._pv_title = lbl("Überschrift", C["text"], bold=True, size=11)
        self._pv_text  = lbl("Normaler Text in der Oberfläche", C["text"], size=10)
        self._pv_sub   = lbl("Untertitel / Beschreibung", C["subtext"], size=10)
        self._pv_dim   = lbl("Ausgegrauter Hinweis", C["dimtext"], size=10)
        for w in (self._pv_title, self._pv_text, self._pv_sub, self._pv_dim):
            cl.addWidget(w)

        row = QHBoxLayout()
        row.setSpacing(6)
        # Chips spiegeln die tatsächliche Button-Farb-Bedeutung im Tool wider.
        self._pv_btn     = lbl("  Aktion  ", "#ffffff", size=10)
        self._pv_save    = lbl(" Speichern ", "#ffffff", size=9)
        self._pv_export  = lbl(" Export ", "#ffffff", size=9)
        self._pv_special = lbl(" Sonderfkt. ", "#000000", size=9)
        self._pv_err     = lbl(" Löschen ", "#ffffff", size=9)
        for w in (self._pv_btn, self._pv_save, self._pv_export,
                  self._pv_special, self._pv_err):
            row.addWidget(w)
        row.addStretch()
        cl.addLayout(row)

        bl.addWidget(self._pv_card)
        v.addWidget(body)

        self._update_theme_preview()
        return f

    def _update_theme_preview(self):
        """Färbt die Vorschau anhand von self._pending_colors neu ein."""
        def col(k):
            return self._pending_colors.get(k, DEFAULT_COLORS.get(k, "#888888"))
        self._pv_frame.setStyleSheet(
            f"QFrame {{ background:{col('bg')}; border:1px solid {col('border')};"
            f" border-radius:8px; }}")
        self._pv_header.setStyleSheet(
            f"background:{col('header')}; color:{col('accent')}; font-weight:bold;"
            f" font-size:10px; border-top-left-radius:8px;"
            f" border-top-right-radius:8px; padding-left:10px;")
        self._pv_body.setStyleSheet("background:transparent; border:none;")
        self._pv_card.setStyleSheet(
            f"background:{col('surface')}; border:1px solid {col('border')};"
            f" border-left:3px solid {col('accent')}; border-radius:6px;")
        self._pv_title.setStyleSheet(f"color:{col('text')}; font-weight:bold; font-size:11px;")
        self._pv_text.setStyleSheet(f"color:{col('text')}; font-size:10px;")
        self._pv_sub.setStyleSheet(f"color:{col('subtext')}; font-size:10px;")
        self._pv_dim.setStyleSheet(f"color:{col('dimtext')}; font-size:10px;")
        chip = ("background:{bg}; color:{fg}; border-radius:4px;"
                " padding:3px 8px; font-size:9px; font-weight:bold;")
        self._pv_btn.setStyleSheet(
            f"background:{col('accent')}; color:#ffffff; border-radius:4px;"
            f" padding:3px 10px; font-size:10px; font-weight:bold;")
        self._pv_save.setStyleSheet(chip.format(bg=col('green'),  fg="#ffffff"))
        self._pv_export.setStyleSheet(chip.format(bg=col('mauve'), fg="#ffffff"))
        self._pv_special.setStyleSheet(chip.format(bg=col('yellow'), fg="#000000"))
        self._pv_err.setStyleSheet(chip.format(bg=col('red'),    fg="#ffffff"))

    def _make_color_swatch(self, key):
        """Quadratischer Button, der die aktuelle Farbe von 'key' anzeigt und
        per Klick einen Farbauswahl-Dialog öffnet."""
        b = QPushButton()
        b.setFixedSize(36, 24)
        self._style_swatch(b, self._pending_colors[key])
        b.clicked.connect(lambda _checked=False, k=key: self._pick_color(k))
        return b

    def _style_swatch(self, button, hex_color):
        button.setStyleSheet(
            f"background-color:{hex_color}; border:1px solid {C['border']}; border-radius:4px;"
        )
        button.setToolTip(hex_color)

    def _pick_color(self, key):
        current = QColor(self._pending_colors.get(key, DEFAULT_COLORS[key]))
        chosen = QColorDialog.getColor(current, self, f"Farbe wählen: {COLOR_LABELS[key]}")
        if chosen.isValid():
            hex_code = chosen.name()
            self._pending_colors[key] = hex_code
            self._style_swatch(self._color_buttons[key], hex_code)
            self._update_theme_preview()

    def _reset_colors(self):
        self._pending_colors = dict(DEFAULT_COLORS)
        for key, button in self._color_buttons.items():
            self._style_swatch(button, self._pending_colors[key])
        self._update_theme_preview()

    def _apply_palette(self, palette_key):
        """Übernimmt eine der drei Standardpaletten in _pending_colors und
        aktualisiert alle Swatch-Buttons. Wird erst durch 'Speichern und neu
        starten' wirksam — bis dahin lässt sich noch jedes Feld einzeln anpassen."""
        palette = PRESET_PALETTES.get(palette_key)
        if not palette:
            return
        self._pending_colors = dict(palette["colors"])
        for key, button in self._color_buttons.items():
            self._style_swatch(button, self._pending_colors.get(key, DEFAULT_COLORS[key]))
        self._update_theme_preview()

    def _save_colors_and_restart(self):
        antwort = QMessageBox.question(
            self, "Neu starten?",
            "Die Farben werden gespeichert und das Programm wird jetzt neu "
            "gestartet, damit die Änderungen angezeigt werden.\n\n"
            "Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        save_colors(self._pending_colors)
        restart_app()
        QApplication.instance().quit()

    def _pick_export_dir(self, line_edit):
        start = line_edit.text() or RES_DIR
        chosen = QFileDialog.getExistingDirectory(self, "Export-Ordner wählen", start)
        if chosen:
            line_edit.setText(chosen)

    def _check_update_now(self):
        self._update_mgr.check(self._update_url.text().strip(), manual=True)

    def _save(self):
        bundesland_code = next(
            (code for code, name in BUNDESLAND_NAMES.items()
             if name == self._bundesland_cb.currentText()),
            "NW")
        self._profile.update({
            "vorname":         self._vorname.text(),
            "nachname":        self._nachname.text(),
            "wohnort":         self._wohnort.text(),
            "pers_nr":         self._pers_nr.text(),
            "bundesland":      bundesland_code,
            "sf_session":           self._sf_session.text(),
            "oauth_email":          self._oauth_email.text(),
            "oauth_password":       self._oauth_pw.text(),
            "oauth_security_token": self._oauth_token.text(),
            "oauth_client_id":      self._oauth_cid.text(),
            "oauth_client_secret":  self._oauth_csec.text(),
            "oauth_login_url":      self._oauth_url.text(),
            "export_dir_arbeitszeiten": self._export_az.text().strip() or ARBEITSZEITEN_EXPORT_DIR_DEFAULT,
            "export_dir_reisekosten":   self._export_rk.text().strip() or REISEKOSTEN_EXPORT_DIR_DEFAULT,
            "export_dir_bestellungen":  self._export_best.text().strip() or BESTELLUNGEN_EXPORT_DIR_DEFAULT,
            "update_url":      self._update_url.text().strip(),
            "auto_update":     self._auto_update_cb.isChecked(),
        })
        save_json(PROFILE_FILE, self._profile)
        QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert.")

    def get_wohnort(self):
        return self._wohnort.text().strip() or "Wohnort"
