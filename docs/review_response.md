# Response to the adversarial review of 838f10d

All four identified findings have implementation fixes and regression coverage.
Original evidence remains unchanged. The recommendation is to review these
changes for an evidence/methodology release; this is not approval of a causal
accident finding or authorization to merge PR #1.

| Finding | Priority | Correction | Verification |
|---|---|---|---|
| F1: missing/nonfinite metadata accepted; site coordinates ignored | Medium | Required metadata must be finite; native/API latitude, longitude, height, angles and radial index are compared; full ray coverage required; all-masked value maxima are null; JSON serialization is strict | `tests/test_review_fixes.py` rejects NaN/±infinity, shifted coordinates, missing comparisons and incomplete coverage; full 48,600-ray API check passes |
| F2: geometry failures disappear when raw comparison unavailable | Medium | `field_summary` counts geometry independently and reports unavailable comparisons, with null rather than zero for unperformed value comparisons | Unequal-length fixture reports one geometry failure and one unavailable raw comparison; actual shared-gate results remain unchanged |
| F3: inconsistent edge point and rectangular joint beam test | Medium | Fixed-ground vertical projections; explicit circular 3D cone; aircraft-point slant range and native gate containment; separately retained beam-axis samples; cone altitude intervals and revised overlays | Axis round trips, diagonal false-overlap fixture, target scenarios, and separate all-ray/geometry implementation |
| F4: nominal selection restricts shifted clock scenarios | Low | Every ray evaluated before nominal filtering for each shift; full coverage ledger plus selected-neighbor detail | Synthetic state unavailable nominally but recovered after shift; independent comparison of all 243,000 coverage/overlap flags |

The further pass also replaces a 12-km endpoint shortcut in the proposed-circle
segment search with a triangle-inequality lower bound. A regression ensures that
distant endpoints cannot hide a crossing segment. The 3.363040-NM minimum is
unchanged. Clean reproduction backs up and removes generated products before
execution to exclude stale-output dependence.

Implementation: `scripts/check_highlevel_api.py`, `scripts/summarize_validation.py`,
`scripts/radar_geometry.py`, `scripts/run_investigation.py`, and
`scripts/make_overlays.py`. Reproduction, boundary tests and independent checks
are described in [scripts/README.md](../scripts/README.md).

## What changed scientifically

The decoder conclusion is unchanged: 48,600 native rays, 29,556 custom rays,
19,044 omitted rays (39.185185%), and 3,929 missing custom SW moments on shared
rays. The separate review walker checks 121,557,600 native REF/VEL/SW codes and
their descriptors against installed Py-ART without disagreement on these files.

At 17:44:26.796, the aircraft-point range selects 99,875 m: 13.5 dBZ, −6.0 m/s,
1.5 m/s. The previously reported 100,125-m gate remains available under `axis_*`:
12.5 dBZ, −6.0 m/s, 0.5 m/s. Neither is an identified aircraft return.

The old 184.332-m same-ground gap and “1,000 ft alone admits overlap” statement
are corrected. The vertical-projection gap is 172.489 m; the circular-cone lower
edge at the aircraft bearing is 427.278 m above the assumed altitude. Angular
separation is 0.694240° versus the nominal 0.5° half-width. A ±1,000-ft interval
alone still misses the 1° cone. A 1.5° cone, or specified combined uncertainties,
can admit overlap. These are model assumptions, not measured safety margins.

## Conclusions after another pass

1. The decoder omissions are reproduced and must be accounted for before using
   the original custom products to characterize radar coverage.
2. Under nominal assumptions, the only modeled overlap has masked moments.
   All tested clock-only shifts through ±10 s retain no valid-return overlap.
   Wider-beam and a combined clock/altitude/refraction scenario do produce
   valid-return overlap. Therefore “weather encounter not demonstrated” is
   supported; “weather encounter ruled out” is not.
3. A source-reported descent sequence is supported by 118 decreasing altitude
   observations over 58.174435 s. Physical descent rate, endpoint validity and
   cause are unverified. Repeated 8,750-ft reports coexist with −32,640-ft/min
   reports and cannot be treated as an exact synchronized final state.
4. The closest reported position is 3.363040 NM from the FAA proposal's reference
   center, outside that proposed 1-NM circle. This establishes a conditional
   geographic relationship only, not a property-perimeter finding, intent,
   an active TFR or an airspace violation.

The [technical report](technical_investigation_report.md) now states these
limits explicitly. The [unresolved-issues register](unresolved_issues.md)
identifies evidence needed for stronger conclusions. Passing tests and agreement
of implementations do not validate evidence authenticity or completeness.
