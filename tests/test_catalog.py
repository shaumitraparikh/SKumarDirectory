import json
import sys
import unittest
from pathlib import Path


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT))

from src import build_catalog


class CatalogDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = build_catalog.load_csv_data(CATALOG_ROOT / "data" / "catalog_data.csv")
        cls.by_serial = {item["sr_number"]: item for item in cls.items}

    def test_serial_and_hierarchical_numbers_are_unique_and_positive(self):
        serials = [item["sr_number"] for item in self.items]
        hierarchy = [(int(item["sr_number"].split(".")[0]), int(item["sr_number"].split(".")[1])) for item in self.items]
        self.assertTrue(all(len(serial.split(".")) == 2 for serial in serials))
        self.assertEqual(len(serials), len(set(serials)))
        self.assertTrue(all(group > 0 and number > 0 for group, number in hierarchy))
        self.assertEqual(len(hierarchy), len(set(hierarchy)))

    def test_removing_a_catalog_item_does_not_require_renumbering(self):
        remaining = self.items[:10] + self.items[11:]
        build_catalog.validate_catalog_data(remaining)

    def test_manual_item_is_complete_and_has_expected_price(self):
        item = self.by_serial["65.1"]
        self.assertEqual(item["item_name"], "Bulbs & Holders 1000W bulb")
        self.assertEqual(item["hsn_code"], "94059900")
        self.assertEqual(item["list_price"], "996.0")
        self.assertEqual(item["unit"], "Pcs.")

    def test_inferable_hsn_is_filled_from_consistent_category_peers(self):
        item = self.by_serial["7.2"]
        self.assertEqual(item["hsn_code"], "39173210")
        self.assertTrue(all(row["hsn_code"] for row in self.items))
        peer_codes = {
            peer["hsn_code"] for peer in self.items
            if peer["category"] == item["category"] and peer["hsn_code"]
        }
        self.assertEqual(peer_codes, {item["hsn_code"]})

    def test_quote_only_products_remain_unpriced_not_fabricated(self):
        quote_items = [item for item in self.items if not item["list_price"]]
        self.assertGreater(len(quote_items), 0)
        for item in quote_items:
            self.assertEqual(item["list_price"], "")

    def test_ambiguous_source_price_is_preserved_as_a_quote_note(self):
        self.assertEqual(self.by_serial["19.6"]["list_price"], "50.0")
        item = self.by_serial["21.15"]
        self.assertEqual(item["list_price"], "")
        notes_path = CATALOG_ROOT / "data" / "catalog_data_notes.json"
        notes = json.loads(notes_path.read_text(encoding="utf-8"))
        self.assertEqual(notes["21.15"]["source_text"], "280.00 / 190.00")
        self.assertEqual(notes["21.15"]["status"], "requires_business_review")

    def test_invalid_price_and_serial_sequences_fail_fast(self):
        valid = {
            "sr_number": "1.1", "group_number": "1", "item_number": "1",
            "category": "Test", "item_name": "Part", "list_price": ""
        }
        build_catalog.validate_catalog_data([valid.copy()])
        invalid_price = dict(valid, list_price="-5")
        with self.assertRaisesRegex(ValueError, "non-negative"):
            build_catalog.validate_catalog_data([invalid_price])
        duplicate_serial = [valid.copy(), dict(valid, sr_number="1.1")]
        with self.assertRaisesRegex(ValueError, "unique"):
            build_catalog.validate_catalog_data(duplicate_serial)

    def test_category_images_are_marked_as_representative_fallbacks(self):
        categories = build_catalog.group_by_category(self.items, build_catalog.IMAGES_DIR)
        fallback_items = [
            item for category in categories for item in category["products"]
            if item["image_is_representative"]
        ]
        self.assertGreater(len(fallback_items), 0)
        self.assertTrue(all(item["display_image_path"] for item in fallback_items))
        self.assertTrue(all(not item["image_path"] for item in fallback_items))

    def test_generated_pages_include_quote_ui_and_checkout_assets(self):
        search = (CATALOG_ROOT / "index.html").read_text(encoding="utf-8")
        printed = (CATALOG_ROOT / "print_catalog.html").read_text(encoding="utf-8")
        for page in (search, printed):
            self.assertTrue(all(line == line.rstrip() for line in page.splitlines()))
        search_js = (CATALOG_ROOT / "app" / "assets" / "js" / "search_catalog.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Price on request", search_js)
        self.assertIn("Add to quote", search_js)
        self.assertIn("commerce_core.js", search)
        self.assertIn("search_catalog.css", search)
        self.assertIn('href="app/assets/css/search_catalog.css"', search)
        self.assertIn('src="app/assets/js/commerce_core.js"', search)
        self.assertIn('href="print_catalog.html"', search)
        self.assertIn("Price on request", printed)
        self.assertNotIn("../images/", printed)
        self.assertIn("Amit G. Parikh", search)
        self.assertIn("27ACJPP2955J1Z4", search)
        self.assertIn("9869905779", printed)
        self.assertIn("window.INJECTED_CLIENT_DATA = []", search)

if __name__ == "__main__":
    unittest.main()
