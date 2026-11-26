import test from 'node:test';import assert from 'node:assert/strict';
import {decodeAFDC,selectAFDC,afdcCSV} from '../web/afdc-model.mjs';
const row={id:1,title:'=Example',town:'Langley',region:'BC',network:'',status:'E',access:'Public',accessCode:'public',confirmed:'2026-01-01',updated:'',pricing:'',lat:49.1,lon:-123,connectors:['J1772'],level1:null,level2:0,dcFast:1};
test('AFDC compares by geography and independent connector/access filters',()=>{
 const rows=[row,{...row,id:2,lat:60},{...row,id:3,accessCode:'private'}];
 assert.deepEqual(selectAFDC(rows,{lat:49.1,lon:-123},10).map(r=>r.id),[1]);
 assert.equal(selectAFDC(rows,{lat:49.1,lon:-123},10,{access:'',connector:'J1772'}).length,2);
});
test('AFDC schema rejects duplicate ids and preserves unknown counts',()=>{
 const capture={schema:'coolcode.chargegaps.afdc.v1',checkedAt:'2026-11-26T01:00:00Z',coverage:['CA'],recordCount:1,records:[row]};
 assert.equal(decodeAFDC(capture).records[0].level1,null);
 assert.throws(()=>decodeAFDC({...capture,recordCount:2,records:[row,row]}));
});
test('AFDC CSV is source-labelled and escapes formula cells',()=>{
 const csv=afdcCSV([{...row,distance:1}]);assert.match(csv,/AFDC ID/);assert.match(csv,/'=Example/);assert.doesNotMatch(csv,/OCM ID/);
});
