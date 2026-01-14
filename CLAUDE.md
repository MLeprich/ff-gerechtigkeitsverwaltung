# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FF (Feuerwehr-Fairness) Electron App - A desktop application wrapping the Django web application for managing volunteer fire department scheduling. Uses SQLite for local data storage and Electron for cross-platform desktop deployment.

## Development Commands

```bash
# === Python Setup ===
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# === Node.js Setup ===
npm install

# === Database ===
python manage.py migrate
python manage.py createsuperuser

# === Run App ===
npm start              # Start Electron app
npm run start:dev      # Start with debug mode
python manage.py runserver  # Django only (for debugging)

# === Build ===
npm run build:win      # Windows installer
npm run build:mac      # macOS DMG
npm run build:linux    # Linux AppImage/deb

# === Tests ===
python manage.py test
python manage.py test apps.core  # Single app
```

## Architecture

### Electron Layer (`electron/`)

- **main.js**: Main process - spawns Django as subprocess, creates BrowserWindow, handles app lifecycle
- **preload.js**: Exposes limited IPC APIs to renderer (contextBridge)
- Django runs on `localhost:8000`, Electron loads this URL in BrowserWindow

### Django Backend

Uses SQLite database stored in user data directory:
- Windows: `%APPDATA%/ff-feuerwehr-fairness/ff_database.sqlite3`
- macOS: `~/Library/Application Support/ff-feuerwehr-fairness/`
- Linux: `~/.config/ff-feuerwehr-fairness/`

### Django Apps (`apps/`)

- **core**: Custom User model with roles, Settings singleton, AuditLog
- **members**: Member/Unit management, availability tracking
- **vehicles**: Fleet management, Position definitions, VehiclePosition with qualification rules
- **qualifications**: Training records (TM1, TF, GF, AGT), MedicalExam (G26.3), ExerciseRecord
- **scheduling**: Duty planning, Assignment, FairnessScore, AssignmentHistory

### Key Files

| File | Purpose |
|------|---------|
| `electron/main.js` | Electron main process, Django subprocess management |
| `config/settings.py` | Django settings (SQLite, no .env needed) |
| `package.json` | Electron dependencies, build config |
| `requirements.txt` | Python dependencies (no psycopg2) |

### Frontend Stack

- Tailwind CSS (browser runtime)
- Alpine.js (minimal client state)
- HTMX (loaded but mostly unused)
- Templates in `/templates/` with `base.html` layout

## Key Differences from Web Version

| Aspect | Web Version | Electron Version |
|--------|-------------|------------------|
| Database | PostgreSQL | SQLite |
| Server | Gunicorn/Nginx | Django dev server |
| Config | .env file | Hardcoded in settings.py |
| Auth | Session cookies | Same (local only) |
| SSL | Required | Not needed |

## Domain Concepts

- **AGT**: Respiratory protection (G26.3 medical + annual exercises)
- **Positions**: GF, MA, ATF/ATM, WTF/WTM, STF/STM, ME
- **Qualification hierarchy**: ZF > GF > TF > TM

## Troubleshooting

```bash
# Check Django logs
cat logs/ff_app.log

# Test Django standalone
python manage.py runserver

# Reset database
rm data/ff_database.sqlite3
python manage.py migrate
python manage.py createsuperuser
```
