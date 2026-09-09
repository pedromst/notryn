const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const PORT = 4783;
let window = null;
let quitting = false;

app.setName('Notryn');
app.setPath('userData', path.join(app.getPath('appData'), 'Notryn', 'desktop-shell'));

function stateDirectory() {
  if (process.platform === 'darwin') {
    return path.join(app.getPath('home'), 'Library', 'Application Support', 'Notryn');
  }
  if (process.platform === 'win32') {
    return path.join(process.env.LOCALAPPDATA || app.getPath('userData'), 'Notryn');
  }
  return path.join(process.env.XDG_DATA_HOME || path.join(app.getPath('home'), '.local', 'share'), 'notryn');
}

function sidecar() {
  const name = process.platform === 'win32' ? 'notryn.exe' : 'notryn';
  return path.join(process.resourcesPath, 'notryn', name);
}

function command(args) {
  return spawnSync(sidecar(), args, {
    encoding: 'utf8',
    timeout: 15000,
    env: { ...process.env, NOTRYN_HOME: stateDirectory() },
  });
}

function startServer() {
  const result = command(['start', '--port', String(PORT), '--data-dir', stateDirectory()]);
  if (result.error || result.status !== 0) {
    const detail = (result.stderr || result.stdout || result.error?.message || '').trim();
    throw new Error(detail || 'The private local server could not start.');
  }
}

function stopServer() {
  command(['stop', '--data-dir', stateDirectory()]);
}

function createWindow() {
  window = new BrowserWindow({
    title: 'notryn',
    width: 1500,
    height: 940,
    // Let tiling window managers reach the existing compact layout (<= 900px).
    minWidth: 320,
    minHeight: 320,
    backgroundColor: '#071018',
    autoHideMenuBar: true,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: false,
    },
  });
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url) && !url.startsWith(`http://127.0.0.1:${PORT}`)) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(`http://127.0.0.1:${PORT}/`)) event.preventDefault();
  });
  window.loadURL(`http://127.0.0.1:${PORT}/`);
  window.on('closed', () => { window = null; });
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (window) {
      if (window.isMinimized()) window.restore();
      window.focus();
    }
  });
  app.whenReady().then(() => {
    try {
      startServer();
      createWindow();
    } catch (error) {
      dialog.showErrorBox('Notryn could not open', error.message);
      app.quit();
    }
  });
  app.on('activate', () => { if (!window) createWindow(); });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', () => {
    if (!quitting) {
      quitting = true;
      stopServer();
    }
  });
}
