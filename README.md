# FF Feuerwehr-Fairness

Eine Desktop-Anwendung zur fairen Dienstplan- und Einteilungsverwaltung für Freiwillige Feuerwehren.

![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## Inhalt

- [Über das Projekt](#über-das-projekt)
- [Features](#features)
- [Installation](#installation)
  - [Fertige Anwendung (Windows)](#fertige-anwendung-windows)
  - [Entwicklungsumgebung](#entwicklungsumgebung)
- [Mehrbenutzer-Betrieb](#mehrbenutzer-betrieb)
- [Architektur](#architektur)
- [Django Apps](#django-apps)
- [Fachbegriffe](#fachbegriffe)
- [Fehlerbehebung](#fehlerbehebung)
- [Entwicklung](#entwicklung)
- [Lizenz](#lizenz)

---

## Über das Projekt

**FF Feuerwehr-Fairness** hilft Freiwilligen Feuerwehren bei der gerechten Verteilung von Diensten und Einsätzen. Die Anwendung verfolgt, wer wie oft eingeteilt wurde, und unterstützt bei der Erstellung fairer Dienstpläne.

### Warum diese Anwendung?

Bei Freiwilligen Feuerwehren ist es wichtig, dass die Belastung durch Dienste und Übungen fair auf alle Mitglieder verteilt wird. Diese Software:

- **Erfasst alle Dienste** und wer daran teilgenommen hat
- **Berechnet Fairness-Scores** basierend auf der Teilnahme
- **Berücksichtigt Qualifikationen** bei der Besetzung von Fahrzeugpositionen
- **Überwacht Atemschutz-Anforderungen** (G26.3 Untersuchungen, Übungsnachweise)

---

## Features

### Mitgliederverwaltung
- Stammdaten aller Feuerwehrangehörigen
- Zuordnung zu Einheiten/Gruppen
- Verfügbarkeits-Tracking
- Kontaktdaten und Notfallkontakte

### Qualifikationsverwaltung
- Ausbildungsnachweise (TM1, TM2, TF, GF, ZF, AGT, MA, etc.)
- Atemschutz-Tauglichkeit (G26.3) mit Ablaufdatum
- Übungsnachweise für Atemschutzgeräteträger
- Automatische Warnung bei ablaufenden Qualifikationen

### Fahrzeugverwaltung
- Fahrzeugstammdaten
- Positionsbesetzung mit Qualifikationsanforderungen
- Staffel- und Gruppenbesetzung (1/5, 1/8)

### Dienstplanung
- Erstellung von Dienstplänen
- Verschiedene Diensttypen (Übung, Dienstabend, Sonderdienst, etc.)
- Automatische Besetzungsvorschläge
- Fairness-basierte Einteilung

### Statistiken & Auswertungen
- Dienst-Übersicht pro Mitglied
- Fairness-Ranking
- Qualifikations-Übersichten
- Export-Funktionen

---

## Installation

### Fertige Anwendung (Windows)

1. **Download** der aktuellen Version:
   - [FF Feuerwehr-Fairness-1.0.0-portable.exe](https://ff.resqware.de/download.html)

2. **Starten**: Die portable EXE kann direkt gestartet werden, keine Installation nötig.

3. **Erster Start**:
   - Beim ersten Start wird ein Admin-Konto erstellt
   - Der Setup-Wizard führt durch die Grundkonfiguration
   - Standard-Qualifikationen und Positionen werden angelegt

### Entwicklungsumgebung

#### Voraussetzungen

- **Python** 3.10 oder höher
- **Node.js** 18 oder höher
- **npm** (kommt mit Node.js)
- **Git** (optional, zum Klonen)

#### 1. Repository klonen

```bash
git clone https://github.com/MLeprich/ff-gerechtigkeitsverwaltung.git
cd ff-gerechtigkeitsverwaltung
```

#### 2. Python-Umgebung einrichten

```bash
# Virtual Environment erstellen
python -m venv venv

# Aktivieren (Linux/macOS)
source venv/bin/activate

# Aktivieren (Windows CMD)
venv\Scripts\activate.bat

# Aktivieren (Windows PowerShell)
venv\Scripts\Activate.ps1

# Dependencies installieren
pip install -r requirements.txt
```

#### 3. Node.js Dependencies installieren

```bash
npm install
```

#### 4. Datenbank initialisieren

```bash
# Migrationen ausführen
python manage.py migrate

# Static Files sammeln
python manage.py collectstatic --noinput

# Admin-Benutzer erstellen
python manage.py createsuperuser
```

#### 5. Anwendung starten

```bash
# Electron App starten
npm start

# Mit Developer Tools
npm run start:dev
```

---

## Mehrbenutzer-Betrieb

Die Anwendung unterstützt den Betrieb mit mehreren Benutzern auf demselben Computer. Die Datenbank wird in einem gemeinsamen Ordner gespeichert:

| Betriebssystem | Datenbankpfad |
|----------------|---------------|
| **Windows** | `C:\ProgramData\FF-Feuerwehr-Fairness\ff_database.sqlite3` |
| **macOS** | `/Users/Shared/FF-Feuerwehr-Fairness/ff_database.sqlite3` |
| **Linux** | `/var/lib/FF-Feuerwehr-Fairness/ff_database.sqlite3` |

### Einrichtung für mehrere Benutzer

1. **Erster Benutzer**: Startet die App und führt den Setup-Wizard durch
2. **Weitere Benutzer**: Starten die App und melden sich mit ihren Zugangsdaten an
3. **Berechtigungen**: Der Admin kann weitere Benutzerkonten anlegen unter *Verwaltung → Benutzer*

### Rollen

| Rolle | Berechtigungen |
|-------|----------------|
| **Mitglied** | Eigenes Profil ansehen, eigene Verfügbarkeit eintragen |
| **Gruppenführer** | Mitglieder der eigenen Gruppe verwalten, Dienste planen |
| **Admin** | Vollzugriff auf alle Funktionen |

---

## Architektur

Die Anwendung basiert auf einer Hybrid-Architektur:

```
┌─────────────────────────────────────────┐
│           Electron (Desktop)            │
│  ┌───────────────────────────────────┐  │
│  │         BrowserWindow             │  │
│  │    (zeigt Django-Frontend an)     │  │
│  └───────────────────────────────────┘  │
│                    ↕                    │
│  ┌───────────────────────────────────┐  │
│  │      Django (Subprocess)          │  │
│  │  • REST-ähnliche Views            │  │
│  │  • Template-Rendering             │  │
│  │  • SQLite-Datenbank               │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| **Desktop-Framework** | Electron 28 |
| **Backend** | Django 5.x |
| **Datenbank** | SQLite 3 |
| **Frontend** | Tailwind CSS, Alpine.js |
| **Interaktivität** | HTMX (optional) |

### Projektstruktur

```
ff-gerechtigkeitsverwaltung/
├── electron/
│   ├── main.js              # Electron Hauptprozess
│   └── preload.js           # IPC-Bridge
├── apps/
│   ├── core/                # Benutzer, Einstellungen
│   ├── members/             # Mitgliederverwaltung
│   ├── vehicles/            # Fahrzeugverwaltung
│   ├── qualifications/      # Qualifikationen, G26.3
│   └── scheduling/          # Dienstplanung
├── config/
│   ├── settings.py          # Django-Konfiguration
│   └── urls.py              # URL-Routing
├── templates/               # HTML-Templates
├── static/                  # CSS, JS, Bilder
├── package.json             # Node.js-Konfiguration
├── requirements.txt         # Python-Dependencies
└── manage.py                # Django-Management
```

---

## Django Apps

### core
Zentrale Funktionen der Anwendung.

| Model | Beschreibung |
|-------|--------------|
| `User` | Erweitertes Benutzermodell mit Rollen (admin, leader, member) |
| `Settings` | Singleton für Feuerwehr-Einstellungen (Name, Stadt, etc.) |
| `AuditLog` | Protokollierung von Änderungen |

### members
Verwaltung der Feuerwehrangehörigen.

| Model | Beschreibung |
|-------|--------------|
| `Member` | Stammdaten eines Mitglieds |
| `Unit` | Einheit/Gruppe (z.B. "1. Gruppe", "Jugendfeuerwehr") |
| `Availability` | Verfügbarkeitseinträge |

### vehicles
Fahrzeug- und Positionsverwaltung.

| Model | Beschreibung |
|-------|--------------|
| `Vehicle` | Fahrzeugstammdaten (Kennzeichen, Typ, etc.) |
| `VehicleType` | Fahrzeugtyp (LF, TLF, DLK, etc.) |
| `Position` | Taktische Position (GF, MA, ATF, etc.) |
| `VehiclePosition` | Zuordnung Position → Fahrzeug mit Qualifikationsanforderungen |

### qualifications
Ausbildungs- und Befähigungsnachweise.

| Model | Beschreibung |
|-------|--------------|
| `Qualification` | Qualifikationstyp (TM1, AGT, GF, etc.) |
| `QualificationCategory` | Kategorie (Grundausbildung, Führung, etc.) |
| `MemberQualification` | Zuordnung Mitglied → Qualifikation |
| `MedicalExam` | Ärztliche Untersuchung (G26.3) |
| `MedicalExamType` | Untersuchungstyp |
| `ExerciseRecord` | Übungsnachweis (für AGT) |

### scheduling
Dienstplanung und Fairness-Tracking.

| Model | Beschreibung |
|-------|--------------|
| `DutyType` | Dienstart (Übung, Dienstabend, etc.) |
| `Duty` | Einzelner Dienst/Termin |
| `Assignment` | Einteilung eines Mitglieds zu einer Position |
| `FairnessScore` | Fairness-Punkte pro Mitglied |
| `AssignmentHistory` | Historische Einteilungsdaten |

---

## Fachbegriffe

### Qualifikationen nach FwDV

| Kürzel | Bezeichnung | Voraussetzung |
|--------|-------------|---------------|
| **TM1** | Truppmann Teil 1 | - |
| **TM2** | Truppmann Teil 2 | TM1 |
| **TM** | Truppmann (vollständig) | TM1 + TM2 |
| **TF** | Truppführer | TM |
| **GF** | Gruppenführer | TF |
| **ZF** | Zugführer | GF |
| **AGT** | Atemschutzgeräteträger | TM + G26.3 |
| **MA** | Maschinist | TM |
| **MKS** | Motorkettensägenführer | TM |

### Taktische Positionen

| Kürzel | Position | Qualifikation |
|--------|----------|---------------|
| **GF** | Gruppenführer / Fahrzeugführer | GF oder TF |
| **MA** | Maschinist | MA |
| **ME** | Melder | TM |
| **ATF** | Angriffstruppführer | TF, AGT |
| **ATM** | Angriffstruppmann | TM, AGT |
| **WTF** | Wassertruppführer | TF |
| **WTM** | Wassertruppmann | TM |
| **STF** | Schlauchtruppführer | TF |
| **STM** | Schlauchtruppmann | TM |

### Fahrzeugbesetzung

| Besetzung | Bedeutung |
|-----------|-----------|
| **1/5** | 1 Führungskraft + 5 Einsatzkräfte (Staffel) |
| **1/8** | 1 Führungskraft + 8 Einsatzkräfte (Gruppe) |

### Atemschutz (AGT)

- **G26.3**: Arbeitsmedizinische Vorsorgeuntersuchung für Atemschutzgeräteträger
- **Gültigkeit**: 36 Monate (unter 50 Jahre) bzw. 12 Monate (ab 50 Jahre)
- **Übungsnachweis**: Mindestens 1 Übung pro Jahr erforderlich

---

## Fehlerbehebung

### Die Anwendung startet nicht

1. **Logs prüfen**:
   - Windows: `C:\ProgramData\FF-Feuerwehr-Fairness\logs\main.log`
   - Oder im Entwicklungsmodus: Konsole zeigt Fehler

2. **Port belegt**: Django benötigt Port 8000. Prüfen mit:
   ```bash
   # Windows
   netstat -ano | findstr :8000

   # Linux/macOS
   lsof -i :8000
   ```

3. **Python nicht gefunden**: Stellen Sie sicher, dass Python im PATH ist:
   ```bash
   python --version
   ```

### Datenbank-Probleme

1. **Datenbank zurücksetzen** (Achtung: Alle Daten werden gelöscht!):
   ```bash
   # Entwicklung
   rm data/ff_database.sqlite3
   python manage.py migrate
   python manage.py createsuperuser
   ```

2. **Datenbank reparieren**:
   ```bash
   python manage.py dbshell
   > .integrity_check
   ```

### Login funktioniert nicht

1. **Passwort vergessen**: Neuen Superuser erstellen:
   ```bash
   python manage.py createsuperuser
   ```

2. **Session-Probleme**: Cookies löschen oder anderen Browser verwenden

---

## Entwicklung

### Django separat starten

Für Backend-Entwicklung ohne Electron:

```bash
source venv/bin/activate  # Linux/macOS
python manage.py runserver
```

Dann im Browser: http://localhost:8000

### Tests ausführen

```bash
# Alle Tests
python manage.py test

# Einzelne App
python manage.py test apps.core
python manage.py test apps.scheduling
```

### Build erstellen

```bash
# Für Windows (portable EXE)
npm run build:win

# Für macOS (DMG)
npm run build:mac

# Für Linux (AppImage)
npm run build:linux
```

Die fertigen Dateien befinden sich im `dist/` Ordner.

### Code-Stil

- **Python**: PEP 8
- **JavaScript**: ESLint (Standard)
- **Templates**: Django Template Language

---

## Mitwirken

Beiträge sind willkommen! So können Sie helfen:

1. **Issues erstellen** für Bugs oder Feature-Requests
2. **Pull Requests** für Code-Beiträge
3. **Dokumentation** verbessern
4. **Übersetzungen** hinzufügen

### Entwicklungs-Workflow

1. Fork erstellen
2. Feature-Branch anlegen (`git checkout -b feature/neue-funktion`)
3. Änderungen committen (`git commit -m 'Neue Funktion hinzugefügt'`)
4. Branch pushen (`git push origin feature/neue-funktion`)
5. Pull Request erstellen

---

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe [LICENSE](LICENSE) für Details.

---

## Kontakt

- **GitHub**: [https://github.com/MLeprich/ff-gerechtigkeitsverwaltung](https://github.com/MLeprich/ff-gerechtigkeitsverwaltung)
- **Issues**: [https://github.com/MLeprich/ff-gerechtigkeitsverwaltung/issues](https://github.com/MLeprich/ff-gerechtigkeitsverwaltung/issues)

---

*Entwickelt mit Unterstützung von Claude Code*
