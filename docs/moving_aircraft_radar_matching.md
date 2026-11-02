> Historical preliminary analysis. Superseded by the [November 2 independent validation and reconstruction](technical_investigation_report.md). Original numerical claims below are retained for provenance.

# Moving-aircraft KAMX radar match: preliminary pass

Analysis of uploaded N722BD flight tracking and five KAMX NEXRAD Level II volumes (2026-11-01 UTC). This is a **screening exercise**, not a verified 3D weather encounter analysis.

## Method
- Parsed 29,556 message-31 radials across the five radar files.
- Interpolated aircraft latitude, longitude, and altitude at each radial's timestamp, requiring bracketing observations within 10 seconds on each side; in the 48 retained matches the maximum actual bracketing interval on either side was <0.56 seconds.
- Matched radar azimuth within 0.6 degrees of the contemporaneous aircraft bearing from KAMX.
- Estimated beam center height using 4/3 effective-Earth-radius refraction and an approximate 1-degree full beam width; compared to reported aircraft altitude, tentatively assumed MSL.
- Sampled reflectivity, Doppler radial velocity, and spectrum width at the nearest range gate, where present.

## Results
- 15,590 radials had usable interpolated position, 15,514 also had altitude, 48 matched azimuth, **0** were within the estimated vertical beam envelope.
- Matches by radar volume: 17:35 volume 20 (7 with REF, 2 with VEL); 17:40 volume 19 (13 REF, 3 VEL); 17:45 volume 9 (9 REF, 0 VEL). Later volumes contain no aircraft-position-supported matches because the flight record ends earlier.
- Closest vertical separation: 17:44:26.796 UTC, aircraft reported 35,000 ft, beam center ~38,185 ft MSL, nominal half-width ~2,853 ft; REF 14 dBZ, VEL -6 m/s. The aircraft lies slightly outside the estimated beam envelope, not a direct weather observation.
- At 17:47:09 UTC, aircraft ~35,000 ft, sampled beam center ~11,673 ft, REF 32–32.5 dBZ; this is **not** an altitude match.
- At 17:48:39 UTC, aircraft ~31,300 ft, sampled beam center ~6,403 ft, REF 12–16.5 dBZ; also **not** an altitude match.

## Limitations
No intersection is **not evidence of absence** of convective weather or turbulence. The screen uses a narrow azimuth tolerance and actual sampled radials, not a volumetric interpolation across neighboring rays and elevation angles. Aircraft altitude datum and radar height have not been independently checked. Beam width and propagation are approximate. The custom decoder needs independent cross-validation. Radial velocity measures line-of-sight motion, not downdraft or vertical wind. No causal conclusion is supported.

## Reproducibility
Local generated files: `moving_match_n722bd.py` and `N722BD_moving_aircraft_radar_matches.csv`. Raw binaries and CSV are not yet committed to the repository. Further work should validate radar moment decoding, altitude references, beam geometry, neighboring radials and gate uncertainty, and compare with independent weather data.
