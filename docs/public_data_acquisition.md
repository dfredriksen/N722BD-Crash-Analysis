# Public evidence acquisition — 2 November 2026

This collection adds publicly downloadable sources for the 1 November 2026
investigation. It is an acquisition and content audit, **not a revised accident
reconstruction**. The existing five-volume/FR24 results have not been recomputed
using these supplements. No crash cause, intent, encounter or airspace violation
is established by obtaining them.

## Acquired material

The acquisition contains **379 HTTP response bodies, 3,744,758,386 bytes
(3.74 GB decimal)**, plus receipts and an unchanged compressed aircraft trace
extracted from the ADSB.lol archive. Response counts include documentation,
inventories and explicit no-data/error responses; they are not all observations.

Raw root: `data/public/2026-11-01/acquisition_20261102/`.
Every HTTP body has an adjacent `.receipt.json` recording URL, retrieval UTC,
HTTP status, headers (session-cookie values omitted), byte size and SHA-256. The consolidated
[manifest](public_evidence_manifest.csv) preserves the same provenance.

| Dataset | Actual acquisition and coverage | Qualification |
|---|---|---|
| KAMX NEXRAD Level II | 18 volumes; actual radial times 16:58:12.144–18:32:30.859 UTC; 174,960 rays | Starts in 17:00–18:30 plus preceding volume; complete files retained |
| KMLB NEXRAD Level II | 15 volumes; actual radial times 16:54:45.374–18:36:21.605 UTC; 151,200 rays | A second radar geometry, not automatically an independent measurement of the aircraft |
| ADSB.lol daily archive | Two original split-TAR parts, 3,118,588,416 bytes; both match the SHA-256 digests published in the GitHub release | Processed network traces, not raw Mode S payloads; global archive retained locally |
| N722BD trace from that archive | ICAO `a9ab17`, registration `N722BD`, type `LJ60`; 1,028 points, 14:17:43.240–17:49:32.750 UTC; 370 points in 17:00–18:30 | Preserved gzip member `trace_full_a9ab17.json`, SHA-256 `4ebab6b9897e4feefa69dcacd0065c1d353cac675f3d4da3541416cf0747dd95` |
| GOES-19 GLM | 270 twenty-second lightning files, 17:00:00–18:30:00 UTC | Full-disk detections; not a direct aircraft strike/encounter record |
| GOES-19 ABI | 18 CONUS channel-13 infrared images; acquisition times 17:01:17.6–18:28:56.1 UTC | Discrete scans, not continuous or altitude-resolved weather observations |
| AWC surface observations | 118 METAR/SPECI records, 14:00–20:00 UTC, nine returned airports | KPBI was requested but absent; five NOAA rolling METAR-cycle snapshots also preserved |
| AWC PIREPs | 151 reports, 14:00–20:00 UTC, all within requested 24–29°N, 83–78°W box | Pilot reports have their own timing/location/aircraft uncertainties |
| AWC forecasts/advisories | Three TAF snapshots of eight records each, selected at 17, 18 and 20 UTC; 41 G-AIRMET records valid at 18 UTC; eight CWA records | Snapshots overlap and are not unique totals; G-AIRMET/CWA responses are national; later-issued products are not pre-event knowledge |
| NWS bulletins via IEM | Nine eastern convective-SIGMET bulletins issued 12:55–20:55; two Miami and two Melbourne AFDs; Miami/Melbourne warning bundles with 33/12 WMO headers | Eleven queries saved; six returned explicit error/no-product text and are not usable bulletins |
| IGRA soundings | Original 2026 archives for Miami, Key West and Tampa; five November 1 soundings available in total | Miami and Tampa 00/12 UTC, Key West 00 UTC; no November 2 00 UTC profiles in these retrievals |
| FAA airspace records | Full web text and XML for FDC 6/0100, 6/3803 and 6/3963; current TFR-list snapshot | A current snapshot and published validity text do not supply the complete historical amendment/cancellation chain or flight authorizations |

The radar archive copies of **all five supplied KAMX files match exactly by
SHA-256**. This independently reproduces acquisition of those bytes from the
public archive and strengthens their provenance. It does not calibrate the radar,
authenticate FR24's source messages, or prove atmospheric truth. See
[file comparisons](../results/public_acquisition/supplied_radar_public_comparison.csv).

## Aircraft trace and airspace records requiring follow-up

The ADSB.lol trace exposes separate geometric altitude/rate fields, source flags,
and sparse NIC, NACp, SIL and related quality fields. The
[readable trace](../results/public_acquisition/adsblol_N722BD_trace.csv) preserves
each recorded point without interpolation or forward-filling sparse metadata.
The [extraction record](../results/public_acquisition/adsblol_member_provenance.json)
links its bytes to both original archive parts and their published digests.

For example, its last point reports a barometric altitude of 8,750 ft and a
geometric altitude of 325 ft at 17:49:32.750 UTC. These are **provider-reported
fields**, not a verified simultaneous physical state or impact altitude. The
barometric/geometric discrepancy, time offsets, quality fields and shared upstream
receivers must be examined before combining this trace with FR24. The collection
does not resolve the −32,640 ft/min encoding issue or certify either altitude.

The FAA text for 6/3803 states a VIP restriction ending **1 November at 17:30
UTC**, before the 17:44:26 and 17:49:32 samples. Separately, 6/0100 describes a
one-nautical-mile security restriction centered at 26°40′37″N, 80°02′16″W, surface
to 2,000 ft AGL, with published dates 20 October 2026–20 October 2027. Its text
contains ATC/IFR exceptions. The center matches the previously used proposed-circle
reference. These records are distinct; neither supports treating the earlier
proposed circle as a verified presidential TFR or asserting an aircraft violation.
The amendment/cancellation chain and operational permissions remain unresolved.
6/3963 concerns an earlier interval ending 31 October at 03:00 UTC.

## Availability gaps and failed routes

| Requested evidence | Actual result | Status |
|---|---|---|
| TPBI terminal radar | NCEI Level II inventory reports its period ending 31 July 2026; the requested November 1 date is outside it. Public Level III `PBI_TZ0`, `PBI_TV0`, `PBI_TZL` listings returned zero objects; the GCP date listing also returned none | Not acquired. Archive coverage/access failure does not establish radar inactivity |
| KPBI surface observations | AWC omitted KPBI; the IEM PBI request returned a header-only CSV; no KPBI reports found in the five NOAA cycle files | Not acquired for the airport itself; surrounding-airport observations remain available |
| Late soundings | Key West 12 UTC and all three November 2 00 UTC profiles absent from the saved IGRA archives | Revisit after archive updates; preserve a new retrieval separately |
| Some IEM bulletin identifiers | AIRMET, CWAMIA, CWAJAX, FTMAMX, FTMMLB and FTMPBI returned `ERROR: Could not Find` despite HTTP 200 | Not observations and not proof of no advisory or maintenance event. AWC CWA/G-AIRMET data were separately obtained |
| Direct ADSB.lol trace URL | HTTP 403 during discovery | No restriction bypassed; downloaded the documented public GitHub release instead |
| FAA registry web lookup | HTTP 403 during discovery | No authenticated registration record acquired; trace itself labels ICAO/registration/type |
| Raw transponder messages and receiver timing | Not present in the downloaded processed trace | Provider/receiver records still needed |
| ATC audio/surveillance, recorder/maintenance records, official accident docket | No verified case-specific evidence acquired in this collection | Still outstanding; no requests, emails or paid orders submitted |
| Full historical NOTAM change history | Three published records and current list obtained | Complete effective-state and authorization audit outstanding |

Successful anonymous download does not guarantee permanent availability. The NOAA
METAR cycles, IGRA year-to-date archives, AWC API results and FAA current list can
change. Their captured bodies are preserved in Git; failed restoration of a
different hash must be reported, never silently substituted.

## Storage and reproduction

The supplied evidence and its two existing manifests are unchanged. Thirty
original-manifest checks, covering 24 unique preserved targets, still pass.
Supplementary data are kept out of `data/radar/KAMX/` so existing scripts do not
silently include new volumes.

Small source responses, sounding ZIPs, the extracted compressed aircraft trace,
HTTP receipts, manifests and derived audit tables are committed on the feature
branch. The 33 bulk radar files, 288 satellite files and two global ADS-B archive
parts remain downloaded locally and are excluded from Git. In particular, the
1.12/2.00 GB parts exceed GitHub's ordinary per-file limit. No LFS quota or paid
storage was provisioned. The manifest and restore command fetch and check the
exact bulk bytes on another machine; they do not claim the bulk files are present
in a normal Git clone.

With the existing Python 3.11 environment:

```powershell
.venv\Scripts\python.exe scripts\collect_public_data.py --restore
.venv\Scripts\python.exe scripts\audit_public_data.py
.venv\Scripts\python.exe -m pytest tests -q
```

`--restore` refuses a hash mismatch, verifies any existing file, and does not
overwrite original evidence. A fresh collection can be initiated with group names
`radar weather satellite soundings bulletins availability airspace adsb`; to collect
an updated snapshot use a new acquisition directory/manifest, not these paths.
The audit opens all 33 volumes with ARM Py-ART, reads all 288 satellite files,
checks IGRA ZIP integrity/record structure, parses weather/FAA responses and
extracts the aircraft member from the split archive without modifying it.
The initial audit encountered a Windows text-decoding error on UTF-8 release
metadata; explicit UTF-8 handling was added and the audit rerun. Acquisition
boundary/restoration tests supplement the existing science tests. Passing these
checks validates their tested behavior, not the truth/completeness of observations.
The final audit completed successfully: all 379 response-body SHA-256 checks,
33 radar reads, 288 satellite reads and 30 original-manifest checks passed. The
combined test suite passed 29 tests and 21 subtests; two Cartopy deprecation
warnings remain. See [execution record](../results/public_acquisition/validation_execution.json),
[audit log](../results/public_acquisition/audit_run.txt) and
[test output](../results/public_acquisition/test_run.txt).
The restore path also passed an actual missing-file download in an isolated
directory, reproducing the first GLM file's recorded SHA-256 without changing the
preserved acquisition.

## Sources and usage

- [NOAA NODD](https://www.ncei.noaa.gov/products/ncei-data-noaa-open-dissemination-program), with anonymous NEXRAD objects served from `unidata-nexrad-level2`.
- [NOAA GOES public archive](https://registry.opendata.aws/noaa-goes/), GOES-19 GLM and ABI objects.
- [Aviation Weather Center API](https://aviationweather.gov/data/api/) and [IEM NWS bulletin API](https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help=).
- [NCEI IGRA](https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive) and [TDWR archive description](https://www.ncei.noaa.gov/products/radar/terminal-doppler-weather-radar).
- [ADSB.lol November 1 release](https://github.com/adsblol/globe_history_2026/releases/tag/v2026.11.01-planes-readsb-prod-0): ADSB.lol and contributors, **ODbL-1.0**, retained with its license and readsb schema. The source can incorporate partners' feeds; separate hosting does not prove independent reception.
- [FAA 6/0100 XML](https://tfr.faa.gov/download/detail_6_0100.xml), [6/3803 XML](https://tfr.faa.gov/download/detail_6_3803.xml), [6/3963 XML](https://tfr.faa.gov/download/detail_6_3963.xml); raw web-text API responses and extraction receipts accompany them.

PR #1 remains unmerged. This collection is ready for a further scientific review;
its additions must not be described as already incorporated in the prior clean
reproduction or as certifying the investigation's conclusions.
