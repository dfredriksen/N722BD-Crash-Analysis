# Generated analysis products

Authoritative run: Python 3.11.15, Py-ART 2.3.0. See `execution.json`,
`pyart_api_validation.json`, `requirements.lock` and the technical report.
Files outside this directory may be historical supplied results.

| File | Meaning |
|---|---|
| `evidence_audit.csv`, `package_audit.json` | Six expected source-file checksums and retained ZIP hash |
| `package_members.json`, `supplied_member_integrity.csv` | All 24 package-member hashes and preserved-copy integrity |
| `radar_comparison.csv` | Every native Py-ART ray; custom coverage, per-field gate/geometry/mask/value comparisons |
| `volume_summary.csv`, `sweep_coverage.csv`, `validation_summary.json` | Decoder coverage and comparison totals |
| `pyart_highlevel_samples.csv` | Full API metadata and common-grid sample near 117.467 km for every ray |
| `pyart_api_comparison.csv`, `pyart_api_validation.json` | Internal high-level/native Py-ART agreement at that gate |
| `aircraft_radar_matches.csv` | Nearby rays across every sweep with independently bracketed position and altitude |
| `beam_uncertainty.csv` | Exploratory k, beamwidth and altitude-tolerance scenarios on near-height rays |
| `clock_sensitivity.csv` | Exploratory aircraft clock shifts of −2, −1, 0, +1 and +2 seconds |
| `fixed_final_position_samples.csv` | Screen around final position bearing, explicitly noncontemporaneous |
| `flight_observations.csv`, `flight_summary.json` | Parsed original asynchronous observations and endpoint summaries |
| `flight_state_timeline.csv` | Position-time states with independent field support/status and bounded interpolation |
| `flight_path.geojson` | WGS84 observed position segments; splits gaps >20 seconds; no inferred height coordinate |
| `radar_flight_overlay.geojson` | Segmented track and nominal REF gate footprints, with individual UTC/height/moment properties |
| `*.png` | Timeline, per-volume overlays, 17:44:26 beam profile and time-varying 3D sampling figure |

All timestamps are UTC. Per-field sampled values use REF in dBZ, VEL in m/s
and SW in m/s. Raw codes are preserved: zero is masked below-threshold/missing;
one is range-folded. `moment_absent` and `outside_range` are separate conditions.
Missing/masked numeric values are empty CSV cells, never zero-filled. Compare
boolean `*_present` and `*_mask_agrees` fields separately from numeric differences;
an empty comparison value does not establish agreement.

`range_m` is native radar slant gate-center range. `ground_range_m` is WGS84
surface distance. Nearest-gate selection records the gate index and spacing;
REF cell-corner min/max heights account for half a native gate and the nominal
half-power beamwidth. Native radial `ray_index` is zero-based within each volume;
`elevation_number` is the transmitted one-based elevation identifier.

`reported_altitude_ft`, `altitude`, ground speed and vertical rate retain the
units identified in the supplied analyses (ft, kt and ft/min). Source altitude
datum and pressure correction are unverified. Geometric heights are modeled
MSL using the encoded 33-m radar/feedhorn height. No vertical datum conversion
is claimed. GeoJSON uses longitude then latitude; modeled MSL height remains a
property rather than an incorrect ellipsoidal third coordinate.

The nominal beam screen assumes k=4/3 and 1° full half-power width. The ±2°
candidate screen retains neighbors outside that nominal footprint. Nominal
horizontal and vertical overlap are separate booleans and must both hold for
joint screening. Neither implies a valid moment measurement or aircraft encounter.
Scenario tolerances are not measured errors or confidence limits. No radar
quantity is converted into vertical wind, turbulence intensity or crash causation.

`flight_state_timeline.csv` records `reported`/`interpolated`/unavailable status
and before/after support seconds independently for each field. No interpolation
crosses a bracket more than ten seconds away on either side. Circular track is
unwrapped before interpolation. Altitude-difference rate is a derived quantity
separate from source-reported vertical rate.
