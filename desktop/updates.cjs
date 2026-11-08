// Electron owns package updates. The renderer receives status and fixed actions only.
function createUpdateController({ updater, packaged, version, readSettings, beforeInstall = () => {} }) {
  let state = { state: packaged ? 'idle' : 'development', currentVersion: version, availableVersion: null, progress: null, error: null, lastChecked: null, automatic: true };
  let checking = false;
  const patch = values => { state = { ...state, ...values }; };
  if (packaged) {
    updater.autoDownload = true;
    updater.autoInstallOnAppQuit = true;
    updater.allowPrerelease = false;
    updater.allowDowngrade = false;
    updater.on('checking-for-update', () => patch({ state: 'checking', error: null }));
    updater.on('update-available', info => patch({ state: 'downloading', availableVersion: info.version, error: null }));
    updater.on('update-not-available', () => { if (state.state !== 'downloaded') patch({ state: 'up to date', error: null }); });
    updater.on('download-progress', info => patch({ state: 'downloading', progress: Math.max(0, Math.min(100, Number(info.percent) || 0)) }));
    updater.on('update-downloaded', info => patch({ state: 'downloaded', availableVersion: info.version, progress: 100, error: null }));
    updater.on('error', error => patch({ state: 'error', error: String(error.message || error).slice(0, 400) }));
  }
  async function preferences() {
    try {
      const settings = await readSettings();
      patch({ automatic: settings.auto_app_updates !== false, error: null });
      if (packaged) updater.autoInstallOnAppQuit = state.automatic;
    } catch (error) { patch({ error: String(error.message || error).slice(0, 400) }); }
    return { ...state };
  }
  async function check(manual = false) {
    if (!packaged || checking || state.state === 'downloading' || state.state === 'downloaded') return { ...state };
    await preferences();
    if (state.error) { patch({ state: 'error' }); return { ...state }; }
    if (!manual && !state.automatic) { patch({ state: 'paused' }); return { ...state }; }
    checking = true;
    patch({ state: 'checking', error: null, lastChecked: new Date().toISOString() });
    try { await updater.checkForUpdates(); }
    catch (error) { patch({ state: 'error', error: String(error.message || error).slice(0, 400) }); }
    finally { checking = false; }
    return { ...state };
  }
  async function install() {
    if (!packaged || state.state !== 'downloaded') throw new Error('No verified desktop update is ready to install');
    await beforeInstall();
    patch({ state: 'installing' });
    updater.quitAndInstall(false, true);
    return { ...state };
  }
  return { status: () => ({ ...state }), check, install, preferences };
}
module.exports = { createUpdateController };
