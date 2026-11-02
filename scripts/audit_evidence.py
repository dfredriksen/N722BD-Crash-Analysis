"""Stream evidence checksums; optionally materialize verified original files.

Never overwrites an existing file. The supplied ZIP remains the original package.
"""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
import zipfile
from evidence_source import EvidenceSource


def sha256(stream):
    h = hashlib.sha256()
    while block := stream.read(1024*1024):
        h.update(block)
    return h.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=root/'data/evidence_packages/N722BD_remaining_GitHub_upload.zip')
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    rows = list(csv.DictReader((root/'docs/evidence_manifest.csv').open()))
    audits = []
    with EvidenceSource(root,args.zip) as z:
        for row in rows:
            name = row['repository_target']
            if name not in z.namelist():
                raise ValueError(f'Missing evidence member: {name}')
            with z.open(name) as f:
                actual = sha256(f)
            size = z.getinfo(name).file_size
            good = actual == row['sha256'] and size == int(row['size_bytes'])
            audits.append(dict(repository_target=name, actual_size_bytes=size,
                               actual_sha256=actual, verified=good))
        if not all(r['verified'] for r in audits):
            raise ValueError('Checksum failure; extraction refused')
        if args.extract:
            for row in rows:
                target = (root/row['repository_target']).resolve()
                if not target.is_relative_to(root.resolve()):
                    raise ValueError('Evidence target escapes repository')
                if target.name != row['filename']:
                    raise ValueError('Original filename would change')
                if target.exists():
                    with target.open('rb') as f:
                        if sha256(f) != row['sha256']:
                            raise ValueError(f'Refusing to overwrite conflicting file: {target}')
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(row['repository_target']) as source, target.open('xb') as dest:
                    shutil.copyfileobj(source, dest)
                with target.open('rb') as f:
                    if sha256(f) != row['sha256']:
                        raise ValueError(f'Post-extraction checksum failure: {target}')
        supplementary = []
        for member in z.infolist():
            with z.open(member.filename) as f:
                supplementary.append(dict(filename=member.filename, size_bytes=member.file_size,
                                          sha256=sha256(f)))
        out = root/'results/independent'
        out.mkdir(parents=True, exist_ok=True)
        (out/'package_members.json').write_text(json.dumps(supplementary, indent=2))
        member_checks=[]
        with (root/'docs/supplied_package_manifest.csv').open() as manifest:
            for row in csv.DictReader(manifest):
                target=root/row['repository_target']
                with target.open('rb') as stream:
                    actual=sha256(stream)
                with z.open(row['original_package_member']) as stream:
                    supplied=sha256(stream)
                member_checks.append(dict(repository_target=row['repository_target'],
                    expected_sha256=row['sha256'],actual_sha256=actual,
                    source_sha256=supplied,verified=actual==supplied==row['sha256'] and
                    target.stat().st_size==int(row['size_bytes'])))
        with (out/'supplied_member_integrity.csv').open('w',newline='') as dest:
            writer=csv.DictWriter(dest,fieldnames=member_checks[0].keys())
            writer.writeheader();writer.writerows(member_checks)
        if not all(r['verified'] for r in member_checks):
            raise ValueError('Supplied artifact integrity check failed')
        package_hash = None
        if args.zip.exists():
            with args.zip.open('rb') as f:
                package_hash = sha256(f)
        (out/'package_audit.json').write_text(json.dumps(dict(package_name=args.zip.name,
            size_bytes=args.zip.stat().st_size if args.zip.exists() else None, sha256=package_hash,
            evidence_source='retained_zip' if args.zip.exists() else 'committed_original_members',
            extracted=args.extract, evidence=audits), indent=2))
    print(json.dumps(dict(verified=sum(r['verified'] for r in audits), total=len(audits),
                          extracted=args.extract, package_sha256=package_hash), indent=2))


if __name__ == '__main__':
    main()
