#!/usr/bin/env python3
"""Scan backup directories for scraped data files (JSON/NDJSON/CSV/TSV/YAML)
and compile them into CSVs under results/compiled/. Creates a manifest.
"""
import csv
import json
import os
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKUP_GLOB = ROOT.parent.joinpath('mcp-backup-*')
OUT_DIR = ROOT.joinpath('results','compiled')
OUT_DIR.mkdir(parents=True, exist_ok=True)

def iter_backup_paths():
    parent = ROOT.parent
    for p in parent.glob('mcp-backup-*'):
        if p.is_dir():
            yield p

def find_files(backup_path):
    patterns = ['**/*.json','**/*.jsonl','**/*.ndjson','**/*.csv','**/*.tsv','**/*.yaml','**/*.yml']
    for pat in patterns:
        for f in backup_path.glob(pat):
            yield f

def try_load_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None

def write_csv_rows(outpath, headers, rows):
    with open(outpath, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def process_json_file(path, out_prefix):
    text = path.read_text(encoding='utf-8', errors='ignore')
    data = try_load_json(text)
    if data is None:
        # try ndjson
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = try_load_json(line)
            if obj is None:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        if rows:
            keys = sorted({k for r in rows for k in r.keys()})
            out = OUT_DIR.joinpath(f"{out_prefix}.csv")
            write_csv_rows(out, keys, rows)
            return out
        return None

    # If data is a dict with known keys
    rows = []
    if isinstance(data, dict):
        # If it contains a 'results' or 'seeds' list, expand
        if 'results' in data and isinstance(data['results'], list):
            rows = data['results']
        elif 'seeds' in data and isinstance(data['seeds'], list):
            rows = data['seeds']
        else:
            # treat the dict as single row
            rows = [data]
    elif isinstance(data, list):
        rows = data

    if rows:
        keys = sorted({k for r in rows for k in (r.keys() if isinstance(r, dict) else [])})
        out = OUT_DIR.joinpath(f"{out_prefix}.csv")
        write_csv_rows(out, keys, [r for r in rows if isinstance(r, dict)])
        return out
    return None

def process_csv_file(path, out_prefix):
    # copy or normalize header
    out = OUT_DIR.joinpath(f"{out_prefix}.csv")
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as src, open(out, 'w', newline='', encoding='utf-8') as dst:
            dst.write(src.read())
        return out
    except Exception:
        return None

def main():
    manifest = []
    for b in iter_backup_paths():
        for f in find_files(b):
            rel = f.relative_to(b)
            out_prefix = f"{b.name}_{rel.as_posix().replace('/','_').replace('\\','_')}"
            ext = f.suffix.lower()
            out = None
            try:
                if ext in ['.json','.jsonl','.ndjson']:
                    out = process_json_file(f, out_prefix)
                elif ext in ['.csv','.tsv']:
                    out = process_csv_file(f, out_prefix)
                elif ext in ['.yaml','.yml']:
                    # skip yaml seed files for now, but copy as text
                    out = OUT_DIR.joinpath(f"{out_prefix}.yaml")
                    out.write_text(f.read_text(encoding='utf-8', errors='ignore'))
                if out:
                    manifest.append({'source': str(f), 'compiled': str(out), 'size': f.stat().st_size})
            except Exception as e:
                manifest.append({'source': str(f), 'error': repr(e)})
    manifest_path = OUT_DIR.parent.joinpath('compiled_manifest.json')
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Wrote manifest:', manifest_path)

if __name__ == '__main__':
    main()
