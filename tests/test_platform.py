import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from server import db
from server.app import app,admin_token,attempts,scanner,companion,live_trades
from server.catalog import markets,character_markets,parse_public_catalog
from server.snapshots import accept_snapshot,characters,shared_storage,lumber_rates
from server.companion import decode_saved_export,lua_literal,install_addons,Companion
from server.admin import gather_estimate
from server.ingest import Scanner

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('LAZYCRAWLER_DATA',str(tmp_path/'data'));attempts.clear();scanner.task=None;scanner.next_scan=None
    companion.last_revision=None
    with TestClient(app) as c:
        c.post('/api/login',json={'token':admin_token()}).raise_for_status()
        yield c


def snapshot(account='one',gold=10000,stamp=None):
    return dict(schema_version=2,account_id=account,addon_version='0.2.0',warbank_group='bn:123',
        characters={'Hanami-Gurubashi':dict(name='Hanami',realm='Gurubashi',region='us',class_name='HUNTER',level=90,professions=['Alchemy'],storages={'bags':dict(observed_at=stamp or int(time.time()),money=gold,items=[])},recipes=[])},
        warbank=dict(observed_at=stamp or int(time.time()),money=20000,items=[]),lumber=[],tasks=[],integrations={})


def test_catalog_covers_region_and_deduplicates_gurubashi(client):
    groups=markets('us')
    assert sum(len(m['realms']) for m in groups)>=200
    guru=next(m for m in groups if any(r['slug']=='gurubashi' for r in m['realms']))
    assert {'gurubashi','aegwynn','bonechewer','hakkar','garrosh','daggerspine'} <= {r['slug'] for r in guru['realms']}
    assert len([m for m in groups if any(r['slug']=='gurubashi' for r in m['realms'])])==1
    assert not character_markets('us')
    accept_snapshot(snapshot())
    assert character_markets('us')=={guru['connected_id']}


def test_demo_is_isolated_from_live_and_outgoing_bundle(client):
    admin=client.get('/api/admin').json()
    assert admin['origin']=='live' and admin['characters']==[] and admin['telemetry']==[]
    assert admin['trades']==[]
    assert not characters()
    plan=client.get('/api/addon/plan').json()
    assert plan['origin']=='live' and plan['opportunities']==[] and plan['crafting']==[]
    assert db.rows('SELECT COUNT(*) AS n FROM observations')[0]['n']==0
    c=client.get('/api/settings').json();c['demo_mode']=True
    client.put('/api/settings',json=c).raise_for_status()
    assert client.get('/api/admin').json()['characters']==[]


def test_partial_sources_are_preserved_and_shared_warbank_once(client):
    accept_snapshot(snapshot())
    value=snapshot('two',gold=7000)
    accept_snapshot(value)
    assert len(characters())==2
    assert len(shared_storage())==1
    assert sum(s['money'] for s in shared_storage())==20000
    # No mail observation is different from zero mail.
    assert 'mail' not in characters()[0]['captures']
    old=snapshot('one',gold=1,stamp=int(time.time())-100)
    accept_snapshot(old)
    one=next(c for c in characters() if c['account_id']=='one')
    assert one['captures']['bags']['money']==10000
    empty=snapshot();empty['characters']['Hanami-Gurubashi']['storages']={}
    accept_snapshot(empty)
    assert next(c for c in characters() if c['account_id']=='one')['captures']['bags']['money']==10000


def test_unresolved_shared_identity_is_conservative(client):
    first=snapshot();first.pop('warbank_group');accept_snapshot(first)
    second=snapshot('two');second.pop('warbank_group');accept_snapshot(second)
    assert len(shared_storage())==1
    assert shared_storage()[0]['account_id'].startswith('unresolved:')


def test_snapshot_validation_future_and_version(client):
    s=snapshot();s['schema_version']=99
    assert client.post('/api/addon/snapshot',json=s).status_code==422
    s=snapshot(stamp=int(time.time())+7200)
    assert client.post('/api/addon/snapshot',json=s).status_code==422
    assert not characters()


def test_mail_receivables_do_not_become_wallet_gold(client):
    s=snapshot();s['characters']['Hanami-Gurubashi']['storages']['mail']=dict(observed_at=int(time.time()),money=45000,complete=False,note='Partial inbox',items=[dict(item_id=1,count=2,cod=True)])
    accept_snapshot(s)
    c=characters()[0]
    assert c['captures']['mail']['money']==45000 and not c['captures']['mail']['complete']
    assert c['captures']['bags']['money']==10000
    assert c['captures']['mail']['items'][0]['cod'] is True


def test_lumber_samples_weight_time_and_deduplicate(client):
    s=snapshot();s['lumber']=[dict(item_id=123,quantity=100,seconds=3600,zone='Forest',source='Registered provider'),dict(item_id=123,quantity=100,seconds=1800,zone='Forest',source='Registered provider')]
    accept_snapshot(s);accept_snapshot(s)
    rates=lumber_rates();assert rates[0]['samples']==2 and rates[0]['per_hour']==pytest.approx(133.333333)
    assert gather_estimate(123,100)['minutes']==45
    assert gather_estimate(99,100)['minutes'] is None
    assert gather_estimate(99,0)['minutes']==0


def test_savedvariables_decoder_never_executes_and_handles_utf8():
    value={'schema_version':2,'name':'Élodie','items':[]}
    encoded=json.dumps(value,ensure_ascii=False)
    lua='LazyCrawlerDB = { ["exportJSON"] = '+lua_literal(encoded)+' } -- malicious calls are never evaluated'
    assert decode_saved_export(lua)==value
    byte_escaped=lua.replace('É','\\195\\137')
    assert decode_saved_export(byte_escaped)==value
    with pytest.raises(ValueError):decode_saved_export('LazyCrawlerDB = { ["exportJSON"] = "truncated')
    with pytest.raises(ValueError):decode_saved_export('LazyCrawlerDB = os.execute("something")')


def test_companion_publishes_data_for_reload_but_blocks_install_while_game_running(client,tmp_path):
    root=tmp_path/'wow'/'_retail_';root.mkdir(parents=True);(root/'Wow.exe').touch()
    out=root/'Interface'/'AddOns'/'LazyCrawler_Data';out.mkdir(parents=True);target=out/'Data.lua';target.write_text('original')
    config=client.get('/api/settings').json();config['wow_path']=str(root);client.put('/api/settings',json=config).raise_for_status()
    worker=Companion();worker.plan_provider=lambda:{'origin':'live','schema_version':2,'opportunities':[]}
    with patch('server.companion.game_state',return_value='running'):
        worker.tick()
        assert 'LazyCrawlerData = ' in target.read_text() and not worker.pending
        assert '/reload' in worker.state
        with pytest.raises(ValueError):install_addons(str(root))
    with patch('server.companion.game_state',return_value='closed'):
        worker.tick()
        assert 'LazyCrawlerData = ' in target.read_text() and not worker.pending
    worker.last_revision=None;worker.plan_provider=lambda:{'origin':'demo'}
    with patch('server.companion.game_state',return_value='closed'):
        with pytest.raises(ValueError):worker.tick()


def test_companion_installs_own_addons_and_imports_stable_exports(client,tmp_path):
    root=tmp_path/'Retail';root.mkdir();(root/'Wow.exe').touch()
    config=client.get('/api/settings').json();config['wow_path']=str(root);client.put('/api/settings',json=config).raise_for_status()
    with patch('server.companion.game_state',return_value='closed'):
        result=install_addons(str(root));assert result['installed']
    saved=root/'WTF'/'Account'/'account'/'SavedVariables';saved.mkdir(parents=True)
    (saved/'LazyCrawler.lua').write_text('LazyCrawlerDB = {["exportJSON"] = '+lua_literal(json.dumps(snapshot()))+'}')
    worker=Companion()
    with patch('server.companion.game_state',return_value='running'):
        worker.tick();assert not characters()
        worker.tick();assert len(characters())==1
        worker.tick();assert len(db.rows('SELECT * FROM sync_events'))==1


def test_scan_ignores_legacy_realm_selection(client):
    config=client.get('/api/settings').json();config['realms']=['ignored'];client.put('/api/settings',json=config).raise_for_status()
    db.put('catalog_refresh',time.time())
    calls=[]
    async def run():
        worker=Scanner()
        async def capture(c,source,url,region,scope,realm,auth=None):calls.append((scope,realm))
        worker.fetch_source=capture
        with patch('server.ingest.markets',return_value=[{'representative':'aegwynn'},{'representative':'stormrage'}]):await worker.run()
    asyncio.run(run())
    assert ('realm','aegwynn') in calls and ('realm','stormrage') in calls and ('realm','ignored') not in calls


def test_catalog_parser_schema_failure_preserves_snapshot(client):
    count=len(markets('us'))
    with pytest.raises(ValueError):parse_public_catalog('<html>changed</html>')
    assert len(markets('us'))==count


def test_schema_v1_upgrade_preserves_existing_settings_and_prices(tmp_path,monkeypatch):
    import sqlite3
    data=tmp_path/'old-data';data.mkdir();monkeypatch.setenv('LAZYCRAWLER_DATA',str(data))
    conn=sqlite3.connect(data/'crawler.sqlite')
    conn.executescript('CREATE TABLE migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL); CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);')
    conn.execute('INSERT INTO migrations VALUES(1,?)',(db.now(),))
    conn.execute('INSERT INTO settings VALUES(?,?)',('config',json.dumps({'budget_gold':12345,'realms':['gurubashi']})))
    conn.commit();conn.close()
    db.init()
    assert db.get('config')['budget_gold']==12345
    assert db.rows('SELECT MAX(version) AS version FROM migrations')[0]['version']==2
    assert db.rows('SELECT COUNT(*) AS n FROM characters')[0]['n']==0


def test_region_routes_use_character_markets_in_both_directions(client):
    from server.market import parse_tsm
    from server.ingest import save_snapshot
    accept_snapshot(snapshot())
    config=client.get('/api/settings').json();config.update(demo_mode=False,deposit_gold=0,min_roi=0,min_profit_gold=0,realms=['ignored'])
    client.put('/api/settings',json=config).raise_for_status()
    guru=next(m['representative'] for m in markets('us') if any(r['slug']=='gurubashi' for r in m['realms']))
    stamp=db.now()
    for realm,price in [(guru,1000000),('stormrage',10000000),('area-52',500000),('gurubashi',1)]:
        source='tsm:us:realm:'+realm
        text=f'itemId,name,marketValue,minBuyout,historical,updatedAt\n123,Decor,{price},{price},{price},{stamp}'
        save_snapshot(source,parse_tsm(text,'us','realm',realm,source,stamp))
    source='tsm:us:region:'
    text=f'itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt\n123,Decor,10000000,10000000,10000000,0.1,2,{stamp}'
    save_snapshot(source,parse_tsm(text,'us','region','',source,stamp))
    db.put('market_revision',stamp)
    routes=client.get('/api/opportunities').json()
    assert any(r['source_realm']=='area-52' and r['destination_realm']==guru for r in routes)
    assert any(r['source_realm']==guru and r['destination_realm']=='stormrage' for r in routes)
    assert not any(r['source_realm']=='area-52' and r['destination_realm']=='stormrage' for r in routes)
    assert not any(r['source_realm']=='gurubashi' or r['destination_realm']=='gurubashi' for r in routes)  # Same cluster's non-representative feed is ignored.


def test_crafting_discovery_uses_prices_and_demand_without_inventing_unlocks(client):
    from server.ingest import save_snapshot
    from server.market import parse_tsm
    value=snapshot();recipe=dict(id='42',name='Decor',profession='Alchemy',output_item_id=777,output_quantity=1,
        learned=False,materials=[dict(item_id=2008,quantity=3,alternatives=[2008])])
    value['characters']['Hanami-Gurubashi']['recipes']=[recipe]
    accept_snapshot(value)
    config=client.get('/api/settings').json();config['deposit_gold']=0;client.put('/api/settings',json=config).raise_for_status()
    stamp=db.now()
    header='itemId,name,marketValue,minBuyout,historical,avgSalePrice,soldPerDay,updatedAt\n'
    for scope,realm,line in [('realm','aegwynn','777,Decor,1000000,1000000,1000000,1000000,2,'),('region','','777,Decor,1000000,1000000,1000000,1000000,2,'),('commodity','','2008,Lumber,100000,100000,100000,100000,100,')]:
        source='tsm:us:'+scope+':'+realm
        save_snapshot(source,parse_tsm(header+line+stamp,'us',scope,realm,source,stamp))
    discovery=client.get('/api/addon/plan').json()['crafting_discovery']
    assert len(discovery)==1 and discovery[0]['profit_copper']==555000
    assert discovery[0]['learned'] is False and discovery[0]['sold_day']==2
    assert discovery[0]['destination_realm']=='aegwynn'
    recipe['materials'][0]['alternatives']=[2008,2009];accept_snapshot(value)
    assert client.get('/api/addon/plan').json()['crafting_discovery'][0]['profit_copper'] is None
    assert client.get('/api/admin').json()['crafting']==[]  # Unlearned recipe is discovery, not a craftable queue.


def test_bundle_distinguishes_missing_prices_from_missing_transport(client):
    accept_snapshot(snapshot())
    plan=client.get('/api/addon/plan').json()
    assert plan['generated_at'] and plan['opportunities']==[]
    info=plan['market_diagnostics']
    assert info['state']=='prices_missing' and info['owned_markets']==1
    assert 'Character captures and market prices are separate' in info['message']
    assert 'region refresh' in info['action']
    assert client.get('/api/admin').json()['market_diagnostics']['state']=='prices_missing'


def test_readiness_distinguishes_fresh_filtered_stale_and_home_missing(client):
    from server.ingest import save_snapshot
    from server.market import parse_tsm
    from server.diagnostics import market_readiness
    from server.models import Settings
    accept_snapshot(snapshot())
    groups=markets('us');home=next(m for m in groups if m['connected_id'] in character_markets('us'))['representative']
    others=[m['representative'] for m in groups if m['representative']!=home][:2]
    config=Settings();stamp=db.now()
    header='itemId,name,marketValue,minBuyout,historical,avgSalePrice,soldPerDay,updatedAt\n'
    def add(scope,realm,when):
        source='tsm:us:'+scope+':'+realm
        save_snapshot(source,parse_tsm(header+'123,Test,100000,100000,100000,100000,2,'+when,'us',scope,realm,source,stamp))
    add('region','',stamp)
    for realm in others:add('realm',realm,stamp)
    assert market_readiness(config,0)['state']=='home_prices_missing'
    add('realm',home,stamp)
    assert market_readiness(config,0)['state']=='no_matches'
    assert market_readiness(config,1)['state']=='ready'
    assert market_readiness(config,0,True)['scanning'] is True
    assert 'running' in market_readiness(config,0,True)['action']
    with db.connect() as conn:conn.execute("UPDATE observations SET observed_at='2000-01-01T00:00:00+00:00'")
    assert market_readiness(config,0)['state']=='prices_stale'
    config.tsm_enabled=False
    assert market_readiness(config,0)['state']=='pricing_disabled'


def test_identical_bundle_not_republished_and_loaded_identity_acknowledged(client,tmp_path):
    root=tmp_path/'Retail';root.mkdir();(root/'Wow.exe').touch()
    config=client.get('/api/settings').json();config['wow_path']=str(root);client.put('/api/settings',json=config).raise_for_status()
    with patch('server.companion.game_state',return_value='closed'):install_addons(str(root))
    worker=Companion();worker.plan_provider=lambda:dict(origin='live',schema_version=2,generated_at=db.now(),generated_epoch=int(time.time()),opportunities=[])
    worker.tick();target=root/'Interface'/'AddOns'/'LazyCrawler_Data'/'Data.lua'
    published=worker.status()['published_bundle'];first=target.read_bytes();mtime=target.stat().st_mtime_ns
    value=snapshot();value['loaded_bundle']=published;accept_snapshot(value)
    worker.tick()
    assert target.read_bytes()==first and target.stat().st_mtime_ns==mtime
    assert worker.status()['loaded_bundle']['generated_at']==published
    assert 'acknowledged' in worker.state
    target.write_text('manually replaced')
    db.put('config_revision','changed');worker.tick()
    assert 'LazyCrawlerData = ' in target.read_text()  # A changed/deleted file must be repaired despite identical semantic data.
