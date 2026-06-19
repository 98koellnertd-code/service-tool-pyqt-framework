#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py
Zentrale Hilfsmodule für das Servicetechniker Tool.

Hier liegt alles, was von mehreren Menüs gemeinsam genutzt wird:
  - Pfade (BASE_DIR, RES_DIR, ...)
  - Farbpalette & Stylesheet (einheitliches Dark-Theme)
  - JSON-Lade-/Speicherfunktionen
  - Datums-/Zeit-Hilfsfunktionen für Arbeitszeiten & Reisekosten
  - Kleine Widget-Ersteller (Buttons, Labels, Trennlinien, Eingabefelder)

Alle anderen Module importieren aus dieser Datei, statt Dinge doppelt
zu definieren.
"""

import sys
import os
import json
import datetime
import calendar
import shutil
import subprocess
import tempfile
from collections import defaultdict

from PyQt6.QtWidgets import (
    QFrame, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

# ══════════════════════════════════════════════════════════════════════════════
# Pfade
# ══════════════════════════════════════════════════════════════════════════════
# Läuft das Tool als gebaute EXE (PyInstaller), liegt BASE_DIR neben der EXE,
# ansonsten neben dem Skript.
# MEIPASS_DIR ist bei einer --onefile-EXE der temporäre Entpack-Ordner, in dem
# über --add-data fest eingebettete Dateien (z.B. icon.ico) zur Laufzeit landen.
# Für res/ wird das NICHT genutzt, da dort auch geschrieben wird (Profile,
# Vorlagen) und der MEIPASS-Ordner bei jedem Start verworfen wird.
if getattr(sys, "frozen", False):
    BASE_DIR    = os.path.dirname(sys.executable)
    MEIPASS_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    MEIPASS_DIR = BASE_DIR

RES_DIR       = os.path.join(BASE_DIR, "res")
KW_DIR        = os.path.join(RES_DIR, "kw_data")
TEMPLATES_DIR = os.path.join(RES_DIR, "templates")
ET_DIR        = os.path.join(RES_DIR, "et")   # Ersatzteile
FD_DIR        = os.path.join(RES_DIR, "fd")   # Fehlerdiagnose
ANL_DIR       = os.path.join(RES_DIR, "anl")  # Anleitungen (Dokus mit PDF-Verweis)
ORDERS_DIR    = os.path.join(RES_DIR, "orders")        # Bestellungen (JSON je Bestellung, Favoriten)
PROFILE_FILE  = os.path.join(RES_DIR, "user_profile.json")
KUNDEN_FILE   = os.path.join(RES_DIR, "kunden_vorlagen.json")
COLOR_FILE    = os.path.join(RES_DIR, "farben.json")
# Zwischenspeicher der zuletzt von der Update-URL gelesenen version.json
# (Version, Changelog, Download-URL) — damit die Info-Seite diese Angaben
# auch ohne erneuten Netzwerkaufruf anzeigen kann (siehe updater.py).
UPDATE_CACHE_FILE = os.path.join(RES_DIR, "update_cache.json")
# Titelleiste / Fenster-Icon: .ico (enthält mehrere Auflösungen, ideal für die
# OS-Titelleiste und Taskleiste).
ICON_FILE     = os.path.join(MEIPASS_DIR, "icon.ico")
# Hochauflösende PNG für die Darstellung im App-Header (Sidebar-Markenkopf) —
# eine .ico würde dort beim Herunterskalieren verpixeln, die PNG bleibt scharf.
ICON_PNG      = os.path.join(MEIPASS_DIR, "icons", "icon.png")

# Standard-Exportordner für Servicezeitenmeldung (Arbeitszeiten) und
# Reisekostenabrechnung (Reisekosten) — auf der Einstellungen-Seite
# änderbar (siehe get_arbeitszeiten_export_dir/get_reisekosten_export_dir,
# Profil-Schlüssel "export_dir_arbeitszeiten"/"export_dir_reisekosten").
ARBEITSZEITEN_EXPORT_DIR_DEFAULT = os.path.join(RES_DIR, "arbeitszeiten")
REISEKOSTEN_EXPORT_DIR_DEFAULT   = os.path.join(RES_DIR, "reisekosten")
# Excel-Export-Ordner für Bestellungen — wie bei Arbeitszeiten/Reisekosten
# auf der Einstellungen-Seite überschreibbar (siehe get_bestellungen_export_dir,
# Profil-Schlüssel "export_dir_bestellungen").
BESTELLUNGEN_EXPORT_DIR_DEFAULT  = os.path.join(RES_DIR, "bestellungen")

for _d in [RES_DIR, KW_DIR, TEMPLATES_DIR, ET_DIR, FD_DIR, ANL_DIR, ORDERS_DIR,
           ARBEITSZEITEN_EXPORT_DIR_DEFAULT, REISEKOSTEN_EXPORT_DIR_DEFAULT,
           BESTELLUNGEN_EXPORT_DIR_DEFAULT]:
    os.makedirs(_d, exist_ok=True)


def get_arbeitszeiten_export_dir(profile):
    """Aktuellen Export-Ordner für die Servicezeitenmeldung liefern (Standard
    oder per Einstellungen überschriebener Pfad) und sicherstellen, dass er existiert."""
    path = (profile or {}).get("export_dir_arbeitszeiten") or ARBEITSZEITEN_EXPORT_DIR_DEFAULT
    os.makedirs(path, exist_ok=True)
    return path


def get_reisekosten_export_dir(profile):
    """Aktuellen Export-Ordner für die Reisekostenabrechnung liefern (Standard
    oder per Einstellungen überschriebener Pfad) und sicherstellen, dass er existiert."""
    path = (profile or {}).get("export_dir_reisekosten") or REISEKOSTEN_EXPORT_DIR_DEFAULT
    os.makedirs(path, exist_ok=True)
    return path


def get_bestellungen_export_dir(profile):
    """Aktuellen Export-Ordner für den Bestellungen-Excel-Export liefern (Standard
    oder per Einstellungen überschriebener Pfad) und sicherstellen, dass er existiert."""
    path = (profile or {}).get("export_dir_bestellungen") or BESTELLUNGEN_EXPORT_DIR_DEFAULT
    os.makedirs(path, exist_ok=True)
    return path


def find_reisekosten_template():
    """
    Sucht die FB_0020-Reisekostenabrechnung-Vorlage in TEMPLATES_DIR. Der
    Dateiname enthält je Versionsstand einen Zusatz (z.B. 'FB_0020_Reise-
    kostenabrechnung V4.4_R09.xlsm'), daher wird per Präfix gesucht statt
    eines exakten Dateinamens.
    """
    import glob
    matches = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "FB_0020*")))
    return matches[0] if matches else None


# ══════════════════════════════════════════════════════════════════════════════
# PyInstaller-Temp-Ordner (_MEIxxxxx) aufräumen & Neustart
# ══════════════════════════════════════════════════════════════════════════════
# Eine --onefile-EXE entpackt sich bei jedem Start in einen frischen _MEIxxxxx-
# Ordner im Temp-Verzeichnis. Beendet sich das Programm normal (sys.exit /
# Event-Loop läuft regulär aus), räumt der PyInstaller-Bootloader diesen
# Ordner automatisch selbst auf — das passiert NICHT, wenn der Prozess
# stattdessen per os.execv() ersetzt oder hart abgeschossen wird, deshalb
# wird für den Neustart bewusst ein neuer Prozess gestartet und der alte
# ganz regulär beendet (siehe restart_app()).
# cleanup_orphaned_meipass() fängt zusätzlich Reste vorheriger Abstürze ab.

def cleanup_orphaned_meipass():
    """
    Entfernt verwaiste _MEIxxxxx-Ordner früherer (z.B. abgestürzter) Läufe
    aus dem Temp-Verzeichnis. Der Ordner des AKTUELL laufenden Prozesses
    (sys._MEIPASS) wird dabei nie berührt. Fehler (z.B. weil ein anderer
    Prozess noch läuft und den Ordner sperrt) werden bewusst ignoriert.
    """
    if not getattr(sys, "frozen", False):
        return
    current = getattr(sys, "_MEIPASS", None)
    tmp_dir = tempfile.gettempdir()
    try:
        for name in os.listdir(tmp_dir):
            if not name.startswith("_MEI"):
                continue
            full = os.path.join(tmp_dir, name)
            if full == current:
                continue
            shutil.rmtree(full, ignore_errors=True)
    except Exception:
        pass


def restart_app():
    """
    Startet die Anwendung als neuen Prozess neu und beendet den aktuellen
    danach regulär (kein os.execv!), damit der PyInstaller-Bootloader den
    _MEIPASS-Ordner des alten Prozesses ordentlich aufräumen kann. Vor dem
    Start des neuen Prozesses werden zusätzlich Reste älterer Läufe entfernt.

    Der Aufrufer (z.B. ein Button in den Einstellungen) muss nach diesem
    Aufruf nur noch QApplication.quit() bzw. die Event-Loop normal beenden
    lassen — main() läuft dann zu Ende und der Prozess schließt sauber.
    """
    cleanup_orphaned_meipass()
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])])

# ══════════════════════════════════════════════════════════════════════════════
# Konstanten
# ══════════════════════════════════════════════════════════════════════════════
APP_NAME    = "Service - Tool"
APP_VERSION = "1.0"
SF_INSTANCE_URL = "https://koenig-bauer.my.salesforce.com"
SF_API_VER      = "v59.0"

DAY_NAMES   = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTH_NAMES = ["Januar", "Februar", "März", "April", "Mai", "Juni",
               "Juli", "August", "September", "Oktober", "November", "Dezember"]
STATUS_OPTIONS = ["Arbeit", "Krank", "Urlaub", "Kurzarbeit", "GLZ", "Feiertag", "Sonstiges", "Frei"]

BUNDESLAND_NAMES = {
    "BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin",
    "BB": "Brandenburg", "HB": "Bremen", "HH": "Hamburg", "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SL": "Saarland",
    "SN": "Sachsen", "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}

ALLGEMEIN_CODES = {
    "0010": "Customer Preparation", "0020": "Service Hotline",
    "0030": "Maintenance of Rental Equipment", "0040": "Department of Rental Equipment",
    "0050": "Cleaning Service", "0060": "Internal Meetings / Trainings",
    "0070": "Inventory Service", "0080": "Materials Management Activities",
    "0090": "Documentation Activities", "0100": "Fixture Construction",
    "0120": "Inspection of Returns", "0130": "Proactive Customer Service",
    "0140": "Automotive Workshop / Inspection", "0180": "Preparation Training Documents",
    "0190": "Dealer & Subsidiary Support", "0200": "Online Training Preparation",
    "2100": "Activities Service Cloud",
}

# ══════════════════════════════════════════════════════════════════════════════
# Farbpalette (Helles Theme — heller Hintergrund, dunkler Text)
# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT_COLORS ist die Werks-Palette. In der Einstellungen-Seite ("🎨
# Farbanpassung") kann der Benutzer einzelne Farben überschreiben — diese
# Anpassungen werden in COLOR_FILE (res/farben.json) gespeichert und beim
# nächsten Programmstart über load_colors() automatisch wieder eingelesen.
DEFAULT_COLORS = {
    "bg":      "#f0f1f4", "surface":  "#ffffff", "surface2": "#f7f8fa",
    "overlay": "#e2e5ea", "header":   "#e7e9ed", "border":   "#cbd0d6",
    "text":    "#1e2127", "subtext":  "#5b6270", "dimtext":  "#9aa0ab",
    "accent":  "#2563eb", "green":    "#16a34a", "red":      "#dc2626",
    "yellow":  "#b45309", "mauve":    "#7c3aed",
    # Tag-Status-Farben (helle, pastellige Hintergründe statt dunkler Tönung)
    "krank_bg":  "#fde2e2", "urlaub_bg": "#fef3c7", "we_bg": "#eceef1",
    "glz_bg":    "#dbeafe",
}

# Lesbare Anzeigenamen für die Farbanpassung-Seite (Reihenfolge = Anzeige-
# reihenfolge der Buttons).
COLOR_LABELS = {
    "bg":        "Hintergrund",
    "surface":   "Fläche (Karten/Dialoge)",
    "surface2":  "Fläche, leicht abgesetzt",
    "overlay":   "Hover-Overlay",
    "header":    "Statusleiste",
    "border":    "Rahmen/Trennlinien",
    "text":      "Text",
    "subtext":   "Text, gedämpft",
    "dimtext":   "Text, sehr blass",
    "accent":    "Akzentfarbe",
    "green":     "Grün (Erfolg)",
    "red":       "Rot (Fehler/Warnung)",
    "yellow":    "Gelb/Orange",
    "mauve":     "Violett",
    "krank_bg":  "Tag-Status: Krank",
    "urlaub_bg": "Tag-Status: Urlaub",
    "we_bg":     "Tag-Status: Wochenende",
    "glz_bg":    "Tag-Status: GLZ",
}


# ══════════════════════════════════════════════════════════════════════════════
# Standard-Farbpaletten (Einstellungen → 🎨 Farbanpassung)
# ══════════════════════════════════════════════════════════════════════════════
# Drei Vorlagen, die per Klick in den Einstellungen übernommen werden können.
# Danach bleibt die volle individuelle Anpassung (einzelne Swatches) erhalten —
# die Vorlagen setzen nur einen sinnvollen Startpunkt für _pending_colors.
PRESET_PALETTES = {
    "hell": {
        "label": "☀  Hell (Standard)",
        "colors": dict(DEFAULT_COLORS),
    },
    "hellgrau": {
        "label": "⬜  Hellgrau",
        "colors": {
            "bg":      "#e9e9ec", "surface":  "#f5f5f6", "surface2": "#eeeeef",
            "overlay": "#dcdcde", "header":   "#dddde0", "border":   "#c5c5c9",
            "text":    "#202124", "subtext":  "#5c5e66", "dimtext":  "#97989f",
            "accent":  "#4b5563", "green":    "#3f8a4d", "red":      "#b3433b",
            "yellow":  "#a36a1f", "mauve":    "#6d5b94",
            "krank_bg":  "#f0dcdc", "urlaub_bg": "#efe7d0", "we_bg": "#e2e2e5",
            "glz_bg":    "#d8dee5",
        },
    },
    "dunkel": {
        "label": "🌙  Dunkel",
        "colors": {
            "bg":      "#1b1d23", "surface":  "#23262e", "surface2": "#2a2d36",
            "overlay": "#343844", "header":   "#20222a", "border":   "#3a3e4a",
            "text":    "#e6e7eb", "subtext":  "#aab0bd", "dimtext":  "#737a89",
            "accent":  "#5b8def", "green":    "#22c55e", "red":      "#ef4444",
            "yellow":  "#f59e0b", "mauve":    "#a78bfa",
            "krank_bg":  "#4a2530", "urlaub_bg": "#4a3d1f", "we_bg": "#2f323c",
            "glz_bg":    "#1f3350",
        },
    },
}


def load_colors():
    """
    Werks-Farben + lokal gespeicherte Anpassungen aus COLOR_FILE zusammen-
    führen. Unbekannte/fehlerhafte Einträge werden ignoriert, damit eine
    beschädigte farben.json nie den Programmstart verhindert.
    """
    colors = dict(DEFAULT_COLORS)
    try:
        with open(COLOR_FILE, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        for key, value in overrides.items():
            if key in DEFAULT_COLORS and isinstance(value, str):
                colors[key] = value
    except Exception:
        pass
    return colors


def save_colors(colors):
    """Farbpalette (nur abweichende Werte) lokal in COLOR_FILE speichern."""
    overrides = {k: v for k, v in colors.items() if v != DEFAULT_COLORS.get(k)}
    return save_json(COLOR_FILE, overrides)


C = load_colors()

# ══════════════════════════════════════════════════════════════════════════════
# Globales Stylesheet
# ══════════════════════════════════════════════════════════════════════════════
STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 10pt; color: {C["text"]}; }}
QMainWindow, QWidget {{ background-color: {C["bg"]}; }}
QDialog {{ background-color: {C["surface"]}; }}

/* Scrollbars */
QScrollBar:vertical {{ background:{C["bg"]}; width:8px; border-radius:4px; }}
QScrollBar::handle:vertical {{ background:{C["border"]}; border-radius:4px; min-height:24px; }}
QScrollBar::handle:vertical:hover {{ background:{C["subtext"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar:horizontal {{ background:{C["bg"]}; height:8px; border-radius:4px; }}
QScrollBar::handle:horizontal {{ background:{C["border"]}; border-radius:4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}

/* Eingabefelder */
QLineEdit, QSpinBox, QTextEdit {{
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-radius:5px; padding:4px 8px; color:{C["text"]};
    selection-background-color:{C["accent"]};
}}
QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{ border:1px solid {C["accent"]}; }}
QLineEdit[echoMode="2"] {{ letter-spacing:2px; }}

/* SpinBox (Jahr/KW-Auswahl) — eigene Pfeil-Bereiche, damit Zahl nicht
   von den Knöpfen überlagert wird und die Pfeile gut lesbar sind. */
QSpinBox {{ padding-right:18px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width:16px; background:{C["surface2"]}; border-left:1px solid {C["border"]};
    subcontrol-origin:border;
}}
QSpinBox::up-button {{ subcontrol-position:top right; border-top-right-radius:5px; }}
QSpinBox::down-button {{ subcontrol-position:bottom right; border-bottom-right-radius:5px; border-top:1px solid {C["border"]}; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background:{C["overlay"]}; }}
QSpinBox::up-arrow {{ width:8px; height:8px; image:none; border-left:3px solid transparent; border-right:3px solid transparent; border-bottom:5px solid {C["subtext"]}; }}
QSpinBox::down-arrow {{ width:8px; height:8px; image:none; border-left:3px solid transparent; border-right:3px solid transparent; border-top:5px solid {C["subtext"]}; }}
QSpinBox::up-arrow:hover, QSpinBox::down-arrow:hover {{ border-bottom-color:{C["accent"]}; border-top-color:{C["accent"]}; }}

/* ComboBox */
QComboBox {{
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-radius:5px; padding:4px 8px; color:{C["text"]};
}}
QComboBox:focus {{ border:1px solid {C["accent"]}; }}
QComboBox::drop-down {{ border:none; width:18px; }}
QComboBox QAbstractItemView {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    selection-background-color:{C["overlay"]}; outline:none;
    color:{C["text"]};
}}

/* Buttons */
QPushButton {{
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-radius:7px; padding:6px 14px; color:{C["text"]};
}}
QPushButton:hover {{ background:{C["overlay"]}; border-color:{C["accent"]}; }}
QPushButton:pressed {{ background:{C["border"]}; }}
QPushButton:disabled {{ color:{C["dimtext"]}; border-color:{C["border"]}; }}

/* Tabs */
QTabWidget::pane {{ border:1px solid {C["border"]}; border-radius:6px; background:{C["surface"]}; }}
QTabBar::tab {{
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-bottom:none; border-radius:5px 5px 0 0;
    padding:7px 18px; color:{C["subtext"]}; margin-right:2px;
}}
QTabBar::tab:selected {{ background:{C["surface"]}; color:{C["accent"]}; }}
QTabBar::tab:hover:!selected {{ background:{C["overlay"]}; color:{C["text"]}; }}

/* GroupBox */
QGroupBox {{
    border:1px solid {C["border"]}; border-radius:7px;
    margin-top:12px; padding-top:6px; color:{C["accent"]}; font-weight:bold;
}}
QGroupBox::title {{ subcontrol-origin:margin; left:12px; padding:0 5px; }}

/* Splitter */
QSplitter::handle {{ background:{C["border"]}; }}
QSplitter::handle:vertical {{ height:2px; }}
QSplitter::handle:horizontal {{ width:2px; }}

/* Tabellen */
QTableWidget {{
    background:{C["surface"]}; gridline-color:{C["border"]};
    border:1px solid {C["border"]}; border-radius:6px;
}}
QHeaderView::section {{
    background:{C["surface2"]}; color:{C["accent"]};
    padding:5px; border:none; border-bottom:1px solid {C["border"]};
    font-weight:bold;
}}
QTableWidget::item:selected {{ background:{C["overlay"]}; color:{C["text"]}; }}

/* ToolTip */
QToolTip {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    color:{C["text"]}; padding:4px 8px; border-radius:4px;
}}
QStatusBar {{ background:{C["header"]}; color:{C["subtext"]}; border-top:1px solid {C["border"]}; font-size:9pt; }}

/* Checkboxen */
QCheckBox {{
    spacing: 8px;
    color: {C["text"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {C["border"]};
    border-radius: 3px;
    background: {C["surface2"]};
}}
QCheckBox::indicator:hover {{
    border-color: {C["accent"]};
    background: {C["overlay"]};
}}
QCheckBox::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}
QCheckBox::indicator:checked:disabled {{
    background: {C["dimtext"]};
    border-color: {C["dimtext"]};
}}
QCheckBox:disabled {{
    color: {C["dimtext"]};
}}

/* Radio-Buttons */
QRadioButton {{
    spacing: 8px;
    color: {C["text"]};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {C["border"]};
    border-radius: 8px;
    background: {C["surface2"]};
}}
QRadioButton::indicator:hover {{
    border-color: {C["accent"]};
    background: {C["overlay"]};
}}
QRadioButton::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}
QRadioButton::indicator:checked:disabled {{
    background: {C["dimtext"]};
    border-color: {C["dimtext"]};
}}
QRadioButton:disabled {{
    color: {C["dimtext"]};
}}
"""

# ══════════════════════════════════════════════════════════════════════════════
# JSON Hilfsfunktionen
# ══════════════════════════════════════════════════════════════════════════════

def lighten_color(hex_color, amount=24):
    """
    Hellt eine #rrggbb Farbe um 'amount' je Kanal auf (für Hover-Effekte).
    Qt-Stylesheets unterstützen kein CSS 'opacity' bei QPushButton —
    deshalb wird hier stattdessen eine echte hellere Farbe berechnet.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, c + amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color, amount=24):
    """
    Dunkelt eine #rrggbb Farbe um 'amount' je Kanal ab (Hover-Effekt im
    hellen Theme — dort soll Hover dunkler statt heller wirken).
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, c - amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def load_json(path, default=None):
    """JSON-Datei laden, gibt default zurück wenn nicht vorhanden / fehlerhaft."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    """Daten als JSON speichern (UTF-8, eingerückt). Legt Ordner bei Bedarf an."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Datums-/Zeit-Hilfsfunktionen (Arbeitszeiten & Reisekosten)
# ══════════════════════════════════════════════════════════════════════════════

def current_kw():
    """Aktuelle (KW, Jahr) zurückgeben."""
    iso = datetime.date.today().isocalendar()
    return iso[1], iso[0]


def week_dates(year, week):
    """7 date-Objekte für eine ISO-Kalenderwoche (Mo–So)."""
    jan4  = datetime.date(year, 1, 4)
    start = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
    start += datetime.timedelta(weeks=week - 1)
    return [start + datetime.timedelta(days=i) for i in range(7)]


def _easter_sunday(year):
    """Ostersonntag eines Jahres (Gaußsche Osterformel)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day   = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def _buss_und_bettag(year):
    """Buß- und Bettag: der Mittwoch vor dem 23. November (auch wenn der
    23. selbst ein Mittwoch ist — dann gilt der Mittwoch davor)."""
    d = datetime.date(year, 11, 23)
    diff = (d.weekday() - 2) % 7
    if diff == 0:
        diff = 7
    return d - datetime.timedelta(days=diff)


def get_feiertage(year, bundesland=None):
    """
    Gesetzliche Feiertage eines Jahres als {iso_date: name}.
    Bundesweite Feiertage sind immer enthalten, regionale nur wenn das
    übergebene Bundesland-Kürzel (z.B. "NW") passt — wir arbeiten in
    verschiedenen Bundesländern, daher hängt das von den Einstellungen ab.
    """
    ostern = _easter_sunday(year)
    days = {
        datetime.date(year, 1, 1):                       "Neujahr",
        datetime.date(year, 5, 1):                        "Tag der Arbeit",
        ostern - datetime.timedelta(days=2):              "Karfreitag",
        ostern + datetime.timedelta(days=1):              "Ostermontag",
        ostern + datetime.timedelta(days=39):             "Christi Himmelfahrt",
        ostern + datetime.timedelta(days=50):             "Pfingstmontag",
        datetime.date(year, 10, 3):                       "Tag der Deutschen Einheit",
        datetime.date(year, 12, 25):                      "1. Weihnachtstag",
        datetime.date(year, 12, 26):                      "2. Weihnachtstag",
    }
    bl = (bundesland or "").upper()
    if bl in ("BW", "BY", "ST"):
        days[datetime.date(year, 1, 6)] = "Heilige Drei Könige"
    if bl in ("BE", "MV"):
        days[datetime.date(year, 3, 8)] = "Internationaler Frauentag"
    if bl in ("BW", "BY", "HE", "NW", "RP", "SL"):
        days[ostern + datetime.timedelta(days=60)] = "Fronleichnam"
    if bl in ("BY", "SL"):
        days[datetime.date(year, 8, 15)] = "Mariä Himmelfahrt"
    if bl == "TH":
        days[datetime.date(year, 9, 20)] = "Weltkindertag"
    if bl in ("BB", "MV", "SN", "ST", "TH", "HB", "HH", "NI", "SH"):
        days[datetime.date(year, 10, 31)] = "Reformationstag"
    if bl in ("BW", "BY", "NW", "RP", "SL"):
        days[datetime.date(year, 11, 1)] = "Allerheiligen"
    if bl == "SN":
        days[_buss_und_bettag(year)] = "Buß- und Bettag"
    return {d.isoformat(): name for d, name in days.items()}


def calc_entry_hours(entry):
    """Netto-Stunden eines einzelnen Eintrags berechnen."""
    try:
        s = datetime.datetime.strptime(entry.get("start", ""), "%H:%M")
        e = datetime.datetime.strptime(entry.get("end", ""), "%H:%M")
        p = int(entry.get("pause", 0) or 0)
        return max(0.0, (e - s).seconds / 3600 - p / 60)
    except Exception:
        return 0.0


def calc_day_hours(day):
    """Tages-Netto-Stunden (Summe aller Einträge eines Tages)."""
    entries = [e for e in day.get("entries", []) if e.get("start") and e.get("end")]
    if entries:
        return sum(calc_entry_hours(e) for e in entries)
    return calc_entry_hours(day)


def entry_detail_text(entry, wohnort="Wohnort"):
    """Detail-Text für einen Eintrag (Route oder Allgemeinkosten-Code)."""
    dienst = entry.get("dienst", "Außendienst")
    if dienst in ("Innendienst", "Homeoffice", "Home Office"):
        code   = entry.get("allg_code", "")
        bez    = ALLGEMEIN_CODES.get(code, "")
        detail = (entry.get("allg_detail") or "").strip()
        base   = f"{code} – {bez}" if code else "Innendienst"
        return f"{base}: {detail}" if detail else base
    start = (entry.get("start_punkt") or wohnort).strip()
    loc   = (entry.get("standort") or "").strip()
    kunde = (entry.get("kunde_name") or "").strip()
    auftr = entry.get("auftr_nr", "").strip()
    end   = (entry.get("end_punkt") or wohnort).strip()
    lok   = loc or kunde
    stop  = f"{lok} ({auftr})" if lok and auftr else lok or auftr or ""
    parts = [p for p in [start, stop, end] if p]
    route = " → ".join(parts)
    prefix = f"{kunde}: " if kunde and kunde != lok else ""
    return f"{prefix}{route}"


def get_month_summary(year, month, override=None):
    """Monats-Stunden und Gleitzeitkonto berechnen."""
    total, gleit, SOLL = 0.0, 0.0, 8.0
    override = override or {}
    for dn in range(1, calendar.monthrange(year, month)[1] + 1):
        d  = datetime.date(year, month, dn)
        ds = d.isoformat()
        if ds in override:
            day = override[ds]
        else:
            iso  = d.isocalendar()
            data = load_json(os.path.join(KW_DIR, f"{iso[0]}-W{iso[1]:02d}.json"), {})
            day  = data.get(ds, {})
        if not day:
            continue
        status = day.get("status", "Frei" if d.weekday() >= 5 else "Arbeit")
        h = calc_day_hours(day)
        total += h
        if d.weekday() < 5:
            if status == "Arbeit":
                gleit += h - SOLL
            elif status in ("GLZ", "Kurzarbeit"):
                gleit -= SOLL
    return total, round(gleit, 2)


def load_month_data(year, month):
    """Alle Tagesdaten eines Monats aus den KW-JSON-Dateien laden."""
    result, seen = {}, set()
    for dn in range(1, calendar.monthrange(year, month)[1] + 1):
        d   = datetime.date(year, month, dn)
        iso = d.isocalendar()
        key = (iso[0], iso[1])
        if key not in seen:
            seen.add(key)
            raw = load_json(os.path.join(KW_DIR, f"{iso[0]}-W{iso[1]:02d}.json"), {})
            raw.pop("_extras", None)
            result.update(raw)
    return result


def save_day_to_kw(iso_date, day_data):
    """Einen einzelnen Tag in die passende KW-Datei speichern."""
    d    = datetime.date.fromisoformat(iso_date)
    iso  = d.isocalendar()
    path = os.path.join(KW_DIR, f"{iso[0]}-W{iso[1]:02d}.json")
    existing = load_json(path, {})
    existing[iso_date] = day_data
    save_json(path, existing)


def save_kw_data(kw, year, day_data, extras=None):
    """Gesamte KW-Daten speichern."""
    path = os.path.join(KW_DIR, f"{year}-W{kw:02d}.json")
    data = dict(day_data)
    if extras:
        data["_extras"] = extras
    save_json(path, data)


# ══════════════════════════════════════════════════════════════════════════════
# Kleine Widget-Ersteller
# ══════════════════════════════════════════════════════════════════════════════

def btn(text, cb=None, tooltip="", color=None, small=False):
    """Schnell-Ersteller für Buttons mit optionaler Farbe und Tooltip."""
    b = QPushButton(text)
    if cb:
        b.clicked.connect(cb)
    if tooltip:
        b.setToolTip(tooltip)
    if color:
        # Qt-Stylesheets kennen kein "opacity" für QPushButton — daher beim
        # Hover eine echte, abgedunkelte Farbe verwenden statt Transparenz
        # (im hellen Theme wirkt ein Abdunkeln des satten Buttons stimmiger
        # als ein Aufhellen, das schnell zu blass/unleserlich würde).
        hover_color = darken_color(color, 18)
        pressed_color = darken_color(color, 32)
        # Weißer Text statt der normalen (dunklen) Theme-Textfarbe — sonst
        # wäre dunkler Text auf satten Farben (Grün/Rot/Blau) kaum lesbar.
        b.setStyleSheet(f"""
            QPushButton {{ background:{color}; border:1px solid {color}; color:#ffffff; border-radius:7px; padding:6px 14px; }}
            QPushButton:hover {{ background:{hover_color}; border-color:{hover_color}; }}
            QPushButton:pressed {{ background:{pressed_color}; border-color:{pressed_color}; }}
        """)
    if small:
        b.setFixedHeight(26)
    return b


def lbl(text, color=None, bold=False, size=None):
    """Label-Schnell-Ersteller."""
    l = QLabel(text)
    style = ""
    if color: style += f"color:{color};"
    if bold:  style += "font-weight:bold;"
    if size:  style += f"font-size:{size}pt;"
    if style: l.setStyleSheet(style)
    return l


def sep_line():
    """Horizontale Trennlinie."""
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{C['border']}; background:{C['border']}; max-height:1px;")
    return f


def page_hero(icon_rel_path, title, desc, *extra_desc):
    """
    Einheitlicher Seitenkopf für alle Menüseiten — Icon links, Seitenname
    und Kurzbeschreibung rechts. Wird auf allen Inhaltsseiten verwendet,
    damit das Tool durchgehend denselben Header zeigt.

    Mehrere Beschreibungszeilen sind möglich: zusätzlich zu 'desc' können
    beliebig viele weitere Zeilen übergeben werden (jede wird als eigene
    umbrechende Zeile dargestellt). Beispiel:
        page_hero("icons/x.png", "Titel", "Zeile 1", "Zeile 2", "Zeile 3")
    """
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background:{C['surface']}; border-radius:12px; border:none; }}"
    )
    h = QHBoxLayout(frame)
    h.setContentsMargins(24, 20, 24, 20)
    h.setSpacing(20)

    icon_lbl = QLabel()
    icon_lbl.setFixedSize(48, 48)
    pix = QPixmap(os.path.join(MEIPASS_DIR, icon_rel_path))
    if not pix.isNull():
        icon_lbl.setPixmap(pix.scaled(
            48, 48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
    h.addWidget(icon_lbl)

    text_col = QVBoxLayout()
    text_col.setSpacing(4)
    text_col.addWidget(lbl(title, C["accent"], bold=True, size=16))
    for line in (desc, *extra_desc):
        if not line:
            continue
        desc_lbl = lbl(line, C["subtext"], size=10)
        desc_lbl.setWordWrap(True)
        text_col.addWidget(desc_lbl)
    h.addLayout(text_col, 1)
    return frame


def make_entry(placeholder="", width=None, pw=False):
    """QLineEdit-Ersteller."""
    e = QLineEdit()
    if placeholder: e.setPlaceholderText(placeholder)
    if width:       e.setFixedWidth(width)
    if pw:          e.setEchoMode(QLineEdit.EchoMode.Password)
    return e


def make_combo(items, width=None, current=None):
    """QComboBox-Ersteller."""
    c = QComboBox()
    c.addItems(items)
    if width:   c.setFixedWidth(width)
    if current: c.setCurrentText(current)
    return c
