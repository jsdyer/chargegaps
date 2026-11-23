#!/usr/bin/env python3
"""Compile explicitly open-licensed OCM country exports; no API key required."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://github.com/openchargemap/ocm-export.git'
COLUMNS = ['id','title','lat','lon','country','region','town','address','operator','usage','status','verified','updated','provider','connections','cost']

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def clean(value, limit=500):
    return str(value).strip()[:limit] if value is not None else ''

def numeric(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def validate_config(c):
    countries=c.get('countries')
    if not isinstance(countries,list) or not countries or len(countries)>20 or len(set(countries))!=len(countries) or any(not isinstance(x,str) or not re.fullmatch('[A-Z]{2}',x) for x in countries):
        raise ValueError('countries must contain 1–20 distinct uppercase ISO country codes')
    for key,low,high in [('retainedCaptures',1,52),('minimumRecords',1,150000),('maximumRecords',1,1000000),('pageSize',1,100),('maxMapPoints',1,5000)]:
        if not isinstance(c.get(key),int) or not low<=c[key]<=high: raise ValueError(f'Invalid {key}')
    if not numeric(c.get('maximumDropFraction')) or not 0<=c['maximumDropFraction']<=1:raise ValueError('Invalid maximumDropFraction')
    return c

def normalize(poi,country,reference):
    if not isinstance(poi,dict) or not isinstance(poi.get('ID'),int) or poi['ID']<=0:raise ValueError('Invalid POI ID')
    provider=reference['DataProviders'].get(poi.get('DataProviderID'))
    # Other providers' contributions do not inherit OCM's contributor licence.
    if not provider or provider.get('IsOpenDataLicensed') is not True or not provider.get('License'):return None,'licence'
    a=poi.get('AddressInfo') or {}
    country_row=reference['Countries'].get(a.get('CountryID'))
    if not country_row or country_row.get('ISOCode')!=country:raise ValueError('Country folder and POI country disagree')
    lat,lon=a.get('Latitude'),a.get('Longitude')
    if not numeric(lat) or not numeric(lon) or not -90<=lat<=90 or not -180<=lon<=180:return None,'coordinates'
    connections=[]
    for item in poi.get('Connections') or []:
        if not isinstance(item,dict):raise ValueError('Invalid connection record')
        kw=item.get('PowerKW');q=item.get('Quantity')
        connections.append([item.get('ConnectionTypeID'),kw if numeric(kw) and kw>=0 else None,q if isinstance(q,int) and q>=0 else None,item.get('StatusTypeID')])
    values=[poi['ID'],clean(a.get('Title')) or f"OCM {poi['ID']}",round(lat,7),round(lon,7),country,clean(a.get('StateOrProvince')),clean(a.get('Town')),clean(a.get('AddressLine1')),poi.get('OperatorID'),poi.get('UsageTypeID'),poi.get('StatusTypeID'),clean(poi.get('DateLastVerified')),clean(poi.get('DateLastStatusUpdate')),poi.get('DataProviderID'),connections,clean(poi.get('UsageCost'),1500)]
    return values,None

def compile_data(source,c,stamp,commit,source_date):
    raw=read(source/'data/referencedata.json')
    needed=['Countries','DataProviders','Operators','UsageTypes','StatusTypes','ConnectionTypes']
    ref={key:{r['ID']:r for r in raw[key]} for key in needed}
    records=[];seen=set();excluded={'licence':0,'coordinates':0};country_counts={};input_count=0
    for country in c['countries']:
        folder=source/'data'/country
        files=sorted(folder.glob('*.json'))
        if not files:raise ValueError(f'No source files for {country}')
        country_counts[country]=0
        for path in files:
            input_count+=1
            row,reason=normalize(read(path),country,ref)
            if reason:excluded[reason]+=1;continue
            if row[0] in seen:raise ValueError('Duplicate OCM ID')
            seen.add(row[0]);records.append(row);country_counts[country]+=1
    if not c['minimumRecords']<=len(records)<=c['maximumRecords']:raise ValueError('Record count outside configured safeguards')
    records.sort(key=lambda r:r[0])
    operators={str(r[8]) for r in records};providers={str(r[13]) for r in records};connection_types={str(x[0]) for r in records for x in r[14]}
    lookups={
      'operators':{str(k):clean(v.get('Title')) for k,v in ref['Operators'].items() if str(k) in operators},
      'connectors':{str(k):clean(v.get('Title')) for k,v in ref['ConnectionTypes'].items() if str(k) in connection_types},
      'usage':{str(k):clean(v.get('Title')) for k,v in ref['UsageTypes'].items()},
      'status':{str(k):clean(v.get('Title')) for k,v in ref['StatusTypes'].items()},
      'providers':{str(k):{'title':clean(v.get('Title')),'license':clean(v.get('License'),4000),'url':clean(v.get('WebsiteURL'))} for k,v in ref['DataProviders'].items() if str(k) in providers}}
    return {'schema':'coolcode.chargegaps.v1','capturedAt':stamp,'sourceCommit':commit,'sourceUpdatedAt':source_date,'coverage':sorted(c['countries']),'countryCounts':country_counts,'sourceRecords':input_count,'excluded':excluded,'columns':COLUMNS,'lookup':lookups,'records':records,'source':'https://github.com/openchargemap/ocm-export'}

def changes(previous,current):
    if previous is None:return {'kind':'baseline','added':0,'absent':0,'changed':0}
    if previous.get('coverage')!=current['coverage']:return {'kind':'coverage-changed','added':0,'absent':0,'changed':0}
    old={r[0]:r for r in previous['records']};new={r[0]:r for r in current['records']}
    return {'kind':'comparable','added':len(new.keys()-old.keys()),'absent':len(old.keys()-new.keys()),'changed':sum(old[k]!=new[k] for k in old.keys()&new.keys())}

def run_git(source,*args):
    return subprocess.run(['git','-C',str(source),*args],check=True,text=True,capture_output=True).stdout.strip()

def refresh(root=ROOT,source=None):
    c=validate_config(read(root/'web/config.json'))
    source=source or root/'.cache/ocm-export'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','clone','--depth','1','--filter=blob:none','--sparse',SOURCE,str(source)],check=True)
    else:
        run_git(source,'fetch','--depth','1','origin','main')
        run_git(source,'reset','--hard','FETCH_HEAD')
    run_git(source,'sparse-checkout','set',*[f'data/{code}' for code in c['countries']])
    commit=run_git(source,'rev-parse','HEAD');source_date=run_git(source,'show','-s','--format=%cI','HEAD')
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    data=root/'web/data';data.mkdir(exist_ok=True)
    index=read(data/'index.json') if (data/'index.json').exists() else {'schema':'coolcode.chargegaps.index.v1','captures':[]}
    previous=None
    if index['captures']:
        old=index['captures'][0]
        previous=json.loads(gzip.decompress((data/old['file']).read_bytes()))
        if previous['sourceCommit']==commit and previous['coverage']==sorted(c['countries']):
            index['checkedAt']=stamp;(data/'index.json').write_text(json.dumps(index,indent=2)+'\n');print('Source edition unchanged; successful check saved.');return
    new=compile_data(source,c,stamp,commit,source_date)
    if previous and previous['coverage']==new['coverage'] and len(new['records'])<len(previous['records'])*(1-c['maximumDropFraction']):raise ValueError('Unexpected source shrink; previous files preserved')
    new['changes']=changes(previous,new)
    payload=json.dumps(new,ensure_ascii=False,separators=(',',':')).encode();packed=gzip.compress(payload,mtime=0)
    name='captures/'+stamp.replace('-','').replace(':','')+'-'+commit[:8]+'.json.gz'
    entry={'file':name,'capturedAt':stamp,'sourceUpdatedAt':source_date,'sourceCommit':commit,'count':len(new['records']),'coverage':new['coverage'],'sha256':hashlib.sha256(packed).hexdigest(),'expandedBytes':len(payload)}
    index.update(checkedAt=stamp,captures=([entry]+index['captures'])[:c['retainedCaptures']])
    # Stage a complete generation before replacing any published file.
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        stage=Path(tmp)/'data';shutil.copytree(data,stage)
        (stage/'captures').mkdir(exist_ok=True);(stage/name).write_bytes(packed)
        keep={x['file'] for x in index['captures']}
        for file in (stage/'captures').glob('*.gz'):
            if file.relative_to(stage).as_posix() not in keep:file.unlink()
        (stage/'index.json').write_text(json.dumps(index,indent=2)+'\n')
        for file in stage.rglob('*'):
            if file.is_file():
                dest=data/file.relative_to(stage);dest.parent.mkdir(parents=True,exist_ok=True);file.replace(dest)
        for file in (data/'captures').glob('*.gz'):
            if file.relative_to(data).as_posix() not in keep:file.unlink()
    print(f"Saved {len(new['records']):,} licensed, geolocated records; excluded {new['excluded']}; source edition {source_date}.")

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);args=p.parse_args();refresh(source=args.source)
