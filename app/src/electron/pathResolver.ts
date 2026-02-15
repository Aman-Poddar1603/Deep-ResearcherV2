import { isDev } from "./util.js"
import path from "path"
import { app } from "electron"


export function getPreloadPath() {
    return path.join(
        app.getAppPath(),
        '/dist-electron/preload.js'
    )
}

export function getUIPath() {
    return path.join(app.getAppPath(), '/dist-react/index.html');
}

export function getIconPath() {
    if (isDev()) {
        return path.join(app.getAppPath(), 'public/brand/inner_logo_dr_light.png');
    }
    return path.join(
        path.dirname(app.getAppPath()),
        'brand/inner_logo_dr_light.png'
    );
}