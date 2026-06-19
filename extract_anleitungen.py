"""
Extrahiert Anleitungs-PDFs (Hotline, Laser, alphaJET, Organisatorisches …)
und erzeugt lokale JSON-Dateien zum Durchsuchen im Tool.

Pro System ein Ordner mit PDFs. Jede PDF wird zu EINEM Eintrag:
Titel + kompletter extrahierter Text (durchsuchbar) + Verweis auf die
mitkopierte Original-PDF, damit sie im Tool geöffnet werden kann.

Aufbau (analog extract_spare_parts.py / extract_fehlerdiagnose.py):
  Output:  res/anl/<key>.json        -> {"system": <label>, "entries": [...]}
           res/anl/systeme.json      -> {key: Anzeigename, ...}  (Registry)
           res/anl/files/<key>/*.pdf -> Kopien der Original-PDFs

Ein Eintrag:
  {
    "id":      1,
    "cat":     "",                         # Unterkategorie, im Tool pflegbar
    "title":   "In SAP anmelden",          # aus Dateiname
    "content": "In SAP anmelden\n1. ...",  # Volltext aller Seiten
    "file":    "files/hotline/In SAP anmelden.pdf",  # relativ zu res/anl
    "pages":   1
  }
"""

import re
import os
import json
import shutil
import unicodedata

import pdfplumber

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "res", "anl")
FILES_DIR = os.path.join(OUT_DIR, "files")

# Basisordner, in dem die System-Unterordner mit den PDFs liegen.
PDF_BASE = r"C:\Users\marvi\Desktop\123"

# System-Ordner -> (Schlüssel/Dateiname, Anzeigename).
# Fehlende Ordner werden übersprungen (Meldung), neue einfach hier ergänzen.
SYSTEM_SOURCES = [
    ("hotline dokus",          "hotline",  "Hotline (SAP / Salesforce)"),
    ("laser dokus",            "laser",    "Laser"),
    ("alphajet dokus",         "alphajet", "alphaJET"),
    ("organisatorisches dokus","orga",     "Organisatorisches"),
]

# Führende Datums-/Versionstokens im Dateinamen, die nicht in den Titel sollen,
# z.B. "20230517 Serviceliste Tinte" -> "Serviceliste Tinte".
LEADING_DATE_RE = re.compile(r"^\d{6,8}[ _-]+")


def clean_text(text):
    """Whitespace normalisieren, aber Zeilenumbrüche (Schrittfolgen!) behalten.
    Symbol-/Wingdings-Glyphen aus dem Private-Use-Bereich werden entfernt."""
    if not text:
        return ""
    # Private-Use-Glyphen (z.B.  Häkchen aus Symbol-Fonts) raus
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Co")
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    # Mehrfache Leerzeilen auf eine reduzieren
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def title_from_filename(fname):
    """Anzeige-Titel aus dem Dateinamen ableiten."""
    stem = os.path.splitext(fname)[0]
    stem = LEADING_DATE_RE.sub("", stem)
    stem = stem.replace("_", " ").strip()
    return stem


def extract_pdf(pdf_path):
    """Volltext + Seitenzahl einer PDF zurückgeben."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return clean_text("\n".join(parts)), n_pages


def process_system(folder_name, key, label):
    """Alle PDFs eines System-Ordners zu Einträgen verarbeiten."""
    src_dir = os.path.join(PDF_BASE, folder_name)
    if not os.path.isdir(src_dir):
        print(f"  ÜBERSPRUNGEN (Ordner fehlt): {src_dir}")
        return None

    pdf_files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".pdf"))
    if not pdf_files:
        print(f"  Keine PDFs in {src_dir}")
        return []

    dst_dir = os.path.join(FILES_DIR, key)
    os.makedirs(dst_dir, exist_ok=True)

    entries = []
    for fname in pdf_files:
        src = os.path.join(src_dir, fname)
        try:
            content, pages = extract_pdf(src)
        except Exception as exc:                       # defekte/gesperrte PDF
            print(f"    FEHLER bei {fname}: {exc}")
            continue

        # Original-PDF ins res-Verzeichnis kopieren (selbst-enthaltenes Tool)
        shutil.copy2(src, os.path.join(dst_dir, fname))
        rel_path = os.path.join("files", key, fname).replace("\\", "/")

        entries.append({
            "id":      len(entries) + 1,
            "cat":     "",
            "title":   title_from_filename(fname),
            "content": content,
            "file":    rel_path,
            "pages":   pages,
        })
        print(f"    + {fname}  ({pages} S., {len(content)} Zeichen)")

    return entries


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)

    registry = {}

    for folder_name, key, label in SYSTEM_SOURCES:
        print(f"\n=== {label} [{key}] ===")
        entries = process_system(folder_name, key, label)
        if entries is None:        # Ordner fehlt -> System nicht anlegen
            continue

        registry[key] = label
        out_path = os.path.join(OUT_DIR, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"system": label, "entries": entries}, f,
                      ensure_ascii=False, indent=2)
        print(f"  {len(entries)} Anleitungen -> {out_path}")

    # Registry (key -> Anzeigename) schreiben/aktualisieren
    reg_path = os.path.join(OUT_DIR, "systeme.json")
    bestehend = {}
    if os.path.isfile(reg_path):
        try:
            with open(reg_path, encoding="utf-8") as f:
                bestehend = json.load(f)
        except Exception:
            bestehend = {}
    bestehend.update(registry)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(bestehend, f, ensure_ascii=False, indent=2)
    print(f"\nRegistry -> {reg_path}: {bestehend}")


if __name__ == "__main__":
    main()
