const {
  app,
  BrowserWindow,
  dialog,
  session,
  shell,
  ipcMain,
  clipboard,
} = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");
let backend,
  win,
  exiting = false;
// Electron 38+ selects native Wayland on Plasma when available; no sandbox bypasses.
app.setName("WoW LazyCrawler");
app.setDesktopName("wowlazycrawler.desktop");
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.show();
      win.focus();
    }
  });
  app
    .whenReady()
    .then(start)
    .catch((error) => {
      dialog.showErrorBox(
        "LazyCrawler could not start",
        error.message + "\nSee backend.log in the application data folder.",
      );
      app.quit();
    });
}
async function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}
async function start() {
  // Stable Linux XDG path, independent of app version and install directory.
  const data =
    process.env.LAZYCRAWLER_DATA ||
    path.join(
      process.env.XDG_DATA_HOME ||
        path.join(app.getPath("home"), ".local", "share"),
      "wowlazycrawler",
    );
  fs.mkdirSync(data, { recursive: true, mode: 0o700 });
  let existing;
  try {
    const record = JSON.parse(
      fs.readFileSync(path.join(data, "runtime.json"), "utf8"),
    );
    if (
      Number.isInteger(record.port) &&
      record.port > 0 &&
      record.port < 65536 &&
      Number.isInteger(record.pid)
    ) {
      process.kill(record.pid, 0);
      const result = await fetch(`http://127.0.0.1:${record.port}/api/health`, {
        signal: AbortSignal.timeout(1000),
      });
      if (result.ok && (await result.json()).version === "0.4.0")
        existing = record;
    }
  } catch {}
  const port = existing ? existing.port : await freePort();
  const url = `http://127.0.0.1:${port}`;
  const root = path.join(__dirname, "..");
  const binary = app.isPackaged
    ? path.join(process.resourcesPath, "backend", "lazycrawler-server")
    : path.join(root, ".venv", "bin", "python");
  const args = app.isPackaged ? [] : [path.join(root, "server_entry.py")];
  if (!existing) {
    const logPath = path.join(data, "backend.log");
    if (fs.existsSync(logPath) && fs.statSync(logPath).size > 5 * 1024 * 1024)
      fs.renameSync(logPath, logPath + ".old");
    const log = fs.openSync(logPath, "a", 0o600);
    backend = spawn(binary, [...args, "--port", String(port), "--data", data], {
      stdio: ["ignore", log, log],
      env: { ...process.env, LAZYCRAWLER_DATA: data },
      cwd: app.isPackaged ? data : root,
    });
    fs.closeSync(log);
  }
  let failed;
  backend?.once("error", (e) => (failed = e));
  backend?.once("exit", (code) => {
    failed = new Error(`Backend exited (${code}).`);
    if (win && !exiting) {
      dialog.showErrorBox(
        "Backend stopped",
        "Restart LazyCrawler. Details are in backend.log.",
      );
      app.quit();
    }
  });
  let ready = false;
  for (let i = 0; i < 150; i++) {
    if (failed) throw failed;
    try {
      const r = await fetch(url + "/api/health", {
        signal: AbortSignal.timeout(1000),
      });
      if (r.ok) {
        ready = true;
        break;
      }
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  if (!ready)
    throw new Error(
      "The local backend did not become ready within 30 seconds.",
    );
  const token = fs.readFileSync(path.join(data, "admin-token"), "utf8").trim();
  const response = await fetch(url + "/api/login", {
    signal: AbortSignal.timeout(5000),
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!response.ok)
    throw new Error("Unable to authenticate with local backend.");
  let cookie = response.headers
    .get("set-cookie")
    ?.match(/lc_session=([^;]+)/)?.[1];
  if (!cookie) throw new Error("Backend did not supply a session.");
  await session.defaultSession.cookies.set({
    url,
    name: "lc_session",
    value: cookie,
    httpOnly: true,
    sameSite: "strict",
  });
  win = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 860,
    minHeight: 640,
    backgroundColor: "#101615",
    autoHideMenuBar: true,
    title: "WoW LazyCrawler",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  ipcMain.handle("lazycrawler:choose-wow-folder", async (event) => {
    if (
      event.sender !== win.webContents ||
      new URL(event.sender.getURL()).origin !== url
    )
      throw new Error("Untrusted window");
    const result = await dialog.showOpenDialog(win, {
      title: "Choose World of Warcraft Retail folder",
      properties: ["openDirectory"],
    });
    return result.canceled ? null : result.filePaths[0];
  });
  win.webContents.setWindowOpenHandler(({ url: target }) => {
    if (
      /^https:\/\/(community\.developer\.battle\.net|tradeskillmaster\.com|github\.com)\//.test(
        target,
      )
    )
      shell.openExternal(target);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, target) => {
    if (new URL(target).origin !== url) event.preventDefault();
  });
  const { createUpdateController } = require("./updates.cjs");
  const updateLibrary = app.isPackaged ? require("electron-updater") : null;
  const updater = updateLibrary ? (process.env.APPIMAGE ? new updateLibrary.AppImageUpdater() : updateLibrary.autoUpdater) : null;
  async function backendRequest(route, options = {}) {
      const read = () => fetch(url + "/api/" + route, { ...options, headers: { ...options.headers, Cookie: `lc_session=${cookie}` }, signal: AbortSignal.timeout(30000) });
      let result = await read();
      if (result.status === 401) {
        const login = await fetch(url + "/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }), signal: AbortSignal.timeout(5000) });
        const renewed = login.headers.get("set-cookie")?.match(/lc_session=([^;]+)/)?.[1];
        if (login.ok && renewed) {
          cookie = renewed;
          await session.defaultSession.cookies.set({url, name:"lc_session", value:cookie, httpOnly:true, sameSite:"strict"});
          result = await read();
        }
      }
      if (!result.ok) throw new Error(`Local service request failed (${result.status})`);
      return result.json();

  }
  const updates = createUpdateController({
    updater, packaged: app.isPackaged, version: app.getVersion(),
    readSettings: () => backendRequest("settings"),
  });
  const trusted = event => {
    if (event.sender !== win.webContents || new URL(event.sender.getURL()).origin !== url) throw new Error("Untrusted window");
  };
  ipcMain.handle("lazycrawler:copy-market-data", async event => {
    trusted(event);const plan = await backendRequest("addon/plan");
    const text = "LC1:" + JSON.stringify(plan);
    if (Buffer.byteLength(text, "utf8") > 4 * 1024 * 1024) throw new Error("Market bundle exceeds the 4 MB live import limit");
    clipboard.writeText(text);return { generatedAt: plan.generated_at, candidates: plan.opportunities.length };
  });
  ipcMain.handle("lazycrawler:import-character-capture", async event => {
    trusted(event);const text = clipboard.readText();
    if (!text.startsWith("LC_CAPTURE1:") || Buffer.byteLength(text,"utf8") > 4 * 1024 * 1024 + 20) throw new Error("Copy a LazyCrawler character capture with /lc export first");
    let capture;try { capture = JSON.parse(text.slice(12)); } catch { throw new Error("Clipboard capture is not valid JSON"); }
    if (capture?.schema_version !== 2 || typeof capture.account_id !== "string" || !capture.characters) throw new Error("Clipboard does not contain a supported LazyCrawler capture");
    return backendRequest("addon/snapshot", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(capture)});
  });
  ipcMain.handle("lazycrawler:update-status", event => { trusted(event); return updates.status(); });
  ipcMain.handle("lazycrawler:check-updates", event => { trusted(event); return updates.check(true); });
  ipcMain.handle("lazycrawler:update-preferences", event => { trusted(event); return updates.preferences(); });
  ipcMain.handle("lazycrawler:install-update", event => { trusted(event); return updates.install(); });
  await win.loadURL(url);
  const check = () => updates.check().catch(error => console.error("Update check:", error.message));
  void check();
  const updateTimer = setInterval(check, 60 * 60 * 1000);
  updateTimer.unref();
}
app.on("window-all-closed", () => app.quit());
app.on("before-quit", event => {
  exiting = true;
  if (!backend) return;
  event.preventDefault();
  const child = backend;backend = null;
  let finished = false;
  const done = () => { if (finished) return;finished = true;clearTimeout(timeout);app.quit(); };
  const timeout = setTimeout(() => { child.kill("SIGKILL");done(); }, 8000);
  child.once("exit", done);child.kill("SIGTERM");
});
