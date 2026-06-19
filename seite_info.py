#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_info.py
Menüpunkt "Info" — zeigt Versions- und Speicherort-Informationen sowie den
zuletzt über die Update-URL gelesenen Changelog an (siehe updater.py).
"""

import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from utils import (
    C, BASE_DIR, APP_NAME, APP_VERSION, SF_INSTANCE_URL, UPDATE_CACHE_FILE,
    load_json, lbl, page_hero,
)


class InfoPage(QWidget):
    """Statische Info-Seite mit Tool-Version, Datenpfaden und Update-Stand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(14)
        lay.addWidget(page_hero(
            "icons/info.png", "Info",
            "Versionsinformationen, Datenpfade und letzter Update-Stand auf einen Blick",
        ))
        for t, c in [
            (f"{APP_NAME}  v{APP_VERSION}", C["text"]),
            ("Arbeitszeiten, Reisekosten, Ersatzteile & Fehlerdiagnose", C["subtext"]),
            ("", None),
            ("📁  Datenspeicherung", C["accent"]),
            (f"  {os.path.join(BASE_DIR,'res','kw_data')}", C["dimtext"]),
            (f"  {os.path.join(BASE_DIR,'res','et')}", C["dimtext"]),
            (f"  {os.path.join(BASE_DIR,'res','fd')}", C["dimtext"]),
            (f"  {os.path.join(BASE_DIR,'res','orders')}", C["dimtext"]),
            ("", None),
            ("🌐  Salesforce-Instanz", C["accent"]),
            (f"  {SF_INSTANCE_URL}", C["dimtext"]),
            ("", None),
            ("📋  Datenformat", C["accent"]),
            ("  JSON — lokal, kompatibel mit den bestehenden Ersatzteil-/Fehlerdiagnose-Skripten", C["dimtext"]),
            ("", None),
            ("⚙  Framework", C["accent"]),
            ("  PyQt6  ·  Python 3.10+", C["dimtext"]),
        ]:
            if t:
                lay.addWidget(lbl(t, c or C["text"]))

        lay.addWidget(lbl("", None))
        lay.addWidget(lbl("🔄  Update", C["accent"]))
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

    def refresh(self):
        """Liest den Update-Zwischenspeicher (UPDATE_CACHE_FILE) neu ein —
        wird beim Öffnen der Seite aufgerufen, damit nach einer Prüfung in
        den Einstellungen hier sofort der aktuelle Stand angezeigt wird."""
        cache = load_json(UPDATE_CACHE_FILE, {})
        if not cache:
            self._update_version_lbl.setText(f"  Aktuell installiert: v{APP_VERSION}  ·  noch nicht geprüft")
            self._update_url_lbl.setText("  Download-URL: —")
            self._update_notes_lbl.setText("  Letzte Änderungen: noch keine Update-Prüfung durchgeführt.")
            return
        checked_at = cache.get("checked_at", "")
        suffix = f"  ·  geprüft am {checked_at}" if checked_at else ""
        self._update_version_lbl.setText(
            f"  Aktuell installiert: v{APP_VERSION}  ·  zuletzt gefunden: v{cache.get('version','—')}{suffix}")
        self._update_url_lbl.setText(
            f"  Download-URL (aus version.json, nicht änderbar): {cache.get('download_url') or '—'}")
        self._update_notes_lbl.setText(
            f"  Letzte Änderungen:\n{cache.get('notes') or '—'}")
