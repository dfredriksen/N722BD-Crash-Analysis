# Unresolved issues after review fixes

The four implementation findings F1–F4 are addressed in
[review_response.md](review_response.md). These remaining evidence/model limits
cannot be resolved by changing code or obtaining agreement among implementations.

| ID | Priority for stronger conclusions | Missing evidence / limitation | Consequence / next evidence needed |
|---|---|---|---|
| U1 | High | Flight-file authentication, original aircraft-message identity and quality indicators | Five supplied radar files now match separately downloaded public archives; a second processed aircraft trace is preserved. Authenticated provider/transponder records and upstream provenance remain needed |
| U2 | High | Aircraft altitude datum/pressure correction and clock accuracy | Near-beam classifications and rate interpretation remain conditional; obtain altitude encoding/calibration and independent time anchors |
| U3 | High | Actual antenna pattern, refractivity profile, position errors and their joint distributions | 55 cases are diagnostic, not a probability estimate or exhaustive uncertainty bound; obtain contemporaneous propagation/quality evidence |
| U4 | High | Synchronized ATC, operational records, flight recorder and verified accident timeline | No weather avoidance, intent, causal mechanism or impact-state conclusion |
| U5 | High for airspace claims | Time-applicable property perimeter, complete NOTAM amendment/cancellation history and operational permissions | Three FAA NOTAM records now supply published geometry/altitude/time limits; the historical effective state and exceptions still need review. Proposed-circle distances cannot determine compliance |
| U6 | High | Final altitude plateau versus extreme vertical rate; asynchronous observations; −32,640 ft/min numerically matches the TC19 encoding endpoint | No extrapolated final state or proven clipping; obtain original payloads, vertical-rate source bit and provider processing history |
| U7 | Medium | Review walker follows Py-ART framing conventions, skips ancillary messages, and only covers these archives | Not a general NEXRAD conformance certificate; use another maintained decoder and format/calibration expertise for broader validation |
| U8 | Medium | Finite ray/elevation/time samples and masked returns; no volumetric weather truth | Nominal non-overlap cannot rule out hazardous weather; integrate the new KMLB/KAMX volumes and weather/aircraft supplements with explicit sampling and uncertainty checks |

Acquisition update, 2 November 2026: [public supplements](public_data_acquisition.md)
partly address U1/U3/U5/U8. All five original radar volumes match independently
downloaded public copies. A separate N722BD trace supplies barometric/geometric
fields and sparse quality indicators; additional radar, soundings and weather
records are now available. Full FAA text/XML gives separate security and VIP
restriction intervals. These additions do not authenticate aircraft payloads,
resolve clock/altitude discrepancies, establish the complete NOTAM change history,
or supply ATC permissions. Their integration and scientific review remain open;
the prior reconstruction has not been recalculated with them.

Recommendation: suitable for human review as a reproducible evidence and methods
repository with these limitations retained. It is not sufficient for a crash
causation, intentional maneuvering, hazardous-weather exclusion, or airspace
violation finding. PR #1 must remain unmerged pending the user's review.
