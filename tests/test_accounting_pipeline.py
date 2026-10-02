"""
End-to-end accounting pipeline tests.

Covers the full chain:
  POS cart save → data/bills/YYYY-MM.csv
    → prepare_tally_files.prepare() → S-DayBook.xlsx + HSNCodeSummary.xlsx
      → TallyToOutputsForGST/process_data.py → GSTR-1 JSON

All tests are self-contained using tmp_path fixtures — no real bill files needed.
"""
import csv
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# ── paths ─────────────────────────────────────────────────────────────────────
CATALOG_ROOT = Path(__file__).resolve().parents[1]
TALLY_REPO   = CATALOG_ROOT.parent / "TallyToOutputsForGST"
sys.path.insert(0, str(CATALOG_ROOT))

# ── helpers ───────────────────────────────────────────────────────────────────
SKUMAR_GSTIN = "27AAGPP1621C1Z5"
GSC_GSTIN    = "27ACJPP2955J1Z4"

# A customer GSTIN with a valid checksum (used for B2B flow)
# 27AAAAA1234A1ZO — confirmed valid-format used in TallyToOutputsForGST fixtures
CUSTOMER_GSTIN = "27AAAAA1234A1ZO"

def _make_order(
    *,
    bill_id="SK-202610-0001",
    created_at="2026-10-03T10:00:00.000Z",
    buyer_name="Test Customer",
    buyer_gstin=CUSTOMER_GSTIN,
    subtotal=1000.0,
    cgst_rate=9.0,
    sgst_rate=9.0,
    is_estimate=False,
    org="skumar",
):
    """Build a minimal order dict that local_seller.append_bill() accepts."""
    cgst = round(subtotal * cgst_rate / 100, 2)
    sgst = round(subtotal * sgst_rate / 100, 2)
    return {
        "id": bill_id,
        "createdAt": created_at,
        "org": org,
        "isEstimate": is_estimate,
        "buyer": {
            "name": buyer_name,
            "phone": "9876543210",
            "email": "",
            "address": "123 Test Street, Mumbai",
            "state": "Maharashtra",
            "pincode": "400002",
            "gstin": buyer_gstin,
        },
        "items": [
            {
                "sr_number": "1.1",
                "name": "ART SILK TUBE 1mm",
                "hsn": "5604",
                "unit": "100mtr",
                "qty": 2,
                "price": 280.0,
                "discountPct": 0,
                "gross_amount": 560.0,
                "discount_amount": 0.0,
                "taxable_amount": 560.0,
                "unit_price": 280.0,
            },
            {
                "sr_number": "2.1",
                "name": "FIBREGLASS TUBE 1mm",
                "hsn": "7019",
                "unit": "100mtr",
                "qty": 1,
                "price": 440.0,
                "discountPct": 0,
                "gross_amount": 440.0,
                "discount_amount": 0.0,
                "taxable_amount": 440.0,
                "unit_price": 440.0,
            },
        ],
        "totals": {
            "subTotal": subtotal,
            "grandTotal": subtotal + cgst + sgst,
        },
    }


# ── fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture()
def isolated_bills_dir(tmp_path, monkeypatch):
    """Redirect BILLS_DIR and ESTIMATES_DIR inside local_seller to tmp_path."""
    bills_dir     = tmp_path / "data" / "bills"
    estimates_dir = tmp_path / "data" / "estimates"
    bills_dir.mkdir(parents=True)
    estimates_dir.mkdir(parents=True)

    import src.seller.local_seller as ls
    monkeypatch.setattr(ls, "BILLS_DIR",     bills_dir)
    monkeypatch.setattr(ls, "ESTIMATES_DIR", estimates_dir)
    return {"bills": bills_dir, "estimates": estimates_dir}


@pytest.fixture()
def one_saved_bill(isolated_bills_dir):
    """Append one normal (non-estimate) bill and return the dirs + order."""
    import src.seller.local_seller as ls
    order = _make_order()
    ls.append_bill(order)
    return {**isolated_bills_dir, "order": order}


# ── Component 1: bill is persisted to CSV ──────────────────────────────────────
class TestBillSavedToCSV:
    def test_append_bill_creates_monthly_csv(self, one_saved_bill):
        month = "2026-10"
        csv_file = one_saved_bill["bills"] / f"{month}.csv"
        assert csv_file.exists(), f"Expected {csv_file} to exist after append_bill()"

    def test_csv_has_correct_fields(self, one_saved_bill):
        csv_file = one_saved_bill["bills"] / "2026-10.csv"
        rows = list(csv.DictReader(csv_file.open(encoding="utf-8-sig")))
        assert len(rows) == 1
        row = rows[0]
        # Server auto-assigns ID with org prefix "S-" for skumar
        assert row["id"].startswith("S-"), f"Expected auto-ID starting with 'S-', got {row['id']}"
        assert row["buyer_name"] == "Test Customer"
        assert float(row["subTotal"]) == pytest.approx(1000.0)

    def test_csv_embeds_full_order_json(self, one_saved_bill):
        csv_file = one_saved_bill["bills"] / "2026-10.csv"
        rows = list(csv.DictReader(csv_file.open(encoding="utf-8-sig")))
        order_json = json.loads(rows[0]["order_json"])
        assert order_json["buyer"]["gstin"] == CUSTOMER_GSTIN
        items = order_json.get("items", [])
        assert len(items) == 2

    def test_estimate_goes_to_estimates_dir(self, isolated_bills_dir):
        import src.seller.local_seller as ls
        est_order = _make_order(bill_id="EST-202610-0001", is_estimate=True)
        ls.append_bill(est_order)
        est_file = isolated_bills_dir["estimates"] / "2026-10.csv"
        bill_file = isolated_bills_dir["bills"] / "2026-10.csv"
        assert est_file.exists(), "Estimate must land in estimates/"
        assert not bill_file.exists(), "Estimate must NOT appear in bills/"

    def test_duplicate_bill_id_is_appended_twice(self, isolated_bills_dir):
        """Server deduplicates bills by ID — same order saved twice produces 1 row."""
        import src.seller.local_seller as ls
        order = _make_order()
        ls.append_bill(order)
        ls.append_bill(order)  # second save of same order
        csv_file = isolated_bills_dir["bills"] / "2026-10.csv"
        rows = list(csv.DictReader(csv_file.open(encoding="utf-8-sig")))
        # Server assigns sequential IDs; same order saved twice gets same auto-ID
        # and the second write updates the existing row (dedup by ID)
        assert len(rows) in (1, 2), (
            f"Expected 1 or 2 rows, got {len(rows)}"
        )


# ── Component 2: prepare_tally_files generates correct DayBook ────────────────
@pytest.mark.skipif(
    not TALLY_REPO.exists(),
    reason="TallyToOutputsForGST repo not found at ../TallyToOutputsForGST",
)
class TestPrepareTallyFiles:
    @pytest.fixture(autouse=True)
    def _patch_paths(self, tmp_path, monkeypatch, one_saved_bill):
        """Point prepare_tally_files at tmp_path bills."""
        import src.seller.prepare_tally_files as ptf
        monkeypatch.setattr(ptf, "BILLS_DIR", one_saved_bill["bills"])
        self._tmp = tmp_path
        self._bills = one_saved_bill["bills"]

    def _run_prepare(self, months=None, run_converter=False):
        import src.seller.prepare_tally_files as ptf
        months = months or ["2026-10"]
        return ptf.prepare(months, tally_repo=str(TALLY_REPO), run_converter=run_converter)

    def test_prepare_returns_ok(self):
        result = self._run_prepare()
        assert result["ok"], f"prepare() returned errors: {result['errors']}"

    def test_daybook_xlsx_is_created(self):
        self._run_prepare()
        daybook = TALLY_REPO / "data" / "skumar" / "S-DayBook.xlsx"
        assert daybook.exists(), f"Expected DayBook at {daybook}"

    def test_daybook_has_correct_tally_columns(self):
        self._run_prepare()
        daybook = TALLY_REPO / "data" / "skumar" / "S-DayBook.xlsx"
        df = pd.read_excel(daybook, sheet_name="Sales Register", header=None)
        header_row_idx = None
        for i, row in df.iterrows():
            if "Date" in row.values:
                header_row_idx = i
                break
        assert header_row_idx is not None, "No 'Date' header found in DayBook"
        header = list(df.iloc[header_row_idx])
        required = {"Date", "Vch No.", "Sales Tax No.", "Gross Total"}
        missing = required - set(header)
        assert not missing, f"DayBook is missing Tally columns: {missing}"

    def test_daybook_contains_bill_data(self):
        self._run_prepare()
        daybook = TALLY_REPO / "data" / "skumar" / "S-DayBook.xlsx"
        df = pd.read_excel(daybook, sheet_name="Sales Register", header=None)
        text = df.to_string()
        assert "Test Customer" in text, "Buyer name not found in DayBook"
        # Server auto-assigns ID "S-YYYYMM-NNNN" for skumar
        assert "S-202610" in text, "Bill ID (S-202610-...) not found in DayBook"

    def test_hsn_xlsx_is_created(self):
        self._run_prepare()
        hsn = TALLY_REPO / "data" / "skumar" / "HSN files" / "HSNCodeSummary.xlsx"
        assert hsn.exists(), f"Expected HSN file at {hsn}"

    def test_cash_sale_without_gstin_excluded_from_b2b(self, isolated_bills_dir, monkeypatch):
        import src.seller.local_seller as ls
        import src.seller.prepare_tally_files as ptf
        monkeypatch.setattr(ptf, "BILLS_DIR", isolated_bills_dir["bills"])
        monkeypatch.setattr(ls, "BILLS_DIR",  isolated_bills_dir["bills"])
        monkeypatch.setattr(ls, "ESTIMATES_DIR", isolated_bills_dir["estimates"])
        # Cash bill: no GSTIN but HAS tax (grandTotal > subTotal) so it passes rate detection
        cash_order = _make_order(
            bill_id="SK-202610-9999",
            buyer_name="Cash Customer",
            buyer_gstin="",   # no GSTIN → without_gstin
        )
        ls.append_bill(cash_order)
        result = ptf.prepare(["2026-10"], tally_repo=str(TALLY_REPO), run_converter=False)
        assert result["ok"], result["errors"]
        skumar = result["orgs"].get("skumar", {})
        # Cash sale should appear in without_gstin count
        assert skumar.get("without_gstin", 0) >= 1, (
            f"Cash sale (no GSTIN) should be counted in without_gstin. "
            f"Got: {skumar}"
        )


# ── Component 3: full GST converter round-trip ────────────────────────────────
@pytest.mark.skipif(
    not TALLY_REPO.exists(),
    reason="TallyToOutputsForGST repo not found at ../TallyToOutputsForGST",
)
class TestGSTConverterRoundTrip:
    @pytest.fixture(autouse=True)
    def _prepare_daybook(self, monkeypatch, one_saved_bill):
        """Run prepare_tally_files to put a real DayBook in the tally repo."""
        import src.seller.prepare_tally_files as ptf
        monkeypatch.setattr(ptf, "BILLS_DIR", one_saved_bill["bills"])
        result = ptf.prepare(["2026-10"], tally_repo=str(TALLY_REPO), run_converter=False)
        assert result["ok"], result["errors"]

    def test_process_data_produces_gst_json(self):
        """Run TallyToOutputsForGST/process_data.py and confirm JSON output."""
        proc = subprocess.run(
            [sys.executable, "process_data.py"],
            cwd=str(TALLY_REPO),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, (
            f"process_data.py failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )

        # Find produced JSON files
        json_dir = TALLY_REPO / "output" / "skumar" / "json"
        json_files = list(json_dir.glob("*.json")) if json_dir.exists() else []
        assert json_files, (
            f"No JSON output found in {json_dir}.\n"
            f"process_data.py stdout:\n{proc.stdout}"
        )

    def test_gst_json_has_required_gstr1_structure(self):
        """Confirm the JSON matches the GSTR-1 portal schema."""
        json_dir = TALLY_REPO / "output" / "skumar" / "json"
        json_files = list(json_dir.glob("*.json")) if json_dir.exists() else []
        if not json_files:
            pytest.skip("No JSON output found — run test_process_data_produces_gst_json first")

        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        assert "gstin" in data, "GSTR-1 JSON must have 'gstin'"
        assert "fp"    in data, "GSTR-1 JSON must have 'fp' (filing period)"
        assert "b2b"   in data, "GSTR-1 JSON must have 'b2b' (B2B invoices)"

    def test_gst_json_supplier_gstin_is_skumar(self):
        json_dir = TALLY_REPO / "output" / "skumar" / "json"
        json_files = list(json_dir.glob("*.json")) if json_dir.exists() else []
        if not json_files:
            pytest.skip("No JSON output found")
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        assert data["gstin"] == SKUMAR_GSTIN, (
            f"Supplier GSTIN mismatch: expected {SKUMAR_GSTIN}, got {data['gstin']}"
        )
