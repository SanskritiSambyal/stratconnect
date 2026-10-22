"""Google Sheets storage layer for contacts and the access list.

The sheet holds two worksheets:
  - "contacts" : header row = CONTACT_COLUMNS, one row per contact
  - "access"   : header row = ["entry", "role"], where entry is a full email
                 (grants that person) or "@domain.tld" (grants everyone on that
                 institute domain), and role is viewer / editor / admin.

Concurrency note: writes update individual rows, which is fine for a club-sized
tracker (hundreds of rows, a handful of simultaneous editors).
"""
import time
import uuid

import streamlit as st

from constants import CONTACT_COLUMNS, FIELD_KEYS

ACCESS_HEADERS = ["entry", "role"]


@st.cache_resource(show_spinner=False)
def _client():
    """Authorized gspread client from the service-account secret."""
    import gspread
    from google.oauth2.service_account import Credentials

    info = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def _spreadsheet():
    gc = _client()
    ref = st.secrets["gsheets"]["spreadsheet"]
    if ref.startswith("http"):
        return gc.open_by_url(ref)
    return gc.open_by_key(ref)


def _ws(title, headers):
    """Return a worksheet, creating it (with headers) if missing."""
    ss = _spreadsheet()
    try:
        ws = ss.worksheet(title)
    except Exception:
        ws = ss.add_worksheet(title=title, rows=200, cols=max(4, len(headers)))
        ws.update(values=[headers], range_name="A1")
        return ws
    # ensure header row exists
    first = ws.row_values(1)
    if first != headers:
        ws.update(values=[headers], range_name="A1")
    return ws


def _ws_contacts():
    return _ws("contacts", CONTACT_COLUMNS)


def _ws_access():
    return _ws("access", ACCESS_HEADERS)


# --------------------------------------------------------------------- contacts
def list_contacts():
    ws = _ws_contacts()
    rows = ws.get_all_records(expected_headers=CONTACT_COLUMNS)
    out = []
    for r in rows:
        if not r.get("_id"):
            continue
        rec = {k: ("" if r.get(k) is None else str(r.get(k))) for k in CONTACT_COLUMNS}
        try:
            rec["created_at"] = int(r.get("created_at") or 0)
        except (ValueError, TypeError):
            rec["created_at"] = 0
        out.append(rec)
    out.sort(key=lambda r: r.get("created_at", 0), reverse=True)
    return out


def _row_values(rec):
    return [str(rec.get(col, "")) for col in CONTACT_COLUMNS]


def add_contact(data):
    ws = _ws_contacts()
    rec = {k: data.get(k, "") for k in FIELD_KEYS}
    rec["_id"] = uuid.uuid4().hex
    rec["created_at"] = int(time.time() * 1000)
    ws.append_row(_row_values(rec), value_input_option="USER_ENTERED")
    return rec["_id"]


def _find_row(ws, _id):
    ids = ws.col_values(1)  # includes header at index 0
    for i, v in enumerate(ids):
        if v == _id:
            return i + 1  # 1-based row number
    return None


def update_contact(_id, data, created_at=None):
    ws = _ws_contacts()
    row = _find_row(ws, _id)
    if not row:
        raise KeyError(_id)
    rec = {k: data.get(k, "") for k in FIELD_KEYS}
    rec["_id"] = _id
    rec["created_at"] = int(created_at or time.time() * 1000)
    last_col = _col_letter(len(CONTACT_COLUMNS))
    ws.update(values=[_row_values(rec)], range_name=f"A{row}:{last_col}{row}")


def delete_contact(_id):
    ws = _ws_contacts()
    row = _find_row(ws, _id)
    if row:
        ws.delete_rows(row)


def _col_letter(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ----------------------------------------------------------------------- access
def list_access():
    """Return [(entry, role), ...] from the access worksheet."""
    ws = _ws_access()
    rows = ws.get_all_records(expected_headers=ACCESS_HEADERS)
    out = []
    for r in rows:
        entry = str(r.get("entry", "")).strip().lower()
        role = str(r.get("role", "")).strip().lower()
        if entry and role:
            out.append((entry, role))
    return out


def set_access(entry, role):
    """Add or update an access entry (email or @domain)."""
    entry = entry.strip().lower()
    role = role.strip().lower()
    ws = _ws_access()
    entries = ws.col_values(1)
    for i, v in enumerate(entries):
        if i == 0:
            continue
        if v.strip().lower() == entry:
            ws.update(values=[[entry, role]], range_name=f"A{i + 1}:B{i + 1}")
            return
    ws.append_row([entry, role], value_input_option="USER_ENTERED")


def remove_access(entry):
    entry = entry.strip().lower()
    ws = _ws_access()
    entries = ws.col_values(1)
    for i, v in enumerate(entries):
        if i == 0:
            continue
        if v.strip().lower() == entry:
            ws.delete_rows(i + 1)
            return


def sheet_url():
    try:
        return _spreadsheet().url
    except Exception:
        return None
