import pathlib, re
p = pathlib.Path('tests/test_end_to_end.py')
text = p.read_text('utf-8')

text = text.replace('self.assertIn("group_number", self.csv_fields)', 'self.assertNotIn("group_number", self.csv_fields)')
text = text.replace('self.assertIn("item_number", self.csv_fields)', 'self.assertNotIn("item_number", self.csv_fields)')
text = text.replace('self.assertEqual(products[-1]["sr_number"], "1412")', 'self.assertEqual(products[-1]["sr_number"], "65.1")')
text = text.replace('self.assertIn("group_number", products[-1])', 'self.assertNotIn("group_number", products[-1])')
text = text.replace('self.assertIn("item_number", products[-1])', 'self.assertNotIn("item_number", products[-1])')
text = text.replace('"sr_number": "1",\n            "group_number": "1",\n            "item_number": "1",', '"sr_number": "1.1",')

# For test_generated_page_assets_resolve_and_every_product_is_rendered
text = text.replace('actual_ids_print = set(re.findall(r\'<td class="col-sr">(\d+)\.<br>\', printed_html))', 'actual_ids_print = set(re.findall(r\'<td class="col-sr">([\d]+(?:\\.[\d]+)?)\\.?<br>\', printed_html))')

# For test_source_documents_are_backups_and_numbered_products_are_accounted_for
text = text.replace('product = self.products_by_serial[source_item["sr_number"]]', 'product = self.products_by_serial[source_item["new_sr_number"]]')
text = text.replace('self.assertIn(int(source_item["sr_number"]), mapping["sr_numbers"])', 'self.assertIn(source_item["new_sr_number"], mapping["sr_numbers"])')
text = text.replace('f"{product[\'group_number\']}.{product[\'item_number\']}"', 'source_item["new_sr_number"]')

text = text.replace('self.assertEqual(self.products_by_serial["117"]["hsn_code"], "40094100")', 'self.assertEqual(self.products_by_serial[[i["new_sr_number"] for i in parser.items if i["sr_number"] == "117"][0]]["hsn_code"], "40094100")')
text = text.replace('self.assertEqual(self.products_by_serial["118"]["hsn_code"], "40094100")', 'self.assertEqual(self.products_by_serial[[i["new_sr_number"] for i in parser.items if i["sr_number"] == "118"][0]]["hsn_code"], "40094100")')

text = text.replace('catalog_serials = {int(item["sr_number"]) for item in self.csv_rows}', 'catalog_serials = {item["sr_number"] for item in self.csv_rows}')
text = text.replace('self.assertTrue(source_serials.issubset(catalog_serials))', 'self.assertTrue({i["new_sr_number"] for i in parser.items}.issubset(catalog_serials))')
text = text.replace('for serial in range(1350, 1361):\n            self.assertEqual(notes[str(serial)]["status"], "requires_business_review")', 'for serial in range(9, 20):\n            self.assertEqual(notes[f"56.{serial}"]["status"], "requires_business_review")')

text = text.replace('self.assertEqual(source_item["sr_number"], "303")', 'self.assertEqual(source_item["new_sr_number"], "19.6")')
text = text.replace('if source_item["sr_number"] == "393":', 'if source_item["new_sr_number"] == "21.15":')
text = text.replace('self.assertIn("393", notes)', 'self.assertIn("21.15", notes)')
text = text.replace('source_item["sr_number"] not in {"303", "393"}', 'source_item["new_sr_number"] not in {"19.6", "21.15"}')
text = text.replace('f"Source particulars not found for sr_number {source_item[\'sr_number\']}: "', 'f"Source particulars not found for sr_number {source_item[\'new_sr_number\']}: "')

# For image mappings
text = text.replace('image_ref.startswith("sr_") or "_sr_" in image_ref', 'bool(re.match(r"^[\d.,-]+_", image_ref))')
text = text.replace('self.assertTrue(all(stem.startswith(("sr_", "group_", "groups_")) for stem in image_stems))', 'self.assertTrue(all(re.match(r"^[\d.,-]+_", stem) for stem in image_stems))')

# Also fix the regex in test_every_source_photo_is_serial_mapped_and_kept_in_the_asset_output
text = text.replace('r"(?:^|_)sr_(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)_"', 'r"^([\d.,-]+)_"')

p.write_text(text, 'utf-8')
print("DONE REPLACING")
