# Reproduction

Use Python 3.11 and `requirements.lock`. Run from the repository root after
activating the environment. Analysis scripts read the retained source ZIP when
present and otherwise use committed byte-identical original members, mapped by
`docs/supplied_package_manifest.csv`. A fresh clone is sufficient to rerun the
analysis. Rechecking the ZIP itself requires the original package. See
`data/README.md` for provenance.

```powershell
uv python install 3.11
uv venv --python 3.11 .venv
uv pip sync --python .venv/Scripts/python.exe requirements.lock
.venv/Scripts/Activate.ps1
python scripts/audit_evidence.py --extract
$radarFiles = Get-ChildItem data/radar/KAMX -File | Sort-Object Name | ForEach-Object FullName
python scripts/validate_n722bd_pyart.py @radarFiles --all-rays --output results/independent/pyart_highlevel_samples.csv
python scripts/check_highlevel_api.py
python scripts/run_investigation.py
python scripts/flight_state_timeline.py
python scripts/make_overlays.py
python scripts/summarize_validation.py
python -m unittest discover -s tests -v
```

The full API validator samples one common-grid gate near 117.467 km on every ray.
It sets `linear_interp=False` explicitly. `check_highlevel_api.py` compares these
samples and metadata against native Py-ART records. That is an internal API
consistency check, not a third independent implementation.

`run_investigation.py` independently compares the supplied custom decoder against
native Py-ART records across all five volumes, all shared rays and all returned
REF/VEL/SW gates. It extracts only the custom parser function definitions through
AST, avoiding the supplied scripts' `/mnt/data` assumptions and side effects.
Native gates and per-ray moment metadata are used for aircraft matching, avoiding
common-grid interpolation. The BSD-licensed reader under `vendor/` is unmodified.

The following scripts are historical supplied analyses: `decode_n722bd.py`,
`analyze_3d_n722bd.py`, `moving_match_n722bd.py`, `neighbor_beam_screen.py`, and
`N722BD_beam_sensitivity.py`. They contain environment-specific paths and known
decoder/geometry limitations. They are retained for provenance, not used as the
authoritative reconstruction. Exact received versions are under
`data/supplied_artifacts/scripts/`. The enhanced API validator adds `--all-rays`
because its original fixed-bearing/time window excludes much of the evidence.

The initial full-stack installation failed for lack of disk space. A Python 3.14
low-level-reader fallback identified the decoder coverage discrepancy. After
space became available, the environment was installed and the authoritative
analysis rerun under Python 3.11.15. Only the final execution metadata describe
the delivered results.
