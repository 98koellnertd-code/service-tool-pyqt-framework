#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_pdf.py
PDF-Export für Arbeitszeiten (Servicezeitenmeldung), Reisekosten und
Bestellungen.

Erzeugt sauber gesetzte A4-PDFs aus HTML über QPdfWriter + QTextDocument —
beides ist in PyQt6 enthalten, es wird also KEINE zusätzliche Bibliothek
(reportlab o.ä.) benötigt.

Die Funktionen spiegeln bewusst dieselben Daten wie export_excel.py wider,
damit PDF und Excel inhaltlich übereinstimmen. Sie sind eigenständig nutzbar
und werden von den Seiten seite_arbeitszeiten / seite_reisekosten /
seite_bestellungen aufgerufen.
"""

import calendar
import datetime
import html as _html

from utils import (
    DAY_NAMES, MONTH_NAMES,
    calc_entry_hours, calc_day_hours, entry_detail_text, week_dates,
)

# Druckfreundliche Farben (bewusst unabhängig vom App-Theme, damit das PDF
# immer gleich und gut lesbar aussieht).
_HEAD_BG = "#1E3A5F"
_HEAD_FG = "#FFFFFF"
_SUB_BG = "#E8EEF5"
_BORDER = "#BDBDBD"
_MUTED = "#5c5e66"
_AD_BG = "#D6E4F0"   # Außendienst
_ID_BG = "#E8F5E9"   # Innendienst / HO
_KRANK = "#FDECEA"
_URLAUB = "#FFF9C4"
_WE_BG = "#EEEEEE"


def _esc(value):
    return _html.escape(str(value)) if value is not None else ""


def _write_html_pdf(dest, html, landscape=False):
    """Rendert HTML in ein A4-PDF unter 'dest'."""
    from PyQt6.QtGui import QPdfWriter, QTextDocument, QPageSize, QPageLayout
    from PyQt6.QtCore import QMarginsF

    writer = QPdfWriter(dest)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    if landscape:
        writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
    doc = QTextDocument()
    doc.setDefaultStyleSheet(
        "body { font-family: Arial, sans-serif; color: #202124; }"
        "h2 { margin: 0 0 2px 0; }"
        "table { border-collapse: collapse; }"
        "th { background:%s; color:%s; }" % (_HEAD_BG, _HEAD_FG)
    )
    doc.setHtml(html)
    doc.print(writer)


def _doc(title, subtitle, table_html, footer=""):
    """Baut ein vollständiges HTML-Dokument mit Kopf, Tabelle und Fußnote."""
    foot = (f"<p style='color:#97989f; font-size:8pt; margin-top:14px;'>{footer}</p>"
            if footer else "")
    return f"""<html><body>
      <div style="background:{_HEAD_BG}; color:{_HEAD_FG}; padding:10px 12px;">
        <h2>{_esc(title)}</h2>
        <div style="font-size:9pt; color:#CCDDEE;">{subtitle}</div>
      </div>
      <div style="height:8px;"></div>
      {table_html}
      {foot}
    </body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
# Dateinamen-Vorschläge
# ══════════════════════════════════════════════════════════════════════════════

def default_stundenblatt_pdf_name(month_name, year, profile):
    name = f"{profile.get('nachname','')}_{profile.get('vorname','')}".strip("_")
    return f"Servicezeitenmeldung_{month_name}_{year}_{name}.pdf"


def default_reisekosten_pdf_name(kw, year, profile):
    name = f"{profile.get('nachname','')}_{profile.get('vorname','')}".strip("_")
    return f"Reisekosten_KW{kw:02d}_{year}_{name}.pdf"


def default_bestellung_pdf_name(bestellung):
    name = (bestellung.get("name") or "Bestellung").strip().replace(" ", "_")
    return f"Bestellung_{bestellung.get('id', '')}_{name}.pdf"


# ══════════════════════════════════════════════════════════════════════════════
# Servicezeitenmeldung (Arbeitszeiten)
# ══════════════════════════════════════════════════════════════════════════════

def export_stundenblatt(dest, month_data, month, year, profile, wohnort="Wohnort"):
    """
    Erstellt die Servicezeitenmeldung als PDF. Spiegelt die Logik aus
    export_excel.export_stundenblatt. Gibt (ad_days, id_days, total_h) zurück.
    """
    month_name = MONTH_NAMES[month - 1]
    name = f"{profile.get('vorname','')} {profile.get('nachname','')}".strip()
    pers_nr = profile.get("pers_nr", "")

    SOLL_H = 8.0
    cal_days = calendar.monthrange(year, month)[1]
    ad_days = id_days = 0
    total_h = 0.0

    rows = []
    for dn in range(1, cal_days + 1):
        d = datetime.date(year, month, dn)
        ds = d.isoformat()
        day = month_data.get(ds, {})
        wd = DAY_NAMES[d.weekday()]
        is_we = d.weekday() >= 5

        status = day.get("status", "Frei" if is_we else "Arbeit")
        entries = day.get("entries") or [{}]
        netto = calc_day_hours(day)
        is_arbeits = status == "Arbeit" and not is_we
        soll = SOLL_H if is_arbeits else 0.0
        gleit = round(netto - soll, 2) if is_arbeits else 0.0

        if status == "Krank":
            day_art, day_bg = "Krank", _KRANK
            soll, gleit = SOLL_H, 0.0
        elif status in ("Urlaub", "Feiertag", "Sonstiges"):
            day_art, day_bg = status, _URLAUB
            soll, gleit = SOLL_H, 0.0
        elif status in ("GLZ", "Kurzarbeit"):
            day_art, day_bg = f"{status} (−8h)", _URLAUB
            soll, gleit = SOLL_H, -SOLL_H
        elif is_we or status == "Frei":
            day_art, day_bg = "", _WE_BG
        else:
            day_art, day_bg = None, None

        total_h += netto

        # AD/ID-Tage zählen (wie im Excel-Export)
        for e in entries:
            ed = e.get("dienst", "Außendienst")
            if day_bg is None:
                if ed in ("Innendienst", "Homeoffice", "Home Office"):
                    id_days += 1
                else:
                    ad_days += 1
        if len(entries) > 1 and day_bg is None:
            ad_days -= (len(entries) - 1)

        start, end, pause = day.get("start", ""), day.get("end", ""), day.get("pause", "")
        gleit_str = (f"+{gleit:.2f}" if gleit > 0 else f"{gleit:.2f}" if gleit < 0 else "0")

        for ei, entry in enumerate(entries):
            if day_bg is not None:
                art_text, bg = day_art, day_bg
            else:
                ed = entry.get("dienst", "Außendienst")
                if ed in ("Innendienst", "Homeoffice", "Home Office"):
                    art_text, bg = "Innendienst / HO", _ID_BG
                elif ed == "Ausland":
                    art_text, bg = "Ausland (AD)", _ID_BG
                else:
                    art_text, bg = "Außendienst", _AD_BG

            route = entry_detail_text(entry, wohnort)
            e_start = entry.get("start") or (start if ei == 0 else "")
            e_end = entry.get("end") or (end if ei == 0 else "")
            e_pause = entry.get("pause") or (pause if ei == 0 else "")
            e_netto = (calc_entry_hours(entry) if entry.get("start") and entry.get("end")
                       else (netto if ei == 0 else 0.0))

            if ei == 0:
                cells = [str(dn), d.strftime("%d.%m.%Y"), wd, art_text,
                         e_start, e_end,
                         str(int(e_pause)) if str(e_pause).isdigit() else "",
                         f"{e_netto:.2f}" if e_netto else "",
                         f"{soll:.1f}" if soll else "", gleit_str]
            else:
                cells = ["", d.strftime("%d.%m.%Y"), "", art_text,
                         e_start, e_end,
                         str(int(e_pause)) if str(e_pause).isdigit() else "",
                         f"{e_netto:.2f}" if e_netto else "", "", ""]

            cells += [entry.get("auftr_nr", ""), entry.get("kunde_name", ""),
                      entry.get("standort", ""), route]

            tds = "".join(
                f"<td style='border:1px solid {_BORDER}; padding:3px; "
                f"background:{bg}; font-size:8pt; text-align:{'center' if i in (0,2,4,5,6,7,8,9) else 'left'};'>"
                f"{_esc(v)}</td>"
                for i, v in enumerate(cells))
            rows.append(f"<tr>{tds}</tr>")

    headers = ["Nr", "Datum", "Wt", "Dienstart", "Start", "Ende", "Pause",
               "Netto h", "Soll", "Gleit", "Auftrag-Nr", "Kunde", "Standort", "Details"]
    head = "".join(
        f"<th style='border:1px solid {_BORDER}; padding:4px; font-size:8pt;'>{h}</th>"
        for h in headers)
    table = (f"<table width='100%' cellspacing='0'>"
             f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>")

    subtitle = (f"Name: {_esc(name)} &nbsp;·&nbsp; Personal-Nr: {_esc(pers_nr)} "
                f"&nbsp;·&nbsp; Monat: {month_name} {year}")
    footer = (f"Außendienst: {ad_days} Tage &nbsp;·&nbsp; Innendienst: {id_days} Tage "
              f"&nbsp;·&nbsp; Gesamt: {total_h:.2f} Stunden &nbsp;·&nbsp; "
              f"K&amp;B Coding GmbH — Servicetechniker")
    _write_html_pdf(dest, _doc("Servicezeitenmeldung", subtitle, table, footer),
                    landscape=True)
    return ad_days, id_days, total_h


# ══════════════════════════════════════════════════════════════════════════════
# Reisekostenabrechnung
# ══════════════════════════════════════════════════════════════════════════════

def _entry_is_filled(entry):
    return bool(entry.get("start") or entry.get("end") or entry.get("kunde_name")
                or entry.get("standort") or entry.get("auftr_nr"))


def export_reisekosten(dest, kw_data, kw, year, profile, wohnort="Wohnort"):
    """
    Erstellt die Reisekostenabrechnung (Außendienst-Reisen der KW) als PDF.
    Spiegelt die Auswahllogik aus export_excel.export_reisekosten.
    Gibt die Anzahl exportierter Reise-Einträge zurück.
    """
    name = f"{profile.get('nachname','')}, {profile.get('vorname','')}".strip(", ")
    dates = week_dates(year, kw)
    kw_extras = kw_data.get("_extras", {})

    rows = []
    block = 0
    for ds in sorted(k for k in kw_data if k != "_extras"):
        day = kw_data[ds]
        if not day:
            continue
        try:
            d = datetime.date.fromisoformat(ds)
        except Exception:
            continue
        default_status = "Frei" if d.weekday() >= 5 else "Arbeit"
        if day.get("status", default_status) != "Arbeit":
            continue
        entries = day.get("entries") or [{}]
        first_ad = True
        for entry in entries:
            dienst = entry.get("dienst", "Außendienst")
            if dienst in ("Innendienst", "Homeoffice", "Home Office"):
                continue
            if not _entry_is_filled(entry):
                continue

            e_start = entry.get("start") or (day.get("start", "") if first_ad else "")
            e_end = entry.get("end") or (day.get("end", "") if first_ad else "")
            land = entry.get("land") or day.get("land", "DE") or "DE"
            reise = entry_detail_text(entry, wohnort)

            datum = d.strftime("%d.%m.%Y") if first_ad else ""
            verpflegung = []
            if first_ad and day.get("uebernacht") == "ja": verpflegung.append("Übernachtung")
            if first_ad and day.get("fruehstueck") == "ja": verpflegung.append("Frühstück")
            if first_ad and day.get("mittag") == "ja": verpflegung.append("Mittag")
            if first_ad and day.get("abend") == "ja": verpflegung.append("Abend")

            cells = [datum, e_start, e_end, land, reise, ", ".join(verpflegung)]
            tds = "".join(
                f"<td style='border:1px solid {_BORDER}; padding:4px; font-size:9pt; "
                f"text-align:{'center' if i in (1,2,3) else 'left'};'>{_esc(v)}</td>"
                for i, v in enumerate(cells))
            rows.append(f"<tr>{tds}</tr>")

            first_ad = False
            block += 1

    # Sonstige Kosten
    try:
        s_txt = kw_extras.get("sonstiges_txt", "").strip()
        s_val = float(kw_extras.get("sonstiges", "") or 0)
    except Exception:
        s_txt, s_val = "", 0.0
    sonstiges_html = ""
    if s_txt or s_val:
        betrag = f"{s_val:.2f} €" if s_val else ""
        sonstiges_html = (
            f"<p style='margin-top:12px; font-size:9pt;'>"
            f"<b>Sonstige Kosten:</b> {_esc(s_txt or 'Sonstige Kosten')} "
            f"&nbsp;{_esc(betrag)}</p>")

    if not rows:
        rows.append(
            f"<tr><td colspan='6' style='border:1px solid {_BORDER}; padding:8px; "
            f"color:{_MUTED}; text-align:center;'>Keine Außendienst-Reisen in dieser "
            f"Kalenderwoche.</td></tr>")

    headers = ["Datum", "Start", "Ende", "Land", "Reise (Strecke / Tätigkeit)", "Verpflegung"]
    head = "".join(
        f"<th style='border:1px solid {_BORDER}; padding:5px; font-size:9pt;'>{h}</th>"
        for h in headers)
    table = (f"<table width='100%' cellspacing='0'>"
             f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
             f"{sonstiges_html}")

    subtitle = (f"Name: {_esc(name)} &nbsp;·&nbsp; KW {kw} / {year} "
                f"&nbsp;·&nbsp; {dates[0]:%d.%m.%Y} – {dates[-1]:%d.%m.%Y}")
    footer = f"{block} Reise-Eintrag(e) &nbsp;·&nbsp; K&amp;B Coding - Service"
    _write_html_pdf(dest, _doc("Reisekostenabrechnung", subtitle, table, footer))
    return block


# ══════════════════════════════════════════════════════════════════════════════
# Bestellung (Ersatzteile)
# ══════════════════════════════════════════════════════════════════════════════

def export_bestellung(dest, bestellung):
    """Erstellt eine Ersatzteilbestellung als PDF aus dem Bestellungs-dict."""
    teile = bestellung.get("teile", [])
    rows = []
    for teil in teile:
        cells = [teil.get("order_no", ""), teil.get("name", ""), teil.get("anzahl", 1)]
        tds = "".join(
            f"<td style='border:1px solid {_BORDER}; padding:5px; font-size:10pt; "
            f"text-align:{'center' if i == 2 else 'left'};'>{_esc(v)}</td>"
            for i, v in enumerate(cells))
        rows.append(f"<tr>{tds}</tr>")
    if not rows:
        rows.append(
            f"<tr><td colspan='3' style='border:1px solid {_BORDER}; padding:8px; "
            f"color:{_MUTED}; text-align:center;'>Keine Positionen.</td></tr>")

    headers = ["Bestellnummer", "Name", "Anzahl"]
    head = "".join(
        f"<th style='border:1px solid {_BORDER}; padding:6px; font-size:10pt;'>{h}</th>"
        for h in headers)
    table = (f"<table width='100%' cellspacing='0'>"
             f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>")

    bid = bestellung.get("id")
    subtitle = (f"Name: {_esc(bestellung.get('name',''))} &nbsp;·&nbsp; "
                f"Datum: {_esc(bestellung.get('datum',''))}"
                + (f" &nbsp;·&nbsp; Bestell-Nr. (intern): {bid}" if bid is not None else ""))
    footer = f"{len(teile)} Position(en)"
    _write_html_pdf(dest, _doc("Ersatzteilbestellung", subtitle, table, footer))
