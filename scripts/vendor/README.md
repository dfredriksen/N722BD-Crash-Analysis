`pyart_nexrad_level2.py` is an **unmodified** copy of
`pyart/io/nexrad_level2.py` from the ARM Py-ART 2.3.0 wheel downloaded by uv.
Its BSD license and copyright notice are embedded in the file.

SHA-256: `9fef39126f56ef28ca29cc1bea4dac4d291c58772628bdf3ea48045c16708e73`.

Upstream: https://github.com/ARM-DOE/pyart/blob/v2.3.0/pyart/io/nexrad_level2.py

This reader deliberately depends only on NumPy and Python's standard library.
It enables native-resolution cross-validation without requiring Py-ART's full
dependency stack. Using it is distinct from running `pyart.io.read_nexrad_archive`.
