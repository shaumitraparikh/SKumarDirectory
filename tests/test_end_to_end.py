import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from decimal import Decimal, InvalidOperation


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT))

import build_catalog


class EmbeddedCatalogParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_catalog_data = False
        self.catalog_data = ""
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("id") == "catalogData":
            self.in_catalog_data = True
        for attribute in ("src", "href"):
            value = attributes.get(attribute)
            if value:
                self.assets.append(value)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_catalog_data:
            self.in_catalog_data = False

    def handle_data(self, data):
        if self.in_catalog_data:
            self.catalog_data += data


class CatalogEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (CATALOG_ROOT / "data" / "catalog_data.csv").open(
            encoding="utf-8-sig", newline=""
        ) as csv_file:
            reader = csv.DictReader(csv_file)
            cls.csv_fields = reader.fieldnames
            cls.csv_rows = list(reader)
        cls.products_by_serial = {row["sr_number"]: row for row in cls.csv_rows}

    def test_full_catalog_build_runs_from_outside_repository(self):
        with tempfile.TemporaryDirectory(prefix="catalog-build-e2e-") as working_dir:
            environment = os.environ.copy()
            environment["CATALOG_NO_BROWSER"] = "1"
            result = subprocess.run(
                [sys.executable, str(CATALOG_ROOT / "build_catalog.py")],
                cwd=working_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"Loaded {len(self.csv_rows)} items", result.stdout)
        self.assertTrue((CATALOG_ROOT / "search_catalog.html").is_file())
        self.assertTrue((CATALOG_ROOT / "customer_catalog.html").is_file())
        self.assertTrue((CATALOG_ROOT / "print_catalog.html").is_file())

    def test_build_configuration_is_loaded_from_data(self):
        self.assertEqual(build_catalog.CONFIG_FILE, CATALOG_ROOT / "data" / "config.json")
        config = build_catalog.load_config()
        self.assertEqual(config["company"]["name"], "S. Kumar & Bros")
        self.assertEqual(config["checkout"]["provider"], "whatsapp")

    def test_customer_directory_stays_local_and_order_forms_are_accessible_disclosures(self):
        example_file = CATALOG_ROOT / "data" / "client_data.example.csv"
        self.assertIn("client_id,name,business_name,phone,email,address,state,pincode,gstin",
                      example_file.read_text(encoding="utf-8-sig"))
        self.assertIn("data/client_data.csv", (CATALOG_ROOT / ".gitignore").read_text(encoding="utf-8"))
        tracked_customer_data = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "data/client_data.csv"],
            cwd=CATALOG_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(tracked_customer_data.returncode, 0)
        ignored_customer_data = subprocess.run(
            ["git", "check-ignore", "--quiet", "data/client_data.csv"],
            cwd=CATALOG_ROOT,
            check=False,
        )
        self.assertEqual(ignored_customer_data.returncode, 0)
        search_html = (CATALOG_ROOT / "customer_catalog.html").read_text(encoding="utf-8")
        self.assertIn('id="buyerDetails"', search_html)
        self.assertIn('<details class="buyer-info"', search_html)
        self.assertIn('id="orderSummaryDetails"', search_html)
        self.assertIn('id="customerLookup"', search_html)
        self.assertIn('id="clientCsvFile"', search_html)
        self.assertIn('assets/js/client_directory_core.js', search_html)
        self.assertIn('assets/js/bill_archive.js', search_html)
        self.assertIn('id="billArchiveDialog"', search_html)
        self.assertIn('id="openBillsButton"', search_html)
        self.assertNotIn("client_data.csv", search_html)
        seller_html = (CATALOG_ROOT / "search_catalog.html").read_text(encoding="utf-8")
        self.assertIn('id="sellerSaveButton"', seller_html)
        self.assertIn('tools/seller/seller_editor.js', seller_html)
        self.assertNotIn('tools/seller/seller_editor.js', search_html)

    def test_hidden_catalog_items_are_excluded_from_customer_output(self):
        self.assertIn("hidden", self.csv_fields)
        rows = [
            {"sr_number": "1", "hidden": False},
            {"sr_number": "2", "hidden": True},
        ]
        self.assertEqual(
            [row["sr_number"] for row in build_catalog.visible_catalog_items(rows)],
            ["1"],
        )
        seller_html = (CATALOG_ROOT / "search_catalog.html").read_text(encoding="utf-8")
        customer_html = (CATALOG_ROOT / "customer_catalog.html").read_text(encoding="utf-8")
        self.assertIn('id="sellerSaveButton"', seller_html)
        self.assertNotIn("seller-tools", customer_html)

    def test_generated_bills_are_local_only_and_monthly_archive_is_available(self):
        ignore_file = (CATALOG_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/generated_bills/*", ignore_file)
        self.assertTrue((CATALOG_ROOT / "generated_bills" / ".gitkeep").is_file())

        ignored_bill = subprocess.run(
            ["git", "check-ignore", "--quiet", "generated_bills/2026-09/PI-test.html"],
            cwd=CATALOG_ROOT,
            check=False,
        )
        self.assertEqual(ignored_bill.returncode, 0)
        bill_archive_script = (
            CATALOG_ROOT / "assets" / "js" / "bill_archive.js"
        ).read_text(encoding="utf-8")
        self.assertIn("getDirectoryHandle(month, { create: true })", bill_archive_script)
        self.assertIn("BillArchive.prototype.listBills", bill_archive_script)
        self.assertIn("assets/js/bill_archive.js", (
            CATALOG_ROOT / "templates" / "search_template.html"
        ).read_text(encoding="utf-8"))

    def test_search_payload_retains_all_csv_and_future_fields(self):
        self.assertIn("sr_number", self.csv_fields)
        self.assertNotIn("sr_no", self.csv_fields)
        self.assertIn("group_number", self.csv_fields)
        self.assertIn("item_number", self.csv_fields)
        search_html = (CATALOG_ROOT / "search_catalog.html").read_text(encoding="utf-8")
        parser = EmbeddedCatalogParser()
        parser.feed(search_html)
        products = json.loads(parser.catalog_data)

        self.assertEqual(len(products), len(self.csv_rows))
        self.assertTrue(set(self.csv_fields).issubset(products[0]))
        self.assertEqual(products[-1]["sr_number"], "1412")
        self.assertEqual(products[-1]["item_name"], "Bulbs & Holders 1000W bulb")
        self.assertIn("group_number", products[-1])
        self.assertIn("item_number", products[-1])

        prepared = build_catalog.prepare_search_catalog_data([{
            "sr_number": "1",
            "group_number": "1",
            "item_number": "1",
            "future_specification": "M12",
            "image_path": "images/private-build-path.png",
            "display_image_path": "images/derived.png",
            "image_is_representative": True,
        }])
        self.assertEqual(prepared[0]["future_specification"], "M12")
        self.assertNotIn("image_path", prepared[0])
        self.assertIn("display_image_path", prepared[0])
        self.assertEqual(prepared[0]["display_image_path"], "images/derived.png")

    def test_generated_page_assets_resolve_and_every_product_is_rendered(self):
        expected_ids = {str(row['sr_number']) for row in self.csv_rows}
        search_html = (CATALOG_ROOT / "search_catalog.html").read_text(encoding="utf-8")
        printed_html = (CATALOG_ROOT / "print_catalog.html").read_text(encoding="utf-8")
        
        # Verify JSON payload in search_catalog contains all serials
        json_match = re.search(r'<script id="catalogData" type="application/json">(.+?)</script>', search_html, re.DOTALL)
        self.assertIsNotNone(json_match)
        catalog_data = json.loads(json_match.group(1))
        actual_ids_json = {str(item['sr_number']) for item in catalog_data}
        self.assertEqual(actual_ids_json, expected_ids)
        
        # Verify printed_html renders all serials
        actual_ids_print = set(re.findall(r'<td class="col-sr">(\d+)\.<br>', printed_html))
        self.assertEqual(actual_ids_print, expected_ids)

        for page_html in (search_html, printed_html):
            parser = EmbeddedCatalogParser()
            parser.feed(page_html)
            for asset_url in parser.assets:
                parts = urlsplit(asset_url)
                if parts.scheme or not parts.path:
                    continue
                asset_path = CATALOG_ROOT / unquote(parts.path.lstrip("/"))
                self.assertTrue(asset_path.is_file(), f"Missing generated page asset: {asset_url}")

    def test_catalog_pages_include_mobile_viewports_and_responsive_layouts(self):
        for page_name in ("index.html", "search_catalog.html", "customer_catalog.html", "print_catalog.html"):
            page_html = (CATALOG_ROOT / page_name).read_text(encoding="utf-8")
            self.assertIn('name="viewport"', page_html, f"{page_name} has no mobile viewport")

        search_css = (CATALOG_ROOT / "assets" / "css" / "search_catalog.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("@media (max-width: 760px)", search_css)
        self.assertIn("@media (max-width: 380px)", search_css)

        print_template = (CATALOG_ROOT / "templates" / "print_template.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("@media screen and (max-width: 700px)", print_template)
        self.assertIn(".page-content { column-count: 1;", print_template)
        self.assertIn("minmax(min(100%, 320px), 1fr)", search_css)

    def test_order_price_breakdown_is_collapsible_with_subtotal_always_visible(self):
        search_html = (CATALOG_ROOT / "customer_catalog.html").read_text(encoding="utf-8")
        disclosure_start = search_html.index('<details class="price-breakdown" id="priceBreakdown">')
        disclosure_end = search_html.index("</details>", disclosure_start)
        disclosure = search_html[disclosure_start:disclosure_end]
        self.assertNotIn(" open", disclosure.split(">", 1)[0])
        self.assertIn("Priced items subtotal", disclosure)
        self.assertIn('id="itemsSubtotal"', disclosure)
        self.assertIn('id="discountTotal"', disclosure)
        self.assertIn('id="subTotal"', disclosure)
        self.assertIn('id="cgstAmount"', disclosure)
        self.assertIn('id="sgstAmount"', disclosure)
        self.assertIn('id="taxAmount"', disclosure)
        self.assertIn('id="grandTotal"', search_html[disclosure_end:])

    def test_source_documents_are_backups_and_numbered_products_are_accounted_for(self):
        docs_dir = CATALOG_ROOT / "docs 2025"
        source_path = docs_dir / "List 2025.docx"
        photo_path = docs_dir / "GSC - SK Catlog Photo.docx"
        self.assertTrue(source_path.is_file())
        self.assertTrue(photo_path.is_file())
        for document in (source_path, photo_path):
            with zipfile.ZipFile(document) as archive:
                self.assertIsNone(archive.testzip(), f"Damaged source backup: {document.name}")
        self.assertFalse(any(docs_dir.glob("*.csv")))
        self.assertFalse(any(docs_dir.glob("*.html")))

        extractor_path = CATALOG_ROOT / "tools" / "extract" / "extract_smart_v2.py"
        spec = importlib.util.spec_from_file_location("catalog_source_extractor", extractor_path)
        extractor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extractor)
        image_map = json.loads(
            (CATALOG_ROOT / "data" / "image_serial_map.json").read_text(encoding="utf-8")
        )
        captured_inline_images = 0
        with tempfile.TemporaryDirectory(prefix="catalog-source-images-") as image_dir:
            parser = extractor.TableParser(source_path)
            parser.images_dir = Path(image_dir)
            with contextlib.redirect_stdout(io.StringIO()):
                parser.process()
            for source_item in parser.items:
                if not source_item["image_ref"].startswith("sr_"):
                    continue
                extracted = list(Path(image_dir).glob(source_item["image_ref"] + ".*"))
                self.assertTrue(extracted, f"Missing source image for sr_number {source_item['sr_number']}")
                captured_inline_images += 1
                product = self.products_by_serial[source_item["sr_number"]]
                image_path = build_catalog.find_image(product["image_ref"], build_catalog.IMAGES_DIR)
                self.assertIsNotNone(
                    image_path,
                    f"Catalog image missing for source sr_number {source_item['sr_number']}",
                )
                published_asset = CATALOG_ROOT / image_path
                source_hashes = {
                    hashlib.sha256(path.read_bytes()).digest() for path in extracted
                }
                self.assertIn(
                    hashlib.sha256(published_asset.read_bytes()).digest(),
                    source_hashes,
                    f"Catalog image does not match source sr_number {source_item['sr_number']}",
                )
                mapping = image_map[product["image_ref"]]
                self.assertIn(int(source_item["sr_number"]), mapping["sr_numbers"])
                self.assertIn(
                    f"{product['group_number']}.{product['item_number']}",
                    mapping["group_items"],
                )
        self.assertEqual(captured_inline_images, 411)
        source_document = extractor.Document(source_path)
        source_inherited_hsn = any(
            "118" in [cell.text.strip().rstrip(".") for cell in row.cells]
            and any("HSN Code-40094100" in cell.text for cell in row.cells)
            for row in source_document.tables[0].rows
        )
        self.assertTrue(source_inherited_hsn)
        self.assertEqual(self.products_by_serial["117"]["hsn_code"], "40094100")
        self.assertEqual(self.products_by_serial["118"]["hsn_code"], "40094100")

        source_serials = {int(item["sr_number"]) for item in parser.items}
        catalog_serials = {int(item["sr_number"]) for item in self.csv_rows}
        expected_source_serials = set(range(1, 1350)) | set(range(1361, 1412))
        self.assertEqual(source_serials, expected_source_serials)
        self.assertTrue(source_serials.issubset(catalog_serials))
        self.assertEqual(len(parser.items), len(expected_source_serials))
        self.assertNotIn(1412, source_serials)
        notes = json.loads(
            (CATALOG_ROOT / "data" / "catalog_data_notes.json").read_text(encoding="utf-8")
        )
        for serial in range(1350, 1361):
            self.assertEqual(notes[str(serial)]["status"], "requires_business_review")
        self.assertTrue(
            (CATALOG_ROOT / "data" / "catalog_data.csv").is_file(),
            "The curated catalog CSV remains the canonical, editable product dataset.",
        )
        for source_item in parser.items:
            product = self.products_by_serial[source_item["sr_number"]]
            source_name = source_item["item_name"]
            if source_item["list_price"]:
                source_name = re.sub(
                    r"\s+" + re.escape(source_item["list_price"]) + r"\s*$",
                    "",
                    source_name,
                )
            source_tokens = set(re.findall(r"[a-z0-9]+", source_name.casefold()))
            source_tokens.difference_update({"size", "id", "od", "lf", "hsn", "code"})
            catalog_text = " ".join(
                product[field]
                for field in (
                    "category", "item_name", "size", "id_size", "od_size", "lf_size"
                )
            )
            catalog_tokens = set(re.findall(r"[a-z0-9]+", catalog_text.casefold()))
            self.assertTrue(
                source_tokens.issubset(catalog_tokens),
                f"Source particulars not found for sr_number {source_item['sr_number']}: "
                f"{sorted(source_tokens - catalog_tokens)}",
            )
            source_price = source_item["list_price"].strip()
            catalog_price = product["list_price"].strip()
            try:
                source_amount = Decimal(source_price) if source_price else None
            except InvalidOperation:
                source_amount = None
                if source_item["sr_number"] == "393":
                    self.assertEqual(catalog_price, "")
                    self.assertIn("393", notes)
                else:
                    self.assertEqual(source_item["sr_number"], "303")
                    self.assertEqual(catalog_price, "50.00")
            if source_amount is None and source_item["sr_number"] not in {"303", "393"}:
                self.assertEqual(catalog_price, "")
            elif source_amount is not None:
                self.assertEqual(Decimal(catalog_price), source_amount)
            if product["image_ref"]:
                mapped = image_map[product["image_ref"]]
                self.assertIn(int(source_item["sr_number"]), mapped["sr_numbers"])
                label = f"{product['group_number']}.{product['item_number']}"
                self.assertIn(label, mapped["group_items"])

    def test_catalog_image_names_map_back_to_each_referenced_serial(self):
        image_map = json.loads(
            (CATALOG_ROOT / "data" / "image_serial_map.json").read_text(encoding="utf-8")
        )
        for row in self.csv_rows:
            image_ref = row["image_ref"]
            if not image_ref:
                continue
            image_path = build_catalog.find_image(image_ref, build_catalog.IMAGES_DIR)
            self.assertIsNotNone(image_path, f"Missing image for sr_number {row['sr_number']}")
            self.assertTrue(
                image_ref.startswith("sr_") or "_sr_" in image_ref,
                f"Image {image_ref!r} has no serial in its filename.",
            )
            mapping = image_map[image_ref]
            self.assertIn(int(row["sr_number"]), mapping["sr_numbers"])
            self.assertIn(
                f"{row['group_number']}.{row['item_number']}",
                mapping["group_items"],
            )
            if image_ref.startswith("sr_"):
                self.assertTrue(
                    image_ref.startswith(f"sr_{int(row['sr_number']):04d}_"),
                    f"Image {image_ref!r} is not tagged for sr_number {row['sr_number']}",
                )
            else:
                match = re.search(r"(?:^|_)sr_(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)_", image_ref)
                self.assertIsNotNone(match, f"Image {image_ref!r} has no serial mapping")
                ranges = match.group(1).split(",")
                serial = int(row["sr_number"])
                self.assertTrue(
                    any(
                        serial == int(value.split("-")[0])
                        if "-" not in value
                        else int(value.split("-")[0]) <= serial <= int(value.split("-")[1])
                        for value in ranges
                    ),
                    f"Image {image_ref!r} does not map to sr_number {serial}",
                )

    def test_every_source_photo_is_serial_mapped_and_kept_in_the_asset_output(self):
        from docx import Document

        photo_document = Document(CATALOG_ROOT / "docs 2025" / "GSC - SK Catlog Photo.docx")
        image_map = json.loads(
            (CATALOG_ROOT / "data" / "image_serial_map.json").read_text(encoding="utf-8")
        )
        assets_by_hash = {}
        for path in (CATALOG_ROOT / "images").iterdir():
            if path.is_file():
                assets_by_hash.setdefault(hashlib.sha256(path.read_bytes()).digest(), []).append(path)

        source_hashes = set()
        for table in photo_document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for blip in cell._element.xpath(".//a:blip"):
                        relationship = blip.get(
                            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                        )
                        if relationship:
                            source_hashes.add(
                                hashlib.sha256(
                                    photo_document.part.related_parts[relationship].blob
                                ).digest()
                            )

        self.assertEqual(len(source_hashes), 80)
        for source_hash in source_hashes:
            self.assertIn(source_hash, assets_by_hash, "A source category photo is not in the output assets.")
            for asset in assets_by_hash[source_hash]:
                self.assertIn(asset.stem, image_map)
                self.assertTrue(image_map[asset.stem]["sr_numbers"])
                self.assertTrue(image_map[asset.stem]["group_items"])

        image_stems = {path.stem for path in (CATALOG_ROOT / "images").iterdir() if path.is_file()}
        self.assertEqual(image_stems, set(image_map))
        self.assertTrue(all(stem.startswith(("sr_", "group_", "groups_")) for stem in image_stems))
        for stem, mapping in image_map.items():
            serial_match = re.search(
                r"(?:^|_)sr_(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)_",
                stem,
            )
            self.assertIsNotNone(serial_match, f"Image {stem!r} has no serial identifier")

            def expand_ranges(value):
                numbers = set()
                for part in value.split(","):
                    bounds = [int(number) for number in part.split("-")]
                    numbers.update(range(bounds[0], bounds[-1] + 1))
                return numbers

            filename_serials = expand_ranges(serial_match.group(1))
            mapped_serials = set(mapping["sr_numbers"])
            if stem[serial_match.end():].startswith("span_"):
                self.assertTrue(mapped_serials.issubset(filename_serials))
                self.assertEqual(
                    (min(filename_serials), max(filename_serials)),
                    (min(mapped_serials), max(mapped_serials)),
                )
            else:
                self.assertEqual(
                    filename_serials,
                    mapped_serials,
                    f"Filename serials disagree with image map for {stem!r}",
                )

            mapped_groups = {
                int(value.split(".")[0]) for value in mapping["group_items"]
            }
            mapped_items = {
                (int(group), int(item))
                for group, item in (value.split(".") for value in mapping["group_items"])
            }
            if stem.startswith("sr_"):
                single_match = re.match(
                    r"sr_(\d+)_group_(\d+)_item_(\d+)_",
                    stem,
                )
                self.assertIsNotNone(single_match, f"Image {stem!r} has no group.item ID")
                self.assertEqual(
                    mapped_items,
                    {(int(single_match.group(2)), int(single_match.group(3)))},
                )
            elif len(mapped_groups) == 1:
                group_match = re.match(
                    r"group_(\d+)_items_([\d,-]+)(?:_span)?_sr_",
                    stem,
                )
                self.assertIsNotNone(group_match, f"Shared image {stem!r} has no item range")
                self.assertEqual(int(group_match.group(1)), next(iter(mapped_groups)))
                item_numbers = expand_ranges(group_match.group(2))
                mapped_item_numbers = {item for _, item in mapped_items}
                if "_span_sr_" in stem:
                    self.assertTrue(mapped_item_numbers.issubset(item_numbers))
                    self.assertEqual(
                        (min(item_numbers), max(item_numbers)),
                        (min(mapped_item_numbers), max(mapped_item_numbers)),
                    )
                else:
                    self.assertEqual(
                        item_numbers,
                        mapped_item_numbers,
                        f"Filename item numbers disagree with image map for {stem!r}",
                    )
            else:
                group_match = re.match(r"groups_([\d,-]+)_sr_", stem)
                self.assertIsNotNone(group_match, f"Shared image {stem!r} has no group range")
                self.assertEqual(expand_ranges(group_match.group(1)), mapped_groups)

    def test_extraction_drafts_do_not_target_canonical_catalog_data(self):
        source = (CATALOG_ROOT / "tools" / "extract" / "extract_smart.py").read_text(
            encoding="utf-8"
        )
        source_v2 = (CATALOG_ROOT / "tools" / "extract" / "extract_smart_v2.py").read_text(
            encoding="utf-8"
        )
        for script, expected_draft in (
            (source, "catalog_extraction_draft.csv"),
            (source_v2, "catalog_extraction_draft_v2.csv"),
        ):
            self.assertIn(expected_draft, script)
            self.assertNotIn('"data" / "catalog_data.csv"', script)


if __name__ == "__main__":
    unittest.main()
