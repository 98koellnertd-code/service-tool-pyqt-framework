#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wissen_generator.py
Erzeugt aus den vorhandenen, gepflegten Programm-Quellen automatisch eine
durchsuchbare Wissensdatei für den Service-Assistenten:

    res/docs/programm_referenz.md

Quellen (alle bereits im Programm vorhanden — eine Quelle der Wahrheit):
  • utils.MODULES            – Name + Beschreibung jedes Moduls
  • gprint_core.BUILTIN_COMMANDS (optional, nur alphaJET) – G-PRINT-Schnellbefehle
  • die Modul-Docstrings der seite_*.py (aus sys.modules gelesen — daher auch
    in der gepackten .exe verfügbar, ohne Quellcode mitzuliefern)

Die Datei wird bei jedem Öffnen des Assistenten neu geschrieben und ist reine
Maschinenausgabe — NICHT von Hand bearbeiten. Eigene, dauerhafte Hilfe-Artikel
als separate faq_*.md in res/docs ablegen (die werden nie überschrieben).

Bewusst NICHT umgesetzt: das Einlesen von rohem Quellcode aus dem MEIPASS-
Ordner. Im PyInstaller-Build liegt der Code als kompiliertes Bytecode-Archiv
vor (nicht als lesbare .py), und roher Code wäre für Servicetechniker nur
Rauschen, das die Relevanzbewertung der Suche verschlechtert.
"""

import os
import sys

from utils import MODULES, APP_NAME, RES_DIR

try:
    from gprint_core import BUILTIN_COMMANDS
except Exception:           # TimingTool / Programme ohne G-PRINT
    BUILTIN_COMMANDS = None

DOCS_DIR    = os.path.join(RES_DIR, "docs")
OUTPUT_FILE = os.path.join(DOCS_DIR, "programm_referenz.md")

# Ab diesen Markierungen enthält ein Docstring entwickler-internes Detail
# (Migrationshinweise, Architektur), das für den Techniker irrelevant ist.
_NOISE_MARKERS = (
    "Nachgebaut", "PyQt-Pendant", "Reine ", "Hinweis zur Anpassung",
    "Felder je", "Cross-page", "Alle blockierenden", "Die reine",
    "Vollständige Portierung", "Portierung des", "(PyQt6-Portierung)",
    "Datenquellen:",
)


def _clean_docstring(doc: str) -> str:
    """Macht aus einem Modul-Docstring sauberen, technikertauglichen Text:
    entfernt die erste Zeile (Dateiname) und schneidet ab dem ersten
    Entwickler-Detail-Marker ab."""
    lines = (doc or "").strip().splitlines()
    if lines and lines[0].strip().lower().startswith(("seite_", "wissen_")):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    for marker in _NOISE_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].rstrip(" \n.,;:–-")
    return text.strip()


def _nice_title(modname: str) -> str:
    """seite_print_control -> 'Print Control'."""
    base = modname.replace("seite_", "").replace("_", " ").strip()
    return base.title() if base else modname


def programm_wissen_schreiben() -> str | None:
    """Schreibt res/docs/programm_referenz.md neu und gibt den Pfad zurück
    (oder None bei Fehler — der Assistent läuft dann ohne diese Datei weiter)."""
    try:
        os.makedirs(DOCS_DIR, exist_ok=True)
        parts = [
            f"# {APP_NAME} — Programm-Referenz",
            "",
            "> Automatisch erzeugt beim Start des Service-Assistenten. "
            "Nicht von Hand bearbeiten — eigene Artikel als faq_*.md ablegen.",
            "",
        ]

        # ── Module (aus utils.MODULES) ────────────────────────────────────────
        for m in MODULES:
            parts.append(f"## Modul: {m['name']}")
            parts.append(m["desc"])
            parts.append("")

        # ── G-PRINT-Schnellbefehle (nur alphaJET) ─────────────────────────────
        if BUILTIN_COMMANDS:
            parts.append("## G-PRINT-Schnellbefehle")
            parts.append("Eingebaute Kommandos der Schnell-Befehle-Seite "
                         "(Protokoll G-PRINT, TCP, Standard-Port 3000):")
            for label, xml in BUILTIN_COMMANDS:
                parts.append(f"- **{label}** — sendet `{xml}`")
            parts.append("")

        # ── Modul-Details (bereinigte Docstrings aus sys.modules) ─────────────
        for name in sorted(sys.modules):
            if not name.startswith("seite_"):
                continue
            mod = sys.modules.get(name)
            doc = getattr(mod, "__doc__", None) if mod else None
            clean = _clean_docstring(doc) if doc else ""
            if len(clean) < 60:
                continue
            parts.append(f"## {_nice_title(name)} — Details")
            parts.append(clean)
            parts.append("")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(parts).rstrip() + "\n")
        return OUTPUT_FILE
    except Exception:
        return None
