#!/usr/bin/env python3
"""Capture the Canadian AFDC catalogue without publishing a credential or raw response."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://developer.nlr.gov/api/alt-fuel-stations/v1.json'
LIMIT = 60_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise ValueError('AFDC redirect refused; credentials were not forwarded')


def text(value):
    return value[:1000] if isinstance(value, str) else ''


def count(value):
    return value if type(value) is int and value >= 0 else None


def normalize(payload, captured, key=''):
    records = payload.get('fuel_stations') if isinstance(payload, dict) else None
    total = payload.get('total_results') if isinstance(payload, dict) else None
    if not isinstance(records, list) or type(total) is not int or total != len(records) or not 100 <= total <= 100000:
        raise ValueError('AFDC returned an empty, truncated or unsupported catalogue')
    rows, ids, excluded = [], set(), 0
    for item in records:
        if not isinstance(item, dict) or item.get('country') != 'CA' or item.get('fuel_type_code') != 'ELEC':
            raise ValueError('AFDC country or fuel coverage did not match the request')
        identity = item.get('id')
        if type(identity) is not int or identity <= 0 or identity in ids:
            raise ValueError('AFDC supplied invalid or duplicate station identities')
        ids.add(identity)
        lat, lon = item.get('latitude'), item.get('longitude')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in (lat, lon)) or abs(lat) > 90 or abs(lon) > 180:
            excluded += 1
            continue
        connectors = item.get('ev_connector_types') or []
        if not isinstance(connectors, list) or any(not isinstance(x, str) for x in connectors):
            raise ValueError('AFDC connector metadata was malformed')
        rows.append({
            'id':identity, 'title':text(item.get('station_name')) or 'Unnamed station',
            'lat':lat, 'lon':lon, 'region':text(item.get('state')), 'town':text(item.get('city')),
            'address':text(item.get('street_address')), 'network':text(item.get('ev_network')),
            'status':text(item.get('status_code')), 'access':text(item.get('groups_with_access_code')),
            'accessCode':text(item.get('access_code')), 'hours':text(item.get('access_days_time')),
            'connectors':sorted(set(connectors)), 'level1':count(item.get('ev_level1_evse_num')),
            'level2':count(item.get('ev_level2_evse_num')), 'dcFast':count(item.get('ev_dc_fast_num')),
            'confirmed':text(item.get('date_last_confirmed')), 'updated':text(item.get('updated_at')),
            'pricing':text(item.get('ev_pricing')), 'restricted':item.get('restricted_access') is True,
            'unverified':item.get('unverified') is True,
        })
    if len(rows) < total * .95:
        raise ValueError('AFDC returned too many locations without usable coordinates')
    rows.sort(key=lambda x:x['id'])
    result = {'schema':'coolcode.chargegaps.afdc.v1', 'checkedAt':captured, 'coverage':['CA'],
              'source':'U.S. Department of Energy Alternative Fuels Data Center / NRCan',
              'sourceUrl':'https://afdc.energy.gov/stations/',
              'sourceRecords':total, 'excludedCoordinates':excluded,
              'recordCount':len(rows), 'records':rows}
    if key and key in json.dumps(result, ensure_ascii=False):
        raise ValueError('Credential material detected; capture not written')
    result['recordsSha256'] = hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    return result


def fetch(key):
    url = ENDPOINT + '?' + urlencode({'country':'CA','fuel_type':'ELEC','status':'all','access':'all','limit':'all'})
    request = Request(url, headers={'X-Api-Key':key,'Accept':'application/json',
                      'User-Agent':'CoolCode ChargeGaps/1.0 (+https://coolcode.ca/chargegaps/)'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=90) as response:
            raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('AFDC response exceeded the supported size')
        return json.loads(raw)
    except HTTPError as error:
        raise ValueError(f'AFDC returned HTTP {error.code}; previous capture preserved') from None
    except (URLError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError('AFDC did not return readable catalogue data; previous capture preserved') from None


def main():
    key = os.environ.get('DATA_GOV_API_KEY','').strip()
    if not key:
        raise ValueError('Configure the Actions secret DATA_GOV_API_KEY for the AFDC collection')
    path = ROOT / 'web/data/afdc.json'
    result = normalize(fetch(key), datetime.now(timezone.utc).isoformat(), key)
    if path.exists():
        previous = json.loads(path.read_text())
        if len(result['records']) < previous['recordCount'] * .75:
            raise ValueError('AFDC record count dropped by more than 25%; review before replacing the capture')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    temporary.replace(path)
    print(f"Captured {result['recordCount']} Canadian AFDC charging locations")


if __name__ == '__main__':
    try: main()
    except ValueError as error: raise SystemExit(str(error)) from None
