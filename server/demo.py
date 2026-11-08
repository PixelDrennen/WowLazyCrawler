"""Isolated synthetic presentation data. Never ingested or sent to the addon."""
from datetime import datetime,timezone,timedelta
import math
from .catalog import markets


def dataset(config):
    now=datetime.now(timezone.utc)
    stamp=lambda minutes:(now-timedelta(minutes=minutes)).isoformat()
    capture=lambda scope,minutes,count,money=0:dict(observed_at=int((now-timedelta(minutes=minutes)).timestamp()),count=count,money=money,complete=True,note='Synthetic demonstration capture',items=[])
    chars=[]
    for name,realm,cls,prof,gold,bags,bank,mail,auc in [
        ('Hanami','gurubashi','Hunter',['Alchemy','Leatherworking'],38250,146,18,12,16),
        ('Noraxei','gurubashi','Warrior',['Inscription','Enchanting'],18740,98,95,36,9),
        ('Ninachu','stormrage','Paladin',['Herbalism','Mining'],12600,202,28,None,0),
        ('Elesmere','area-52','Evoker',['Skinning','Tailoring'],9410,84,None,9,4)]:
        captures={'bags':capture('bags',bags%7, bags,int(gold*10000)),'auctions':capture('auctions',auc+4,auc)}
        if bank is not None:captures['bank']=capture('bank',bank,180+bank)
        if mail is not None:captures['mail']=capture('mail',mail,3,mail*110000)
        chars.append(dict(id='demo:'+name,account_id='demo',name=name,realm=realm,region='us',class_name=cls,level=90,professions=prof,last_sync=stamp(3),captures=captures))
    trades=[]
    for i,(name,source,dest,buy,sale,category) in enumerate([
        ('Silvermoon Drape','area-52','gurubashi',1240,2430,'Housing décor'),
        ('Plans: Ornate Garden Bench','stormrage','gurubashi',750,1820,'Recipe'),
        ('Carved Wooden Bookcase','gurubashi','proudmoore',980,1880,'Housing décor'),
        ('Garn Nighthowl','area-52','stormrage',1700,2940,'Mount'),
        ('Enchanted Wall Sconce','stormrage','gurubashi',420,995,'Housing décor'),
        ('Ancient Scholar’s Lectern','gurubashi','wyrmrest-accord',2200,3990,'Housing décor'),
        ('Pattern: Embroidered Curtains','proudmoore','gurubashi',640,1460,'Recipe'),
        ('Moonlit Garden Lantern','area-52','stormrage',890,1630,'Housing décor')]):
        net=sale*.95-buy-1
        trades.append(dict(item_key=str(900001+i),name=name,source_realm=source,destination_realm=dest,buyout=int(buy*10000),estimated_sale=int(sale*10000),net_profit=int(net*10000),roi=round(net/buy*100,1),sold_day=round(.08+.03*i,3),score=int(net*100),confidence='demo',category=category,source_covered=source in ['gurubashi','area-52','stormrage'],destination_covered=dest in ['gurubashi','area-52','stormrage'],observed_at=stamp(25),risks=['DEMO: invented prices and demand; not a trading recommendation.'],explanation='Synthetic review of a route the addon would guide in game.'))
    crafts=[]
    for i,(name,char,prof,qty,cost,profit,lumber,hours) in enumerate([
        ('Silvermoon Drape','Hanami','Leatherworking',4,2840,1820,'Thalassian Lumber',.42),
        ('Carved Wooden Bookcase','Elesmere','Tailoring',3,1960,1240,'Olemba Lumber',.28),
        ('Enchanted Wall Sconce','Noraxei','Enchanting',6,2100,1370,'Thalassian Lumber',.33)]):
        crafts.append(dict(id='demo-craft-'+str(i),name=name,character=char,profession=prof,category='Housing décor',crafts=qty,economic_cost=cost,cash_required=round(cost*.63),net_profit=profit,status='Simulated addon queue',concentration=80 if i==0 else 0,profit_per_concentration=2.4 if i==0 else None,assumptions='DEMO: invented recipe, cost and observed gathering rates.',materials=[dict(item_id=900100+i,required=120,owned=24,missing=96,unit_cost_gold=4,source='Demo stock')],lumber=lumber,lumber_missing=96,estimated_gather_minutes=round(hours*60)))
    rows=markets('us')
    own={'gurubashi','area-52','stormrage'}
    coverage=[]
    for i,m in enumerate(rows):
        owned=[c['name'] for c in chars if c['realm'] in {r['slug'] for r in m['realms']}]
        coverage.append(dict(m,owned=bool(owned),characters=owned,status='ready' if i<round(len(rows)*.92) else 'pending',observations=6400+(i*199)%9800,updated_at=stamp(15+i)))
    telemetry=[dict(at=(now-timedelta(hours=23-i)).isoformat(),observations=530000+int(125000*i/23)+int(4500*math.sin(i)),healthy=round(len(rows)*(.83+.09*i/23)),syncs=2+(i%5),inventory_gold=138000+i*900,queue_profit=6800+i*160) for i in range(24)]
    rates=[dict(item_id=900100+i,name=n,zone=z,source='Simulated Housing Lumber Tracker session',quantity=q,seconds=secs,samples=4+i,per_hour=q*3600/secs) for i,(n,z,q,secs) in enumerate([('Thalassian Lumber','Eversong Woods',312,2800),('Olemba Lumber','Terokkar Forest',224,2100),('Ironwood Lumber','Felwood',166,1800)])]
    tasks=[dict(id='demo-task-'+str(i),name=t['name'],character='Hanami' if i%2==0 else 'Noraxei',state=['retrieve','transfer','post','collect'][i%4],from_realm=t['source_realm'],to_realm=t['destination_realm'],net_profit=t['net_profit']) for i,t in enumerate(trades[:5])]
    return dict(materials=[dict(item_id=900100+i,name=rates[i]['name'],character=c['character'],required=120,owned=24,missing=96,is_lumber=True,gather=dict(minutes=c['estimated_gather_minutes'],source='Simulated lumber session')) for i,c in enumerate(crafts)],origin='demo',generated_at=now.isoformat(),characters=chars,warbanks=[dict(account_id='demo',observed_at=int(now.timestamp())-540,money=180000000,items=[],count=612,complete=True)],coverage=coverage,trades=trades,crafting=crafts,lumber=rates,tasks=tasks,telemetry=telemetry,integrations={'CraftSim':'Simulated · recipe estimates received','Auctionator':'Simulated · shopping list ready','Housing Lumber Tracker':'Simulated · session provider','LazyCrawler':'Simulated · waiting on next disk snapshot'},last_sync=stamp(3),events=[dict(at=stamp(i*7+3),kind=k,message=m,account_id='demo') for i,(k,m) in enumerate([('snapshot','Hanami · bags, mailbox and auctions observed'),('bank','Warband bank updated · shared once across characters'),('crafting','3 housing décor plans received from addon'),('lumber','Eversong Woods · gathering session recorded')])])
