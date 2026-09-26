import csv
import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def load_tool(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seller = load_tool("local_seller_tool", "tools/seller/local_seller.py")
actions_budget = load_tool("actions_budget_tool", "tools/seller/actions_budget.py")


class SellerEditorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="seller-editor-test-")
        root = Path(self.temporary_directory.name)
        self.original_data = seller.DATA_FILE
        self.original_history = seller.HISTORY_FILE
        seller.DATA_FILE = root / "catalog_data.csv"
        seller.HISTORY_FILE = root / ".seller_history.json"
        with seller.DATA_FILE.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "sr_number", "group_number", "item_number", "category",
                    "item_name", "hsn_code", "list_price", "hidden",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "sr_number": "1.1",
                "category": "Test", "item_name": "Item", "hsn_code": "",
                "list_price": "10", "hidden": "",
            })

    def tearDown(self):
        seller.DATA_FILE = self.original_data
        seller.HISTORY_FILE = self.original_history
        self.temporary_directory.cleanup()

    def test_save_persists_hidden_and_editable_fields_and_undo_restores_snapshot(self):
        fields, rows, revision = seller.read_catalog()
        rows[0]["list_price"] = "25.50"
        rows[0]["hidden"] = "true"
        _, saved_rows, saved_revision = seller.update_catalog(rows, revision)
        self.assertEqual(saved_rows[0]["list_price"], "25.50")
        self.assertEqual(saved_rows[0]["hidden"], "true")
        self.assertNotEqual(saved_revision, revision)

        _, restored, undo_revision = seller.undo_catalog(saved_revision)
        self.assertEqual(restored[0]["list_price"], "10")
        self.assertEqual(restored[0]["hidden"], "")
        self.assertNotEqual(undo_revision, saved_revision)

    def test_stale_revision_and_invalid_catalog_values_are_rejected(self):
        fields, rows, revision = seller.read_catalog()
        with self.assertRaisesRegex(ValueError, "changed in another window"):
            seller.update_catalog(rows, "stale")
        rows[0]["list_price"] = "-2"
        with self.assertRaisesRegex(ValueError, "non-negative"):
            seller.update_catalog(rows, revision)

    def test_local_service_is_loopback_only(self):
        self.assertEqual(seller.HOST, "127.0.0.1")
        source = (ROOT / "tools" / "seller" / "local_seller.py").read_text(encoding="utf-8")
        self.assertIn("authorized_local_request", source)
        self.assertIn("SKUMAR_SELLER_ALLOW_NONLOOPBACK", source)


class ActionsBudgetTests(unittest.TestCase):
    def test_monthly_limit_defaults_to_conservative_cap_and_can_be_configured(self):
        self.assertEqual(actions_budget.monthly_run_limit({}), 20)
        self.assertEqual(
            actions_budget.monthly_run_limit({"SKUMAR_PAGES_RUN_LIMIT": "12"}),
            12,
        )
        with self.assertRaises(ValueError):
            actions_budget.monthly_run_limit({"SKUMAR_PAGES_RUN_LIMIT": "0"})

    def test_remaining_run_count_never_goes_below_zero(self):
        self.assertEqual(actions_budget.remaining_run_count(4, 20), 16)
        self.assertEqual(actions_budget.remaining_run_count(20, 20), 0)
        self.assertEqual(actions_budget.remaining_run_count(25, 20), 0)

    def test_monthly_count_uses_current_utc_month_and_fails_on_api_errors(self):
        now = datetime(2026, 9, 26, 20, tzinfo=timezone.utc)
        seen = {}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"total_count":3}'

        def opener(request, timeout):
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            return Response()

        count = actions_budget.get_monthly_run_count(
            now=now,
            opener=opener,
            environment={},
        )
        self.assertEqual(count, 3)
        self.assertIn("created=2026-09-01", seen["url"])
        self.assertIn("deploy-pages.yml", seen["url"])
        self.assertIn("event=push", seen["url"])
        self.assertEqual(seen["timeout"], 15)

        def failed_opener(request, timeout):
            raise OSError("network unavailable")

        with self.assertRaisesRegex(RuntimeError, "publishing is blocked"):
            actions_budget.get_monthly_run_count(
                now=now,
                opener=failed_opener,
                environment={},
            )


if __name__ == "__main__":
    unittest.main()
