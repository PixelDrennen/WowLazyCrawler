"""Validated addon observations. Unknown storage is never replaced by zero."""
import json
import time
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,field_validator,model_validator
from . import db
from .catalog import slug_for

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

class Item(Strict):
    item_id:int=Field(gt=0)
    name:str=Field(default='',max_length=300)
    count:int=Field(ge=1,le=1000000)
    link:str=Field(default='',max_length=2000)
    transferable:bool|None=None
    bound:bool|None=None
    cod:bool=False

class Storage(Strict):
    observed_at:int=Field(gt=0)
    items:list[Item]=Field(default_factory=list,max_length=20000)
    money:int=Field(default=0,ge=0,le=10**16)
    complete:bool=True
    note:str=Field(default='',max_length=500)
    @field_validator('observed_at')
    @classmethod
    def time_valid(cls,value):
        if value>time.time()+600:raise ValueError('Observation is in the future')
        return value

class LumberSession(Strict):
    item_id:int=Field(gt=0)
    quantity:int=Field(gt=0,le=1000000)
    seconds:float=Field(gt=0,le=86400*30)
    zone:str=Field(default='',max_length=150)
    source:str=Field(default='LazyCrawler observed session',max_length=150)
    @model_validator(mode='after')
    def enough_time(self):
        if self.seconds<10:raise ValueError('A lumber estimate needs at least ten seconds of observation')
        return self

class Character(Strict):
    name:str=Field(min_length=1,max_length=80)
    realm:str=Field(min_length=1,max_length=100)
    region:Literal['us','eu','kr','tw']='us'
    class_name:str=Field(default='',max_length=80)
    level:int=Field(default=1,ge=1,le=1000)
    professions:list[str]=Field(default_factory=list,max_length=20)
    storages:dict[Literal['bags','bank','reagents','mail','auctions','equipped','guild_bank'],Storage]=Field(default_factory=dict,max_length=7)
    recipes:list[dict]=Field(default_factory=list,max_length=10000)
    material_plan:list[dict]=Field(default_factory=list,max_length=20000)

class Snapshot(Strict):
    schema_version:Literal[2]
    account_id:str=Field(pattern=r'^[\w-]{1,100}$')
    addon_version:str=Field(max_length=40)
    loaded_bundle:str|None=Field(default=None,max_length=100)
    loaded_transport:Literal['file','clipboard']='file'
    characters:dict[str,Character]=Field(max_length=100)
    warbank:Storage|None=None
    warbank_group:str|None=Field(default=None,pattern=r'^[\w:-]{1,100}$')
    lumber:list[LumberSession]=Field(default_factory=list,max_length=2000)
    integrations:dict[str,str]=Field(default_factory=dict,max_length=30)
    tasks:list[dict]=Field(default_factory=list,max_length=1000)


def accept_snapshot(value,origin='companion'):
    snap=Snapshot.model_validate(value)
    stamp=db.now()
    with db.connect() as conn:
        for char_id,char in snap.characters.items():
            identity=snap.account_id+':'+char_id
            realm=slug_for(char.realm,char.region) or char.realm
            conn.execute('''INSERT INTO characters(id,account_id,name,realm,region,class_name,level,professions,last_sync)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,realm=excluded.realm,
                region=excluded.region,class_name=excluded.class_name,level=excluded.level,professions=excluded.professions,last_sync=excluded.last_sync''',
                (identity,snap.account_id,char.name,realm,char.region,char.class_name,char.level,json.dumps(char.professions),stamp))
            for scope,storage in char.storages.items():
                conn.execute('''INSERT INTO captures(owner,scope,observed_at,payload) VALUES(?,?,?,?)
                    ON CONFLICT(owner,scope) DO UPDATE SET observed_at=excluded.observed_at,payload=excluded.payload
                    WHERE excluded.observed_at>=captures.observed_at''',(identity,scope,storage.observed_at,storage.model_dump_json()))
            # Profession snapshots are facts from a client, not editable dashboard recipes.
            conn.execute('INSERT OR REPLACE INTO addon_recipes VALUES(?,?)',(identity,json.dumps(char.recipes)))
            conn.execute('INSERT OR REPLACE INTO addon_materials VALUES(?,?)',(identity,json.dumps(char.material_plan)))
        if snap.warbank is not None:
            region=next(iter(snap.characters.values())).region if snap.characters else 'unknown'
            group=snap.warbank_group or 'unresolved:'+region
            conn.execute('''INSERT INTO captures VALUES(?,?,?,?) ON CONFLICT(owner,scope) DO UPDATE
                SET observed_at=excluded.observed_at,payload=excluded.payload WHERE excluded.observed_at>=captures.observed_at''',
                (group,'warbank',snap.warbank.observed_at,snap.warbank.model_dump_json()))
        for entry in snap.lumber:
            payload=entry.model_dump_json()
            import hashlib
            digest=hashlib.sha256((snap.account_id+payload).encode()).hexdigest()
            conn.execute('INSERT OR IGNORE INTO lumber_samples VALUES(?,?,?,?)',(digest,snap.account_id,stamp,payload))
        for task in snap.tasks:
            if isinstance(task.get('id'),str) and isinstance(task.get('state'),str):
                conn.execute('INSERT OR REPLACE INTO addon_tasks VALUES(?,?,?,?)',(snap.account_id,task['id'][:200],stamp,json.dumps(task)))
        conn.execute('INSERT INTO sync_events(at,account_id,kind,message) VALUES(?,?,?,?)',
                     (stamp,snap.account_id,'snapshot',f'{len(snap.characters)} characters received from {origin}'))
        conn.execute('DELETE FROM sync_events WHERE id NOT IN (SELECT id FROM sync_events ORDER BY id DESC LIMIT 500)')
        balances={scope:0 for scope in ('bags','warbank','mail')}
        for row in conn.execute("SELECT scope,payload FROM captures WHERE scope IN ('bags','warbank','mail')"):
            balances[row['scope']]+=json.loads(row['payload']).get('money',0)
        telemetry=dict(inventory_gold=(balances['bags']+balances['warbank'])/10000,mail_gold=balances['mail']/10000,
            observations=conn.execute('SELECT COUNT(*) FROM observations').fetchone()[0],
            healthy=conn.execute("SELECT COUNT(*) FROM sources WHERE status IN ('ready','unchanged')").fetchone()[0])
        conn.execute('INSERT OR REPLACE INTO telemetry VALUES(?,?)',(stamp,json.dumps(telemetry)))
    db.put('last_addon_sync',stamp)
    db.put('last_addon_version',snap.addon_version)
    if snap.loaded_bundle:db.put('last_loaded_bundle',dict(generated_at=snap.loaded_bundle,observed_at=stamp,account_id=snap.account_id,transport=snap.loaded_transport))
    db.put('addon_integrations',snap.integrations)
    return dict(characters=len(snap.characters),accepted_at=stamp)


def characters():
    result=db.rows('SELECT * FROM characters ORDER BY name')
    for char in result:
        char['professions']=json.loads(char['professions'])
        char['captures']={}
        for row in db.rows('SELECT * FROM captures WHERE owner=?',(char['id'],)):
            data=json.loads(row['payload'])
            char['captures'][row['scope']]=dict(observed_at=row['observed_at'],count=sum(i['count'] for i in data['items']),
                money=data['money'],complete=data['complete'],items=data['items'],note=data['note'])
    return result


def shared_storage():
    return [dict(account_id=r['owner'],**json.loads(r['payload'])) for r in db.rows("SELECT * FROM captures WHERE scope='warbank'")]


def lumber_rates():
    groups={}
    for row in db.rows('SELECT payload FROM lumber_samples'):
        sample=json.loads(row['payload']);key=(sample['item_id'],sample['zone'],sample['source'])
        group=groups.setdefault(key,dict(item_id=key[0],zone=key[1],source=key[2],quantity=0,seconds=0,samples=0))
        group['quantity']+=sample['quantity'];group['seconds']+=sample['seconds'];group['samples']+=1
    return [dict(g,per_hour=g['quantity']*3600/g['seconds']) for g in groups.values()]
