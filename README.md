# Charge Gaps

[Open Charge Gaps](https://coolcode.ca/chargegaps/) explores charging locations from
Open Charge Map country downloads. It helps inspect recorded coverage around any
latitude/longitude, with connector, power, access, operator and region filters.
It requires **no API key**. The first edition covers Canada.

## Try it

<!-- coolcode:guide -->
Start with **Langley**, select a connector and minimum power, then compare the nearest matching record and the number inside your radius. Enter any valid coordinates to investigate another point; the shortcuts are optional. Distances are straight lines, not driving routes, and an empty result means no matching record in this capture—not proof that no charger exists. **Recorded access** and **Recorded status** include private, restricted and planned locations unless filtered. The source export date is prominent because these downloads can be much older than their retrieval date. Save capture JSON to keep a portable record; imports and coordinate calculations stay in this tab.
<!-- /coolcode:guide -->

1. Use a place shortcut or enter latitude, longitude and a 1–2,000 km radius.
2. Select connectors and minimum power. Both must match the **same connection**.
3. Click a location in the map or list for connection detail, dates and attribution.
4. Export the matching nearby rows as CSV or save the complete capture JSON.
5. Import a previous `.json`/`.json.gz` capture to inspect it. An imported capture is
   compared with the previously viewed capture only when country coverage matches.

The initial real download contains **18,798** geolocated, explicitly open-licensed
Canadian records, from **18,804** source rows. Six rows lacked an explicit open-data
licence and were excluded. These numbers describe the first capture, not fixed
application limits. The initial export commit is `8e3bedca48ca94807d96b2f5e7ee02cffe63ae54`,
dated **22 April 2026**; it was retrieved **23 November 2026**. The application
calculates and displays the source edition's age. It does not present this as a
current or complete charging inventory.

## Sources and rights

- [Official OCM country exports](https://github.com/openchargemap/ocm-export) contain
  `data/CA/*.json` and shared `data/referencedata.json`. The old `ocm-data` repository
  is deprecated; this application uses its documented successor.
- [Open Charge Map terms](https://www.openchargemap.org/about/terms): contributor
  records are CC BY 4.0; third-party providers retain their own terms. The collector
  includes only providers with `IsOpenDataLicensed: true` and a nonempty `License`.
  Each capture, location detail and CSV retains the provider attribution/licence.
- Initial included providers: Open Charge Map Contributors (CC BY 4.0), NREL/AFDC
  (source states use for any purpose), AddÉnergie Technologies Inc. (CC BY 3.0),
  and Greems Technologies (CC0). Filtering and normalization are performed here;
  neither OCM nor those providers endorse this tool.
- [Leaflet 1.9.4](https://leafletjs.com/) is vendored under its BSD-2-Clause licence
  in `web/vendor/leaflet/`; provenance and upstream licence are retained.
- Street maps use [OpenStreetMap](https://www.openstreetmap.org/copyright) tiles
  under the [tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
  Tiles are requested only for the interactive view, with ordinary browser caching
  and a Referer. No tile downloads/prefetching are offered. CI blocks tile requests.

Power ratings may be estimates and vary by vehicle. Connection quantities are not
necessarily independent stalls. Operational status is **the recorded status in an
export**, not availability now. Straight-line distance does not account for roads,
ferries, water, topography or permitted access. Confirm details with the operator.
No routing, booking, charge-session or real-time status API is called.

## Expand or customize

Edit [`web/config.json`](web/config.json):

```json
{
  "countries": ["CA", "US"],
  "defaultPoint": {"name": "Victoria", "lat": 48.4284, "lon": -123.3656},
  "defaultRadiusKm": 25,
  "presets": [{"name": "Victoria", "lat": 48.4284, "lon": -123.3656}]
}
```

Merge those fields into the complete config rather than replacing the file.
`countries` accepts 1–20 distinct two-letter ISO codes present in the export.
`presets` may contain any named valid coordinate pair; visitors can always enter
coordinates themselves. `pageSize`, `maxMapPoints` and `retainedCaptures` control
presentation and history. The map caps the number of displayed markers, nearest
first; the full list/export still includes every matching record in the radius.
`minimumRecords`, `maximumRecords`, and `maximumDropFraction` protect against
incomplete upstream captures and can be adjusted for deliberate coverage changes.
`tiles.url` can point at another permitted HTTPS tile service; update attribution
in `web/app.mjs` along with provider terms when doing so. A default public tile
service is not an unlimited hosting service.

**Refresh and publish:** push config changes, then open Actions → **Charge Gaps ·
Capture, check and publish** → **Run workflow**, check **Check and import the
official country export** (`refresh`) and run on `main`. A normal code push only
builds the retained data. Scheduled source checks run Mondays at **08:37 UTC**.
They update the successful check time, but download/compile a new capture only
when the source commit or country coverage changes. Unchanged source data stays
clearly dated. Schedules can be delayed or disabled by GitHub; dates are authoritative.

The collector uses an ignored sparse checkout of the upstream export. Each country
must exist and have records; duplicate IDs, country mismatches and suspicious drops
fail the collection. Validation/build/browser checks must pass before a successful
capture is committed and deployed. Failed runs leave the previous public deployment.
Eight complete compressed captures are retained by default. Earlier captures stay
usable when the watchlist changes; differing country coverage begins a new baseline.
New or absent directory rows are not claimed as newly opened/closed chargers.

Local equivalent:

```sh
python3 scripts/refresh.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The ordinary build is offline. `web/data/index.json` exposes `checkedAt`, source
edition, retrieval time, country coverage, counts and SHA-256 digests. Data uses
`coolcode.chargegaps.v1`; compressed capture files are linked by that index.

## Privacy and deployment

Search terms, reference coordinates and imported files stay in memory in this tab.
Nothing is saved automatically. The map tile provider receives ordinary requests
for the viewed area; switch off **Street map** to stop new tile requests. Opening
OCM/provider links contacts those sites. The shared CoolCode counter records an
aggregate app open, not the tool's coordinate/search/file input. No secret or API
key is embedded or required.

Source lives in `web/`; `scripts/build.py` produces `dist/` for GitHub Pages at
`/chargegaps/`. Keep the project's Pages source set to GitHub Actions; no CNAME.
Unit tests cover geodesic distances, connection-specific power matching, unknown
values, record/licence validation, capture comparisons, coordinate expansion,
CSV formula handling and source configuration expansion beyond the starter country.
CI also tests real-data loading, a non-preset point, search, import/export and mobile
layout at a project subpath. Browser-only tests use Playwright; no app runtime
package manager is needed.

Related tools: [Road Pulse](https://coolcode.ca/roadpulse/),
[Dock Diary](https://coolcode.ca/dockdiary/) and
[Trailglass](https://coolcode.ca/trailglass/).

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
