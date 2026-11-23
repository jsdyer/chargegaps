import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import ROOT,validate_config,normalize,compile_data,changes

class RefreshTests(unittest.TestCase):
    def reference(self):
        return {'Countries':{44:{'ID':44,'ISOCode':'CA'}},'DataProviders':{1:{'ID':1,'Title':'OCM','IsOpenDataLicensed':True,'License':'CC BY 4.0'}}}
    def poi(self,id=1):
        return {'ID':id,'DataProviderID':1,'AddressInfo':{'CountryID':44,'Title':'Sample','Latitude':49,'Longitude':-123},'Connections':[{'ConnectionTypeID':1,'PowerKW':7,'Quantity':2}]}
    def test_valid_metadata_and_unknown_fields(self):
        r,reason=normalize(self.poi(),'CA',self.reference());self.assertIsNone(reason);self.assertEqual(r[0],1);self.assertEqual(r[14],[[1,7,2,None]]);self.assertIsNone(r[10])
    def test_licence_exclusion_is_not_a_blanket_ocm_licence(self):
        ref=self.reference();ref['DataProviders'][1]['IsOpenDataLicensed']=False
        self.assertEqual(normalize(self.poi(),'CA',ref),(None,'licence'))
        ref['DataProviders'][1]['IsOpenDataLicensed']=True;ref['DataProviders'][1]['License']=''
        self.assertEqual(normalize(self.poi(),'CA',ref),(None,'licence'))
    def test_invalid_geo_is_reported_and_country_mismatch_rejected(self):
        p=self.poi();p['AddressInfo']['Latitude']=100;self.assertEqual(normalize(p,'CA',self.reference()),(None,'coordinates'))
        with self.assertRaises(ValueError):normalize(self.poi(),'US',self.reference())
    def test_zero_power_kept_but_invalid_quantities_unknown(self):
        p=self.poi();p['Connections'][0].update(PowerKW=0,Quantity=-1)
        self.assertEqual(normalize(p,'CA',self.reference())[0][14],[[1,0,None,None]])
    def test_config_accepts_extra_country_and_rejects_paths(self):
        c=json.loads((ROOT/'web/config.json').read_text());c['countries'].append('US');self.assertEqual(len(validate_config(c)['countries']),2)
        c['countries']=['../'];self.assertRaises(ValueError,validate_config,c)
    def test_difference_uses_ids_not_array_order(self):
        old={'coverage':['CA'],'records':[[1,'A'],[2,'B']]};new={'coverage':['CA'],'records':[[3,'C'],[1,'A2']]}
        self.assertEqual(changes(old,new),{'kind':'comparable','added':1,'absent':1,'changed':1})
        new['coverage']=['CA','US'];self.assertEqual(changes(old,new)['kind'],'coverage-changed')
    def test_compile_includes_added_country_and_rejects_missing_folder(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'data/CA').mkdir(parents=True);(p/'data/US').mkdir()
            refs={'Countries':[{'ID':44,'ISOCode':'CA'},{'ID':2,'ISOCode':'US'}],'DataProviders':list(self.reference()['DataProviders'].values()),'Operators':[],'UsageTypes':[],'StatusTypes':[],'ConnectionTypes':[]}
            (p/'data/referencedata.json').write_text(json.dumps(refs));(p/'data/CA/1.json').write_text(json.dumps(self.poi()));us=self.poi(2);us['AddressInfo']['CountryID']=2;(p/'data/US/2.json').write_text(json.dumps(us))
            c=json.loads((ROOT/'web/config.json').read_text());c.update(countries=['CA','US'],minimumRecords=1)
            result=compile_data(p,c,'2026-11-23T00:00:00Z','a'*40,'2026-04-22T00:00:00Z');self.assertEqual(len(result['records']),2);self.assertEqual(result['countryCounts'],{'CA':1,'US':1})
            c['countries'].append('MX');self.assertRaises(ValueError,compile_data,p,c,'2026-11-23T00:00:00Z','a'*40,'2026-04-22T00:00:00Z')

if __name__=='__main__':unittest.main()
