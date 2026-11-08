from datetime import datetime, timezone
import pytest
from server.market import parse_tsm,parse_blizzard,opportunities,crafting_plan
from server.models import Settings,Recipe

STAMP=datetime.now(timezone.utc).isoformat()

def row(realm,price,scope='realm',sold=None):
    return dict(region='us',scope=scope,realm=realm,item_key='123',name='Test item',buyout=price,
        market=price,historical=price,sale_price=None,sale_rate=None,sold_day=sold,quantity=None,
        observed_at=STAMP,fetched_at=STAMP,source='tsm:us:'+scope+':'+realm)


def test_csv_current_schema_copper_and_missing_metrics():
    values=parse_tsm('itemId,name,marketValue,minBuyout,historical,updatedAt\n123,Test,20000,10000,20000,'+STAMP,'us','realm','area-52','tsm:x',STAMP)
    assert values[0][5]==10000
    assert values[0][10] is None


def test_regional_demand():
    values=parse_tsm('itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt\n123,Test,20000,20000,18000,0.1,2.5,'+STAMP,'us','region','','tsm:x',STAMP)
    assert values[0][8:11]==(18000,.1,2.5)


@pytest.mark.parametrize('csv', ['<html>error</html>','itemId,name,marketValue,minBuyout,historical,updatedAt\n123,Test,-1,1,1,'+STAMP,
    'itemId,name,marketValue,minBuyout,historical,updatedAt\n123,Test,1,1,1,2099-01-01T00:00:00Z'])
def test_invalid_upstream_rejected(csv):
    with pytest.raises(ValueError):parse_tsm(csv,'us','realm','a','tsm:x',STAMP)


def test_commodity_never_cross_realm_and_unknown_demand_excluded():
    config=Settings(realms=['a','b'],selling_realms=['b'],min_profit_gold=0,min_roi=0)
    data=[row('a',10000),row('b',1000000),row('',1000000,'commodity',20)]
    assert not opportunities(data,config,{})
    data.append(row('',1000000,'region',2))
    result=opportunities(data,config,{})
    assert len(result)==1 and result[0]['net_profit']==835000
    assert result[0]['confidence']=='review'
    assert not opportunities(data,config,{},realm_groups={'a':1,'b':1})


def test_conservative_caps_and_budget_and_staleness():
    config=Settings(realms=['a','b'],selling_realms=['b'],min_profit_gold=0,min_roi=0,max_item_gold=1)
    data=[row('a',20000),row('b',1000000),row('',1000000,'region',2)]
    assert not opportunities(data,config,{})
    config.max_item_gold=100
    data[-1]['sale_price']=10000
    assert not opportunities(data,config,{})
    data[-1]['sale_price']=None
    data[0]['observed_at']='2020-01-01T00:00:00+00:00'
    assert not opportunities(data,config,{})


def test_blizzard_preserves_variants_and_excludes_bids():
    values=parse_blizzard({'auctions':[{'item':{'id':1,'bonus_lists':[2]},'buyout':10000,'quantity':2},
        {'item':{'id':1,'bonus_lists':[3]},'buyout':20000,'quantity':1},
        {'item':{'id':2},'bid':30,'quantity':1}]},'us','realm','1','blizzard:1',STAMP,STAMP)
    assert len(values)==2 and values[0][3]!=values[1][3]
    assert values[0][5]==10000  # Entire lot, never a fictitious fractional purchase.


def test_owned_stock_not_free_and_concentration_incremental():
    recipe=Recipe(id='x',name='Test',output_item_id=1,crafts=2,expected_yield=1,sale_price_gold=100,
        concentration=10,baseline_profit_gold=50,materials=[{'item_id':2,'quantity':2,'owned':3,'unit_cost_gold':10}])
    plan=crafting_plan(recipe,Settings(),{})
    assert plan['economic_cost']==40
    assert plan['cash_required']==10
    assert plan['net_profit']==148
    assert plan['profit_per_concentration']==4.9


def test_missing_prices_do_not_invent_profit():
    recipe=Recipe(id='x',name='Test',output_item_id=1,sale_price_gold=100,materials=[{'item_id':2,'quantity':1}])
    assert crafting_plan(recipe,Settings(),{})['net_profit'] is None
