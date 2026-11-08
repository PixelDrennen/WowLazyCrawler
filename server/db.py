"""Small, versioned SQLite store. Connections are transaction-scoped."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def data_dir():
    path = Path(os.environ.get('LAZYCRAWLER_DATA', 'data')).resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


@contextmanager
def connect():
    db = sqlite3.connect(data_dir() / 'crawler.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, etag TEXT, modified TEXT,
            last_attempt TEXT, last_success TEXT, status TEXT, rows INTEGER DEFAULT 0, error TEXT);
        CREATE TABLE IF NOT EXISTS observations(
            region TEXT NOT NULL, scope TEXT NOT NULL, realm TEXT NOT NULL,
            item_key TEXT NOT NULL, name TEXT NOT NULL, buyout INTEGER NOT NULL,
            market INTEGER NOT NULL, historical INTEGER NOT NULL,
            sale_price INTEGER, sale_rate REAL, sold_day REAL, quantity INTEGER,
            observed_at TEXT NOT NULL, fetched_at TEXT NOT NULL, source TEXT NOT NULL,
            PRIMARY KEY(region,scope,realm,item_key,source));
        CREATE TABLE IF NOT EXISTS history(
            region TEXT NOT NULL, scope TEXT NOT NULL, realm TEXT NOT NULL, item_key TEXT NOT NULL,
            observed_at TEXT NOT NULL, buyout INTEGER NOT NULL, market INTEGER NOT NULL, source TEXT NOT NULL,
            PRIMARY KEY(region,scope,realm,item_key,observed_at,source));
        CREATE INDEX IF NOT EXISTS history_item ON history(region,item_key,observed_at);
        CREATE TABLE IF NOT EXISTS realms(region TEXT NOT NULL, slug TEXT NOT NULL, name TEXT NOT NULL,
            connected_id INTEGER NOT NULL, PRIMARY KEY(region,slug));
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, started TEXT NOT NULL, finished TEXT,
            status TEXT NOT NULL, message TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recipes(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS metadata(item_key TEXT PRIMARY KEY, transferable INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, expires REAL NOT NULL);
        ''')
        db.execute('INSERT OR IGNORE INTO migrations VALUES(1,?)', (now(),))
        # Recover jobs interrupted by process exit; no job is silently left running.
        db.execute("UPDATE jobs SET status='interrupted',finished=?,message='Process stopped during scan; run again.' WHERE status='running'", (now(),))


def get(key, default=None):
    with connect() as db:
        row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default


def put(key, value):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (key, json.dumps(value)))


def rows(sql, args=()):
    with connect() as db:
        return [dict(r) for r in db.execute(sql, args)]
