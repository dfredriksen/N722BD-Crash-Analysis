> Historical preliminary analysis. Superseded by the [November 2 independent validation and reconstruction](technical_investigation_report.md). Original numerical claims below are retained for provenance.

# Radar beam sensitivity and independent-decoder status

## Sensitivity results
Based on the 12 previously screened KAMX neighboring rays, aircraft positions interpolated at each ray's time, and the same 4/3-Earth beam geometry. This is **not** a new independent decoding of the Level II data.

| Assumed full beam width | Additional vertical tolerance | Rays intersecting expanded envelope |
|---|---:|---:|
| 0.8° | 0 ft | 0/12 |
| 0.8° | 500 ft | 0/12 |
| 0.8° | 1000 ft | 4/12 |
| 1.0° | 0 ft | 0/12 |
| 1.0° | 500 ft | 4/12 |
| 1.0° | 1000 ft | 4/12 |
| 1.2° | 0 ft | 4/12 |
| 1.5° | 0 ft | 4/12 |
| 1.5° | 500 ft | 8/12 |

The nominal closest separation is ~331 ft at 17:44:26 UTC. The result is sensitive to plausible uncertainty assumptions. These tolerance values are exploratory and **not measured uncertainties or probabilistic confidence bounds**. Azimuthal beam footprint, range gate volume, refractivity and aircraft altitude datum are not comprehensively modeled.

## Independent decoder validation: pending
ARM Py-ART provides a standard Level II archive reader, `pyart.io.read_nexrad_archive`: https://arm-doe.github.io/pyart/API/generated/pyart.io.read_nexrad_archive.html . Py-ART, xradar, wradlib and MetPy are not installed in the current runtime, so a true independent decoder cross-check **has not been performed**. Previously decoded reflectivity, Doppler velocity, spectrum width, radar ray count, and beam geometries remain provisional.

Next steps: install a trusted independent NEXRAD reader in a controlled environment, compare per-ray timestamp/azimuth/elevation, gate locations, masked gates and moment values against the custom parser, then recalculate the aircraft-centered 3D radar intersections. Document decoder version and discrepancies.

Local files: `N722BD_beam_sensitivity.py`, `N722BD_beam_sensitivity.csv`; not uploaded to GitHub. No weather causation is established.
