"""Price-backed recipe discovery. Missing unlock or simulation data stays explicit."""
import json
import time
from datetime import datetime
from . import db


def discovery(config):
    recipes=[];ids=set()
    for row in db.rows('SELECT r.owner,r.payload,c.name AS character,c.region,c.realm FROM addon_recipes r JOIN characters c ON c.id=r.owner WHERE c.region=?',(config.region,)):
        for recipe in json.loads(row['payload']):
            if not isinstance(recipe,dict) or not recipe.get('output_item_id'):continue
            recipes.append((row,recipe));ids.add(str(recipe['output_item_id']))
            for material in recipe.get('materials',[]):
                if isinstance(material,dict) and material.get('item_id'):ids.add(str(material['item_id']))
    observations=[];keys=sorted(ids)
    for start in range(0,len(keys),800):
        batch=keys[start:start+800]
        observations.extend(db.rows("SELECT * FROM observations WHERE region=? AND source LIKE 'tsm:%' AND item_key IN ("+','.join('?' for _ in batch)+')',(config.region,*batch)))
    by_item={};clock=time.time()
    for row in observations:
        limit=config.max_context_age_hours if row['scope']=='region' else config.max_age_hours
        if clock-datetime.fromisoformat(row['observed_at']).timestamp()>limit*3600:continue
        by_item.setdefault(row['item_key'],[]).append(row)
    result=[]
    for owner,recipe in recipes:
        output=by_item.get(str(recipe['output_item_id']),[])
        context=next((r for r in output if r['scope']=='region'),None)
        sales=context.get('sold_day') if context else None
        entry=dict(recipe,character=owner['character'],character_realm=owner['realm'],profit_copper=None,sold_day=sales,
            market_status='Fresh ingredient and output prices required',destination_realm=None,
            assumptions='Base-item estimate before quality, specialization, multicraft, resourcefulness and concentration. CraftSim remains authoritative for this character.')
        costs=[];observed=[];complete=bool(recipe.get('materials'))
        for material in recipe.get('materials',[]):
            # No implicit quality substitution: multi-quality recipes require a simulation.
            if len(material.get('alternatives',[]))>1:complete=False;break
            available=[r for r in by_item.get(str(material.get('item_id')),[]) if r['scope'] in ('commodity','realm') and r['buyout']>0]
            if not available:complete=False;break
            source=min(available,key=lambda r:r['buyout'])
            costs.append(source['buyout']*material.get('quantity',0));observed.append(source['observed_at'])
        candidates=[]
        if complete and context and sales and sales>=config.min_sold_day and 1/sales<=config.max_sale_days:
            for dest in output:
                if dest['scope'] not in ('commodity','realm') or dest['buyout']<=0:continue
                caps=[dest['buyout'],dest['market'],dest['historical'],context['market'],context['historical'],context.get('sale_price') or 0]
                exit_price=int(min(v for v in caps if v>0)*.9)
                yield_count=max(1,recipe.get('output_quantity') or 1)
                profit=int(exit_price*yield_count*(1-config.fee_percent/100))-sum(costs)-int(config.deposit_gold*10000)
                candidates.append((profit,dest))
        if candidates:
            profit,dest=max(candidates,key=lambda value:value[0]);observed.extend([dest['observed_at'],context['observed_at']])
            entry.update(profit_copper=profit,destination_realm=dest['realm'] or 'Region-wide commodities',material_cost_copper=sum(costs),
                market_status='Market estimate; verify character requirements in CraftSim',
                expires_at=int(min(datetime.fromisoformat(v).timestamp() for v in observed))+min(config.max_age_hours,config.max_context_age_hours)*3600)
        elif context and (not sales or sales<config.min_sold_day):entry['market_status']='Trading demand does not meet the configured threshold'
        result.append(entry)
    result.sort(key=lambda r:((r['profit_copper'] or 0)>0,(r['profit_copper'] or 0)*(r['sold_day'] or 0)),reverse=True)
    return result[:500]
