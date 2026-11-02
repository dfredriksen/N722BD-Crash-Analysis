# Supplemental public evidence

The dated acquisition directories preserve downloaded bytes, original object
filenames and HTTP receipts. They are separate from the supplied original evidence.
See [acquisition report](../../docs/public_data_acquisition.md) and
[SHA-256 manifest](../../docs/public_evidence_manifest.csv).

Large radar, satellite and split-TAR downloads are present locally but excluded
from Git. Restore missing files with `python scripts/collect_public_data.py --restore`
from the repository root, then run `python scripts/audit_public_data.py`.
Source changes cause checksum failure rather than silent replacement.

ADSB.lol and contributors provide the daily trace database under **ODbL-1.0**.
The unchanged extracted trace and its derived
`results/public_acquisition/adsblol_N722BD_trace.csv` retain that attribution and
license. The source license is preserved at
`2026-11-01/acquisition_20261102/metadata/adsblol/LICENSE-ODbL.txt`.
The aircraft member has a `.json` name but gzip-compressed bytes, as stored in the
original archive; its filename and compression have not been changed.

NOAA/NWS/FAA responses retain their source metadata. IEM redistributes NWS
bulletins. Different download hosts may serve the same upstream observations;
counting them as independent measurements requires a separate provenance audit.
