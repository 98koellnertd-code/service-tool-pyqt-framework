#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
updater.py
Selbst-Update über GitHub (version.json + SHA-256-Prüfung) — Pendant zum
Update-Mechanismus des alten G-PRINT-Tools, hier auf PyQt6/QThread umgestellt.

Ablauf:
  1. UpdateCheckWorker lädt die in den Einstellungen hinterlegte Update-URL
     (zeigt auf eine version.json) und vergleicht die Versionsnummer.
  2. Ist eine neuere Version verfügbar, fragt UpdateManager nach Bestätigung
     und startet UpdateDownloadWorker, der die neue EXE herunterlädt, ihre
     SHA-256-Prüfsumme verifiziert und sie per Batch-Skript einspielt
     (Ersetzen während die alte EXE noch läuft ist unter Windows nicht
     möglich, daher der kurze Umweg über cmd.exe).
  3. Das Ergebnis der letzten Prüfung (Version, Changelog, Download-URL)
     wird in UPDATE_CACHE_FILE zwischengespeichert, damit die Info-Seite es
     auch ohne erneute Netzwerkabfrage anzeigen kann.
"""

import os
import re
import sys
import json
import hashlib
import datetime
import tempfile
import subprocess
import urllib.request

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal

from utils import APP_VERSION, UPDATE_CACHE_FILE, save_json


def version_newer(remote, current):
    """Vergleicht zwei Versionsnummern ('1.2.3', evtl. mit führendem 'v')."""
    def parts(v):
        try:
            cleaned = re.sub(r"[^0-9.]", "", str(v))
            return [int(x) for x in cleaned.split(".") if x != ""]
        except Exception:
            return [0]
    return parts(remote) > parts(current)


def verify_sha256(file_path, expected):
    """Prüft die SHA-256-Summe einer Datei gegen den erwarteten Wert."""
    if not expected:
        return True
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower().strip()


# ══════════════════════════════════════════════════════════════════════════════
# Hintergrund-Threads
# ══════════════════════════════════════════════════════════════════════════════

class UpdateCheckWorker(QThread):
    """Lädt version.json von der Update-URL und prüft, ob sie neuer ist."""
    found = pyqtSignal(dict)   # version.json-Inhalt, neuer als APP_VERSION
    none  = pyqtSignal(dict)   # version.json-Inhalt, aber keine neuere Version
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            if not self.url:
                raise ValueError("Keine Update-URL konfiguriert.")
            with urllib.request.urlopen(self.url, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            remote_ver = str(data.get("version", "0.0.0"))
            if version_newer(remote_ver, APP_VERSION):
                self.found.emit(data)
            else:
                self.none.emit(data)
        except Exception as e:
            self.error.emit(str(e)[:400])


class UpdateDownloadWorker(QThread):
    """Lädt die neue EXE herunter, prüft die SHA-256-Summe und spielt sie ein."""
    success = pyqtSignal()
    error   = pyqtSignal(str)

    def __init__(self, download_url, sha256=""):
        super().__init__()
        self.download_url = download_url
        self.sha256 = sha256

    def run(self):
        try:
            if not self.download_url.startswith("https://"):
                raise ValueError(
                    "Download-URL ist nicht sicher (https:// fehlt).\nUpdate abgebrochen.")
            tmp = os.path.join(tempfile.gettempdir(), "TimingTool_new.exe")
            urllib.request.urlretrieve(self.download_url, tmp)
            if self.sha256 and not verify_sha256(tmp, self.sha256):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                raise ValueError(
                    "SHA-256-Prüfsumme stimmt nicht überein.\n"
                    "Update-Datei könnte manipuliert sein.\nUpdate abgebrochen.")
            self._apply(tmp)
            self.success.emit()
        except Exception as e:
            self.error.emit(str(e)[:400])

    @staticmethod
    def _clean_env():
        # PyInstaller-Bootloader-Variablen raus: verhindern, dass die neue
        # .exe sich für einen Kindprozess hält ("Failed to load Python DLL").
        return {k: v for k, v in os.environ.items()
                if not (k.startswith("_MEI") or k.startswith("_PYI"))}

    def _apply(self, new_exe_path):
        if not getattr(sys, "frozen", False):
            raise ValueError(
                "Im Python-Entwicklermodus kein automatisches Ersetzen.\n"
                f"Neue Exe liegt unter:\n{new_exe_path}\n\n"
                f"Manuell kopieren nach: {os.path.abspath(sys.argv[0])}")
        current_exe = sys.executable
        pid      = os.getpid()
        bat_path = os.path.join(tempfile.gettempdir(), f"_ttupdate_{pid}.bat")
        bat_content = (
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'copy /y "{new_exe_path}" "{current_exe}"\n'
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            env=self._clean_env(),
            cwd=tempfile.gettempdir(),
            creationflags=subprocess.CREATE_NO_WINDOW)


# ══════════════════════════════════════════════════════════════════════════════
# UpdateManager — bündelt Prüfung, Rückfrage-Dialog und Download für ein
# beliebiges Eltern-Widget. Hält Worker-Referenzen als Attribute, damit sie
# während der Laufzeit nicht vom Garbage Collector eingesammelt werden.
# ══════════════════════════════════════════════════════════════════════════════

class UpdateManager:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self._check_worker = None
        self._dl_worker     = None
        self._prog_dlg      = None

    def check(self, url, manual=True):
        """Startet die Update-Prüfung. manual=True zeigt auch dann eine
        Rückmeldung, wenn keine neuere Version gefunden wurde (Button-Klick);
        bei manual=False (Auto-Check beim Start) bleibt es bei Stille."""
        url = (url or "").strip()
        if not url:
            if manual:
                QMessageBox.information(
                    self.parent, "Update",
                    "Keine Update-URL konfiguriert.\n"
                    "Bitte unter Einstellungen → Update eintragen.")
            return
        self._check_worker = UpdateCheckWorker(url)
        self._check_worker.found.connect(lambda d: self._on_found(d, manual))
        self._check_worker.none.connect(lambda d: self._on_none(d, manual))
        self._check_worker.error.connect(lambda e: self._on_error(e, manual))
        self._check_worker.start()

    @staticmethod
    def _cache(data):
        save_json(UPDATE_CACHE_FILE, {
            "version":      data.get("version", ""),
            "notes":        data.get("notes", ""),
            "download_url": data.get("download_url", ""),
            "checked_at":   datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        })

    def _on_found(self, data, manual):
        self._cache(data)
        remote_ver = data.get("version", "?")
        notes      = data.get("notes", "")
        dl_url     = data.get("download_url", "")
        sha256     = data.get("sha256", "")
        msg = f"Neue Version verfügbar: {remote_ver}\n(Aktuell: {APP_VERSION})"
        if notes:
            msg += f"\n\nÄnderungen:\n{notes}"
        msg += "\n\nJetzt aktualisieren?"
        antwort = QMessageBox.question(
            self.parent, "Update verfügbar", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if antwort != QMessageBox.StandardButton.Yes:
            return
        if not dl_url:
            QMessageBox.critical(self.parent, "Fehler", "Keine Download-URL angegeben.")
            return
        self._start_download(remote_ver, dl_url, sha256)

    def _on_none(self, data, manual):
        self._cache(data)
        if manual:
            QMessageBox.information(
                self.parent, "Kein Update", f"Du hast die aktuelle Version ({APP_VERSION}).")

    def _on_error(self, err, manual):
        if manual:
            QMessageBox.critical(
                self.parent, "Update-Fehler", f"Update-Prüfung fehlgeschlagen:\n{err}")

    def _start_download(self, remote_ver, dl_url, sha256):
        self._prog_dlg = QProgressDialog(
            f"Lade Version {remote_ver} herunter…", "", 0, 0, self.parent)
        self._prog_dlg.setWindowTitle("Update")
        self._prog_dlg.setCancelButton(None)
        self._prog_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self._prog_dlg.show()

        self._dl_worker = UpdateDownloadWorker(dl_url, sha256)
        self._dl_worker.success.connect(self._on_download_success)
        self._dl_worker.error.connect(self._on_download_error)
        self._dl_worker.start()

    def _on_download_success(self):
        if self._prog_dlg:
            self._prog_dlg.close()
        # Update-Skript läuft bereits im Hintergrund (kopiert die neue EXE,
        # startet sie neu) — die aktuelle Instanz muss sich jetzt nur noch
        # regulär beenden, damit die Datei nicht mehr gesperrt ist.
        QApplication.instance().quit()

    def _on_download_error(self, err):
        if self._prog_dlg:
            self._prog_dlg.close()
        QMessageBox.critical(self.parent, "Update-Fehler", err)
