import csv
with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for r in list(csv.DictReader(f))[138:143]:
        print(f"{r['sr_no']} | Cat: {r['category']} | Name: {r['item_name']}")
