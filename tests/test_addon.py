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
    for name in ['Core.lua','Capture.lua','Crafting.lua','Workflow.lua','Sessions.lua','UI.lua']:
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
    lua.execute('LC:ShowUI();LC.page="setup";LC:RefreshUI();DrainTimers()')
    assert lua.eval('LC.db.tutorialStep')==2  # Bags already observed; next actionable context is the bank.
    lua.execute('LC.bankOpen=true;LC:CaptureBank();LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==3
    lua.execute('LC.mailOpen=true;LC:CaptureMail();LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==4
    lua.execute('LC.db.tutorialStep=1;LC.db.tutorialReplay=true;LC:RefreshUI()')
    assert lua.eval('LC.db.tutorialStep')==1  # Replay explanations are not skipped by existing facts.


def setup_route(lua):
    lua.execute('''LC.data.catalog={{connected_id=1,realms={{slug='gurubashi'}}},{connected_id=2,realms={{slug='stormrage'}}}}
    LC:QueueCandidate({item_key='2008',name='Decor',source_realm='gurubashi',destination_realm='stormrage',buyout=100,estimated_sale=500,net_profit=300,expires_at=NOW+3600})''')


def test_session_timer_pause_reload_and_exploration_does_not_start_timer(lua):
    setup_route(lua)
    lua.execute('LC:StartActivity("flip");NOW=NOW+25;LC:ToggleSessionPause();NOW=NOW+100')
    assert lua.eval('LC:SessionElapsed()')==25
    lua.execute('LC:Export()')
    snap=Snapshot.model_validate_json(lua.globals().LC.db.exportJSON)
    assert snap.tasks[-1]['seconds']==25 and snap.tasks[-1]['state']=='paused'
    lua.execute('LC:ToggleSessionPause();NOW=NOW+5;LC:Export();NOW=NOW+1000;LC:Initialize()')
    assert lua.eval('LC:SessionElapsed()')==30  # Offline time is excluded on initialization.
    lua.execute('LC:StopActivity(false);LC:StartActivity("discover");NOW=NOW+30')
    assert lua.eval('LC:SessionElapsed()')==30
    assert lua.eval('LC.page')=='discover'


def test_flip_session_requires_observed_stock_deposit_and_gold(lua):
    setup_route(lua)
    lua.execute('LC:StartActivity("flip");LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='deposit'  # 3 bag items already meet default bulk target.
    lua.execute('LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='deposit'
    lua.execute('LC.bankOpen=true;LC:CaptureBank();BAG_DATA[0]={};MONEY=0;LC:CaptureBags();LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='withdraw'
    assert lua.eval('LC:SessionRealm()')=='stormrage'
    lua.execute('LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='withdraw'  # Wrong realm cannot advance.


def test_bank_wallet_topup_and_exact_partial_stack_withdrawal(lua):
    setup_route(lua)
    lua.execute('''LC:StartActivity('posting');LC.db.activity.routes[1]=next(LC.db.tasks)
    local task=LC.db.tasks[LC.db.activity.routes[1]];task.to_realm='gurubashi'
    LC.bankOpen=true;MONEY=2000000;BAG_DATA[0]={false,false};LC:CaptureBags()
    C_Bank.FetchDepositedMoney=function()return 10000000 end
    C_Bank.WithdrawMoney=function(kind,amount)WITHDRAW_AMOUNT=amount end
    C_Container.SplitContainerItem=function(bag,slot,amount)SPLIT={bag,slot,amount}end
    C_Container.PickupContainerItem=function(bag,slot)PLACED={bag,slot}end
    LC:SessionBankAction(true)''')
    assert lua.globals().WITHDRAW_AMOUNT==3000000  # Top up 200g to 500g, not withdraw another 500g.
    lua.execute('NOW=NOW+3;LC:SessionBankAction(false)')
    assert lua.eval('SPLIT[3]')==1 and lua.eval('PLACED[1]')==0
    lua.execute('LC:ToggleSessionPause();WITHDRAW_AMOUNT=nil;NOW=NOW+3;LC:SessionBankAction(true)')
    assert lua.globals().WITHDRAW_AMOUNT is None


def test_crafting_session_rejects_unknown_or_expired_simulations_and_plans_stock(lua):
    lua.execute('LC:CaptureRecipes();DrainTimers();LC:StartActivity("craft")')
    assert lua.globals().LC.db.activity is None
    lua.execute('''local recipe=LC:Current().recipes[1];recipe.simulation={profit_copper=20000,observed_at=NOW-50000};LC:StartActivity('craft')''')
    assert lua.globals().LC.db.activity is None
    lua.execute('LC:Current().recipes[1].simulation.observed_at=NOW;LC:StartActivity("craft");LC.db.activity.stock=2;LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='craft'
    assert lua.eval('LC:Current().recipes[1].crafts')==2
    lua.execute('LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='craft'
    lua.execute('BAG_DATA[0][2]={itemID=777,stackCount=2,transferable=true};LC:CaptureBags();LC:SessionNext()')
    assert lua.eval('LC.db.activity.phase')=='craft_deposit'


def test_missing_bank_gold_and_unloaded_mail_headers_preserve_last_observation(lua):
    lua.execute('LC.bankOpen=true;LC:CaptureBank();LC.mailOpen=true;LC:CaptureMail();LC:Export()')
    before=json.loads(lua.globals().LC.db.exportJSON)
    lua.execute('C_Bank.FetchDepositedMoney=function()return nil end;GetInboxHeaderInfo=function()return nil end;LC:CaptureBank();LC:CaptureMail();LC:Export()')
    after=json.loads(lua.globals().LC.db.exportJSON)
    assert after['warbank']==before['warbank']
    assert after['characters']['Hanami-Gurubashi']['storages']['mail']==before['characters']['Hanami-Gurubashi']['storages']['mail']
    assert lua.eval('LC.errors["Capture warbank"]') and lua.eval('LC.errors["Capture mail"]')


def test_compact_ui_gold_header_and_conditional_scrollbar(lua):
    lua.execute('LC:ShowUI();LC.page="setup";LC.db.tutorialStep=6;LC:RefreshUI()')
    assert lua.eval('LC.ui.frame:GetWidth()')==680
    assert lua.eval('LC.ui.frame:GetHeight()')<400
    assert lua.eval('LC.ui.bar:IsShown()') is False
    assert 'Unknown' in lua.eval('LC.ui.gold[2].text')
    lua.execute('LC.page="inventory";LC:RefreshUI()')
    assert lua.eval('LC.ui.bar:IsShown()') is True
    lua.execute('MONEY=7650000;LC:RefreshHeader()')
    assert '765.0g' in lua.eval('LC.ui.gold[1].text')


def test_live_undercut_scan_requires_full_results_and_excludes_owned(lua):
    setup_route(lua)
    lua.execute('''LC:StartActivity('posting');local s=LC.db.activity;s.phase='undercuts'
    local task=LC.db.tasks[s.routes[1]];task.to_realm='gurubashi';LC.auctionOpen=true
    C_AuctionHouse.GetNumOwnedAuctions=function()return 1 end
    C_AuctionHouse.GetOwnedAuctionInfo=function()return {itemKey={itemID=2008,itemLevel=0,itemSuffix=0,battlePetSpeciesID=0},buyoutAmount=10000,quantity=1}end
    C_AuctionHouse.HasFullItemSearchResults=function()return false end
    C_AuctionHouse.GetNumItemSearchResults=function()return 2 end
    C_AuctionHouse.GetItemSearchResultInfo=function(key,index)return {buyoutAmount=index==1 and 100 or 9000,quantity=1,containsOwnerItem=index==1}end
    LC:CheckUndercut(task)
    for _,fn in ipairs(LC.events.ITEM_SEARCH_RESULTS_UPDATED) do fn({itemID=2008,itemLevel=0,itemSuffix=0,battlePetSpeciesID=0})end''')
    assert lua.eval('next(LC.db.activity.undercuts)') is None
    lua.execute('''C_AuctionHouse.HasFullItemSearchResults=function()return true end
    for _,fn in ipairs(LC.events.ITEM_SEARCH_RESULTS_UPDATED) do fn({itemID=2008,itemLevel=0,itemSuffix=0,battlePetSpeciesID=0})end''')
    assert lua.eval('LC.db.activity.undercuts["2008:0:0:0"].status')=='Undercut detected'
    assert lua.eval('LC.db.activity.undercuts["2008:0:0:0"].competitor_price')==9000


def test_posting_session_can_use_observed_outputs_from_completed_crafting(lua):
    lua.execute('''LC:CaptureRecipes();DrainTimers();local r=LC:Current().recipes[1]
    r.simulation={profit_copper=20000,observed_at=NOW};LC:StartActivity('craft');LC:StopActivity(true)
    LC.db.warbank={observed_at=NOW,money=10000000,items={{item_id=777,count=2,transferable=true}},complete=true}
    LC:StartActivity('posting')''')
    assert lua.eval('LC.db.activity.mode')=='posting'
    assert lua.eval('LC:SessionItems()[1].item_id')==777
    assert lua.eval('LC:SessionRealm()')=='Gurubashi'


def test_session_can_skip_unavailable_route_without_hanging(lua):
    setup_route(lua)
    lua.execute('LC:StartActivity("flip");LC:SkipSessionRoute(LC.db.activity.routes[1])')
    assert lua.eval('LC.db.activity.state')=='stopped'
    assert lua.eval('#LC.db.activity.routes')==0
