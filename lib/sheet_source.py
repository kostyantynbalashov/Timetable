"""Reads tabular data either from a local .xlsx (for testing / offline use)
or from a Google Sheet via a service account (for GitHub Actions).

Returns the same shape either way: dict[sheet_name] -> list[dict[header] -> value].
Header row defines the dict keys (lower-cased, stripped).
"""
from __future__ import annotations

import os


def _normalize_header(h) -> str:
    return str(h or "").strip().lower()


def load_from_xlsx(path: str, sheet_names: list[str]) -> dict[str, list[dict]]:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    out: dict[str, list[dict]] = {}
    for name in sheet_names:
        if name not in wb.sheetnames:
            out[name] = []
            continue
        rows = wb[name].iter_rows(values_only=True)
        try:
            header = [_normalize_header(c) for c in next(rows)]
        except StopIteration:
            out[name] = []
            continue
        records = []
        for r in rows:
            rec = {header[i]: r[i] for i in range(min(len(header), len(r)))}
            if any(v not in (None, "") for v in rec.values()):
                records.append(rec)
        out[name] = records
    return out


def load_from_google_sheet(
    sheet_id: str, sheet_names: list[str], credentials_json: str
) -> dict[str, list[dict]]:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        __import__("json").loads(credentials_json), scopes=scopes
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(sheet_id)

    out: dict[str, list[dict]] = {}
    for name in sheet_names:
        try:
            ws = sh.worksheet(name)
        except gspread.WorksheetNotFound:
            out[name] = []
            continue
        values = ws.get_all_values()
        if not values:
            out[name] = []
            continue
        header = [_normalize_header(c) for c in values[0]]
        records = []
        for row in values[1:]:
            rec = {header[i]: row[i] for i in range(min(len(header), len(row)))}
            if any(v.strip() for v in rec.values()):
                records.append(rec)
        out[name] = records
    return out


def write_private_sheet(sheet_id: str, sheet_name: str, rows: list[list], credentials_json: str) -> None:
    """Overwrites `sheet_name` tab (creating it if missing) with `rows`
    (first row = header). Used for the workload results, which never go
    into the public site/data.js."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        __import__("json").loads(credentials_json), scopes=scopes
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=max(len(rows), 10), cols=max((len(r) for r in rows), default=10))
    ws.update(rows, "A1")


SHEETS = ["Налаштування", "Викладачі", "Аудиторії", "Групи", "Дисципліни", "Заняття"]


def load_source() -> dict[str, list[dict]]:
    """Picks Google Sheets if GOOGLE_SHEET_ID + GOOGLE_SERVICE_ACCOUNT_JSON
    env vars are set (GitHub Actions), else falls back to a local .xlsx
    (DATA_XLSX env var, default data_samples/sample.xlsx) for local testing."""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sheet_id and creds_json:
        return load_from_google_sheet(sheet_id, SHEETS, creds_json)
    path = os.environ.get("DATA_XLSX", "data_samples/sample.xlsx")
    return load_from_xlsx(path, SHEETS)
