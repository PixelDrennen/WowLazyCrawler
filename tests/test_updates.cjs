const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { createUpdateController } = require('../desktop/updates.cjs');
class Updater extends EventEmitter {
  async checkForUpdates() { this.calls = (this.calls || 0) + 1; this.emit('checking-for-update'); this.emit('update-available', {version:'0.5.0'}); }
  quitAndInstall(...args) { this.installArgs = args; }
}
test('stable desktop updates download, expose progress and require ready state before install', async () => {
  const updater = new Updater(); const controller = createUpdateController({updater,packaged:true,version:'0.4.0',readSettings:async()=>({auto_app_updates:true})});
  await assert.rejects(controller.install(), /No verified/);
  await controller.check(); assert.equal(updater.calls,1);assert.equal(updater.autoDownload,true);assert.equal(updater.allowDowngrade,false);
  updater.emit('download-progress',{percent:42});assert.equal(controller.status().progress,42);
  updater.emit('update-downloaded',{version:'0.5.0'});await controller.check();assert.equal(updater.calls,1);
  updater.emit('update-not-available',{});assert.equal(controller.status().state,'downloaded');
  await controller.install();assert.deepEqual(updater.installArgs,[false,true]);
});
test('automatic updates can be disabled while explicit checks still work',async()=>{
  const updater=new Updater();const controller=createUpdateController({updater,packaged:true,version:'0.4.0',readSettings:async()=>({auto_app_updates:false})});
  await controller.check();assert.equal(controller.status().state,'paused');assert.equal(updater.calls,undefined);assert.equal(updater.autoInstallOnAppQuit,false);
  await controller.check(true);assert.equal(updater.calls,1);
});
test('failed updates report errors and development runs do not download or install',async()=>{
  const updater=new Updater();updater.checkForUpdates=async()=>{throw new Error('offline');};
  const controller=createUpdateController({updater,packaged:true,version:'0.4.0',readSettings:async()=>({})});
  await controller.check();assert.equal(controller.status().state,'error');assert.match(controller.status().error,/offline/);
  const dev=createUpdateController({updater:null,packaged:false,version:'0.4.0',readSettings:async()=>({})});await dev.check();assert.equal(dev.status().state,'development');await assert.rejects(dev.install());
});
