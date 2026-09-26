import csv
rows = list(csv.DictReader(open('data/catalog_data.csv', 'r', encoding='utf-8-sig')))
for i in range(0, len(rows), 40):
    print(f"{rows[i]['sr_no']} : {rows[i]['item_name'][:40]}")
