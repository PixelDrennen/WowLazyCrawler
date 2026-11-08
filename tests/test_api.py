import json
import sqlite3
from unittest.mock import patch
import httpx
import pytest
from fastapi.testclient import TestClient
from server import db
from server.app import app,admin_token,attempts,scanner
from server.ingest import Scanner,save_snapshot
from server.market import parse_tsm

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('LAZYCRAWLER_DATA',str(tmp_path))
    attempts.clear()
    scanner.task=None
    scanner.next_scan=None
    with TestClient(app) as c:
        yield c


def unlock(client):
    assert client.post('/api/login',json={'token':admin_token()}).status_code==200


def test_auth_origin_and_logout(client):
    assert client.get('/api/health').status_code==200
    assert client.get('/api/settings').status_code==401
    assert client.post('/api/login',json={'token':'bad'}).status_code==401
    unlock(client)
    assert client.get('/api/settings').status_code==200
    assert client.put('/api/settings',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/logout').status_code==200
    assert client.get('/api/status').status_code==401


def test_login_rate_limit(client):
    for _ in range(10):client.post('/api/login',json={'token':'bad'})
    assert client.post('/api/login',json={'token':admin_token()}).status_code==429


def test_config_validation_and_credentials_redaction(client):
    unlock(client)
    assert client.put('/api/settings',json={'realms':['../evil']}).status_code==422
    assert client.put('/api/settings',json={'selling_realms':['b']}).status_code==422
    assert client.put('/api/settings',json={'budget_gold':-1}).status_code==422
    assert client.put('/api/credentials',json={'client_id':'id','client_secret':'sensitive'}).status_code==200
    assert 'sensitive' not in client.get('/api/status').text
    assert 'sensitive' not in client.get('/api/settings').text
    assert (db.data_dir()/'credentials.json').stat().st_mode&0o777==0o600


def test_export_and_backup_restore(client,tmp_path):
    unlock(client)
    client.put('/api/settings',json={'realms':['a','b'],'selling_realms':['b']})
    recipe={'id':'r','name':'Recipe','output_item_id':1,'sale_price_gold':100,'materials':[{'item_id':1,'quantity':1,'unit_cost_gold':10}]}
    assert client.put('/api/recipes/r',json=recipe).status_code==200
    assert client.get('/api/crafting').json()[0]['net_profit']==84
    assert client.get('/api/export').json()['schema_version']==1
    backup=client.get('/api/backup')
    path=tmp_path/'restore.sqlite'
    path.write_bytes(backup.content)
    conn=sqlite3.connect(path)
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
    assert json.loads(conn.execute("SELECT value FROM settings WHERE key='config'").fetchone()[0])['realms']==['a','b']
    assert conn.execute('SELECT COUNT(*) FROM recipes').fetchone()[0]==1
    conn.close()


def test_snapshot_replacement_and_history_dedup(client):
    stamp=db.now()
    csv='itemId,name,marketValue,minBuyout,historical,updatedAt\n1,Test,100,100,100,'+stamp
    values=parse_tsm(csv,'us','realm','a','tsm:a',stamp)
    save_snapshot('tsm:a',values)
    save_snapshot('tsm:a',values)
    assert len(db.rows('SELECT * FROM history'))==1
    save_snapshot('tsm:a',[])
    assert len(db.rows('SELECT * FROM observations'))==0
    assert len(db.rows('SELECT * FROM history'))==1


def test_changed_schema_preserves_previous_snapshot(client):
    import asyncio
    stamp=db.now()
    values=parse_tsm('itemId,name,marketValue,minBuyout,historical,updatedAt\n1,Test,100,100,100,'+stamp,'us','realm','a','tsm:a',stamp)
    save_snapshot('tsm:a',values)
    async def run():
        transport=httpx.MockTransport(lambda req:httpx.Response(200,text='bad,schema\n1,2'))
        async with httpx.AsyncClient(transport=transport) as c:
            with pytest.raises(ValueError):await Scanner().fetch_source(c,'tsm:a','https://example.test','us','realm','a')
    asyncio.run(run())
    assert len(db.rows('SELECT * FROM observations'))==1
    assert db.rows('SELECT status FROM sources')[0]['status']=='error'


def test_304_does_not_refresh_observation_age(client):
    import asyncio
    stamp=db.now()
    save_snapshot('tsm:a',parse_tsm('itemId,name,marketValue,minBuyout,historical,updatedAt\n1,Test,100,100,100,'+stamp,'us','realm','a','tsm:a',stamp),'tag')
    async def run():
        def handle(req):
            assert req.headers['if-none-match']=='tag'
            return httpx.Response(304)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            await Scanner().fetch_source(c,'tsm:a','https://example.test','us','realm','a')
    asyncio.run(run())
    assert db.rows('SELECT observed_at FROM observations')[0]['observed_at']==stamp
    assert db.rows('SELECT status FROM sources')[0]['status']=='unchanged'


def test_retry_and_duplicate_scan(client):
    import asyncio
    async def run():
        responses=iter([429,503,200])
        async def no_sleep(*args): pass
        with patch('server.ingest.asyncio.sleep',no_sleep):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(next(responses)))) as c:
                assert (await Scanner().request(c,'GET','https://example.test')).status_code==200
        s=Scanner()
        async def pending(): await asyncio.Future()
        s.run=pending
        assert s.start()
        assert not s.start()
        s.task.cancel()
        await asyncio.gather(s.task,return_exceptions=True)
    asyncio.run(run())
