import csv
rows = list(csv.DictReader(open('data/catalog_data.csv', 'r', encoding='utf-8-sig')))
issues = []
for r in rows:
    if not r['item_name']: issues.append(f"SR {r['sr_no']}: Empty Name")
    if not r['list_price']: issues.append(f"SR {r['sr_no']}: No Price")
print(f"Found {len(issues)} issues.")
if issues: print(issues[:5])
