#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_assistent.py
Menüpunkt "Service-Assistent" — ein OFFLINE-Suchassistent.

Der Assistent durchsucht das vorhandene Wissen (Fehlerdiagnose-Einträge,
Anleitungen/Hotline sowie eine kurze Programm-Hilfe) und zeigt zu einer Frage
oder einem Symptom die am besten passenden Einträge an. Er nutzt KEINE
Online-KI und keine externen Bibliotheken — die Suche läuft komplett lokal
über eine einfache Stichwort-/Relevanzbewertung. Dadurch ist er schnell,
kostenlos und funktioniert ohne Internet (auch in der .exe).

Datenquellen:
  - res/fd/<system>.json   (Fehlerdiagnose, Format {"entries": [...]})
  - res/anl/<system>.json  (Anleitungen/Hotline, Format {"entries": [...]})
  - PROGRAMM_HILFE          (fest hinterlegt, Fragen zum Tool selbst)
"""

import os
import re
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QTextBrowser,
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils import C, RES_DIR, FD_DIR, ANL_DIR, btn, lbl, page_hero
from katalog_utils import load_registry, load_liste

# Ordner für zusätzliche Dokumentation, die der Assistent mit durchsucht.
# Hier können später .md- oder .json-Dateien abgelegt werden (siehe
# _lade_dokumentation): Markdown wird je Überschrift in Abschnitte zerlegt,
# JSON im selben Format wie die Anleitungen ({"entries": [...]}) übernommen.
DOCS_DIR = os.path.join(RES_DIR, "docs")

# Sehr kurze deutsche Stoppwortliste — hält die Relevanzbewertung sauber,
# damit Füllwörter ("der", "wie", "ich") das Ergebnis nicht verfälschen.
_STOPWORDS = {
    "der", "die", "das", "und", "oder", "ein", "eine", "einen", "einem", "einer",
    "ist", "war", "wie", "was", "wann", "wo", "wer", "warum", "wieso", "welche",
    "welcher", "welches", "ich", "du", "er", "sie", "es", "wir", "ihr", "man",
    "mit", "ohne", "für", "von", "zu", "im", "in", "am", "an", "auf", "bei",
    "nach", "vor", "über", "unter", "den", "dem", "des", "kann", "muss", "soll",
    "habe", "hat", "haben", "wird", "werden", "sich", "nicht", "auch", "noch",
    "mal", "bitte", "machen", "macht", "tun", "geht", "gibt", "beim", "als",
}

# Kurze Programm-Hilfe — damit der Assistent auch Fragen zum Tool beantwortet.
# Hier neue Einträge ergänzen, wenn der Assistent mehr über das Programm
# wissen soll (Format wie bei Fehlerdiagnose/Anleitungen: cat/title/content).
PROGRAMM_HILFE = [
    {"cat": "Salesforce",
     "title": "Mit Salesforce verbinden und Daten laden",
     "content": "Im Menü Salesforce stellst du die Verbindung her — entweder per "
                "Session ID (Cookie 'sid', einfach aber läuft nach ~8 Stunden ab) "
                "oder per OAuth mit E-Mail und Passwort (dauerhaft, benötigt eine "
                "Connected App). Voraussetzung ist meist eine VPN-Verbindung "
                "(GlobalProtect). Eine grüne Statusanzeige bestätigt die Verbindung. "
                "Danach kannst du in den Menüs Arbeitszeiten und Reisekosten die "
                "Servicezeiten und Reisedaten direkt aus Salesforce laden."},
    {"cat": "Start",
     "title": "Startseite und Schnellzugriff",
     "content": "Die Startseite zeigt alle Module als Kacheln. Ein Klick auf eine "
                "Kachel öffnet das jeweilige Menü."},
    {"cat": "Dashboard",
     "title": "Dashboard mit Wochenübersicht",
     "content": "Das Dashboard zeigt eine Übersicht mit Kennzahlen und den nächsten "
                "Terminen."},
    {"cat": "Service-Assistent",
     "title": "Service-Assistent (diese Suche)",
     "content": "Der Service-Assistent durchsucht offline das vorhandene Wissen "
                "(Fehlerdiagnose, Anleitungen und diese Programm-Hilfe) und zeigt zu "
                "einer Frage oder einem Symptom die am besten passenden Einträge."},
    {"cat": "Arbeitszeiten",
     "title": "Arbeitszeiten erfassen und exportieren",
     "content": "Im Menü Arbeitszeiten erfasst du die Servicezeiten je Monat. "
                "Mit 'Excel-Export' erzeugst du die Servicezeitenmeldung als Excel, "
                "mit 'PDF-Export' dieselbe Meldung als PDF. Daten lassen sich auch "
                "aus Salesforce laden."},
    {"cat": "Reisekosten",
     "title": "Reisekostenabrechnung erstellen und exportieren",
     "content": "Im Menü Reisekosten erfasst du die Kalenderwoche inkl. Verpflegung "
                "und Sonstigem. 'Excel-Export' füllt die FB_0020-Vorlage, 'PDF-Export' "
                "erzeugt die Abrechnung als PDF (ohne Vorlage)."},
    {"cat": "Ersatzteile",
     "title": "Ersatzteile suchen und in Bestellung übernehmen",
     "content": "Im Menü Ersatzteile durchsuchst du den Katalog je Gerätesystem. "
                "Ein Doppelklick übernimmt ein Teil direkt in die aktuelle Bestellung."},
    {"cat": "Bestellung",
     "title": "Bestellung erstellen, speichern und als Excel oder PDF exportieren",
     "content": "Im Menü Bestellung stellst du Ersatzteil-Bestellungen zusammen, "
                "speicherst sie und exportierst sie als Excel oder PDF. Häufige Teile "
                "lassen sich als Favoriten speichern."},
    {"cat": "Datenbank",
     "title": "Serviceberichte per Mail importieren, anzeigen und löschen",
     "content": "Das Menü Datenbank zeigt Serviceberichte, verbrauchte Mittel und "
                "Kunden. Mit 'E-Mails abrufen' werden zugesandte Berichte automatisch "
                "ausgelesen und gespeichert; 'PDF analysieren' macht das manuell. "
                "Berichte lassen sich auch wieder löschen."},
    {"cat": "Mein Lager",
     "title": "Lagerbestand ansehen und als PDF exportieren",
     "content": "Im Menü Mein Lager siehst du deinen persönlichen Bestand mit "
                "Unterbestands-Warnung und kannst ihn als PDF exportieren. Später per "
                "SAP (read-only)."},
    {"cat": "Fehlerdiagnose",
     "title": "Fehlercodes und Diagnosen nachschlagen",
     "content": "Im Menü Fehlerdiagnose schlägst du Fehler und Lösungen je "
                "Gerätesystem nach und kannst eigene Einträge anlegen."},
    {"cat": "Anleitungen",
     "title": "Anleitungen und Dokumentationen durchsuchen",
     "content": "Im Menü Anleitungen findest du Dokumentationen je Kategorie, teils "
                "mit Verweis auf die zugehörige PDF."},
    {"cat": "Einstellungen",
     "title": "Profil, Export-Ordner, Farben und Updates",
     "content": "In den Einstellungen pflegst du persönliche Daten, Export-Ordner, "
                "das Farbthema und die automatische Update-Prüfung."},

    # ── Salesforce / API-Verbindungen (ausführlich) ─────────────────────────
    {"cat": "Salesforce",
     "title": "Session ID vs. OAuth — welche Anmeldung?",
     "content": "Session ID (sf) ist die schnellste Methode: den Cookie 'sid' aus "
                "einer offenen Salesforce-Sitzung im Browser kopieren und einfügen — "
                "läuft aber nach etwa 8 Stunden ab. OAuth (E-Mail, Passwort, ggf. "
                "Security-Token und Connected App mit Client-ID/Secret) bleibt "
                "dauerhaft verbunden. Beides im Menü API Verbindungen / Salesforce."},
    {"cat": "Salesforce",
     "title": "VPN / GlobalProtect für Salesforce nötig",
     "content": "Für den Zugriff auf Salesforce ist meist eine aktive "
                "VPN-Verbindung (GlobalProtect) erforderlich. Schlägt die Anmeldung "
                "trotz korrekter Daten fehl, zuerst prüfen, ob das VPN verbunden ist. "
                "Der Verbindungsstatus wird unten links in der Sidebar angezeigt."},
    {"cat": "Salesforce",
     "title": "Session läuft ab / Verbindung verloren",
     "content": "Das Tool pingt Salesforce regelmäßig. Läuft die Session ab, "
                "erscheint ein Hinweis und der Status wird rot — dann im Menü API "
                "Verbindungen neu anmelden (bei Session ID einen frischen 'sid' "
                "kopieren). Mit OAuth tritt das Problem seltener auf. Weitere "
                "Provider (SAP read-only, TIA Portal) sind vorbereitet, aber noch "
                "nicht aktiv."},

    # ── Arbeitszeiten (ausführlich) ─────────────────────────────────────────
    {"cat": "Arbeitszeiten",
     "title": "Arbeitszeiten: Monatsansicht und Bearbeitung",
     "content": "Die Arbeitszeiten-Seite zeigt alle Tage eines Monats. Tage sind "
                "direkt in der Liste editierbar; das Detail-Panel unten bearbeitet "
                "einzelne Einträge (Kunde, Start/Ende, Pause, Außendienst/"
                "Innendienst). Daten lassen sich aus Salesforce laden oder manuell "
                "erfassen und werden lokal in res/kw_data je Kalenderwoche "
                "gespeichert."},
    {"cat": "Arbeitszeiten",
     "title": "Gleitzeitkonto (GLZ) und Tagesstatus",
     "content": "Pro Tag gibt es einen Status: Arbeit, Krank, Urlaub, Kurzarbeit, "
                "GLZ, Feiertag, Sonstiges oder Frei. Das Gleitzeitkonto ergibt sich "
                "aus geleisteten Stunden minus Soll (8 h an Werktagen); GLZ und "
                "Kurzarbeit ziehen das Soll ab. Wochenende ist standardmäßig frei."},
    {"cat": "Arbeitszeiten",
     "title": "Servicezeitenmeldung als Excel oder PDF exportieren",
     "content": "Über 'Excel-Export' wird die Servicezeitenmeldung als Excel-Datei "
                "erzeugt, über 'PDF-Export' dieselbe Meldung als PDF. Der Zielordner "
                "lässt sich in den Einstellungen festlegen. Bei Innendienst/Homeoffice "
                "kann ein Allgemeinkosten-Code (z.B. 0020 Service Hotline) angegeben "
                "werden."},

    # ── Reisekosten (ausführlich) ───────────────────────────────────────────
    {"cat": "Reisekosten",
     "title": "Reisekosten: Wochenansicht (KW) erfassen",
     "content": "Die Reisekosten-Seite arbeitet je Kalenderwoche (KW) und zeigt "
                "Montag bis Sonntag mit allen Feldern inkl. Verpflegung/Mahlzeiten und "
                "Sonstigem. Nach einem Salesforce-Import werden die Daten automatisch "
                "lokal gespeichert (res/kw_data)."},
    {"cat": "Reisekosten",
     "title": "Reisekostenabrechnung exportieren (FB_0020-Vorlage)",
     "content": "'Excel-Export' füllt die offizielle FB_0020-Reisekostenvorlage aus "
                "(liegt in res/templates). 'PDF-Export' erzeugt die Abrechnung als PDF "
                "ohne Vorlage. Jahr und KW werden oben über die Auswahl eingestellt."},

    # ── Ersatzteile & Bestellung (ausführlich) ──────────────────────────────
    {"cat": "Ersatzteile",
     "title": "Ersatzteilkatalog je Gerätesystem durchsuchen",
     "content": "Im Menü Ersatzteile wird der Katalog je Gerätesystem durchsucht. "
                "Die Daten liegen in res/et/<system>.json; welche Systeme es gibt, "
                "steht in res/et/systeme.json. Neue Systeme und Einträge lassen sich "
                "direkt im Tool anlegen. Ein Doppelklick auf ein Teil übernimmt es in "
                "die aktuelle Bestellung."},
    {"cat": "Bestellung",
     "title": "Bestellung anlegen, speichern und laden",
     "content": "Eine Bestellung besteht aus Name, Datum und Positionen "
                "(Bestellnummer, Name, Anzahl). Bestellungen werden als JSON unter "
                "res/orders/<id>.json mit fortlaufender Nummer gespeichert und über "
                "die Combobox 'Bestellung laden' wieder geöffnet. Positionen können "
                "jederzeit manuell hinzugefügt und bearbeitet werden."},
    {"cat": "Bestellung",
     "title": "Favoriten für häufige Ersatzteile",
     "content": "Häufig benötigte Teile lassen sich als Favoriten speichern "
                "(res/orders/favoriten.json) und beim nächsten Mal schneller in eine "
                "Bestellung übernehmen. Die Bestellung lässt sich als Excel oder PDF "
                "exportieren."},

    # ── Datenbank / Serviceberichte (ausführlich) ───────────────────────────
    {"cat": "Datenbank",
     "title": "Serviceberichte automatisch per Mail importieren",
     "content": "Im Menü Datenbank werden Serviceberichte, verbrauchte Mittel und "
                "Kunden aus der (Railway-PostgreSQL-)Datenbank angezeigt. Über "
                "'E-Mails abrufen' werden ungelesene Mails mit PDF-Anhang per IMAP "
                "geholt, mit Claude analysiert und automatisch in die DB eingefügt. "
                "Mit 'PDF analysieren' geht das auch manuell. Berichte lassen sich "
                "wieder löschen."},
    {"cat": "Datenbank",
     "title": "Mail-Abruf einrichten (IMAP)",
     "content": "Die Mail-Zugangsdaten (Host, Port, Benutzer, Passwort, Ordner) "
                "stehen in res/service_config.json; DB-URL und Anthropic-API-Key "
                "kommen aus der .env. Für Gmail wird ein App-Passwort und der Server "
                "imap.gmail.com:993 benötigt. Es werden nur ungelesene Mails "
                "verarbeitet und danach als gelesen markiert."},

    # ── Fehlerdiagnose & Anleitungen (ausführlich) ──────────────────────────
    {"cat": "Fehlerdiagnose",
     "title": "Fehlerdiagnose: Fehlercodes nachschlagen und eigene anlegen",
     "content": "Die Fehlerdiagnose ist eine Master-Detail-Ansicht je Gerätesystem. "
                "Daten liegen in res/fd/<system>.json; die Systemliste in "
                "res/fd/systeme.json. Über die Suche findest du Fehler und Lösungen; "
                "neue Systeme und Einträge lassen sich direkt im Tool anlegen und "
                "speichern. Diese Einträge durchsucht auch der Service-Assistent."},
    {"cat": "Anleitungen",
     "title": "Anleitungen: Kategorien, Suche und PDF-Verweis",
     "content": "Anleitungen liegen je Kategorie in res/anl/<kategorie>.json. Oben "
                "kann eine einzelne Kategorie oder 'Alle' (Voreinstellung) gewählt "
                "werden; die Spalte 'Kategorie' zeigt die Zuordnung (z.B. Hotline). "
                "Gesucht wird in Titel UND Inhalt; Titeltreffer werden bevorzugt. "
                "Einträge können auf eine zugehörige PDF verweisen."},

    # ── Lager & Dashboard (Demo) ────────────────────────────────────────────
    {"cat": "Mein Lager",
     "title": "Mein Lager: Bestand, Unterbestands-Warnung, PDF",
     "content": "Mein Lager zeigt den persönlichen Fahrzeug-/Kofferbestand mit Suche "
                "und Unterbestands-Warnung und kann als PDF exportiert werden (nutzt "
                "QPdfWriter, keine Zusatzbibliothek nötig). Aktuell sind die Bestände "
                "Beispieldaten (Mock); später ist ein read-only SAP-Zugriff geplant."},
    {"cat": "Dashboard",
     "title": "Dashboard 'Meine Woche' (Vorschau)",
     "content": "Das Dashboard zeigt KPI-Karten (Stunden, offene Aufträge, "
                "gefahrene km, verbaute Teile), ein Wochen-Chart (Stunden je "
                "Wochentag) und die nächsten Termine. Aktuell sind das Beispieldaten "
                "(Mock); Layout und Chart funktionieren bereits, später kommen echte "
                "Daten aus Arbeitszeiten/Reisekosten und Salesforce."},

    # ── Einstellungen / Update / Technik ────────────────────────────────────
    {"cat": "Einstellungen",
     "title": "Farbthema und Export-Ordner anpassen",
     "content": "Unter Einstellungen lassen sich persönliche Daten, der "
                "Export-Zielordner für Excel/PDF, das Farbthema (einzelne Farben per "
                "Farbwähler) sowie die Update-URL und die automatische Update-Prüfung "
                "einstellen. Farbänderungen werden nach einem Neustart wirksam."},
    {"cat": "Update",
     "title": "Programm aktualisieren (Selbst-Update)",
     "content": "Das Tool prüft (optional beim Start oder manuell) eine hinterlegte "
                "version.json-URL und bietet bei neuerer Version ein Update an. Der "
                "Download läuft nur über HTTPS und wird per SHA-256-Prüfsumme "
                "verifiziert; stimmt sie nicht, wird abgebrochen. Der letzte "
                "Prüfstand erscheint auf der Info-Seite."},
    {"cat": "Technik",
     "title": "Technische Basis (Python, PyQt6, Daten)",
     "content": "Das Service Tool ist in Python (py) ab 3.10 mit PyQt6 geschrieben. "
                "Alle Daten liegen lokal im res-Ordner als JSON (Arbeitszeiten in "
                "res/kw_data, Kataloge in res/et, res/fd, res/anl, Bestellungen in "
                "res/orders). Externe Zugriffe nur auf Salesforce, die Service-DB und "
                "das Mail-Postfach. Der Service-Assistent arbeitet komplett offline."},
    {"cat": "Datenschutz",
     "title": "Welche Daten verlassen den PC?",
     "content": "Lokal bleibt alles im res-Ordner. Internet wird nur genutzt für: "
                "Salesforce-Anmeldung/-Import, die Serviceberichts-Datenbank, den "
                "Mail-Abruf und die optionale Update-Prüfung. Für die automatische "
                "Berichtsanalyse werden PDF-Inhalte an die Claude-API gesendet "
                "(API-Key aus der .env). Der Assistent selbst sendet nichts."},

    # ── Service-Assistent (Bedienung) ───────────────────────────────────────
    {"cat": "Service-Assistent",
     "title": "Assistent findet nichts / eigenes Wissen ergänzen",
     "content": "Der Assistent durchsucht Fehlerdiagnose (res/fd), Anleitungen "
                "(res/anl), die Programm-Hilfe und zusätzliche Dokumentation in "
                "res/docs (.md je Überschrift, .json im entries-Format). Nach dem "
                "Hinzufügen oder Ändern einer Datei auf 'Wissen neu laden' klicken "
                "(kein Neustart nötig). Findet die Suche nichts, mit anderen "
                "Stichworten versuchen — Bauteil, Fehlertext oder Menüname statt "
                "ganzer Sätze."},
]


def _tokens(text):
    """Zerlegt Text in bedeutungstragende Kleinbuchstaben-Wörter.

    Wörter ab 2 Zeichen werden berücksichtigt — kurze, aber bedeutungsvolle
    Fach-/Abkürzungen wie 'sf' (Salesforce), 'kw', 'pdf', 'sap', 'py' oder 'et'
    sollen suchbar sein. Nur 1-Zeichen-Reste und Stopwörter werden verworfen."""
    return [t for t in re.findall(r"\w+", (text or "").lower())
            if len(t) >= 2 and t not in _STOPWORDS]


def _split_markdown(text, default_title):
    """
    Zerlegt Markdown in (Titel, Inhalt)-Abschnitte — je Überschrift (# … ######)
    ein Abschnitt. Text vor der ersten Überschrift wird als eigener Abschnitt
    behalten. Gibt (doc_titel, [(titel, inhalt), …]) zurück, wobei doc_titel
    die erste H1-Überschrift ist (sonst der Dateiname).
    """
    doc_title = default_title
    sections = []
    cur_title = default_title
    cur_buf = []
    saw_heading = False

    def flush():
        body = "\n".join(cur_buf).strip()
        # Leere Vorspann-Abschnitte (nur der Standardtitel, kein Text) auslassen
        if body or cur_title != default_title:
            sections.append((cur_title, body))

    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            if cur_buf or saw_heading:
                flush()
            cur_title = m.group(2).strip()
            cur_buf = []
            saw_heading = True
            if len(m.group(1)) == 1 and doc_title == default_title:
                doc_title = cur_title
        else:
            cur_buf.append(line)

    if cur_buf or saw_heading:
        flush()
    return doc_title, sections


class AssistentSeite(QWidget):
    """Offline-Suchassistent über Fehlerdiagnose, Anleitungen und Programm-Hilfe."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._docs = []          # Liste der durchsuchbaren Wissens-Einträge
        self._build()
        self._lade_wissen()
        self._begruessung()

    # ── Wissen laden ──────────────────────────────────────────────────────────

    def _lade_wissen(self):
        """Sammelt alle Einträge aus Fehlerdiagnose, Anleitungen und der
        Programm-Hilfe in eine einheitliche, durchsuchbare Liste."""
        self._docs = []

        # Fehlerdiagnose
        for key, label in load_registry(FD_DIR, {}).items():
            for e in load_liste(FD_DIR, key, "entries"):
                self._add_doc("Fehlerdiagnose", label, e)

        # Anleitungen / Hotline
        for key, label in load_registry(ANL_DIR, {}).items():
            for e in load_liste(ANL_DIR, key, "entries"):
                self._add_doc("Anleitungen", label, e)

        # Programm-Hilfe
        for e in PROGRAMM_HILFE:
            self._add_doc("Programm-Hilfe", "Service Tool", e)

        # Programm-Referenz (Module, Modul-Docstrings) automatisch aus den
        # vorhandenen Quellen erzeugen — wird danach mit eingelesen.
        try:
            from wissen_generator import programm_wissen_schreiben
            programm_wissen_schreiben()
        except Exception:
            pass

        # Zusätzliche Dokumentation aus res/docs (optional)
        self._lade_dokumentation()

    def _lade_dokumentation(self):
        """Liest optionale Doku aus res/docs ein: .md (je Überschrift ein
        Abschnitt) und .json (Format {"entries": [...]} oder eine Liste von
        {title, content}). Dateinamen, die mit '_' oder '.' beginnen, werden
        übersprungen — so kann man Vorlagen/Notizen ablegen, ohne dass sie
        durchsucht werden."""
        try:
            os.makedirs(DOCS_DIR, exist_ok=True)
            dateien = sorted(os.listdir(DOCS_DIR))
        except OSError:
            return

        for name in dateien:
            if name.startswith(("_", ".")):
                continue
            pfad = os.path.join(DOCS_DIR, name)
            if not os.path.isfile(pfad):
                continue
            ext = os.path.splitext(name)[1].lower()
            try:
                if ext in (".md", ".markdown", ".txt"):
                    with open(pfad, encoding="utf-8") as f:
                        text = f.read()
                    doc_titel, abschnitte = _split_markdown(
                        text, os.path.splitext(name)[0])
                    for titel, inhalt in abschnitte:
                        self._add_doc("Dokumentation", doc_titel,
                                      {"title": titel, "content": inhalt})
                elif ext == ".json":
                    with open(pfad, encoding="utf-8") as f:
                        daten = json.load(f)
                    eintraege = daten.get("entries", []) if isinstance(daten, dict) else daten
                    doc_titel = (daten.get("system") if isinstance(daten, dict) else None) \
                        or os.path.splitext(name)[0]
                    for e in eintraege:
                        if isinstance(e, dict):
                            self._add_doc("Dokumentation", doc_titel, e)
            except Exception:
                # Eine fehlerhafte Datei darf den Assistenten nicht lahmlegen.
                continue

    def _add_doc(self, quelle, system, eintrag):
        title = (eintrag.get("title") or "").strip()
        content = (eintrag.get("content") or "").strip()
        cat = (eintrag.get("cat") or "").strip()
        if not title and not content:
            return
        self._docs.append({
            "quelle": quelle, "system": system, "cat": cat,
            "title": title, "content": content,
            "_title_l": title.lower(), "_cat_l": cat.lower(),
            "_content_l": content.lower(),
        })

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(12)

        root.addWidget(page_hero(
            "icons/assistent.png", "Service-Assistent",
            "Frag den Assistenten zu Fehlern, Anleitungen und dem Programm",
            "Offline-Suche über das vorhandene Wissen — ohne Internet, ohne Kosten.",
        ))

        # Chat-Verlauf
        self._chat = QTextBrowser()
        self._chat.setOpenExternalLinks(False)
        self._chat.setStyleSheet(
            f"QTextBrowser {{ background:{C['surface']}; color:{C['text']};"
            f" border:1px solid {C['border']}; border-radius:10px; padding:10px; }}")
        root.addWidget(self._chat, 1)

        # Eingabezeile
        bar = QFrame()
        bar.setStyleSheet(f"background:{C['surface']}; border-radius:10px;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 8, 12, 8)
        bl.setSpacing(8)
        self._eingabe = QLineEdit()
        self._eingabe.setPlaceholderText(
            "Frage oder Symptom eingeben, z.B. „Rückflusssensor Fehler“ oder "
            "„Wie exportiere ich Reisekosten?“ …")
        self._eingabe.returnPressed.connect(self._frage_stellen)
        bl.addWidget(self._eingabe, 1)
        bl.addWidget(btn("Senden", self._frage_stellen, color=C["accent"]))
        bl.addWidget(btn("🔄 Wissen neu laden", self._wissen_neu_laden,
                         "Liest Fehlerdiagnose, Anleitungen, Programm-Hilfe und die "
                         "Dokumentation aus res/docs erneut ein — z.B. nach dem "
                         "Hinzufügen oder Ändern einer Datei (kein Neustart nötig)."))
        bl.addWidget(btn("Verlauf leeren", self._verlauf_leeren))
        root.addWidget(bar)

    def _begruessung(self):
        self._append_bot(
            f"Hallo! Ich durchsuche <b>{len(self._docs)}</b> Wissens-Einträge "
            "(Fehlerdiagnose, Anleitungen und Programm-Hilfe). "
            "Beschreibe dein Problem oder stell eine Frage zum Tool — ich zeige dir "
            "die passendsten Einträge.")

    # ── Suche / Relevanzbewertung ─────────────────────────────────────────────

    def _suche(self, frage, max_treffer=4):
        """Bewertet alle Einträge gegen die Frage und gibt die besten zurück."""
        q_tokens = _tokens(frage)
        q_phrase = frage.strip().lower()
        if not q_tokens:
            return []

        ergebnisse = []
        for doc in self._docs:
            score = 0
            for tok in set(q_tokens):
                if tok in doc["_title_l"]:
                    score += 6
                if tok in doc["_cat_l"]:
                    score += 4
                # Häufigkeit im Inhalt, gedeckelt (lange Einträge nicht bevorzugen)
                score += min(doc["_content_l"].count(tok), 3)
            # Bonus, wenn die ganze Phrase exakt vorkommt
            if len(q_phrase) > 4 and (q_phrase in doc["_title_l"]
                                      or q_phrase in doc["_content_l"]):
                score += 8
            if score > 0:
                ergebnisse.append((score, doc))

        ergebnisse.sort(key=lambda x: x[0], reverse=True)
        return ergebnisse[:max_treffer]

    @staticmethod
    def _snippet(content, frage, laenge=320):
        """Schneidet einen sinnvollen Ausschnitt rund um den ersten Treffer aus."""
        content = re.sub(r"[ \t]+", " ", content).strip()
        low = content.lower()
        pos = -1
        for tok in _tokens(frage):
            pos = low.find(tok)
            if pos != -1:
                break
        if pos == -1:
            return content[:laenge] + ("…" if len(content) > laenge else "")
        start = max(0, pos - 60)
        ende = min(len(content), start + laenge)
        text = content[start:ende]
        return ("…" if start > 0 else "") + text + ("…" if ende < len(content) else "")

    # ── Interaktion ───────────────────────────────────────────────────────────

    def _frage_stellen(self):
        frage = self._eingabe.text().strip()
        if not frage:
            return
        self._append_user(frage)
        self._eingabe.clear()

        treffer = self._suche(frage)
        if not treffer:
            self._append_bot(
                "Dazu habe ich leider nichts im hinterlegten Wissen gefunden. "
                "Versuch es mit anderen Stichworten (z.B. Bauteil, Fehlertext oder "
                "Menüname).")
            return

        bester_score = treffer[0][0]
        teile = [f"Ich habe <b>{len(treffer)}</b> passende Einträge gefunden — "
                 "der wahrscheinlichste zuerst:"]
        for rang, (score, doc) in enumerate(treffer, start=1):
            # Relevanz relativ zum besten Treffer (nur zur groben Orientierung)
            rel = int(round(100 * score / bester_score)) if bester_score else 0
            badge = (f"<span style='color:{C['subtext']}; font-size:8pt;'>"
                     f"[{doc['quelle']} · {doc['system']}"
                     + (f" · {doc['cat']}" if doc['cat'] else "")
                     + f" · Relevanz {rel}%]</span>")
            kopf = (f"<div style='margin-top:8px;'><b style='color:{C['accent']};'>"
                    f"{rang}. {doc['title'] or '(ohne Titel)'}</b><br>{badge}</div>")
            text = self._snippet(doc["content"], frage)
            koerper = (f"<div style='margin:2px 0 6px 0;'>{self._html(text)}</div>"
                       if text else "")
            teile.append(kopf + koerper)
        self._append_bot("".join(teile))

    # ── Chat-Ausgabe ──────────────────────────────────────────────────────────

    @staticmethod
    def _html(text):
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br>"))

    def _append_user(self, text):
        self._chat.append(
            f"<div style='margin:8px 0;'><span style='color:{C['accent']};"
            f" font-weight:bold;'>Du:</span> {self._html(text)}</div>")
        self._scroll_unten()

    def _append_bot(self, html):
        self._chat.append(
            f"<div style='margin:8px 0; padding:8px 10px; background:{C['surface2']};"
            f" border-radius:8px;'><span style='color:{C['green']}; font-weight:bold;'>"
            f"Assistent:</span> {html}</div>")
        self._scroll_unten()

    def _scroll_unten(self):
        sb = self._chat.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _verlauf_leeren(self):
        self._chat.clear()
        self._begruessung()

    def _wissen_neu_laden(self):
        """Lädt alle Wissensquellen neu (Fehlerdiagnose, Anleitungen,
        Programm-Hilfe und res/docs) — nützlich, wenn während des Programmlaufs
        eine Datei hinzugefügt oder geändert wurde (vermeidet einen Neustart)."""
        vorher = len(self._docs)
        self._lade_wissen()
        nachher = len(self._docs)
        self._append_bot(
            f"Wissen neu eingelesen: jetzt <b>{nachher}</b> Einträge "
            f"(vorher {vorher}). Quellen: Fehlerdiagnose, Anleitungen, "
            f"Programm-Hilfe und <code>res/docs</code> (*.md, *.json).")
        self.status_msg.emit(f"🔄  Wissen neu geladen ({nachher} Einträge).")
