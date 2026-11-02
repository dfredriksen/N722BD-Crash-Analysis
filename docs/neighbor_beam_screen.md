# Expanded neighboring-beam screen — N722BD

2026-11-01 KAMX Level II radar / Flightradar24 comparison. **Preliminary, not a causal conclusion.**

## Procedure
Reused the custom Archive II Message 31 parser and time-bracketed aircraft position/altitude interpolation from the earlier moving-aircraft screen. Examined 29,556 radials across five KAMX files, accepting azimuth differences within ±2° and keeping beams within 4,000 ft of the nominal vertical beam envelope. Assumed 4/3 effective Earth radius, 1° full beam width and approximate radar altitude 4 m MSL. These are modeling assumptions, not independently verified instrument specifications for every ray.

## Results
Twelve neighboring rays met the expanded candidate filter. **Zero** intersected the estimated vertical beam envelope, whether the azimuth tolerance was ±0.6°, ±1°, or ±2°. Closest ray at 17:44:26.759 UTC: azimuth difference −1.415°, beam center ~38,184 ft, nominal half-width ~2,853 ft, aircraft altitude ~35,000 ft, gap to beam edge ~331 ft. At 17:44:26.796 UTC, azimuth difference −0.428°, gap ~332 ft, reflectivity 14 dBZ, radial velocity −6 m/s, spectrum width 2 m/s.

The 331-ft separation is **smaller than plausible combined uncertainty** in the altitude reference, propagation, beam model, and ray geometry; do not infer that radar coverage was conclusively absent. Nearby reflectivity and velocity are not direct in-situ aircraft measurements.

## Validation status
The expanded analysis tests angular sensitivity, but **does not constitute independent decoder validation**: it reuses the same custom parser. Py-ART, wradlib and xradar were not installed in the analysis environment. Before using any decoded moment quantitatively, compare radial metadata and gate values with an independent NEXRAD reader and verify radar/aircraft altitude datums, radar site elevation, sweep times, beam geometry, and quality flags.

Local reproducibility outputs: `neighbor_beam_screen.py`, `N722BD_neighbor_beam_candidates.csv`. Neither original radar binaries nor these local files have been uploaded to GitHub.
