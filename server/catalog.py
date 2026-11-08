"""Region-wide auction clusters. The catalog is not selected by character realm."""
import json
from pathlib import Path
from . import db


def seed_catalog():
    path=Path(__file__).parent/'data'/'realms.json'
    if not path.exists():
        return
    data=json.loads(path.read_text())
    with db.connect() as conn:
        conn.executemany('INSERT OR IGNORE INTO realms VALUES(?,?,?,?)',
                         [(r['region'],r['slug'],r['name'],r['connected_id']) for r in data['realms']])
    if not db.get('catalog_provenance'):
        db.put('catalog_provenance',data['provenance'])


def markets(region):
    groups={}
    for r in db.rows('SELECT * FROM realms WHERE region=? ORDER BY slug',(region,)):
        groups.setdefault(r['connected_id'],[]).append(r)
    return [dict(connected_id=k,representative=next((r['slug'] for r in v if r.get('realm_id')==k),v[0]['slug']),
                 name=' / '.join(r['name'] for r in v),realms=v) for k,v in sorted(groups.items())]


def slug_for(name,region):
    key=''.join(c for c in name.casefold() if c.isalnum())
    for r in db.rows('SELECT slug,name FROM realms WHERE region=?',(region,)):
        if key in (''.join(c for c in r['name'].casefold() if c.isalnum()),''.join(c for c in r['slug'].casefold() if c.isalnum())):
            return r['slug']
    return None


def character_markets(region):
    result=set()
    for r in db.rows('SELECT realm FROM characters WHERE region=?',(region,)):
        slug=slug_for(r['realm'],region)
        if slug:
            cluster=db.rows('SELECT connected_id FROM realms WHERE region=? AND slug=?',(region,slug))
            if cluster:result.add(cluster[0]['connected_id'])
    return result


def parse_public_catalog(html):
    """Decode only documented-in-code public-page metadata, never execute page JS.

    React Router's flattened payload is not a stable TSM API. Schema changes fail
    closed, retaining the last catalog. Blizzard is authoritative when configured.
    Negative IDs are TSM AH IDs, never Blizzard endpoint IDs.
    """
    import re
    match=re.search(r'streamController.enqueue\(("(?:\\.|[^"\\])*")\)',html)
    if not match:raise ValueError('Public realm catalog layout changed')
    flat=json.loads(json.loads(match[1]))
    if not isinstance(flat,list) or len(flat)>100000:raise ValueError('Invalid catalog')
    names={v:i for i,v in enumerate(flat) if isinstance(v,str)}
    def prop(index,name):
        obj=flat[index]
        if not isinstance(obj,dict):raise ValueError('Unexpected catalog structure')
        value=obj.get('_'+str(names.get(name)), -5)
        return value if isinstance(value,int) and value>=0 else None
    root=prop(prop(prop(0,'loaderData'),'root'),'realmAuctionHouses')
    result=[]
    for entry in flat[root]:
        rid=prop(entry,'realm');aid=prop(entry,'auctionHouse')
        reg=prop(rid,'region')
        region=flat[prop(reg,'slug')]
        if region not in ('us','eu','kr','tw') or flat[prop(reg,'gameType')]!='retail':continue
        slug=flat[prop(rid,'slug')]
        if not isinstance(slug,str) or not slug or '/' in slug:raise ValueError('Invalid realm slug')
        result.append(dict(region=region,slug=slug,name=flat[prop(rid,'name')],connected_id=-int(flat[prop(aid,'id')])))
    if sum(r['region']=='us' for r in result)<100:raise ValueError('Incomplete region catalog')
    return result


def save_catalog(rows,provenance):
    # A complete TSM catalog is one namespace: do not mix its negative group IDs
    # with a partially updated Blizzard mapping. Blizzard stores its own mapping.
    with db.connect() as conn:
        conn.executemany('INSERT OR REPLACE INTO realms VALUES(?,?,?,?)',
            [(r['region'],r['slug'],r['name'],r['connected_id']) for r in rows])
    db.put('catalog_provenance',provenance)
