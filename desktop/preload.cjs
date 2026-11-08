const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld(
  "lazyCrawler",
  Object.freeze({
    chooseWowFolder: () => ipcRenderer.invoke("lazycrawler:choose-wow-folder"),
  }),
);
