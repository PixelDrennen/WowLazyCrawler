"""Read models for administration. Player decisions and queues live in the addon."""
import json
import time
from datetime import datetime,timezone
from . import db
from .catalog import markets,character_markets
from .snapshots import characters,shared_storage,lumber_rates


def live_crafting(config):
    rows=[];rates=lumber_rates()
    for entry in db.rows('SELECT owner,payload FROM addon_recipes'):
        owner=db.rows('SELECT name,professions FROM characters WHERE id=?',(entry['owner'],))
        if not owner:continue
        recipes=json.loads(entry['payload'])
        for recipe in recipes[:1000]:
            if not isinstance(recipe,dict):continue
            simulation=recipe.get('simulation') or {}
            profit=simulation.get('profit_copper')
            if not isinstance(profit,(float,int)) or not __import__('math').isfinite(profit):profit=None
            materials=[]
            for mat in recipe.get('materials',[])[:100]:
                if not isinstance(mat,dict):continue
                materials.append(dict(item_id=mat.get('item_id'),required=mat.get('quantity',0),missing=mat.get('missing'),owned=mat.get('owned'),alternatives=mat.get('alternatives',[])))
            rows.append(dict(id=str(recipe.get('id','')),name=str(recipe.get('name','Unknown recipe')),character=owner[0]['name'],
                profession=str(recipe.get('profession','')),category='Housing décor' if recipe.get('is_decor') is True else 'Crafting',
                crafts=recipe.get('crafts',0),economic_cost=None,cash_required=None,net_profit=None if profit is None else profit/10000,
                status='CraftSim observation' if profit is not None else 'Awaiting character simulation',materials=materials,
                assumptions='Read from the addon. Profit is per craft from CraftSim when available; no specialization or quality is invented.',
                concentration=recipe.get('concentration'),profit_per_concentration=None))
    return rows[:500]


def gather_estimate(item_id,missing,rates=None):
    if missing<=0:return dict(minutes=0,source='Inventory covers requirement',per_hour=None)
    available=[r for r in (rates if rates is not None else lumber_rates()) if r['item_id']==item_id and r['per_hour']>0]
    if not available:return dict(minutes=None,source='Gathering session required',per_hour=None)
    best=max(available,key=lambda r:r['per_hour'])
    return dict(minutes=round(missing/best['per_hour']*60,1),source=best['source'],zone=best['zone'],per_hour=round(best['per_hour'],1),
                confidence='limited sample' if best['samples']<3 else 'observed estimate',seconds_observed=best['seconds'])


def live_view(config,trade_provider):
    chars=characters();shared=shared_storage();owned=character_markets(config.region)
    feeds={r['id']:r for r in db.rows('SELECT s.*,MIN(o.observed_at) AS observed_at FROM sources s LEFT JOIN observations o ON o.source=s.id GROUP BY s.id')}
    coverage=[]
    for market in markets(config.region):
        source=feeds.get(f"tsm:{config.region}:realm:{market['representative']}")
        status=source['status'] if source else 'pending'
        if source and source['observed_at']:
            age=time.time()-datetime.fromisoformat(source['observed_at']).timestamp()
            if age>config.max_age_hours*3600:status='stale'
        members={r['slug'] for r in market['realms']}
        coverage.append(dict(market,owned=market['connected_id'] in owned,characters=[c['name'] for c in chars if c['region']==config.region and c['realm'] in members],
            status=status,observations=source['rows'] if source else 0,updated_at=source['observed_at'] if source else None))
    telemetry=[dict(at=r['at'],**json.loads(r['payload'])) for r in db.rows('SELECT * FROM telemetry ORDER BY at DESC LIMIT 96')][::-1]
    material_plan=[]
    rates=lumber_rates()
    for row in db.rows('SELECT * FROM addon_materials'):
        char=next((c for c in chars if c['id']==row['owner']),None)
        for material in json.loads(row['payload'])[:20000]:
            if not isinstance(material,dict) or not isinstance(material.get('item_id'),int):continue
            missing=material.get('missing')
            if not isinstance(missing,(int,float)) or missing<0:continue
            entry=dict(material,character=char['name'] if char else row['owner'])
            if material.get('is_lumber'):entry['gather']=gather_estimate(material['item_id'],missing,rates)
            material_plan.append(entry)
    return dict(materials=material_plan,origin='live' ,generated_at=db.now(),characters=chars,warbanks=shared,coverage=coverage,trades=trade_provider(),
        crafting=live_crafting(config),lumber=lumber_rates(),tasks=[json.loads(r['payload']) for r in db.rows('SELECT payload FROM addon_tasks ORDER BY at DESC')],
        telemetry=telemetry,integrations=db.get('addon_integrations',{}),last_sync=db.get('last_addon_sync'),
        events=db.rows('SELECT * FROM sync_events ORDER BY id DESC LIMIT 30'))
