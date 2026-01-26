import electron from "electron";

electron.contextBridge.exposeInMainWorld("electron", {
    subscribeStatistics: (callback) =>
        ipcOn("statistics", stats => {
            callback(stats);
        }),
    getStaticData: () => ipcInvoke("getStaticData"),
    closeWindow: () => ipcSend("closeWindow"),
    minimizeWindow: () => ipcSend("minimizeWindow"),
    maximizeWindow: () => ipcSend("maximizeWindow"),
    toggleDevTools: () => ipcSend("toggleDevTools"),
} satisfies Window['electron'])

function ipcSend<Key extends keyof EventPayloadMapping>(key: Key) {
    electron.ipcRenderer.send(key);
}

function ipcInvoke<Key extends keyof EventPayloadMapping>(key: Key): Promise<EventPayloadMapping[Key]> {
    return electron.ipcRenderer.invoke(key);
}

function ipcOn<Key extends keyof EventPayloadMapping>(key: Key, callback: (payload: EventPayloadMapping[Key]) => void) {
    const cb = (_: Electron.IpcRendererEvent, payload: any) => callback(payload)
    electron.ipcRenderer.on(key, cb);
    return () => electron.ipcRenderer.off(key, cb)
}
