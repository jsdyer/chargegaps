import {decodeAFDC,selectAFDC,afdcCSV} from './afdc-model.mjs';
import {fetchBytes,point} from './model.mjs';
const $=id=>document.getElementById(id),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
let capture,near=[];
const labels={E:'Available in the directory',P:'Planned',T:'Temporarily unavailable'};
function show(){
  if(!capture)return;
  try {
    const origin=point($('lat').value,$('lon').value),radius=Number($('radius').value);
    if(!Number.isFinite(radius)||radius<1||radius>2000)return;
    near=selectAFDC(capture.records,origin,radius,{connector:$('afdc-connector').value,access:$('afdc-access').value});
    $('afdc-status').textContent=`${near.length.toLocaleString('en-CA')} AFDC records within ${radius} km; showing the nearest ${Math.min(20,near.length)}. These records are separate from the OCM results above.`;
    const body=$('afdc-results');body.replaceChildren();
    for(const r of near.slice(0,20)) {
      const card=el('article'),a=el('a',r.title);a.href='https://afdc.energy.gov/stations/#/station/'+r.id;a.target='_blank';a.rel='noopener noreferrer';
      card.append(a,el('p',`${r.distance.toFixed(1)} km · ${r.town}, ${r.region} · ${r.network||'Network not supplied'}`),
        el('p',`${r.connectors.join(', ')||'Connectors unknown'} · ${r.access||'Access unknown'} · ${labels[r.status]||r.status||'Status unknown'}`),
        el('p',`Ports: L1 ${r.level1??'unknown'}, L2 ${r.level2??'unknown'}, DC ${r.dcFast??'unknown'} · Confirmed ${r.confirmed||'not supplied'} · Updated ${r.updated||'not supplied'}`));
      if(r.hours)card.append(el('p',r.hours));if(r.pricing)card.append(el('p','Source pricing text: '+r.pricing));
      body.append(card);
    }
    $('afdc-export').disabled=!near.length;
  } catch { /* Keep the last valid comparison while coordinates are edited. */ }
}
for(const id of ['lat','lon','radius','afdc-connector','afdc-access'])$(id).addEventListener('change',show);
$('filters').addEventListener('submit',()=>queueMicrotask(show));$('presets').addEventListener('click',()=>queueMicrotask(show));
window.addEventListener('chargegaps:point',show);
$('afdc-update').addEventListener('click',show);
$('afdc-export').addEventListener('click',()=>{const a=el('a');a.href=URL.createObjectURL(new Blob([afdcCSV(near)],{type:'text/csv;charset=utf-8'}));a.download='chargegaps-afdc.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});
try {
  capture=decodeAFDC(JSON.parse(new TextDecoder().decode(await fetchBytes('./data/afdc.json',25*1024*1024))));
  $('afdc-date').textContent=`${capture.recordCount.toLocaleString('en-CA')} Canadian records · captured ${new Date(capture.checkedAt).toISOString().slice(0,16).replace('T',' ')} UTC. Individual confirmation dates vary. This is not live stall availability.`;
  for(const name of [...new Set(capture.records.flatMap(r=>r.connectors))].sort())$('afdc-connector').append(new Option(name,name));
  show();
}catch{ $('afdc-status').textContent='The AFDC capture is not available. The retained Open Charge Map collection remains usable.'; }
