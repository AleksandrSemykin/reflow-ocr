const { app, BrowserWindow, shell } = require("electron");
const path = require("node:path");
const { fileURLToPath } = require("node:url");

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);

const resolvePath = (...segments) => {
  const dirname = path.dirname(fileURLToPath(__filename));
  return path.join(dirname, "..", ...segments);
};

const createWindow = async () => {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: resolvePath("electron", "preload.cjs"),
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    await win.loadURL(process.env.VITE_DEV_SERVER_URL);
    win.webContents.openDevTools();
  } else {
    await win.loadFile(resolvePath("dist", "index.html"));
  }
};

app.whenReady().then(() => {
  createWindow().catch((error) => {
    console.error("Failed to create window", error);
    app.quit();
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
