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
    if game_state()!='closed':raise ValueError('Close World of Warcraft before installing or updating addon files')
    root=retail_root(configured);dest=root/'Interface'/'AddOns'
    dest.mkdir(parents=True,exist_ok=True)
    if not dest.resolve().is_relative_to(root):raise ValueError('Addon path escapes installation')
    for name in ['LazyCrawler','LazyCrawler_Data']:
        source=ROOT/'addon'/name
        target=dest/name
        if target.is_symlink():raise ValueError('Cannot update a symlinked addon directory')
        # Preserve a previous version for rollback; no game SavedVariables are touched.
        if target.exists():
            backup=dest/(name+'.previous')
            if backup.is_symlink():raise ValueError('Unsafe backup directory')
            if backup.exists():shutil.rmtree(backup)
            target.rename(backup)
        try:shutil.copytree(source,target)
        except Exception:
            backup=dest/(name+'.previous')
            if backup.exists() and not target.exists():backup.rename(target)
            raise
    return dict(installed=True,path=str(dest),notice='Enable both LazyCrawler addons on the Retail character screen')


class Companion:
    def __init__(self):
        self.last_read={};self.stable={};self.state='not configured';self.error=None;self.pending=False;self.last_output=None;self.last_revision=None
        self.plan_provider=None

    def status(self):
        return dict(state=self.state,error=self.error,pending=self.pending,last_output=self.last_output,game_state=game_state(),last_sync=db.get('last_addon_sync'),protocol=2)

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
        revision=(db.get('last_addon_sync'),db.get('market_revision'),db.get('config_revision'))
        if revision==self.last_revision:return
        self.pending=True
        target=root/'Interface'/'AddOns'/'LazyCrawler_Data'/'Data.lua'
        if not target.parent.is_dir():self.state='addon installation needed';return
        if not target.resolve().is_relative_to(root):raise ValueError('Unsafe addon output path')
        if self.plan_provider is None:return
        payload=self.plan_provider()
        if payload.get('origin')=='demo':raise ValueError('Demonstration data cannot be synchronized to WoW')
        content='-- Generated atomically by LazyCrawler. No gameplay code.\nLazyCrawlerData = '+lua_literal(payload)+'\n'
        fd,temp=tempfile.mkstemp(dir=target.parent,prefix='.lazycrawler-',suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(content)
            os.replace(temp,target)
        finally:
            if Path(temp).exists():Path(temp).unlink()
        self.last_revision=revision;self.last_output=db.now();self.pending=False;self.state='bundle ready — /reload in WoW' if game_state()=='running' else 'up to date'
