import pathlib, re
p2 = pathlib.Path('tests/test_catalog.py')
t2 = p2.read_text('utf-8')
t2 = re.sub(r'valid\[\"sr_number\"\] = \"1\"', 'valid[\"sr_number\"] = \"1.1\"', t2)
t2 = re.sub(r'self\.assertTrue\(all\(serial > 0 for serial in serials\)\)', 'self.assertTrue(all(len(serial.split(\".\")) == 2 for serial in serials))', t2)
p2.write_text(t2, 'utf-8')
print("Done")
