import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

rows = list(csv.DictReader(open('data/catalog_data.csv', 'r', encoding='utf-8-sig')))
for r in rows:
    if r['sr_no'].isdigit():
        sr = int(r['sr_no'])
        if sr in [1020, 1040, 1082, 1101, 1108, 1150, 1168, 1169, 1233, 1258, 1284, 1361, 1391, 1437]:
            print(f"{sr} : Cat={r['category']} | Name={r['item_name'][:30]}")
