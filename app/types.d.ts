type Statistics = {
    cpuUsage: number;
    ramUsage: number;
    storageData: number;
}

type StaticData = {
    totalStorage: number;
    cpuModel: string;
    totalMemoryGB: number;
}

type UnsubscribeFunction = () => void;

type EventPayloadMapping = {
    statistics: Statistics;
    getStaticData: StaticData;
    closeWindow: void;
    minimizeWindow: void;
    maximizeWindow: void;
    resizeWindow: boolean;
    toggleDevTools: void;
}

interface Window {
    electron: {
        subscribeStatistics: (callback: (statistics: Statistics) => void) => UnsubscribeFunction;
        subscribeWindowResize: (callback: (isMaximized: boolean) => void) => UnsubscribeFunction;
        getStaticData: () => Promise<StaticData>;
        closeWindow: () => void;
        minimizeWindow: () => void;
        maximizeWindow: () => void;
        toggleDevTools: () => void;
    }
}
