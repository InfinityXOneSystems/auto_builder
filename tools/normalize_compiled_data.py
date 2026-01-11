#!/usr/bin/env python3
"""Normalize compiled CSVs into a common schema and produce a consolidated signals.csv

This script does not require pandas; it uses the stdlib csv/json modules.

Output:
- results/compiled/normalized/<source>_normalized.csv
- results/compiled/signals.csv  (consolidated)
"""
import csv
import json
import re
import sys
from pathlib import Path

MANIFEST = Path("results/compiled_manifest.json")
COMPILED_DIR = Path("results/compiled")
NORMALIZED_DIR = COMPILED_DIR / "normalized"
CONSOLIDATED = COMPILED_DIR / "signals.csv"

SAMPLE_ROWS_PER_FILE = 200
MAX_CONSOLIDATED_ROWS = 5000

FIELD_HINTS = {
    "url": ["url", "link", "href", "source_url", "page_url"],
    "title": ["title", "name", "headline", "subject"],
    "text": ["text", "content", "body", "description", "snippet", "html", "raw"],
    "date": ["date", "ts", "timestamp", "created_at", "created", "time"],
    "score": ["score", "rating", "confidence", "ai_score", "relevance"],
}


def guess_column(header, hints):
    hdr = [h.lower() for h in header]
    for hint in hints:
        if hint in hdr:
            return header[hdr.index(hint)]
    # try substring match
    for h in header:
        lh = h.lower()
        for hint in hints:
            if hint in lh:
                return h
    return None


def extract_from_cell(cell):
    if cell is None:
        return ""
    cell = cell.strip()
    if not cell:
        return ""
    # try json
    if cell.startswith("{") or cell.startswith("["):
        try:
            obj = json.loads(cell)
        except Exception:
            return cell
        # if it's dict, try to get useful string fields
        if isinstance(obj, dict):
            for key in ("text", "content", "body", "description"):
                if key in obj and isinstance(obj[key], str):
                    return obj[key].strip()
            # fallback: join string values
            parts = []
            for v in obj.values():
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
            return " ".join(parts)[:10000]
        if isinstance(obj, list):
            parts = []
            for item in obj:
                if isinstance(item, str):
                    parts.append(item.strip())
                elif isinstance(item, dict):
                    for key in ("text", "content", "body", "description"):
                        if key in item and isinstance(item[key], str):
                            parts.append(item[key].strip())
            return " ".join(parts)[:10000]
    return cell


def normalize_file(
    compiled_path, source_path, out_dir, sample_limit=SAMPLE_ROWS_PER_FILE
):
    compiled = Path(compiled_path)
    if not compiled.exists():
        return 0, 0
    # Increase CSV field size limit to avoid _csv.Error on very large fields
    try:
        csv.field_size_limit(10 * 1024 * 1024)
    except Exception:
        try:
            csv.field_size_limit(sys.maxsize)
        except Exception:
            pass

    with compiled.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        url_col = guess_column(header, FIELD_HINTS["url"])
        title_col = guess_column(header, FIELD_HINTS["title"])
        text_col = guess_column(header, FIELD_HINTS["text"])
        date_col = guess_column(header, FIELD_HINTS["date"])
        score_col = guess_column(header, FIELD_HINTS["score"])

        rows_out = []
        read = 0
        for r in reader:
            read += 1
            if read > sample_limit:
                break
            url = extract_from_cell(r.get(url_col, "")) if url_col else ""
            title = extract_from_cell(r.get(title_col, "")) if title_col else ""
            text = extract_from_cell(r.get(text_col, "")) if text_col else ""
            # Truncate overly large text
            if isinstance(text, str) and len(text) > 1000000:
                text = text[:1000000]
            # if no text found, attempt to join common fields
            if not text:
                possible = []
                for k in header:
                    if re.search(
                        r"(paragraph|line|sentence|content|body|text)", k, re.I
                    ):
                        v = extract_from_cell(r.get(k, ""))
                        if v:
                            possible.append(v)
                if possible:
                    text = " ".join(possible)[:10000]
            date = r.get(date_col, "") if date_col else ""
            score = r.get(score_col, "") if score_col else ""
            # sanitize
            if isinstance(date, str):
                date = date.strip()
            if isinstance(score, str):
                score = score.strip()

            if not (url or title or text):
                continue
            rows_out.append(
                {
                    "source": source_path,
                    "orig": str(compiled),
                    "url": url,
                    "title": title,
                    "text": text,
                    "date": date,
                    "score": score,
                }
            )

    if not rows_out:
        return 0, read

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / (compiled.stem + "_normalized.csv")
    with out_file.open("w", encoding="utf-8", newline="") as outfh:
        writer = csv.DictWriter(
            outfh,
            fieldnames=["source", "orig", "url", "title", "text", "date", "score"],
        )
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)

    return len(rows_out), read


def main():
    if not MANIFEST.exists():
        print("Manifest not found at", MANIFEST)
        return
    with MANIFEST.open("r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    consolidated_fh = CONSOLIDATED.open("w", encoding="utf-8", newline="")
    consolidated_writer = csv.DictWriter(
        consolidated_fh,
        fieldnames=["source", "orig", "url", "title", "text", "date", "score"],
    )
    consolidated_writer.writeheader()

    total_files = 0
    total_rows = 0
    consolidated_rows = 0

    for item in manifest:
        src = item.get("source")
        compiled = item.get("compiled")
        if not compiled:
            continue
        compiled_path = Path(compiled)
        if not compiled_path.exists():
            continue
        # skip very small files
        if item.get("size", 0) < 50:
            continue

        total_files += 1
        rows_out, read = normalize_file(compiled_path, src, NORMALIZED_DIR)
        total_rows += rows_out
        if rows_out > 0:
            # append rows to consolidated up to a cap
            with (NORMALIZED_DIR / (compiled_path.stem + "_normalized.csv")).open(
                "r", encoding="utf-8"
            ) as nf:
                rreader = csv.DictReader(nf)
                for r in rreader:
                    if consolidated_rows >= MAX_CONSOLIDATED_ROWS:
                        break
                    consolidated_writer.writerow(r)
                    consolidated_rows += 1

    consolidated_fh.close()

    print("Normalized files:", total_files)
    print("Normalized rows written (per-source):", total_rows)
    print("Consolidated rows:", consolidated_rows)
    print("Per-source normalized files in", NORMALIZED_DIR)
    print("Consolidated signals file at", CONSOLIDATED)


if __name__ == "__main__":
    main()
