#!/usr/bin/env python3
"""Load compiled CSVs from results/compiled and consolidate into an Excel workbook.
If pandas/openpyxl aren't installed, prints instructions and exits.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
COMPILED_DIR = ROOT.joinpath('results','compiled')
MANIFEST = ROOT.joinpath('results','compiled_manifest.json')
OUT_XLSX = COMPILED_DIR.joinpath('compiled_data.xlsx')

def main():
    try:
        import pandas as pd
    except Exception:
        print('pandas is required to build Excel workbook. Install with: pip install pandas openpyxl')
        return 2

    if not MANIFEST.exists():
        print('Manifest not found at', MANIFEST)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    # pick top N by size (default 30) but only compiled CSV outputs
    csv_entries = [m for m in manifest if m.get('compiled','').endswith('.csv')]
    csv_entries.sort(key=lambda x: x.get('size',0), reverse=True)
    top = csv_entries[:30]

    writer = pd.ExcelWriter(OUT_XLSX, engine='openpyxl')
    for e in top:
        comp = Path(e['compiled'])
        sheet = Path(e['source']).stem
        try:
            df = pd.read_csv(comp, dtype=str)
            # limit columns/sheet name length
            sheet_name = sheet[:31]
            df.to_excel(writer, sheet_name=sheet_name or 'sheet', index=False)
            print('Wrote sheet', sheet_name)
        except Exception as ex:
            print('Failed to write', comp, '->', ex)
    writer.close()
    print('Wrote Excel workbook to', OUT_XLSX)
    return 0

if __name__ == '__main__':
    sys.exit(main())
