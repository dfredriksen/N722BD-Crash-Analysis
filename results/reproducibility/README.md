# Clean reproduction records

Tested analysis commit: `860c9e27cb15a48edbf52f24f73b83506a861a51`.

`run.json` records all 14 stages passing, generated outputs cleared first,
30 source-manifest checks unchanged, and 47/49 baseline artifacts byte-identical.
Five artifacts are static README/Git/baseline snapshots: 44 products were
regenerated, 42 identical, two with expected run/ZIP metadata differences.

`output_comparison.json` contains each baseline and regenerated SHA-256.
`source_audit_before.json` and `source_audit_after.json` contain the six principal
source checks and 24 package-member checks (24 unique source files).
`stages.json` records commands, durations and zero exit codes.
`tests.log` records 25 passing tests; the remaining logs cover the full raw
processing and separate review checks. `environment.log` lists all 69 packages.
`reader_provenance.json` compares the installed and vendored native reader.

Local checkout and managed-Python prefixes were sanitized as placeholders in
published logs. Generated scientific artifacts and evidence hashes were not
normalized or altered. Original full local logs remain outside the repository.

See [reproducibility report](../../docs/reproducibility_report.md) for the
procedure, distinctions from prior recorded outputs and limitations.
