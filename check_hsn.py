import csv
with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if 'HSN' in row['item_name'].upper() or 'HSN' in row['category'].upper():
            print(f"{row['sr_no']} | Cat: {row['category']} | Name: {row['item_name']}")
