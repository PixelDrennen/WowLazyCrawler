const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld(
  "lazyCrawler",
  Object.freeze({
    refreshUpdatePreferences: () => ipcRenderer.invoke("lazycrawler:update-preferences"),
    copyMarketData: () => ipcRenderer.invoke("lazycrawler:copy-market-data"),
    importCharacterCapture: () => ipcRenderer.invoke("lazycrawler:import-character-capture"),
    updateStatus: () => ipcRenderer.invoke("lazycrawler:update-status"),
    checkUpdates: () => ipcRenderer.invoke("lazycrawler:check-updates"),
    installUpdate: () => ipcRenderer.invoke("lazycrawler:install-update"),
    chooseWowFolder: () => ipcRenderer.invoke("lazycrawler:choose-wow-folder"),
  }),
);
