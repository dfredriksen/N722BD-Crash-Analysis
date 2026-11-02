# Preliminary KAMX Level II reflectivity decoding — N722BD

Analysis date: 2026-11-02 UTC. **Preliminary; not a causal finding.**

## Decoded data
A standalone Python parser read BZip2-compressed NEXRAD Level II Archive II message 31 radials, parsed REF moments and radar location, and generated low-elevation reflectivity plots with Flightradar24 reported positions.

| Radar volume | REF radials parsed | Lowest-elevation radials | First parsed radial (UTC) | Last parsed radial (UTC) |
|---|---:|---:|---|---|
| 17:35:07 | 6245 | 720 | 17:35:07.528 | 17:40:23.879 |
| 17:40:32 | 5674 | 720 | 17:40:32.501 | 17:45:39.130 |
| 17:45:48 | 5789 | 531 | 17:45:48.587 | 17:50:55.371 |

Radar position decoded from VOL metadata: 25.611084 N, -80.412666 W. The 17:45 volume includes radar measurements during the time window of the last flight-track observation (17:49:32 UTC).

## Limitations and next validation
- Plots represent the lowest-elevation REF sweep; they **do not** depict reflectivity at the aircraft's altitude (~35,000 ft earlier in the flight).
- The 17:45 file's lowest-elevation sweep has 531 REF radials in this parser output, compared with 720 in earlier volumes. Confirm scan coverage and parser completeness before using the image quantitatively.
- Radials have different acquisition times; a radar volume is not an instantaneous snapshot.
- Reflectivity alone cannot diagnose turbulence, wind shear, icing, aircraft structural failure, or crash causation.
- No aircraft-centered, altitude-matched reflectivity or radial velocity extraction has yet been validated.
- Before drawing conclusions, cross-check parsing against a standard radar library, verify individual sweep times and beam height, and decode VEL and SW products.

## Working files
Generated locally (not committed): `KAMX20261101_173507_V06_reflectivity_overlay.png`, `KAMX20261101_174032_V06_2_reflectivity_overlay.png`, `KAMX20261101_174548_V06_1_reflectivity_overlay.png`, `N722BD_radar_decode_summary.csv`, `decode_n722bd.py`.

No original radar binaries have been uploaded to this repository by this analysis.
