import { app, BrowserWindow, ipcMain } from "electron"
import { ipcMainHandle, isDev } from "./util.js";
import { getPreloadPath, getUIPath, getIconPath } from "./pathResolver.js";
import { getStaticData, pollResources } from "./test.js";
import dotenv from "dotenv";

dotenv.config();

const PORT = process.env.PORT;
if (!PORT) throw new Error("PORT env variable is not set");

app.on("ready", () => {
    const mainWindow = new BrowserWindow({
        width: 1800,
        height: 600,
        // Shouldn't add contextIsolate or nodeIntegration because of security vulnerabilities
        webPreferences: {
            preload: getPreloadPath(),
        },
        icon: getIconPath(),
        frame: false,
    });

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
})
