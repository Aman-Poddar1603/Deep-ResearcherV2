import { app, BrowserWindow, ipcMain } from "electron"
import { ipcMainHandle, isDev, ipcWebContentsSend } from "./util.js";
import { getPreloadPath, getUIPath, getIconPath } from "./pathResolver.js";
import { getStaticData, pollResources } from "./test.js";
import dotenv from "dotenv";

dotenv.config();

app.on("ready", () => {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 900,
        minWidth: 1200,
        minHeight: 900,
        // Shouldn't add contextIsolate or nodeIntegration because of security vulnerabilities
        webPreferences: {
            preload: getPreloadPath(),
            webSecurity: true,
            allowRunningInsecureContent: false, // Explicitly disable insecure content execution
        },
        icon: getIconPath(),
        frame: false,
    });

    mainWindow.maximize();

    if (isDev()) {
        const PORT = process.env.PORT || '3000'; // Default to 3000 if not set
        mainWindow.loadURL(`http://localhost:${PORT}`);
        // Automaticaly open DevTools on start (removable/closable)
        mainWindow.webContents.openDevTools();
    } else {
        mainWindow.loadFile(getUIPath());
    }

    pollResources(mainWindow);

    ipcMainHandle("getStaticData", () => {
        return getStaticData();
    });

    ipcMain.on("closeWindow", () => {
        mainWindow.close();
    });

    ipcMain.on("minimizeWindow", () => {
        mainWindow.minimize();
    });

    ipcMain.on("maximizeWindow", () => {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    });

    ipcMain.on("toggleDevTools", () => {
        mainWindow.webContents.toggleDevTools();
    });

    ipcMainHandle("getZoomLevel", () => {
        return mainWindow.webContents.zoomLevel;
    });

    ipcMain.on("zoomIn", () => {
        const newZoom = Math.min(mainWindow.webContents.zoomLevel + 0.1, 3);
        mainWindow.webContents.zoomLevel = newZoom;
        ipcWebContentsSend("zoomLevelChanged", mainWindow.webContents, newZoom);
    });

    ipcMain.on("zoomOut", () => {
        const newZoom = Math.max(mainWindow.webContents.zoomLevel + (-0.1), 1.0);
        mainWindow.webContents.zoomLevel = newZoom;
        ipcWebContentsSend("zoomLevelChanged", mainWindow.webContents, newZoom);
    });

    ipcMain.on("resetZoom", () => {
        mainWindow.webContents.zoomLevel = 0;
        ipcWebContentsSend("zoomLevelChanged", mainWindow.webContents, 0);
    });

    mainWindow.webContents.on('before-input-event', (_, input) => {
        if (input.type === 'keyDown' && input.key === 'F5') {
            mainWindow.webContents.reload();
        }
    });

    mainWindow.on('maximize', () => ipcWebContentsSend('resizeWindow', mainWindow.webContents, true));
    mainWindow.on('unmaximize', () => ipcWebContentsSend('resizeWindow', mainWindow.webContents, false));
})
