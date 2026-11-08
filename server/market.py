"""Pure adapters and explainable conservative estimates; copper throughout."""
import csv
import io
import math
import heapq
from datetime import datetime, timezone


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Upstream timestamps must include a timezone')
    if dt.timestamp() > datetime.now(timezone.utc).timestamp() + 600:
        raise ValueError('Upstream scan timestamp is in the future')
    return dt.isoformat()


def parse_tsm(text, region, scope, realm, source, fetched):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required = {'itemId', 'name', 'marketValue', 'historical', 'updatedAt'}
    if scope != 'region':
        required.add('minBuyout')
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('TSM CSV schema changed or is invalid; previous snapshot retained')
    output = []
    def money(row, key):
        value = int(row.get(key) or 0)
        if value < 0 or value > 9_000_000_000_000_000:
            raise ValueError('Invalid copper amount')
        return value
    def metric(row, key):
        value = row.get(key)
        if value in (None, ''):
            return None
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError('Invalid demand metric')
        return number
    for row in reader:
        item = int(row['itemId'])
        if item <= 0:
            raise ValueError('Invalid item identity')
        output.append((region, scope, realm, str(item), row['name'][:300], money(row, 'minBuyout'),
                       money(row, 'marketValue'), money(row, 'historical'),
                       money(row, 'avgSalePrice') if row.get('avgSalePrice') else None,
                       metric(row, 'saleRate'), metric(row, 'soldPerDay'), None,
                       timestamp(row['updatedAt']), fetched, source))
    if not output:
        raise ValueError('Empty upstream snapshot; previous data retained')
    return output


def blizzard_key(item):
    # Preserve all identity fields, including bonus lists, pet stats and modifiers.
    import json
    return json.dumps(item, sort_keys=True, separators=(',', ':'))


def parse_blizzard(payload, region, scope, realm, source, observed, fetched):
    if not isinstance(payload.get('auctions'), list):
        raise ValueError('Invalid Blizzard auction snapshot')
    prices = {}
    for auction in payload['auctions']:
        price = auction.get('unit_price') if scope == 'commodity' else auction.get('buyout')
        if not price:  # Bid-only auctions are not executable buyouts.
            continue
        quantity = int(auction['quantity'])
        if quantity <= 0 or int(price) < 0:
            raise ValueError('Invalid auction amount')
        key = str(auction['item']['id']) if scope == 'commodity' else blizzard_key(auction['item'])
        # Realm buyout is the entire auction, not a unit price. Never create a fictitious fractional purchase.
        entry = prices.setdefault(key, [int(price), 0])
        entry[0] = min(entry[0], int(price))
        entry[1] += quantity
    return [(region, scope, realm, key, 'Item ' + (key if scope == 'commodity' else str(__import__('json').loads(key)['id'])),
             price, 0, 0, None, None, None, quantity, observed, fetched, source)
            for key, (price, quantity) in prices.items()]


def opportunities(observations, settings, transferable, clock=None, realm_groups=None):
    clock = clock or datetime.now(timezone.utc).timestamp()
    groups, regional = {}, {}
    for row in observations:
        age_limit = settings.max_context_age_hours if row['scope'] == 'region' else settings.max_age_hours
        if clock - datetime.fromisoformat(row['observed_at']).timestamp() > age_limit * 3600:
            continue
        if row['scope'] == 'region':
            regional[row['item_key']] = row
        elif row['scope'] == 'realm' and row['source'].startswith('tsm:') and row['buyout'] > 0:
            groups.setdefault(row['item_key'], []).append(row)
    results = []
    sequence=0
    for key, realms in groups.items():
        context = regional.get(key)
        if not context or not context['sold_day'] or context['sold_day'] < settings.min_sold_day:
            continue
        if 1 / context['sold_day'] > settings.max_sale_days:
            continue
        # Collapse shared houses once and retain only the two cheapest distinct
        # sources needed for each destination. Region-wide work stays O(rows log R),
        # rather than building a new O(R) candidate list for every destination.
        by_cluster={}
        for row in realms:
            cluster=(realm_groups or {}).get(row['realm'],row['realm'])
            if cluster not in by_cluster or row['buyout']<by_cluster[cluster]['buyout']:
                by_cluster[cluster]=row
        realms=sorted(by_cluster.values(),key=lambda r:r['buyout'])
        owned_sources=[r for r in realms if r['realm'] in settings.selling_realms]
        if transferable.get(key) is False:
            continue
        for dest in realms:
            # Connected realms share one AH; unknown cluster mapping is explicitly flagged.
            pool=realms if dest['realm'] in settings.selling_realms else owned_sources
            destination_cluster=(realm_groups or {}).get(dest['realm'],dest['realm'])
            src=next((r for r in pool[:2] if (realm_groups or {}).get(r['realm'],r['realm'])!=destination_cluster),None)
            if src is None:
                continue
            caps = [dest['buyout'], dest['market'], dest['historical'], context['market'], context['historical']]
            if context['sale_price']:
                caps.append(context['sale_price'])
            caps = [p for p in caps if p > 0]
            if not caps:
                continue
            exit_price = int(min(caps) * .9)
            net = int(exit_price * (1 - settings.fee_percent/100)) - src['buyout'] - int(settings.deposit_gold * 10000)
            roi = net / src['buyout'] * 100
            if net < settings.min_profit_gold * 10000 or roi < settings.min_roi:
                continue
            if src['buyout'] > min(settings.budget_gold, settings.max_item_gold) * 10000:
                continue
            risks = ['TSM base-item prices do not resolve variants; verify exact item and live buyout.',
                     'Regional sold/day is a population metric, not your expected realm sales.']
            verified = transferable.get(key) is True
            if not verified:
                risks.append('Transfer eligibility unverified: check binding and Warband Bank eligibility in game.')
            if not (realm_groups or {}).get(src['realm']) or not (realm_groups or {}).get(dest['realm']):
                risks.append('Connected-realm mapping unavailable; verify these are separate auction houses.')
            if dest['buyout'] > exit_price * 3:
                risks.append('Destination listing is far above conservative valuation.')
            confidence = 'review' if not verified else 'estimated'
            score = net * min(context['sold_day'], 1) / (1 + len(risks))
            if len(results)>=500 and score<=results[0][0]:
                continue
            entry=dict(source_covered=src['realm'] in settings.selling_realms,destination_covered=dest['realm'] in settings.selling_realms,item_key=key, name=src['name'], source_realm=src['realm'], destination_realm=dest['realm'],
                buyout=src['buyout'], estimated_sale=exit_price, net_profit=net, roi=round(roi,1),
                sold_day=context['sold_day'], score=round(score), confidence=confidence, risks=risks,
                observed_at=min(src['observed_at'], dest['observed_at'], context['observed_at']),
                explanation='Estimated exit = 90% of lowest available destination/regional historical, market, sale and buyout values. Fees and deposit reserve deducted.')
            sequence+=1
            if len(results)<500:heapq.heappush(results,(score,sequence,entry))
            else:heapq.heapreplace(results,(score,sequence,entry))
    return [row[2] for row in sorted(results,key=lambda row:(-row[0],row[1]))]


def crafting_plan(recipe, settings, commodity_prices):
    materials, cost, cash = [], 0, 0
    for material in recipe.materials:
        market = commodity_prices.get(str(material.item_id))
        unit = material.unit_cost_gold
        if unit is None and market:
            unit = market['buyout'] / 10000
        needed = material.quantity * recipe.crafts
        missing = max(0, needed - material.owned)
        if unit is None or unit <= 0:
            return dict(id=recipe.id, name=recipe.name, status='missing prices', materials=[], net_profit=None)
        cost += needed * unit
        cash += missing * unit
        materials.append(dict(item_id=material.item_id, required=needed, owned=material.owned, missing=missing,
                              unit_cost_gold=unit, source='manual' if material.unit_cost_gold is not None else 'TSM commodities'))
    revenue = recipe.sale_price_gold * recipe.expected_yield * recipe.crafts * (1-settings.fee_percent/100)
    profit = revenue - cost - recipe.crafts*settings.deposit_gold
    concentration = recipe.concentration * recipe.crafts
    incremental = None if recipe.baseline_profit_gold is None else profit - recipe.baseline_profit_gold
    return dict(id=recipe.id, name=recipe.name, character=recipe.character, profession=recipe.profession,
                status='manual simulation', crafts=recipe.crafts, materials=materials, economic_cost=cost,
                cash_required=cash, net_profit=profit, revenue_after_fee=revenue, concentration=concentration,
                incremental_profit=incremental, profit_per_concentration=incremental/concentration if concentration and incremental is not None else None,
                assumptions=recipe.assumptions)
