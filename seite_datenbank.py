#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seite_datenbank.py
Menüpunkt "Datenbank" — Serviceberichte, Ersatzteile/Mittel und Kunden aus der
Railway-PostgreSQL-Datenbank.

Portiert aus dem alten G-PRINT-Tool (service_db.py, tkinter) nach PyQt6.
Unterschied zum Original: KEIN Techniker-Namensfilter — es werden immer alle
Daten geladen.

Neu: Serviceberichte können per Mail geschickt werden. Über "E-Mails abrufen"
(oder automatisch im Hintergrund) werden ungelesene Mails mit PDF-Anhang
ausgelesen, mit Claude analysiert und automatisch in die DB eingefügt
(siehe mail_ingest.py + analyse_bericht.py).

DB-URL und Anthropic-API-Key kommen aus der .env (wie früher), die
Mail-Zugangsdaten aus res/service_config.json.
"""

import os
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter, QTextEdit, QFileDialog, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QDialogButtonBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor

from utils import C, RES_DIR, btn, lbl, page_hero, load_json, save_json
from mail_ingest import PROVIDER_PRESETS, fetch_and_process

SERVICE_CFG = os.path.join(RES_DIR, "service_config.json")

_MONTH_DE = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
             "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# Diagramm-/Techniker-Farben aus den vorhandenen Theme-Farben
_CHART_COLORS = [C["accent"], C["green"], C["mauve"], C["yellow"], C["red"],
                 "#7ab8e8", "#88c888", "#c888b8"]
_CHART_ITEMS = 8


def _last_12_months():
    today = date.today()
    y, m = today.year, today.month
    result = []
    for _ in range(12):
        result.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    result.reverse()
    return result


def _get_conn():
    if not PSYCOPG2_OK:
        raise RuntimeError("psycopg2 nicht installiert.\n"
                           "Bitte ausführen: pip install psycopg2-binary")
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL nicht gesetzt.\n"
                           "Bitte .env-Datei mit DATABASE_URL anlegen.")
    return psycopg2.connect(url)


# ══════════════════════════════════════════════════════════════════════════════
# Hintergrund-Threads
# ══════════════════════════════════════════════════════════════════════════════

class DBLoadWorker(QThread):
    """Lädt alle Übersichtsdaten (ohne Techniker-Filter)."""
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, month):
        super().__init__()
        self.month = month   # None = Alle, sonst (year, month)

    def _mittel(self, cur, month):
        base = """
            SELECT e.datum, e.bezeichnung, e.teilenummer, e.menge, t.name
            FROM   ersatzteile e
            LEFT JOIN techniker t ON t.id = e.techniker_id
        """
        if month is None:
            cur.execute(base + " ORDER BY e.datum DESC NULLS LAST")
        else:
            y, m = month
            cur.execute(
                base +
                " WHERE EXTRACT(YEAR  FROM e.datum)::int = %s"
                "   AND EXTRACT(MONTH FROM e.datum)::int = %s"
                " ORDER BY e.datum DESC NULLS LAST",
                (y, m))
        return cur.fetchall()

    def run(self):
        try:
            conn = _get_conn()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM serviceberichte")
            n_berichte = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(arbeitszeit), 0) FROM serviceberichte")
            total_h = float(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM ersatzteile "
                        "WHERE datum >= CURRENT_DATE - INTERVAL '30 days'")
            n_teile = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT kunde_id) FROM serviceberichte")
            n_kunden = cur.fetchone()[0]

            mittel_rows = self._mittel(cur, self.month)

            cur.execute("""
                SELECT s.datum, s.geraet_nr, k.name, s.arbeitszeit,
                       s.zusatztext, t.name, s.id
                FROM   serviceberichte s
                LEFT JOIN kunden    k ON k.id = s.kunde_id
                LEFT JOIN techniker t ON t.id = s.techniker_id
                ORDER  BY s.datum DESC NULLS LAST
            """)
            berichte_rows = cur.fetchall()

            cur.execute("""
                SELECT k.name, COUNT(s.id), COALESCE(SUM(s.arbeitszeit), 0), k.id
                FROM   kunden k
                JOIN   serviceberichte s ON s.kunde_id = k.id
                GROUP  BY k.id, k.name
                ORDER  BY SUM(s.arbeitszeit) DESC NULLS LAST
            """)
            kunden_rows = cur.fetchall()

            cur.close()
            conn.close()
            self.done.emit({
                "n_berichte": n_berichte, "total_h": total_h,
                "n_teile": n_teile, "n_kunden": n_kunden,
                "mittel": mittel_rows, "berichte": berichte_rows,
                "kunden": kunden_rows,
            })
        except Exception as e:
            self.error.emit(str(e))


class KundenDetailWorker(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, kunde_id):
        super().__init__()
        self.kunde_id = kunde_id

    def run(self):
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT s.datum, s.geraet_nr, s.arbeitszeit, t.name
                FROM   serviceberichte s
                LEFT JOIN techniker t ON t.id = s.techniker_id
                WHERE  s.kunde_id = %s
                ORDER  BY s.datum DESC NULLS LAST
            """, (self.kunde_id,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self.done.emit(list(rows))
        except Exception as e:
            self.error.emit(str(e))


class PdfWorker(QThread):
    progress = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pfad):
        super().__init__()
        self.pfad = pfad

    def run(self):
        try:
            from analyse_bericht import analysiere_pdf, speichere_in_db
            self.progress.emit(f"🤖  Claude liest »{os.path.basename(self.pfad)}« …")
            daten = analysiere_pdf(self.pfad)
            self.progress.emit("💾  Speichere in Datenbank …")
            speichere_in_db(daten)
            kunde = (daten.get("kunde") or {}).get("name", "")
            terminnr = daten.get("terminnummer", "")
            self.done.emit(f"✓  {terminnr} – {kunde}")
        except Exception as e:
            self.error.emit(str(e))


class DeleteBerichtWorker(QThread):
    """Löscht einen Servicebericht (per id) aus der Datenbank."""
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, bericht_id):
        super().__init__()
        self.bericht_id = bericht_id

    def run(self):
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM serviceberichte WHERE id = %s", (self.bericht_id,))
            conn.commit()
            cur.close()
            conn.close()
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


class MailWorker(QThread):
    progress = pyqtSignal(str)
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            results = fetch_and_process(self.config, on_progress=self.progress.emit)
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# Balkendiagramm (meistverbrauchte Teile)
# ══════════════════════════════════════════════════════════════════════════════

class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self.setMinimumHeight(190)

    def set_rows(self, rows):
        self._rows = rows or []
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        totals = {}
        for _datum, bezeichnung, _teilenr, menge, _tech in self._rows:
            if not bezeichnung:
                continue
            totals[bezeichnung] = totals.get(bezeichnung, 0) + (menge or 0)
        top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:_CHART_ITEMS]
        if not top or w < 60:
            p.setPen(QColor(C["dimtext"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Keine Daten für den gewählten Zeitraum")
            return

        max_val = max(v for _, v in top) or 1
        n = len(top)
        pad_l, pad_top = 14, 8
        label_w, pad_r = 220, 52
        bar_area = max(10, w - pad_l - label_w - pad_r)
        row_h = (h - 2 * pad_top) / n
        bar_h = max(8, min(24, row_h - 6))

        p.setPen(QColor(C["subtext"]))
        for i, (name, val) in enumerate(top):
            y_center = pad_top + i * row_h + row_h / 2
            display = name if len(name) <= 30 else name[:28] + "…"
            p.setPen(QColor(C["subtext"]))
            p.drawText(pad_l, int(y_center + 4), display)

            bar_w = int(bar_area * val / max_val)
            x0 = pad_l + label_w
            color = QColor(_CHART_COLORS[i % len(_CHART_COLORS)])
            if bar_w > 0:
                p.fillRect(x0, int(y_center - bar_h / 2), bar_w, int(bar_h), color)
            p.setPen(QColor(C["text"]))
            p.drawText(x0 + bar_w + 6, int(y_center + 4), str(int(val)))
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Mail-Einstellungen-Dialog
# ══════════════════════════════════════════════════════════════════════════════

class MailSettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mail-Einstellungen")
        self.setMinimumWidth(440)
        self._cfg = dict(cfg or {})

        form = QFormLayout(self)

        self._provider = QComboBox()
        self._provider.addItems(list(PROVIDER_PRESETS.keys()))
        self._provider.currentTextChanged.connect(self._apply_preset)
        form.addRow("Anbieter:", self._provider)

        self._host = QLineEdit(self._cfg.get("host", ""))
        form.addRow("IMAP-Server:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(int(self._cfg.get("port", 993)))
        form.addRow("Port:", self._port)

        self._user = QLineEdit(self._cfg.get("user", ""))
        self._user.setPlaceholderText("z.B. name@gmail.com")
        form.addRow("Benutzer / E-Mail:", self._user)

        self._pw = QLineEdit(self._cfg.get("password", ""))
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("Passwort bzw. App-Passwort")
        form.addRow("Passwort:", self._pw)

        self._folder = QLineEdit(self._cfg.get("folder", "INBOX"))
        form.addRow("Ordner:", self._folder)

        self._ssl = QCheckBox("SSL/TLS verwenden")
        self._ssl.setChecked(bool(self._cfg.get("ssl", True)))
        form.addRow("", self._ssl)

        self._auto = QCheckBox("Automatisch im Hintergrund abrufen")
        self._auto.setChecked(bool(self._cfg.get("auto_poll", True)))
        form.addRow("", self._auto)

        self._interval = QSpinBox()
        self._interval.setRange(1, 120)
        self._interval.setValue(int(self._cfg.get("interval_min", 5)))
        self._interval.setSuffix(" Min")
        form.addRow("Abruf-Intervall:", self._interval)

        hint = lbl("Gmail/Outlook benötigen meist ein App-Passwort (bei aktivierter "
                   "2-Faktor-Anmeldung).", C["dimtext"], size=8)
        hint.setWordWrap(True)
        form.addRow("", hint)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _apply_preset(self, name):
        preset = PROVIDER_PRESETS.get(name)
        if preset and preset[0]:
            self._host.setText(preset[0])
            self._port.setValue(preset[1])

    def values(self):
        return {
            "host": self._host.text().strip(),
            "port": self._port.value(),
            "user": self._user.text().strip(),
            "password": self._pw.text(),
            "folder": self._folder.text().strip() or "INBOX",
            "ssl": self._ssl.isChecked(),
            "auto_poll": self._auto.isChecked(),
            "interval_min": self._interval.value(),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Hauptseite
# ══════════════════════════════════════════════════════════════════════════════

class DatenbankSeite(QWidget):
    """Service-Datenbank: Serviceberichte, Mittel und Kunden — ohne Namensfilter."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_month = None
        self._month_btns = {}
        self._berichte_data = []
        self._kunden_data = []
        self._sel_bericht_id = None
        self._busy = False
        self._mail_cfg = load_json(SERVICE_CFG, {}).get("mail", {})
        self._build()
        self._setup_poll_timer()
        # Erstabruf der Daten kurz nach dem Öffnen
        QTimer.singleShot(150, self._reload)

    # ── Aufbau ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addWidget(page_hero(
            "icons/datenbank.png", "Datenbank",
            "Serviceberichte, können aktuell per Mail gesendet werden, werden im Backend bearbeitet und zur Datenbank hinzugefügt. Manuelle Analyse über 'PDF analyiseren'",
            "Was ist möglich? Wäre eine Art KSU, nur ohne manuelle Eingabe. Beim senden des Servicebrichts, könnte dieser automatisch im Backend extrahiert werden. ",
            "Neuronales Netzwerk möglich. 'Wann geht welches Teil kaputt.' 'Ich habe dieses Symtom, was wurde letztes mal gemacht?' ",
        ))

        # ── Aktionsleiste ──────────────────────────────────────────────────────
        bar = QFrame()
        bar.setStyleSheet(f"background:{C['surface']}; border-radius:10px;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 8, 14, 8)
        bl.setSpacing(10)

        self._status_lbl = lbl("● nicht geladen", C["red"], size=9)
        bl.addWidget(self._status_lbl)
        bl.addStretch()

        self._load_btn = btn("⟳  Aus Datenbank laden", self._reload, color=C["accent"])
        bl.addWidget(self._load_btn)
        self._pdf_btn = btn("📄  PDF analysieren", self._upload_pdf, color=C["green"])
        bl.addWidget(self._pdf_btn)
        self._mail_btn = btn("📧  E-Mails abrufen", self._fetch_mail,
                             tooltip="Ungelesene Mails mit Servicebericht-PDF abrufen "
                                     "und automatisch in die DB einfügen")
        bl.addWidget(self._mail_btn)
        self._mail_cfg_btn = btn("⚙", self._edit_mail_settings,
                                 tooltip="Mail-Einstellungen")
        self._mail_cfg_btn.setFixedWidth(38)
        bl.addWidget(self._mail_cfg_btn)
        root.addWidget(bar)

        # ── Fortschrittszeile ──────────────────────────────────────────────────
        self._progress_frame = QFrame()
        self._progress_frame.setStyleSheet(f"background:{C['surface2']}; border-radius:8px;")
        pl = QHBoxLayout(self._progress_frame)
        pl.setContentsMargins(14, 6, 14, 6)
        self._progress_lbl = lbl("", C["yellow"], size=9)
        pl.addWidget(self._progress_lbl)
        pl.addStretch()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)   # unbestimmt
        self._progress_bar.setFixedWidth(180)
        pl.addWidget(self._progress_bar)
        self._progress_frame.setVisible(False)
        root.addWidget(self._progress_frame)

        # ── Stats-Karten ───────────────────────────────────────────────────────
        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._stat_berichte = self._stat_card(stats, "Serviceberichte")
        self._stat_stunden = self._stat_card(stats, "Stunden gesamt")
        self._stat_teile = self._stat_card(stats, "Teile (30 Tage)")
        self._stat_kunden = self._stat_card(stats, "Kunden")
        root.addLayout(stats)

        # ── Tabs ───────────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_mittel_tab(), "🔧  Letzte Mittel")
        self._tabs.addTab(self._build_berichte_tab(), "📋  Serviceberichte")
        self._tabs.addTab(self._build_kunden_tab(), "🏢  Kunden")
        root.addWidget(self._tabs, 1)

    def _stat_card(self, parent_layout, label):
        f = QFrame()
        f.setStyleSheet(f"background:{C['surface2']}; border-radius:10px;")
        v = QVBoxLayout(f)
        v.setContentsMargins(20, 10, 20, 10)
        v.setSpacing(2)
        v.addWidget(lbl(label, C["subtext"], size=8))
        value = lbl("—", C["accent"], bold=True, size=20)
        v.addWidget(value)
        parent_layout.addWidget(f)
        return value

    # ── Tab: Letzte Mittel ────────────────────────────────────────────────────

    def _build_mittel_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        # Monats-Kacheln
        tiles = QHBoxLayout()
        tiles.setSpacing(4)
        tiles.addWidget(lbl("Zeitraum:", C["subtext"], size=8))
        self._add_month_tile(tiles, "Alle", None)
        for y, m in _last_12_months():
            self._add_month_tile(tiles, f"{_MONTH_DE[m]} {str(y)[2:]}", (y, m))
        tiles.addStretch()
        v.addLayout(tiles)

        # Diagramm
        v.addWidget(lbl("Meistverbrauchte Teile", C["subtext"], bold=True, size=8))
        self._chart = BarChart()
        v.addWidget(self._chart)

        # Tabelle
        self._tv_mittel = QTableWidget(0, 5)
        self._tv_mittel.setHorizontalHeaderLabels(
            ["Datum", "Artikel / Bezeichnung", "Teilenummer", "Menge", "Techniker"])
        self._prep_table(self._tv_mittel, stretch_col=1)
        self._tv_mittel.setColumnWidth(0, 90)
        self._tv_mittel.setColumnWidth(2, 120)
        self._tv_mittel.setColumnWidth(3, 60)
        self._tv_mittel.setColumnWidth(4, 160)
        v.addWidget(self._tv_mittel, 1)
        return w

    def _add_month_tile(self, layout, text, key):
        b = QPushButton(text)
        b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setChecked(key is None)
        b.clicked.connect(lambda _=False, k=key: self._select_month(k))
        b.setStyleSheet(self._tile_style(key is None))
        layout.addWidget(b)
        self._month_btns[key] = b

    def _tile_style(self, active):
        if active:
            return (f"QPushButton {{ background:{C['accent']}; color:#fff; border:none;"
                    f" border-radius:6px; padding:4px 10px; font-weight:bold; }}")
        return (f"QPushButton {{ background:{C['surface2']}; color:{C['subtext']};"
                f" border:none; border-radius:6px; padding:4px 10px; }}"
                f"QPushButton:hover {{ background:{C['overlay']}; color:{C['text']}; }}")

    def _select_month(self, key):
        self._selected_month = key
        for k, b in self._month_btns.items():
            b.setChecked(k == key)
            b.setStyleSheet(self._tile_style(k == key))
        self._reload()

    # ── Tab: Serviceberichte ──────────────────────────────────────────────────

    def _build_berichte_tab(self):
        split = QSplitter(Qt.Orientation.Horizontal)

        self._tv_berichte = QTableWidget(0, 5)
        self._tv_berichte.setHorizontalHeaderLabels(
            ["Datum", "Terminnr.", "Kunde", "Std.", "Techniker"])
        self._prep_table(self._tv_berichte, stretch_col=2)
        self._tv_berichte.setColumnWidth(0, 90)
        self._tv_berichte.setColumnWidth(1, 110)
        self._tv_berichte.setColumnWidth(3, 55)
        self._tv_berichte.setColumnWidth(4, 150)
        self._tv_berichte.itemSelectionChanged.connect(self._on_bericht_select)
        split.addWidget(self._tv_berichte)

        right = QFrame()
        right.setStyleSheet(f"background:{C['surface']};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(14, 12, 14, 12)
        rv.addWidget(lbl("Bericht-Details", C["accent"], bold=True, size=10))
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setStyleSheet(
            f"QTextEdit {{ background:{C['surface2']}; color:{C['text']};"
            f" border:none; border-radius:8px; padding:8px; }}")
        rv.addWidget(self._detail, 1)

        self._del_btn = btn("🗑  Bericht löschen", self._delete_bericht, color=C["red"],
                            tooltip="Den ausgewählten Servicebericht aus der Datenbank löschen")
        self._del_btn.setEnabled(False)
        rv.addWidget(self._del_btn)
        split.addWidget(right)

        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        return split

    # ── Tab: Kunden ───────────────────────────────────────────────────────────

    def _build_kunden_tab(self):
        split = QSplitter(Qt.Orientation.Horizontal)

        self._tv_kunden = QTableWidget(0, 3)
        self._tv_kunden.setHorizontalHeaderLabels(["Kunde", "Berichte", "Stunden"])
        self._prep_table(self._tv_kunden, stretch_col=0)
        self._tv_kunden.setColumnWidth(1, 80)
        self._tv_kunden.setColumnWidth(2, 90)
        self._tv_kunden.itemSelectionChanged.connect(self._on_kunden_select)
        split.addWidget(self._tv_kunden)

        right = QFrame()
        right.setStyleSheet(f"background:{C['surface']};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(14, 12, 14, 12)
        self._kunden_hdr = lbl("Bitte Kunde auswählen", C["accent"], bold=True, size=10)
        rv.addWidget(self._kunden_hdr)
        self._tv_kunden_detail = QTableWidget(0, 4)
        self._tv_kunden_detail.setHorizontalHeaderLabels(
            ["Datum", "Terminnr.", "Std.", "Techniker"])
        self._prep_table(self._tv_kunden_detail, stretch_col=3)
        self._tv_kunden_detail.setColumnWidth(0, 90)
        self._tv_kunden_detail.setColumnWidth(1, 110)
        self._tv_kunden_detail.setColumnWidth(2, 55)
        rv.addWidget(self._tv_kunden_detail, 1)
        split.addWidget(right)

        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        return split

    def _prep_table(self, tv, stretch_col):
        tv.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tv.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tv.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tv.verticalHeader().setVisible(False)
        tv.horizontalHeader().setSectionResizeMode(
            stretch_col, QHeaderView.ResizeMode.Stretch)

    # ── Daten laden ───────────────────────────────────────────────────────────

    def _reload(self):
        if getattr(self, "_db_worker", None) and self._db_worker.isRunning():
            return
        self._status_lbl.setText("● Verbinde …")
        self._status_lbl.setStyleSheet(f"color:{C['yellow']};")
        self._load_btn.setEnabled(False)
        self._db_worker = DBLoadWorker(self._selected_month)
        self._db_worker.done.connect(self._on_data)
        self._db_worker.error.connect(self._on_db_error)
        self._db_worker.start()

    def _on_db_error(self, err):
        self._status_lbl.setText(f"● Fehler: {err[:50]}…")
        self._status_lbl.setStyleSheet(f"color:{C['red']};")
        self._load_btn.setEnabled(True)
        QMessageBox.critical(self, "Datenbankfehler", err)

    def _on_data(self, d):
        self._load_btn.setEnabled(True)
        self._status_lbl.setText(f"● {d['n_berichte']} Berichte geladen")
        self._status_lbl.setStyleSheet(f"color:{C['green']};")
        self._stat_berichte.setText(str(d["n_berichte"]))
        self._stat_stunden.setText(f"{d['total_h']:.1f}")
        self._stat_teile.setText(str(d["n_teile"]))
        self._stat_kunden.setText(str(d["n_kunden"]))
        self._fill_mittel(d["mittel"])
        self._fill_berichte(d["berichte"])
        self._fill_kunden(d["kunden"])

    def _fill_mittel(self, rows):
        self._chart.set_rows(rows)
        tv = self._tv_mittel
        tv.setRowCount(len(rows))
        for r, (datum, bez, teilenr, menge, tech) in enumerate(rows):
            datum_str = datum.strftime("%d.%m.%Y") if datum else "—"
            for c, val in enumerate([datum_str, bez or "—", teilenr or "—",
                                     str(menge or 0), tech or "—"]):
                tv.setItem(r, c, QTableWidgetItem(val))

    def _fill_berichte(self, rows):
        self._berichte_data = list(rows)
        self._sel_bericht_id = None
        self._del_btn.setEnabled(False)
        self._detail.clear()
        tv = self._tv_berichte
        tv.setRowCount(len(rows))
        for r, row in enumerate(rows):
            datum, terminnr, kunde, stunden, _zusatz, tech, _bid = row
            datum_str = datum.strftime("%d.%m.%Y") if datum else "—"
            for c, val in enumerate([datum_str, terminnr or "—", kunde or "—",
                                     f"{float(stunden or 0):.1f}", tech or "—"]):
                tv.setItem(r, c, QTableWidgetItem(val))

    def _fill_kunden(self, rows):
        self._kunden_data = list(rows)
        tv = self._tv_kunden
        tv.setRowCount(len(rows))
        for r, (name, n_b, total_h, _kid) in enumerate(rows):
            for c, val in enumerate([name or "—", str(int(n_b)),
                                     f"{float(total_h):.1f}"]):
                tv.setItem(r, c, QTableWidgetItem(val))

    def _on_bericht_select(self):
        row = self._tv_berichte.currentRow()
        if row < 0 or row >= len(self._berichte_data):
            self._sel_bericht_id = None
            self._del_btn.setEnabled(False)
            return
        datum, terminnr, kunde, stunden, zusatz, tech, bid = self._berichte_data[row]
        self._sel_bericht_id = bid
        self._del_btn.setEnabled(not self._busy)
        datum_str = datum.strftime("%d.%m.%Y") if datum else "—"
        html = (
            f"<table cellspacing='6'>"
            f"<tr><td><b style='color:{C['accent']}'>Terminnummer</b></td><td>{terminnr or '—'}</td></tr>"
            f"<tr><td><b style='color:{C['accent']}'>Datum</b></td><td>{datum_str}</td></tr>"
            f"<tr><td><b style='color:{C['accent']}'>Kunde</b></td><td>{kunde or '—'}</td></tr>"
            f"<tr><td><b style='color:{C['accent']}'>Techniker</b></td><td>{tech or '—'}</td></tr>"
            f"<tr><td><b style='color:{C['accent']}'>Arbeitszeit</b></td><td>{float(stunden or 0):.1f} h</td></tr>"
            f"</table>"
        )
        if zusatz:
            html += (f"<p style='color:{C['subtext']}; margin-top:10px'>Zusatztext / Lösung</p>"
                     f"<p>{str(zusatz).replace(chr(10), '<br>')}</p>")
        self._detail.setHtml(html)

    def _delete_bericht(self):
        if getattr(self, "_del_worker", None) and self._del_worker.isRunning():
            return
        row = self._tv_berichte.currentRow()
        if self._sel_bericht_id is None or row < 0 or row >= len(self._berichte_data):
            return
        _datum, terminnr, kunde, _stunden, _zusatz, _tech, _bid = self._berichte_data[row]
        antwort = QMessageBox.question(
            self, "Bericht löschen",
            f"Soll dieser Servicebericht wirklich gelöscht werden?\n\n"
            f"Terminnummer: {terminnr or '—'}\n"
            f"Kunde: {kunde or '—'}\n\n"
            f"Das Löschen kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if antwort != QMessageBox.StandardButton.Yes:
            return
        self._show_progress("🗑  Lösche Servicebericht …")
        self._set_busy(True)
        self._del_btn.setEnabled(False)
        self._del_worker = DeleteBerichtWorker(self._sel_bericht_id)
        self._del_worker.done.connect(self._on_delete_done)
        self._del_worker.error.connect(self._on_delete_error)
        self._del_worker.start()

    def _on_delete_done(self):
        self._set_busy(False)
        self._set_progress_text("✓  Bericht gelöscht", C["green"])
        self.status_msg.emit("🗑  Servicebericht gelöscht")
        QTimer.singleShot(2500, self._hide_progress)
        self._reload()

    def _on_delete_error(self, err):
        self._set_busy(False)
        self._set_progress_text(f"✗  {err[:80]}", C["red"])
        QTimer.singleShot(5000, self._hide_progress)
        QMessageBox.critical(self, "Löschfehler", err)

    def _on_kunden_select(self):
        row = self._tv_kunden.currentRow()
        if row < 0 or row >= len(self._kunden_data):
            return
        name, _n_b, _total_h, kid = self._kunden_data[row]
        self._kunden_hdr.setText(name or "Kunde")
        self._kd_worker = KundenDetailWorker(kid)
        self._kd_worker.done.connect(self._fill_kunden_detail)
        self._kd_worker.start()

    def _fill_kunden_detail(self, rows):
        tv = self._tv_kunden_detail
        tv.setRowCount(len(rows))
        for r, (datum, terminnr, stunden, tech) in enumerate(rows):
            datum_str = datum.strftime("%d.%m.%Y") if datum else "—"
            for c, val in enumerate([datum_str, terminnr or "—",
                                     f"{float(stunden or 0):.1f}", tech or "—"]):
                tv.setItem(r, c, QTableWidgetItem(val))

    # ── PDF-Upload ────────────────────────────────────────────────────────────

    def _upload_pdf(self):
        pfad, _ = QFileDialog.getOpenFileName(
            self, "Servicebericht-PDF auswählen", "",
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)")
        if not pfad:
            return
        self._show_progress(f"🤖  Claude liest »{os.path.basename(pfad)}« …")
        self._set_busy(True)
        self._pdf_worker = PdfWorker(pfad)
        self._pdf_worker.progress.connect(self._set_progress_text)
        self._pdf_worker.done.connect(self._on_pdf_done)
        self._pdf_worker.error.connect(self._on_pdf_error)
        self._pdf_worker.start()

    def _on_pdf_done(self, info):
        self._set_progress_text(info, C["green"])
        self._set_busy(False)
        QTimer.singleShot(2500, self._hide_progress)
        self._reload()

    def _on_pdf_error(self, err):
        self._set_progress_text(f"✗  {err[:80]}", C["red"])
        self._set_busy(False)
        QTimer.singleShot(5000, self._hide_progress)
        QMessageBox.critical(self, "Analyse-Fehler", err)

    # ── E-Mail-Abruf ──────────────────────────────────────────────────────────

    def _fetch_mail(self, silent=False):
        if getattr(self, "_mail_worker", None) and self._mail_worker.isRunning():
            return
        if not self._mail_cfg.get("host"):
            if not silent:
                QMessageBox.information(
                    self, "Mail-Einstellungen",
                    "Bitte zuerst die Mail-Zugangsdaten über das ⚙-Symbol eintragen.")
                self._edit_mail_settings()
            return
        self._silent_mail = silent
        self._show_progress("📧  Rufe E-Mails ab …")
        self._set_busy(True)
        self._mail_worker = MailWorker(self._mail_cfg)
        self._mail_worker.progress.connect(self._set_progress_text)
        self._mail_worker.done.connect(self._on_mail_done)
        self._mail_worker.error.connect(self._on_mail_error)
        self._mail_worker.start()

    def _on_mail_done(self, results):
        self._set_busy(False)
        ok = sum(1 for r in results if r["ok"])
        fail = len(results) - ok
        if not results:
            self._set_progress_text("✓  Keine neuen Berichte", C["green"])
        else:
            self._set_progress_text(
                f"✓  {ok} importiert" + (f", {fail} fehlgeschlagen" if fail else ""),
                C["green"] if not fail else C["yellow"])
        self.status_msg.emit(f"📧  E-Mail-Abruf: {ok} Bericht(e) importiert")
        QTimer.singleShot(3500, self._hide_progress)
        if ok:
            self._reload()

    def _on_mail_error(self, err):
        self._set_busy(False)
        self._set_progress_text(f"✗  {err[:80]}", C["red"])
        QTimer.singleShot(5000, self._hide_progress)
        if not getattr(self, "_silent_mail", False):
            QMessageBox.critical(self, "Mail-Fehler", err)

    def _edit_mail_settings(self):
        dlg = MailSettingsDialog(self._mail_cfg, self)
        if dlg.exec():
            self._mail_cfg = dlg.values()
            cfg = load_json(SERVICE_CFG, {})
            cfg["mail"] = self._mail_cfg
            save_json(SERVICE_CFG, cfg)
            self._setup_poll_timer()

    # ── Auto-Poll-Timer ───────────────────────────────────────────────────────

    def _setup_poll_timer(self):
        if not hasattr(self, "_poll_timer"):
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(lambda: self._fetch_mail(silent=True))
        self._poll_timer.stop()
        if self._mail_cfg.get("auto_poll") and self._mail_cfg.get("host"):
            minutes = int(self._mail_cfg.get("interval_min", 5))
            self._poll_timer.start(minutes * 60_000)

    # ── Fortschritt / Busy ────────────────────────────────────────────────────

    def _show_progress(self, text):
        self._progress_lbl.setText(text)
        self._progress_lbl.setStyleSheet(f"color:{C['yellow']};")
        self._progress_frame.setVisible(True)

    def _set_progress_text(self, text, color=None):
        self._progress_lbl.setText(text)
        self._progress_lbl.setStyleSheet(f"color:{color or C['yellow']};")
        self._progress_frame.setVisible(True)

    def _hide_progress(self):
        self._progress_frame.setVisible(False)

    def _set_busy(self, busy):
        self._busy = busy
        for b in (self._pdf_btn, self._mail_btn, self._load_btn):
            b.setEnabled(not busy)
