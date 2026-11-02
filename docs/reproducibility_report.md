# Reproduction of the review fixes

**Result: passed.** The full investigation and scientific review were executed
from preserved originals in a separate checkout at
`860c9e27cb15a48edbf52f24f73b83506a861a51`. Later delivery changes add this report,
logs and file-size metadata; they do not change the tested analysis or tests.

## Environment and procedure

A separate remote clone was created, then the local review-fix commits were
fetched into it and checked out detached. A new Python 3.11.15 virtual environment
was installed with `uv --no-cache pip sync --link-mode copy` and the committed
`requirements.lock`: 69 packages, including ARM Py-ART 2.3.0. Dependency checks
passed. System site packages were disabled, inherited `PYTHONPATH` was removed,
user site packages were disabled, and Matplotlib used a separate cache. This was
the same Windows host, not a different operating system or independent laboratory.

The final command was:

```powershell
python scripts/reproduce.py --clear-generated --log-dir ../N722BD-fix-review-clean-empty
```

The runner verified and backed up generated products, then removed them before
executing the pipeline. Original evidence was only read. The retained ZIP was
absent from the clean checkout: all processing used committed original members.
All 14 stages completed successfully: environment capture, source audit, full
Py-ART API decode, API/native comparison, investigation, flight-state timeline,
overlays, summary, review byte walker, custom coverage audit, scientific
challenges, proposed-circle geometry, flight evidence check, and tests.

## Provenance and output comparisons

- Both source manifests passed before and after processing: 30 manifest checks
  covering **24 unique preserved package members**, including all six principal
  source files. Hashes and sizes were unchanged. Separate staged-blob checks
  also verified all 24 original members before delivery.
- The primary checkout's retained ZIP audit matched the previously recorded
  SHA-256 `4796e260f7ac30527d2760530a275c1e7562a13ce8bb8e069101a3a19fde08a0`.
  A clean-clone check cannot reverify an absent ZIP; it verifies its preserved
  members. Receipt integrity does not authenticate acquisition or sensor truth.
- Of **49 baseline artifacts**, five were retained static documentation/audit
  snapshots and **44 were regenerated**. **42 regenerated products matched byte
  for byte**, including every scientific CSV, JSON, GeoJSON and PNG.
- The only regenerated differences were `execution.json` (run timestamp) and
  `package_audit.json` (ZIP absent versus present). Their source-file hashes,
  scientific parameters and environment versions agree. All 47 other artifacts
  matched, including the five static snapshots; those snapshots are not counted
  as regenerated science.
- Ten unaffected scientific products also match reviewed head `838f10d` byte for
  byte, including native decoder comparison, volume/sweep coverage, high-level
  samples, flight observations/state timeline and fixed-position samples. The
  revised geometry, selected gates, uncertainty products and API metadata
  columns intentionally differ and are explained in the review response.
- Installed and vendored native-reader source hashes match:
  `9fef39126f56ef28ca29cc1bea4dac4d291c58772628bdf3ea48045c16708e73`.
  This identifies shared implementation provenance; it is not independent
  decoder agreement.

## Reproduced scientific checks

**25 tests passed**: 21 boundary/plot/adversarial tests and four recorded-output
regressions. The full raw-archive pipeline is additional to these tests.

The separate review walker checked **121,557,600** native REF/VEL/SW codes and
descriptors against installed Py-ART. It reproduced **48,600 / 29,556** native /
custom rays, **19,044** omitted custom rays and **3,929** missing custom SW
moments on shared rays. Its limited framing conventions are documented in the
technical report and review dataset README.

Separate geodesic and geometry calculations agree on the revised nominal 290
candidates, one masked overlap, aircraft-point range and angular separation.
All **243,000** production clock-case evaluations agree with independently
implemented bracketing/geometry flags. **55** all-ray diagnostic scenarios were
executed, including combined assumptions that change nominal overlap results.
The proposed-circle minimum and provider-reported altitude sequence reproduce.

These are newly executed results, not merely inspection of previous outputs.
The assistant authored both the implementation and review code; this is not an
independent human/organizational certification. Model agreement and passing
tests do not establish physical correctness, evidence completeness, weather
exposure, accident causation, intent or airspace compliance.

## Records and recommendation

Per-stage logs, environment versions, before/after source hashes, reader hash,
output hashes and stage exit codes are in
[`results/reproducibility/`](../results/reproducibility/README.md). Local checkout
and Python-install prefixes are replaced by placeholders in published logs;
scientific outputs and original evidence retain their exact bytes.

The corrected evidence/methodology repository is ready for renewed human review.
The causal and operational limitations in
[`unresolved_issues.md`](unresolved_issues.md) remain. PR #1 has not been merged.
