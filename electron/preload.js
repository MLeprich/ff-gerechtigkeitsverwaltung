/**
 * Preload script for Electron
 * Exposes limited APIs to the renderer process
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // App info
    getVersion: () => ipcRenderer.invoke('get-version'),
    getPlatform: () => process.platform,

    // Window controls
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close'),

    // File dialogs
    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),
    showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),

    // Notifications
    showNotification: (title, body) => ipcRenderer.send('show-notification', { title, body }),

    // Check if running in Electron
    isElectron: true
});

// Add custom styles for Electron environment
window.addEventListener('DOMContentLoaded', () => {
    // Add class to body for Electron-specific styling
    document.body.classList.add('electron-app');

    // Disable context menu on right-click (optional)
    // document.addEventListener('contextmenu', (e) => e.preventDefault());
});
