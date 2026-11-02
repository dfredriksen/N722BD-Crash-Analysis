# N722BD Learjet crash analysis

## Status
Independent decoder validation and aircraft-centered 3D sampling reconstruction executed on November 2, 2026. All six source files are checksum-verified and committed. This repository is an independent technical analysis, not an official accident finding. Observations, hypotheses, and conclusions remain distinct.

Read the [technical investigation report](docs/technical_investigation_report.md) for authoritative findings, methods and limitations, and [reproduction instructions](scripts/README.md) to rerun the analysis from a fresh clone with Python 3.11. Earlier preliminary reports and supplied result files are retained as historical evidence.

The report separates preserved source observations and decoded measurements, model-dependent geographic calculations, analytical hypotheses, and unresolved limitations. Passing tests establishes the tested calculations' behavior under stated assumptions; it does not establish source accuracy or completeness. Weather avoidance, intentional maneuvering, storm exposure, Mar-a-Lago perimeter relationships, ATC synchronization and historical TFR activity remain unverified.

## Evidence received (2026-11-01)
- Flightradar24 granular CSV: 78,107 records, UTC timestamps from 14:17:03.168653 to 17:49:32.411285; ICAO24 `a9ab17`. Position is populated on 16,107 rows. Missing fields must not be interpolated without documentation.
- Five KAMX NEXRAD Level II radar volumes (UTC filename timestamps): 17:35:07, 17:40:32, 17:45:48, 17:51:04, and 17:56:21. Original archive headers begin with `AR2V`. Actual ray times extend through 18:01:20.523 UTC.
- Supplied figures, logs, custom decoder and preliminary datasets: preserved under `data/supplied_artifacts/`; every original package member is mapped in `docs/supplied_package_manifest.csv`.
- New WGS84 radar-gate/flight GeoJSON overlays, 3D figure and flight timeline: `results/independent/`.

**Timing caution:** Two radar volumes have nominal timestamps after the last flight-tracking CSV record. This does not establish that any radar feature coincides with the aircraft; align actual radar sweep times and aircraft timestamps before making comparisons.

## Repository layout
- `data/public/2026-11-01/acquisition_20261102/`: supplementary public-source acquisition; see the [download inventory, coverage and limitations](docs/public_data_acquisition.md). Bulk files are local downloads restored by manifest, not ordinary Git objects.
- `results/public_acquisition/`: checksums, actual coverage and a separately sourced N722BD trace; not yet integrated into the original reconstruction.
- `data/flight_tracking/`: original CSV and source details
- `data/radar/KAMX/`: unmodified Level II radar volumes
- `data/supplied_artifacts/`: unmodified supplied scripts, figures, logs and preliminary results
- `results/independent/`: new comparison CSVs, 3D matches, state timeline, uncertainty scenarios, GeoJSON overlays and figures
- `overlays/`: historical supplied imagery; not authoritative georeferencing
- `docs/evidence_manifest.csv`: filenames, byte sizes, SHA-256 hashes and provenance
- `docs/supplied_package_manifest.csv`: all 24 original package members and preserved-copy locations
- `requirements.lock`: exact Python 3.11 dependency versions
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
Py-ART 2.3.0 decoded 48,600 rays across five volumes, versus 29,556 returned by the supplied custom parser: **19,044 rays (39.19%) were omitted**. Gate values and geometry agree where both parsers returned the moment; the custom parser also omitted spectrum width on 3,929 shared rays. The full Py-ART API check passed for all 48,600 rays and the sampled REF/VEL/SW gate values and masks.

The WGS84 reconstruction retains 290 neighboring-ray candidates with contemporaneous position/altitude support. One meets the nominal circular-cone/range-cell screen, but all three moments at that gate are masked. At 17:44:26.796 UTC, the modeled aircraft direction is 0.694° from the ray axis, outside the assumed 0.5° half-width. The corrected same-ground vertical-projection gap is 172 m; the cone edge at the aircraft's bearing is 427 m above its assumed-MSL altitude. These are model calculations, not clearance from hazardous weather. Both aircraft-range and beam-axis-range gates are retained with explicit labels.

All four findings from the review of `838f10d` are addressed: required finite metadata and site-coordinate checks, geometry-failure counting independent of raw-array comparability, consistent 3D sampling geometry, and clock scenarios reselected from all 48,600 rays. The suite has 25 tests. A separate review reader checks all native REF/VEL/SW codes, and 55 geometry/timing/missing-data scenarios test conclusion sensitivity. See the [review response and conclusions](docs/review_response.md).

The FR24 file contains 118 decreasing altitude reports over about 58 seconds, from 35,000 to 8,750 ft. That supports a source-reported descent sequence, not a verified physical descent rate or cause. Alternative beamwidth and combined clock/altitude/refraction scenarios admit radar-return overlap, so nominal non-overlap cannot rule out weather exposure. A sourced proposed-circle reference calculation is included, without claiming a property-perimeter or active-TFR determination.

No causal finding has been established. The aircraft altitude datum, source accuracy, actual atmospheric refractivity and official accident timeline remain unresolved. Radial velocity is not vertical wind; spectrum width is not direct turbulence intensity.

Primary outputs: [decoder comparisons](results/independent/radar_comparison.csv), [3D matching dataset](results/independent/aircraft_radar_matches.csv), [flight-state timeline](results/independent/flight_state_timeline.csv), [georeferenced overlay](results/independent/radar_flight_overlay.geojson), [beam uncertainty scenarios](results/independent/beam_uncertainty.csv), and [API validation results](results/independent/pyart_api_validation.json).
