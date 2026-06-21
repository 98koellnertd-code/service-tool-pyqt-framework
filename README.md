<div align="center">

# 🛠️ Service - Tool

### Benutzerhandbuch & Cybersicherheits-Dokumentation

**Das All-in-One-Werkzeug für den Serviceaußendienst**
Arbeitszeiten · Reisekosten · Ersatzteile · Fehlerdiagnose · Bestellungen · Serviceberichte

![Version](https://img.shields.io/badge/Version-1.0-2ea043?style=for-the-badge)
![Plattform](https://img.shields.io/badge/Plattform-Windows%2010%2F11-5b6270?style=for-the-badge)
![Framework](https://img.shields.io/badge/PyQt6-Python%203.10%2B-16a34a?style=for-the-badge)
![Offline](https://img.shields.io/badge/Kernfunktionen-offline--fähig-2ea043?style=for-the-badge)
![CRA](https://img.shields.io/badge/Cyber%20Resilience%20Act-konform%20dokumentiert-7c3aed?style=for-the-badge)

<br>

*Dokument aktualisiert am 20.06.2026 · Bezieht sich auf Softwareversion 1.0*

</div>

---

> [!NOTE]
> Dieses Handbuch erfüllt die Anforderungen an **Information und Anweisungen für
> Nutzer** gemäß der **Verordnung (EU) 2024/2847 (Cyber Resilience Act, CRA),
> Anhang II**. Die sicherheitsrelevanten Angaben sind im Kapitel
> [6 — Cybersicherheit (Cyber Resilience Act)](#6--cybersicherheit-cyber-resilience-act)
> gebündelt und im gesamten Dokument mit dem Symbol 🔐 markiert.

---

## Inhaltsverzeichnis

1. [Über dieses Handbuch](#1--über-dieses-handbuch)
2. [Produktbeschreibung &amp; bestimmungsgemäße Verwendung](#2--produktbeschreibung--bestimmungsgemäße-verwendung)
3. [Systemvoraussetzungen &amp; Installation](#3--systemvoraussetzungen--installation)
4. [Erste Schritte](#4--erste-schritte)
5. [Die Module im Detail](#5--die-module-im-detail)
   - [5.1 Start &amp; geführte Tour](#51-start--geführte-tour) · [5.2 API Verbindungen (Salesforce)](#52-api-verbindungen-salesforce) · [5.3 Dashboard](#53-dashboard) · [5.4 Mein Lager](#54-mein-lager)
   - [5.5 Arbeitszeiten](#55-arbeitszeiten) · [5.6 Reisekosten](#56-reisekosten) · [5.7 Ersatzteile](#57-ersatzteile) · [5.8 Bestellung](#58-bestellung)
   - [5.9 Datenbank](#59-datenbank) · [5.10 Fehlerdiagnose](#510-fehlerdiagnose) · [5.11 Anleitungen](#511-anleitungen)
   - [5.12 Service-Assistent &amp; Wissensgenerator](#512-service-assistent--wissensgenerator) · [5.13 Info](#513-info) · [5.14 Einstellungen](#514-einstellungen)
6. [Cybersicherheit (Cyber Resilience Act)](#6--cybersicherheit-cyber-resilience-act)
7. [Fehlerbehebung &amp; FAQ](#7--fehlerbehebung--faq)
8. [Anhang](#8--anhang)

---

## 1 · Über dieses Handbuch

Das **Service - Tool** ist eine Windows-Desktop-Anwendung (PyQt6) für
Servicetechniker:innen im Außendienst. Sie bündelt die täglichen Aufgaben —
Arbeitszeiten, Reisekosten, Ersatzteile, Fehlerdiagnose, Bestellungen,
Anleitungen und Serviceberichte — in einer einzigen Oberfläche. Dieses Handbuch
richtet sich an Anwender:innen sowie IT-Verantwortliche, die das Werkzeug
installieren, bedienen oder in eine bestehende Umgebung integrieren.

| | |
|---|---|
| **Produktname** | Service - Tool |
| **Produktart** | Software mit digitalen Elementen (Desktop-Anwendung) |
| **Version** | 1.0 |
| **Zielsystem** | Windows 10 / 11 (64-Bit) |
| **Technische Basis** | Python 3.10+, PyQt6 |
| **Verwendungszweck** | Zeiterfassung, Reisekosten, Ersatzteil-/Wissensverwaltung und Serviceberichte |
| **Dokumentstand** | 20.06.2026 |

### 1.1 Impressum / Hersteller

> [!IMPORTANT]
> 🔐 **CRA Anhang II Nr. 1 &amp; 2 — Hersteller- und Kontaktangaben.**
> Die folgenden Angaben sind vom Inverkehrbringer vor der Auslieferung zu
> vervollständigen. Die hinterlegte Kontaktadresse dient zugleich als
> **zentrale Anlaufstelle zur Meldung von Schwachstellen** (siehe
> [Kapitel 6.7](#67-meldung-von-schwachstellen-coordinated-vulnerability-disclosure)).

| Feld | Angabe |
|---|---|
| Hersteller / Inverkehrbringer | *[Firmenname eintragen]* |
| Postanschrift | *[Straße, PLZ, Ort, Land eintragen]* |
| E-Mail (allgemein &amp; Sicherheit) | `mitarbeiter@firmenname.de` |
| Single Point of Contact (Schwachstellen) | `mitarbeiter@firmenname.de` |
| EU-Konformitätserklärung | *[URL eintragen, sofern zutreffend]* |

---

## 2 · Produktbeschreibung &amp; bestimmungsgemäße Verwendung

### 2.1 Funktionsumfang

| Bereich | Was es kann |
|---|---|
| **Arbeitszeiten** | Monatsweise erfassen, aus Salesforce laden, als Excel/PDF exportieren |
| **Reisekosten** | Wochenweise (KW) erfassen, Vorlage FB_0020 befüllen, PDF exportieren |
| **Ersatzteile** | Teilekatalog je Gerätesystem durchsuchen, pflegen, direkt bestellen |
| **Fehlerdiagnose** | Fehlercodes und Diagnosetexte je System nachschlagen und pflegen |
| **Anleitungen** | Hotline-Anleitungen und Dokus durchsuchen, PDF öffnen |
| **Bestellungen** | Schnelle Bestelllisten mit Favoriten, Excel/PDF-Export |
| **Datenbank** | Serviceberichte aus PostgreSQL ansehen und per E-Mail/KI einpflegen |
| **Service-Assistent** | Offline-Stichwortsuche über alle Wissensinhalte, mit automatisch erzeugter Programm-Referenz |
| **Geführte Tour** | Schritt-für-Schritt-Erklärung jedes Moduls für die Einarbeitung |
| **Dashboard / Lager** | Wochenübersicht und Fahrzeugbestand (derzeit Mock, SAP-Anbindung geplant) |

Die meisten Wissens- und Erfassungsfunktionen laufen **komplett offline** —
ohne Internet.

### 2.2 Bestimmungsgemäße Verwendung

> [!IMPORTANT]
> 🔐 **CRA Anhang II Nr. 4 — Verwendungszweck und Einsatzumgebung.**

Das Produkt ist bestimmt zum Einsatz durch **fachkundiges Servicepersonal** auf
einem **persönlichen, abgesicherten Arbeitsgerät**. Optionale Online-Funktionen
(Salesforce, E-Mail-Import, Datenbank, KI-Analyse) sind nur für den Betrieb in
einer vertrauenswürdigen Unternehmensumgebung vorgesehen (ggf. über VPN).

### 2.3 Nicht bestimmungsgemäße Verwendung

> [!WARNING]
> Die Anwendung speichert personenbezogene Daten und Zugangsdaten lokal. Der
> Betrieb auf **gemeinsam genutzten oder ungesicherten Geräten** ohne
> Dateisystem-Zugriffsschutz ist **keine bestimmungsgemäße Verwendung**. Siehe
> [Kapitel 6.4](#64-datenhaltung--datenschutz).

---

## 3 · Systemvoraussetzungen &amp; Installation

### 3.1 Voraussetzungen

| Komponente | Anforderung |
|---|---|
| Betriebssystem | Windows 10 oder 11 (64-Bit) |
| Arbeitsspeicher | ≥ 4 GB empfohlen |
| Berechtigungen | Schreibrecht im Programmverzeichnis (Ordner `res/`) |
| Netzwerk (optional) | Für Salesforce, E-Mail-Import, Datenbank und Updates |
| Optional (Entwicklerbetrieb) | Python 3.10+, PyQt6, openpyxl, anthropic, pdfplumber, psycopg2-binary, beautifulsoup4 |

### 3.2 Installation

1. Die ausgelieferte `.exe` in einen Ordner mit **Schreibrechten** kopieren
   (z. B. `C:\Service-Tool\`). Beim ersten Start legt das Programm dort den
   Datenordner `res/` an.
2. Anwendung per Doppelklick starten — **keine systemweite Installation, kein
   Administratorrecht, keine Registry-Änderung** („portable" Anwendung).
3. Beim ersten Start unter *Einstellungen* die persönlichen Daten, das
   Bundesland (für Feiertage) und – falls genutzt – die Online-Zugänge
   hinterlegen.

> [!NOTE]
> Die Anwendung wird als eigenständige `--onefile`-EXE (PyInstaller)
> ausgeliefert. Sie entpackt sich bei jedem Start in ein temporäres
> Verzeichnis, das beim regulären Beenden automatisch aufgeräumt wird
> (`cleanup_orphaned_meipass`).

### 3.3 Start aus dem Quellcode

```bash
pip install PyQt6 anthropic pdfplumber psycopg2-binary beautifulsoup4 openpyxl
python main.py
```

---

## 4 · Erste Schritte

Der schnellste Weg in die tägliche Arbeit:

| Schritt | Aktion |
|:---:|---|
| **1** | **Profil einrichten** — Unter *Einstellungen* Name, Wohnort, Personalnummer und Bundesland eintragen. |
| **2** | **(Optional) Salesforce verbinden** — Unter *API Verbindungen* anmelden, um Zeiten direkt zu importieren. |
| **3** | **Zeiten erfassen** — In *Arbeitszeiten* den Monat pflegen, in *Reisekosten* die Woche (KW). |
| **4** | **Exportieren** — Servicezeitenmeldung bzw. Reisekostenabrechnung (FB_0020) als Excel/PDF erzeugen. |
| **5** | **Wissen nutzen** — *Ersatzteile*, *Fehlerdiagnose*, *Anleitungen* und den *Service-Assistenten* offline durchsuchen. |

> [!TIP]
> Neu im Tool? Auf der Startseite **„🧭 Tour starten"** klicken — die geführte
> Tour erklärt jedes Modul und navigiert dabei automatisch mit.

---

## 5 · Die Module im Detail

Die linke Navigationsleiste führt zu allen Modulen. Seiten werden erst beim
ersten Aufruf geladen („Lazy Loading"), was den Programmstart beschleunigt.

> [!NOTE]
> Sidebar, Startseite, Info-Seite, die geführte Tour und der Wissensgenerator
> beziehen die Modul-Liste aus **einer einzigen zentralen Quelle**
> (`utils.MODULES`). Dadurch sind Reihenfolge, Namen und Beschreibungen überall
> konsistent.

### 5.1 Start &amp; geführte Tour

Übersichtsseite mit Modul-Kacheln (Direktsprung per Klick) und einem
„Erste Schritte"-Leitfaden.

**🧭 Geführte Tour:** Über „Tour starten" erklärt eine Tour jedes Modul
nacheinander und **navigiert dabei automatisch** zur jeweiligen Seite. Die
Tourschritte werden aus dem zentralen Modul-Register erzeugt und bleiben so
immer aktuell.

### 5.2 API Verbindungen (Salesforce)

Verbindungen zu externen Systemen, als **Provider-Tabs** aufgebaut.

| Methode | Wann benutzen | Vorgehen |
|---|---|---|
| **Session ID** | Schnellzugriff, kurzlebig (~8 h) | Cookie `sid` aus dem Browser kopieren, einfügen, „Verbinden" |
| **OAuth (Username/Password)** | Dauerhaft, Produktivbetrieb | E-Mail, Passwort, Security Token, Consumer Key/Secret eintragen |

Nach erfolgreicher Verbindung leuchtet der **grüne Punkt** unten in der Sidebar.
Die Session wird alle 10 s im Hintergrund geprüft (`SFPingWorker`).
**SAP / TIA Portal** sind als Tab vorbereitet (noch nicht aktiv).

### 5.3 Dashboard

> [!NOTE]
> **Mock-Stand:** Zeigt derzeit Beispieldaten. Layout und Widgets sind fertig;
> die Datenquelle wird später gegen echte Arbeitszeiten-/Salesforce-Werte
> getauscht.

Enthält KPI-Kacheln (gearbeitete Stunden, offene Aufträge, gefahrene km,
verbaute Teile), ein Wochen-Chart (Stunden je Wochentag) und die nächsten
Termine.

### 5.4 Mein Lager

> [!NOTE]
> **Mock-Stand:** Bestandsdaten sind Beispielwerte; später ist eine read-only
> SAP-Anbindung geplant.

Zeigt den persönlichen Fahrzeug-/Kofferbestand mit Suche,
Unterbestands-Warnung und PDF-Export (über `QPdfWriter`, keine Zusatzbibliothek).

### 5.5 Arbeitszeiten

Monatliche Zeiterfassung für alle Arbeitstage.

- **Steuerleiste:** Monat/Jahr wählen, *Von SF laden*, *Speichern*, *Excel-* und
  *PDF-Export* (Servicezeitenmeldung).
- **Tageszeilen (DayRow):** Wochentag · Datum · Status · Start · Ende · Pause ·
  berechnete Stunden. Status: Arbeit · Krank · Urlaub · Kurzarbeit · GLZ ·
  Feiertag · Sonstiges · Frei. Feiertage werden je Bundesland automatisch
  vorbelegt; Wochenenden/Krank/Urlaub/GLZ sind farblich hinterlegt.
- **Detail-Panel:** Zeiten &amp; Dienstart, Kunde/Auftrag (Außendienst) bzw.
  Allgemeinkosten-Code (Innendienst), Navigation zwischen mehreren Einträgen
  pro Tag, Kundenvorlagen.
- **Statusleiste:** Monatsstunden · Vormonat · Gleitzeitkonto (grün/rot).
- **Speicherung:** je Kalenderwoche in `res/kw_data/YYYY-Www.json` (SF-Import
  speichert automatisch).

### 5.6 Reisekosten

Wochenweise Erfassung (Mo–So), Bedienung wie bei Arbeitszeiten. Zusätzlich:
Mahlzeiten/Übernachtung je Tag sowie eine *Sonstiges*-Zeile (Betrag +
Bezeichnung). **Excel-Export** befüllt die Vorlage **FB_0020**.

> [!TIP]
> Die Vorlage muss als `FB_0020*.xlsm` im Ordner `res/templates/` liegen — das
> Tool sucht per Präfix, damit Versionsnummern im Dateinamen kein Problem sind.

### 5.7 Ersatzteile

Ersatzteilkatalog je Gerätesystem (`res/et/`) mit Suche, Baugruppen-Filter und
CRUD (Anlegen/Bearbeiten/Löschen). **Doppelklick** auf ein Teil kopiert die
Bestell-Nr. in die Zwischenablage **und** fügt es der aktuell offenen
Bestellung hinzu.

### 5.8 Bestellung

Schnelles Erstellen und Verwalten von Ersatzteil-Bestellungen (`res/orders/`):
Positionen hinzufügen/bearbeiten, Favoriten, Speichern, **Excel-** und
**PDF-Export**.

### 5.9 Datenbank

Zugriff auf die PostgreSQL-Datenbank mit Serviceberichten, Ersatzteilen/Mitteln
und Kunden (DB-URL aus `.env`). Über den **E-Mail-Import** werden eingehende
Servicebericht-PDFs automatisch abgeholt, mit **Claude** ausgewertet und in die
DB geschrieben.

> [!IMPORTANT]
> 🔐 Zugangsdaten (DB, IMAP, API-Schlüssel) liegen außerhalb des Quellcodes
> (`.env`, `res/service_config.json`) — siehe
> [Kapitel 6.4](#64-datenhaltung--datenschutz).

### 5.10 Fehlerdiagnose

Master-Detail-Ansicht für Fehlercodes und Diagnose-Artikel je Gerätesystem
(`res/fd/`), mit Echtzeit-Suche und CRUD. Detailtext per Knopf kopierbar.

### 5.11 Anleitungen

Anleitungs- und Dokumentationskatalog (`res/anl/`), durchsuchbar nach Titel und
Volltext. Einträge können auf eine Original-PDF verweisen, die per **📂 PDF
öffnen** im Standardprogramm startet.

### 5.12 Service-Assistent &amp; Wissensgenerator

Vollständig **offline** arbeitende Stichwortsuche über das gesamte Wissen —
**ohne Internet, ohne KI-Abo, ohne externe Bibliotheken**. Durchsucht werden:
Fehlerdiagnose (`res/fd`), Anleitungen (`res/anl`), die fest hinterlegte
Programmhilfe sowie **alle** Dateien in `res/docs` (`.md`/`.json`).

**Der Wissensgenerator (automatisches „Dazulernen"):** Beim Öffnen des
Assistenten wird die Datei `res/docs/programm_referenz.md` automatisch neu
erzeugt und mitgelesen — so ist die durchsuchbare Programm-Referenz immer
aktuell, **ohne dass Doku von Hand gepflegt werden muss**. Quellen sind
ausschließlich Daten, die ohnehin im Programm liegen:

- das zentrale Modul-Register (Name + Beschreibung jedes Moduls),
- die bereinigten Modul-Beschreibungen (gelesen aus den bereits geladenen
  Modulen — daher auch in der EXE verfügbar, **ohne Quellcode mitzuliefern**).

> [!NOTE]
> 🔐 Der Wissensgenerator arbeitet **rein lokal**: nichts wird heruntergeladen
> oder versendet, kein roher Quellcode wird eingelesen, keine KI angefragt.
> `programm_referenz.md` ist reine Maschinenausgabe und wird bei jedem Öffnen
> überschrieben — **nicht von Hand bearbeiten**. Eigene, dauerhafte Artikel als
> `faq_*.md` ablegen (werden nie überschrieben). „🔄 Wissen neu laden" liest
> ohne Neustart neu ein.

### 5.13 Info

Zeigt Programmversion, Speicherorte und den zuletzt gelesenen Changelog
(`res/update_cache.json`, ohne erneuten Netzwerkaufruf). Zusätzlich ausgebaut um
die Abschnitte **Typische Arbeitsabläufe**, **Häufige Fragen (FAQ)**,
**Bedienhinweise**, **Systemvoraussetzungen** und **Support & Kontakt**.

### 5.14 Einstellungen

Die Seite ist scrollbar. Abschnitte: **Persönliche Daten** (inkl. Bundesland für
Feiertage), **Salesforce-Standardwerte**, **Datenspeicherung** (öffnet `res/`),
**Export-Pfade** und **Update**.

- **Farbanpassung** — Drei Standardpaletten (Hell, Hellgrau, Dunkel) plus
  individuelle Farbfelder. Jede Zeile ist als **Swatch → Funktionsbeschreibung**
  angeordnet (korrigiert, jetzt identisch zum alphaJET-Tool); die Labels nennen
  die Funktion (Akzent = Aktion, Grün = Erfolg/Speichern, Rot = Fehler/Löschen,
  Gelb/Orange = Sonderfunktion, Violett = Export). Eine **Live-Vorschau**
  (Mini-Mockup) zeigt die Wirkung sofort; die vollständige Übernahme erfolgt
  nach „Speichern und neu starten".

---

## 6 · Cybersicherheit (Cyber Resilience Act)

> [!NOTE]
> Dieses Kapitel fasst alle sicherheitsrelevanten Eigenschaften und Pflichten
> gemäß **Verordnung (EU) 2024/2847 (CRA)** zusammen. Die Zuordnung zu den
> Anhängen findet sich in der [Konformitätstabelle](#69-zuordnung-zu-den-cra-anforderungen).

### 6.1 Sicherheitsmerkmale (Security by Design)

🔐 *CRA Anhang I, Teil I — wesentliche Cybersicherheitsanforderungen.*

| Merkmal | Umsetzung im Produkt |
|---|---|
| **Minimale Angriffsfläche** | Keine systemweite Installation, kein Administratorrecht, keine Registry-Einträge, keine Hintergrunddienste. Module werden nur bei Bedarf geladen. |
| **Offline-First** | Kernfunktionen arbeiten ohne Netzwerk; auch der Wissensgenerator ist rein lokal. |
| **Keine Preisgabe interner Pfade** | Fehlermeldungen sind nutzerfreundlich; interne Pfade werden nicht offengelegt. |
| **Integrität von Updates** | Update-Dateien werden per **SHA-256** geprüft; der Download erfordert zwingend **HTTPS**. |
| **Robuste Nebenläufigkeit** | Blockierende Netzwerkaufrufe laufen in Hintergrund-Threads (`QThread`); die Oberfläche bleibt bedienbar. |
| **Fehlerresilienz** | JSON-Ladefunktionen fangen Ausnahmen ab — eine beschädigte Datei verhindert nie den Start. |

### 6.2 Sichere Inbetriebnahme &amp; Konfiguration (Härtung)

🔐 *CRA Anhang II Nr. 8 — Anweisungen zur sicheren Nutzung.*

1. **Gerät absichern** — Auf einem persönlichen, durch Anmeldung geschützten
   Windows-Gerät betreiben; den Programmordner (insbesondere `res/`) nur
   berechtigten Benutzern zugänglich machen.
2. **Geheimnisse schützen** — `.env` und `res/service_config.json` mit
   Dateisystem-Berechtigungen schützen (kein Lesezugriff für andere Benutzer).
3. **Update-Quelle absichern** — Nur eine vertrauenswürdige, per HTTPS
   erreichbare `version.json` hinterlegen (6.6).
4. **Unternehmensnetz** — Beim Zugriff auf Salesforce/DB ggf. VPN-Richtlinien
   beachten (z. B. GlobalProtect).

### 6.3 Netzwerk &amp; externe Verbindungen

🔐 *CRA Anhang I Teil I — Schutz von Daten bei der Übertragung.*

Ausgehende Verbindungen werden nur dort aufgebaut, wo sie funktional notwendig
sind, und nutzen verschlüsselte Transportwege:

| Verbindung | Protokoll | Zweck |
|---|---|---|
| Salesforce | HTTPS | Zeiterfassungsdaten importieren |
| IMAP-Postfach | IMAP/SSL (Port 993) | Serviceberichte empfangen |
| PostgreSQL | TCP/TLS (via `DATABASE_URL`) | Serviceberichte speichern |
| Update-Server | HTTPS | Softwareaktualisierung |
| Anthropic (Claude) | HTTPS | PDF-Bericht-Analyse |

### 6.4 Datenhaltung &amp; Datenschutz

🔐 *CRA Anhang I Teil I — Vertraulichkeit und Datenminimierung.*

- **Lokale Speicherung** — Erfassungs- und Wissensdaten liegen lokal im Ordner
  `res/`. Es findet **keine Telemetrie** statt.
- **Personenbezug** — Persönliche Angaben (Name, Personalnummer, Wohnort) sowie
  erfasste Zeiten/Reisekosten bleiben lokal, sofern sie nicht bewusst exportiert
  oder an Salesforce/DB übergeben werden.
- **Zugangsdaten** — Salesforce-Daten liegen im Benutzerprofil
  (`user_profile.json`); API-Schlüssel (`ANTHROPIC_API_KEY`) und DB-Verbindung
  (`DATABASE_URL`) in der **`.env`-Datei** außerhalb des Quellcodes; IMAP-Daten
  in `res/service_config.json`. Passwortfelder verwenden `EchoMode.Password`.

> [!CAUTION]
> 🔐 `.env`, `res/service_config.json` und `res/user_profile.json` können
> **Zugangsdaten** enthalten. Diese Dateien wie vertrauliche Daten behandeln und
> bei der Außerbetriebnahme sicher löschen (6.8).

### 6.5 Stabilität &amp; Protokollierung

🔐 *CRA Anhang I Teil II — robuster Betrieb.*

- Alle Netzwerkaufrufe laufen in **Hintergrundthreads** — die UI bleibt bei
  Verbindungsproblemen vollständig bedienbar.
- Verwaiste temporäre Ordner früherer Läufe werden beim Start bereinigt
  (`cleanup_orphaned_meipass`).
- Die Salesforce-Session wird alle 10 Sekunden geprüft; abgelaufene Sessions
  werden klar angezeigt (roter Punkt + Statusleiste).

### 6.6 Updates &amp; Integrität

🔐 *CRA Anhang I Teil II — Bereitstellung sicherer Updates.*

- **Bezug** — Das Tool prüft eine konfigurierbare `version.json` (URL unter
  *Einstellungen → Update*). Auto-Prüfung beim Start ist optional (Standard: an).
- **Integrität** — Vor dem Einspielen wird die heruntergeladene Datei gegen die
  in `version.json` angegebene **SHA-256-Prüfsumme** verifiziert. Stimmt sie
  nicht, wird das Update **abgebrochen**.
- **Transport** — Der Download erfolgt **ausschließlich über HTTPS**.
- **Einspielen** — Da Windows eine laufende `.exe` nicht überschreiben kann,
  ersetzt ein kurzes Batch-Skript die alte Datei und startet die neue.

### 6.7 Meldung von Schwachstellen (Coordinated Vulnerability Disclosure)

🔐 *CRA Anhang II Nr. 2 — zentrale Anlaufstelle &amp; CVD-Politik.*

> [!IMPORTANT]
> **Sicherheitslücke gefunden?** Bitte melden Sie diese **vertraulich** an die
> zentrale Anlaufstelle:
>
> **📧 `mitarbeiter@firmenname.de`**
>
> - Bitte **keine** Veröffentlichung vor einer abgestimmten Behebung
>   („Responsible Disclosure"), keine öffentlichen Issues.
> - Hilfreich: betroffene Version, Beschreibung, Reproduktionsschritte und
>   mögliche Auswirkungen.
> - Der Hersteller bestätigt den Eingang und informiert über den Bearbeitungs-
>   und Behebungsstand.

### 6.8 Sichere Außerbetriebnahme &amp; Datenlöschung

🔐 *CRA Anhang II Nr. 9 — sichere Stilllegung.*

1. Anwendung beenden.
2. Den gesamten Ordner **`res/`** sowie die **`.env`-Datei** sicher löschen — sie
   enthalten persönliche Daten, Zugangsdaten und Protokolle.
3. Die Programmdatei (`.exe`) entfernen.
4. Auf Datenträgern mit erhöhtem Schutzbedarf ein **sicheres Löschverfahren**
   (Überschreiben) verwenden.

### 6.9 Support-Zeitraum &amp; Software-Stückliste (SBOM)

🔐 *CRA Anhang II Nr. 6 &amp; 7 — Support-Zeitraum und SBOM.*

**Support-Zeitraum:** Für Version 1.0 werden Sicherheitsupdates für mindestens
**fünf Jahre ab Inverkehrbringen** bereitgestellt *(vom Hersteller verbindlich
zu bestätigen)*.

**Software-Stückliste (SBOM):** Die Anwendung basiert auf den folgenden
Hauptkomponenten. Eine vollständige, maschinenlesbare SBOM (z. B. CycloneDX) ist
auf Anfrage über die Kontaktadresse erhältlich; die direkten Abhängigkeiten sind
mit `pip list` reproduzierbar.

| Komponente | Zweck | Lizenz (typisch) |
|---|---|---|
| Python 3.10+ | Laufzeitumgebung | PSF |
| PyQt6 / Qt 6 | Grafische Oberfläche | GPL/Commercial |
| openpyxl | Excel-Export | MIT |
| pdfplumber | Text aus Servicebericht-PDFs | MIT |
| psycopg2-binary | PostgreSQL-Anbindung | LGPL |
| beautifulsoup4 | HTML-Auswertung (Import) | MIT |
| anthropic | KI-Auswertung (Claude) | MIT |
| PyInstaller | Erstellung der ausführbaren Datei | GPL m. Ausnahme |
| Standardbibliothek (`imaplib`, `hashlib`, `urllib`, …) | Netzwerk, Krypto-Prüfsummen, Update | PSF |

### 6.9 Zuordnung zu den CRA-Anforderungen

🔐 *Übersicht: Wo dieses Handbuch die CRA-Pflichtangaben erfüllt.*

| CRA-Bezug | Anforderung | Fundstelle |
|---|---|---|
| Anhang II Nr. 1 | Hersteller- &amp; Kontaktangaben | [1.1 Impressum](#11-impressum--hersteller) |
| Anhang II Nr. 2 | Anlaufstelle Schwachstellen / CVD | [6.7](#67-meldung-von-schwachstellen-coordinated-vulnerability-disclosure) |
| Anhang II Nr. 3 | Produktidentifikation &amp; Version | [1 Über dieses Handbuch](#1--über-dieses-handbuch) |
| Anhang II Nr. 4 | Verwendungszweck &amp; Umgebung | [2.2](#22-bestimmungsgemäße-verwendung) |
| Anhang II Nr. 5 | Vorhersehbare Risiken | [2.3](#23-nicht-bestimmungsgemäße-verwendung), [6.4](#64-datenhaltung--datenschutz) |
| Anhang II Nr. 6 | SBOM | [6.9](#69-support-zeitraum--software-stückliste-sbom) |
| Anhang II Nr. 7 | Support-Zeitraum &amp; Updates | [6.6](#66-updates--integrität), [6.9](#69-support-zeitraum--software-stückliste-sbom) |
| Anhang II Nr. 8 | Sichere Konfiguration &amp; Nutzung | [6.2](#62-sichere-inbetriebnahme--konfiguration-härtung) |
| Anhang II Nr. 9 | Sichere Außerbetriebnahme | [6.8](#68-sichere-außerbetriebnahme--datenlöschung) |
| Anhang I Teil I | Security by Design | [6.1](#61-sicherheitsmerkmale-security-by-design), [6.4](#64-datenhaltung--datenschutz) |
| Anhang I Teil II | Schwachstellenbehandlung &amp; Updates | [6.5](#65-stabilität--protokollierung), [6.6](#66-updates--integrität), [6.7](#67-meldung-von-schwachstellen-coordinated-vulnerability-disclosure) |

---

## 7 · Fehlerbehebung &amp; FAQ

| Problem | Mögliche Ursache &amp; Lösung |
|---|---|
| **Salesforce verbindet nicht** | Session ID abgelaufen (~8 h) — neu kopieren; oder OAuth-Daten (Token/Consumer Key/Secret) prüfen. |
| **Excel-Export (FB_0020) schlägt fehl** | Vorlage `FB_0020*.xlsm` muss in `res/templates/` liegen. |
| **Datenbank nicht erreichbar** | `psycopg2` installiert? `DATABASE_URL` in `.env` gesetzt und gültig? |
| **E-Mail-Import findet nichts** | IMAP-Zugangsdaten/Ordner prüfen; nur ungelesene Mails mit PDF-Anhang werden verarbeitet. |
| **Assistent findet nichts** | Andere Stichwörter (Menüname/Fachbegriff) versuchen; ggf. „🔄 Wissen neu laden". |
| **Update schlägt fehl** | Update-URL (HTTPS) und Erreichbarkeit prüfen. Bei „SHA-256 stimmt nicht überein" wird das Update aus Sicherheitsgründen abgebrochen. |
| **Farbänderung wirkt nicht** | Farben werden erst nach „Speichern und neu starten" vollständig übernommen (die Live-Vorschau zeigt sie vorab). |

---

## 8 · Anhang

### 8.1 Speicherorte

Alle Daten liegen im Unterordner **`res/`** neben der Programmdatei:

| Pfad | Inhalt |
|---|---|
| `res/user_profile.json` | Persönliche Daten, Export-Pfade, Update-Einstellungen |
| `res/service_config.json` | IMAP-Zugangsdaten |
| `res/farben.json` | Abweichende Farben (Theme) |
| `res/kw_data/` | Arbeitszeiten/Reisekosten je KW |
| `res/et/` · `res/fd/` · `res/anl/` | Ersatzteile, Fehlerdiagnose, Anleitungen |
| `res/orders/` | Bestellungen + Favoriten |
| `res/docs/` | Doku für den Assistenten (`faq_*.md` + auto-erzeugte `programm_referenz.md`) |
| `res/templates/` | Excel-Vorlage FB_0020 |
| `.env` | `ANTHROPIC_API_KEY`, `DATABASE_URL` (nicht versionieren) |

### 8.2 Glossar

| Begriff | Bedeutung |
|---|---|
| **KW** | Kalenderwoche (ISO). |
| **FB_0020** | Excel-Vorlage für die Reisekostenabrechnung. |
| **GLZ** | Gleitzeit. |
| **SBOM** | Software Bill of Materials – Software-Stückliste. |
| **CVD** | Coordinated Vulnerability Disclosure – abgestimmte Schwachstellenmeldung. |
| **Wissensgenerator** | Erzeugt offline `programm_referenz.md` für den Service-Assistenten. |

### 8.3 Änderungshistorie des Dokuments

| Version | Datum | Änderung |
|---|---|---|
| 1.0 | 20.06.2026 | Erstausgabe als gestaltetes Benutzerhandbuch mit CRA-konformer Struktur; ergänzt um zentrales Modul-Register, geführte Tour, Wissensgenerator für den Service-Assistenten, Live-Theme-Vorschau & Funktions-Labels, korrigierte Farbraster-Anordnung und ausgebaute Info-Seite. |

---

<div align="center">

**Service - Tool · Benutzerhandbuch v1.0**

Kontakt &amp; Schwachstellenmeldung: `mitarbeiter@firmenname.de`

<sub>Mit *[Hersteller]* zu vervollständigende Felder sind kursiv in eckigen
Klammern markiert.</sub>

</div>
