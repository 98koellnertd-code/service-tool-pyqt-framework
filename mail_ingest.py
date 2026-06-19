#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mail_ingest.py
Holt Serviceberichte aus einem IMAP-Postfach ab.

Ablauf:
  1. Mit dem Postfach verbinden (IMAP über SSL).
  2. Ungelesene Mails suchen.
  3. Aus jeder Mail die PDF-Anhänge extrahieren und in einen Temp-Ordner legen.
  4. Jede PDF mit analyse_bericht.verarbeite_pdf() auslesen und in die DB speichern.
  5. Erfolgreich verarbeitete Mails als gelesen markieren (\\Seen).

Die Zugangsdaten (Host/Port/User/Passwort/Ordner) kommen aus der Tool-Konfig
(res/service_config.json), DB-URL und API-Key weiterhin aus der .env.

Bekannte IMAP-Server (für die Voreinstellungen im Tool):
    Gmail              imap.gmail.com        993   (App-Passwort nötig)
    Outlook/Office365  outlook.office365.com 993
    IONOS              imap.ionos.de         993
    web.de             imap.web.de           993
    GMX                imap.gmx.net          993
"""

import os
import email
import imaplib
import tempfile
from email.header import decode_header


PROVIDER_PRESETS = {
    "Gmail":              ("imap.gmail.com",        993),
    "Outlook / Office365": ("outlook.office365.com", 993),
    "IONOS":              ("imap.ionos.de",         993),
    "web.de":             ("imap.web.de",           993),
    "GMX":                ("imap.gmx.net",          993),
    "Eigener Server":     ("",                      993),
}


def _decode(value):
    """Dekodiert MIME-kodierte Header/Dateinamen in lesbaren Text."""
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _pdf_attachments(msg):
    """Gibt eine Liste von (dateiname, bytes) für alle PDF-Anhänge zurück."""
    result = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        disp = (part.get("Content-Disposition") or "").lower()
        filename = _decode(part.get_filename())
        ctype = (part.get_content_type() or "").lower()
        is_pdf = ctype == "application/pdf" or filename.lower().endswith(".pdf")
        if not is_pdf:
            continue
        if "attachment" not in disp and not filename:
            continue
        payload = part.get_payload(decode=True)
        if payload:
            result.append((filename or "bericht.pdf", payload))
    return result


def fetch_and_process(config, on_progress=None, mark_seen=True):
    """
    Verbindet sich mit dem Postfach, verarbeitet alle ungelesenen Mails mit
    PDF-Anhang und speichert die Berichte in der Datenbank.

    config: dict mit host, port, user, password, folder (optional), ssl (optional)
    on_progress: optionale Callback-Funktion(str) für Statusmeldungen
    mark_seen: verarbeitete Mails als gelesen markieren

    Gibt eine Liste von Ergebnis-Dicts zurück:
        {"datei": str, "ok": bool, "info": str}
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    # Lokaler Import: vermeidet, dass anthropic/psycopg2 schon beim
    # Modul-Import gebraucht werden, falls man nur Presets lesen will.
    from analyse_bericht import verarbeite_pdf

    host = (config.get("host") or "").strip()
    port = int(config.get("port") or 993)
    user = (config.get("user") or "").strip()
    password = config.get("password") or ""
    folder = (config.get("folder") or "INBOX").strip() or "INBOX"
    use_ssl = config.get("ssl", True)

    if not host or not user or not password:
        raise RuntimeError(
            "Mail-Zugangsdaten unvollständig.\n"
            "Bitte Server, Benutzer und Passwort in den Mail-Einstellungen eintragen."
        )

    log(f"🔌  Verbinde mit {host} …")
    if use_ssl:
        imap = imaplib.IMAP4_SSL(host, port)
    else:
        imap = imaplib.IMAP4(host, port)

    results = []
    try:
        imap.login(user, password)
        imap.select(folder)

        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            raise RuntimeError(f"IMAP-Suche fehlgeschlagen: {status}")

        ids = data[0].split()
        log(f"📬  {len(ids)} ungelesene Mail(s) gefunden.")

        for num in ids:
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            betreff = _decode(msg.get("Subject"))
            anhaenge = _pdf_attachments(msg)

            if not anhaenge:
                # Keine PDF → ungelesen lassen, nicht anfassen
                log(f"⏭  '{betreff[:40]}' – kein PDF-Anhang, übersprungen.")
                continue

            alle_ok = True
            for dateiname, payload in anhaenge:
                tmp_path = None
                try:
                    log(f"🤖  Lese »{dateiname}« …")
                    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                    with os.fdopen(fd, "wb") as f:
                        f.write(payload)
                    daten, _bid = verarbeite_pdf(tmp_path)
                    kunde = (daten.get("kunde") or {}).get("name", "")
                    terminnr = daten.get("terminnummer", "")
                    info = f"{terminnr} – {kunde}".strip(" –")
                    results.append({"datei": dateiname, "ok": True, "info": info})
                    log(f"✓  {dateiname}: {info}")
                except Exception as e:
                    alle_ok = False
                    results.append({"datei": dateiname, "ok": False, "info": str(e)})
                    log(f"✗  {dateiname}: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

            # Nur als gelesen markieren, wenn alle Anhänge erfolgreich waren –
            # so bleiben fehlgeschlagene Mails für einen erneuten Versuch übrig.
            if mark_seen and alle_ok:
                imap.store(num, "+FLAGS", "\\Seen")

        return results
    finally:
        try:
            imap.logout()
        except Exception:
            pass
