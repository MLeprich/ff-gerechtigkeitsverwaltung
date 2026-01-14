#!/bin/bash
# FF Feuerwehr-Fairness - Setup Script

set -e

echo "========================================"
echo "FF Feuerwehr-Fairness - Setup"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 ist nicht installiert!"
    echo "Bitte installieren Sie Python 3.10 oder höher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python Version: $PYTHON_VERSION"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js ist nicht installiert!"
    echo "Bitte installieren Sie Node.js 18 oder höher."
    exit 1
fi

NODE_VERSION=$(node -v)
echo "Node.js Version: $NODE_VERSION"

echo ""
echo "1. Python Virtual Environment erstellen..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   Virtual Environment erstellt."
else
    echo "   Virtual Environment existiert bereits."
fi

echo ""
echo "2. Python Dependencies installieren..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "   Python Dependencies installiert."

echo ""
echo "3. Node.js Dependencies installieren..."
npm install
echo "   Node.js Dependencies installiert."

echo ""
echo "4. Datenbank initialisieren..."
python manage.py migrate
echo "   Datenbank initialisiert."

echo ""
echo "5. Statische Dateien sammeln..."
python manage.py collectstatic --noinput
echo "   Statische Dateien gesammelt."

echo ""
echo "========================================"
echo "Setup abgeschlossen!"
echo "========================================"
echo ""
echo "Nächste Schritte:"
echo ""
echo "  1. Admin-Benutzer erstellen:"
echo "     python manage.py createsuperuser"
echo ""
echo "  2. App starten:"
echo "     npm start"
echo ""
echo "  3. Oder nur Django starten (zum Testen):"
echo "     python manage.py runserver"
echo ""
