#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tour.py
Geführte Tour, die das Tool Schritt für Schritt erklärt. Wird von der
Startseite aus gestartet (Button "Tour starten").

Die Schritte werden generisch aus utils.MODULES + Intro/Outro erzeugt — dadurch
bleibt die Tour automatisch synchron zu Sidebar/Start/Info und funktioniert in
beiden Programmen. Beim Weiterklicken navigiert die Tour das Hauptfenster zur
jeweiligen Seite (über die übergebene navigate-Funktion), sodass man die echte
Seite hinter dem Tour-Fenster sieht.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from utils import C, APP_NAME, APP_VERSION, MODULES, MEIPASS_DIR, btn, lbl


# Ausführlichere Erklärungen je Modul (Schlüssel = Modulname). Deckt die Module
# beider Programme ab; fehlt ein Name, wird die Kurzbeschreibung aus MODULES
# verwendet.
TOUR_DETAILS = {
    # ── alphaJET ──────────────────────────────────────────────────────────────
    "Netzwerk":
        "Trage IP-Adresse und Port des Druckers ein und speichere sie. Mit "
        "»Verbindung prüfen« testest du die Erreichbarkeit (ohne einen Befehl zu "
        "senden). Mehrere Geräte lassen sich als Profile speichern; der Netzwerk-"
        "Helfer zeigt, ob PC und Drucker im selben Subnetz liegen.",
    "Dashboard":
        "Der Live-Status des Druckers: die Ampel zeigt Störung / Warnung / "
        "Druckbereit. Darunter Druckbereitschaft, Datum & Uhrzeit (mit Knopf zum "
        "Setzen), Netzwerk- und Firmware-Infos, verfügbare Fonts und das aktuell "
        "geladene Label – alles aus echten G-PRINT-Abfragen.",
    "Monitor":
        "Zum Testen ohne echte Hardware: der TCP-Proxy schneidet die Kommunikation "
        "mit, Mock-Drucker und Mock-FTP simulieren ein Gerät. Ideal zum "
        "Ausprobieren und zur Fehlersuche.",
    "Schnell-Befehle":
        "Fertige G-PRINT-Kommandos per Klick (Status, Start, Stopp, Version …). "
        "Gesendete Befehle landen in der Historie und lassen sich per Doppelklick "
        "erneut senden.",
    "GPRINT":
        "Eigene G-PRINT-XML-Befehle schreiben, formatieren, senden und als "
        "wiederverwendbare Funktion dauerhaft speichern.",
    "Labels":
        "Label-Dateien lokal verwalten (neu, importieren, speichern) und an den "
        "Drucker senden – auf der internen Disk ablegen (SAVELAB) oder direkt in "
        "den Druckpuffer laden.",
    "Configs":
        "Konfigurationsdateien bearbeiten, vom Drucker laden und wieder "
        "zurückspielen.",
    "Print Control":
        "PrintControl-Dateien verwalten sowie Druckaufträge laden und abgleichen.",
    "FTP":
        "Das Dateisystem des Druckers durchsuchen, Dateien hoch- und "
        "herunterladen, ein komplettes Backup als ZIP ziehen und Dateien direkt "
        "im passenden Editor öffnen.",
    "Label Editor":
        "Labels grafisch gestalten – Text, Datum/Zeit, Zähler, DataMatrix, "
        "Barcode/QR, Logos und Formen – mit pixelgenauer 1-Bit-Druckervorschau. "
        "Im Tab »Vorschau« siehst du alle gespeicherten Labels als Thumbnails.",
    "Logo Editor":
        "Pixel-Logos zeichnen und als MLG, BMP, PNG, JPG oder SVG speichern bzw. "
        "direkt an den Drucker senden.",
    # ── Service-Tool (TimingTool) ─────────────────────────────────────────────
    "API Verbindungen":
        "Verbindung zu Salesforce herstellen (Session ID oder OAuth); SAP und TIA "
        "Portal sind vorbereitet. Der Verbindungsstatus bleibt unten links in der "
        "Sidebar sichtbar.",
    "Mein Lager":
        "Den persönlichen Lagerbestand verwalten – mit automatischer Warnung bei "
        "Unterbestand – und als PDF exportieren.",
    "Arbeitszeiten":
        "Servicezeiten je Monat erfassen, Gleitzeit berechnen und die "
        "Servicezeitenmeldung als Excel oder PDF exportieren.",
    "Reisekosten":
        "Reisekosten je Kalenderwoche inklusive Verpflegung erfassen und die "
        "FB_0020-Abrechnung als Excel oder PDF erzeugen.",
    "Ersatzteile":
        "Den Ersatzteilkatalog je Gerätesystem durchsuchen und Teile zur "
        "Bestellung hinzufügen.",
    "Bestellung":
        "Bestellungen zusammenstellen, Favoriten für wiederkehrende Positionen "
        "nutzen und als Datei exportieren.",
    "Datenbank":
        "Serviceberichte per Mail (IMAP/SSL) abholen, von Claude AI analysieren "
        "lassen und in der Datenbank verwalten.",
    "Fehlerdiagnose":
        "Fehlercodes und Lösungen je Gerätesystem nachschlagen.",
    "Anleitungen":
        "Anleitungen und Dokumentationen je Kategorie durchsuchen (mit PDF-Verweis).",
    # ── In beiden Tools ───────────────────────────────────────────────────────
    "Service-Assistent":
        "Offline-Suche über die gesamte Programm-Hilfe und eigene Dokumente in "
        "res/docs – ganz ohne Internet. Beschreibe ein Problem und erhalte die "
        "passendsten Einträge.",
    "Info":
        "Version, Kennzahlen, Modulübersicht, Schnittstellen, Sicherheitshinweise "
        "und der letzte Update-Stand.",
    "Einstellungen":
        "Persönliche Daten, Update-URL und das Farbthema anpassen – inklusive "
        "Live-Vorschau der gewählten Farben.",
}


def build_default_steps():
    """Tour-Schritte: Intro, ein Schritt je Modul (aus MODULES), Outro."""
    steps = [{
        "title": f"Willkommen bei {APP_NAME}",
        "body": ("Diese kurze Tour zeigt dir die wichtigsten Bereiche des Tools. "
                 "Beim Weiterklicken wechselt das Programm jeweils zur passenden "
                 "Seite — du kannst die Tour jederzeit überspringen."),
        "icon": "icons/icon.png",
    }]
    for m in MODULES:
        steps.append({
            "title": m["name"],
            "body": TOUR_DETAILS.get(m["name"], m["desc"] + "."),
            "nav": m["nav"],
            "icon": m["icon"],
        })
    steps.append({
        "title": "Fertig!",
        "body": ("Das war die Tour. Du kannst sie jederzeit über »Tour starten« "
                 "auf der Startseite erneut aufrufen. Viel Erfolg!"),
        "icon": "icons/icon.png",
    })
    return steps


class TourDialog(QDialog):
    """Schritt-für-Schritt-Tour mit Zurück/Weiter und Seiten-Navigation."""

    def __init__(self, navigate=None, steps=None, parent=None):
        super().__init__(parent)
        self._nav   = navigate
        self._steps = steps or build_default_steps()
        self._i     = 0
        self.setWindowTitle("Tour")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setStyleSheet(f"QDialog {{ background:{C['bg']}; }}")
        self._build()
        self._show_step()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Kopf mit Icon + Titel
        head = QFrame()
        head.setStyleSheet(f"background:{C['surface']}; border:none;")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(20, 16, 20, 16)
        hl.setSpacing(14)
        self._icon = QLabel()
        self._icon.setFixedSize(44, 44)
        hl.addWidget(self._icon)
        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        self._counter = lbl("", C["dimtext"], size=8)
        self._title   = lbl("", C["accent"], bold=True, size=15)
        tcol.addWidget(self._counter)
        tcol.addWidget(self._title)
        hl.addLayout(tcol, 1)
        lay.addWidget(head)

        # Körper
        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 16, 20, 16)
        self._body = QLabel("")
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color:{C['text']}; font-size:11px;")
        self._body.setMinimumHeight(80)
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop)
        bl.addWidget(self._body)
        lay.addWidget(body, 1)

        # Fußleiste mit Buttons
        foot = QFrame()
        foot.setStyleSheet(f"background:{C['surface']}; border:none;")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(8)
        # Sekundär-Buttons als sichtbarer Umriss-Stil (heller Grund, dunkler Text,
        # Rahmen) – color=surface2 wäre weißer Text auf fast-weiß = unsichtbar.
        ghost = (
            f"QPushButton {{ background:{C['surface2']}; color:{C['text']};"
            f" border:1px solid {C['border']}; border-radius:7px; padding:6px 14px; }}"
            f"QPushButton:hover {{ background:{C['overlay']}; }}"
            f"QPushButton:disabled {{ color:{C['dimtext']}; }}")
        self._skip_btn = btn("Überspringen", self.reject, "Tour schließen.")
        self._skip_btn.setStyleSheet(ghost)
        fl.addWidget(self._skip_btn)
        fl.addStretch()
        self._back_btn = btn("‹  Zurück", self._back, "Vorheriger Schritt.")
        self._back_btn.setStyleSheet(ghost)
        self._next_btn = btn("Weiter  ›", self._next, "Nächster Schritt.",
                             color=C["accent"])
        fl.addWidget(self._back_btn)
        fl.addWidget(self._next_btn)
        lay.addWidget(foot)

    def _show_step(self):
        step = self._steps[self._i]
        nav = step.get("nav")
        if nav is not None and self._nav is not None:
            self._nav(nav)

        self._counter.setText(f"Schritt {self._i + 1} von {len(self._steps)}")
        self._title.setText(step["title"])
        self._body.setText(step["body"])

        pix = QPixmap(os.path.join(MEIPASS_DIR, step.get("icon", "icons/icon.png")))
        if not pix.isNull():
            self._icon.setPixmap(pix.scaled(
                44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self._icon.clear()

        self._back_btn.setEnabled(self._i > 0)
        self._next_btn.setText("Fertig" if self._i == len(self._steps) - 1 else "Weiter  ›")

    def _next(self):
        if self._i >= len(self._steps) - 1:
            self.accept()
            return
        self._i += 1
        self._show_step()

    def _back(self):
        if self._i > 0:
            self._i -= 1
            self._show_step()
