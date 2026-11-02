# Original evidence and provenance

All six files in `docs/evidence_manifest.csv` were extracted without renaming or
editing from `N722BD_remaining_GitHub_upload.zip`. SHA-256 and byte sizes match all
six pre-existing manifest entries. `docs/supplied_package_manifest.csv` records
all 24 ZIP members and the locations of their byte-identical copies.

The package was located in the CYINT mailbox email **N722BD GitHub Evidence**,
dated November 1, 2026 at 22:25:34 -1000. The Drive file identifier is
`1JiyriOnNgYsiLL6QBo7ar-AfYoydFkKJ`. No mailbox credentials or access tokens are
part of this repository.

Package size: 78,116,546 bytes. SHA-256:
`4796e260f7ac30527d2760530a275c1e7562a13ce8bb8e069101a3a19fde08a0`.
Drive-reported MD5: `51c2f4f96a59fe0f3e92a985e3264e9d`.

- `flight_tracking/`: original FR24 CSV.
- `radar/KAMX/`: five original Archive II volumes.
- `supplied_artifacts/`: original scripts, figures, logs and preliminary result
  CSVs, including package versions that differ from the original Git repository.
- `evidence_packages/`: local retained ZIP, ignored by Git to avoid duplicating
  all committed originals. Download it from the Drive file above to reproduce the
  package audit. The analysis reads it without modifying it.

Manifest hashes establish agreement with the received package, not independent
authentication by FR24 or NOAA. Acquisition/export history and official-source
cross-checks remain unresolved. The ZIP does not include aircraft altitude datum
documentation, pressure correction, an independently verified accident time,
radar calibration evidence, or atmospheric refractivity measurements.

Each original radar file is under 15 MB and the flight CSV is 4.2 MB. They are
below GitHub's 50 MiB warning and 100 MiB blocking thresholds. Git LFS is not
needed for these individual committed files. The larger duplicate package is
retained locally rather than committed as an ordinary Git blob. See
[GitHub's file-size documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
