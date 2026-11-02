"""Collect bounded, anonymous public evidence without changing supplied originals.

Every response has a receipt and SHA-256. HTTP success is NOT a coverage or
scientific-validity assertion; audit_public_data.py separately checks contents.
Existing bytes are never overwritten. Reuse verifies the recorded hash.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("data/public/2026-11-01/acquisition_20261102")
MANIFEST = ROOT / "docs/public_evidence_manifest.csv"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
FIELDS = ["repository_target", "kind", "source_url", "final_url", "retrieved_utc",
          "http_status", "size_bytes", "sha256", "content_type", "content_encoding",
          "etag", "last_modified", "receipt_path", "transport_error"]


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


class Collector:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows = {}
        if MANIFEST.exists():
            with MANIFEST.open(newline="", encoding="utf-8") as f:
                self.rows = {r["repository_target"]: r for r in csv.DictReader(f)}

    def save_manifest(self):
        temporary = MANIFEST.with_suffix(".csv.tmp")
        with temporary.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(self.rows[k] for k in sorted(self.rows))
        temporary.replace(MANIFEST)

    def fetch(self, relative, url, kind):
        with self.lock:
            base = (ROOT / BASE).resolve()
            target = (base / relative).resolve()
            if not target.is_relative_to(base):
                raise ValueError(f"Destination escapes acquisition directory: {target} vs {base}")
            target.parent.mkdir(parents=True, exist_ok=True)
            key = target.relative_to(ROOT).as_posix()
            old = self.rows.get(key)
        if old:
            if old["source_url"] != url or (target.exists() and digest(target) != old["sha256"]):
                raise ValueError(f"Existing receipt/file conflict: {key}")
            if target.exists():
                return old
        if target.exists():
            raise FileExistsError(f"Refusing unreceipted existing file: {target}")
        row = dict.fromkeys(FIELDS, "")
        row.update(repository_target=key, kind=kind, source_url=url,
                   retrieved_utc=datetime.now(timezone.utc).isoformat())
        headers = {}
        temporary = target.with_name(target.name + ".part")
        # A bounded stream prevents accidentally requesting an entire large archive.
        # Identity encoding preserves response payload bytes (TLS framing excluded).
        try:
            with requests.get(url, timeout=(20, 90), stream=True,
                              headers={"User-Agent": "N722BD-evidence-research/1.0",
                                       "Accept-Encoding": "identity"}) as response:
                # Session cookies are not scientific provenance. These are
                # anonymous fetches; retain content/transport headers only.
                headers = {k: v for k, v in response.headers.items() if k.lower() != "set-cookie"}
                row.update(final_url=response.url, http_status=response.status_code,
                           content_type=response.headers.get("Content-Type", ""),
                           content_encoding=response.headers.get("Content-Encoding", ""),
                           etag=response.headers.get("ETag", ""),
                           last_modified=response.headers.get("Last-Modified", ""))
                count = 0
                with temporary.open("xb") as f:
                    for chunk in response.iter_content(1024 * 1024):
                        count += len(chunk)
                        cap = 2_100_000_000 if kind == "adsblol_archive_part" else 100 * 1024 * 1024
                        if count > cap:
                            raise ValueError(f"Individual response exceeded {cap} byte acquisition cap")
                        f.write(chunk)
                if response.headers.get("Content-Encoding") not in (None, "identity"):
                    raise ValueError("Unexpected HTTP content encoding; raw preservation not established")
                length = response.headers.get("Content-Length")
                if length is not None and int(length) != count:
                    raise ValueError("Truncated HTTP response")
                if old and (digest(temporary) != old["sha256"] or count != int(old["size_bytes"])):
                    raise ValueError("Source changed since preserved acquisition; original hash not restored")
                temporary.rename(target)
        except Exception as exc:
            if temporary.exists():
                temporary.unlink()  # Only this exact acquisition's partial file.
            row["transport_error"] = f"{type(exc).__name__}: {exc}"
            # No placeholder file is represented as downloaded evidence.
            error_path = ROOT / BASE / "metadata/errors" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
            error_path.parent.mkdir(parents=True, exist_ok=True)
            if not error_path.exists():
                error_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
            print(f"FAILED {relative}: {row['transport_error']}", flush=True)
            return row
        row.update(size_bytes=target.stat().st_size, sha256=digest(target))
        if old:
            # Keep the historical acquisition record. A later verified fetch has
            # a separate receipt and must not impersonate the original retrieval.
            restored = ROOT / "results/public_acquisition/restoration_receipts"
            restored.mkdir(parents=True, exist_ok=True)
            receipt = restored / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            receipt.write_text(json.dumps(dict(row, response_headers=headers), indent=2), encoding="utf-8")
            print(f"RESTORED verified original bytes: {relative}", flush=True)
            return old
        receipt = target.with_name(target.name + ".receipt.json")
        row["receipt_path"] = receipt.relative_to(ROOT).as_posix()
        with self.lock:
            with receipt.open("x", encoding="utf-8") as f:
                json.dump(dict(row, response_headers=headers), f, indent=2)
            self.rows[key] = row
            self.save_manifest()
        print(f"HTTP {row['http_status']} {relative} ({row['size_bytes']} bytes)", flush=True)
        return row

    def batch(self, jobs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(lambda args: self.fetch(*args), jobs))

    def s3_list(self, bucket, prefix, label):
        objects, token, page = [], None, 1
        while True:
            params = {"list-type": "2", "prefix": prefix, "max-keys": 1000}
            if token:
                params["continuation-token"] = token
            row = self.fetch(f"metadata/inventories/{label}_{page:03}.xml",
                             f"https://{bucket}.s3.amazonaws.com/?{urlencode(params)}", "inventory")
            if str(row["http_status"]) != "200":
                raise RuntimeError(f"Inventory failed: {label}")
            tree = ET.parse(ROOT / row["repository_target"])
            for item in tree.findall("s:Contents", NS):
                objects.append({"key": item.findtext("s:Key", namespaces=NS),
                                "size": int(item.findtext("s:Size", namespaces=NS)),
                                "etag": item.findtext("s:ETag", namespaces=NS)})
            if tree.findtext("s:IsTruncated", namespaces=NS) != "true":
                break
            token = tree.findtext("s:NextContinuationToken", namespaces=NS)
            if not token:
                raise RuntimeError("Truncated inventory lacks continuation token")
            page += 1
        return objects


def select_radar(objects, site):
    eligible = sorted((o for o in objects if re.fullmatch(
        rf"2026/11/01/{site}/{site}20261101_\d{{6}}_V06", o["key"])), key=lambda o: o["key"])
    before = [o for o in eligible if Path(o["key"]).name[13:19] < "170000"]
    within = [o for o in eligible if "170000" <= Path(o["key"]).name[13:19] < "183000"]
    return before[-1:] + within


def collect_radar(c):
    bucket = "unidata-nexrad-level2"
    jobs = []
    for site in ("KAMX", "KMLB"):
        objects = c.s3_list(bucket, f"2026/11/01/{site}/", site)
        selected = select_radar(objects, site)
        print(f"Selected {site}: {len(selected)} volumes, {sum(o['size'] for o in selected)/1e6:.1f} MB", flush=True)
        for o in selected:
            jobs.append((f"radar/{site}/{Path(o['key']).name}",
                         f"https://{bucket}.s3.amazonaws.com/{o['key']}", "nexrad_level2"))
    c.batch(jobs)


def collect_weather(c):
    c.fetch("metadata/openapi.yaml", "https://aviationweather.gov/data/schema/openapi.yaml", "documentation")
    date = "2026-11-01T20:00:00Z"
    stations = "KPBI,KBCT,KFLL,KMIA,KFXE,KOPF,KFPR,KAPF,KMLB,KTMB"
    queries = {
        "metar": dict(ids=stations, format="json", date=date, hours=6),
        "taf": dict(ids=stations, format="json", date=date),
        "pirep": dict(bbox="24,-83,29,-78", format="json", date=date, age=6),
        "gairmet": dict(format="json", date="2026-11-01T18:00:00Z"),
        "cwa": dict(format="json", date="2026-11-01T18:00:00Z"),
    }
    # Keep requests below AWC's published rate limit; no current SIGMET substituted
    # for an event-time archive (that endpoint has no historical date parameter).
    for product, params in queries.items():
        c.fetch(f"weather/awc/{product}_20261101.json",
                f"https://aviationweather.gov/api/data/{product}?{urlencode(params)}", "aviation_weather")
    for hour in (17, 18):
        params = dict(ids=stations, format="json", date=f"2026-11-01T{hour}:00:00Z")
        c.fetch(f"weather/awc/taf_20261101_{hour}Z.json",
                "https://aviationweather.gov/api/data/taf?" + urlencode(params), "aviation_weather")
    c.batch([(f"weather/noaa_metar_cycles/{hour}Z.TXT",
              f"https://tgftp.nws.noaa.gov/data/observations/metar/cycles/{hour}Z.TXT", "metar_rolling_snapshot")
             for hour in ("16", "17", "18", "19", "20")])


def goes_start(key):
    match = re.search(r"_s(\d{13})\d_", key)
    if not match:
        raise ValueError(f"Unrecognized GOES timestamp: {key}")
    return datetime.strptime(match[1], "%Y%j%H%M%S").replace(tzinfo=timezone.utc)


def collect_satellite(c):
    bucket = "noaa-goes19"
    begin = datetime(2026, 11, 1, 17, tzinfo=timezone.utc)
    end = datetime(2026, 11, 1, 18, 30, tzinfo=timezone.utc)
    for product in ("GLM-L2-LCFA", "ABI-L2-CMIPC"):
        objects = []
        for hour in (17, 18):
            objects += c.s3_list(bucket, f"{product}/2026/305/{hour}/", f"G19_{product}_{hour}")
        selected = [o for o in objects if begin <= goes_start(o["key"]) < end
                    and (product.startswith("GLM") or "-M6C13_" in o["key"])]
        print(f"Selected {product}: {len(selected)} files, {sum(o['size'] for o in selected)/1e6:.1f} MB", flush=True)
        c.batch([(f"satellite/{product}/{Path(o['key']).name}",
                  f"https://{bucket}.s3.amazonaws.com/{o['key']}", "goes_glm" if product.startswith("GLM") else "goes_abi_c13")
                 for o in selected])


def collect_soundings(c):
    base = "https://www.ncei.noaa.gov/pub/data/igra/"
    c.fetch("metadata/igra/igra2-station-list.txt", base + "igra2-station-list.txt", "station_metadata")
    c.fetch("metadata/igra/igra2-data-format.txt", base + "data/igra2-data-format.txt", "documentation")
    c.fetch("metadata/igra/igra2-readme.txt", base + "igra2-readme.txt", "documentation")
    c.fetch("metadata/igra/data-y2d.html", base + "data/data-y2d/", "inventory")
    c.batch([(f"soundings/{station}-data-beg2026.txt.zip",
              base + f"data/data-y2d/{station}-data-beg2026.txt.zip", "igra_sounding")
             for station in ("USM00072202", "USM00072201", "USM00072210")])


def collect_bulletins(c):
    # Explicit documented sdate/edate required: unsupported 'date' silently
    # returns current products on this endpoint. Preserve server bundles intact.
    c.fetch("metadata/iem_afos_help.html",
            "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help=", "documentation")
    for pil in ("SIGE", "AIRMET", "AFDMFL", "AFDMLB", "CWAMIA", "CWAJAX",
                "FTMAMX", "FTMMLB", "FTMPBI", "WARMFL", "WARMLB"):
        params = dict(pil=pil, sdate="2026-11-01T12:00Z", edate="2026-11-01T21:00Z",
                      limit=9999, fmt="text", order="asc")
        c.fetch(f"weather/nws_bulletins/{pil}_20261101_12-21Z.txt",
                "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?" + urlencode(params),
                "nws_bulletin_bundle")


def collect_availability(c):
    for product in ("AAL2", "ABL3ALL"):
        params = dict(id="TPBI", yyyy=2026, mm=11, dd="01", product=product)
        c.fetch(f"metadata/availability/TPBI_NCEI_{product}.html",
                "https://www.ncei.noaa.gov/nexradinv/displaygraphs.jsp?" + urlencode(params), "availability_only")
    for product in ("TZ0", "TV0", "TZL"):
        c.s3_list("unidata-nexrad-level3", f"PBI_{product}_2026_11_01", f"TPBI_{product}")
    c.fetch("metadata/availability/GCP_Level3_20261101.json",
            "https://storage.googleapis.com/storage/v1/b/gcp-public-data-nexrad-l3/o?" +
            urlencode(dict(prefix="2026/11/01/", delimiter="/", maxResults=1000)), "availability_only")
    params = dict(station="PBI", data="all", year1=2026, month1=11, day1=1,
                  year2=2026, month2=11, day2=2, tz="Etc/UTC", format="onlycomma",
                  latlon="yes", elev="yes", missing="M", trace="T", direct="no")
    c.fetch("metadata/availability/IEM_PBI_20261101.csv",
            "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + urlencode(params) +
            "&report_type=1&report_type=2", "availability_only")


def collect_airspace(c):
    # Current-list snapshot is not proof of the historical amendment/cancellation
    # chain. Save full text/XML for identified potentially relevant NOTAMs too.
    c.fetch("airspace/FAA_getTfrList_20261102.json",
            "https://tfr.faa.gov/tfrapi/getTfrList", "faa_current_tfr_list")
    for number in ("6/0100", "6/3803", "6/3963"):
        label = number.replace("/", "_")
        c.fetch(f"airspace/FAA_{label}_webtext.json",
                "https://tfr.faa.gov/tfrapi/getWebText?" + urlencode(dict(notamId=number)), "faa_notam_webtext")
        c.fetch(f"airspace/detail_{label}.xml",
                f"https://tfr.faa.gov/download/detail_{label}.xml", "faa_notam_xml")


def collect_adsb(c):
    repo = "adsblol/globe_history_2026"
    tag = "v2026.11.01-planes-readsb-prod-0"
    row = c.fetch("metadata/adsblol/release_prod0_20261101.json",
                  f"https://api.github.com/repos/{repo}/releases/tags/{tag}", "release_inventory")
    if str(row["http_status"]) != "200":
        raise RuntimeError("ADS-B release inventory unavailable")
    release = json.loads((ROOT / row["repository_target"]).read_text(encoding="utf-8"))
    assets = sorted(release["assets"], key=lambda x: x["name"])
    if sum(a["size"] for a in assets) > 4_000_000_000:
        raise ValueError("ADS-B daily archive exceeds bounded 4 GB acquisition")
    c.fetch("metadata/adsblol/README.md", f"https://raw.githubusercontent.com/{repo}/main/README.md", "documentation")
    c.fetch("metadata/adsblol/LICENSE-ODbL.txt", f"https://raw.githubusercontent.com/{repo}/main/LICENSE-ODbL.txt", "license")
    c.fetch("metadata/adsblol/README-json.md", "https://raw.githubusercontent.com/wiedehopf/readsb/dev/README-json.md", "documentation")
    for asset in assets:
        row = c.fetch(f"flight_tracking/adsblol/archive/{asset['name']}",
                      asset["browser_download_url"], "adsblol_archive_part")
        expected = asset.get("digest")
        if str(row["http_status"]) != "200" or int(row["size_bytes"]) != asset["size"]:
            raise ValueError("ADS-B archive response does not match published byte count")
        if expected and expected != "sha256:" + row["sha256"]:
            raise ValueError("ADS-B archive does not match GitHub published digest")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    groups = ["radar", "weather", "satellite", "soundings", "bulletins", "availability", "airspace", "adsb"]
    parser.add_argument("groups", nargs="*", metavar="GROUP", help=", ".join(groups))
    parser.add_argument("--restore", action="store_true", help="Restore missing files against the preserved manifest hashes")
    args = parser.parse_args()
    if any(group not in groups for group in args.groups):
        parser.error("Unknown acquisition group")
    collector = Collector()
    if args.restore:
        for row in list(collector.rows.values()):
            relative = Path(row["repository_target"]).relative_to(BASE)
            result = collector.fetch(str(relative), row["source_url"], row["kind"])
            if result["transport_error"]:
                raise RuntimeError(result["transport_error"])
        return
    if not args.groups:
        parser.error("Select acquisition groups or --restore")
    for group in args.groups:
        globals()[f"collect_{group}"](collector)


if __name__ == "__main__":
    main()
