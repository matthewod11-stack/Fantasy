"""
CSV-backed storage for metrics (with optional Google Sheets integration).

Features:
- Append new PostRecord rows to CSV
- Upsert by post_id (idempotent behavior)
- If SHEETS_ENABLED and gspread creds present, attempt to sync to a sheet.

This module is defensive: it wraps gspread imports so code runs without Google
libraries installed.
"""
from typing import List, Dict, Optional
import csv
import os
from .config import get_metrics_settings
from .schemas import PostRecord

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GS_AVAILABLE = True
except Exception:
    GS_AVAILABLE = False


SETTINGS = get_metrics_settings()
os.makedirs(SETTINGS.METRICS_DIR, exist_ok=True)


def _read_all() -> List[Dict[str, str]]:
    path = SETTINGS.CSV_PATH
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_all(rows: List[Dict[str, str]]) -> None:
    path = SETTINGS.CSV_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        # Write header only
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(PostRecord.schema().get("properties").keys())
        return
    # Use keys from first row to define header
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def upsert_post(record: PostRecord) -> None:
    """Insert or update a PostRecord by post_id in the CSV backing store."""
    rows = _read_all()
    updated = False
    # Normalize types to strings for CSV storage
    def _to_row(r: PostRecord) -> Dict[str, str]:
        d = r.dict()
        return {k: ("" if v is None else str(v)) for k, v in d.items()}

    new_row = _to_row(record)
    for i, r in enumerate(rows):
        if r.get("post_id") == record.post_id:
            rows[i] = new_row
            updated = True
            break
    if not updated:
        rows.append(new_row)

    _write_all(rows)

    # Optionally sync to Google Sheets
    if SETTINGS.SHEETS_ENABLED and GS_AVAILABLE and SETTINGS.SHEETS_SERVICE_ACCOUNT_JSON and SETTINGS.SHEETS_SPREADSHEET_ID:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(SETTINGS.SHEETS_SERVICE_ACCOUNT_JSON, ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"])
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SETTINGS.SHEETS_SPREADSHEET_ID).sheet1
            # For simplicity, overwrite sheet with CSV rows
            headers = list(rows[0].keys())
            sheet.clear()
            sheet.append_row(headers)
            for r in rows:
                sheet.append_row([r.get(h, "") for h in headers])
        except Exception:
            # Fail silently; metrics should not break the app
            pass


def read_post(post_id: str) -> Optional[PostRecord]:
    rows = _read_all()
    for r in rows:
        if r.get("post_id") == post_id:
            # Convert types loosely
            coerced = {k: _coerce_type(v) for k, v in r.items()}
            return PostRecord(**coerced)
    return None


def list_posts_by_date(date: str) -> List[PostRecord]:
    rows = _read_all()
    out = []
    for r in rows:
        if r.get("date") == date:
            out.append(PostRecord(**{k: _coerce_type(v) for k, v in r.items()}))
    return out


def _coerce_type(val: Optional[str]):
    if val is None or val == "":
        return None
    # Try int
    try:
        if val.isdigit():
            return int(val)
    except Exception:
        pass
    # Try float
    try:
        return float(val)
    except Exception:
        return val
