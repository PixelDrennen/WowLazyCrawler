"""Explain empty market results without conflating transport with price readiness."""
from datetime import datetime, timedelta, timezone
from . import db
from .catalog import markets, character_markets


def market_readiness(config, candidate_count, scanning=False):
    catalog=markets(config.region)
    owned=character_markets(config.region)
    groups={m['representative']:m['connected_id'] for m in catalog}
    price_cutoff=(datetime.now(timezone.utc)-timedelta(hours=config.max_age_hours)).isoformat()
    context_cutoff=(datetime.now(timezone.utc)-timedelta(hours=config.max_context_age_hours)).isoformat()
    rows=db.rows('''SELECT scope,realm,COUNT(*) AS rows,
        SUM(CASE WHEN julianday(observed_at)>=julianday(CASE WHEN scope='region' THEN ? ELSE ? END) THEN 1 ELSE 0 END) AS fresh_rows
        FROM observations WHERE region=? AND source LIKE 'tsm:%' GROUP BY scope,realm''',
        (context_cutoff,price_cutoff,config.region)) if config.tsm_enabled else []
    region_rows=sum(r['rows'] for r in rows if r['scope']=='region')
    fresh_context=sum(r['fresh_rows'] for r in rows if r['scope']=='region')
    realm_rows=sum(r['rows'] for r in rows if r['scope']=='realm')
    fresh_markets={groups[r['realm']] for r in rows if r['scope']=='realm' and r['fresh_rows']>0 and r['realm'] in groups}
    source_errors=db.rows("SELECT id,error,last_attempt FROM sources WHERE id LIKE ? AND status='error' ORDER BY last_attempt DESC LIMIT 8",(f'tsm:{config.region}:%',))
    jobs=db.rows('SELECT status,message FROM jobs ORDER BY id DESC LIMIT 1')
    diagnostics=dict(region=config.region,state='ready',title='Market data ready',message='Qualified routes are available in Radar.',
        action='Review candidates and verify live prices before purchasing.',candidate_count=candidate_count,
        regional_rows=region_rows,fresh_regional_rows=fresh_context,realm_rows=realm_rows,
        fresh_markets=len(fresh_markets),total_markets=len(catalog),owned_markets=len(owned),
        fresh_owned_markets=len(fresh_markets & owned),scanning=scanning,source_errors=source_errors,last_job=jobs[0] if jobs else None,
        filters=dict(min_profit_gold=config.min_profit_gold,min_roi=config.min_roi,max_item_gold=config.max_item_gold,
            budget_gold=config.budget_gold,min_sold_day=config.min_sold_day,max_sale_days=config.max_sale_days,
            max_age_hours=config.max_age_hours,max_context_age_hours=config.max_context_age_hours))
    if not config.tsm_enabled:
        diagnostics.update(state='pricing_disabled',title='Route pricing is disabled',message='Realm-flip estimates currently require the TSM price and regional-demand feeds. Blizzard snapshots alone do not provide that demand context.',action='Enable TSM public feeds in desktop Configuration, then run a region refresh.')
    elif not region_rows or not realm_rows:
        diagnostics.update(state='prices_missing',title='Market prices are missing',message='Character captures and market prices are separate. Opening bags, banks and auctions does not download region-wide prices.',action='In the desktop Command center, run a region refresh. Review Server health if feeds fail; then copy the latest market data into /lc import (no reload needed).')
    elif not fresh_context or len(fresh_markets)<2:
        diagnostics.update(state='prices_stale',title='Not enough fresh market data',message='Routes require fresh regional demand and prices from at least two distinct auction markets.',action='Run a region refresh in the desktop app and inspect source errors. Existing captures are preserved; stale prices do not become recommendations.')
    elif not owned:
        diagnostics.update(state='characters_missing',title='No character market identified',message='No imported character maps to a known auction market in this region.',action='Check the desktop region setting and character captures. Log into a character, /reload to export, and let Companion import it.')
    elif not fresh_markets & owned:
        diagnostics.update(state='home_prices_missing',title='Your character markets have no fresh prices',message='Other realm feeds exist, but none of your characters’ auction markets has fresh price evidence.',action='Run a region refresh and inspect the feeds for your character markets in Market coverage.')
    elif not candidate_count:
        diagnostics.update(state='no_matches',title='No qualifying routes',message='Fresh prices exist. No route involving your character markets passed the current price, demand, freshness, budget and profit filters.',action='Review the filters in desktop Configuration and feed coverage. Zero matches is a valid result; prices and profits are never invented.')
    if scanning:
        diagnostics['action']='A region refresh is running. Watch its progress in desktop Server health; copy the latest market data into /lc import when it completes.'
    return diagnostics
