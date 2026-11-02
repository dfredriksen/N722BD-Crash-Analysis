"""Offline integrity/content audit of the supplemental public acquisition.

Does not revise the original scientific analysis or equate dataset presence with
an aircraft encounter. Original source bytes and receipts remain untouched.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
import csv
from datetime import datetime, timezone
import gc
import gzip
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from netCDF4 import Dataset, num2date

from collect_public_data import BASE, ROOT, MANIFEST, digest

OUT = ROOT / "results/public_acquisition"


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(name, rows):
    if not rows:
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        writer.writerows(rows)


def iso(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat()


def audit_originals():
    checked = []
    for manifest in ("evidence_manifest.csv", "supplied_package_manifest.csv"):
        with (ROOT / "docs" / manifest).open(newline="") as f:
            for row in csv.DictReader(f):
                p = ROOT / row["repository_target"]
                valid = digest(p) == row["sha256"] and p.stat().st_size == int(row["size_bytes"])
                checked.append(dict(manifest=manifest, path=row["repository_target"], verified=valid))
    if not all(r["verified"] for r in checked):
        raise ValueError("Supplied original evidence has changed")
    write_json("original_evidence_integrity.json", checked)
    return len(checked)


def radar_audit(rows):
    os.environ["PYART_QUIET"] = "1"
    import pyart
    results = []
    supplied = list(csv.DictReader((ROOT / "docs/evidence_manifest.csv").open()))
    comparisons = []
    for row in rows:
        if row["kind"] != "nexrad_level2":
            continue
        p = ROOT / row["repository_target"]
        radar = pyart.io.read_nexrad_archive(str(p))
        times = radar.time["data"]
        start, end = num2date([float(np.min(times)), float(np.max(times))], radar.time["units"])
        if start.year != 2026 or start.month != 11 or start.day != 1:
            raise ValueError(f"Wrong radar date: {p.name}")
        results.append(dict(filename=p.name, site=p.parent.name, first_radial_utc=start.isoformat()+"Z",
                            last_radial_utc=end.isoformat()+"Z", rays=radar.nrays, sweeps=radar.nsweeps,
                            latitude=float(radar.latitude["data"][0]), longitude=float(radar.longitude["data"][0]),
                            radar_altitude_m=float(radar.altitude["data"][0]),
                            decoded_fields=";".join(sorted(radar.fields)), pyart_version=pyart.__version__))
        for original in supplied:
            if original["filename"].replace("(1)", "").replace("(2)", "") == p.name:
                comparisons.append(dict(supplied_file=original["repository_target"],
                    public_file=row["repository_target"], supplied_sha256=original["sha256"],
                    public_sha256=row["sha256"], exact_byte_match=original["sha256"] == row["sha256"]))
        print(f"Decoded {p.name}: {radar.nrays} rays", flush=True)
        del radar
        gc.collect()
    write_csv("radar_volume_coverage.csv", results)
    write_csv("supplied_radar_public_comparison.csv", comparisons)
    return results, comparisons


def satellite_audit(rows):
    results = []
    for row in rows:
        if row["kind"] not in ("goes_glm", "goes_abi_c13"):
            continue
        with Dataset(ROOT / row["repository_target"]) as ds:
            result = dict(filename=Path(row["repository_target"]).name, kind=row["kind"],
                          start_utc=ds.time_coverage_start, end_utc=ds.time_coverage_end,
                          platform=ds.platform_ID)
            if not result["start_utc"].startswith("2026-11-01T") or result["platform"] != "G19":
                raise ValueError("Satellite date/platform mismatch")
            if row["kind"] == "goes_glm":
                lat, lon = ds["flash_lat"][:], ds["flash_lon"][:]
                result.update(all_flashes=len(lat),
                    regional_flashes=int(np.ma.sum((lat >= 24) & (lat <= 29) & (lon >= -83) & (lon <= -78))))
            else:
                result.update(band=int(ds["band_id"][:].item()), image_shape=str(ds["CMI"].shape))
                # Exercise decompression of the image payload too.
                result["unmasked_pixels"] = int(np.ma.count(ds["CMI"][:]))
                if result["band"] != 13:
                    raise ValueError("Unexpected ABI band")
            results.append(result)
    write_csv("satellite_coverage.csv", results)
    return results


def weather_audit():
    base = ROOT / BASE
    results = []
    for p in sorted((base / "weather/awc").glob("*.json")):
        if ".receipt." in p.name:
            continue
        records = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"AWC did not return a record list: {p}")
        time_key = ("obsTime" if p.name.startswith(("metar", "pirep")) else
                    "validTime" if p.name.startswith("gairmet") else "validTimeFrom")
        times = [iso(r[time_key]) if isinstance(r.get(time_key), (float, int)) else str(r.get(time_key, ""))
                 for r in records if r.get(time_key) is not None]
        result = dict(file=p.name, records=len(records), time_field=time_key,
                      earliest=min(times, default=None), latest=max(times, default=None),
                      station_ids=sorted({r["icaoId"] for r in records if "icaoId" in r}))
        if p.name.startswith("pirep"):
            result["inside_requested_bbox"] = sum(24 <= r["lat"] <= 29 and -83 <= r["lon"] <= -78
                                                   for r in records if r.get("lat") is not None and r.get("lon") is not None)
        results.append(result)
    write_json("aviation_weather_coverage.json", results)
    bullets = []
    for p in sorted((base / "weather/nws_bulletins").glob("*.txt")):
        text = p.read_text(encoding="utf-8")
        headers = re.findall(r"(?m)^([A-Z]{4}\d{2}) ([A-Z]{4}) (\d{6})", text)
        bullets.append(dict(file=p.name, bulletin_headers=len(headers),
                            day_hour_minute=sorted({h[2] for h in headers}),
                            no_usable_bulletins=not headers,
                            error_response=text.strip() if text.startswith("ERROR:") else ""))
    write_json("bulletin_coverage.json", bullets)
    return results, bullets


def sounding_audit():
    results = []
    for p in sorted((ROOT / BASE / "soundings").glob("*.zip")):
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None:
                raise ValueError(f"ZIP CRC failure: {p}")
            members = [n for n in z.namelist() if n.endswith(".txt")]
            if len(members) != 1:
                raise ValueError("Unexpected IGRA ZIP structure")
            lines = z.read(members[0]).splitlines(keepends=True)
        headers = [i for i, line in enumerate(lines) if line.startswith(b"#")]
        selected = []
        for i in headers:
            h = lines[i].decode().rstrip()
            year, month, day, hour = int(h[13:17]), int(h[18:20]), int(h[21:23]), int(h[24:26])
            count = int(h[32:36])
            if i + count >= len(lines) or any(x.startswith(b"#") for x in lines[i+1:i+1+count]):
                raise ValueError("IGRA level count mismatch")
            if (year, month, day) in ((2026, 11, 1), (2026, 11, 2)):
                selected.extend(lines[i:i+count+1])
                results.append(dict(station=h[1:12], nominal_utc=f"{year:04}-{month:02}-{day:02}T{hour:02}:00:00Z",
                                    release_hhmm_utc=h[27:31], levels=count, source_zip=p.name))
        (OUT / (p.name.replace(".zip", "") + ".event_subset.txt")).write_bytes(b"".join(selected))
    write_csv("sounding_coverage.csv", results)
    return results


class JoinedParts(io.RawIOBase):
    """Seek across original split TAR parts without rewriting a combined archive."""
    def __init__(self, paths):
        self.files = [p.open("rb") for p in paths]
        self.offsets = [0]
        for p in paths:
            self.offsets.append(self.offsets[-1] + p.stat().st_size)
        self.position = 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position + offset if whence == 1 else self.offsets[-1] + offset
        if position < 0:
            raise ValueError("Negative seek")
        self.position = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.offsets[-1] - self.position)
        size = remaining if size < 0 else min(size, remaining)
        blocks = []
        while size:
            index = bisect_right(self.offsets, self.position) - 1
            count = min(size, self.offsets[index+1] - self.position)
            stream = self.files[index]
            stream.seek(self.position - self.offsets[index])
            block = stream.read(count)
            if len(block) != count:
                raise EOFError("Truncated archive part")
            blocks.append(block)
            size -= count
            self.position += count
        return b"".join(blocks)

    def close(self):
        for f in self.files:
            f.close()
        super().close()


def adsb_audit():
    directory = ROOT / BASE / "flight_tracking/adsblol"
    paths = sorted((directory / "archive").glob("*.tar.*"))
    paths = [p for p in paths if p.suffix in (".aa", ".ab")]
    if len(paths) != 2:
        return dict(status="archive_not_complete")
    inventory = json.loads((ROOT / BASE / "metadata/adsblol/release_prod0_20261101.json").read_text(encoding="utf-8"))
    for asset, path in zip(sorted(inventory["assets"], key=lambda a: a["name"]), paths):
        if path.name != asset["name"] or path.stat().st_size != asset["size"]:
            raise ValueError("ADS-B split archive incomplete")
        if asset.get("digest") != "sha256:" + digest(path):
            raise ValueError("ADS-B archive publisher checksum mismatch")
    matches = []
    member_count = 0
    with JoinedParts(paths) as stream, tarfile.open(fileobj=stream, mode="r:") as archive:
        for member in archive:
            member_count += 1
            if not member.isfile() or "a9ab17" not in Path(member.name).name.lower():
                continue
            payload = archive.extractfile(member).read()
            # Preserve member bytes including their original gzip representation.
            target = directory / "extracted" / member.name.lstrip("./")
            if not target.resolve().is_relative_to((directory / "extracted").resolve()):
                raise ValueError("Unsafe TAR member path")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() != payload:
                    raise ValueError("Existing ADS-B member differs")
            else:
                with target.open("xb") as f:
                    f.write(payload)
            data = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
            if data.get("icao", "").lower() != "a9ab17":
                raise ValueError("Trace ICAO mismatch")
            trace = data.get("trace", [])
            times = [data["timestamp"] + row[0] for row in trace]
            trace_rows = []
            for point, epoch in zip(trace, times):
                extra = point[8] if len(point) > 8 and isinstance(point[8], dict) else {}
                flags = point[6]
                trace_row = dict(utc=iso(epoch), unix_seconds=epoch, latitude=point[1], longitude=point[2],
                    altitude_ft=point[3], altitude_source="ground" if point[3] == "ground" else "geometric" if flags & 8 else "barometric",
                    ground_speed_kt=point[4], track_or_ground_heading_deg=point[5],
                    direction_kind="true_heading" if point[3] == "ground" else "ground_track",
                    flags=flags, position_stale=bool(flags & 1),
                    vertical_rate_fpm=point[7], vertical_rate_source="geometric" if flags & 4 else "barometric",
                    position_source=point[9] if len(point)>9 else None,
                    geometric_altitude_ft=point[10] if len(point)>10 else None,
                    geometric_vertical_rate_fpm=point[11] if len(point)>11 else None,
                    sparse_metadata_present=bool(extra))
                # No forward filling: sparse quality fields remain absent where
                # the trace did not include the corresponding aircraft object.
                for key in ("nic", "nac_p", "nac_v", "sil", "sil_type", "nic_baro", "rc", "gva", "sda", "squawk", "flight"):
                    trace_row[key] = extra.get(key)
                trace_rows.append(trace_row)
            write_csv("adsblol_N722BD_trace.csv", trace_rows)
            matches.append(dict(member=member.name, path=target.relative_to(ROOT).as_posix(),
                                sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload),
                                icao=data.get("icao"), registration=data.get("r"), aircraft_type=data.get("t"),
                                points=len(trace), first_utc=iso(min(times)) if times else None,
                                last_utc=iso(max(times)) if times else None,
                                event_window_points=sum("2026-11-01T17:00" <= iso(t) < "2026-11-01T18:30" for t in times),
                                metadata_keys=sorted({k for row in trace if len(row)>8 and isinstance(row[8], dict) for k in row[8]})))
    result = dict(status="target_found" if matches else "target_not_found", tar_members_scanned=member_count,
                  archive_parts=[dict(file=p.relative_to(ROOT).as_posix(), sha256=digest(p)) for p in paths],
                  matches=matches, license="ODbL-1.0; ADSB.lol and contributors",
                  limitation="Processed trace; not raw 1090 MHz payloads. Shared upstream receivers possible.")
    write_json("adsblol_member_provenance.json", result)
    return result


def airspace_audit():
    rows = []
    for p in sorted((ROOT / BASE / "airspace").glob("FAA_*_webtext.json")):
        records = json.loads(p.read_text(encoding="utf-8"))
        for record in records:
            text = " ".join(html.unescape(re.sub("<[^>]+>", " ", record.get("text", ""))).split())
            (OUT / (p.stem + ".txt")).write_text(text + "\n", encoding="utf-8")
            rows.append(dict(file=p.name, records=len(records), notam_id=record.get("notam_id"),
                             text_present=bool(text)))
    for p in (ROOT / BASE / "airspace").glob("*.xml"):
        ET.parse(p)
    write_json("airspace_record_coverage.json", rows)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original_checks = audit_originals()
    rows = list(csv.DictReader(MANIFEST.open(newline="", encoding="utf-8")))
    for row in rows:
        p = ROOT / row["repository_target"]
        if digest(p) != row["sha256"] or p.stat().st_size != int(row["size_bytes"]):
            raise ValueError(f"Public evidence checksum failure: {p}")
    radar, comparisons = radar_audit(rows)
    satellite = satellite_audit(rows)
    weather, bulletins = weather_audit()
    soundings = sounding_audit()
    adsb = adsb_audit()
    airspace = airspace_audit()
    summary = dict(public_http_responses=len(rows), response_bytes=sum(int(r["size_bytes"]) for r in rows),
        counts_by_kind=dict(Counter(r["kind"] for r in rows)), all_download_sha256_verified=True,
        supplied_manifest_checks=original_checks, supplied_radar_exact_matches=sum(r["exact_byte_match"] for r in comparisons),
        decoded_radar_volumes=len(radar), satellite_files_opened=len(satellite),
        aviation_weather=weather, bulletin_coverage=bulletins, event_soundings=soundings,
        adsb=adsb, airspace=airspace,
        limitations=["Integrity and format/date checks are not an independent validation of every measurement.",
                     "New material has not been integrated into the 3D radar/flight analysis.",
                     "Empty responses and inventory limits do not prove absence of weather, radar operations or restrictions."])
    write_json("acquisition_summary.json", summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ("aviation_weather", "bulletin_coverage", "event_soundings", "adsb", "airspace")}, indent=2))


if __name__ == "__main__":
    main()
