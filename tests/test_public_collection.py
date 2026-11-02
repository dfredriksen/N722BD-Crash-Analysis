"""Acquisition boundaries and preservation guarantees, without network access."""
import csv
import hashlib
import io
from pathlib import Path
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_public_data as collect
from audit_public_data import JoinedParts


def test_radar_window_keeps_preceding_volume_and_rejects_other_dates():
    names = ["KAMX20261101_164800_V06", "KAMX20261101_165800_V06",
             "KAMX20261101_170000_V06", "KAMX20261101_182959_V06",
             "KAMX20261101_183000_V06", "KAMX20261031_172000_V06",
             "KAMX20261101_170000_V06_MDM"]
    rows = [{"key": "2026/11/01/KAMX/" + name, "size": 10} for name in names]
    assert [Path(r["key"]).name for r in collect.select_radar(rows, "KAMX")] == names[1:4]


def test_tar_member_crosses_split_boundary_without_rewriting_parts(tmp_path):
    payload = b"preserved original bytes" * 43
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        member = tarfile.TarInfo("traces/17/trace_full_a9ab17.json")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    raw = archive.getvalue()
    paths = [tmp_path / "day.tar.aa", tmp_path / "day.tar.ab"]
    paths[0].write_bytes(raw[:600])
    paths[1].write_bytes(raw[600:])
    before = [collect.digest(p) for p in paths]
    with JoinedParts(paths) as stream, tarfile.open(fileobj=stream, mode="r:") as tar:
        assert tar.extractfile(tar.next()).read() == payload
    assert [collect.digest(p) for p in paths] == before


@pytest.fixture
def recorded_download(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "ROOT", tmp_path)
    monkeypatch.setattr(collect, "BASE", Path("acquisition"))
    monkeypatch.setattr(collect, "MANIFEST", tmp_path / "manifest.csv")
    payload = b"original evidence"
    row = dict.fromkeys(collect.FIELDS, "")
    row.update(repository_target="acquisition/source.bin", source_url="https://example.test/source",
               sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload), http_status=200)
    with collect.MANIFEST.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=collect.FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return tmp_path, payload, row


def test_existing_evidence_tampering_fails_before_network(recorded_download, monkeypatch):
    root, _, row = recorded_download
    target = root / row["repository_target"]
    target.parent.mkdir()
    target.write_bytes(b"different")
    monkeypatch.setattr(collect.requests, "get", lambda *a, **kw: pytest.fail("Network must not be used"))
    with pytest.raises(ValueError, match="conflict"):
        collect.Collector().fetch("source.bin", row["source_url"], "test")
    assert target.read_bytes() == b"different"


def test_changed_remote_cannot_restore_a_recorded_original(recorded_download, monkeypatch):
    root, _, row = recorded_download
    class Response:
        headers = {"Content-Length": "7"}
        url = row["source_url"]
        status_code = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def iter_content(self, size): yield b"changed"
    monkeypatch.setattr(collect.requests, "get", lambda *a, **kw: Response())
    result = collect.Collector().fetch("source.bin", row["source_url"], "test")
    assert "Source changed" in result["transport_error"]
    assert not (root / row["repository_target"]).exists()
    assert list(csv.DictReader(collect.MANIFEST.open()))[0]["sha256"] == row["sha256"]
