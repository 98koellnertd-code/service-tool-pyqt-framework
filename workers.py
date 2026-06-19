#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workers.py
Salesforce-Hintergrund-Threads (QThread).

Diese Klassen laufen außerhalb des UI-Threads, damit Netzwerk-Aufrufe
(Login, Ping, Datenabruf) die Oberfläche nicht blockieren. Jeder Worker
meldet sein Ergebnis über Qt-Signale an den Aufrufer zurück.
"""

import json
import time as _t
import datetime
import urllib.request
import urllib.parse
from collections import defaultdict

from PyQt6.QtCore import QThread, pyqtSignal

from utils import SF_API_VER


class SFSessionWorker(QThread):
    """Verbindet sich bei Salesforce per Session-ID (Cookie 'sid')."""
    success = pyqtSignal(str, str, str, str)   # token, inst_url, user_id, name
    error   = pyqtSignal(str)

    def __init__(self, session_id, inst_url):
        super().__init__()
        self.session_id = session_id
        self.inst_url   = inst_url.rstrip("/")

    def run(self):
        try:
            if not self.session_id:
                raise ValueError("Bitte Session ID eingeben.")
            url = f"{self.inst_url}/services/oauth2/userinfo"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {self.session_id}")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=15) as r:
                info = json.loads(r.read().decode())
            uid  = info.get("user_id", "")
            name = info.get("preferred_username") or info.get("name") or info.get("email", "Verbunden")
            self.success.emit(self.session_id, self.inst_url, uid, name)
        except Exception as e:
            self.error.emit(str(e)[:400])


class SFOAuthWorker(QThread):
    """Verbindet sich bei Salesforce per OAuth Username-Password-Flow."""
    success = pyqtSignal(str, str, str, str)
    error   = pyqtSignal(str)

    def __init__(self, email, password, token, client_id, client_secret, login_url):
        super().__init__()
        self.email, self.password, self.token = email, password, token
        self.client_id, self.client_secret    = client_id, client_secret
        self.login_url = login_url.rstrip("/") if login_url else "https://login.salesforce.com"

    def run(self):
        try:
            if not self.email or not self.password:
                raise ValueError("E-Mail und Passwort sind erforderlich.")
            if not self.client_id or not self.client_secret:
                raise ValueError("Consumer Key und Consumer Secret sind erforderlich.")
            post = urllib.parse.urlencode({
                "grant_type":    "password",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "username":      self.email,
                "password":      self.password + self.token,
            }).encode()
            req = urllib.request.Request(f"{self.login_url}/services/oauth2/token", data=post, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            access_token = data.get("access_token", "")
            instance_url = data.get("instance_url", self.login_url)
            if not access_token:
                raise ValueError(f"Kein Access Token: {data}")
            # Benutzername aus ID-URL holen
            id_url = data.get("id", "")
            name   = self.email
            uid    = ""
            if id_url:
                idr = urllib.request.Request(id_url)
                idr.add_header("Authorization", f"Bearer {access_token}")
                idr.add_header("Accept", "application/json")
                with urllib.request.urlopen(idr, timeout=10) as ir:
                    id_info = json.loads(ir.read().decode())
                uid  = id_info.get("user_id", "")
                name = id_info.get("display_name") or id_info.get("preferred_username") or self.email
            self.success.emit(access_token, instance_url, uid, name)
        except Exception as e:
            self.error.emit(str(e)[:400])


class SFPingWorker(QThread):
    """Prüft regelmäßig, ob die Salesforce-Session noch gültig ist."""
    alive   = pyqtSignal()
    expired = pyqtSignal()
    warning = pyqtSignal()

    def __init__(self, token, inst_url):
        super().__init__()
        self.token, self.inst_url = token, inst_url

    def run(self):
        try:
            req = urllib.request.Request(f"{self.inst_url}/services/data/")
            req.add_header("Authorization", f"Bearer {self.token}")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=6) as r:
                r.read()
            self.alive.emit()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                self.expired.emit()
            else:
                self.warning.emit()
        except Exception:
            self.warning.emit()


class SFLoadWorker(QThread):
    """Lädt Zeiteinträge aus Salesforce für einen Datumsbereich."""
    success  = pyqtSignal(dict)   # {iso_date: day_data}
    error    = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, token, inst_url, user_id, start_str, end_str, wohnort="Wohnort"):
        super().__init__()
        self.token, self.inst_url, self.user_id = token, inst_url, user_id
        self.start_str, self.end_str, self.wohnort = start_str, end_str, wohnort

    def _query(self, soql):
        url = f"{self.inst_url}/services/data/{SF_API_VER}/query?q={urllib.parse.quote(soql)}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode()).get("records", [])
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                ed = json.loads(body)
                msg = f"{ed[0].get('errorCode','')}: {ed[0].get('message','')}" if isinstance(ed, list) and ed else str(ed)[:300]
            except Exception:
                msg = body[:300]
            raise RuntimeError(f"HTTP {e.code}: {msg}") from None

    def run(self):
        try:
            self.progress.emit("🔍  Suche TimeSheets…")
            ts = self._query(
                f"SELECT Id FROM TimeSheet WHERE OwnerId='{self.user_id}' "
                f"AND StartDate >= {self.start_str} AND EndDate <= {self.end_str}")
            if not ts:
                # KW-übergreifend versuchen
                ts = self._query(
                    f"SELECT Id FROM TimeSheet WHERE OwnerId='{self.user_id}' "
                    f"AND (StartDate >= {self.start_str} OR EndDate >= {self.start_str}) "
                    f"AND StartDate <= {self.end_str}")
            if not ts:
                self.success.emit({})
                return

            ts_ids = "','".join(r["Id"] for r in ts)
            self.progress.emit(f"📋  Lade {len(ts)} TimeSheet(s)…")
            te = self._query(
                f"SELECT Id,StartTime,EndTime,Type,WorkOrderId,"
                f"formulaAccount__c,OverheadsType__c "
                f"FROM TimeSheetEntry WHERE TimeSheetId IN ('{ts_ids}')")

            wo_ids = list({r["WorkOrderId"] for r in te if r.get("WorkOrderId")})
            wo_map = {}
            if wo_ids:
                self.progress.emit(f"🏢  Lade {len(wo_ids)} WorkOrder(s)…")
                wo_str  = "','".join(wo_ids)
                wo_recs = self._query(
                    f"SELECT Id,WorkOrderNumber,Street,City FROM WorkOrder WHERE Id IN ('{wo_str}')")
                wo_map  = {r["Id"]: r for r in wo_recs}

            # UTC → Lokale Zeit
            utc_off = datetime.timedelta(seconds=-_t.timezone)
            if _t.daylight and _t.localtime().tm_isdst:
                utc_off = datetime.timedelta(seconds=-_t.altzone)

            self.progress.emit("⚙️  Verarbeite Einträge…")
            parsed = []
            for e in te:
                raw = e.get("StartTime", "")
                if not raw:
                    continue
                try:
                    dt_s = datetime.datetime.fromisoformat(raw[:19]) + utc_off
                except Exception:
                    continue
                try:
                    dt_e = datetime.datetime.fromisoformat(e["EndTime"][:19]) + utc_off
                except Exception:
                    dt_e = dt_s
                ds = dt_s.date().isoformat()
                if ds < self.start_str or ds > self.end_str:
                    continue
                wo = wo_map.get(e.get("WorkOrderId", ""), {})
                parsed.append({
                    "date": ds, "dt_s": dt_s, "dt_e": dt_e,
                    "type": e.get("Type", "Work"),
                    "wo_id": e.get("WorkOrderId", "") or "",
                    "auftr_nr":  wo.get("WorkOrderNumber", ""),
                    "kunde_name": e.get("formulaAccount__c") or "",
                    "standort":  wo.get("City") or wo.get("Street", ""),
                    "overhead":  e.get("OverheadsType__c") or "",
                })
            parsed.sort(key=lambda x: (x["date"], x["dt_s"]))

            per_day = defaultdict(list)
            for p in parsed:
                per_day[p["date"]].append(p)

            new_data = {}
            for ds, tes in sorted(per_day.items()):
                pauses  = [t for t in tes if t["type"] == "Break"]
                work    = [t for t in tes if t["type"] != "Break"]
                pause_m = sum(max(0, int((t["dt_e"] - t["dt_s"]).seconds / 60)) for t in pauses)
                if not work:
                    continue
                day_s = min(t["dt_s"] for t in tes)
                day_e = max(t["dt_e"] for t in tes)

                groups = defaultdict(list)
                anon = 0
                for t in work:
                    k = t["wo_id"] if t["wo_id"] else f"_anon_{anon}"
                    if not t["wo_id"]:
                        anon += 1
                    groups[k].append(t)

                entries = []
                for grp in sorted(groups.values(), key=lambda g: min(x["dt_s"] for x in g)):
                    gs = min(x["dt_s"] for x in grp)
                    ge = max(x["dt_e"] for x in grp)
                    r  = grp[0]
                    entries.append({
                        "start": gs.strftime("%H:%M"), "end": ge.strftime("%H:%M"),
                        "pause": "0", "start_punkt": self.wohnort, "end_punkt": self.wohnort,
                        "dienst": "Außendienst" if r["wo_id"] else "Innendienst",
                        "auftr_nr": r["auftr_nr"], "kunde_name": r["kunde_name"],
                        "standort": r["standort"], "allg_code": r["overhead"], "land": "DE",
                    })
                if entries:
                    entries[0]["pause"] = str(pause_m)

                new_data[ds] = {
                    "status": "Arbeit",
                    "start": day_s.strftime("%H:%M"), "end": day_e.strftime("%H:%M"),
                    "pause": str(pause_m),
                    "uebernacht": "nein", "fruehstueck": "nein", "mittag": "nein", "abend": "nein",
                    "entries": entries,
                }
            self.success.emit(new_data)
        except Exception as e:
            self.error.emit(str(e)[:500])
