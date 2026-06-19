<div align="center">

# 🛠️ Service - Tool

**Das All-in-One-Werkzeug für Servicetechniker:innen**
Arbeitszeiten · Reisekosten · Ersatzteile · Fehlerdiagnose · Bestellungen · Serviceberichte

![Version](https://img.shields.io/badge/version-1.0-2ea043?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Plattform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Offline](https://img.shields.io/badge/Kernfunktionen-offline--fähig-success?style=flat-square)
![CRA](https://img.shields.io/badge/EU%20Cyber%20Resilience%20Act-konform-blueviolet?style=flat-square)

</div>

---

## Überblick ##

Das **Service - Tool** ist eine Desktop-Anwendung (PyQt6, Windows) für Servicetechniker:innen im Außendienst. Sie bündelt alle täglichen Aufgaben in einer einzigen schnellen Oberfläche:

| Bereich | Was es kann |
|---|---|
| **Arbeitszeiten** | Monatsweise erfassen, aus Salesforce laden, als Excel/PDF exportieren |
| **Reisekosten** | Wochenweise (KW) erfassen, Vorlage FB_0020 befüllen, PDF exportieren |
| **Ersatzteile** | Teilekatalog je Gerätesystem durchsuchen, pflegen, direkt bestellen |
| **Fehlerdiagnose** | Fehlercodes und Diagnosetexte je System nachschlagen und pflegen |
| **Anleitungen** | Hotline-Anleitungen und Dokus durchsuchen, PDF öffnen |
| **Bestellungen** | Schnelle Bestelllisten mit Favoriten, Excel/PDF-Export |
| **Datenbank** | Serviceberichte aus PostgreSQL ansehen und per E-Mail/KI einpflegen |
| **Service-Assistent** | Offline-Stichwortsuche über alle Wissensinhalte |
| **Dashboard / Lager** | Wochenübersicht und Fahrzeugbestand (Mock, SAP geplant) |

Die meisten Wissens-Funktionen laufen **komplett offline** — kein Internet nötig.

---

## Architektur ##

Jeder Menüpunkt ist ein eigenes `seite_*.py`-Modul mit einer `QWidget`-Klasse. Das Hauptfenster lädt Seiten erst beim ersten Klick auf den jeweiligen Menüpunkt (**Lazy Loading**) und hält sie danach im Cache.

```
main.py               ← Hauptfenster, Sidebar, Lazy-Loading
├── seite_start.py
├── seite_salesforce.py
├── seite_dashboard.py
├── seite_lager.py
├── seite_arbeitszeiten.py
├── seite_reisekosten.py
├── seite_ersatzteile.py
├── seite_bestellungen.py
├── seite_datenbank.py
├── seite_fehlerdiagnose.py
├── seite_anleitungen.py
├── seite_assistent.py
├── seite_info.py
└── seite_einstellungen.py

utils.py              ← Pfade, Theme, Widget-Helfer, Datum-Funktionen
gemeinsame_widgets.py ← DayRow + DetailPanel (geteilt AZ & RK)
katalog_utils.py      ← Registry + Dialoge für ET, FD, ANL
workers.py            ← Salesforce-Hintergrundthreads (QThread)
updater.py            ← Selbst-Update (version.json + SHA-256)
export_excel.py       ← Excel-Ausgabe (Stundenblatt, FB_0020, Bestellungen)
export_pdf.py         ← PDF-Ausgabe (QPdfWriter, keine Zusatzbibliothek)
mail_ingest.py        ← IMAP-E-Mail-Import
analyse_bericht.py    ← PDF-Bericht → Claude → PostgreSQL
extract_*.py          ← Daten-Import-Skripte (einmalig, offline)
```

**Neuen Menüpunkt hinzufügen:** Neues `seite_xyz.py`-Modul anlegen, Eintrag in `Sidebar.NAV` (Icon + Name) und in `_page_factories` (Fabrikfunktion) ergänzen — fertig.

---

## Installation ##

**Voraussetzungen:** Windows, Python 3.10 oder neuer.

```bash
pip install PyQt6 anthropic pdfplumber psycopg2-binary beautifulsoup4 openpyxl
```

| Abhängigkeit | Wozu |
|---|---|
| `PyQt6` | Grafische Oberfläche |
| `openpyxl` | Excel-Export (wird erst beim ersten Export geladen) |
| `anthropic` | KI-Auswertung von Serviceberichten (Claude) |
| `pdfplumber` | Text aus Servicebericht-PDFs lesen |
| `psycopg2-binary` | Anbindung an die PostgreSQL-Datenbank |
| `beautifulsoup4` | HTML-Auswertung beim Fehlerdiagnose-Import |

Starten aus dem Quellcode:

```bash
python main.py
```

---

## Build (.exe erstellen) ##

`build.bat` erstellt mit **PyInstaller** eine eigenständige Windows-`.exe` ohne Installationspflicht.

```bat
build.bat
```

Das Skript prüft, ob Python, PyInstaller und PyQt6 vorhanden sind, installiert Fehlendes nach, räumt alte Build-Artefakte auf und legt das Ergebnis in `dist/` ab. Alle Ressourcen (`res/`, `icons/`) sind enthalten.

**Technischer Hinweis:** PyInstaller entpackt sich bei jedem Start in einen temporären `_MEIxxxxx`-Ordner. Verwaiste Ordner abgestürzter Läufe werden beim nächsten Start automatisch bereinigt (`cleanup_orphaned_meipass` in `utils.py`).

---

## Verzeichnisstruktur der Ressourcen ##

```
res/
├── user_profile.json       ← Persönliche Einstellungen (Profil)
├── farben.json             ← Individuelle Farbüberschreibungen
├── kunden_vorlagen.json    ← Gespeicherte Kundenvorlagen
├── kw_data/                ← Arbeitszeiten/Reisekosten je KW (YYYY-Www.json)
├── templates/              ← Excel-Vorlage FB_0020 (Reisekosten)
├── et/                     ← Ersatzteilkatalog (systeme.json + <key>.json je System)
├── fd/                     ← Fehlerdiagnose (systeme.json + <key>.json je System)
├── anl/                    ← Anleitungen (systeme.json + <key>.json je Kategorie)
├── orders/                 ← Bestellungen (<id>.json) + favoriten.json
├── arbeitszeiten/          ← Standard-Export-Ordner für Stundenblätter
├── reisekosten/            ← Standard-Export-Ordner für Reisekostenabrechnungen
├── bestellungen/           ← Standard-Export-Ordner für Bestelllisten
├── docs/                   ← Zusätzliche Docs für den Service-Assistenten
└── update_cache.json       ← Letzter Update-Stand (für Info-Seite)
```

---

## Konfiguration ##

| Quelle | Inhalt |
|---|---|
| `res/user_profile.json` | Vorname, Nachname, Wohnort, Personalnummer, Bundesland, Salesforce-Zugangsdaten, Export-Pfade, Update-URL, Auto-Update-Schalter |
| `res/service_config.json` | IMAP-Zugangsdaten (Host, Port, User, Passwort, Ordner) |
| `.env` | `ANTHROPIC_API_KEY` und `DATABASE_URL` (nie ins Repository einchecken) |
| `res/farben.json` | Nur die vom Standard abweichenden Farben (wird von den Einstellungen geschrieben) |

---

## Menü: Start ##

`seite_start.py` · `StartPage`

Zeigt alle verfügbaren Module als klickbare Kacheln mit Kurzbeschreibung sowie eine „Erste Schritte"-Anleitung.

**Bedienung:** Kachel anklicken → wechselt direkt zum jeweiligen Menü (internes Signal `navigate_to` an die Sidebar). Die Salesforce-Anmeldung selbst erfolgt im Menüpunkt „API Verbindungen".

---

## Menü: API Verbindungen (Salesforce) ##

`seite_salesforce.py` · `SalesforcePage`

Verbindungen zu externen Systemen, als **Provider-Tabs** aufgebaut (weitere APIs einfach ergänzbar).

### Tab: Salesforce ###

Zwei Anmelde-Methoden:

| Methode | Wann benutzen | Vorgehen |
|---|---|---|
| **Session ID** | Schnellzugriff, kurzlebig (~8 h) | Cookie `sid` aus dem Browser kopieren, einfügen, „Verbinden" klicken |
| **OAuth (Username/Password)** | Dauerhaft, für Produktivbetrieb | E-Mail, Passwort, Security Token, Consumer Key/Secret aus der Salesforce Connected App eintragen |

Nach erfolgreicher Verbindung leuchtet der **grüne Punkt** unten in der Sidebar. Das Tool prüft alle 10 Sekunden im Hintergrund (`SFPingWorker`), ob die Session noch gültig ist. Bei Ablauf erscheint ein Hinweis in der Statusleiste.

### Tab: SAP / TIA Portal ###

Vorbereitet (noch nicht aktiv). Geplant für read-only Lagerbestände (SAP) und Datenübergabe (TIA Portal).

---

## Menü: Dashboard ##

`seite_dashboard.py` · `DashboardSeite`

> **Hinweis (Mock-Stand):** Zeigt Beispieldaten. Layout und Widgets sind fertig; die Datenquelle wird später gegen echte Arbeitszeiten-/Salesforce-Werte getauscht.

Enthält:
- **KPI-Kacheln:** Gearbeitete Stunden, offene Aufträge, gefahrene km, verbaute Teile
- **Wochen-Chart:** Stunden je Wochentag (Mo–Fr)
- **Nächste Termine:** Kommende Einsätze

---

## Menü: Mein Lager ##

`seite_lager.py` · `LagerSeite`

> **Hinweis (Mock-Stand):** Bestandsdaten sind Beispielwerte. Später read-only SAP-Anbindung geplant.

Zeigt den persönlichen Fahrzeug-/Kofferbestand. Bereits funktionsfähig:
- **Suche** über Artikelname/Nummer
- **Unterbestands-Warnung** (farbliche Markierung)
- **PDF-Export** des Bestands (via `QPdfWriter`, keine Zusatzbibliothek)

---

## Menü: Arbeitszeiten ##

`seite_arbeitszeiten.py` · `ArbeitsZeitenPage`

Monatliche Zeiterfassung für alle Arbeitstage.

### Obere Steuerleiste ###

| Element | Funktion | Tooltip |
|---|---|---|
| Monat-Dropdown | Monat wählen | — |
| Jahr-Spinbox | Jahr wählen | — |
| ☁ Von SF laden | Daten für den gewählten Monat aus Salesforce importieren | „Daten aus Salesforce für diesen Monat laden" |
| 💾 Speichern | Alle Monatsdaten lokal in KW-JSON-Dateien speichern | „Alle Monatsdaten lokal speichern" |
| 📊 Excel-Export | Servicezeitenmeldung als `.xlsx` exportieren | „Servicezeitenmeldung für diesen Monat als Excel exportieren" |
| 📄 PDF-Export | Servicezeitenmeldung als `.pdf` exportieren | „Servicezeitenmeldung für diesen Monat als PDF exportieren" |

### Tageszeilen (DayRow) ###

Jeder Tag zeigt inline editierbar: **Wochentag · Datum · Status-Dropdown · Start · Ende · Pause (min) · berechnete Stunden · Eintrags-Zusammenfassung**.

- **Status-Optionen:** Arbeit · Krank · Urlaub · Kurzarbeit · GLZ · Feiertag · Sonstiges · Frei
- Feiertage (nach eingestelltem Bundesland) werden automatisch vorbelegt und per Tooltip am Datum angezeigt
- Wochenendtage werden grau hinterlegt, Kranktage rötlich, Urlaub gelblich, GLZ/Kurzarbeit blau
- Klick auf eine Tageszeile öffnet das **Detail-Panel** unten

### Detail-Panel (DetailPanel) ###

Editier-Panel am unteren Rand, das beim Klick auf einen Tag erscheint.

**Kopfzeile:**

| Schaltfläche | Funktion | Tooltip |
|---|---|---|
| ◀ / ▶ | Zwischen mehreren Einträgen desselben Tages navigieren | „Vorheriger / Nächster Eintrag" |
| ＋ Neu | Neuen Eintrag für diesen Tag hinzufügen | „Neuen Eintrag hinzufügen" |
| 🗑 | Aktuellen Eintrag löschen | „Eintrag löschen" |
| Vorlage-Dropdown | Gespeicherte Kundenvorlage laden | — |
| 💾 Vorlage speichern | Aktuelle Felder als Vorlage speichern | „Aktuelle Felder als Vorlage speichern" |

**Felder – Gruppe „Zeiten & Dienstart":**

| Feld | Inhalt |
|---|---|
| Start | Arbeitsbeginn (HH:MM) |
| Ende | Arbeitsende (HH:MM) |
| Pause (min) | Pausendauer in Minuten |
| Dienstart | Außendienst / Innendienst / Ausland |
| Land | Länderkürzel (Standard: DE) |

**Felder – Gruppe „Auftrag / Kunde" (Außendienst):**

| Feld | Inhalt |
|---|---|
| Auftrags-Nr | Salesforce-Auftragsnummer |
| Kundenname | Name des Kunden |
| Standort | Ort/Adresse |
| Startpunkt | Wohnort oder Hotel |
| Endpunkt | Wohnort oder Hotel |

**Felder – Gruppe „Allgemeinkosten" (Innendienst):**

| Feld | Inhalt |
|---|---|
| Code | Allgemeinkosten-Code (z.B. 0020 = Service Hotline) |
| Details | Freitext-Beschreibung |

Bekannte Codes: `0010` Customer Preparation · `0020` Service Hotline · `0060` Internal Meetings/Trainings · `0090` Documentation · `0130` Proactive Customer Service · `0140` Automotive Workshop · u.v.m.

**Unterer Button-Bereich:**

| Schaltfläche | Funktion | Tooltip |
|---|---|---|
| 💾 Kunde speichern | Kundenname + Standort als Vorlage speichern | „Kundenname + Standort als Vorlage speichern" |
| ✓ Übernehmen | Felder in den Tageseintrag übernehmen (danach noch speichern!) | „Änderungen in den Tageseintrag übernehmen (dann noch KW speichern!)" |

### Statusleiste (Stunden-Bar) ###

Zeigt dauerhaft: **Monatsstunden · Vormonat-Stunden · Gleitzeitkonto** (grün = Plus, rot = Minus).

### Datenspeicherung ###

Daten werden je Kalenderwoche in `res/kw_data/YYYY-Www.json` gespeichert. Der SF-Import speichert automatisch (kein manueller Klick nötig).

---

## Menü: Reisekosten ##

`seite_reisekosten.py` · `ReisekostenPage`

Wochenweise Reisekostenerfassung (Mo–So).

### Steuerleiste ###

| Element | Funktion | Tooltip |
|---|---|---|
| KW-Spinbox | Kalenderwoche wählen | — |
| Jahr-Spinbox | Jahr wählen | — |
| Datums-Anzeige | Zeigt den Datumsbereich der KW | — |
| ☁ Von SF laden | Wochendaten aus Salesforce importieren | „Wochendaten aus Salesforce laden" |
| 💾 Speichern | KW-Daten lokal speichern | „KW-Daten lokal speichern" |
| 📊 Excel-Export | Reisekostenabrechnung (Vorlage **FB_0020**) exportieren | „Reisekostenabrechnung (FB_0020) für diese KW exportieren" |
| 📄 PDF-Export | Reisekostenabrechnung als PDF (ohne Vorlage) exportieren | „Reisekostenabrechnung für diese KW als PDF exportieren" |

> **Hinweis FB_0020:** Die Vorlage muss als `FB_0020*.xlsm` im Ordner `res/templates/` liegen. Das Tool sucht per Präfix, damit Versionsnummern im Dateinamen kein Problem sind.

### Tageszeilen ###

Gleiche Bedienung wie bei Arbeitszeiten. Das Detail-Panel zeigt zusätzlich:

**Felder – Gruppe „Mahlzeiten / Übernachtung"** (nur Reisekosten):

| Feld | Inhalt |
|---|---|
| Übernachtung | ja / nein |
| Frühstück | ja / nein |
| Mittagessen | ja / nein |
| Abendessen | ja / nein |

### Sonstiges-Zeile ###

Am unteren Rand: **Sonstiges €** (Betrag) und **Bezeichnung** (z.B. „Parkgebühren, Maut, Fähre…") — werden im Export berücksichtigt.

---

## Menü: Ersatzteile ##

`seite_ersatzteile.py` · `ErsatzteileSeite`

Ersatzteilkatalog je Gerätesystem mit CRUD-Funktionen.

### Datenstruktur ###

```
res/et/
├── systeme.json        ← {"aj5": "alphaJET 5", "ajx": "alphaJET 5 X", ...}
├── aj5.json            ← {"parts": [{order_no, name, group_de, sources}, ...]}
└── ajd.json
```

Standard-Systeme beim ersten Start: **alphaJET 5 (HS·HS-M·SP)**, **alphaJET 5 X/X-FP**, **alphaJET D**.

### Steuerleiste ###

| Element | Funktion | Tooltip |
|---|---|---|
| System-Dropdown | Gerätesystem wählen | — |
| ＋ Neues System | Neues System anlegen | „Neues Gerätesystem anlegen" |

### Such-/Filterzeile ###

| Element | Funktion |
|---|---|
| 🔍 Suche | Sucht in Bestell-Nr. und Bezeichnung (Echtzeit) |
| Baugruppe-Dropdown | Filter auf eine Baugruppe einschränken |
| ✕ Suche leeren | Suche und Filter zurücksetzen |
| Anzahl-Anzeige | „X / Y Einträge" |

### Tabelle ###

Spalten: **Bestell-Nr. · Bezeichnung · Baugruppe · Modelle**

**Doppelklick** auf einen Eintrag:
1. Kopiert die Bestell-Nr. in die **Zwischenablage**
2. Fügt das Teil automatisch der aktuell offenen **Bestellung** hinzu (Signal `teil_hinzufuegen` → `BestellungenSeite`)

> Tooltip der Aktionsleiste: „Doppelklick = Bestell-Nr. kopieren & zur Bestellung hinzufügen"

### Aktionsleiste ###

| Schaltfläche | Funktion |
|---|---|
| ＋ Neuer Eintrag | Neues Ersatzteil anlegen (Dialog) |
| ✎ Bearbeiten | Ausgewählten Eintrag bearbeiten |
| 🗑 Löschen | Ausgewählten Eintrag löschen (nach Rückfrage) |

### Editier-Dialog (EintragDialog) ###

Felder: **Bestell-Nr.** (Text) · **Bezeichnung** (mehrzeilig) · **Baugruppe** (Einfachauswahl per Checkbox) · **Modelle** (Mehrfachauswahl per Checkbox).

Vorhandene Baugruppen/Modelle werden als Checkboxen angezeigt; neue Werte über das „Neu:"-Textfeld ergänzbar.

---

## Menü: Bestellung ##

`seite_bestellungen.py` · `BestellungenSeite`

Schnelles Erstellen und Verwalten von Ersatzteil-Bestellungen.

### Datenstruktur ###

```
res/orders/
├── 1.json         ← {"name": "...", "datum": "...", "positionen": [...]}
├── 2.json
└── favoriten.json ← [{order_no, name}, ...]
```

IDs werden beim Speichern automatisch fortlaufend vergeben.

### Steuerleiste ###

| Element | Funktion |
|---|---|
| Bestellung-laden-Dropdown | Gespeicherte Bestellung öffnen |
| ＋ Neue Bestellung | Leere Bestellung anlegen |
| 🗑 Bestellung löschen | Aktuelle Bestellung löschen (nach Rückfrage) |

### Kopf-Felder ###

**Name** der Bestellung · **Datum**

### Positionstabelle ###

Spalten: **Bestell-Nr. · Bezeichnung · Anzahl**

Positionen können manuell hinzugefügt, bearbeitet und gelöscht werden. Die Anzahl ist direkt in der Tabelle änderbar (Spinbox).

### Aktionsleiste ###

| Schaltfläche | Funktion |
|---|---|
| ＋ Position | Position manuell hinzufügen |
| ✎ Bearbeiten | Ausgewählte Position bearbeiten |
| 🗑 Löschen | Position löschen |
| ★ Als Favorit | Ausgewähltes Teil als Favorit speichern |
| Favoriten | Gespeicherte Favoriten als Positionen übernehmen |
| 💾 Speichern | Bestellung als JSON speichern |
| 📊 Excel | Bestellliste als Excel exportieren |
| 📄 PDF | Bestellliste als PDF exportieren |

**Automatik:** Ein Doppelklick im Menü „Ersatzteile" fügt das Teil sofort der aktuell offenen Bestellung hinzu (Signal-Verdrahtung in `main.py`).

---

## Menü: Datenbank ##

`seite_datenbank.py` · `DatenbankSeite`

Zugriff auf die Railway-PostgreSQL-Datenbank mit Serviceberichten, Ersatzteilen/Mitteln und Kunden.

### Verbindung ###

DB-URL aus der `.env`-Datei (`DATABASE_URL=postgresql://...`). Ist `psycopg2` nicht installiert oder die Umgebungsvariable nicht gesetzt, erscheint eine lesbare Fehlermeldung mit Installationshinweis.

### Tabs ###

**Serviceberichte:** Tabelle aller Berichte mit Detailansicht. Berichte können per Mail als PDF eingereicht werden — das Tool holt sie automatisch ab und schreibt sie in die DB.

**Ersatzteile/Mittel:** Verbaute Teile und Materialien.

**Kunden:** Kundenstammdaten.

### E-Mail-Import ###

| Schaltfläche | Funktion |
|---|---|
| 📧 E-Mails abrufen | IMAP-Postfach prüfen, PDFs extrahieren, Claude auswerten, in DB speichern |
| ⚙ E-Mail-Einstellungen | IMAP-Zugangsdaten konfigurieren |

Unterstützte Provider (vorkonfiguriert): **Gmail** (imap.gmail.com:993) · **Outlook/Office365** (outlook.office365.com:993) · **IONOS** (imap.ionos.de:993) · **web.de** (imap.web.de:993) · **GMX** (imap.gmx.net:993)

**Ablauf E-Mail-Import:**
1. Mit IMAP/SSL verbinden
2. Ungelesene Mails suchen
3. PDF-Anhänge in einen temporären Ordner extrahieren
4. Jede PDF mit `analyse_bericht.py` (Claude) auslesen
5. Extrahierte Daten in die Datenbank schreiben
6. Mails als gelesen markieren

---

## Menü: Fehlerdiagnose ##

`seite_fehlerdiagnose.py` · `FehlerdiagnoseSeite`

Master-Detail-Ansicht für Fehlercodes und Diagnose-Artikel je Gerätesystem.

### Datenstruktur ###

```
res/fd/
├── systeme.json      ← {"aj5": "alphaJET 5", "ajd": "alphaJET D", ...}
├── aj5.json          ← {"entries": [{cat, title, content}, ...]}
└── ajd_epti.json
```

Standard-Systeme: **alphaJET 5**, **alphaJET D (mondo)**, **alphaJET epti / duo**.

### Bedienung ###

| Element | Funktion |
|---|---|
| System-Dropdown | Gerätesystem wählen |
| ＋ Neues System | System anlegen (Dialog: Kurzname + Anzeigename) |
| 🔍 Suche | Filtert Kategorie und Titel in Echtzeit |
| ✕ Suche leeren | Suchfeld zurücksetzen |
| Master-Tabelle | Kategorie + Titel; Klick zeigt Detailtext unten |
| Detailansicht | Volltext des Eintrags (schreibgeschützt) |
| 📋 Kopieren | Detailtext in die Zwischenablage kopieren |
| ＋ Neuer Eintrag | Kategorie, Titel und Inhalt anlegen |
| ✎ Bearbeiten | Ausgewählten Eintrag bearbeiten |
| 🗑 Löschen | Ausgewählten Eintrag löschen (nach Rückfrage) |

### Editier-Dialog ###

Felder: **Kategorie** (Einfachauswahl per Checkbox, neue Kategorien über Freitext) · **Titel** · **Inhalt** (mehrzeiliges Textfeld).

---

## Menü: Anleitungen ##

`seite_anleitungen.py` · `AnleitungenSeite`

Anleitungs- und Dokumentationskatalog, durchsuchbar nach Titel und Volltext.

### Datenstruktur ###

```
res/anl/
├── systeme.json           ← {"hotline": "Hotline (SAP / Salesforce)", ...}
├── hotline.json           ← {"entries": [{title, content, file, pages}, ...]}
└── files/hotline/*.pdf    ← Kopien der Original-PDFs
```

Einträge können auf eine Original-PDF verweisen (Feld `file`, relativ zu `res/anl/`).

### Besonderheiten gegenüber Fehlerdiagnose ###

- Kategorie-Dropdown mit **„Alle"**-Option (Voreinstellung zeigt alles)
- Suche in **Titel UND Inhalt** — Titeltreffer erscheinen oben
- Spalte „Kategorie" in der Tabelle
- Button **📂 PDF öffnen** erscheint, wenn der Eintrag auf eine Originaldatei verweist (öffnet im Standardprogramm)

### Bedienung ###

| Element | Funktion |
|---|---|
| Kategorie-Dropdown | Kategorie oder „Alle" wählen |
| ＋ Neue Kategorie | Neue Kategorie anlegen |
| 🔍 Suche | Filtert in Titel + Inhalt (Titeltreffer zuerst) |
| 📂 PDF öffnen | Original-PDF im Standardprogramm öffnen (falls vorhanden) |
| ＋ / ✎ / 🗑 | Einträge anlegen, bearbeiten, löschen |

---

## Menü: Service-Assistent ##

`seite_assistent.py` · `AssistentSeite`

Vollständig **offline** arbeitende Stichwort-Suche über alle Wissensinhalte.

### Datenquellen ###

| Quelle | Inhalt |
|---|---|
| `res/fd/<system>.json` | Fehlerdiagnose-Einträge aller Systeme |
| `res/anl/<system>.json` | Anleitungen und Hotline-Infos |
| `res/docs/` | Zusätzliche Markdown- oder JSON-Dateien |
| `PROGRAMM_HILFE` | Fest hinterlegte Hilfe zu Programmfunktionen |

### Bedienung ###

Stichwörter oder Symptombeschreibung in das Suchfeld eingeben, dann **Enter** drücken oder den Suche-Button klicken. Der Assistent:

1. Tokenisiert die Anfrage (deutsche Stoppwörter werden herausgefiltert)
2. Bewertet alle Einträge nach Trefferhäufigkeit und Feldgewichtung (Titel > Inhalt)
3. Zeigt die relevantesten Einträge sortiert nach Score an

**Kein Internet, kein KI-Abo, keine Latenz.** Funktioniert auch in der `.exe` ohne Netzwerk.

Ergebnisse erscheinen im Textbereich mit Kategorie, Titel und relevantem Auszug. Per Klick auf einen Treffer wird der vollständige Inhalt angezeigt.

---

## Menü: Info ##

`seite_info.py` · `InfoPage`

Zeigt:
- App-Name und Version
- Speicherorte (Basispfad, Ressourcen, Profildatei)
- Zuletzt gelesener **Changelog** aus `res/update_cache.json` (ohne erneuten Netzwerkaufruf)

---

## Menü: Einstellungen ##

`seite_einstellungen.py` · `EinstellungenPage`

Die Seite ist scrollbar, damit sie auch bei kleinen Fenstergrößen vollständig zugänglich bleibt.

### Abschnitt: Persönliche Daten ###

| Feld | Beschreibung |
|---|---|
| Vorname / Nachname | Erscheinen auf Exportdokumenten |
| Wohnort | Startpunkt für die Routenberechnung in Reisekosten/Arbeitszeiten |
| Personal-Nr. | Personalnummer für den Excel-Export |
| Bundesland | Für automatische Feiertagsvorbelegung in den Arbeitszeiten. Tooltip: „Wird genutzt, um Feiertage in ‚Arbeitszeiten' automatisch vorzubelegen (Status bleibt für einzelne Tage trotzdem editierbar)." |

Unterstützte Bundesländer: alle 16 deutschen Bundesländer. Feiertage werden per Gaußscher Osterformel berechnet, regionale Feiertage (Allerheiligen, Buß- und Bettag usw.) je nach Bundesland.

### Abschnitt: Salesforce Standardwerte ###

| Feld | Beschreibung |
|---|---|
| Session ID | Gespeicherter Wert (Passwortfeld) |
| OAuth E-Mail | Benutzername für den OAuth-Flow |
| Passwort | Salesforce-Passwort |
| Security Token | Aus SF-Profil → Einstellungen → Sicherheits-Token zurücksetzen |
| Consumer Key | Aus der Connected App |
| Consumer Secret | Aus der Connected App (Passwortfeld) |
| Login-URL | Standard: `https://login.salesforce.com` |

Diese Felder werden auf der Salesforce-Seite vorausgefüllt angezeigt.

### Abschnitt: Datenspeicherung ###

Zeigt die aktuellen Pfade für KW-Daten und Profildatei. Button **📂 Ordner öffnen** öffnet den `res/`-Ordner im Windows-Explorer.

### Abschnitt: Export-Pfade ###

Standard-Ordner für die drei Export-Typen (Arbeitszeiten, Reisekosten, Bestellungen). Per **📂**-Button einen anderen Ordner auswählen.

### Abschnitt: Update ###

| Element | Funktion |
|---|---|
| URL-Feld | URL zur `version.json` auf dem Update-Server |
| Checkbox „Beim Start automatisch prüfen" | Auto-Update an/aus (Standard: ein) |
| 🔄 Jetzt prüfen | Sofort nach neuer Version suchen. Tooltip: „Prüft sofort, ob eine neue Version verfügbar ist." |

### Abschnitt: Farbanpassung ###

Das gesamte Farbschema ist anpassbar. Drei **Standardpaletten** als Ausgangspunkt:

| Palette | Beschreibung |
|---|---|
| ☀ Hell (Standard) | Heller Hintergrund, dunkler Text |
| ⬜ Hellgrau | Etwas gedämpfter, neutraler |
| 🌙 Dunkel | Dunkles Theme, heller Text |

Darunter **18 individuelle Farbfelder** (Swatches, klickbar → Farbauswahl-Dialog):
Hintergrund · Flächen · Hover-Overlay · Statusleiste · Rahmen · Text (3 Stufen) · Akzentfarbe · Grün/Rot/Gelb/Violett · 4 Tag-Status-Farben

| Button | Funktion | Tooltip |
|---|---|---|
| ↺ Auf Standardfarben zurücksetzen | Alle Farben auf Werkseinstellung | „Alle Farben auf die Werkseinstellung zurücksetzen" |
| 💾 Speichern und neu starten | Farben in `res/farben.json` speichern und Programm neu starten | „Farben lokal speichern und das Programm neu starten, damit die neuen Farben angewendet werden" |

> Farbänderungen wirken erst nach „Speichern und neu starten".

---

## Gemeinsame Hilfsmodule ##

### utils.py ###

Zentrales Hilfsmodul — alle anderen Dateien importieren von hier.

**Pfade (automatisch erkannt ob Quellcode oder `.exe`):**

| Konstante | Pfad |
|---|---|
| `BASE_DIR` | Ordner neben der `.exe` bzw. dem Skript |
| `RES_DIR` | `BASE_DIR/res` |
| `KW_DIR` | `res/kw_data` |
| `ET_DIR` | `res/et` |
| `FD_DIR` | `res/fd` |
| `ANL_DIR` | `res/anl` |
| `ORDERS_DIR` | `res/orders` |
| `TEMPLATES_DIR` | `res/templates` |
| `PROFILE_FILE` | `res/user_profile.json` |

**Wichtige Funktionen:**

| Funktion | Beschreibung |
|---|---|
| `load_json(path, default)` | JSON laden, gibt `default` zurück bei Fehler/Nichtvorhanden |
| `save_json(path, data)` | JSON speichern, legt Ordner bei Bedarf an |
| `get_feiertage(year, bundesland)` | Gesetzliche Feiertage als `{iso_date: name}` |
| `calc_day_hours(day)` | Netto-Stunden eines Tages berechnen |
| `get_month_summary(year, month)` | Monatsstunden + Gleitzeitkonto |
| `load_month_data(year, month)` | Alle Tage eines Monats aus KW-Dateien laden |
| `week_dates(year, week)` | 7 `date`-Objekte für eine ISO-KW |
| `current_kw()` | Aktuelle KW und Jahr |
| `load_colors()` / `save_colors()` | Farbschema laden/speichern |
| `cleanup_orphaned_meipass()` | Verwaiste PyInstaller-Temp-Ordner aufräumen |
| `restart_app()` | Anwendung sauber neu starten |

**Widget-Helfer:**

| Funktion | Beschreibung |
|---|---|
| `btn(text, cb, tooltip, color, small)` | Button mit optionalem Tooltip und Farbstil |
| `lbl(text, color, bold, size)` | Label-Schnellerstellung |
| `sep_line()` | Horizontale Trennlinie |
| `page_hero(icon, title, desc, *extra)` | Einheitlicher Seitenkopf (alle Inhaltsseiten) |
| `make_entry(placeholder, width, pw)` | QLineEdit mit Optionen |
| `make_combo(items, width, current)` | QComboBox |

**Allgemeinkosten-Codes:** 17 fest hinterlegte SAP-Codes (0010–2100) für den Innendienst.

### gemeinsame_widgets.py ###

Enthält die beiden Widgets, die Arbeitszeiten und Reisekosten teilen:

**`DayRow`** — Tageszeile in der Monats-/Wochenübersicht:
- Zeigt Wochentag, Datum, Status-Dropdown, Start/Ende/Pause-Felder, Stunden-Anzeige, Eintrags-Zusammenfassung
- Hintergrundfarbe je Status (Krank = rot, Urlaub = gelb, WE = grau, GLZ = blau)
- Feiertags-Tooltip am Datum
- Klick sendet `clicked`-Signal mit ISO-Datum

**`DetailPanel`** — Editier-Panel für Tageseinträge:
- Felder für Zeiten, Dienstart, Kunde/Auftrag (Außendienst) oder Allgemeinkosten (Innendienst)
- Optional Mahlzeiten/Übernachtung (nur Reisekosten)
- Navigation zwischen mehreren Einträgen pro Tag (◀ ▶)
- Vorlagen laden/speichern (`res/kunden_vorlagen.json`)
- `saved`-Signal nach „Übernehmen"

### katalog_utils.py ###

Gemeinsame Logik für Ersatzteile, Fehlerdiagnose und Anleitungen:

- `load_registry / save_registry` — lädt/speichert `systeme.json`
- `load_liste / save_liste` — lädt/speichert die Eintrags-Liste eines Systems
- `NeuesSystemDialog` — Dialog: Kurzname (Dateiname) + Anzeigename eingeben
- `EintragDialog` — generischer Editier-Dialog, feldspec-gesteuert (text / mehrzeilig / checkbox_single / checkbox_multi)
- `CheckboxOptionsWidget` — Checkboxen für vorhandene Werte + Freitext für Neue

### workers.py ###

Alle Netzwerkaufrufe laufen in eigenen `QThread`-Klassen, damit die UI reaktionsfähig bleibt:

| Klasse | Aufgabe | Signale |
|---|---|---|
| `SFSessionWorker` | Anmeldung per Session ID | `success(token, inst_url, user_id, name)` · `error(msg)` |
| `SFOAuthWorker` | Anmeldung per OAuth Username/Password | `success` · `error` |
| `SFPingWorker` | Session-Gültigkeitsprüfung (alle 10 s) | `alive` · `expired` · `warning` |
| `SFLoadWorker` | Zeiteinträge für Datumsbereich laden | `success(dict)` · `error` · `progress(msg)` |

`SFLoadWorker` mapped Salesforce-`TimeSheet`/`TimeSheetEntry`/`WorkOrder`-Records automatisch auf das interne Tages-Datenformat (UTC → Lokalzeit, Pausenberechnung, Gruppen je WorkOrder).

---

## Export-Module ##

### export_excel.py ###

`openpyxl` wird lazy importiert (erst beim ersten Export, nicht beim Programmstart).

| Funktion | Beschreibung |
|---|---|
| `export_stundenblatt(dest, day_data, month, year, profile, wohnort)` | Neue Excel-Servicezeitenmeldung erstellen |
| `export_reisekosten(tmpl, dest, kw_data, kw, year, profile, wohnort)` | FB_0020-Vorlage befüllen |
| `default_stundenblatt_filename(...)` | Vorgeschlagener Dateiname |
| `default_reisekosten_filename(...)` | Vorgeschlagener Dateiname |

### export_pdf.py ###

Nutzt `QPdfWriter` + `QTextDocument` — beide in PyQt6 enthalten, keine Zusatzbibliothek nötig.

| Funktion | Beschreibung |
|---|---|
| `export_stundenblatt(dest, ...)` | A4-PDF Servicezeitenmeldung |
| `export_reisekosten(dest, ...)` | A4-PDF Reisekostenabrechnung |
| Bestellungen-Export | A4-PDF Bestellliste |

---

## Daten-Pipeline (Import-Skripte) ##

Diese Skripte werden **einmalig** ausgeführt, um die JSON-Wissensdatenbank zu befüllen.

### extract_spare_parts.py ###

Extrahiert Ersatzteile aus alphaJET-PDF-Ersatzteillisten und schreibt `res/et/<key>.json`.

### extract_fehlerdiagnose.py ###

Extrahiert Fehlerdiagnose-Einträge aus alphaJET Google-Sites-HTML und schreibt `res/fd/<key>.json`.

### extract_anleitungen.py ###

Extrahiert Anleitungs-PDFs und erzeugt durchsuchbare JSON-Einträge mit Verweis auf die Original-PDF:

```json
{
  "id": 1,
  "title": "In SAP anmelden",
  "content": "In SAP anmelden\n1. ...",
  "file": "files/hotline/In SAP anmelden.pdf",
  "pages": 3
}
```

Original-PDFs werden nach `res/anl/files/<kategorie>/` kopiert.

### mail_ingest.py ###

IMAP-E-Mail-Import der Serviceberichte:

```python
# Verwendung (aus seite_datenbank.py)
fetch_and_process(config)
```

Konfigurationsfelder in `res/service_config.json`: `host`, `port`, `user`, `password`, `folder`.

### analyse_bericht.py ###

Liest einen Koenig & Bauer Servicebericht (PDF) mit **Claude** aus und speichert die Daten in der PostgreSQL-Datenbank. Kann auch direkt als CLI verwendet werden:

```bash
python analyse_bericht.py bericht.pdf
```

Benötigt `.env` mit `ANTHROPIC_API_KEY` und `DATABASE_URL`.

---

## Selbst-Update-Mechanismus ##

`updater.py` · `UpdateManager`, `UpdateCheckWorker`, `UpdateDownloadWorker`

**Ablauf:**

1. `UpdateCheckWorker` (QThread) lädt die konfigurierte Update-URL → `version.json`
2. Vergleicht `version` mit der laufenden `APP_VERSION`
3. Bei neuerer Version: Bestätigungsdialog mit Changelog
4. `UpdateDownloadWorker` lädt die neue `.exe` herunter
5. **SHA-256-Prüfsumme** verifizieren (aus `version.json`)
6. Batch-Skript schreibt die neue `.exe` ein (Ersetzen der laufenden `.exe` unter Windows nur via externem Prozess möglich)
7. Ergebnis wird in `res/update_cache.json` zwischengespeichert (für die Info-Seite ohne erneuten Netzwerkaufruf)

**Format `version.json`:**

```json
{
  "version": "1.1",
  "download_url": "https://example.com/ServiceTool.exe",
  "sha256": "abc123...",
  "changelog": "- Bugfix XY\n- Feature Z"
}
```

---

## Sicherheit & EU Cyber Resilience Act (CRA) ##

Dieses Tool orientiert sich an den Anforderungen der EU-Verordnung **Cyber Resilience Act (Regulation (EU) 2024/2847)** für Produkte mit digitalen Elementen.

### Sichere Update-Mechanismen (Art. 13 Abs. 5, Anhang I) ###

Software-Updates werden ausschließlich über eine konfigurierte **HTTPS-URL** bezogen. Vor der Installation wird die **SHA-256-Prüfsumme** der heruntergeladenen Datei verifiziert (`updater.py`). Manipulierte oder unvollständige Downloads werden abgelehnt. Sicherheitsupdates können zeitnah und automatisiert verteilt werden (Auto-Update standardmäßig aktiv).

### Schutz sensibler Zugangsdaten (Anhang I, „secure by default") ###

- API-Schlüssel (`ANTHROPIC_API_KEY`) und Datenbankverbindung (`DATABASE_URL`) liegen in einer **`.env`-Datei** außerhalb des Quellcodes und werden nicht versioniert
- Salesforce-Zugangsdaten werden im Benutzerprofil (`user_profile.json`) lokal gespeichert — kein Cloud-Sync, kein Klartext-Logging
- Passwortfelder in der UI verwenden `EchoMode.Password` (keine Klartextanzeige)
- Keine fest hinterlegten Geheimnisse im Quellcode

### Datenminimierung & Offline-First (Art. 13, Erwägungsgrund 28) ###

Die Kernfunktionen (Service-Assistent, Fehlerdiagnose, Ersatzteile, Anleitungen, Arbeitszeiten, Reisekosten, Bestellungen) arbeiten **vollständig offline** ohne Datenübertragung an Dritte. Netzwerkverbindungen werden nur dort aufgebaut, wo sie funktional notwendig sind:

| Verbindung | Protokoll | Zweck |
|---|---|---|
| Salesforce | HTTPS | Zeiterfassungsdaten importieren |
| IMAP-Postfach | IMAP/SSL (Port 993) | Serviceberichte empfangen |
| PostgreSQL | TCP/TLS (via `DATABASE_URL`) | Serviceberichte speichern |
| Update-Server | HTTPS | Softwareaktualisierung |
| Anthropic (Claude) | HTTPS | PDF-Bericht-Analyse |

### Stabilität & Fehlerresilienz ###

- Alle Netzwerkaufrufe laufen in **Hintergrundthreads** (`QThread`) — die UI bleibt bei Verbindungsproblemen vollständig bedienbar
- Verwaiste temporäre Ordner früherer Läufe werden beim Start bereinigt (`cleanup_orphaned_meipass`)
- Die Salesforce-Session wird alle 10 Sekunden geprüft; abgelaufene Sessions werden klar angezeigt (roter Punkt + Statusleiste)
- JSON-Ladefunktionen fangen alle Ausnahmen ab — eine beschädigte Datei verhindert nie den Start

### Schwachstellenbehandlung & Meldewesen (Art. 13/14) ###

- **Versionierung:** Die App-Version ist zentral in `utils.py` (`APP_VERSION`) gepflegt und erscheint in Titelleiste und Info-Seite
- **SBOM (Software-Stückliste):** Alle direkten Abhängigkeiten sind im Abschnitt *Installation* dokumentiert und können mit `pip list` reproduziert werden
- **Changelog:** Jede Auslieferung führt einen Changelog in `version.json`, der auf der Info-Seite angezeigt wird
- **Coordinated Vulnerability Disclosure:** Sicherheitslücken bitte vertraulich an den Betreiber melden — keine öffentlichen GitHub-Issues für sicherheitskritische Funde

### Empfohlene Betreiberpflichten ###

- Abhängigkeiten regelmäßig aktualisieren: `pip list --outdated`
- `.env` und `service_config.json` mit Dateisystem-Berechtigungen schützen (kein Lesezugriff für andere Benutzer)
- Auto-Update aktiviert lassen, um Sicherheitsupdates zeitnah zu erhalten
- Beim Einsatz in Unternehmensnetzen VPN-Richtlinien beachten (GlobalProtect o.ä. für Salesforce-Zugriff)

---

## Lizenz & Kontakt ##

Internes Werkzeug für den Serviceaußendienst. Für Sicherheitsmeldungen und Rückfragen wenden Sie sich vertraulich an die zuständige Stelle des Betreibers.

<div align="center">

**Service - Tool · v1.0**

</div>
