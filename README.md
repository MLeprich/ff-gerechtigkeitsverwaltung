# FF Feuerwehr-Fairness - Electron Desktop App

Desktop-Anwendung für die Dienstplan- und Einteilungsverwaltung bei Freiwilligen Feuerwehren.

## Voraussetzungen

- **Node.js** 18+ (für Electron)
- **Python** 3.10+ (für Django Backend)
- **npm** oder **yarn**

## Installation (Entwicklung)

### 1. Python-Umgebung einrichten

```bash
# Virtual Environment erstellen
python -m venv venv

# Aktivieren (Linux/macOS)
source venv/bin/activate

# Aktivieren (Windows)
venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

### 2. Node.js Dependencies installieren

```bash
npm install
```

### 3. Datenbank initialisieren

```bash
# Migrationen ausführen
python manage.py migrate

# Static Files sammeln
python manage.py collectstatic --noinput

# Admin-Benutzer erstellen
python manage.py createsuperuser
```

### 4. App starten

```bash
# Electron App starten
npm start

# Oder mit Debug-Modus
npm run start:dev
```

## Build für Produktion

```bash
# Für Windows
npm run build:win

# Für macOS
npm run build:mac

# Für Linux
npm run build:linux

# Für alle Plattformen
npm run build
```

Die fertigen Installer befinden sich dann im `dist/` Ordner.

## Datenbank

Die App verwendet SQLite als lokale Datenbank. Die Datenbank-Datei wird im Benutzer-Datenverzeichnis gespeichert:

- **Windows**: `%APPDATA%/ff-feuerwehr-fairness/ff_database.sqlite3`
- **macOS**: `~/Library/Application Support/ff-feuerwehr-fairness/ff_database.sqlite3`
- **Linux**: `~/.config/ff-feuerwehr-fairness/ff_database.sqlite3`

## Projektstruktur

```
electron-app/
├── electron/
│   ├── main.js         # Electron Hauptprozess
│   └── preload.js      # Preload-Script für IPC
├── apps/               # Django Apps
├── config/             # Django Konfiguration
├── templates/          # HTML Templates
├── static/             # Statische Dateien
├── build/              # Icons und Build-Ressourcen
├── package.json        # Node.js Dependencies
├── requirements.txt    # Python Dependencies
└── manage.py           # Django Management
```

## Entwicklung

### Django separat starten (ohne Electron)

```bash
source venv/bin/activate
python manage.py runserver
```

Dann im Browser öffnen: http://localhost:8000

### Logs

Electron-Logs befinden sich in:
- **Windows**: `%APPDATA%/ff-feuerwehr-fairness/logs/`
- **macOS**: `~/Library/Logs/ff-feuerwehr-fairness/`
- **Linux**: `~/.config/ff-feuerwehr-fairness/logs/`

## Bekannte Einschränkungen

- Die App benötigt Python auf dem System (nicht gebündelt)
- Beim ersten Start dauert die Initialisierung etwas länger
- Updates müssen manuell installiert werden

## Lizenz

MIT
