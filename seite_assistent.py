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
]


def _tokens(text):
    """Zerlegt Text in bedeutungstragende Kleinbuchstaben-Wörter."""
    return [t for t in re.findall(r"\w+", (text or "").lower())
            if len(t) > 2 and t not in _STOPWORDS]


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
        root.setContentsMargins(20, 16, 20, 16)
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
