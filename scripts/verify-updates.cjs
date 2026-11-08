const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
const yaml = require('js-yaml');
const metadata = yaml.load(fs.readFileSync('release/latest-linux.yml', 'utf8'));
const version = require('../package.json').version;
assert.equal(metadata.version, version);
for (const extension of ['.rpm', '.AppImage']) {
  const info = metadata.files.find(file => file.url.endsWith(extension));
  assert.ok(info, `Missing ${extension} update asset in latest-linux.yml`);
  assert.match(info.sha512, /^[A-Za-z0-9+/]{86}==$/);
  assert.ok(fs.existsSync(path.join('release', decodeURIComponent(info.url))));
}
const config = yaml.load(fs.readFileSync('release/linux-unpacked/resources/app-update.yml', 'utf8'));
assert.equal(config.provider, 'github');
assert.equal(config.owner, 'PixelDrennen');
assert.equal(config.repo, 'WowLazyCrawler');
console.log('Verified RPM/AppImage update metadata and pinned GitHub release provider');
