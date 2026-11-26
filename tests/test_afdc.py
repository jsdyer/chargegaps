import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

spec=importlib.util.spec_from_file_location('afdc',Path(__file__).resolve().parents[1]/'scripts/refresh_afdc.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def payload():
    return {'total_results':100,'api_key':'FAKE_KEY','fuel_stations':[{'id':i+1,'country':'CA','fuel_type_code':'ELEC','latitude':49.1,'longitude':-123,'station_name':'Example','ev_connector_types':['J1772'],'ev_level2_evse_num':None,'api_key':'FAKE_KEY'} for i in range(100)]}

class AFDCTests(unittest.TestCase):
    def test_full_capture_whitelist_and_missing_port_count(self):
        result=a.normalize(payload(),'2026-11-26T01:00:00Z','FAKE_KEY')
        self.assertEqual(result['recordCount'],100)
        self.assertIsNone(result['records'][0]['level2'])
        self.assertNotIn('FAKE_KEY',json.dumps(result))

    def test_partial_duplicate_and_wrong_country_fail(self):
        for kind in ('partial','duplicate','country'):
            p=payload()
            if kind=='partial':p['total_results']=200
            if kind=='duplicate':p['fuel_stations'][1]['id']=1
            if kind=='country':p['fuel_stations'][0]['country']='US'
            with self.subTest(kind=kind),self.assertRaises(ValueError):a.normalize(p,'2026-11-26T01:00:00Z')

    def test_secret_header_and_error_redaction(self):
        with patch.object(a,'build_opener') as op:
            op.return_value.open.side_effect=HTTPError('https://example/?api_key=FAKE_KEY',403,'FAKE_KEY',{},None)
            with self.assertRaises(ValueError) as error:a.fetch('FAKE_KEY')
            request=op.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('X-api-key'),'FAKE_KEY')
            self.assertNotIn('FAKE_KEY',request.full_url)
            self.assertNotIn('FAKE_KEY',str(error.exception))
