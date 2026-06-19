<div align="center">

# 🛠️ Service - Tool

**Das All-in-One-Werkzeug für Servicetechniker:innen — Arbeitszeiten, Reisekosten, Ersatzteile, Fehlerdiagnose & mehr.**

![Version](https://img.shields.io/badge/version-1.0-2ea043?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Plattform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Offline](https://img.shields.io/badge/Kernfunktionen-offline-success?style=flat-square)
![CRA](https://img.shields.io/badge/EU%20Cyber%20Resilience%20Act-konform-blueviolet?style=flat-square)

</div>

---

## Überblick ##

Das **Service - Tool** ist eine Desktop-Anwendung (PyQt6) für Servicetechniker:innen.
Sie bündelt die täglichen Aufgaben rund um den Außeneinsatz in einer einzigen,
schnellen Oberfläche:

- **Zeit- und Kostenerfassung** (Arbeitszeiten, Reisekosten) mit Excel-/PDF-Export
- **Salesforce-Anbindung** zum Importieren der Einsatzdaten
- **Wissensdatenbank** offline: Ersatzteilkatalog, Fehlerdiagnose, Anleitungen, Service-Assistent
- **Bestellwesen** für Ersatzteile inkl. Favoriten
- **Serviceberichte** aus dem E-Mail-Postfach automatisch per KI auslesen und in die Datenbank schreiben
- **Lager- und Dashboard-Übersicht**

Die Oberfläche ist in ein einheitliches Dark-Theme gehalten und vollständig auf
Deutsch. Die meisten Wissens-Funktionen arbeiten **komplett offline**, damit das
Tool auch ohne Internetverbindung beim Kunden nutzbar bleibt.

---

## Architektur ##

Die Anwendung folgt einem modularen Seiten-Konzept. Jeder Menüpunkt ist ein
eigenes `seite_*.py`-Modul mit einer `QWidget`-Klasse. Gemeinsame Logik liegt
zentral in Hilfsmodulen, damit nichts doppelt gepflegt werden muss.

| Schicht | Module | Aufgabe |
|---|---|---|
| **Einstieg & Navigation** | `main.py` | Hauptfenster, Sidebar, Lazy-Loading der Seiten |
| **Seiten (UI)** | `seite_*.py` | je ein Menüpunkt / Funktionsbereich |
| **Gemeinsame Bausteine** | `utils.py`, `gemeinsame_widgets.py`, `katalog_utils.py` | Pfade, Theme, Widgets, Katalog-Logik |
| **Hintergrundprozesse** | `workers.py`, `updater.py` | Netzwerk-Threads, Selbst-Update |
| **Export** | `export_excel.py`, `export_pdf.py` | Excel-/PDF-Ausgabe |
| **Daten-Pipeline** | `mail_ingest.py`, `analyse_bericht.py`, `extract_*.py` | E-Mail-Import, KI-Auswertung, Daten-Extraktion |

**Lazy Loading:** Seiten werden nicht beim Start, sondern erst beim ersten
Klick auf den Menüpunkt erzeugt und danach im Cache gehalten. Das hält den
Start schnell und spart Speicher.

**Neuen Menüpunkt hinzufügen:** Neues `seite_xyz.py`-Modul anlegen, einen
Eintrag in `Sidebar.NAV` (Icon + Name) und in `_page_factories` (wie die Seite
erzeugt wird) ergänzen — Sidebar und Lazy-Loading übernehmen den Rest.

---

## Installation ##

**Voraussetzungen:** Windows, Python 3.10 oder neuer.

```bash
pip install PyQt6 anthropic pdfplumber psycopg2-binary beautifulsoup4 openpyxl
```

| Abhängigkeit | Verwendung |
|---|---|
| `PyQt6` | Grafische Oberfläche (UI) |
| `openpyxl` | Excel-Export (lazy importiert) |
| `anthropic` | KI-Auswertung der Serviceberichte (Claude) |
| `pdfplumber` | Text aus PDF-Berichten lesen |
| `psycopg2` | Anbindung an die PostgreSQL-Datenbank |
| `beautifulsoup4` (`bs4`) | HTML-Auswertung beim Daten-Import |

Start aus dem Quellcode:

```bash
python main.py
```

---

## Build (.exe erstellen) ##

Über `build.bat` wird mit **PyInstaller** eine eigenständige Windows-`.exe`
erzeugt. Das Skript prüft, ob Python, PyInstaller und PyQt6 vorhanden sind,
installiert Fehlendes nach, räumt alte Build-Artefakte auf und legt das
Ergebnis im Ordner `dist/` ab.

```bash
build.bat
```

Die fertige `.exe` enthält alle Ressourcen (`res/`, `icons/`). Beim Start
entpackt PyInstaller diese in einen temporären `_MEIxxxxx`-Ordner; verwaiste
Ordner abgestürzter Läufe werden beim nächsten Start automatisch aufgeräumt
(`cleanup_orphaned_meipass`).

---

## Konfiguration ##

| Quelle | Inhalt |
|---|---|
| `profile.json` | Persönliche Daten, Wohnort, Bundesland, Update-Einstellungen, gespeicherte SF-Session |
| `res/service_config.json` | E-Mail-Zugangsdaten (IMAP-Host/Port/User/Ordner) |
| `.env` | `ANTHROPIC_API_KEY` und `DATABASE_URL` |

Zugangsdaten für Datenbank und KI liegen bewusst **außerhalb des Quellcodes**
in der `.env`-Datei. Die Salesforce-Session wird lokal im Profil
zwischengespeichert.

---

## Menü: Start ##

`seite_start.py` — Übersicht und Schnellzugriff.

Zeigt alle verfügbaren Module als klickbare Kacheln mit Kurzbeschreibung sowie
eine „Erste Schritte"-Anleitung. Ein Klick auf eine Kachel wechselt direkt zum
jeweiligen Menü (Signal `navigate_to`). Die eigentliche Salesforce-Anmeldung
liegt im darunter folgenden Menüpunkt „API Verbindungen".

---

## Menü: API Verbindungen ##

`seite_salesforce.py` — Verbindungen zu externen Systemen, als Provider-Tabs
aufgebaut, damit weitere APIs einfach ergänzt werden können.

- **Salesforce** (aktiv): Anmeldung, bevor Arbeitszeiten/Reisekosten geladen werden.
  - *Methode 1 — Session ID:* Cookie `sid` einfügen — einfach, aber kurzlebig.
  - *Methode 2 — OAuth (Username/Password-Flow):* dauerhaft, benötigt eine Connected App.
- **SAP** (vorbereitet): read-only Lagerbestände, noch nicht aktiv.
- **TIA Portal** (vorbereitet): Datenübergabe an TIA, noch nicht aktiv.

Der Verbindungsstatus wird über die Signale `sf_connected` / `sf_disconnected`
zentral an das Hauptfenster gemeldet und in der Sidebar (farbiger Punkt)
angezeigt. Ein Hintergrund-Ping (`SFPingWorker`) prüft alle 10 Sekunden, ob die
Session noch gültig ist.

---

## Menü: Dashboard ##

`seite_dashboard.py` — Wochenübersicht „Meine Woche".

> **Demo-/Mock-Stand:** zeigt mit Beispieldaten, wie das fertige Dashboard
> aussehen soll. Layout, Karten und Chart funktionieren bereits vollständig —
> später wird nur die Datenquelle gegen echte Werte (Arbeitszeiten,
> Reisekosten, Salesforce) getauscht.

Enthält KPI-Karten (Stunden, offene Aufträge, gefahrene km, verbaute Teile),
ein kleines Wochen-Chart (Stunden je Wochentag) und die nächsten Termine.

---

## Menü: Mein Lager ##

`seite_lager.py` — persönlicher Fahrzeug-/Kofferbestand des Technikers.

> **Demo-/Mock-Stand:** Bestände sind aktuell Beispieldaten (`MOCK_BESTAND`).
> Tabelle, Suche, Unterbestands-Warnung und PDF-Export funktionieren bereits —
> später ist ein read-only Zugriff auf SAP vorgesehen.

Der PDF-Export nutzt `QPdfWriter` + `QTextDocument` (in PyQt6 enthalten), es ist
also keine zusätzliche Bibliothek nötig.

---

## Menü: Arbeitszeiten ##

`seite_arbeitszeiten.py` — Monatsansicht aller Arbeitstage.

Lädt Daten aus Salesforce oder ermöglicht manuelle Eingabe. Alle Tage sind
inline editierbar; ein Detail-Panel unten ermöglicht die Bearbeitung einzelner
Einträge (Kunden, Zeiten usw.). Die Zeilen- und Detail-Widgets stammen aus
`gemeinsame_widgets.py` (`DayRow`, `DetailPanel`) und werden mit den
Reisekosten geteilt. Export nach Excel (Servicezeitenmeldung) und PDF möglich.

---

## Menü: Reisekosten ##

`seite_reisekosten.py` — Wochenansicht (Kalenderwoche) für die
Reisekostenerfassung.

Zeigt Montag bis Sonntag mit allen Feldern inklusive Mahlzeiten und Sonstiges.
Daten werden nach dem Salesforce-Import automatisch lokal gespeichert. Export
nach Excel (befüllt die Vorlage **FB_0020**) und PDF.

---

## Menü: Ersatzteile ##

`seite_ersatzteile.py` — Ersatzteilkatalog je Gerätesystem.

Daten liegen in `res/et/<system>.json` (Format `{"parts": [...]}`). Welche
Systeme es gibt, steht in `res/et/systeme.json` (Schlüssel → Anzeigename). Neue
Systeme und Einträge können direkt im Tool angelegt werden.

**Verknüpfung:** Ein Doppelklick auf ein Ersatzteil fügt dieses automatisch der
aktuell offenen Bestellung hinzu (Signal `teil_hinzufuegen`).

---

## Menü: Bestellung ##

`seite_bestellungen.py` — schnelles Erstellen von Ersatzteil-Bestellungen.

Eine Bestellung besteht aus Name, Datum und einer Liste von Positionen
(Bestellnummer, Name, Anzahl) und wird als JSON unter `res/orders/<id>.json`
gespeichert — die ID wird beim Speichern fortlaufend vergeben. Gespeicherte
Bestellungen lassen sich über eine Combobox wieder laden.

Häufig benötigte Teile können als **Favoriten** gespeichert werden
(`res/orders/favoriten.json`). Positionen lassen sich jederzeit manuell
hinzufügen/bearbeiten. Beim allerersten Öffnen steht automatisch eine neue,
leere Bestellung bereit. Export als PDF möglich.

---

## Menü: Datenbank ##

`seite_datenbank.py` — Serviceberichte, Ersatzteile/Mittel und Kunden aus der
Railway-PostgreSQL-Datenbank.

Portiert aus dem alten G-PRINT-Tool. Es werden immer alle Daten geladen (kein
Techniker-Namensfilter). **Neu:** Serviceberichte können per E-Mail empfangen
werden — über „E-Mails abrufen" (oder automatisch im Hintergrund) werden
ungelesene Mails mit PDF-Anhang ausgelesen, mit Claude analysiert und
automatisch in die Datenbank eingefügt (siehe `mail_ingest.py` +
`analyse_bericht.py`).

DB-URL und Anthropic-API-Key kommen aus der `.env`, die Mail-Zugangsdaten aus
`res/service_config.json`.

---

## Menü: Fehlerdiagnose ##

`seite_fehlerdiagnose.py` — Master-Detail-Ansicht je Gerätesystem.

Daten liegen in `res/fd/<system>.json` (Format `{"entries": [...]}`),
verfügbare Systeme in `res/fd/systeme.json`. Neue Systeme und Einträge können
direkt im Tool angelegt werden. Die gemeinsame Katalog-Logik (Registry laden,
Dialoge) stammt aus `katalog_utils.py`.

---

## Menü: Anleitungen ##

`seite_anleitungen.py` — Dokumentations-/Anleitungskatalog je Kategorie.

Daten liegen in `res/anl/<kategorie>.json`, Kategorien in `res/anl/systeme.json`.

Besonderheiten:
- Oben kann eine einzelne Kategorie **oder „Alle"** (Voreinstellung) gewählt werden.
- Eine Spalte „Kategorie" zeigt die Zugehörigkeit jedes Eintrags.
- Gesucht wird in **Titel und Inhalt**; Titeltreffer erscheinen oben.
- Ein Eintrag kann auf eine Original-PDF verweisen (Feld `file`), die per Knopf
  im Standardprogramm geöffnet wird. Per Import-Skript erzeugte Einträge tragen
  zusätzlich `file`/`pages`.

---

## Menü: Service-Assistent ##

`seite_assistent.py` — ein **Offline-Suchassistent**.

Durchsucht das vorhandene Wissen (Fehlerdiagnose-Einträge, Anleitungen/Hotline
sowie eine kurze Programm-Hilfe) und zeigt zu einer Frage oder einem Symptom die
am besten passenden Einträge an.

Er nutzt **keine Online-KI und keine externen Bibliotheken** — die Suche läuft
komplett lokal über eine einfache Stichwort-/Relevanzbewertung. Dadurch ist er
schnell, kostenlos und funktioniert ohne Internet (auch in der `.exe`).

Datenquellen: `res/fd/<system>.json`, `res/anl/<system>.json` und die fest
hinterlegte `PROGRAMM_HILFE`.

---

## Menü: Info ##

`seite_info.py` — zeigt Versions- und Speicherort-Informationen sowie den
zuletzt über die Update-URL gelesenen Changelog an (siehe `updater.py`).

---

## Menü: Einstellungen ##

`seite_einstellungen.py` — persönliche Daten & Salesforce-Konfiguration.

Hier werden Stammdaten (Name, Wohnort), das Bundesland (für Feiertage) und die
Update-Einstellungen (Auto-Update an/aus, Update-URL) gepflegt. Der Wohnort
wird von den Reisekosten/Arbeitszeiten als Startpunkt verwendet
(`get_wohnort()`). Einstellungen werden im `profile.json` gespeichert.

---

## Gemeinsame Module ##

| Modul | Inhalt |
|---|---|
| `utils.py` | Pfade (`BASE_DIR`, `RES_DIR`, …), Farbpalette `C` & Stylesheet `STYLE` (Dark-Theme), JSON-Lade-/Speicherfunktionen (`load_json`, `save_json`), Datums-/Zeit-Hilfen, kleine Widget-Ersteller (`lbl`, Buttons, Eingabefelder), `cleanup_orphaned_meipass()` |
| `gemeinsame_widgets.py` | `DetailPanel` (Editier-Panel für einen Tageseintrag) und `DayRow` (inline-editierbare Tageszeile) — geteilt von Arbeitszeiten & Reisekosten |
| `katalog_utils.py` | Registry laden/speichern und generische Dialoge (`NeuesSystemDialog`, `EintragDialog`) für Ersatzteile & Fehlerdiagnose |
| `workers.py` | Salesforce-Hintergrund-Threads (`QThread`) für Login, Ping, Datenabruf — halten die UI reaktionsfähig; Ergebnis je über Qt-Signale |
| `export_excel.py` | Excel-Export für Arbeitszeiten (neu erzeugt) und Reisekosten (Vorlage FB_0020); `openpyxl` wird lazy importiert |
| `export_pdf.py` | A4-PDF-Export für Arbeitszeiten, Reisekosten und Bestellungen über `QPdfWriter` + `QTextDocument` (keine Zusatzbibliothek) |

---

## Daten-Pipeline ##

Module zum Befüllen der Wissensdatenbank und zum Importieren von Berichten:

| Modul | Aufgabe |
|---|---|
| `mail_ingest.py` | Verbindet sich per IMAP/SSL mit dem Postfach, sucht ungelesene Mails, extrahiert PDF-Anhänge, lässt sie auswerten und markiert verarbeitete Mails als gelesen |
| `analyse_bericht.py` | Liest einen Koenig & Bauer Servicebericht (PDF) mit Claude aus und speichert die Daten in der PostgreSQL-Datenbank (auch als CLI nutzbar) |
| `extract_anleitungen.py` | Erzeugt aus Anleitungs-PDFs durchsuchbare JSON-Einträge inkl. Verweis auf die Original-PDF |
| `extract_fehlerdiagnose.py` | Erzeugt Fehlerdiagnose-JSON aus alphaJET-Google-Sites-HTML |
| `extract_spare_parts.py` | Erzeugt Ersatzteil-JSON aus alphaJET-PDF-Ersatzteillisten |

Unterstützte IMAP-Server (Voreinstellungen): Gmail, Outlook/Office365, IONOS,
web.de, GMX (jeweils Port 993, SSL).

---

## Selbst-Update ##

`updater.py` — Selbst-Update über GitHub (`version.json` + SHA-256-Prüfung).

Ablauf:
1. `UpdateCheckWorker` lädt die in den Einstellungen hinterlegte Update-URL
   (zeigt auf eine `version.json`) und vergleicht die Versionsnummer.
2. Ist eine neuere Version verfügbar, fragt `UpdateManager` nach Bestätigung
   und startet `UpdateDownloadWorker`, der die neue `.exe` herunterlädt, ihre
   **SHA-256-Prüfsumme verifiziert** und sie per Batch-Skript einspielt.
3. Das Ergebnis der letzten Prüfung (Version, Changelog, Download-URL) wird in
   `UPDATE_CACHE_FILE` zwischengespeichert, damit die Info-Seite es auch ohne
   Netzwerkabfrage anzeigen kann.

Der Auto-Update-Check läuft ca. 2 Sekunden nach dem Start im Hintergrund, sofern
in den Einstellungen aktiviert (Standard: ja).

---

## Sicherheit & Cyber Resilience Act (CRA) ##

Dieses Projekt orientiert sich an den Anforderungen der EU-Verordnung
**„Cyber Resilience Act" (Regulation (EU) 2024/2847)** an Produkte mit digitalen
Elementen. Die folgenden Maßnahmen tragen zur Konformität bei:

### Sichere Update-Mechanismen (Art. 13, Annex I) ###
Updates werden ausschließlich über eine konfigurierte HTTPS-Quelle bezogen und
durch eine **SHA-256-Integritätsprüfung** verifiziert, bevor sie eingespielt
werden (`updater.py`). Manipulierte oder unvollständige Downloads werden
abgelehnt. Sicherheitsupdates können zeitnah und automatisiert verteilt werden.

### Schutz von Zugangsdaten (Annex I, „secure by default") ###
API-Schlüssel und Datenbank-Zugangsdaten liegen **außerhalb des Quellcodes** in
einer `.env`-Datei und werden nicht ins Repository eingecheckt. Mail-Zugangsdaten
liegen lokal in `res/service_config.json`. Es werden keine Geheimnisse fest im
Code hinterlegt.

### Datenminimierung & Offline-First (Art. 13, Datensparsamkeit) ###
Die Wissensfunktionen (Service-Assistent, Fehlerdiagnose, Ersatzteile,
Anleitungen) arbeiten vollständig **offline ohne Datenübertragung an Dritte**.
Netzwerkverbindungen werden nur dort aufgebaut, wo sie funktional notwendig sind
(Salesforce, IMAP, Datenbank, Update-Check), und über etablierte
verschlüsselte Protokolle (HTTPS, IMAP über SSL/TLS).

### Sichere Kommunikation ###
Externe Verbindungen nutzen Transportverschlüsselung: Salesforce/Update über
HTTPS, E-Mail-Abruf über **IMAP/SSL (Port 993)**, Datenbank über die
PostgreSQL-Verbindungszeichenfolge der `.env`.

### Stabilität & Fehlerresilienz ###
Netzwerk-Aufrufe laufen in eigenen Hintergrund-Threads (`workers.py`,
`updater.py`), sodass die Anwendung bei Verbindungsproblemen reaktionsfähig
bleibt. Verwaiste temporäre Ordner werden beim Start bereinigt
(`cleanup_orphaned_meipass`). Der Salesforce-Session-Status wird laufend
überwacht und abgelaufene Sessions werden klar gemeldet.

### Schwachstellenbehandlung & Meldewesen (Art. 13/14) ###
- **Versionierung & SBOM:** Die App-Version ist zentral gepflegt (`APP_VERSION`),
  die Abhängigkeiten sind im Abschnitt *Installation* dokumentiert und bilden die
  Grundlage einer Software-Stückliste (SBOM).
- **Changelog:** Jede Auslieferung führt einen Changelog (über `version.json` /
  Info-Seite), sodass sicherheitsrelevante Änderungen nachvollziehbar sind.
- **Meldung von Schwachstellen:** Sicherheitslücken bitte vertraulich an die
  unten genannte Kontaktadresse melden (Coordinated Vulnerability Disclosure).
  Bitte keine öffentlichen Issues für sicherheitskritische Funde verwenden.

### Empfohlene Betreiberpflichten ###
- Abhängigkeiten regelmäßig aktualisieren (`pip list --outdated`).
- `.env` und `service_config.json` mit Dateisystem-Rechten schützen und nie teilen.
- Auto-Update aktiviert lassen, um Sicherheitsupdates zeitnah zu erhalten.

---

## Lizenz & Kontakt ##

Internes Werkzeug. Für Sicherheitsmeldungen und Rückfragen wenden Sie sich an
die zuständige Stelle des Betreibers.

<div align="center">

**Service - Tool · v1.0** — entwickelt für den Serviceaußendienst.

</div>
