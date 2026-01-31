import { app, BrowserWindow, ipcMain } from "electron"
import { ipcMainHandle, isDev, ipcWebContentsSend } from "./util.js";
import { getPreloadPath, getUIPath, getIconPath } from "./pathResolver.js";
import { getStaticData, pollResources } from "./test.js";
import dotenv from "dotenv";

dotenv.config();

const PORT = process.env.PORT;
if (!PORT) throw new Error("PORT env variable is not set");

app.on("ready", () => {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 900,
        minWidth: 1200,
        minHeight: 900,
        // Shouldn't add contextIsolate or nodeIntegration because of security vulnerabilities
        webPreferences: {
            preload: getPreloadPath(),
        },
        icon: getIconPath(),
        frame: false,
    });

    mainWindow.maximize();

    if (isDev()) mainWindow.loadURL(`http://localhost:${PORT}`)
    else mainWindow.loadFile(getUIPath());

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

    mainWindow.webContents.on('before-input-event', (_, input) => {
        if (input.type === 'keyDown' && input.key === 'F5') {
            mainWindow.webContents.reload();
        }
    });

    mainWindow.on('maximize', () => ipcWebContentsSend('resizeWindow', mainWindow.webContents, true));
    mainWindow.on('unmaximize', () => ipcWebContentsSend('resizeWindow', mainWindow.webContents, false));
})
