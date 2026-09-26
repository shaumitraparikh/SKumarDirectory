import csv
with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['image_ref'].startswith('item_'):
            print(f"{r['sr_no']} | {r['item_name']} | {r['image_ref']}")
