"""Read either the retained original ZIP or committed byte-identical members."""
import csv
from pathlib import Path
from types import SimpleNamespace
import zipfile


class EvidenceSource:
    def __init__(self, root, package):
        self.root=Path(root)
        self.package=Path(package) if package is not None else None
        self.archive=zipfile.ZipFile(package) if self.package is not None and self.package.exists() else None
        if self.archive is None:
            with (self.root/'docs/supplied_package_manifest.csv').open() as f:
                self.mapping={r['original_package_member']:r['repository_target'] for r in csv.DictReader(f)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.archive is not None:
            self.archive.close()

    def namelist(self):
        return self.archive.namelist() if self.archive is not None else list(self.mapping)

    def open(self,name):
        return self.archive.open(name) if self.archive is not None else (self.root/self.mapping[name]).open('rb')

    def read(self,name):
        with self.open(name) as f:
            return f.read()

    def getinfo(self,name):
        if self.archive is not None:
            return self.archive.getinfo(name)
        return SimpleNamespace(filename=name,file_size=(self.root/self.mapping[name]).stat().st_size)

    def infolist(self):
        return [self.getinfo(name) for name in self.namelist()]
