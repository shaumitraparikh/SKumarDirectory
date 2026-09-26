import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

rows = list(csv.DictReader(open('data/catalog_data.csv', 'r', encoding='utf-8-sig')))
for r in rows:
    if r['sr_no'] in ['1361', '1370', '1380', '1390']:
        print(f"{r['sr_no']} | {r['item_name']}")
