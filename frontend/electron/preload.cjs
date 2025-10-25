const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("reflow", {
  version: "0.1.0",
});
