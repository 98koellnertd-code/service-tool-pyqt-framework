#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
Einstiegspunkt des Service Tools.

Enthält die Sidebar (Navigation) und das Hauptfenster. Seiten werden
NICHT alle beim Start erzeugt, sondern erst beim ersten Aufruf
("lazy loading") — das hält den Start schnell und spart Speicher,
wenn z.B. nie auf "Fehlerdiagnose" geklickt wird.

Neue Menüpunkte hinzufügen:
  1. Neues seite_xyz.py-Modul mit einer QWidget-Klasse anlegen.
  2. Einen Eintrag in NAV (Icon + Name) und in _PAGE_FACTORIES
     (wie die Seite erzeugt wird) ergänzen.
  Das war's — Sidebar und Lazy-Loading übernehmen den Rest automatisch.
"""

import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from utils import (
    C, STYLE, APP_NAME, APP_VERSION, PROFILE_FILE, ICON_FILE, ICON_PNG,
    MEIPASS_DIR, MODULES,
    load_json, save_json, lbl, cleanup_orphaned_meipass,
)
from workers import SFPingWorker

from seite_start import StartPage
from seite_salesforce import SalesforcePage
from seite_dashboard import DashboardSeite
from seite_arbeitszeiten import ArbeitsZeitenPage
from seite_reisekosten import ReisekostenPage
from seite_ersatzteile import ErsatzteileSeite
from seite_bestellungen import BestellungenSeite
from seite_fehlerdiagnose import FehlerdiagnoseSeite
from seite_anleitungen import AnleitungenSeite
from seite_datenbank import DatenbankSeite
from seite_lager import LagerSeite
from seite_assistent import AssistentSeite
from seite_info import InfoPage
from seite_einstellungen import EinstellungenPage
from updater import UpdateManager


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar — linke Navigationsleiste
# ══════════════════════════════════════════════════════════════════════════════

class Sidebar(QFrame):
    """
    Linke Navigationsleiste mit den Menüpunkten und SF-Statusanzeige.
    Emittiert 'page_changed' mit dem Seitenindex bei Klick.

    NAV wird zentral hier gepflegt — für ein neues Menü reicht ein
    weiterer Eintrag (Index, Icon, Anzeigename).
    """
    page_changed = pyqtSignal(int)

    # Start (Home) vorne, danach das zentrale Modul-Register (utils.MODULES) —
    # so bleiben Reihenfolge, Icons und Namen synchron zu Startseite & Info.
    NAV = [(0, "icons/start.png", "Start")] + [
        (m["nav"], m["icon"], m["name"]) for m in MODULES
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QFrame#sidebar {{
                background:{C["header"]};
                border-right:1px solid {C["border"]};
            }}
        """)
        self._btns = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Markenkopf (Kopfzeile oben links) ───────────────────────────────
        # Freistehendes App-Icon (ohne Rahmen/Plättchen) + zweifarbige
        # Wortmarke und eine dezente Versions-"Pille". Ein feiner Verlauf und
        # der Akzentstreifen unten heben den Kopf optisch von der Navigation ab.
        logo_frame = QFrame()
        logo_frame.setObjectName("brandHeader")
        logo_frame.setFixedHeight(76)
        logo_frame.setStyleSheet(f"""
            QFrame#brandHeader {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {C['surface']}, stop:1 {C['surface2']});
                border-bottom:2px solid {C['accent']};
            }}
            QFrame#brandHeader QLabel {{ background:transparent; border:none; }}
        """)
        logo_lay = QHBoxLayout(logo_frame)
        logo_lay.setContentsMargins(15, 0, 12, 0)
        logo_lay.setSpacing(11)

        icon_badge = QLabel()
        icon_badge.setObjectName("brandIcon")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Bewusst ohne Hintergrund-Plättchen und ohne Rahmen — das Icon steht frei.
        icon_badge.setStyleSheet("QLabel#brandIcon { background:transparent; border:none; }")
        # Hochauflösende PNG verwenden (nicht die .ico) — sonst verpixelt das
        # heruntergerechnete Header-Icon. Mit erhöhtem Device-Pixel-Ratio
        # gerendert, damit es auf HiDPI-Displays gestochen scharf bleibt.
        pix = QPixmap(ICON_PNG)
        if pix.isNull():
            pix = QPixmap(ICON_FILE)
        if not pix.isNull():
            dpr = icon_badge.devicePixelRatioF() or 1.0
            scaled = pix.scaled(
                round(36 * dpr), round(36 * dpr),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(dpr)
            icon_badge.setPixmap(scaled)
        logo_lay.addWidget(icon_badge)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)
        text_col.addStretch()

        title_lbl = QLabel(
            f"<span style='color:{C['accent']}; font-weight:800; "
            f"letter-spacing:1px;'>Service</span>"
            f"<span style='color:{C['subtext']}; font-weight:600;'> Tool</span>"
        )
        title_lbl.setStyleSheet("font-size:15px;")
        text_col.addWidget(title_lbl)

        ver_row = QHBoxLayout()
        ver_row.setContentsMargins(0, 0, 0, 0)
        ver_row.setSpacing(0)
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet(f"""
            QLabel {{
                background:{C['overlay']}; color:{C['subtext']};
                border-radius:7px; padding:1px 9px;
                font-size:8pt; font-weight:700; letter-spacing:0.5px;
            }}
        """)
        ver_row.addWidget(ver_lbl)
        ver_row.addStretch()
        text_col.addLayout(ver_row)

        text_col.addStretch()
        logo_lay.addLayout(text_col, 1)
        lay.addWidget(logo_frame)

        # Navigations-Buttons
        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"background:{C['header']};")
        nav_lay = QVBoxLayout(nav_frame)
        nav_lay.setContentsMargins(8, 12, 8, 0)
        nav_lay.setSpacing(2)

        for idx, icon, name in self.NAV:
            b = QPushButton(f"  {name}")
            b.setIcon(QIcon(os.path.join(MEIPASS_DIR, icon)))
            b.setIconSize(QSize(20, 20))
            b.setCheckable(True)
            b.setFixedHeight(40)
            b.setStyleSheet(self._nav_style(False))
            b.clicked.connect(lambda checked, i=idx: self.select(i))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            nav_lay.addWidget(b)
            self._btns[idx] = b

        nav_lay.addStretch()
        lay.addWidget(nav_frame, 1)

        # Verbindungsstatus-Anzeige unten (Salesforce + TIA Portal)
        sf_frame = QFrame()
        sf_frame.setStyleSheet(f"background:{C['surface']}; border-top:1px solid {C['border']};")
        sf_lay = QVBoxLayout(sf_frame)
        sf_lay.setContentsMargins(12, 10, 12, 10)
        sf_lay.setSpacing(6)

        # — Salesforce —
        sf_top = QHBoxLayout()
        sf_top.setSpacing(6)
        self._sf_dot = lbl("●", C["red"], size=12)
        sf_top.addWidget(self._sf_dot)
        sf_top.addWidget(lbl("Salesforce", C["subtext"], size=9))
        sf_top.addStretch()
        sf_lay.addLayout(sf_top)
        self._sf_name = lbl("Nicht verbunden", C["dimtext"], size=8)
        self._sf_name.setWordWrap(True)
        sf_lay.addWidget(self._sf_name)

        # Trennlinie
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{C['border']}; background:{C['border']}; max-height:1px;")
        sf_lay.addWidget(div)

        # — SAP —
        sap_top = QHBoxLayout()
        sap_top.setSpacing(6)
        self._sap_dot = lbl("●", C["red"], size=12)
        sap_top.addWidget(self._sap_dot)
        sap_top.addWidget(lbl("SAP", C["subtext"], size=9))
        sap_top.addStretch()
        sf_lay.addLayout(sap_top)
        self._sap_name = lbl("Nicht verbunden", C["dimtext"], size=8)
        self._sap_name.setWordWrap(True)
        sf_lay.addWidget(self._sap_name)

        # Trennlinie
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet(f"color:{C['border']}; background:{C['border']}; max-height:1px;")
        sf_lay.addWidget(div2)

        # — TIA Portal —
        tia_top = QHBoxLayout()
        tia_top.setSpacing(6)
        self._tia_dot = lbl("●", C["red"], size=12)
        tia_top.addWidget(self._tia_dot)
        tia_top.addWidget(lbl("TIA Portal", C["subtext"], size=9))
        tia_top.addStretch()
        sf_lay.addLayout(tia_top)
        self._tia_name = lbl("Nicht verbunden", C["dimtext"], size=8)
        self._tia_name.setWordWrap(True)
        sf_lay.addWidget(self._tia_name)

        lay.addWidget(sf_frame)
        # Hinweis: Das Vorauswählen der Start-Seite passiert NICHT hier,
        # sondern erst nachdem MainWindow page_changed verbunden hat
        # (sonst würde das allererste Signal ins Leere laufen).

    def _nav_style(self, active):
        if active:
            return f"""
                QPushButton {{
                    background:{C['surface2']}; border:none; border-left:3px solid {C['accent']};
                    border-radius:7px; color:{C['accent']}; text-align:left;
                    padding-left:12px; font-weight:bold;
                    icon-size:20px; spacing:10px;
                }}
            """
        return f"""
            QPushButton {{
                background:transparent; border:none; border-left:3px solid transparent;
                border-radius:7px; color:{C['subtext']}; text-align:left; padding-left:12px;
                icon-size:20px; spacing:10px;
            }}
            QPushButton:hover {{ background:{C['overlay']}; color:{C['text']}; }}
        """

    def select(self, idx):
        """Menüpunkt aktivieren (auch von außen, z.B. zum Vorauswählen, nutzbar)."""
        for i, b in self._btns.items():
            b.setStyleSheet(self._nav_style(i == idx))
            b.setChecked(i == idx)
        self.page_changed.emit(idx)

    def set_sf_status(self, connected, name=""):
        """SF-Verbindungsstatus in der Sidebar aktualisieren."""
        self._set_conn_status(self._sf_dot, self._sf_name, connected, name)

    def set_sap_status(self, connected, name=""):
        """SAP-Status in der Sidebar aktualisieren."""
        self._set_conn_status(self._sap_dot, self._sap_name, connected, name)

    def set_tia_status(self, connected, name=""):
        """TIA-Portal-Status in der Sidebar aktualisieren."""
        self._set_conn_status(self._tia_dot, self._tia_name, connected, name)

    def _set_conn_status(self, dot, name_lbl, state, name=""):
        if state == "ok":
            dot.setStyleSheet(f"color:{C['green']}; font-size:12pt;")
            name_lbl.setText(name or "Verbunden")
            name_lbl.setStyleSheet(f"color:{C['green']}; font-size:8pt;")
        elif state == "warn":
            dot.setStyleSheet(f"color:{C['yellow']}; font-size:12pt;")
            name_lbl.setText(name or "Verbindungsproblem")
            name_lbl.setStyleSheet(f"color:{C['yellow']}; font-size:8pt;")
        else:
            dot.setStyleSheet(f"color:{C['red']}; font-size:12pt;")
            name_lbl.setText(name or "Nicht verbunden")
            name_lbl.setStyleSheet(f"color:{C['dimtext']}; font-size:8pt;")


# ══════════════════════════════════════════════════════════════════════════════
# Hauptfenster mit Lazy-Loading der Seiten
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Hauptfenster des Service Tools.
    Enthält Sidebar (links) und Inhaltsbereich (rechts, QStackedWidget).
    Verwaltet den Salesforce-Verbindungszustand zentral.

    Seiten werden erst beim ersten Klick auf den jeweiligen Menüpunkt
    instanziiert (Lazy Loading) und danach im Cache (_pages) behalten.
    """

    def __init__(self):
        super().__init__()
        self._sf_token    = None
        self._sf_inst_url = None
        self._sf_user_id  = None
        self._sf_name     = ""
        self._profile     = load_json(PROFILE_FILE, {})

        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}  —  Arbeitszeiten, Reisekosten & mehr")
        self.setMinimumSize(1100, 700)
        self.resize(1320, 800)

        if os.path.isfile(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))

        # Fabrikfunktionen je Seitenindex — werden erst beim ersten Aufruf
        # ausgeführt. So bauen wir z.B. die Ersatzteile-Seite (lädt JSON!)
        # nicht schon beim Programmstart, falls sie nie geöffnet wird.
        self._page_factories = {
            0: lambda: StartPage(self._profile),
            1: lambda: SalesforcePage(self._profile),
            2: lambda: ArbeitsZeitenPage(self._get_sf, self._get_wohnort, self._profile),
            3: lambda: ReisekostenPage(self._get_sf, self._get_wohnort, self._profile),
            4: lambda: ErsatzteileSeite(),
            5: lambda: BestellungenSeite(self._profile),
            6: lambda: FehlerdiagnoseSeite(),
            9: lambda: AnleitungenSeite(),
            10: lambda: DatenbankSeite(),
            11: lambda: LagerSeite(self._profile),
            12: lambda: DashboardSeite(self._profile),
            13: lambda: AssistentSeite(),
            7: lambda: InfoPage(),
            8: lambda: EinstellungenPage(self._profile),
        }
        self._pages = {}          # idx -> bereits erzeugtes Widget
        self._page_salesforce = None
        self._page_settings = None

        self._build_ui()
        self._start_ping_timer()

        # Update-Check (Punkt 2: über version.json + SHA-256 wie das alte
        # G-PRINT-Tool — siehe updater.py). Läuft kurz nach dem Start im
        # Hintergrund, falls in den Einstellungen aktiviert (Standard: ja).
        self._update_mgr = UpdateManager(self)
        if self._profile.get("auto_update", True):
            QTimer.singleShot(2000, self._auto_update_check)

    def _auto_update_check(self):
        url = (self._profile.get("update_url") or "").strip()
        if url:
            self._update_mgr.check(url, manual=False)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._switch_page)
        main_lay.addWidget(self._sidebar)

        # Inhaltsbereich (Seiten werden erst bei Bedarf hinzugefügt)
        self._stack = QStackedWidget()
        main_lay.addWidget(self._stack, 1)

        # Statusleiste
        self._statusbar = self.statusBar()
        self._statusbar.showMessage("Bereit")

        # Jetzt, wo page_changed verbunden ist, die Start-Seite auswählen.
        self._sidebar.select(0)

    def _ensure_page(self, idx):
        """Seite bei Bedarf erzeugen (lazy) und in den Stack einhängen."""
        if idx in self._pages:
            return self._pages[idx]
        page = self._page_factories[idx]()
        self._pages[idx] = page
        self._stack.addWidget(page)

        # Generische Verdrahtung: jede Seite mit status_msg-Signal wird
        # automatisch an die Statusleiste angebunden.
        if hasattr(page, "status_msg"):
            page.status_msg.connect(self._set_status)

        # Start-Seite: Klick auf eine Modul-Kachel wechselt zum jeweiligen Menü.
        if idx == 0:
            page.navigate_to.connect(self._sidebar.select)

        # Salesforce-Seite braucht Sonderbehandlung (SF-Verbindung + TIA-Status).
        if idx == 1:
            self._page_salesforce = page
            page.sf_connected.connect(self._on_sf_connected)
            page.sf_disconnected.connect(self._on_sf_disconnected)
            page.sap_status_changed.connect(
                lambda st, nm: self._sidebar.set_sap_status(st, nm))
            page.tia_status_changed.connect(
                lambda st, nm: self._sidebar.set_tia_status(st, nm))

        # Ersatzteile-Seite: Doppelklick auf einen Eintrag soll das Teil
        # automatisch der aktuellen Bestellung hinzufügen (Bestellung-Seite wird
        # dafür bei Bedarf ebenfalls lazy erzeugt).
        if idx == 4:
            page.teil_hinzufuegen.connect(self._teil_zur_bestellung)

        # Einstellungen-Seite wird für get_wohnort() gebraucht.
        if idx == 8:
            self._page_settings = page

        return page

    def _teil_zur_bestellung(self, teil):
        """Ein in 'Ersatzteile' per Doppelklick gewähltes Teil an die
        Bestellungen-Seite weiterreichen (Seite 4 bei Bedarf lazy erzeugen)."""
        bestellseite = self._ensure_page(5)
        bestellseite.teil_hinzufuegen(teil)
        self._set_status(f"➕  {teil.get('name') or teil.get('order_no','')} zur Bestellung hinzugefügt")

    def _switch_page(self, idx):
        page = self._ensure_page(idx)
        if idx == 7 and hasattr(page, "refresh"):
            page.refresh()
        self._stack.setCurrentWidget(page)

    def _get_sf(self):
        """SF-Verbindungsdaten zurückgeben — None wenn nicht verbunden."""
        if self._sf_token:
            return self._sf_token, self._sf_inst_url, self._sf_user_id
        return None

    def _get_wohnort(self):
        """Wohnort aus den Einstellungen lesen (Seite bei Bedarf lazy erzeugen)."""
        if self._page_settings is None:
            self._page_settings = self._page_factories[8]()
            # Nicht sichtbar einhängen, falls noch nicht im Stack:
            if 8 not in self._pages:
                self._pages[8] = self._page_settings
                self._stack.addWidget(self._page_settings)
        return self._page_settings.get_wohnort()

    def _on_sf_connected(self, token, inst_url, user_id, name):
        self._sf_token    = token
        self._sf_inst_url = inst_url
        self._sf_user_id  = user_id
        self._sf_name     = name
        self._sidebar.set_sf_status("ok", name)
        self._set_status(f"✅  Salesforce verbunden  —  {name}")
        # Session ID im Profil speichern
        self._profile["sf_session"] = token
        save_json(PROFILE_FILE, self._profile)

    def _on_sf_disconnected(self):
        self._sf_token = None
        self._sidebar.set_sf_status("err")
        self._set_status("Salesforce getrennt")

    def _set_status(self, msg):
        self._statusbar.showMessage(msg, 8000)

    # ── SF-Ping alle 10 Sekunden ───────────────────────────────────────────────

    def _start_ping_timer(self):
        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self._ping_sf)
        self._ping_timer.start(10_000)

    def _ping_sf(self):
        if not self._sf_token:
            return
        worker = SFPingWorker(self._sf_token, self._sf_inst_url)
        worker.alive.connect(  lambda: self._sidebar.set_sf_status("ok",  self._sf_name))
        worker.warning.connect(lambda: (
            self._sidebar.set_sf_status("warn"),
            self._page_salesforce.update_status("warn", "Verbindungsproblem") if self._page_salesforce else None))
        worker.expired.connect(lambda: (
            self.__setattr__("_sf_token", None),
            self._sidebar.set_sf_status("err", "Session abgelaufen"),
            self._page_salesforce.update_status("err", "Session abgelaufen") if self._page_salesforce else None,
            self._set_status("⚠  Salesforce-Session abgelaufen — bitte neu verbinden.")))
        worker.start()


# ══════════════════════════════════════════════════════════════════════════════
# Einstiegspunkt
# ══════════════════════════════════════════════════════════════════════════════

def main():
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    cleanup_orphaned_meipass()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(STYLE)
    if os.path.isfile(ICON_FILE):
        app.setWindowIcon(QIcon(ICON_FILE))

    from splash import show_splash
    splash = show_splash()

    splash.advance(1)
    win = MainWindow()
    splash.advance(3)
    app.processEvents()

    win.showMaximized()
    splash.close()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
