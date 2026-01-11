#!/usr/bin/env python3
"""Push consolidated signals CSV to multiple Google Sheets with basic formatting.

Usage:
 - Provide a service account JSON via env `GOOGLE_SERVICE_ACCOUNT_JSON` (path) or place the file at `.secrets/service_account.json`.
 - Alternatively, place OAuth client secrets at `.secrets/credentials.json` and follow the local browser flow.

The script will read `results/compiled/signals.csv` and write it to each target spreadsheet.
"""
import csv
import os
import sys
from pathlib import Path

TARGET_SPREADSHEETS = {
    "real_estate": "1G4ACS7NJRBcE8XyhU4V2un5xPIm_b90fPi2Rt4iMs4k",
    "asset_prediction": "14geQJz48lBe64is7qoOIZFMJQHgPE53PbOZkS8w3WsA",
    "business_loan": "1SMHr-FOksFUgxsRf4QmUzASyKiWPVtG5SpQNurgE_eI",
}

SIGNALS_CSV = Path("results/compiled/signals.csv")


def ensure_packages():
    try:
        import gspread  # noqa: F401
    except Exception:
        print("Required packages missing. Install with:")
        print(
            "  pip install gspread google-auth google-auth-oauthlib google-auth-httplib2 gspread-formatting"
        )
        sys.exit(2)


def get_gspread_client():
    # Prefer service account JSON from env or .secrets
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_path and Path(sa_path).exists():
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
        return gspread.authorize(creds)

    # fallback to .secrets/service_account.json
    fallback = Path(".secrets/service_account.json")
    if fallback.exists():
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(fallback), scopes=scopes)
        return gspread.authorize(creds)

    # OAuth local flow fallback
    oauth_path = Path(".secrets/credentials.json")
    if oauth_path.exists():
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        flow = InstalledAppFlow.from_client_secrets_file(str(oauth_path), scopes=scopes)
        creds = flow.run_local_server(port=0)
        client = gspread.authorize(creds)
        return client

    print(
        "No credentials found. Place a service account JSON at .secrets/service_account.json or set env GOOGLE_SERVICE_ACCOUNT_JSON=path"
    )
    print(
        "Or put OAuth client secrets at .secrets/credentials.json for an interactive flow."
    )
    sys.exit(3)


def write_sheet_from_rows(client, spreadsheet_id, rows, sheet_title="Signals"):
    sh = client.open_by_key(spreadsheet_id)
    try:
        worksheet = sh.worksheet(sheet_title)
        sh.del_worksheet(worksheet)
    except Exception:
        pass
    worksheet = sh.add_worksheet(
        title=sheet_title, rows=str(max(100, len(rows) + 5)), cols="20"
    )

    # write header and rows
    if not rows:
        print("No rows to write to", spreadsheet_id)
        return
    header = list(rows[0].keys())
    worksheet.update([header] + [[r.get(c, "") for c in header] for r in rows])

    # basic formatting: freeze header
    try:
        from gspread_formatting import (CellFormat, TextFormat,
                                        format_cell_ranges, set_frozen)

        fmt = CellFormat(textFormat=TextFormat(bold=True))
        format_cell_ranges(
            worksheet, [("A1:{}1".format(chr(65 + len(header) - 1)), fmt)]
        )
        set_frozen(worksheet, rows=1)
    except Exception:
        # gspread-formatting optional
        pass


def read_signals_csv(path):
    if not Path(path).exists():
        print("Signals CSV not found at", path)
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            out.append(r)
    return out


def main():
    ensure_packages()
    rows = read_signals_csv(SIGNALS_CSV)
    if not rows:
        print("No rows in signals.csv — nothing to push")
        return
    client = get_gspread_client()
    print("Authenticated to Google Sheets")

    for name, key in TARGET_SPREADSHEETS.items():
        print("Writing", name, key)
        try:
            write_sheet_from_rows(client, key, rows, sheet_title="Signals")
            print("Wrote", len(rows), "rows to", name)
        except Exception as e:
            print("Failed to write to", name, key, "error:", repr(e))


if __name__ == "__main__":
    main()
