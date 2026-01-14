@echo off
REM FF Feuerwehr-Fairness - Setup Script (Windows)

echo ========================================
echo FF Feuerwehr-Fairness - Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python ist nicht installiert!
    echo Bitte installieren Sie Python 3.10 oder hoeher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Python Version: %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js ist nicht installiert!
    echo Bitte installieren Sie Node.js 18 oder hoeher.
    pause
    exit /b 1
)

for /f %%i in ('node -v') do set NODE_VERSION=%%i
echo Node.js Version: %NODE_VERSION%

echo.
echo 1. Python Virtual Environment erstellen...
if not exist "venv" (
    python -m venv venv
    echo    Virtual Environment erstellt.
) else (
    echo    Virtual Environment existiert bereits.
)

echo.
echo 2. Python Dependencies installieren...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo    Python Dependencies installiert.

echo.
echo 3. Node.js Dependencies installieren...
call npm install
echo    Node.js Dependencies installiert.

echo.
echo 4. Datenbank initialisieren...
python manage.py migrate
echo    Datenbank initialisiert.

echo.
echo 5. Statische Dateien sammeln...
python manage.py collectstatic --noinput
echo    Statische Dateien gesammelt.

echo.
echo ========================================
echo Setup abgeschlossen!
echo ========================================
echo.
echo Naechste Schritte:
echo.
echo   1. Admin-Benutzer erstellen:
echo      python manage.py createsuperuser
echo.
echo   2. App starten:
echo      npm start
echo.
echo   3. Oder nur Django starten (zum Testen):
echo      python manage.py runserver
echo.
pause
