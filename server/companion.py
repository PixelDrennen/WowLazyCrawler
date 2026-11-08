"""Offline-safe transport. Reads exports; never executes or writes SavedVariables."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from . import db
from .models import Settings
from .snapshots import accept_snapshot

ROOT=Path(__file__).resolve().parent.parent
MAX_EXPORT=16*1024*1024
ADDONS=('LazyCrawler','LazyCrawler_Data')

def addon_update_status(configured):
    root=retail_root(configured);dest=root/'Interface'/'AddOns'
    versions={};needed=False
    for name in ADDONS:
        source=ROOT/'addon'/name;target=dest/name
        toc=target/(name+'.toc')
        match=re.search(r'^## Version:\s*(.+)$',toc.read_text() if toc.is_file() else '',re.M)
        versions[name]=match[1].strip() if match else None
        for item in source.rglob('*'):
            if not item.is_file() or (name=='LazyCrawler_Data' and item.name=='Data.lua'):continue
            installed=target/item.relative_to(source)
            if not installed.is_file() or installed.is_symlink() or installed.read_bytes()!=item.read_bytes():needed=True
        if not (target/'Data.lua').is_file() and name=='LazyCrawler_Data':needed=True
    return dict(needed=needed,installed_versions=versions)



def decode_saved_export(text):
    match=re.search(r'\["exportJSON"\]\s*=\s*"',text)
    if not match:raise ValueError('No LazyCrawler export found; log into a character and reload or log out')
    index=match.end();output=bytearray()
    escapes={'n':'\n','r':'\r','t':'\t','a':'\a','b':'\b','f':'\f','v':'\v','\\':'\\','"':'"',"'":"'"}
    while index<len(text):
        char=text[index];index+=1
        if char=='"':
            payload=json.loads(output.decode('utf-8'))
            if not isinstance(payload,dict):raise ValueError('Export root must be an object')
            return payload
        if char=='\\':
            if index>=len(text):break
            char=text[index];index+=1
            if char.isdigit():
                digits=char
                while len(digits)<3 and index<len(text) and text[index].isdigit():digits+=text[index];index+=1
                value=int(digits)
                if value>255:raise ValueError('Invalid Lua escape')
                output.append(value);continue
            if char not in escapes:raise ValueError('Unsupported Lua string escape')
            char=escapes[char]
        output.extend(char.encode('utf-8'))
    raise ValueError('Truncated SavedVariables export; waiting for a stable file')


def game_state():
    proc=Path('/proc')
    if not proc.exists():return 'unknown'
    uncertain=False
    for folder in proc.iterdir():
        if not folder.name.isdigit():continue
        try:
            status=(folder/'status').read_text()
            uid=re.search(r'^Uid:\s+(\d+)',status,re.M)
            if uid and int(uid[1])!=os.getuid():continue
            command=(folder/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace')
            # Match executable tokens, not this application's docs or a WoW path argument.
            if re.search(r'(?:^|[ /\\])wow(?:-64|b)?\.exe(?:\s|$)',command,re.I):return 'running'
        except FileNotFoundError:continue
        except PermissionError:uncertain=True
        except OSError:uncertain=True
    return 'unknown' if uncertain else 'closed'


def retail_root(configured):
    if not configured:raise ValueError('Choose your WoW installation folder in Companion settings')
    root=Path(configured).expanduser().resolve()
    if (root/'_retail_').is_dir():root=(root/'_retail_').resolve()
    if not (root/'Wow.exe').is_file() and not (root/'WowB.exe').is_file():
        raise ValueError('Choose a Retail directory containing Wow.exe, or its parent World of Warcraft directory')
    for name in ['Interface','WTF']:
        path=root/name
        if path.exists() and not path.resolve().is_relative_to(root):raise ValueError('WoW directories must not point outside the installation')
    return root


def lua_literal(value,depth=0):
    if depth>20:raise ValueError('Data nesting exceeds the addon contract')
    if value is None:return 'nil'
    if value is True:return 'true'
    if value is False:return 'false'
    if isinstance(value,(int,float)):
        import math
        if not math.isfinite(value):raise ValueError('Non-finite data')
        return str(value)
    if isinstance(value,str):
        # JSON's unicode escapes are not Lua escapes; UTF-8 and decimal control escapes are.
        return '"'+''.join('\\'+c if c in '\\"' else ('\\%03d'%ord(c) if ord(c)<32 else c) for c in value)+'"'
    if isinstance(value,list):return '{'+','.join(lua_literal(v,depth+1) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua_literal(str(k),depth+1)+']='+lua_literal(v,depth+1) for k,v in value.items())+'}'
    raise ValueError('Unsupported data value')


def install_addons(configured):
    root=retail_root(configured);dest=root/'Interface'/'AddOns'
    dest.mkdir(parents=True,exist_ok=True)
    if not dest.resolve().is_relative_to(root):raise ValueError('Addon path escapes installation')
    for name in ADDONS:
        for target in [dest/name,dest/(name+'.previous')]:
            if target.is_symlink():raise ValueError('Cannot update a symlinked addon directory')
    with tempfile.TemporaryDirectory(dir=dest,prefix='.lazycrawler-install-') as staging:
        stage=Path(staging);moved=[];installed=[]
        for name in ADDONS:shutil.copytree(ROOT/'addon'/name,stage/name)
        try:
            for name in ADDONS:
                target=dest/name
                if target.exists():target.rename(stage/(name+'.rollback'));moved.append(name)
                (stage/name).rename(target);installed.append(name)
        except Exception:
            for name in reversed(installed):shutil.rmtree(dest/name)
            for name in moved:(stage/(name+'.rollback')).rename(dest/name)
            raise
        for name in moved:
            backup=dest/(name+'.previous')
            if backup.exists():shutil.rmtree(backup)
            (stage/(name+'.rollback')).rename(backup)
    return dict(installed=True,path=str(dest),notice='Enable both LazyCrawler addons on the Retail character screen')


class Companion:
    def __init__(self):
        self.last_read={};self.stable={};self.state='not configured';self.error=None;self.pending=False;self.last_output=None;self.last_revision=None
        self.plan_provider=None;self.addon_update=dict(state='not configured',error=None,installed_versions={})

    def status(self):
        published=db.get('companion_bundle',{})
        loaded=db.get('last_loaded_bundle')
        return dict(addon_update=self.addon_update,state=self.state,error=self.error,pending=self.pending,last_output=self.last_output or published.get('published_at'),
            published_bundle=published.get('generated_at'),loaded_bundle=loaded,
            game_state=game_state(),last_sync=db.get('last_addon_sync'),protocol=2)

    async def loop(self):
        while True:
            try:await asyncio.to_thread(self.tick)
            except Exception as exc:self.error=str(exc)[:300];self.state='attention needed'
            await asyncio.sleep(10)

    def tick(self):
        config=Settings(**db.get('config',{}))
        if not config.companion_enabled:self.state='paused';return
        if not config.wow_path:self.state='not configured';return
        root=retail_root(config.wow_path)
        self.state='watching exports';self.error=None
        update=addon_update_status(config.wow_path)
        running=db.get('last_addon_version')
        expected=update['installed_versions'].get('LazyCrawler')
        self.addon_update=dict(update,state='up to date' if running==expected else 'installed — /reload to apply addon code',error=None,running_version=running)
        if update['needed']:
            if not config.auto_addon_updates:self.addon_update['state']='available — automatic addon updates disabled'
            else:
                try:
                    self.addon_update['state']='installing'
                    install_addons(config.wow_path)
                    self.last_revision=None
                    self.addon_update=dict(addon_update_status(config.wow_path),state='installed — /reload to apply addon code',error=None)
                except Exception as exc:
                    self.addon_update.update(state='update failed — retrying',error=str(exc)[:300])
                    raise

        for path in (root/'WTF'/'Account').glob('*/SavedVariables/LazyCrawler.lua'):
            if not path.resolve().is_relative_to(root):continue
            stat=path.stat()
            if stat.st_size>MAX_EXPORT:raise ValueError('Addon export exceeds 16 MB')
            mark=(stat.st_mtime_ns,stat.st_size)
            if self.stable.get(str(path))!=mark:self.stable[str(path)]=mark;continue
            content=path.read_text(encoding='utf-8-sig')
            if path.stat().st_mtime_ns!=stat.st_mtime_ns:continue
            digest=hashlib.sha256(content.encode()).hexdigest()
            if self.last_read.get(str(path))==digest:continue
            accept_snapshot(decode_saved_export(content))
            self.last_read[str(path)]=digest
        # Only the separate data addon is replaced, atomically. WoW reads it on login or /reload.
        # SavedVariables and executable addon code are never written by this path.
        jobs=db.rows('SELECT id,status FROM jobs ORDER BY id DESC LIMIT 1')
        revision=(db.get('last_addon_sync'),db.get('market_revision'),db.get('config_revision'),int(time.time()//300),tuple(jobs[0].values()) if jobs else None)
        if revision==self.last_revision:
            published=db.get('companion_bundle',{})
            loaded=db.get('last_loaded_bundle',{})
            if published.get('generated_at') and published.get('generated_at')>loaded.get('generated_at',''):self.state='new data ready — live import or normal reload'
            else:self.state='watching exports — bundle acknowledged' if loaded else 'watching exports'
            return
        self.pending=True
        target=root/'Interface'/'AddOns'/'LazyCrawler_Data'/'Data.lua'
        if not target.parent.is_dir():self.state='addon installation needed';return
        if not target.resolve().is_relative_to(root):raise ValueError('Unsafe addon output path')
        if self.plan_provider is None:return
        payload=self.plan_provider()
        if payload.get('origin')=='demo':raise ValueError('Demonstration data cannot be synchronized to WoW')
        # Re-exporting the same captures must not create an endless new-bundle/reload cycle.
        semantic={k:v for k,v in payload.items() if k not in ('generated_at','generated_epoch')}
        digest=hashlib.sha256(json.dumps(semantic,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        published=db.get('companion_bundle',{})
        if published.get('path')==str(target) and published.get('payload_digest')==digest and target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==published.get('file_digest'):
            self.last_revision=revision;self.pending=False;self.last_output=published.get('published_at')
            loaded=db.get('last_loaded_bundle',{})
            self.state='watching exports — bundle acknowledged' if loaded.get('generated_at','')>=published.get('generated_at','') else 'new data ready — live import or normal reload'
            return
        content='-- Generated atomically by LazyCrawler. No gameplay code.\nLazyCrawlerData = '+lua_literal(payload)+'\n'
        fd,temp=tempfile.mkstemp(dir=target.parent,prefix='.lazycrawler-',suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(content)
            os.replace(temp,target)
        finally:
            if Path(temp).exists():Path(temp).unlink()
        db.put('companion_bundle',dict(path=str(target),payload_digest=digest,file_digest=hashlib.sha256(content.encode()).hexdigest(),generated_at=payload.get('generated_at'),published_at=db.now()))
        self.last_revision=revision;self.last_output=db.now();self.pending=False;self.state='new data ready — live import or normal reload'
