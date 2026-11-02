# N722BD: aircraft-azimuth radar samples (preliminary)

Data: uploaded FR24 CSV and five KAMX Level II volumes, 2026-11-01 UTC. This is a **fixed-last-position** radar sampling exercise, not a time-varying 3D aircraft encounter reconstruction.

- Last position: 17:49:31.540320 UTC, 26.632278 N, -80.111424 W.
- Last separately reported altitude: 17:49:24.591710 UTC, 8,750 ft (altitude datum not independently confirmed).
- KAMX radar location used: 25.611084 N, -80.412666 W; distance to last position 117.467 km, azimuth 14.769°.
- Parsed five radar files for REF, VEL and SW along radials within 0.65° of that fixed azimuth; 101 candidate radials. At the nearest range gate, 74 had valid reflectivity, 17 had valid radial velocity and 8 had valid spectrum width.

## Selected samples at the last position's azimuth and range

| Radar radial time UTC | Elevation | Approx. beam center above radar | REF | VEL | SW |
|---|---:|---:|---:|---:|---:|
| 17:47:25.030 | 1.230° | 3,334 m | 17.5 dBZ | +10.5 m/s | missing |
| 17:48:39.950 | 0.483° | 1,803 m | 17.5 dBZ | missing | missing |
| 17:49:29.286 | 5.098° | 11,242 m | 14.0 dBZ | +5.0 m/s | 1.0 m/s |
| 17:49:42.213 | 6.372° | 13,838 m | missing | missing | missing |

Beam center estimates use a standard 4/3 Earth-radius approximation; they are heights above radar, not a verified aircraft altitude match. Radar beam width, terrain, refraction variability, and gate geometry introduce uncertainty. Radial velocity is the line-of-sight component, not vertical wind speed. Spectrum width is not a direct turbulence measurement. Reflectivity is not a direct indicator of severe turbulence.

**No weather encounter or causal finding is established.** In particular, the temporally closest radar sample at 17:49:29 is ~11.2 km above the radar, whereas the last reported aircraft altitude is ~2.67 km; they are not vertically co-located. The 17:48:39 sample is lower but nearly 52 seconds before the last reported position. The fixed final position must not be substituted for aircraft positions at earlier times.

Next: interpolate only within independently validated track segments; match each radial to contemporaneous aircraft location and altitude with uncertainty bounds, compare radar gate height and beam width, cross-validate decoder with a standard NEXRAD library, and investigate radar velocity aliasing and quality flags before interpreting wind fields.
