const { app, BrowserWindow, Menu, shell, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const log = require('electron-log');
const Store = require('electron-store');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

// Store for app settings
const store = new Store({
    defaults: {
        windowBounds: { width: 1400, height: 900 },
        pythonPath: 'python'
    }
});

// Global references
let mainWindow = null;
let djangoProcess = null;
const DJANGO_PORT = 8000;
const DJANGO_HOST = '127.0.0.1';
const DJANGO_URL = `http://${DJANGO_HOST}:${DJANGO_PORT}`;

// Get shared data path (ProgramData on Windows, /var/lib on Linux, /Library on macOS)
function getSharedDataPath() {
    const appName = 'FF-Feuerwehr-Fairness';
    let basePath;

    if (process.platform === 'win32') {
        // Windows: Use ProgramData for shared access
        basePath = process.env.PROGRAMDATA || 'C:\\ProgramData';
    } else if (process.platform === 'darwin') {
        // macOS: Use /Users/Shared
        basePath = '/Users/Shared';
    } else {
        // Linux: Use /var/lib or fallback to home
        basePath = fs.existsSync('/var/lib') ? '/var/lib' : app.getPath('userData');
    }

    const sharedPath = path.join(basePath, appName);

    // Ensure directory exists
    try {
        if (!fs.existsSync(sharedPath)) {
            fs.mkdirSync(sharedPath, { recursive: true, mode: 0o777 });
        }
    } catch (err) {
        log.warn(`Could not create shared path ${sharedPath}, falling back to user data`);
        return app.getPath('userData');
    }

    return sharedPath;
}

// Get database path
function getDatabasePath() {
    return path.join(getSharedDataPath(), 'ff_database.sqlite3');
}

// Get the Django app path (works in both dev and production)
function getDjangoPath() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, 'django');
    }
    return path.dirname(__dirname);
}

// Find Python executable
function getPythonPath() {
    const fs = require('fs');

    // Check for custom path in settings
    const customPath = store.get('pythonPath');
    if (customPath && customPath !== 'python') {
        return customPath;
    }

    // In packaged app, use bundled Python
    if (app.isPackaged) {
        const bundledPython = path.join(process.resourcesPath, 'python', 'python.exe');
        try {
            fs.accessSync(bundledPython);
            log.info(`Using bundled Python: ${bundledPython}`);
            return bundledPython;
        } catch {
            log.warn('Bundled Python not found, falling back to system Python');
        }
    }

    // In development, check for venv
    const appPath = getDjangoPath();
    const venvPython = process.platform === 'win32'
        ? path.join(appPath, 'venv', 'Scripts', 'python.exe')
        : path.join(appPath, 'venv', 'bin', 'python');

    try {
        fs.accessSync(venvPython);
        return venvPython;
    } catch {
        return process.platform === 'win32' ? 'python' : 'python3';
    }
}

// Start Django server
function startDjango() {
    return new Promise((resolve, reject) => {
        const djangoPath = getDjangoPath();
        const pythonPath = getPythonPath();
        const managePath = path.join(djangoPath, 'manage.py');

        log.info(`Starting Django from: ${djangoPath}`);
        log.info(`Python path: ${pythonPath}`);
        log.info(`Manage.py path: ${managePath}`);

        // Set environment variables
        const dbPath = getDatabasePath();
        const env = {
            ...process.env,
            ELECTRON_MODE: 'true',
            DEBUG: process.env.DEBUG || 'false',
            PYTHONUNBUFFERED: '1',
            FF_DATABASE_PATH: dbPath
        };

        log.info(`Database path: ${dbPath} (shared for all users)`);

        // First run migrations
        const migrateProcess = spawn(pythonPath, [managePath, 'migrate', '--run-syncdb'], {
            cwd: djangoPath,
            env: env,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        migrateProcess.stdout.on('data', (data) => {
            log.info(`[migrate] ${data.toString().trim()}`);
        });

        migrateProcess.stderr.on('data', (data) => {
            log.warn(`[migrate] ${data.toString().trim()}`);
        });

        migrateProcess.on('close', (code) => {
            if (code !== 0) {
                log.error(`Migration failed with code ${code}`);
            }

            // Start Django server
            djangoProcess = spawn(pythonPath, [
                managePath,
                'runserver',
                '--noreload',
                `${DJANGO_HOST}:${DJANGO_PORT}`
            ], {
                cwd: djangoPath,
                env: env,
                stdio: ['pipe', 'pipe', 'pipe']
            });

            djangoProcess.stdout.on('data', (data) => {
                const output = data.toString();
                log.info(`[Django] ${output.trim()}`);

                // Check if server is ready
                if (output.includes('Starting development server')) {
                    resolve();
                }
            });

            djangoProcess.stderr.on('data', (data) => {
                const output = data.toString();
                // Django logs to stderr by default
                if (output.includes('Starting development server')) {
                    log.info('[Django] Server started');
                    resolve();
                } else if (output.includes('Error') || output.includes('Exception')) {
                    log.error(`[Django] ${output.trim()}`);
                } else {
                    log.info(`[Django] ${output.trim()}`);
                }
            });

            djangoProcess.on('error', (err) => {
                log.error('Failed to start Django:', err);
                reject(err);
            });

            djangoProcess.on('close', (code) => {
                log.info(`Django process exited with code ${code}`);
                djangoProcess = null;
            });

            // Timeout for server startup
            setTimeout(() => {
                resolve(); // Resolve anyway after timeout
            }, 10000);
        });
    });
}

// Wait for Django to be ready
function waitForDjango(maxAttempts = 30) {
    return new Promise((resolve, reject) => {
        let attempts = 0;

        const check = () => {
            attempts++;

            const req = http.get(`${DJANGO_URL}/`, (res) => {
                log.info(`Django responded with status: ${res.statusCode}`);
                resolve();
            });

            req.on('error', (err) => {
                if (attempts < maxAttempts) {
                    log.debug(`Waiting for Django... (attempt ${attempts})`);
                    setTimeout(check, 500);
                } else {
                    reject(new Error('Django server did not start in time'));
                }
            });

            req.setTimeout(1000, () => {
                req.destroy();
                if (attempts < maxAttempts) {
                    setTimeout(check, 500);
                }
            });
        };

        check();
    });
}

// Stop Django server
function stopDjango() {
    if (djangoProcess) {
        log.info('Stopping Django server...');

        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', djangoProcess.pid, '/f', '/t']);
        } else {
            djangoProcess.kill('SIGTERM');
            setTimeout(() => {
                if (djangoProcess) {
                    djangoProcess.kill('SIGKILL');
                }
            }, 5000);
        }

        djangoProcess = null;
    }
}

// Create main window
function createWindow() {
    const { width, height } = store.get('windowBounds');

    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        minWidth: 1024,
        minHeight: 700,
        title: 'FF Feuerwehr-Fairness',
        icon: path.join(__dirname, '..', 'build', 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        show: false
    });

    // Save window size on resize
    mainWindow.on('resize', () => {
        const { width, height } = mainWindow.getBounds();
        store.set('windowBounds', { width, height });
    });

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Handle external links
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    // Load Django URL
    mainWindow.loadURL(DJANGO_URL);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Create application menu
function createMenu() {
    const template = [
        {
            label: 'Datei',
            submenu: [
                {
                    label: 'Datenbank-Pfad öffnen',
                    click: () => {
                        shell.showItemInFolder(getDatabasePath());
                    }
                },
                { type: 'separator' },
                {
                    label: 'Beenden',
                    accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Alt+F4',
                    click: () => app.quit()
                }
            ]
        },
        {
            label: 'Bearbeiten',
            submenu: [
                { label: 'Rückgängig', accelerator: 'CmdOrCtrl+Z', role: 'undo' },
                { label: 'Wiederholen', accelerator: 'Shift+CmdOrCtrl+Z', role: 'redo' },
                { type: 'separator' },
                { label: 'Ausschneiden', accelerator: 'CmdOrCtrl+X', role: 'cut' },
                { label: 'Kopieren', accelerator: 'CmdOrCtrl+C', role: 'copy' },
                { label: 'Einfügen', accelerator: 'CmdOrCtrl+V', role: 'paste' },
                { label: 'Alles auswählen', accelerator: 'CmdOrCtrl+A', role: 'selectAll' }
            ]
        },
        {
            label: 'Ansicht',
            submenu: [
                { label: 'Neu laden', accelerator: 'CmdOrCtrl+R', role: 'reload' },
                { label: 'Vollbild', accelerator: 'F11', role: 'togglefullscreen' },
                { type: 'separator' },
                { label: 'Vergrößern', accelerator: 'CmdOrCtrl+Plus', role: 'zoomIn' },
                { label: 'Verkleinern', accelerator: 'CmdOrCtrl+-', role: 'zoomOut' },
                { label: 'Zurücksetzen', accelerator: 'CmdOrCtrl+0', role: 'resetZoom' },
                { type: 'separator' },
                { label: 'Entwicklertools', accelerator: 'F12', role: 'toggleDevTools' }
            ]
        },
        {
            label: 'Hilfe',
            submenu: [
                {
                    label: 'Über FF Feuerwehr-Fairness',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'Über FF Feuerwehr-Fairness',
                            message: 'FF Feuerwehr-Fairness',
                            detail: `Version: ${app.getVersion()}\n\nDienstplan und Einteilungsverwaltung für Freiwillige Feuerwehren.\n\nDatenbank (gemeinsam): ${getDatabasePath()}`
                        });
                    }
                },
                {
                    label: 'Log-Datei öffnen',
                    click: () => {
                        shell.openPath(log.transports.file.getFile().path);
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

// App ready
app.whenReady().then(async () => {
    log.info('='.repeat(50));
    log.info('FF Feuerwehr-Fairness starting...');
    log.info(`App version: ${app.getVersion()}`);
    log.info(`Electron version: ${process.versions.electron}`);
    log.info(`Shared data path: ${getSharedDataPath()}`);
    log.info(`Database path: ${getDatabasePath()}`);
    log.info('='.repeat(50));

    createMenu();

    try {
        // Start Django
        await startDjango();
        log.info('Django process started, waiting for server...');

        // Wait for Django to be ready
        await waitForDjango();
        log.info('Django server is ready!');

        // Create window
        createWindow();

    } catch (error) {
        log.error('Failed to start application:', error);
        dialog.showErrorBox(
            'Startfehler',
            `Die Anwendung konnte nicht gestartet werden.\n\nFehler: ${error.message}\n\nBitte stellen Sie sicher, dass Python installiert ist.`
        );
        app.quit();
    }
});

// Handle window activation (macOS)
app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

// Cleanup before quit
app.on('before-quit', () => {
    log.info('Application quitting...');
    stopDjango();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    log.error('Uncaught exception:', error);
    stopDjango();
});
