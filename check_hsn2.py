import csv
with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if 'HSN' in row['item_name'].upper() and len(row['item_name']) < 30:
            print(f"Sr {row['sr_no']} | Name: {row['item_name']} | Price: {row['list_price']}")
