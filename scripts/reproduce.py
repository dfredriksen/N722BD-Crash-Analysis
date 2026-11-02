"""Run the full investigation/review and compare outputs in the current checkout.

For an isolated reproduction, invoke in a separate clone and fresh locked venv.
This runner changes generated results only, records source hashes before/after,
and keeps logs outside results/independent and results/review to avoid recursion.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def source_audit():
    rows=[]
    for name in ('evidence_manifest.csv','supplied_package_manifest.csv'):
        for row in csv.DictReader((ROOT/'docs'/name).open()):
            path=ROOT/row['repository_target']; actual=sha(path)
            if actual!=row['sha256'] or path.stat().st_size!=int(row['size_bytes']):
                raise ValueError('Original evidence mismatch: '+row['repository_target'])
            rows.append(dict(manifest=name,path=row['repository_target'],sha256=actual,size_bytes=path.stat().st_size))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir',type=Path,required=True)
    parser.add_argument('--clear-generated',action='store_true',
                        help='Back up then remove generated results before rerunning; preserves static documentation/audits')
    args=parser.parse_args(); logs=args.log_dir.resolve()
    if any(logs.is_relative_to((ROOT/folder).resolve()) for folder in ('data','results')):
        raise ValueError('Logs/backups must be outside evidence and result directories')
    logs.mkdir(parents=True,exist_ok=True)
    before=source_audit()
    (logs/'source_audit_before.json').write_text(json.dumps(before,indent=2))
    baseline={str(p.relative_to(ROOT)):sha(p) for folder in ('independent','review')
              for p in (ROOT/'results'/folder).glob('*') if p.is_file()}
    if args.clear_generated:
        static={'README.md','git_blob_integrity.csv','git_file_size_audit.csv',
                'unchanged_science_from_838f10d.json'}
        for relative, expected in baseline.items():
            path=(ROOT/relative).resolve()
            if path.name in static:continue
            if not path.is_relative_to((ROOT/'results').resolve()):
                raise ValueError('Generated target escaped results directory')
            backup=logs/'baseline'/relative
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,backup)
            if sha(backup)!=expected:raise ValueError('Baseline backup verification failed')
            path.unlink()
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    env.update(PYTHONNOUSERSITE='1',MPLCONFIGDIR=str(logs/'font-cache'),PYTHONIOENCODING='utf-8')
    stages=[('environment',['-c','import sys,json,importlib.metadata as m; print(json.dumps(dict(python=sys.version,prefix=sys.prefix,base_prefix=sys.base_prefix,packages={x.metadata["Name"]:x.version for x in m.distributions()}),indent=2))']),
        ('audit',['scripts/audit_evidence.py','--extract']),
        ('full_pyart',['scripts/validate_n722bd_pyart.py',*[str(p) for p in sorted((ROOT/'data/radar/KAMX').iterdir())],
                       '--all-rays','--output','results/independent/pyart_highlevel_samples.csv']),
        ('api_consistency',['scripts/check_highlevel_api.py']),
        ('investigation',['scripts/run_investigation.py','--extracted']),
        ('flight_state',['scripts/flight_state_timeline.py']),
        ('overlays',['scripts/make_overlays.py']),
        ('summary',['scripts/summarize_validation.py']),
        ('independent_decode',['scripts/review/independent_decode.py']),
        ('custom_coverage',['scripts/review/custom_coverage_check.py']),
        ('scientific_challenges',['scripts/review/scientific_challenges.py']),
        ('perimeter',['scripts/review/perimeter_check.py']),
        ('flight_evidence',['scripts/review/flight_evidence_check.py']),
        ('tests',['-m','unittest','discover','-s','tests','-v'])]
    status=[]
    for name,command in stages:
        print('START',name,flush=True);start=time.monotonic()
        with (logs/(name+'.log')).open('w',encoding='utf-8') as stream:
            result=subprocess.run([sys.executable,*command],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        status.append(dict(stage=name,returncode=result.returncode,seconds=time.monotonic()-start,command=command))
        (logs/'stages.json').write_text(json.dumps(status,indent=2))
        print('END',name,result.returncode,flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    after=source_audit()
    (logs/'source_audit_after.json').write_text(json.dumps(after,indent=2))
    if before!=after:raise ValueError('Original evidence changed during analysis')
    differences=[]
    for path,old in baseline.items():
        current=sha(ROOT/path) if (ROOT/path).exists() else None
        differences.append(dict(file=path,before_sha256=old,after_sha256=current,byte_identical=old==current))
    (logs/'output_comparison.json').write_text(json.dumps(differences,indent=2))
    (logs/'run.json').write_text(json.dumps(dict(source_entries_verified=len(after),
        original_evidence_unchanged=True,generated_outputs_cleared_before_run=args.clear_generated,
        stages_passed=len(status),baseline_artifacts=len(baseline),
        byte_identical=sum(x['byte_identical'] for x in differences),
        differences=[x['file'] for x in differences if not x['byte_identical']]),indent=2))
    if any(x['after_sha256'] is None for x in differences):
        raise ValueError('Expected output was not regenerated; see output_comparison.json')


if __name__=='__main__':main()
