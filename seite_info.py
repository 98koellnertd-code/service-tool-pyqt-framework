#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_info.py
Menüpunkt "Info" — zeigt Versions-, Funktions- und Speicherort-Informationen,
eine dynamische Kennzahlen-Übersicht, die Modul-Liste, die Systemintegration,
einen Sicherheits-/Datenschutz-Abschnitt sowie den zuletzt über die Update-URL
gelesenen Changelog an (siehe updater.py).

Die Kennzahlen-Kacheln (Ersatzteil-Systeme, Fehlerdiagnose-Systeme, erfasste
Wochen, gespeicherte Bestellungen …) werden zur Laufzeit aus dem res-Ordner
gezählt — beim Öffnen der Seite über refresh() aktualisiert.
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QGridLayout, QScrollArea,
)
from PyQt6.QtCore import Qt

from utils import (
    C, BASE_DIR, APP_NAME, APP_VERSION, SF_INSTANCE_URL, UPDATE_CACHE_FILE,
    load_json, lbl, page_hero, MODULES,
)


# ══════════════════════════════════════════════════════════════════════════════
# Kleine Bausteine
# ══════════════════════════════════════════════════════════════════════════════

def _section(title: str) -> QLabel:
    w = lbl(title, C["accent"], bold=True)
    w.setStyleSheet(f"color:{C['accent']}; font-weight:600; font-size:12px;"
                    f" padding-top:8px;")
    return w


def _item(text: str) -> QLabel:
    w = lbl(text, C["subtext"])
    w.setWordWrap(True)
    w.setContentsMargins(14, 0, 0, 0)
    return w


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{C['border']}; margin:4px 0;")
    return f


def _kpi_card(value: str, label: str, icon: str) -> QFrame:
    """Kompakte Kennzahl-Kachel (Icon + großer Wert + Beschriftung)."""
    card = QFrame()
    card.setStyleSheet(
        f"background:{C['surface']}; border:1px solid {C['border']};"
        f" border-radius:10px;")
    cl = QVBoxLayout(card)
    cl.setContentsMargins(14, 12, 14, 12)
    cl.setSpacing(2)

    top = lbl(f"{icon}  {value}", C["text"], bold=True)
    top.setStyleSheet(f"color:{C['accent']}; font-size:20px; font-weight:800;")
    cl.addWidget(top)

    sub = lbl(label, C["subtext"])
    sub.setStyleSheet(f"color:{C['subtext']}; font-size:10px;")
    sub.setWordWrap(True)
    cl.addWidget(sub)
    return card


def _feature_card(title: str, desc: str) -> QFrame:
    """Hervorgehobene Funktions-Karte (Titel + Beschreibung)."""
    row = QFrame()
    row.setStyleSheet(f"background:{C['surface']}; border-radius:8px; margin:2px 0;")
    rl = QVBoxLayout(row)
    rl.setContentsMargins(14, 10, 14, 10)
    rl.setSpacing(3)
    rl.addWidget(lbl(title, C["text"], bold=True))
    d = lbl(desc, C["subtext"])
    d.setWordWrap(True)
    d.setStyleSheet(f"color:{C['subtext']}; font-size:10px;")
    rl.addWidget(d)
    return row


def _module_card(icon: str, name: str, desc: str) -> QFrame:
    """Kompakte Modul-Kachel für die Funktionsübersicht (Icon · Name · Text)."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background:{C['surface']}; border:1px solid {C['border']};"
        f" border-radius:8px; }}")
    h = QHBoxLayout(card)
    h.setContentsMargins(12, 9, 12, 9)
    h.setSpacing(10)

    ic = lbl(icon, C["accent"])
    ic.setStyleSheet(f"color:{C['accent']}; font-size:18px;")
    ic.setFixedWidth(34)
    ic.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
    h.addWidget(ic)

    col = QVBoxLayout()
    col.setSpacing(1)
    col.addWidget(lbl(name, C["text"], bold=True))
    d = lbl(desc, C["subtext"])
    d.setWordWrap(True)
    d.setStyleSheet(f"color:{C['subtext']}; font-size:9px;")
    col.addWidget(d)
    h.addLayout(col, 1)
    return card


def _faq_card(question: str, answer: str) -> QFrame:
    """Frage/Antwort-Karte für den Hilfe-/FAQ-Abschnitt."""
    card = QFrame()
    card.setStyleSheet(f"background:{C['surface']}; border-radius:8px; margin:2px 0;")
    cl = QVBoxLayout(card)
    cl.setContentsMargins(14, 10, 14, 10)
    cl.setSpacing(3)
    q = lbl(f"❓  {question}", C["text"], bold=True)
    q.setWordWrap(True)
    cl.addWidget(q)
    a = lbl(answer, C["subtext"])
    a.setWordWrap(True)
    a.setStyleSheet(f"color:{C['subtext']}; font-size:10px;")
    cl.addWidget(a)
    return card


class InfoPage(QWidget):
    """Info-Seite: Version, Kennzahlen, Module, Integration, Sicherheit, Update."""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(6)

        # ── Hero ──────────────────────────────────────────────────────────────
        lay.addWidget(page_hero(
            "icons/info.png", "Info",
            "Version, Kennzahlen, Funktionsübersicht, Systemintegration und "
            "letzter Update-Stand",
        ))
        lay.addSpacing(6)

        # ── App-Titel ─────────────────────────────────────────────────────────
        title_lbl = lbl(f"{APP_NAME}  v{APP_VERSION}", C["text"], bold=True)
        title_lbl.setStyleSheet(f"color:{C['text']}; font-size:16px; font-weight:700;")
        lay.addWidget(title_lbl)
        lay.addWidget(_item("Arbeitszeiten · Reisekosten · Ersatzteile · Bestellungen · "
                            "Fehlerdiagnose · Datenbank · Systemintegration"))
        lay.addWidget(_divider())

        # ── Auf einen Blick (dynamische Kennzahlen) ───────────────────────────
        lay.addWidget(_section("📊  Auf einen Blick"))
        self._kpi_grid = QGridLayout()
        self._kpi_grid.setHorizontalSpacing(10)
        self._kpi_grid.setVerticalSpacing(10)
        lay.addLayout(self._kpi_grid)
        lay.addSpacing(4)
        lay.addWidget(_divider())

        # ── Module / Funktionsübersicht ───────────────────────────────────────
        lay.addWidget(_section("🧭  Module"))
        # Modulkacheln aus dem zentralen Register (utils.MODULES) — ohne die
        # Info-Seite selbst (nav 7).
        mod_grid = QGridLayout()
        mod_grid.setHorizontalSpacing(10)
        mod_grid.setVerticalSpacing(8)
        for i, m in enumerate(mod for mod in MODULES if mod["nav"] != 7):
            mod_grid.addWidget(
                _module_card(m["emoji"], m["name"], m["desc"]), i // 2, i % 2)
        lay.addLayout(mod_grid)
        lay.addWidget(_divider())

        # ── Highlights / Neue Funktionen ──────────────────────────────────────
        lay.addWidget(_section("✨  Highlights"))
        new_features = [
            ("🤖  Service-Assistent (Offline-Hilfe & KI)",
             "Durchsucht offline Fehlerdiagnose, Anleitungen und Programm-Hilfe "
             "(über 30 Einträge, ohne Internet). Zusätzlich werden Serviceberichte "
             "per IMAP/SSL abgeholt und von Claude AI analysiert und in die DB "
             "eingefügt."),
            ("🔗  Systemanbindungen",
             "Salesforce-Anmeldung per Session ID oder OAuth; der Verbindungsstatus "
             "(● grün / ● rot) wird dauerhaft unten links in der Sidebar angezeigt. "
             "SAP (Lagerbestände) und TIA Portal sind vorbereitet."),
            ("📄  Excel- & PDF-Export",
             "Servicezeitenmeldung und Reisekostenabrechnung (FB_0020-Vorlage) "
             "lassen sich direkt als Excel oder PDF erzeugen — Zielordner frei "
             "wählbar."),
            ("🗄  PostgreSQL-Anbindung",
             "Optionale zentrale Datenhaltung im Team via psycopg2 "
             "(Serviceberichte, verbrauchte Mittel, Kunden)."),
            ("🔄  SHA-256 gesichertes Self-Update",
             "Prüft auf neue Versionen und lädt Updates nur über HTTPS — jede Datei "
             "wird vor der Installation per SHA-256-Hash verifiziert."),
        ]
        for title, desc in new_features:
            lay.addWidget(_feature_card(title, desc))
        lay.addWidget(_divider())

        # ── Systemintegration ─────────────────────────────────────────────────
        lay.addWidget(_section("🌐  Systemintegration"))
        integrations = [
            ("ok",   "Salesforce", SF_INSTANCE_URL, "Session ID · OAuth / Username-Password Flow"),
            ("ok",   "Claude AI",  "Anthropic API", "E-Mail-Analyse, Fehlerdiagnose, Bericht-Generierung"),
            ("ok",   "IMAP/SSL",   "Port 993",      "Automatischer E-Mail-Eingang für KI-Verarbeitung"),
            ("opt",  "PostgreSQL", "psycopg2",      "Optionale zentrale Datenhaltung"),
            ("plan", "SAP",        "Demo-Modus",    "Lagerbestände je Techniker (geplant: Live-Anbindung)"),
            ("plan", "TIA Portal", "Demo-Modus",    "SPS-Status & Diagnose (geplant: Live-Anbindung)"),
        ]
        dot_color = {"ok": C["green"], "opt": C["yellow"], "plan": C["dimtext"]}
        dot_text  = {"ok": "● aktiv", "opt": "● optional", "plan": "○ geplant"}
        for state, sys_name, endpoint, note in integrations:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(14, 0, 0, 0)
            dot = lbl(dot_text[state], dot_color[state])
            dot.setStyleSheet(f"color:{dot_color[state]}; font-size:9px; font-weight:600;")
            dot.setFixedWidth(70)
            row.addWidget(dot)
            txt = lbl(f"{sys_name}  ·  {endpoint}  —  {note}", C["subtext"])
            txt.setWordWrap(True)
            row.addWidget(txt, 1)
            lay.addLayout(row)
        lay.addWidget(_divider())

        # ── Typische Arbeitsabläufe ───────────────────────────────────────────
        lay.addWidget(_section("🧪  Typische Arbeitsabläufe"))
        workflows = [
            ("Servicezeiten erfassen & melden",
             "Arbeitszeiten → Monat wählen → Tageszeiten und Gleitzeit eintragen → "
             "als Excel/PDF (Servicezeitenmeldung) exportieren und im gewünschten "
             "Zielordner ablegen."),
            ("Reisekosten abrechnen",
             "Reisekosten → Kalenderwoche wählen → Fahrten und Verpflegung erfassen → "
             "FB_0020-Abrechnung als Excel/PDF erzeugen."),
            ("Bestellung zusammenstellen & exportieren",
             "Ersatzteile → Teil im Katalog des Gerätesystems suchen → zur Bestellung "
             "hinzufügen → in »Bestellung« Mengen prüfen, Favoriten nutzen und als "
             "Datei exportieren."),
            ("Servicebericht per KI auswerten",
             "Datenbank → E-Mails per IMAP/SSL abholen → Claude AI analysiert den "
             "Bericht, extrahiert verbrauchte Mittel und legt ihn in der DB ab."),
            ("Fehler nachschlagen",
             "Fehlerdiagnose → Gerätesystem wählen → Fehlercode oder Symptom suchen → "
             "Lösungsschritte ansehen; ergänzend die Anleitungen (PDF) öffnen."),
        ]
        for title, desc in workflows:
            lay.addWidget(_feature_card(title, desc))
        lay.addWidget(_divider())

        # ── Häufige Fragen / Hilfe ────────────────────────────────────────────
        lay.addWidget(_section("💬  Häufige Fragen"))
        faqs = [
            ("Wo werden meine Daten gespeichert?",
             "Alles liegt lokal im res-Ordner (siehe Datenspeicherung unten) als "
             "JSON. Zugangsdaten in res/service_config.json, DB-URL und API-Key in "
             "der .env. Keine Cloud-Pflicht, keine Telemetrie."),
            ("Salesforce verbindet sich nicht?",
             "Verbindungsstatus unten links in der Sidebar prüfen (● grün/rot). "
             "Session ID bzw. OAuth-Zugangsdaten und die Instanz-URL kontrollieren."),
            ("Wofür ist der Service-Assistent?",
             "Eine reine Offline-Suche über Fehlerdiagnose, Anleitungen und "
             "Programm-Hilfe — ohne Internet. Die KI-Berichtsanalyse läuft separat "
             "über die Datenbank-Seite."),
            ("Wie bekomme ich Updates?",
             "Einstellungen → Update-URL (version.json) hinterlegen und »Jetzt "
             "prüfen«. Downloads laufen nur über HTTPS und werden per SHA-256 "
             "verifiziert."),
        ]
        for q, a in faqs:
            lay.addWidget(_faq_card(q, a))
        lay.addWidget(_divider())

        # ── Bedienhinweise ────────────────────────────────────────────────────
        lay.addWidget(_section("⚡  Bedienhinweise"))
        for entry in [
            "Exporte (Excel/PDF) fragen den Zielordner ab — frei wählbar.",
            "Favoriten in der Bestellung beschleunigen wiederkehrende Bestellungen.",
            "Mein Lager warnt automatisch bei Unterbestand.",
            "Tooltips: Maus über Buttons/Felder halten zeigt zusätzliche Hinweise.",
            "Farbthema in den Einstellungen wählbar; Verbindungsstatus bleibt in der Sidebar sichtbar.",
        ]:
            lay.addWidget(_item(f"•  {entry}"))
        lay.addWidget(_divider())

        # ── Sicherheit & Datenschutz ──────────────────────────────────────────
        lay.addWidget(_section("🔒  Sicherheit & Datenschutz"))
        for entry in [
            "Lokale Datenhaltung: alle Arbeitszeiten, Kataloge und Bestellungen "
            "bleiben als JSON im res-Ordner — kein Cloud-Zwang, keine Telemetrie.",
            "Updates nur über HTTPS mit SHA-256-Prüfung der heruntergeladenen Datei.",
            "E-Mail-Abruf verschlüsselt über IMAP/SSL (Port 993); Zugangsdaten lokal "
            "in res/service_config.json, DB-URL und API-Key in der .env.",
            "Externer Datenfluss nur bei aktiver Nutzung: Salesforce, Service-DB, "
            "Mail-Postfach und — für die Berichtsanalyse — die Claude-API.",
            "Der Service-Assistent arbeitet vollständig offline (keine Datenweitergabe).",
        ]:
            lay.addWidget(_item(f"•  {entry}"))
        lay.addWidget(_divider())

        # ── Datenpfade (mit Vorhanden-Markierung) ─────────────────────────────
        lay.addWidget(_section("📁  Datenspeicherung"))
        self._paths_box = QVBoxLayout()
        self._paths_box.setSpacing(2)
        lay.addLayout(self._paths_box)
        lay.addWidget(_item("Format: JSON  —  lokal, kein Cloud-Zwang"))
        lay.addWidget(_divider())

        # ── Technologie-Stack ─────────────────────────────────────────────────
        lay.addWidget(_section("⚙  Technologie-Stack"))
        for entry in [
            "PyQt6  ·  Python 3.10+",
            "QThread — nicht-blockierende Netzwerkabfragen",
            "QTimer — Verbindungs-Ping & Status",
            "pyqtSignal — Sidebar-Statusupdates in Echtzeit",
            "QSS (Qt Stylesheets) — durchgängiges Theme",
            "simple-salesforce  ·  psycopg2  ·  anthropic  ·  openpyxl",
        ]:
            lay.addWidget(_item(entry))
        lay.addWidget(_divider())

        # ── Systemvoraussetzungen ─────────────────────────────────────────────
        lay.addWidget(_section("💻  Systemvoraussetzungen"))
        for entry in [
            "Windows 10/11 (empfohlen) — Linux möglich mit PyQt6.",
            "Als eigenständige .exe lauffähig — keine Python-Installation nötig.",
            "Internet nur für optionale Dienste: Salesforce, Claude-API, Mail (IMAP/SSL), DB.",
            "Aus dem Quellcode: Python 3.10+ mit PyQt6, openpyxl, simple-salesforce, "
            "anthropic, psycopg2.",
        ]:
            lay.addWidget(_item(f"•  {entry}"))
        lay.addWidget(_divider())

        # ── Support & Kontakt ─────────────────────────────────────────────────
        lay.addWidget(_section("📞  Support & Kontakt"))
        for entry in [
            "Service-Assistent (Offline-Hilfe) für die häufigsten Fragen direkt im Tool.",
            "Eigene Dokumentation als Markdown/JSON in res/docs ablegen — wird "
            "automatisch durchsucht.",
            f"{APP_NAME}  ·  Version {APP_VERSION}",
        ]:
            lay.addWidget(_item(f"•  {entry}"))
        lay.addWidget(_divider())

        # ── Update-Bereich ────────────────────────────────────────────────────
        lay.addWidget(_section("🔄  Update"))
        self._update_version_lbl = lbl("", C["dimtext"])
        self._update_url_lbl     = lbl("", C["dimtext"])
        self._update_url_lbl.setWordWrap(True)
        self._update_notes_lbl   = QLabel("")
        self._update_notes_lbl.setWordWrap(True)
        self._update_notes_lbl.setStyleSheet(f"color:{C['dimtext']};")
        lay.addWidget(self._update_version_lbl)
        lay.addWidget(self._update_url_lbl)
        lay.addWidget(self._update_notes_lbl)

        lay.addStretch()
        self.refresh()

    # ──────────────────────────────────────────────────────────────────────────

    def _count_json_keys(self, *path_parts) -> int:
        """Anzahl der Einträge (Schlüssel) in einer JSON-Map; 0 bei Fehler."""
        data = load_json(os.path.join(BASE_DIR, "res", *path_parts), {})
        return len(data) if isinstance(data, (dict, list)) else 0

    def _count_files(self, *path_parts, suffix=".json") -> int:
        """Anzahl passender Dateien in einem Ordner; 0 bei Fehler."""
        folder = os.path.join(BASE_DIR, "res", *path_parts)
        try:
            return sum(1 for f in os.listdir(folder)
                       if f.lower().endswith(suffix) and not f.startswith(("_", ".")))
        except OSError:
            return 0

    def _refresh_kpis(self):
        """Kennzahl-Kacheln neu berechnen und in das Grid setzen."""
        # Grid leeren
        while self._kpi_grid.count():
            item = self._kpi_grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        kpis = [
            ("🔧", self._count_json_keys("et", "systeme.json"),  "Ersatzteil-Systeme"),
            ("🔍", self._count_json_keys("fd", "systeme.json"),  "Fehlerdiagnose-Systeme"),
            ("📚", self._count_json_keys("anl", "systeme.json"), "Anleitungs-Kategorien"),
            ("📅", self._count_files("kw_data"),                 "erfasste Wochen"),
            ("🛒", self._count_files("orders"),                  "gespeicherte Bestellungen"),
            ("📄", self._count_files("docs", suffix=("")),       "Doku-Dateien (res/docs)"),
        ]
        cols = 3
        for i, (icon, value, label) in enumerate(kpis):
            self._kpi_grid.addWidget(
                _kpi_card(str(value), label, icon), i // cols, i % cols)

    def _refresh_paths(self):
        """Datenpfade auflisten und vorhandene mit ✓ markieren."""
        while self._paths_box.count():
            item = self._paths_box.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        paths = [
            os.path.join(BASE_DIR, "res", "kw_data"),
            os.path.join(BASE_DIR, "res", "et"),
            os.path.join(BASE_DIR, "res", "fd"),
            os.path.join(BASE_DIR, "res", "anl"),
            os.path.join(BASE_DIR, "res", "orders"),
            os.path.join(BASE_DIR, "res", "docs"),
        ]
        for p in paths:
            exists = os.path.exists(p)
            mark = "✓" if exists else "—"
            color = C["green"] if exists else C["dimtext"]
            row = lbl(f"{mark}  {p}", color)
            row.setWordWrap(True)
            row.setStyleSheet(f"color:{color};")
            row.setContentsMargins(14, 0, 0, 0)
            self._paths_box.addWidget(row)

    def refresh(self):
        """Kennzahlen, Datenpfade und Update-Cache neu einlesen — wird beim
        Öffnen der Seite aufgerufen."""
        self._refresh_kpis()
        self._refresh_paths()

        cache = load_json(UPDATE_CACHE_FILE, {})
        if not cache:
            self._update_version_lbl.setText(f"  Aktuell installiert: v{APP_VERSION}  ·  noch nicht geprüft")
            self._update_url_lbl.setText("  Download-URL: —")
            self._update_notes_lbl.setText("  Letzte Änderungen: noch keine Update-Prüfung durchgeführt.")
            return
        checked_at = cache.get("checked_at", "")
        suffix = f"  ·  geprüft am {checked_at}" if checked_at else ""
        self._update_version_lbl.setText(
            f"  Aktuell installiert: v{APP_VERSION}  ·  zuletzt gefunden: v{cache.get('version', '—')}{suffix}")
        self._update_url_lbl.setText(
            f"  Download-URL: {cache.get('download_url') or '—'}")
        self._update_notes_lbl.setText(
            f"  Letzte Änderungen:\n{cache.get('notes') or '—'}")
