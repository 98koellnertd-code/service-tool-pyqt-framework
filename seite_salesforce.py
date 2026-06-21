#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_salesforce.py
Menüpunkt "API Verbindungen" — Verbindungen zu externen Systemen.

Als Provider-Tabs aufgebaut, damit weitere APIs einfach ergänzt werden können:
  • Salesforce  — aktiv. Anmeldung bevor Arbeitszeiten/Reisekosten geladen werden.
      Methode 1: Session ID (Cookie 'sid')    — einfach, aber kurzlebig.
      Methode 2: OAuth Username/Password-Flow — dauerhaft, benötigt Connected App.
  • SAP         — vorbereitet (read-only Lagerbestände), noch nicht aktiv.
  • TIA Portal  — vorbereitet (Datenübergabe an TIA), noch nicht aktiv.

Klassen-/Signalnamen (SalesforcePage, sf_connected …) bleiben aus
Kompatibilitätsgründen erhalten — main.py verdrahtet die Salesforce-Verbindung
weiterhin darüber.
"""

import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QTabWidget,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from utils import C, SF_INSTANCE_URL, btn, lbl, make_entry, page_hero
from workers import SFSessionWorker, SFOAuthWorker


class SalesforcePage(QWidget):
    """Salesforce-Anmeldeseite mit den Verbindungsoptionen."""

    sf_connected       = pyqtSignal(str, str, str, str)  # token, inst_url, user_id, name
    sf_disconnected    = pyqtSignal()
    sap_status_changed = pyqtSignal(str, str)           # state ("ok"/"err"/"warn"), text
    tia_status_changed = pyqtSignal(str, str)           # state ("ok"/"err"/"warn"), text

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self._profile = profile
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        # Einheitlicher Seitenkopf (wie auf allen anderen Inhaltsseiten)
        root.addWidget(page_hero(
            "icons/netzwerk.png", "API Verbindungen",
            "Verbindungen zu externen Systemen verwalten",
            "Aktiv: Salesforce.  ·  In Vorbereitung: SAP, TIA Portal.",
        ))

        # Provider-Tabs: je externes System ein Tab. Salesforce ist aktiv,
        # SAP und TIA Portal sind als Platzhalter vorbereitet.
        provider_tabs = QTabWidget()
        root.addWidget(provider_tabs, 1)
        provider_tabs.addTab(self._build_salesforce_tab(), "  Salesforce  ")
        provider_tabs.addTab(self._build_sap_tab(), "  SAP  ")
        provider_tabs.addTab(self._build_tia_tab(), "  TIA Portal  ")

    # ── Tab: Salesforce (aktiv) ────────────────────────────────────────────────

    def _build_salesforce_tab(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Status-Anzeige
        status_frame = QFrame()
        status_frame.setStyleSheet(f"background:{C['surface']}; border-radius:8px;")
        sl = QHBoxLayout(status_frame)
        sl.setContentsMargins(14, 10, 14, 10)
        self._status_dot = lbl("●", C["red"], size=14)
        self._status_txt = lbl("Nicht verbunden", C["subtext"])
        sl.addWidget(self._status_dot)
        sl.addWidget(self._status_txt)
        sl.addStretch()
        disconnect_btn = btn("Trennen", self._disconnect, "Verbindung trennen")
        disconnect_btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{C['red']};}} QPushButton:hover{{color:{C['text']};}}")
        sl.addWidget(disconnect_btn)
        root.addWidget(status_frame)

        # Tab: Verbindungsmethoden
        tabs = QTabWidget()
        root.addWidget(tabs)

        # ── Tab 1: Session ID ──────────────────────────────────────────────────
        t1 = QWidget()
        tl1 = QVBoxLayout(t1)
        tl1.setContentsMargins(20, 16, 20, 16)
        tl1.setSpacing(12)

        info1 = QFrame()
        info1.setStyleSheet(f"background:{C['surface2']}; border-radius:7px;")
        il = QVBoxLayout(info1)
        il.setContentsMargins(14, 12, 14, 12)
        il.setSpacing(4)
        il.addWidget(lbl("📘  Anleitung — Session ID ermitteln", C["accent"], bold=True))
        for step in [
            "1.  VPN verbinden (GlobalProtect)",
            "2.  Unten auf »Salesforce öffnen« klicken und einloggen (SSO)",
            "3.  F12  →  Application  →  Cookies",
            "    →  koenig-bauer.lightning.force.com",
            "4.  Zeile  sid  anklicken  →  Wert kopieren",
            "5.  Wert unten einfügen  →  Verbinden klicken",
            "ℹ  Die Session läuft nach ~8h oder Browser-Neustart ab.",
        ]:
            il.addWidget(lbl(step, C["subtext"], size=9))
        tl1.addWidget(info1)

        sf_btn = btn("🌐  Salesforce in Browser öffnen",
                     lambda: webbrowser.open("https://koenig-bauer.lightning.force.com"),
                     "Öffnet Salesforce im Standardbrowser", color=C["accent"])
        tl1.addWidget(sf_btn)

        fl_sid = QFormLayout()
        fl_sid.setSpacing(8)
        self._sid_edit = make_entry("Session ID (sid-Cookie) einfügen…", pw=True)
        self._sid_edit.setText(self._profile.get("sf_session", ""))
        self._sid_edit.setMinimumWidth(420)
        show_cb = QPushButton("👁")
        show_cb.setFixedSize(30, 30)
        show_cb.setCheckable(True)
        show_cb.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{C['subtext']};}} QPushButton:checked{{color:{C['accent']};}}")
        show_cb.toggled.connect(
            lambda on: self._sid_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        sid_row = QHBoxLayout()
        sid_row.addWidget(self._sid_edit)
        sid_row.addWidget(show_cb)
        sid_row.addStretch()
        fl_sid.addRow("Session ID:", sid_row)
        tl1.addLayout(fl_sid)

        conn1 = btn("🔑  Verbinden  (Session ID)", self._connect_session,
                    "Salesforce-Verbindung mit Session ID herstellen", color=C["accent"])
        tl1.addWidget(conn1)
        tl1.addStretch()
        tabs.addTab(t1, "🍪  Session ID")

        # ── Tab 2: OAuth (Email / Passwort) ────────────────────────────────────
        t2 = QWidget()
        tl2 = QVBoxLayout(t2)
        tl2.setContentsMargins(20, 16, 20, 16)
        tl2.setSpacing(10)

        info2 = QFrame()
        info2.setStyleSheet(f"background:{C['surface2']}; border-radius:7px;")
        il2 = QVBoxLayout(info2)
        il2.setContentsMargins(14, 10, 14, 10)
        il2.addWidget(lbl("🔐  OAuth — Username / Password Flow", C["accent"], bold=True))
        il2.addWidget(lbl("Benötigt eine 'Connected App' in Salesforce Setup.",
                          C["subtext"], size=9))
        il2.addWidget(lbl("Setup → App Manager → New Connected App → OAuth aktivieren.",
                          C["subtext"], size=9))
        tl2.addWidget(info2)

        fl2 = QFormLayout()
        fl2.setSpacing(8)
        fl2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._oauth_email = make_entry("vorname.nachname@firma.de")
        self._oauth_pw    = make_entry("Passwort", pw=True)
        self._oauth_token = make_entry("Security Token (aus SF-Profil → Einstellungen)")
        self._oauth_cid   = make_entry("Consumer Key der Connected App")
        self._oauth_csec  = make_entry("Consumer Secret", pw=True)
        self._oauth_url   = make_entry("Login-URL", width=280)
        self._oauth_url.setText("https://login.salesforce.com")
        # Gespeicherte Werte aus den Einstellungen laden (dort zentral
        # gepflegt) — so muss man hier nichts erneut eintippen.
        for attr, key in [
            ("_oauth_email", "oauth_email"),
            ("_oauth_pw",    "oauth_password"),
            ("_oauth_token", "oauth_security_token"),
            ("_oauth_cid",   "oauth_client_id"),
            ("_oauth_csec",  "oauth_client_secret"),
            ("_oauth_url",   "oauth_login_url"),
        ]:
            getattr(self, attr).setText(self._profile.get(key, "") or getattr(self, attr).text())

        fl2.addRow("E-Mail:",          self._oauth_email)
        fl2.addRow("Passwort:",        self._oauth_pw)
        fl2.addRow("Security Token:",  self._oauth_token)
        fl2.addRow("Consumer Key:",    self._oauth_cid)
        fl2.addRow("Consumer Secret:", self._oauth_csec)
        fl2.addRow("Login-URL:",       self._oauth_url)
        tl2.addLayout(fl2)

        conn2 = btn("🔑  Verbinden  (OAuth)", self._connect_oauth,
                    "Salesforce-Verbindung mit Email/Passwort herstellen", color=C["accent"])
        tl2.addWidget(conn2)
        tl2.addStretch()
        tabs.addTab(t2, "🔐  OAuth / Passwort")

        root.addStretch()
        return page

    # ── Tab: SAP (Demo-Verbindung) ────────────────────────────────────────────

    def _build_sap_tab(self):
        self._sap_connected = False
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        # Status-Anzeige
        status_frame = QFrame()
        status_frame.setStyleSheet(f"background:{C['surface']}; border-radius:8px;")
        sl = QHBoxLayout(status_frame)
        sl.setContentsMargins(14, 10, 14, 10)
        self._sap_dot = lbl("●", C["red"], size=14)
        self._sap_status_txt = lbl("Nicht verbunden", C["subtext"])
        sl.addWidget(self._sap_dot)
        sl.addWidget(self._sap_status_txt)
        sl.addStretch()
        sap_disc = btn("Trennen", self._sap_disconnect, "Demo-Verbindung trennen")
        sap_disc.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{C['red']};}} "
            f"QPushButton:hover{{color:{C['text']};}}")
        sl.addWidget(sap_disc)
        v.addWidget(status_frame)

        # Info-Box
        info = QFrame()
        info.setStyleSheet(f"background:{C['surface2']}; border-radius:7px;")
        il = QVBoxLayout(info)
        il.setContentsMargins(14, 12, 14, 12)
        il.setSpacing(4)
        il.addWidget(lbl("🏭  SAP — Demo-Testverbindung", C["accent"], bold=True))
        desc = lbl(
            "Simuliert eine SAP-Verbindung (read-only). "
            "Geplant: Lagerbestände je Techniker auslesen (Menü »Mein Lager«) "
            "sowie perspektivisch weitere Stammdaten. "
            "Die Demo überträgt keine echten Daten.",
            C["subtext"], size=9)
        desc.setWordWrap(True)
        il.addWidget(desc)
        il.addWidget(lbl("⚠  Noch nicht produktiv — Demo-Modus.", C["yellow"], size=9))
        v.addWidget(info)

        # Eingabefelder
        form = QFormLayout()
        form.setSpacing(8)
        self._sap_host    = make_entry("z.B. sap-erp.firma.intern")
        self._sap_mandant = make_entry("z.B. 100")
        self._sap_user    = make_entry("Benutzername")
        self._sap_pw      = make_entry("Passwort", pw=True)
        form.addRow("SAP-System / Host:", self._sap_host)
        form.addRow("Mandant:",           self._sap_mandant)
        form.addRow("Benutzer:",          self._sap_user)
        form.addRow("Passwort:",          self._sap_pw)
        v.addLayout(form)

        self._sap_btn = btn(
            "🏭  Demo-Verbindung testen", self._sap_connect,
            "Simuliert eine SAP-Verbindung (Demo-Modus, keine echten Daten)",
            color=C["accent"])
        v.addWidget(self._sap_btn)
        v.addStretch()
        return page

    def _sap_connect(self):
        self._sap_set_status("warn", "Verbinde…")
        self._sap_btn.setEnabled(False)
        QTimer.singleShot(1200, self._sap_demo_success)

    def _sap_demo_success(self):
        host    = self._sap_host.text().strip() or "SAP Demo Server"
        mandant = self._sap_mandant.text().strip()
        label   = host + (f" · Mandant {mandant}" if mandant else "")
        self._sap_connected = True
        self._sap_set_status("ok", f"Demo aktiv  ·  {label}")
        self._sap_btn.setEnabled(True)
        self._sap_btn.setText("🏭  Demo neu verbinden")
        self.sap_status_changed.emit("ok", label)

    def _sap_disconnect(self):
        self._sap_connected = False
        self._sap_set_status("err", "Nicht verbunden")
        self._sap_btn.setEnabled(True)
        self._sap_btn.setText("🏭  Demo-Verbindung testen")
        self.sap_status_changed.emit("err", "")

    def _sap_set_status(self, state, text):
        colors = {"ok": C["green"], "warn": C["yellow"], "err": C["red"]}
        col = colors.get(state, C["red"])
        self._sap_dot.setStyleSheet(f"color:{col}; font-size:14pt;")
        self._sap_status_txt.setText(text)
        self._sap_status_txt.setStyleSheet(
            f"color:{col if state != 'err' else C['subtext']};")

    # ── Tab: TIA Portal (Demo-Verbindung) ─────────────────────────────────────

    def _build_tia_tab(self):
        self._tia_connected = False
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        # Status-Anzeige
        status_frame = QFrame()
        status_frame.setStyleSheet(f"background:{C['surface']}; border-radius:8px;")
        sl = QHBoxLayout(status_frame)
        sl.setContentsMargins(14, 10, 14, 10)
        self._tia_dot  = lbl("●", C["red"], size=14)
        self._tia_txt  = lbl("Nicht verbunden", C["subtext"])
        sl.addWidget(self._tia_dot)
        sl.addWidget(self._tia_txt)
        sl.addStretch()
        tia_disc = btn("Trennen", self._tia_disconnect, "Demo-Verbindung trennen")
        tia_disc.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{C['red']};}} "
            f"QPushButton:hover{{color:{C['text']};}}")
        sl.addWidget(tia_disc)
        v.addWidget(status_frame)

        # Info-Box
        info = QFrame()
        info.setStyleSheet(f"background:{C['surface2']}; border-radius:7px;")
        il = QVBoxLayout(info)
        il.setContentsMargins(14, 12, 14, 12)
        il.setSpacing(4)
        il.addWidget(lbl("🔌  TIA Portal — Demo-Testverbindung", C["accent"], bold=True))
        desc = lbl(
            "Simuliert eine Verbindung zum TIA Portal. "
            "Die Demo-Verbindung überträgt keine echten Daten — "
            "sie zeigt, wie die spätere Anbindung aussehen wird "
            "(Datenübergabe von Servicezeiten an TIA-Projekte).",
            C["subtext"], size=9)
        desc.setWordWrap(True)
        il.addWidget(desc)
        il.addWidget(lbl("⚠  Noch nicht produktiv — Demo-Modus.", C["yellow"], size=9))
        v.addWidget(info)

        # Eingabefelder (deaktiviert im Demo-Modus — trotzdem ausfüllbar zum Testen)
        form = QFormLayout()
        form.setSpacing(8)
        self._tia_host    = make_entry("z.B. 192.168.0.10 oder tia-server.intern")
        self._tia_projekt = make_entry("z.B. Projekt_Anlage_01")
        self._tia_user    = make_entry("Benutzername")
        self._tia_pw      = make_entry("Passwort", pw=True)
        form.addRow("Endpunkt / Host:", self._tia_host)
        form.addRow("Projekt:",         self._tia_projekt)
        form.addRow("Benutzer:",        self._tia_user)
        form.addRow("Passwort:",        self._tia_pw)
        v.addLayout(form)

        # Verbinden-Button
        self._tia_btn = btn(
            "🔌  Demo-Verbindung testen", self._tia_connect,
            "Simuliert eine TIA-Portal-Verbindung (Demo-Modus, keine echten Daten)",
            color=C["accent"])
        v.addWidget(self._tia_btn)
        v.addStretch()
        return page

    def _tia_connect(self):
        """Simuliert einen Verbindungsaufbau mit kurzem Delay (Demo)."""
        self._tia_set_status("warn", "Verbinde…")
        self._tia_btn.setEnabled(False)
        QTimer.singleShot(1400, self._tia_demo_success)

    def _tia_demo_success(self):
        host = self._tia_host.text().strip() or "TIA Demo Server"
        proj = self._tia_projekt.text().strip()
        label = f"{host}" + (f" · {proj}" if proj else "")
        self._tia_connected = True
        self._tia_set_status("ok", f"Demo aktiv  ·  {label}")
        self._tia_btn.setEnabled(True)
        self._tia_btn.setText("🔌  Demo neu verbinden")
        self.tia_status_changed.emit("ok", label)

    def _tia_disconnect(self):
        self._tia_connected = False
        self._tia_set_status("err", "Nicht verbunden")
        self._tia_btn.setEnabled(True)
        self._tia_btn.setText("🔌  Demo-Verbindung testen")
        self.tia_status_changed.emit("err", "")

    def _tia_set_status(self, state, text):
        colors = {"ok": C["green"], "warn": C["yellow"], "err": C["red"]}
        col = colors.get(state, C["red"])
        self._tia_dot.setStyleSheet(f"color:{col}; font-size:14pt;")
        self._tia_txt.setText(text)
        self._tia_txt.setStyleSheet(f"color:{col if state != 'err' else C['subtext']};")

    # ── Platzhalter-Tab für noch nicht aktive Verbindungen (SAP) ──────────────

    def _placeholder_tab(self, name, titel, beschreibung, felder):
        """Baut einen vorbereiteten, aber noch inaktiven Verbindungs-Tab —
        Infozeile, deaktivierte Eingabefelder und ein deaktivierter
        Verbinden-Button. So ist die Erweiterung sichtbar angelegt, ohne
        bereits Funktion vorzutäuschen."""
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        info = QFrame()
        info.setStyleSheet(f"background:{C['surface2']}; border-radius:7px;")
        il = QVBoxLayout(info)
        il.setContentsMargins(14, 12, 14, 12)
        il.setSpacing(4)
        il.addWidget(lbl(f"🔌  {titel}", C["accent"], bold=True))
        d = lbl(beschreibung, C["subtext"], size=9)
        d.setWordWrap(True)
        il.addWidget(d)
        il.addWidget(lbl("Diese Verbindung ist vorbereitet, aber noch nicht aktiv.",
                         C["yellow"], size=9))
        v.addWidget(info)

        # Vorbereitete (deaktivierte) Eingabefelder — zeigen, was später kommt.
        form = QFormLayout()
        form.setSpacing(8)
        for feld in felder:
            e = make_entry(f"{feld} …", pw=("passwort" in feld.lower()))
            e.setEnabled(False)
            form.addRow(f"{feld}:", e)
        v.addLayout(form)

        b = btn(f"🔌  Verbinden  ({name})", None, "Noch nicht verfügbar")
        b.setEnabled(False)
        v.addWidget(b)
        v.addStretch()
        return page

    def _set_status(self, state, text):
        colors = {"ok": C["green"], "warn": C["yellow"], "err": C["red"]}
        col = colors.get(state, C["red"])
        self._status_dot.setStyleSheet(f"color:{col}; font-size:14pt;")
        self._status_txt.setText(text)
        self._status_txt.setStyleSheet(f"color:{col};")

    def _connect_session(self):
        inst = SF_INSTANCE_URL
        sid  = self._sid_edit.text().strip()
        self._set_status("warn", "Verbinde…")
        self._worker = SFSessionWorker(sid, inst)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _connect_oauth(self):
        self._set_status("warn", "Verbinde…")
        self._worker = SFOAuthWorker(
            self._oauth_email.text().strip(),
            self._oauth_pw.text(),
            self._oauth_token.text().strip(),
            self._oauth_cid.text().strip(),
            self._oauth_csec.text(),
            self._oauth_url.text().strip() or "https://login.salesforce.com",
        )
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, token, inst_url, user_id, name):
        self._set_status("ok", f"Verbunden  ·  {name}")
        self.sf_connected.emit(token, inst_url, user_id, name)

    def _on_error(self, err):
        self._set_status("err", "Nicht verbunden")
        QMessageBox.critical(self, "Salesforce Fehler", err)

    def _disconnect(self):
        self._set_status("err", "Nicht verbunden")
        self.sf_disconnected.emit()

    def update_status(self, state, text):
        """Wird vom Hauptfenster beim Ping-Ergebnis aufgerufen."""
        self._set_status(state, text)
