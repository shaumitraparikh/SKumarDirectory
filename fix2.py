import pathlib, re
p = pathlib.Path('tests/test_seller_tools.py')
text = p.read_text('utf-8')
text = re.sub(r'\"sr_number\":\s*\"\d+\",\s*\"group_number\":\s*\"\d+\",\s*\"item_number\":\s*\"\d+\",', '\"sr_number\": \"1.1\",', text)
p.write_text(text, 'utf-8')

p2 = pathlib.Path('tests/test_catalog.py')
t2 = p2.read_text('utf-8')
t2 = re.sub(r'self\.by_serial\[71\]', 'self.by_serial[\"7.2\"]', t2)
t2 = re.sub(r'self\.by_serial\[1412\]', 'self.by_serial[\"65.1\"]', t2)
t2 = re.sub(r'notes\[\"393\"\]', 'notes[\"21.15\"]', t2)
t2 = re.sub(r'item\[\"group_number\"\]', 'item[\"sr_number\"].split(\".\")[0]', t2)
t2 = re.sub(r'item\[\"item_number\"\]', 'item[\"sr_number\"].split(\".\")[1]', t2)

t2 = re.sub(r'valid\[\"sr_number\"\] = \"1\"', 'valid[\"sr_number\"] = \"1.1\"', t2)
p2.write_text(t2, 'utf-8')
print("Done")
