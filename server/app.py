import asyncio
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from . import db
from .ingest import Scanner, read_credentials, write_credentials
from .market import opportunities, crafting_plan
from .models import Settings, Credentials, Login, Recipe
from .catalog import seed_catalog,markets,character_markets
from .companion import Companion,install_addons
from .snapshots import Snapshot,accept_snapshot
from .admin import live_view,live_crafting
from .crafting_market import discovery
from .access import SelfHostedAccess

scanner = Scanner()
companion = Companion()
STARTED = time.time()
ROOT = Path(__file__).resolve().parent.parent
attempts = {}
trade_cache = {"key":None,"rows":[]}


def admin_token():
    path = db.data_dir()/'admin-token'
    if not path.exists():
        fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(32))
    return path.read_text().strip()


@asynccontextmanager
async def lifespan(app):
    db.init()
    admin_token()
    seed_catalog()
    companion.plan_provider=addon_plan
    bridge=asyncio.create_task(companion.loop())
    scheduler = asyncio.create_task(scanner.schedule())
    yield
    scheduler.cancel()
    bridge.cancel()
    tasks = [scheduler,bridge]
    if scanner.task and not scanner.task.done():
        scanner.task.cancel()
        tasks.append(scanner.task)
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title='WowLazyCrawler', version='0.3.0', lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware('http')
async def security(request: Request, call_next):
    # Same-origin cookies + origin check protect mutations. No CORS exceptions.
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}':
            return Response('Cross-origin request rejected', status_code=403)
    if request.url.path.startswith('/api/') and request.url.path not in ('/api/health','/api/login'):
        cookie = request.cookies.get('lc_session', '')
        digest = hashlib.sha256(cookie.encode()).hexdigest()
        if not db.rows('SELECT 1 FROM sessions WHERE token_hash=? AND expires>?', (digest, time.time())):
            return Response('Authentication required', status_code=401)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/health')
def health():
    with db.connect() as conn:
        conn.execute('SELECT 1')
    return {'status':'ok','version':'0.3.0'}


@app.post('/api/login')
def login(payload: Login, response: Response, request: Request):
    host = request.client.host if request.client else 'unknown'
    recent = [t for t in attempts.get(host, []) if t > time.time()-60]
    if len(recent) >= 10:
        raise HTTPException(429, 'Too many attempts. Wait one minute.')
    attempts[host] = recent+[time.time()]
    if not secrets.compare_digest(payload.token, admin_token()):
        raise HTTPException(401, 'Invalid access token')
    token = secrets.token_urlsafe(32)
    with db.connect() as conn:
        conn.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
        conn.execute('INSERT INTO sessions VALUES(?,?)', (hashlib.sha256(token.encode()).hexdigest(),time.time()+86400))
    response.set_cookie('lc_session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=86400)
    return {'ok':True}


@app.post('/api/logout')
def logout(request: Request, response: Response):
    with db.connect() as conn:
        conn.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(request.cookies.get('lc_session','').encode()).hexdigest(),))
    response.delete_cookie('lc_session')
    return {'ok':True}


@app.get('/api/settings')
def settings():
    return Settings(**db.get('config', {}))


@app.put('/api/settings')
def save_settings(payload: Settings):
    # Legacy realm fields are retained only to read old configurations. Coverage is region-wide.
    db.put('config',payload.model_dump())
    db.put('config_revision',db.now())
    scanner.next_scan = None
    return payload


@app.put('/api/credentials')
def credentials(payload: Credentials):
    write_credentials(payload.model_dump())
    return {'configured':bool(payload.client_id and payload.client_secret)}


@app.get('/api/status')
def status():
    disk = shutil.disk_usage(db.data_dir())
    with db.connect() as conn:
        count = conn.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
        version = conn.execute('SELECT MAX(version) FROM migrations').fetchone()[0]
    files = sum(f.stat().st_size for f in db.data_dir().glob('*') if f.is_file())
    memory = None
    if Path('/proc/self/status').exists():
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                memory = int(line.split()[1])*1024
    return dict(version='0.3.0',database='connected',schema=version,observations=count,
                data_bytes=files,disk_free=disk.free,memory_bytes=memory,uptime_seconds=int(time.time()-STARTED),
                worker='scanning' if scanner.task and not scanner.task.done() else 'idle',
                tutorial_complete=db.get('tutorial_complete',False),next_scan=scanner.next_scan,sources=db.rows('SELECT s.*, MIN(o.observed_at) AS observed_at FROM sources s LEFT JOIN observations o ON o.source=s.id GROUP BY s.id ORDER BY s.id'),
                jobs=db.rows('SELECT * FROM jobs ORDER BY id DESC LIMIT 20'),
                blizzard_configured=bool(read_credentials().get('client_secret')), addon_status='Connected' if db.get('last_addon_sync') else 'Waiting for first addon export')


@app.post('/api/scan', status_code=202)
async def start_scan():
    config = Settings(**db.get('config', {}))
    if not config.tsm_enabled and not config.blizzard_enabled:
        raise HTTPException(422,'Enable a data source first')
    if not scanner.start():
        raise HTTPException(409,'A scan is already running')
    return {'status':'started'}


def active_observations(config):
    reps={m['representative'] for m in markets(config.region)}
    values=db.rows('SELECT * FROM observations WHERE region=?',(config.region,))
    return [r for r in values if (r['scope']!='realm' or r['realm'] in reps) and
            ((r['source'].startswith('tsm:') and config.tsm_enabled) or (r['source'].startswith('blizzard:') and config.blizzard_enabled))]


def live_trades():
    config=Settings(**db.get('config',{}))
    key=(config.model_dump_json(),db.get('market_revision'),db.get('last_addon_sync'),int(time.time()//300))
    if trade_cache['key']==key:return [r for r in trade_cache['rows'] if r['expires_at']>time.time()]
    coverage=markets(config.region)
    owned=character_markets(config.region)
    if not owned:return []
    config.realms=[m['representative'] for m in coverage]
    config.selling_realms=[m['representative'] for m in coverage if m['connected_id'] in owned]
    transferable={r['item_key']:bool(r['transferable']) for r in db.rows('SELECT * FROM metadata')}
    clusters={r['slug']:r['connected_id'] for r in db.rows('SELECT * FROM realms WHERE region=?',(config.region,))}
    # Stream one item's realm rows at a time. Loading an entire region as Python
    # dictionaries would turn a personal server into a multi-GB request.
    import itertools,heapq
    regional={r['item_key']:r for r in db.rows("SELECT * FROM observations WHERE region=? AND scope='region' AND source LIKE 'tsm:%'",(config.region,))}
    heap=[];sequence=0;representatives=set(config.realms)
    if config.tsm_enabled:
        with db.connect() as conn:
            cursor=conn.execute("SELECT * FROM observations WHERE region=? AND scope='realm' AND source LIKE 'tsm:%' AND buyout>0 ORDER BY item_key",(config.region,))
            for item_key,group in itertools.groupby(cursor,key=lambda r:r['item_key']):
                rows=[dict(r) for r in group if r['realm'] in representatives]
                context=regional.get(item_key)
                if not context:continue
                for candidate in opportunities([context]+rows,config,transferable,realm_groups=clusters):
                    sequence+=1
                    value=(candidate['score'],sequence,candidate)
                    if len(heap)<500:heapq.heappush(heap,value)
                    elif value[0]>heap[0][0]:heapq.heapreplace(heap,value)
    result=[row[2] for row in sorted(heap,key=lambda row:(-row[0],row[1]))]
    from datetime import datetime
    for row in result:row['expires_at']=int(datetime.fromisoformat(row['observed_at']).timestamp())+config.max_age_hours*3600
    trade_cache.update(key=key,rows=result)
    return result


@app.get('/api/opportunities')
def trades():
    return live_trades()


@app.get('/api/history/{item_id}')
def history(item_id: int):
    config = Settings(**db.get('config', {}))
    return db.rows('SELECT * FROM history WHERE region=? AND item_key=? ORDER BY observed_at DESC LIMIT 500', (config.region,str(item_id)))


@app.post('/api/tutorial/complete')
def complete_tutorial():
    db.put('tutorial_complete',True)
    return {'completed':True}


@app.get('/api/realms')
def realms():
    config = Settings(**db.get('config', {}))
    return db.rows('SELECT * FROM realms WHERE region=? ORDER BY name', (config.region,))


@app.get('/api/recipes')
def recipes():
    return [json.loads(r['payload']) for r in db.rows('SELECT payload FROM recipes ORDER BY id')]


@app.put('/api/recipes/{recipe_id}')
def save_recipe(recipe_id: str, payload: Recipe):
    if recipe_id != payload.id:
        raise HTTPException(422,'Recipe ID mismatch')
    with db.connect() as conn:
        conn.execute('INSERT OR REPLACE INTO recipes VALUES(?,?)',(recipe_id,payload.model_dump_json()))
    return payload


@app.delete('/api/recipes/{recipe_id}')
def delete_recipe(recipe_id: str):
    with db.connect() as conn:
        conn.execute('DELETE FROM recipes WHERE id=?',(recipe_id,))
    return {'ok':True}


@app.get('/api/crafting')
def crafting():
    config = Settings(**db.get('config', {}))
    from datetime import datetime
    prices = {r['item_key']:r for r in active_observations(config) if r['scope']=='commodity' and r['source'].startswith('tsm:')
              and time.time()-datetime.fromisoformat(r['observed_at']).timestamp() <= config.max_age_hours*3600}
    return [crafting_plan(Recipe(**r),config,prices) for r in recipes()]


@app.get('/api/export')
def export():
    return JSONResponse(dict(schema_version=1,generated_at=db.now(),kind='server-planning-export',
                opportunities=trades(),crafting=crafting(),notice='Estimates only. No live addon connection. Do not write this JSON into SavedVariables.'),
                headers={'Content-Disposition':'attachment; filename=lazycrawler-plan.json'})


@app.get('/api/backup')
def backup():
    # SQLite online backup API includes committed WAL records consistently.
    import tempfile
    from starlette.background import BackgroundTask
    fd,path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    with db.connect() as conn:
        target=sqlite3.connect(path)
        conn.backup(target)
        target.execute('DELETE FROM sessions')
        target.commit()
        target.close()
    return FileResponse(path, filename='lazycrawler-backup.sqlite',media_type='application/octet-stream',background=BackgroundTask(os.unlink,path))


@app.get('/api/contract')
def contract():
    return app.openapi()


@app.get('/api/admin')
def admin_view():
    config=Settings(**db.get('config',{}))
    result=live_view(config,live_trades)
    result['service']=status()
    result['companion']=companion.status()
    result['catalog']=db.get('catalog_provenance',{})
    result['catalog_error']=db.get('catalog_error')
    result['access']=SelfHostedAccess().describe()
    return result


@app.post('/api/addon/snapshot')
def receive_snapshot(payload:Snapshot):
    return accept_snapshot(payload.model_dump(),origin='authenticated addon transport')


@app.get('/api/addon/plan')
def addon_plan():
    config=Settings(**db.get('config',{}))
    # This endpoint deliberately never uses the presentation/demo view.
    return dict(schema_version=2,origin='live',generated_at=db.now(),generated_epoch=int(time.time()),region=config.region,
        opportunities=live_trades(),crafting=live_crafting(config),crafting_discovery=discovery(config),theme=config.theme,
        catalog=markets(config.region),limits=dict(budget_gold=config.budget_gold,max_item_gold=config.max_item_gold,min_roi=config.min_roi))


@app.post('/api/companion/install')
def install_companion():
    try:return install_addons(Settings(**db.get('config',{})).wow_path)
    except (ValueError,OSError) as exc:raise HTTPException(422,str(exc)) from None


@app.get('/api/companion')
def companion_status():return companion.status()


static = ROOT/'web'/'dist'
if static.exists():
    app.mount('/',StaticFiles(directory=static,html=True),name='dashboard')
