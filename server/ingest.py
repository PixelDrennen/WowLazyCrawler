import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import httpx
from . import db
from .market import parse_tsm, parse_blizzard
from .models import Settings

COLUMNS = 'region,scope,realm,item_key,name,buyout,market,historical,sale_price,sale_rate,sold_day,quantity,observed_at,fetched_at,source'


def save_snapshot(source, values, etag=None, modified=None):
    with db.connect() as conn:
        conn.execute('DELETE FROM observations WHERE source=?', (source,))
        conn.executemany(f'INSERT INTO observations({COLUMNS}) VALUES({",".join("?"*15)})', values)
        conn.executemany('INSERT OR IGNORE INTO history VALUES(?,?,?,?,?,?,?,?)',
                        [(r[0], r[1], r[2], r[3], r[12], r[5], r[6], r[14]) for r in values])
        conn.execute('''INSERT INTO sources(id,etag,modified,last_attempt,last_success,status,rows,error)
            VALUES(?,?,?,?,?,'ready',?,NULL) ON CONFLICT(id) DO UPDATE SET etag=excluded.etag,
            modified=excluded.modified,last_attempt=excluded.last_attempt,last_success=excluded.last_success,
            status='ready',rows=excluded.rows,error=NULL''', (source, etag, modified, db.now(), db.now(), len(values)))


class Scanner:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.task = None
        self.next_scan = None

    async def request(self, client, method, url, **kwargs):
        for attempt in range(3):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        delay = response.headers.get('retry-after', '')
                        await asyncio.sleep(min(30, int(delay)) if delay.isdigit() else 2 ** attempt)
                        continue
                if response.status_code != 304:
                    response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def fetch_source(self, client, source, url, region, scope, realm, auth=None):
        previous = db.rows('SELECT * FROM sources WHERE id=?', (source,))
        headers = dict(auth or {})
        if previous:
            if previous[0]['etag']:
                headers['If-None-Match'] = previous[0]['etag']
            if previous[0]['modified']:
                headers['If-Modified-Since'] = previous[0]['modified']
        try:
            response = await self.request(client, 'GET', url, headers=headers)
            if response.status_code == 304:
                with db.connect() as conn:
                    conn.execute("UPDATE sources SET last_attempt=?,last_success=?,status='unchanged',error=NULL WHERE id=?", (db.now(), db.now(), source))
                return
            fetched = db.now()
            if source.startswith('tsm:'):
                values = parse_tsm(response.text, region, scope, realm, source, fetched)
            else:
                # API snapshot time, not fetch time. If absent, retain an explicit fetch-time proxy.
                modified = response.headers.get('last-modified')
                observed = parsedate_to_datetime(modified).isoformat() if modified else fetched
                values = parse_blizzard(response.json(), region, scope, realm, source, observed, fetched)
            save_snapshot(source, values, response.headers.get('etag'), response.headers.get('last-modified'))
        except Exception as exc:
            # Never store upstream response bodies or URLs containing credentials.
            message = f'HTTP {exc.response.status_code}' if isinstance(exc, httpx.HTTPStatusError) else (
                str(exc)[:240] if isinstance(exc, ValueError) else type(exc).__name__)
            with db.connect() as conn:
                conn.execute('''INSERT INTO sources(id,last_attempt,status,error) VALUES(?,?,'error',?)
                    ON CONFLICT(id) DO UPDATE SET last_attempt=excluded.last_attempt,status='error',error=excluded.error''', (source, db.now(), message))
            raise ValueError(f'{source}: {message}') from None

    async def blizzard(self, client, settings):
        credentials = read_credentials()
        if not credentials.get('client_id') or not credentials.get('client_secret'):
            raise ValueError('Blizzard credentials are not configured')
        token = await self.request(client, 'POST', 'https://oauth.battle.net/token',
            auth=(credentials['client_id'], credentials['client_secret']), data={'grant_type':'client_credentials'})
        auth = {'Authorization':'Bearer ' + token.json()['access_token']}
        root = f'https://{settings.region}.api.blizzard.com/data/wow'
        query = f'?namespace=dynamic-{settings.region}&locale=en_US'
        index = await self.request(client, 'GET', root+'/connected-realm/index'+query, headers=auth)
        wanted = set(settings.realms)
        # Resolve clusters dynamically and save their slugs. Selected slugs may map to the same AH.
        # Walk index only when needed; realm mappings expire daily.
        refreshed = db.get('realm_refresh:'+settings.region, 0)
        if time.time() - refreshed > 86400 or any(not db.rows('SELECT 1 FROM realms WHERE region=? AND slug=?', (settings.region,r)) for r in wanted):
            for entry in index.json()['connected_realms']:
                cluster = int(entry['href'].split('/connected-realm/')[1].split('?')[0])
                response = await self.request(client, 'GET', root+f'/connected-realm/{cluster}'+query, headers=auth)
                with db.connect() as conn:
                    for realm in response.json()['realms']:
                        conn.execute('INSERT OR REPLACE INTO realms VALUES(?,?,?,?)',
                                     (settings.region, realm['slug'], realm['name'], cluster))
                await asyncio.sleep(.1)
            db.put('realm_refresh:'+settings.region, time.time())
        clusters = {r['connected_id'] for r in db.rows('SELECT * FROM realms WHERE region=?', (settings.region,)) if r['slug'] in wanted}
        for cluster in sorted(clusters):
            await self.fetch_source(client, f'blizzard:{settings.region}:{cluster}', root+f'/connected-realm/{cluster}/auctions'+query,
                                    settings.region, 'realm', str(cluster), auth)
        await self.fetch_source(client, f'blizzard:{settings.region}:commodity', root+'/auctions/commodities'+query,
                                settings.region, 'commodity', '', auth)

    async def run(self):
        if self.lock.locked():
            return
        async with self.lock:
            settings = Settings(**db.get('config', {}))
            with db.connect() as conn:
                job = conn.execute("INSERT INTO jobs(started,status,message) VALUES(?,'running','Downloading market snapshots')", (db.now(),)).lastrowid
            errors = []
            cancelled = False
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False,
                    headers={'User-Agent':'WowLazyCrawler/0.1 (self-hosted market analytics)'}) as client:
                    if settings.tsm_enabled:
                        feeds = [('region', '', 'region/items.csv'), ('commodity', '', 'commodities.csv')]
                        feeds += [('realm', realm, f'realm/{realm}/items.csv') for realm in settings.realms]
                        for scope, realm, path in feeds:
                            try:
                                await self.fetch_source(client, f'tsm:{settings.region}:{scope}:{realm}',
                                    f'https://public-data.tradeskillmaster.com/retail/{settings.region}/{path}', settings.region, scope, realm)
                            except ValueError as exc:
                                errors.append(str(exc))
                    if settings.blizzard_enabled:
                        try:
                            await self.blizzard(client, settings)
                        except Exception as exc:
                            errors.append(str(exc) if isinstance(exc, ValueError) else 'Blizzard request failed: '+type(exc).__name__)
                cutoff = (datetime.now(timezone.utc)-timedelta(days=settings.retention_days)).isoformat()
                with db.connect() as conn:
                    conn.execute('DELETE FROM history WHERE observed_at < ?', (cutoff,))
                    conn.execute('DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY id DESC LIMIT 100)')
            except asyncio.CancelledError:
                cancelled = True
                errors.append('Scan interrupted by shutdown; run again.')
                raise
            except Exception as exc:
                errors.append('Scan failed: '+type(exc).__name__)
            finally:
                with db.connect() as conn:
                    conn.execute('UPDATE jobs SET finished=?,status=?,message=? WHERE id=?',
                        (db.now(), 'interrupted' if cancelled else ('error' if errors else 'complete'), '; '.join(errors)[:1000] if errors else 'Market snapshots saved successfully', job))
                self.next_scan = time.time()+settings.interval_minutes*60

    def start(self):
        if self.task and not self.task.done():
            return False
        self.task = asyncio.create_task(self.run())
        return True

    async def schedule(self):
        while True:
            settings = Settings(**db.get('config', {}))
            if settings.scheduled and (self.next_scan is None or time.time() >= self.next_scan):
                self.start()
            await asyncio.sleep(15)


def read_credentials():
    path = db.data_dir()/'credentials.json'
    return json.loads(path.read_text()) if path.exists() else {}


def write_credentials(value):
    import os
    path = db.data_dir()/'credentials.json'
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(value, f)
    os.replace(temp, path)
