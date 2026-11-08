import json
from pathlib import Path
import time
import pytest
from lupa.lua51 import LuaRuntime
from server.snapshots import Snapshot

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def lua():
    engine=LuaRuntime(unpack_returned_tuples=True)
    engine.execute((ROOT/'tests/lua_harness.lua').read_text())
    engine.globals().NOW=int(time.time())
    for name in ['Core.lua','Capture.lua','Crafting.lua','Workflow.lua','UI.lua']:
        engine.execute('assert(loadstring(...))("LazyCrawler", LC)',(ROOT/'addon/LazyCrawler'/name).read_text())
    engine.execute('LC:Initialize(); DrainTimers()')
    return engine


def test_addon_exports_server_valid_contract(lua):
    lua.execute('LC:Export()')
    payload=json.loads(lua.globals().LC.db.exportJSON)
    result=Snapshot.model_validate(payload)
    assert result.warbank_group=='bn:123'
    assert result.characters['Hanami-Gurubashi'].storages['bags'].money==1000000
    assert 'mail' not in result.characters['Hanami-Gurubashi'].storages


def test_mail_partial_cod_and_gold(lua):
    lua.execute('LC.mailOpen=true; LC:CaptureMail(); LC:Export()')
    payload=json.loads(lua.globals().LC.db.exportJSON)
    mail=payload['characters']['Hanami-Gurubashi']['storages']['mail']
    assert mail['money']==20000 and mail['complete'] is False
    assert len(mail['items'])==2 and mail['items'][1]['cod'] is True
    lua.execute('LC.mailOpen=false; MAILS={}; LC:CaptureMail(); LC:Export()')
    assert json.loads(lua.globals().LC.db.exportJSON)['characters']['Hanami-Gurubashi']['storages']['mail']['money']==20000


def test_unavailable_bank_does_not_wipe_existing(lua):
    lua.execute('LC.bankOpen=true;LC:CaptureBank();LC:Export()')
    before=json.loads(lua.globals().LC.db.exportJSON)['warbank']
    assert before['items'][0]['count']==7
    lua.execute('BAG_DATA[100]={};LC:CaptureBank();LC:Export()')
    assert json.loads(lua.globals().LC.db.exportJSON)['warbank']==before


def test_combat_defers_capture(lua):
    lua.execute('COMBAT=true; MONEY=1; LC:CaptureBags(); LC:Export()')
    assert json.loads(lua.globals().LC.db.exportJSON)['characters']['Hanami-Gurubashi']['storages']['bags']['money']==1000000
    assert lua.globals().LC.captureDeferred is True


def test_shared_materials_once_cod_mail_guild_and_bound_alts_excluded(lua):
    lua.execute('''LC.bankOpen=true;LC:CaptureBank()
      LC.db.characters.Other={name='Other',realm='Gurubashi',storages={bags={observed_at=NOW,items={{item_id=2008,count=100,bound=true,transferable=false},{item_id=2008,count=2,transferable=true}}},guild_bank={observed_at=NOW,items={{item_id=2008,count=999}}}},recipes={},professions={}}
      LC.db.characters[LC.characterKey].storages.mail={observed_at=NOW,items={{item_id=2008,count=100,cod=true}}}
    ''')
    assert lua.eval('LC:UsableCount(2008)')==12  # 3 current bags + 2 transferable alt + 7 shared, once.


def test_recipes_are_detected_and_material_queue_consolidated(lua):
    lua.execute('LC:CaptureRecipes();DrainTimers();LC:QueueRecipe(LC:Current().recipes[1]);LC:QueueRecipe(LC:Current().recipes[1])')
    assert lua.eval('LC:Current().recipes[1].is_decor') is True
    assert lua.eval('LC:MissingMaterials()[1].required')==8
    assert lua.eval('LC:MissingMaterials()[1].missing')==5


def test_same_cluster_routes_blocked_and_expired_evidence_blocked(lua):
    lua.execute('''LC.data.catalog={{connected_id=1,realms={{slug='gurubashi'},{slug='aegwynn'}}},{connected_id=2,realms={{slug='stormrage'}}}}
      LC:QueueCandidate({item_key='123',name='x',source_realm='gurubashi',destination_realm='aegwynn'})''')
    assert lua.eval('next(LC.db.tasks)') is None
    lua.execute("LC:QueueCandidate({item_key='123',name='x',source_realm='gurubashi',destination_realm='stormrage',expires_at=NOW-1})")
    assert lua.eval('next(LC.db.tasks)') is None


def test_sale_collection_matches_invoice_and_advances_from_receipt(lua):
    lua.execute('''LC.mailOpen=true;LC.db.tasks.x={id='x',name='Decor',state='collect',to_realm='gurubashi',item_id=777,created_at=NOW}
        LC:TaskAction(LC.db.tasks.x);LC:CaptureMail();LC:CaptureBags()''')
    assert lua.globals().TAKEN_MAIL==1
    assert lua.eval('LC.db.tasks.x.state')=='complete'
    assert lua.eval('LC.db.tasks.x.realized_receipt')==20000


def test_ui_pages_resize_and_refresh_reuse_rows(lua):
    lua.execute('LC:ShowUI();DrainTimers()')
    for page in ['overview','radar','queue','inventory','crafting','housing','materials','settings']:
        lua.globals().LC.page=page
        lua.execute('LC:RefreshUI();DrainTimers()')
    count=lua.eval('#LC.ui.rows')
    lua.execute('for i=1,20 do LC:RefreshUI() end')
    assert lua.eval('#LC.ui.rows')==count
    assert lua.eval('LC.ui.frame:IsShown()') is True
    assert not lua.eval('next(LC.errors)')


def test_walkthrough_recovers_from_capture_progress_and_can_replay(lua):
    lua.execute('LC:ShowUI();DrainTimers()')
    assert lua.eval('LC.db.tutorialStep')==2  # Bags already observed; next actionable context is the bank.
    lua.execute('LC.bankOpen=true;LC:CaptureBank();LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==3
    lua.execute('LC.mailOpen=true;LC:CaptureMail();LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==4
    lua.execute('LC.db.tutorialStep=1;LC.db.tutorialReplay=true;LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==1  # Replay explanations are not skipped by existing facts.
