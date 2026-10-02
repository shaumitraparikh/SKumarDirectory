"""Tests for the POS bill -> Tally DayBook/HSN -> GST converter bridge."""

import csv as csv_module
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_tool(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seller = load_tool("local_seller_tool", "src/seller/local_seller.py")
prepare = load_tool("prepare_tally_files_tool", "src/seller/prepare_tally_files.py")

# Mirrors the column patterns in TallyToOutputsForGST/src/CreateJsonFilefromTallyOutputFile.py.
TAXABLE_COL_RE = re.compile(r"Sale.*?(\d+(?:\.\d+)?)\s*%", re.I)
CGST_COL_RE = re.compile(r"CGST.*?(\d+(?:\.\d+)?)\s*%", re.I)
SGST_COL_RE = re.compile(r"SGST.*?(\d+(?:\.\d+)?)\s*%", re.I)
IGST_COL_RE = re.compile(r"IGST.*?(\d+(?:\.\d+)?)\s*%", re.I)


def parse_rate_columns(columns):
    """Replicates the converter's own rate-column detection."""
    rates = {}
    for column in columns:
        text = str(column).strip()
        if match := TAXABLE_COL_RE.search(text):
            rates.setdefault(float(match.group(1)), {})["taxable"] = column
        elif match := CGST_COL_RE.search(text):
            rates.setdefault(float(match.group(1)) * 2, {})["cgst"] = column
        elif match := SGST_COL_RE.search(text):
            rates.setdefault(float(match.group(1)) * 2, {})["sgst"] = column
        elif match := IGST_COL_RE.search(text):
            rates.setdefault(float(match.group(1)), {})["igst"] = column
    return rates


def make_order(reference, org="skumar", *, gstin="27AAGPP1621C1Z5",
               taxable=1672.0, cgst_rate=9.0, sgst_rate=9.0, items=None,
               is_estimate=False, created_at="2026-10-01T11:30:00.000Z"):
    """Build an order matching CommerceCore.createOrder's output shape."""
    cgst = round(taxable * cgst_rate / 100, 2)
    sgst = round(taxable * sgst_rate / 100, 2)
    estimated = round(taxable + cgst + sgst, 2)
    if items is None:
        items = [{
            "sku": "1.1",
            "name": "ART SILK TUBE",
            "hsn": "85469090",
            "specification": {"unit": "100mtr."},
            "quantity": 2,
            "unit_price": 836.0,
            "discount_percent": 0,
            "gross_amount": taxable,
            "discount_amount": 0,
            "taxable_amount": taxable,
            "price_status": "catalog_estimate",
        }]
    return {
        "schema_version": 1,
        "order_reference": reference,
        "created_at": created_at,
        "source": "skumar_catalog",
        "currency": "INR",
        "status": "awaiting_merchant_confirmation",
        "payment": {"status": "not_started", "provider": "not_configured"},
        "customer": {
            "name": "Shaumitra Traders",
            "phone": "919821361314",
            "address": "11 Kalbadevi Road, Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "gstin": gstin,
        },
        "items": items,
        "amounts": {
            "items_subtotal": taxable,
            "item_discounts": 0,
            "taxable_subtotal": taxable,
            "cgst_rate": cgst_rate,
            "cgst_amount": cgst,
            "sgst_rate": sgst_rate,
            "sgst_amount": sgst,
            "total_tax": round(cgst + sgst, 2),
            "estimated_total": estimated,
            "unpriced_item_count": 0,
            "estimate_excludes_unpriced_items": False,
            "shipping_amount": None,
        },
        "isEstimate": is_estimate,
        "org": org,
    }


class DayBookShapeTests(unittest.TestCase):
    """The generated DayBook must be readable by the Tally converter."""

    def test_identity_columns_required_by_the_converter_are_present(self):
        columns = prepare.daybook_columns([18.0])
        for required in (
            "Date", "Particulars", "Vch No.", "Sales Tax No.",
            "Gross Total", "Round Up Sale",
        ):
            self.assertIn(required, columns)

    def test_rate_columns_are_detected_at_the_expected_rates(self):
        columns = prepare.daybook_columns([18.0])
        rates = parse_rate_columns(columns)

        self.assertEqual(sorted(rates), [18.0])
        self.assertEqual(rates[18.0]["taxable"], "Sale Net 18% A/c.")
        self.assertEqual(rates[18.0]["cgst"], "CGST 9% Received")
        self.assertEqual(rates[18.0]["sgst"], "SGST 9% Received")
        self.assertEqual(rates[18.0]["igst"], "IGST 18% Received")

    def test_several_tax_rates_each_get_their_own_column_group(self):
        columns = prepare.daybook_columns([12.0, 18.0])
        rates = parse_rate_columns(columns)

        self.assertEqual(sorted(rates), [12.0, 18.0])
        self.assertEqual(rates[12.0]["cgst"], "CGST 6% Received")
        self.assertEqual(rates[18.0]["cgst"], "CGST 9% Received")

    def test_identity_columns_are_not_mistaken_for_rate_columns(self):
        rates = parse_rate_columns(prepare.daybook_columns([18.0]))
        self.assertNotIn("Sales Tax No.", rates)


class BillRowTests(unittest.TestCase):
    def test_rows_carry_org_prefix_gstin_and_gross_total(self):
        orders = [make_order("S-202610-000001")]
        rows, rates, stats = prepare.build_daybook_rows(orders, "skumar")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rates, [18.0])
        row = rows[0]
        self.assertEqual(row["Vch No."], "S-202610-000001")
        self.assertEqual(row["Sales Tax No."], "27AAGPP1621C1Z5")
        self.assertEqual(row["Particulars"], "Shaumitra Traders")
        self.assertEqual(row["Gross Total"], 1972.96)
        self.assertEqual(row["Sale Net 18% A/c."], 1672.0)
        self.assertEqual(row["CGST 9% Received"], 150.48)
        self.assertEqual(row["SGST 9% Received"], 150.48)
        self.assertEqual(stats["with_gstin"], 1)

    def test_taxable_plus_tax_equals_gross_total(self):
        rows, _, _ = prepare.build_daybook_rows([make_order("S-202610-000001")], "skumar")
        row = rows[0]
        added_up = (
            row["Sale Net 18% A/c."]
            + row["CGST 9% Received"]
            + row["SGST 9% Received"]
            + row["Round Up Sale"]
        )
        self.assertAlmostEqual(added_up, row["Gross Total"], places=2)

    def test_estimates_are_never_reported_as_taxable_sales(self):
        orders = [make_order("EST-202610-0001", is_estimate=True)]
        rows, rates, stats = prepare.build_daybook_rows(orders, "skumar")

        self.assertEqual(rows, [])
        self.assertEqual(rates, [])
        self.assertEqual(stats["skipped"].get("estimates"), 1)
        self.assertEqual(stats["bills"], 0)

    def test_zero_rate_bills_are_skipped(self):
        orders = [make_order("S-202610-000009", cgst_rate=0.0, sgst_rate=0.0)]
        rows, _, stats = prepare.build_daybook_rows(orders, "skumar")

        self.assertEqual(rows, [])
        self.assertEqual(stats["skipped"].get("no_tax_rate"), 1)

    def test_bill_without_buyer_gstin_is_kept_but_flagged(self):
        orders = [make_order("S-202610-000002", gstin="")]
        rows, _, stats = prepare.build_daybook_rows(orders, "skumar")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Sales Tax No."], "")
        self.assertEqual(stats["with_gstin"], 0)
        self.assertEqual(stats["without_gstin"], 1)

    def test_unreadable_dates_are_skipped(self):
        orders = [make_order("S-202610-000003", created_at="not-a-date")]
        rows, _, stats = prepare.build_daybook_rows(orders, "skumar")

        self.assertEqual(rows, [])
        self.assertEqual(stats["skipped"].get("bad_date"), 1)

    def test_gsc_bills_use_their_own_voucher_series(self):
        orders = [make_order("G-202610-000001", org="gsc", gstin="27ACJPP2955J1Z4")]
        rows, _, _ = prepare.build_daybook_rows(orders, "gsc")

        self.assertEqual(rows[0]["Vch No."], "G-202610-000001")


class HsnRowTests(unittest.TestCase):
    def test_lines_for_the_same_hsn_are_consolidated(self):
        items = [
            {"hsn": "85469090", "name": "TUBE", "quantity": 2, "unit_price": 100.0,
             "gross_amount": 200.0, "taxable_amount": 200.0,
             "specification": {"unit": "100mtr."}},
            {"hsn": "85469090", "name": "TUBE", "quantity": 3, "unit_price": 150.0,
             "gross_amount": 450.0, "taxable_amount": 450.0,
             "specification": {"unit": "100mtr."}},
        ]
        orders = [make_order("S-202610-000001", items=items)]
        rows, stats = prepare.build_hsn_rows(orders, cgst_rate=9.0, sgst_rate=9.0)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["HSN/SAC"], "85469090")
        self.assertEqual(row["Total Quantity"], 5)
        self.assertEqual(row["Total Value"], 650.0)
        self.assertEqual(row["Taxable Value"], 650.0)
        self.assertEqual(row["Rate"], 150.0)
        self.assertEqual(row["Central Tax Amount"], 58.5)
        self.assertEqual(row["State/UT Tax Amount"], 58.5)
        self.assertEqual(row["Integrated Tax Amount"], 0)
        self.assertEqual(stats["lines"], 2)

    def test_catalog_units_are_mapped_to_standard_uqc_codes(self):
        rows, _ = prepare.build_hsn_rows(
            [make_order("S-202610-000001")], cgst_rate=9.0, sgst_rate=9.0
        )
        self.assertEqual(rows[0]["UQC"], "MTR")
        self.assertEqual(prepare.to_uqc("Pcs."), "NOS")
        self.assertEqual(prepare.to_uqc("100mtr."), "MTR")
        self.assertIsNone(prepare.to_uqc(""))

    def test_lines_without_hsn_or_taxable_value_are_excluded(self):
        items = [
            {"hsn": "", "name": "NO HSN", "quantity": 1, "unit_price": 10.0,
             "gross_amount": 10.0, "taxable_amount": 10.0, "specification": {}},
            {"hsn": "85469090", "name": "QUOTE", "quantity": 1, "unit_price": None,
             "gross_amount": None, "taxable_amount": None, "specification": {}},
        ]
        rows, stats = prepare.build_hsn_rows(
            [make_order("S-202610-000001", items=items)], cgst_rate=9.0, sgst_rate=9.0
        )

        self.assertEqual(rows, [])
        self.assertEqual(stats["skipped_no_hsn"], 1)
        self.assertEqual(stats["skipped_no_taxable"], 1)

    def test_estimates_contribute_no_hsn_lines(self):
        rows, stats = prepare.build_hsn_rows(
            [make_order("EST-202610-0001", is_estimate=True)],
            cgst_rate=9.0, sgst_rate=9.0,
        )
        self.assertEqual(rows, [])
        self.assertEqual(stats["lines"], 0)


class ExcelLayoutTests(unittest.TestCase):
    """The converters locate headers by position, so the layout is a contract."""

    def setUp(self):
        import pandas as pd

        self.temporary_directory = tempfile.TemporaryDirectory(prefix="gst-layout-test-")
        self.root = Path(self.temporary_directory.name)
        self.pd = pd

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_daybook_has_two_title_rows_and_header_on_row_three(self):
        import datetime as dt

        path = self.root / "S-DayBook.xlsx"
        rows, rates, _ = prepare.build_daybook_rows([make_order("S-202610-000001")], "skumar")
        prepare.write_daybook(path, {"name": "S. Kumar & Bros", "gstin": "27AAGPP1621C1Z5"},
                              rows, rates, "2026-10")

        raw = self.pd.read_excel(path, header=None)
        header_labels = [str(value).strip() for value in raw.iloc[2] if self.pd.notna(value)]

        self.assertIn("Date", header_labels)
        self.assertIn("Vch No.", header_labels)
        self.assertEqual(prepare.DAYBOOK_TITLE_ROWS, 2)
        # First data row follows the header and carries a real date.
        self.assertIsInstance(raw.iloc[3, 0], dt.datetime)
        self.assertEqual(str(raw.iloc[3, 2]), "S-202610-000001")

    def test_hsn_header_sits_on_row_index_three(self):
        path = self.root / "HSNCodeSummary.xlsx"
        rows, _ = prepare.build_hsn_rows(
            [make_order("S-202610-000001")], cgst_rate=9.0, sgst_rate=9.0
        )
        prepare.write_hsn(path, {"name": "S. Kumar & Bros", "gstin": "27AAGPP1621C1Z5"},
                          rows, "2026-10")

        header_labels = [
            str(value).strip()
            for value in self.pd.read_excel(path, header=3).columns
        ]
        self.assertEqual(header_labels[0], "HSN/SAC")
        self.assertIn("Taxable Value", header_labels)
        self.assertIn("Central Tax Amount", header_labels)

        # And the converter's own read must yield data rows, not preamble text.
        frame = self.pd.read_excel(path, header=3)
        self.assertEqual(str(frame.iloc[0]["HSN/SAC"]), "85469090")


class PrepareRunTests(unittest.TestCase):
    """prepare() writes per-org files into a TallyToOutputsForGST checkout."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="gst-prepare-test-")
        self.root = Path(self.temporary_directory.name)
        self.bills_dir = self.root / "bills"
        self.bills_dir.mkdir(parents=True, exist_ok=True)
        self.tally_repo = self.root / "TallyToOutputsForGST"
        self.tally_repo.mkdir(parents=True, exist_ok=True)
        (self.tally_repo / "process_data.py").write_text("# stub\n", encoding="utf-8")

        self.original_bills_dir = prepare.BILLS_DIR
        prepare.BILLS_DIR = self.bills_dir

        self._write_register("2026-10", [
            make_order("S-202610-000001"),
            make_order("G-202610-000001", org="gsc", gstin="27ACJPP2955J1Z4"),
            make_order("EST-202610-0001", is_estimate=True),
        ])

    def tearDown(self):
        prepare.BILLS_DIR = self.original_bills_dir
        self.temporary_directory.cleanup()

    def _write_register(self, month, orders):
        import csv as csv_module

        path = self.bills_dir / f"{month}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv_module.DictWriter(
                handle,
                fieldnames=["id", "createdAt", "org", "buyer_name", "buyer_phone",
                            "subTotal", "grandTotal", "order_json"],
            )
            writer.writeheader()
            for order in orders:
                writer.writerow({
                    "id": order["order_reference"],
                    "createdAt": order["created_at"],
                    "org": order["org"],
                    "buyer_name": order["customer"]["name"],
                    "buyer_phone": order["customer"].get("phone", ""),
                    "subTotal": order["amounts"]["taxable_subtotal"],
                    "grandTotal": order["amounts"]["estimated_total"],
                    "order_json": json.dumps(order),
                })

    def test_bills_are_split_into_per_org_daybook_and_hsn_files(self):
        result = prepare.prepare(
            ["2026-10"], tally_repo=self.tally_repo, run_converter=False
        )

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(sorted(result["orgs"]), ["gsc", "skumar"])

        skumar = result["orgs"]["skumar"]
        gsc = result["orgs"]["gsc"]

        # The estimate never reaches either company's DayBook.
        self.assertEqual(skumar["daybook_rows"], 1)
        self.assertEqual(gsc["daybook_rows"], 1)
        self.assertEqual(skumar["skipped"].get("estimates"), 1)

        self.assertTrue(Path(skumar["daybook"]).is_file())
        self.assertTrue(Path(gsc["daybook"]).is_file())
        self.assertTrue(skumar["hsn"]["written"])
        self.assertTrue(gsc["hsn"]["written"])

        # Filenames follow the org prefix the converter scans for.
        self.assertEqual(Path(skumar["daybook"]).name, "S-DayBook.xlsx")
        self.assertEqual(Path(gsc["daybook"]).name, "G-DayBook.xlsx")
        self.assertIn("skumar", str(skumar["hsn"]["path"]))
        self.assertIn("HSN files", str(skumar["hsn"]["path"]))

    def test_converter_is_not_run_when_disabled(self):
        result = prepare.prepare(
            ["2026-10"], tally_repo=self.tally_repo, run_converter=False
        )
        self.assertIsNone(result["converter"])

    def test_missing_register_is_reported_as_an_error(self):
        result = prepare.prepare(
            ["2099-01"], tally_repo=self.tally_repo, run_converter=False
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("No bills recorded" in error for error in result["errors"]))

    def test_unknown_tally_repo_is_reported_not_raised(self):
        result = prepare.prepare(
            ["2026-10"], tally_repo=self.root / "nowhere", run_converter=False
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("process_data.py" in error for error in result["errors"]))

    def test_available_months_reads_the_register_filenames(self):
        self.assertEqual(prepare.available_months(), ["2026-10"])


class AppendBillSchemaTests(unittest.TestCase):
    """append_bill must understand the schema CommerceCore.createOrder emits."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="append-bill-test-")
        root = Path(self.temporary_directory.name)
        self.original_bills = seller.BILLS_DIR
        self.original_estimates = seller.ESTIMATES_DIR
        seller.BILLS_DIR = root / "bills"
        seller.ESTIMATES_DIR = root / "estimates"

    def tearDown(self):
        seller.BILLS_DIR = self.original_bills
        seller.ESTIMATES_DIR = self.original_estimates
        self.temporary_directory.cleanup()

    def test_current_create_order_payload_is_persisted(self):
        row = seller.append_bill(make_order("S-202610-000001"))

        self.assertIsNotNone(row)
        # The displayed invoice number survives instead of being renumbered.
        self.assertEqual(row["id"], "S-202610-000001")
        self.assertEqual(row["createdAt"], "2026-10-01T11:30:00.000Z")
        self.assertEqual(row["org"], "skumar")
        self.assertEqual(row["buyer_name"], "Shaumitra Traders")
        self.assertEqual(row["subTotal"], 1672.0)
        self.assertEqual(row["grandTotal"], 1972.96)

        registers = sorted(p.name for p in seller.BILLS_DIR.glob("*.csv"))
        self.assertEqual(registers, ["2026-10.csv"])

        with (seller.BILLS_DIR / "2026-10.csv").open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            stored = next(csv_module.DictReader(handle))
        payload = json.loads(stored["order_json"])
        self.assertEqual(payload["order_reference"], "S-202610-000001")
        self.assertEqual(payload["org"], "skumar")

    def test_estimates_go_to_the_separate_estimate_register(self):
        row = seller.append_bill(make_order("EST-202610-0001", is_estimate=True))

        self.assertIsNotNone(row)
        self.assertTrue(row["id"].startswith("EST-"))
        self.assertTrue(list(seller.ESTIMATES_DIR.glob("*.csv")))
        self.assertFalse(list(seller.BILLS_DIR.glob("*.csv")))

    def test_payload_without_any_timestamp_is_rejected(self):
        self.assertIsNone(seller.append_bill({"org": "skumar"}))

    def test_legacy_payload_shape_is_still_accepted(self):
        legacy = {
            "id": "S-202501-0042",
            "createdAt": "2025-01-15T09:00:00.000Z",
            "org": "skumar",
            "buyer": {"name": "Old Customer", "phone": "9820000000"},
            "totals": {"subTotal": 100.0, "grandTotal": 118.0},
            "html": "<html></html>",
        }
        row = seller.append_bill(legacy)

        self.assertIsNotNone(row)
        self.assertEqual(row["id"], "S-202501-0042")
        self.assertEqual(row["buyer_name"], "Old Customer")
        self.assertEqual(row["subTotal"], 100.0)
        self.assertEqual(row["grandTotal"], 118.0)


if __name__ == "__main__":
    unittest.main()