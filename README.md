# N722BD Learjet crash analysis

## Status
Evidence collection and temporal/geospatial validation in progress. This repository is an independent technical analysis, not an official accident finding. Observations, hypotheses, and conclusions must remain distinct.

## Evidence received (2026-11-01)
- Flightradar24 granular CSV: 78,107 records, UTC timestamps from 14:17:03.168653 to 17:49:32.411285; ICAO24 `a9ab17`. Position is populated on 16,107 rows. Missing fields must not be interpolated without documentation.
- KAMX NEXRAD Level II radar volumes (UTC filename timestamps): 17:40:32, 17:45:48, 17:51:04, and 17:56:21. Original archive headers begin with `AR2V`.
- Georeferenced overlay: pending upload.

**Timing caution:** Two radar volumes have nominal timestamps after the last flight-tracking CSV record. This does not establish that any radar feature coincides with the aircraft; align actual radar sweep times and aircraft timestamps before making comparisons.

## Intended repository layout
- `data/flight_tracking/`: original CSV and source details
- `data/radar/KAMX/`: unmodified Level II radar volumes
- `overlays/`: georeferenced imagery and CRS metadata
- `docs/evidence_manifest.csv`: filenames, byte sizes, SHA-256 hashes and provenance
- `docs/`: timeline, analysis methods, limitations and interpretations

## Methodology
1. Preserve source files unchanged and calculate SHA-256 hashes.
2. Normalize time to UTC; explicitly document units, source clock resolution and missing values.
3. Parse NEXRAD Level II sweep metadata, radar location, elevation angles and beam geometry; distinguish reflectivity and velocity products.
4. Georeference overlay data with an explicit coordinate reference system and verify alignment against known locations.
5. Compare aircraft track, altitude and uncertainty with radar sampling geometry and times. Avoid inferring causation from visual proximity.
6. Record reproducible scripts, software versions, processing parameters and source citations.

## Evidence handling
Do not silently rename, resample or modify originals. Preserve raw filenames in the manifest. For large binaries consider Git LFS, checking GitHub limits and storage quotas first. Do not treat missing ADS-B observations as proof of loss of aircraft tracking or an accident event.

## Findings
No causal finding has been established in this repository.
