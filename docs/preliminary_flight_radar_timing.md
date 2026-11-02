> Historical preliminary analysis. Superseded by the [November 2 independent validation and reconstruction](technical_investigation_report.md). Original numerical claims below are retained for provenance.

# N722BD preliminary flight and KAMX radar timing analysis

Date analyzed: 2026-11-01 (UTC). Source: uploaded Flightradar24 granular CSV and five KAMX Level II archives.

## Verified archive volume start times
The Level II 24-byte archive header records Julian day 20759 and milliseconds after UTC midnight:
- 17:35:07.528 — KAMX20261101_173507_V06
- 17:40:32.501 — KAMX20261101_174032_V06(2)
- 17:45:48.587 — KAMX20261101_174548_V06(1)
- 17:51:04.049 — KAMX20261101_175104_V06(1)
- 17:56:21.201 — KAMX20261101_175621_V06

These are archive volume start timestamps, **not** validated timestamps of individual radar elevation sweeps or weather at the aircraft position.

## Flight observations
- CSV has 78,107 rows; 16,107 include latitude/longitude. Fields are sparse and asynchronously populated.
- At 17:35 UTC, reported altitude was approximately 41,000 ft; around 17:42–17:47 UTC, approximately 35,000 ft.
- Between 17:48:20 and 17:48:30 UTC, reported altitude shifted from approximately 35,400 ft to approximately 34,275 ft, followed by a much faster reported descent.
- Last nonmissing altitude: 8,750 ft at 17:49:24.591710 UTC. This value repeats across the final altitude-bearing rows and may reflect a data limit or other reporting behavior; it must not be extrapolated.
- Last nonmissing position: 26.632278 N, -80.111424 W at 17:49:31.540320 UTC.
- Last nonmissing vertical rate: -32,640 ft/min at 17:49:32.165558 UTC, with ground track 289.9 degrees and ground speed 238 knots.
- Last CSV timestamp: 17:49:32.411285 UTC.

## Interpretation limits
- Reported extreme vertical rate is not independently verified; no causal interpretation is warranted.
- Altitude and position are from different records and times, not a synchronized state vector.
- No radar reflectivity, velocity, shear, storm-cell proximity, or aircraft/radar beam intersection has yet been decoded or validated. Radar sweep timestamps, beam geometry, and moment fields require a Level II parser before meteorological claims.
- The 17:51 and 17:56 volume starts are after the final CSV timestamp and cannot directly establish earlier conditions.

## Next technical steps
1. Parse Level II message 31 radial metadata and sweeps for all five volumes.
2. Extract reflectivity and Doppler velocity at appropriate elevation angles, with exact sweep timestamps.
3. Match aircraft positions at contemporaneous timestamps and evaluate beam height and distance.
4. Produce reproducible georeferenced overlay, documenting CRS and processing parameters.
5. Reconcile ADS-B altitude source/units and the repeated 8,750-ft readings.

This is an independent preliminary analysis, not an official accident investigation or finding.
