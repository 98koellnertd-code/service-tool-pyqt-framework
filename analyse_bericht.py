#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyse_bericht.py
Liest einen Koenig & Bauer Servicebericht (PDF) mit Claude aus und speichert
die extrahierten Daten in der Railway-PostgreSQL-Datenbank.

Zugangsdaten werden – wie im alten Tool – aus einer .env-Datei gelesen:
    ANTHROPIC_API_KEY=sk-ant-...
    DATABASE_URL=postgresql://user:pass@host:port/dbname

Wird sowohl direkt (CLI) als auch aus seite_datenbank.py heraus benutzt.
"""

import os
import json
import base64

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic
import psycopg2

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


def _client():
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nicht gesetzt.\n"
            "Bitte .env-Datei mit ANTHROPIC_API_KEY anlegen."
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def pdf_zu_base64(pfad):
    with open(pfad, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analysiere_pdf(pdf_pfad):
    print(f"Analysiere PDF: {pdf_pfad}")
    pdf_data = pdf_zu_base64(pdf_pfad)

    prompt = """Du analysierst einen Koenig & Bauer Servicebericht.
Extrahiere alle verfuegbaren Informationen und gib sie als JSON zurueck.
Antworte NUR mit dem JSON-Objekt, ohne Erklaerungen oder Markdown.
WICHTIG: Verwende in Texten keine Anfuehrungszeichen. Ersetze " durch ' in allen Textwerten.

Struktur:
{
  "techniker": "Name des Technikers aus Work Report is prepared by",
  "kunde": {
    "name": "Firmenname Account",
    "adresse": "Vollstaendige Adresse",
    "kontakt": "Ansprechpartner Kontakt"
  },
  "terminnummer": "SA-XXXXX",
  "betreff": "Betreff-Feld",
  "datum_start": "TT.MM.JJJJ",
  "datum_ende": "TT.MM.JJJJ",
  "loesung_zusatztext": "Inhalt des Loesungs-Feldes falls vorhanden",
  "abschlusstext": "Abschlusstext falls vorhanden",
  "geraete": [
    {
      "position": "00738267-01",
      "seriennummer": "MID010-039372",
      "geraetetyp": "ALPHAJET EVO 55u DYE V3",
      "status": "Erledigt oder Nicht Erledigt",
      "arbeitszeit_stunden": 2.5,
      "arbeitstext": "Beschreibung der durchgefuehrten Arbeiten ohne Anfuehrungszeichen"
    }
  ],
  "ersatzteile": [
    {
      "position": "00000017",
      "seriennummer": "MID010-038028",
      "produktcode": "1039.4238",
      "produktname": "SERVICE SET FILTERS V3",
      "menge": 1
    }
  ]
}

Regeln:
- arbeitszeit_stunden: Zahl aus Tatsaechliche Dauer, 0 wenn leer
- Alle Geraete aus der Belegposten-Liste erfassen
- Alle Ersatzteile aus Spare Parts Produktverbrauch erfassen
- Falls ein Feld nicht vorhanden ist null verwenden
- Keine Anfuehrungszeichen innerhalb von Textwerten"""

    response = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )

    antwort = response.content[0].text.strip()
    antwort = antwort.replace("```json", "").replace("```", "").strip()

    print("\n🔍 Claude Antwort (erste 500 Zeichen):")
    print(antwort[:500])

    try:
        return json.loads(antwort)
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Fehler: {e}")
        print(f"Problematische Stelle:\n{antwort[max(0,e.pos-100):e.pos+100]}")
        raise


def datum_konvertieren(datum_str):
    """Konvertiert TT.MM.JJJJ zu JJJJ-MM-TT"""
    if not datum_str:
        return None
    try:
        teile = datum_str.split(".")
        return f"{teile[2]}-{teile[1]}-{teile[0]}"
    except Exception:
        return datum_str


def speichere_in_db(daten):
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL nicht gesetzt.\n"
            "Bitte .env-Datei mit DATABASE_URL anlegen."
        )
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO techniker (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id",
        (daten["techniker"],)
    )
    techniker_id = cur.fetchone()[0]

    cur.execute(
        """INSERT INTO kunden (name, kundennummer, adresse)
           VALUES (%s, %s, %s)
           ON CONFLICT (kundennummer) DO UPDATE SET name=EXCLUDED.name RETURNING id""",
        (daten["kunde"]["name"], daten["terminnummer"], daten["kunde"]["adresse"])
    )
    kunde_id = cur.fetchone()[0]

    cur.execute(
        """INSERT INTO serviceberichte
           (techniker_id, kunde_id, datum, geraet_nr, arbeitszeit, zusatztext)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            techniker_id,
            kunde_id,
            datum_konvertieren(daten["datum_ende"]),
            daten["terminnummer"],
            sum(g["arbeitszeit_stunden"] or 0 for g in daten["geraete"]),
            daten.get("loesung_zusatztext") or daten.get("abschlusstext")
        )
    )
    bericht_id = cur.fetchone()[0]

    for et in daten.get("ersatzteile", []):
        cur.execute(
            """INSERT INTO ersatzteile
               (techniker_id, bezeichnung, teilenummer, menge, datum)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                techniker_id,
                et["produktname"],
                et["produktcode"],
                et["menge"],
                datum_konvertieren(daten["datum_ende"])
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅ Gespeichert! Bericht-ID: {bericht_id}")
    return bericht_id


def verarbeite_pdf(pdf_pfad):
    daten = analysiere_pdf(pdf_pfad)
    print("\n📋 Extrahierte Daten:")
    print(json.dumps(daten, indent=2, ensure_ascii=False))
    bericht_id = speichere_in_db(daten)
    return daten, bericht_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Verwendung: python analyse_bericht.py <pfad_zur_pdf>")
        print("Beispiel:   python analyse_bericht.py bericht.pdf")
    else:
        verarbeite_pdf(sys.argv[1])
