#!/usr/bin/env python3
"""
Bridge POS bills -> Tally-format GST inputs -> TallyToOutputsForGST outputs.

Reads the monthly bill registers written by the local seller server
(`data/bills/YYYY-MM.csv`), splits them per billing organisation, and emits the
two files the `TallyToOutputsForGST` converter expects:

    <tally_repo>/data/<org>/<PREFIX>-DayBook.xlsx          2 title rows + header
    <tally_repo>/data/<org>/HSN files/HSNCodeSummary.xlsx  3 title rows + header

It then runs `TallyToOutputsForGST/process_data.py`, which produces the
gst.gov.in JSON uploads and the consolidated Excel reports under
`<tally_repo>/output/<org>/`.

Column layout matches what `CreateJsonFilefromTallyOutputFile.py` looks for:
`Date`, `Particulars`, `Vch No.`, `Sales Tax No.`, `Gross Total`,
`Round Up Sale`, plus one `Sale Net <rate>% A/c.` / `CGST <half>% Received` /
`SGST <half>% Received` / `IGST <rate>% Received` group per distinct tax rate.
The converter locates the header row itself, so the title rows above it are safe
to write.

Usage:
    python3 src/seller/prepare_tally_files.py                 # current month
    python3 src/seller/prepare_tally_files.py --month 2026-09
    python3 src/seller/prepare_tally_files.py --all
    python3 src/seller/prepare_tally_files.py --no-run        # files only
    python3 src/seller/prepare_tally_files.py --tally-repo /path/to/TallyToOutputsForGST

Estimates live in `data/estimates/` and are never included: they are not a
taxable supply until the merchant confirms pricing.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BILLS_DIR = ROOT / "data" / "bills"
CONFIG_FILE = ROOT / "data" / "config.json"

FALLBACK_ORGS = {
    "skumar": {
        "id": "skumar",
        "prefix": "S",
        "name": "S. Kumar & Bros",
        "gstin": "27AAGPP1621C1Z5",
    },
    "gsc": {
        "id": "gsc",
        "prefix": "G",
        "name": "General Supply Corporation",
        "gstin": "27ACJPP2955J1Z4",
    },
}

# Catalog units -> GST-standardised Unique Quantity Codes.
UQC_MAP = {
    "mtr": "MTR", "mtrs": "MTR", "metre": "MTR", "metres": "MTR",
    "meter": "MTR", "meters": "MTR",
    "pcs": "NOS", "pc": "NOS", "piece": "NOS", "pieces": "NOS", "nos": "NOS",
    "kg": "KGS", "kgs": "KGS", "kilogram": "KGS", "kilograms": "KGS",
    "box": "BOX", "boxes": "BOX",
    "set": "SET", "sets": "SET",
    "coil": "NOS", "rolls": "NOS", "roll": "NOS",
    "ltr": "LTR", "litre": "LTR", "litres": "LTR", "liter": "LTR",
    "dozen": "DOZ", "dozens": "DOZ",
    "pack": "PACK", "packs": "PACK",
}

DAYBOOK_TITLE_ROWS = 2   # rows written above the header row
HSN_TITLE_ROWS = 3       # rows above the header row (the reader uses header=3)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
def load_orgs() -> dict:
    """Organisation metadata, taken from data/config.json when available."""
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(FALLBACK_ORGS)

    orgs = {}
    for entry in config.get("organizations", []):
        org_id = str(entry.get("id", "")).strip()
        if not org_id:
            continue
        orgs[org_id] = {
            "id": org_id,
            "prefix": str(entry.get("prefix") or "S").strip(),
            "name": entry.get("name") or org_id,
            "gstin": entry.get("gstin") or "",
        }
    return orgs or dict(FALLBACK_ORGS)


def resolve_tally_repo(explicit=None) -> Path:
    """Locate the TallyToOutputsForGST checkout.

    An explicitly requested path (argument or TALLY_REPO) must be correct --
    we never silently fall back to a different checkout than the caller named.
    """
    for label, requested in (
        ("--tally-repo", explicit),
        ("TALLY_REPO", os.environ.get("TALLY_REPO")),
    ):
        if not requested:
            continue
        candidate = Path(requested).expanduser()
        if (candidate / "process_data.py").is_file():
            return candidate.resolve()
        raise FileNotFoundError(
            f"{label} points at {candidate}, but process_data.py was not found there."
        )

    for candidate in (ROOT.parent / "TallyToOutputsForGST", ROOT / "TallyToOutputsForGST"):
        if (candidate / "process_data.py").is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not find the TallyToOutputsForGST checkout (process_data.py).\n"
        f"Searched:\n  - {ROOT.parent / 'TallyToOutputsForGST'}\n"
        f"  - {ROOT / 'TallyToOutputsForGST'}\n"
        "Pass --tally-repo /path/to/TallyToOutputsForGST or set TALLY_REPO."
    )


def available_months() -> list:
    if not BILLS_DIR.is_dir():
        return []
    pattern = re.compile(r"\d{4}-\d{2}")
    return sorted(p.stem for p in BILLS_DIR.glob("*.csv") if pattern.fullmatch(p.stem))


# ---------------------------------------------------------------------------
# Reading POS bills
# ---------------------------------------------------------------------------
def _parse_date(raw):
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = dt.datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.date()


def read_bills(months: list) -> list:
    """Flatten the monthly bill registers into (month, order) pairs."""
    orders = []
    for month in months:
        path = BILLS_DIR / f"{month}.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                raw = (row.get("order_json") or "").strip()
                if not raw:
                    continue
                try:
                    order = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                # Older registers carried the org only as a CSV column.
                order.setdefault("org", row.get("org") or "skumar")
                order.setdefault("order_reference", row.get("id") or "")
                order.setdefault("created_at", row.get("createdAt") or "")
                orders.append((month, order))
    return orders


def _amounts(order: dict) -> dict:
    return order.get("amounts") or order.get("totals") or {}


def _bill_rate(amounts: dict):
    """Combined GST rate applied to the bill (9% CGST + 9% SGST → 18).

    Tries explicit rate fields first (set by older code paths), then falls back
    to deriving the rate from grandTotal vs subTotal when those are absent (the
    standard output of the POS cart which only stores subTotal + grandTotal).
    """
    try:
        cgst = float(amounts.get("cgst_rate", 0) or 0)
        sgst = float(amounts.get("sgst_rate", 0) or 0)
        rate = round(cgst + sgst, 4)
        if rate > 0:
            return rate
        # Fallback: derive from grand total − sub total
        sub   = float(amounts.get("subTotal",    amounts.get("taxable_subtotal", 0)) or 0)
        grand = float(amounts.get("grandTotal",  amounts.get("estimated_total",  0)) or 0)
        if sub > 0 and grand > sub:
            derived = round((grand - sub) / sub * 100, 4)
            return derived if derived > 0 else None
        return None
    except (TypeError, ValueError):
        return None


def _default_rate(orders: list, which: str) -> float:
    """Typical CGST/SGST rate for the HSN tax columns (defaults to 9%)."""
    for order in orders:
        value = _amounts(order).get(f"{which}_rate")
        if value:
            try:
                rate = float(value)
            except (TypeError, ValueError):
                continue
            if rate > 0:
                return rate
    return 9.0


def _rate_label(rate: float) -> str:
    return f"{rate:g}"


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------
def daybook_columns(rates: list) -> list:
    columns = [
        "Date",
        "Particulars",
        "Vch No.",
        "Sales Tax No.",
        "Gross Total",
        "Round Up Sale",
    ]
    for rate in sorted(rates):
        columns.extend(
            [
                f"Sale Net {_rate_label(rate)}% A/c.",
                f"CGST {_rate_label(rate / 2)}% Received",
                f"SGST {_rate_label(rate / 2)}% Received",
                f"IGST {_rate_label(rate)}% Received",
            ]
        )
    return columns


def build_daybook_rows(orders: list, org_id: str):
    """Return (rows, rates, stats) for one organisation's DayBook."""
    rows, rates_used = [], set()
    stats = {"bills": 0, "rows": 0, "with_gstin": 0, "without_gstin": 0, "skipped": {}}

    def skip(reason):
        stats["skipped"][reason] = stats["skipped"].get(reason, 0) + 1

    for order in orders:
        if order.get("isEstimate"):
            skip("estimates")
            continue

        amounts = _amounts(order)
        rate = _bill_rate(amounts)
        if rate is None:
            skip("no_tax_rate")
            continue

        date = _parse_date(order.get("created_at") or order.get("createdAt"))
        if date is None:
            skip("bad_date")
            continue

        taxable = float(amounts.get("taxable_subtotal", amounts.get("subTotal", 0)) or 0)
        cgst = float(amounts.get("cgst_amount", 0) or 0)
        sgst = float(amounts.get("sgst_amount", 0) or 0)
        gross = float(amounts.get("estimated_total", amounts.get("grandTotal", 0)) or 0)
        if taxable <= 0:
            skip("nothing_taxable")
            continue

        customer = order.get("customer") or order.get("buyer") or {}
        gstin = str(customer.get("gstin") or "").strip().upper()
        reference = str(order.get("order_reference") or order.get("id") or "").strip()

        stats["bills"] += 1
        stats["rows"] += 1
        if gstin:
            stats["with_gstin"] += 1
        else:
            stats["without_gstin"] += 1
        rates_used.add(rate)

        row = {
            "Date": date,
            "Particulars": str(customer.get("name") or "Cash Customer"),
            "Vch No.": reference,
            "Sales Tax No.": gstin,
            "Gross Total": round(gross, 2),
            "Round Up Sale": round(gross - (taxable + cgst + sgst), 2),
        }
        # One tax rate per POS bill: place the amounts in that rate's columns.
        row[f"Sale Net {_rate_label(rate)}% A/c."] = round(taxable, 2)
        row[f"CGST {_rate_label(rate / 2)}% Received"] = round(cgst, 2)
        row[f"SGST {_rate_label(rate / 2)}% Received"] = round(sgst, 2)
        row[f"IGST {_rate_label(rate)}% Received"] = 0
        rows.append(row)

    _ = org_id
    return rows, sorted(rates_used), stats


def to_uqc(unit):
    raw = str(unit or "").strip()
    if not raw:
        return None
    key = re.sub(r"[\d\s]+", "", raw).strip(".").lower()
    return UQC_MAP.get(key, raw.upper())


HSN_COLUMNS = [
    "HSN/SAC", "Description", "UQC", "Total Quantity", "Total Value", "Rate",
    "Taxable Value", "Integrated Tax Amount", "Central Tax Amount",
    "State/UT Tax Amount", "Cess Amount",
]

_HSN_NUMERIC = [
    "Total Quantity", "Total Value", "Rate", "Taxable Value",
    "Integrated Tax Amount", "Central Tax Amount", "State/UT Tax Amount",
]


def build_hsn_rows(orders: list, cgst_rate: float, sgst_rate: float):
    """Consolidate per-item HSN lines for one organisation."""
    grouped: dict = {}
    stats = {"lines": 0, "skipped_no_hsn": 0, "skipped_no_taxable": 0}

    for order in orders:
        if order.get("isEstimate"):
            continue
        for item in order.get("items") or []:
            hsn = str(item.get("hsn") or "").strip()
            if not hsn:
                stats["skipped_no_hsn"] += 1
                continue

            taxable = item.get("taxable_amount")
            if taxable in (None, ""):
                stats["skipped_no_taxable"] += 1
                continue
            taxable = float(taxable)
            if taxable <= 0:
                stats["skipped_no_taxable"] += 1
                continue

            spec = item.get("specification") or {}
            entry = grouped.setdefault(hsn, {column: 0 for column in HSN_COLUMNS})
            entry["HSN/SAC"] = hsn
            entry["Description"] = str(item.get("name") or "").strip()
            if not entry["UQC"]:
                entry["UQC"] = to_uqc(spec.get("unit"))

            entry["Total Quantity"] += float(item.get("quantity") or 0)
            entry["Total Value"] += float(item.get("gross_amount") or taxable)
            entry["Rate"] = max(entry["Rate"], float(item.get("unit_price") or 0))
            entry["Taxable Value"] += taxable
            entry["Central Tax Amount"] += round(taxable * cgst_rate / 100, 2)
            entry["State/UT Tax Amount"] += round(taxable * sgst_rate / 100, 2)
            stats["lines"] += 1

    rows = []
    for hsn in sorted(grouped):
        entry = grouped[hsn]
        entry["UQC"] = entry["UQC"] or ""
        for key in _HSN_NUMERIC:
            entry[key] = round(float(entry[key]), 2)
        rows.append(entry)
    return rows, stats


# ---------------------------------------------------------------------------
# Excel writers
# ---------------------------------------------------------------------------
def _write_excel(path: Path, title_rows: list, columns: list, rows: list, sheet_name: str):
    """Write `title_rows` + the header row + `rows`, with no pandas header."""
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    body = pd.DataFrame(
        [{column: row.get(column, 0) for column in columns} for row in rows],
        columns=columns,
    )
    preamble = pd.DataFrame(list(title_rows) + [columns], columns=columns)
    payload = pd.concat([preamble, body], ignore_index=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        payload.to_excel(writer, sheet_name=sheet_name, index=False, header=False)


def write_daybook(path: Path, org: dict, rows: list, rates: list, period: str):
    columns = daybook_columns(rates)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    titles = [
        [f"Day Book - {org['name']} ({org.get('gstin') or 'no GSTIN'}) | {period}"]
        + [""] * (len(columns) - 1),
        [f"Generated from SKumarDirectory POS {stamp}"] + [""] * (len(columns) - 1),
    ][:DAYBOOK_TITLE_ROWS]
    _write_excel(path, titles, columns, rows, sheet_name="Sales Register")
    return columns


def write_hsn(path: Path, org: dict, rows: list, period: str):
    columns = HSN_COLUMNS
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    titles = [
        [f"HSN Summary - {org['name']} ({org.get('gstin') or 'no GSTIN'}) | {period}"]
        + [""] * (len(columns) - 1),
        [""] * len(columns),
        [f"Generated from SKumarDirectory POS {stamp}"] + [""] * (len(columns) - 1),
    ][:HSN_TITLE_ROWS]
    _write_excel(path, titles, columns, rows, sheet_name="HSN Summary")
    return columns


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _run_converter(repo: Path) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "process_data.py"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"ran": False, "returncode": -1, "output": str(error)}

    output = (proc.stdout or "") + (proc.stderr or "")
    return {"ran": True, "returncode": proc.returncode, "output": output}


def prepare(months: list, tally_repo=None, run_converter: bool = True) -> dict:
    """Build the per-org Tally inputs and (optionally) run process_data.py."""
    orgs = load_orgs()
    orders = read_bills(months)
    period = "all" if len(months) != 1 else months[0]

    result = {
        "ok": False,
        "period": period,
        "months": months,
        "tally_repo": "",
        "orgs": {},
        "converter": None,
        "errors": [],
    }

    if not months:
        result["errors"].append(
            f"No monthly bill registers found in {BILLS_DIR}. Save a bill from the POS first."
        )
        return result
    if not orders:
        result["errors"].append(f"No bills recorded for {period}.")
        return result

    try:
        repo = resolve_tally_repo(tally_repo)
    except FileNotFoundError as error:
        result["errors"].append(str(error))
        return result

    result["tally_repo"] = str(repo)

    # Group bill orders per organisation, preserving register order.
    by_org: dict = defaultdict(list)
    for _month, order in orders:
        org_id = order.get("org") or "skumar"
        if org_id not in orgs:
            org_id = next(iter(orgs))
        by_org[org_id].append(order)

    for org_id, org in orgs.items():
        org_orders = by_org.get(org_id, [])
        prefix = org.get("prefix", "S")

        daybook_path = repo / "data" / org_id / f"{prefix}-DayBook.xlsx"
        hsn_path = repo / "data" / org_id / "HSN files" / "HSNCodeSummary.xlsx"

        daybook_rows, rates, daybook_stats = build_daybook_rows(org_orders, org_id)
        hsn_rows, hsn_stats = build_hsn_rows(
            org_orders,
            cgst_rate=_default_rate(org_orders, "cgst"),
            sgst_rate=_default_rate(org_orders, "sgst"),
        )

        entry = {
            "name": org.get("name"),
            "gstin": org.get("gstin"),
            "orders_read": len(org_orders),
            "daybook": str(daybook_path),
            "daybook_written": bool(daybook_rows),
            "daybook_rows": len(daybook_rows),
            "bills": daybook_stats["bills"],
            "with_gstin": daybook_stats["with_gstin"],
            "without_gstin": daybook_stats["without_gstin"],
            "skipped": daybook_stats["skipped"],
            "rates": rates,
            "hsn": {**hsn_stats, "path": str(hsn_path), "written": bool(hsn_rows)},
            "hsn_rows": len(hsn_rows),
        }

        if daybook_rows:
            write_daybook(daybook_path, org, daybook_rows, rates, period)
        if hsn_rows:
            write_hsn(hsn_path, org, hsn_rows, period)

        result["orgs"][org_id] = entry

    if run_converter:
        result["converter"] = _run_converter(repo)
        if result["converter"]["returncode"] != 0:
            result["errors"].append(
                f"process_data.py exited with code {result['converter']['returncode']}."
            )

    result["ok"] = not result["errors"]
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Tally/GST inputs from POS bills.")
    parser.add_argument("--month", help="Bill register to export, as YYYY-MM (default: current month).")
    parser.add_argument("--all", action="store_true", help="Export every available month.")
    parser.add_argument("--tally-repo", help="Path to the TallyToOutputsForGST checkout.")
    parser.add_argument("--no-run", action="store_true",
                        help="Write the Excel files but do not run process_data.py.")
    parser.add_argument("--json", action="store_true", help="Print only the machine-readable summary.")
    args = parser.parse_args(argv)

    if args.all:
        months = available_months()
    else:
        months = [args.month] if args.month else [dt.date.today().strftime("%Y-%m")]

    result = prepare(months, tally_repo=args.tally_repo, run_converter=not args.no_run)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1

    print("=" * 70)
    print("  POS -> TALLY / GST PREPARATION")
    print("=" * 70)
    print(f"Period: {result['period']}")
    if result["tally_repo"]:
        print(f"Tally repo: {result['tally_repo']}")

    for org_id, entry in result["orgs"].items():
        print(f"\n[{entry['name']}] ({org_id} | {entry['gstin']})")
        print(f"   Orders read       : {entry['orders_read']}")
        print(f"   DayBook rows      : {entry['daybook_rows']}  rates={entry['rates']}")
        print(f"   DayBook file      : {entry['daybook'] if entry['daybook_written'] else '(no taxable rows)'}")
        print(f"   HSN rows          : {entry['hsn_rows']}")
        print(f"   HSN file          : {entry['hsn']['path'] if entry['hsn']['written'] else '(no HSN lines)'}")
        if entry.get("without_gstin"):
            print(f"   NOTE: {entry['without_gstin']} bill(s) have no buyer GSTIN and will be")
            print("         skipped by the converter (B2C sales are not B2B invoices).")
        if entry.get("skipped"):
            print(f"   Skipped           : {entry['skipped']}")

    if result["converter"] is not None:
        print(f"\nprocess_data.py exit code: {result['converter']['returncode']}")
        if result["converter"]["output"]:
            print("-" * 70)
            print(result["converter"]["output"].rstrip())

    for error in result["errors"]:
        print(f"\n[ERROR] {error}")
    print("=" * 70)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
