#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
katalog_utils.py
Gemeinsame Logik für die Kataloge "Ersatzteile" und "Fehlerdiagnose".

Beide Menüs funktionieren nach dem gleichen Muster:
  - Pro Verzeichnis (res/et bzw. res/fd) gibt es eine Registry-Datei
    "systeme.json", die einen technischen Schlüssel (= Dateiname ohne
    .json, z.B. "aj5") auf einen Anzeigenamen (z.B. "alphaJET 5") mappt.
  - Für jedes System liegt eine eigene JSON-Datei mit der Liste der
    Einträge (Ersatzteile bzw. Fehlerdiagnose-Artikel).
  - Neue Systeme legen einfach eine neue Zeile in der Registry + eine
    neue (leere) JSON-Datei an.

Dieses Modul kapselt das Laden/Speichern der Registry und der
Eintragslisten, sowie zwei generische Dialoge:
  - NeuesSystemDialog: fragt Kurzname (= Dateiname) + Anzeigename ab.
  - EintragDialog: generischer Editier-Dialog für eine Liste von Feldern.
"""

import os
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QMessageBox, QWidget, QGridLayout, QScrollArea, QCheckBox, QLabel
)

from utils import C, btn, lbl, load_json, save_json

REGISTRY_NAME = "systeme.json"

# Fällt eine Kategorie/Baugruppe weg (leer gelassen oder beim Anlegen
# nichts ausgewählt), landet der Eintrag einheitlich hier — sowohl beim
# Speichern neuer Einträge als auch bei der Anzeige bereits vorhandener
# Einträge mit leerem Feld (siehe seite_ersatzteile.py / seite_fehlerdiagnose.py).
SONSTIGES = "Sonstiges"


# ══════════════════════════════════════════════════════════════════════════════
# Registry (Systeme) — key -> Anzeigename
# ══════════════════════════════════════════════════════════════════════════════

def registry_path(verzeichnis):
    """Pfad zur systeme.json in einem Ressourcen-Verzeichnis."""
    return os.path.join(verzeichnis, REGISTRY_NAME)


def load_registry(verzeichnis, defaults):
    """
    Lädt die key->label Map. Existiert die Datei noch nicht, wird sie
    mit den übergebenen Default-Werten (z.B. die alten AJ5/AJX/AJD
    Systeme) einmalig angelegt.
    """
    path = registry_path(verzeichnis)
    if not os.path.isfile(path):
        save_json(path, dict(defaults))
        return dict(defaults)
    reg = load_json(path, {})
    if not reg:
        reg = dict(defaults)
        save_json(path, reg)
    return reg


def save_registry(verzeichnis, registry):
    """Registry-Datei speichern."""
    save_json(registry_path(verzeichnis), registry)


def system_file(verzeichnis, key):
    """Pfad zur Daten-Datei eines Systems, z.B. res/et/aj5.json."""
    return os.path.join(verzeichnis, f"{key}.json")


# ══════════════════════════════════════════════════════════════════════════════
# Eintragslisten je System
# ══════════════════════════════════════════════════════════════════════════════

def load_liste(verzeichnis, key, listenfeld):
    """
    Lädt die Einträge eines Systems. listenfeld ist der Schlüssel im
    JSON-Wurzelobjekt, z.B. "parts" (Ersatzteile) oder "entries"
    (Fehlerdiagnose).
    """
    daten = load_json(system_file(verzeichnis, key), {})
    return daten.get(listenfeld, []) or []


def save_liste(verzeichnis, key, listenfeld, items):
    """Speichert die Einträge eines Systems unter listenfeld zurück."""
    path = system_file(verzeichnis, key)
    daten = load_json(path, {})
    daten[listenfeld] = items
    save_json(path, daten)


def schluessel_aus_text(text):
    """
    Wandelt einen frei eingegebenen Kurznamen in einen sicheren
    Datei-/Registry-Schlüssel um (klein geschrieben, Leerzeichen -> _).
    """
    key = text.strip().lower()
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"[^a-z0-9_\-]", "", key)
    return key


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Neues System anlegen
# ══════════════════════════════════════════════════════════════════════════════

class NeuesSystemDialog(QDialog):
    """Fragt einen Kurznamen (= Dateiname) und einen Anzeigenamen ab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues System anlegen")
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.addWidget(lbl("➕  Neues System", C["accent"], bold=True))

        form = QFormLayout()
        self._kurz = QLineEdit()
        self._kurz.setPlaceholderText("z.B. aj6")
        self._anzeige = QLineEdit()
        self._anzeige.setPlaceholderText("z.B. alphaJET 6 (neu)")
        form.addRow("Kurzname (Dateiname):", self._kurz)
        form.addRow("Anzeigename:", self._anzeige)
        lay.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn("Abbrechen", self.reject))
        ok = btn("Anlegen", self._on_ok, color=C["green"])
        row.addWidget(ok)
        lay.addLayout(row)

        self._key_result = None
        self._label_result = None

    def _on_ok(self):
        key = schluessel_aus_text(self._kurz.text())
        label = self._anzeige.text().strip()
        if not key or not label:
            QMessageBox.warning(self, "Hinweis", "Bitte Kurzname und Anzeigename angeben.")
            return
        self._key_result = key
        self._label_result = label
        self.accept()

    def values(self):
        """Gibt (key, label) zurück, nachdem der Dialog mit OK bestätigt wurde."""
        return self._key_result, self._label_result


# ══════════════════════════════════════════════════════════════════════════════
# Checkbox-Auswahl: vorhandene Werte als Checkboxen + Freitext für Neues
# ══════════════════════════════════════════════════════════════════════════════

class CheckboxOptionsWidget(QWidget):
    """
    Zeigt vorhandene Werte (z.B. Baugruppen, Modelle, Kategorien) als
    Checkboxen an, damit man nicht jedes Mal neu tippen muss. Darunter
    steht ein Freitextfeld, mit dem zusätzlich neue Werte angelegt
    werden können (bei 'multi' Komma-getrennt, sonst ein einzelner Wert).

    single (multi=False): es kann immer nur eine Checkbox aktiv sein
    (wie Radiobuttons, optisch aber als Checkbox gewünscht) — typisch
    für Baugruppe/Kategorie. multi=True erlaubt mehrere (z.B. Modelle).
    """

    def __init__(self, options, multi=True, parent=None):
        super().__init__(parent)
        self._multi = multi
        self._checks = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        if options:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFixedHeight(min(150, 30 + 24 * ((len(options) + 1) // 2)))
            inner = QWidget()
            grid = QGridLayout(inner)
            grid.setSpacing(2)
            for i, opt in enumerate(options):
                cb = QCheckBox(opt)
                if not multi:
                    cb.toggled.connect(lambda checked, o=opt: self._auf_exklusiv(o, checked))
                self._checks[opt] = cb
                row, col = divmod(i, 2)
                grid.addWidget(cb, row, col)
            scroll.setWidget(inner)
            lay.addWidget(scroll)

        neu_row = QHBoxLayout()
        neu_row.addWidget(QLabel("Neu:"))
        self._neu = QLineEdit()
        self._neu.setPlaceholderText(
            "Komma-getrennt für weitere neue Werte" if multi else "Neuer Wert (falls nicht in der Liste)")
        neu_row.addWidget(self._neu)
        lay.addLayout(neu_row)

    def _auf_exklusiv(self, gewaehlt, checked):
        """Im single-Modus alle anderen Checkboxen deaktivieren, sobald eine
        ausgewählt wird (Radiobutton-Verhalten, optisch als Checkbox)."""
        if not checked:
            return
        for opt, cb in self._checks.items():
            if opt != gewaehlt and cb.isChecked():
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)

    def selected(self):
        """Gibt bei multi=True eine Liste, sonst einen einzelnen String
        (bzw. "" wenn nichts gewählt/eingegeben wurde) zurück."""
        werte = [opt for opt, cb in self._checks.items() if cb.isChecked()]
        neu_text = self._neu.text().strip()
        if neu_text:
            neu_werte = [v.strip() for v in neu_text.split(",") if v.strip()] if self._multi else [neu_text]
            for v in neu_werte:
                if v not in werte:
                    werte.append(v)
        if not self._multi:
            return werte[0] if werte else ""
        return werte

    def set_selected(self, werte):
        """Vorbelegung setzen (zum Bearbeiten eines vorhandenen Eintrags)."""
        if isinstance(werte, str):
            werte = [werte] if werte else []
        unbekannt = []
        for v in werte:
            if v in self._checks:
                self._checks[v].setChecked(True)
            else:
                unbekannt.append(v)
        if unbekannt:
            self._neu.setText(", ".join(unbekannt))


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Eintrag bearbeiten/anlegen (generisch, feldspec-gesteuert)
# ══════════════════════════════════════════════════════════════════════════════

class EintragDialog(QDialog):
    """
    Generischer Editier-Dialog für einen Katalog-Eintrag.

    feldspec: Liste aus (key, label, art) mit art in
      {"text", "mehrzeilig", "checkbox_single", "checkbox_multi"}.
    werte_init: optionales dict mit Startwerten (zum Bearbeiten).
    options_map: optionales dict {key: [vorhandene Werte]} für die
      checkbox_*-Felder (welche Checkboxen angezeigt werden).
    """

    def __init__(self, feldspec, werte_init=None, titel="Eintrag", parent=None, options_map=None):
        super().__init__(parent)
        self.setWindowTitle(titel)
        self.setMinimumWidth(440)
        self._feldspec = feldspec
        self._felder = {}
        werte_init = werte_init or {}
        options_map = options_map or {}

        lay = QVBoxLayout(self)
        lay.addWidget(lbl(f"✎  {titel}", C["accent"], bold=True))

        form = QFormLayout()
        for key, label, art in feldspec:
            if art == "mehrzeilig":
                w = QTextEdit()
                w.setFixedHeight(90)
                w.setPlainText(str(werte_init.get(key, "")))
            elif art in ("checkbox_single", "checkbox_multi"):
                w = CheckboxOptionsWidget(options_map.get(key, []), multi=(art == "checkbox_multi"))
                if key in werte_init:
                    w.set_selected(werte_init[key])
            else:
                w = QLineEdit()
                w.setText(str(werte_init.get(key, "")))
            self._felder[key] = (w, art)
            form.addRow(f"{label}:", w)
        lay.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn("Abbrechen", self.reject))
        row.addWidget(btn("Speichern", self.accept, color=C["green"]))
        lay.addLayout(row)

    def werte(self):
        """Liest die aktuellen Feldwerte als dict aus."""
        ergebnis = {}
        for key, (w, art) in self._felder.items():
            if art == "mehrzeilig":
                ergebnis[key] = w.toPlainText().strip()
            elif art in ("checkbox_single", "checkbox_multi"):
                ergebnis[key] = w.selected()
            else:
                ergebnis[key] = w.text().strip()
        return ergebnis
