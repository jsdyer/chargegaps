import {distance} from './model.mjs';
export function decodeAFDC(raw) {
  if(raw?.schema!=='coolcode.chargegaps.afdc.v1'||!Number.isFinite(Date.parse(raw.checkedAt))||
     JSON.stringify(raw.coverage)!=='["CA"]'||!Array.isArray(raw.records)||raw.records.length!==raw.recordCount) throw Error('Unsupported AFDC capture.');
  const ids=new Set();
  for(const r of raw.records) {
    if(!Number.isSafeInteger(r.id)||r.id<=0||ids.has(r.id)||!Number.isFinite(r.lat)||Math.abs(r.lat)>90||!Number.isFinite(r.lon)||Math.abs(r.lon)>180||
       !['title','town','region','network','status','access','confirmed','updated','pricing'].every(k=>typeof r[k]==='string')||
       !Array.isArray(r.connectors)||!r.connectors.every(x=>typeof x==='string')||
       [r.level1,r.level2,r.dcFast].some(x=>x!==null&&(!Number.isSafeInteger(x)||x<0))) throw Error('Invalid AFDC location.');
    ids.add(r.id);
  }
  return raw;
}
export function selectAFDC(records,origin,radius,{connector='',access='public'}={}) {
  return records.filter(r=>(!connector||r.connectors.includes(connector))&&(!access||r.accessCode===access))
    .map(r=>({...r,distance:distance(origin,r)})).filter(r=>r.distance<=radius).sort((a,b)=>a.distance-b.distance||a.id-b.id);
}
export function afdcCSV(rows) {
  const q=x=>'"'+String(x??'').replace(/^[=+@\t\r-]/,"'$&").replaceAll('"','""')+'"';
  const header=['AFDC ID','Name','Town','Province','Latitude','Longitude','Straight-line km','Connectors','Recorded access','Recorded status','Confirmed','Updated'];
  return '\uFEFF'+[header,...rows.map(r=>[r.id,r.title,r.town,r.region,r.lat,r.lon,r.distance.toFixed(3),r.connectors.join('; '),r.access,r.status,r.confirmed,r.updated])].map(row=>row.map(q).join(',')).join('\r\n');
}
